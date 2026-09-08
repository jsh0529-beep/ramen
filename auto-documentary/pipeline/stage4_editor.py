"""4단계: 비디오 렌더링 및 편집 엔진 (The Editor)

- 정지 사진 켄 번스 효과 (줌 인/아웃, 좌우 패닝을 섹션마다 번갈아 적용)
- 오디오 파형 매칭 컷 편집: 문장이 끝나는 무음(숨 쉬는 구간)에 컷 포인트를 스냅
- 자막: Whisper(설치 시) 또는 대본 기반 타이밍으로 SRT 생성 + 화면에 번인
- MoviePy + FFmpeg(imageio-ffmpeg 번들)로 최종 mp4 렌더링
"""
from __future__ import annotations

import logging
import wave
from pathlib import Path
from typing import Optional

import numpy as np

from .config import Settings
from .fonts import find_korean_font
from .models import NarrationClip, RenderResult, Script, SubtitleCue, VisualAsset, split_sentences
from .stage3_voice import SR, write_wav

log = logging.getLogger(__name__)
INTER_SCENE_GAP = 0.4   # 섹션 사이 여백(초)
TAIL = 1.5              # 마지막 장면 여운(초)


# ── 오디오 파형 분석 ──────────────────────────────────────────────────

def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        n, sr, ch, sw = w.getnframes(), w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16 if sw == 2 else np.uint8).astype(np.float32)
    if ch > 1:
        raw = raw.reshape(-1, ch).mean(axis=1)
    raw /= 32768.0
    if sr != SR:  # 단순 선형 리샘플
        x_old = np.linspace(0, 1, len(raw))
        raw = np.interp(np.linspace(0, 1, int(len(raw) * SR / sr)), x_old, raw)
    return raw


def detect_silences(samples: np.ndarray, frame_ms: int = 20, thresh: float = 0.004, min_len: float = 0.2) -> list[tuple[float, float]]:
    """RMS 에너지가 임계값 아래로 유지되는 구간(숨 쉬는 구간) 목록."""
    hop = int(SR * frame_ms / 1000)
    n_frames = len(samples) // hop
    if n_frames == 0:
        return []
    rms = np.sqrt(np.mean(samples[: n_frames * hop].reshape(n_frames, hop) ** 2, axis=1))
    quiet = rms < thresh
    silences, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * hop / SR >= min_len:
                silences.append((start * hop / SR, i * hop / SR))
            start = None
    if start is not None and (n_frames - start) * hop / SR >= min_len:
        silences.append((start * hop / SR, n_frames * hop / SR))
    return silences


def snap_cut(t: float, silences: list[tuple[float, float]], window: float = 0.5) -> float:
    """컷 시점 t를 가장 가까운 무음 구간의 중앙으로 스냅 (window 이내일 때만)."""
    best, best_d = t, window
    for s, e in silences:
        mid = (s + e) / 2
        d = abs(mid - t)
        if s <= t <= e:
            return t  # 이미 무음 안 → 그대로
        if d < best_d:
            best, best_d = mid, d
    return best


def build_timeline(narration: list[NarrationClip], workdir: Path) -> tuple[Path, list[dict], list[tuple[float, float]]]:
    """섹션별 내레이션을 하나의 트랙으로 합치고, 무음 구간에 맞춰 장면 경계를 확정."""
    parts, scenes, t = [], [], 0.0
    for clip in narration:
        s = read_wav(Path(clip.path))
        parts += [s, np.zeros(int(INTER_SCENE_GAP * SR), dtype=np.float32)]
        scenes.append({"index": clip.section_index, "narration_start": t, "narration_end": t + clip.duration, "mood": clip.mood})
        t += clip.duration + INTER_SCENE_GAP
    full = np.concatenate(parts) if parts else np.zeros(SR, dtype=np.float32)
    full_path = workdir / "narration" / "narration_full.wav"
    write_wav(full_path, full)
    silences = detect_silences(full)

    total = len(full) / SR + TAIL
    cuts = [0.0]
    for sc in scenes[1:]:
        raw_cut = sc["narration_start"] - INTER_SCENE_GAP / 2
        cuts.append(snap_cut(raw_cut, silences))
    cuts.append(total)
    for i, sc in enumerate(scenes):
        sc["start"], sc["end"] = round(cuts[i], 3), round(cuts[i + 1], 3)
        sc["duration"] = round(sc["end"] - sc["start"], 3)
        sc["cut_snapped_from"] = round(sc["narration_start"] - INTER_SCENE_GAP / 2, 3) if i else 0.0
    return full_path, scenes, silences


# ── 켄 번스 효과 ──────────────────────────────────────────────────────

KB_VARIANTS = [
    {"zoom": (1.00, 1.12), "from": (0.0, 0.0), "to": (0.0, 0.0)},     # 중앙 줌 인
    {"zoom": (1.12, 1.00), "from": (0.0, 0.0), "to": (0.0, 0.0)},     # 줌 아웃
    {"zoom": (1.08, 1.10), "from": (-0.04, 0.0), "to": (0.04, 0.0)},  # 좌→우 패닝
    {"zoom": (1.10, 1.08), "from": (0.04, -0.02), "to": (-0.04, 0.02)},  # 우→좌 대각 패닝
]


def ken_burns_clip(image_path: str, duration: float, size: tuple[int, int], variant: int):
    from moviepy import CompositeVideoClip, ImageClip
    W, H = size
    v = KB_VARIANTS[variant % len(KB_VARIANTS)]
    base = ImageClip(image_path)
    iw, ih = base.size
    cover = max(W / iw, H / ih) * 1.02
    z0, z1 = v["zoom"]
    (fx, fy), (tx, ty) = v["from"], v["to"]

    def scale(t):
        p = min(1.0, t / max(duration, 1e-6))
        return cover * (z0 + (z1 - z0) * p)

    def pos(t):
        p = min(1.0, t / max(duration, 1e-6))
        s = scale(t)
        cw, ch = iw * s, ih * s
        cx = 0.5 + fx + (tx - fx) * p
        cy = 0.5 + fy + (ty - fy) * p
        return (W / 2 - cx * cw, H / 2 - cy * ch)

    clip = base.with_duration(duration).resized(lambda t: scale(t)).with_position(pos)
    return CompositeVideoClip([clip], size=(W, H)).with_duration(duration)


def video_asset_clip(video_path: str, duration: float, size: tuple[int, int]):
    from moviepy import VideoFileClip, vfx
    W, H = size
    clip = VideoFileClip(video_path).without_audio()
    if clip.duration < duration:
        clip = clip.with_effects([vfx.Loop(duration=duration)])
    clip = clip.subclipped(0, duration)
    scale = max(W / clip.w, H / clip.h)
    clip = clip.resized(scale).cropped(x_center=clip.w * scale / 2, y_center=clip.h * scale / 2, width=W, height=H)
    return clip


# ── 자막 ──────────────────────────────────────────────────────────────

def cues_from_script(script: Script, scenes: list[dict]) -> list[SubtitleCue]:
    """대본 문장 길이에 비례해 내레이션 구간 안에서 자막 타이밍 배분."""
    cues, idx = [], 1
    for sc in scenes:
        sec = script.sections[sc["index"]]
        sents = [s for s in sec.sentences if s.strip()] or split_sentences(sec.text())
        total_chars = sum(len(s) for s in sents) or 1
        t = sc["narration_start"]
        span = sc["narration_end"] - sc["narration_start"]
        for s in sents:
            d = span * len(s) / total_chars
            cues.append(SubtitleCue(idx, round(t, 3), round(t + d - 0.05, 3), s.strip()))
            t += d
            idx += 1
    return cues


def cues_from_whisper(full_wav: Path) -> Optional[list[SubtitleCue]]:
    try:
        import whisper  # type: ignore
    except ImportError:
        return None
    try:
        model = whisper.load_model("small")
        result = model.transcribe(str(full_wav), language="ko")
        cues = [SubtitleCue(i + 1, float(s["start"]), float(s["end"]), s["text"].strip())
                for i, s in enumerate(result.get("segments", [])) if s["text"].strip()]
        return cues or None
    except Exception as e:  # 모델 다운로드 실패 등
        log.warning("Whisper 자막 생성 실패, 대본 타이밍으로 대체: %s", e)
        return None


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: list[SubtitleCue], path: Path) -> None:
    lines = [f"{c.index}\n{_srt_time(c.start)} --> {_srt_time(c.end)}\n{c.text}\n" for c in cues]
    path.write_text("\n".join(lines), encoding="utf-8")


def wrap_text(text: str, max_chars: int) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def subtitle_clips(cues: list[SubtitleCue], size: tuple[int, int], font: Optional[str]):
    from moviepy import TextClip
    W, H = size
    if not font:
        log.warning("한글 폰트를 찾지 못해 자막 번인을 건너뜁니다 (SRT는 생성됨). SUBTITLE_FONT를 설정하세요.")
        return []
    font_size = int(H * 0.042)
    clips = []
    for c in cues:
        txt = wrap_text(c.text, max_chars=int(W / font_size * 1.6))
        tc = TextClip(font=font, text=txt, font_size=font_size, color="white", stroke_color="black",
                      stroke_width=max(2, font_size // 14), method="caption", size=(int(W * 0.86), None),
                      text_align="center")
        clips.append(tc.with_start(c.start).with_end(c.end).with_position(("center", H - tc.h - int(H * 0.06))))
    return clips


# ── 렌더링 ────────────────────────────────────────────────────────────

def render(script: Script, assets: list[VisualAsset], narration: list[NarrationClip],
           music_path: Optional[Path], settings: Settings, workdir: Path, output_name: str) -> RenderResult:
    from moviepy import AudioFileClip, CompositeAudioClip, CompositeVideoClip, afx, concatenate_videoclips, vfx

    size = (settings.width, settings.height)
    full_wav, scenes, silences = build_timeline(narration, workdir)
    log.info("타임라인: %d장면, 무음 구간 %d개 감지", len(scenes), len(silences))

    asset_by_idx = {a.section_index: a for a in assets}
    scene_clips = []
    for i, sc in enumerate(scenes):
        a = asset_by_idx[sc["index"]]
        if a.kind == "broll" and a.path.endswith(".mp4"):
            clip = video_asset_clip(a.path, sc["duration"], size)
        else:
            clip = ken_burns_clip(a.path, sc["duration"], size, variant=i)
        clip = clip.with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])
        scene_clips.append(clip)
        sc.update({"asset": a.path, "asset_kind": a.kind, "credit": a.credit, "license": a.license})
    video = concatenate_videoclips(scene_clips, method="compose")

    # 자막
    cues = (cues_from_whisper(full_wav) if settings.can_use_network else None) or cues_from_script(script, scenes)
    srt_path = workdir / f"{output_name}.srt"
    write_srt(cues, srt_path)
    font = find_korean_font(settings.subtitle_font)
    overlays = subtitle_clips(cues, size, font)
    if overlays:
        video = CompositeVideoClip([video, *overlays], size=size).with_duration(video.duration)

    # 오디오: 내레이션 + 덕킹된 BGM
    narration_audio = AudioFileClip(str(full_wav))
    tracks = [narration_audio]
    if music_path and Path(music_path).exists():
        bgm = AudioFileClip(str(music_path))
        if bgm.duration < video.duration:
            bgm = bgm.with_effects([afx.AudioLoop(duration=video.duration)])
        bgm = bgm.subclipped(0, video.duration).with_effects([afx.MultiplyVolume(0.18), afx.AudioFadeOut(2.0)])
        tracks.append(bgm)
    video = video.with_audio(CompositeAudioClip(tracks).with_duration(video.duration))

    out_path = workdir / f"{output_name}.mp4"
    video.write_videofile(str(out_path), fps=settings.fps, codec="libx264", audio_codec="aac",
                          audio_fps=SR, preset="medium", threads=4, logger=None)
    video.close()
    return RenderResult(str(out_path), str(srt_path), round(video.duration, 3), scenes)
