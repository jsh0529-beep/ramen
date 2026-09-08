"""3단계: 내레이션 및 음향 엔진 (The Voice & Sound)

- ElevenLabs로 다큐멘터리 톤 내레이션 합성 (섹션별 → 컷 편집 기준점 확보)
- 문맥 감정 분석 결과로 성우 억양(voice_settings)과 BGM 템포를 자동 조절
- Epidemic Sound 어댑터 / 오프라인 시 무드별 앰비언트 드론을 직접 합성
"""
from __future__ import annotations

import logging
import math
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import requests

from .config import Settings
from .models import NarrationClip, Script

log = logging.getLogger(__name__)
SR = 44100
KOREAN_CHARS_PER_SEC = 5.5

# 감정 → 성우 억양 (ElevenLabs voice_settings)
MOOD_VOICE = {
    "tragic":  {"stability": 0.80, "similarity_boost": 0.80, "style": 0.15, "use_speaker_boost": True},
    "grand":   {"stability": 0.55, "similarity_boost": 0.80, "style": 0.55, "use_speaker_boost": True},
    "mystery": {"stability": 0.65, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True},
    "neutral": {"stability": 0.70, "similarity_boost": 0.75, "style": 0.25, "use_speaker_boost": True},
}
# 감정 → BGM 파라미터 (Epidemic Sound 검색 태그 + 오프라인 합성 파라미터)
MOOD_MUSIC = {
    "tragic":  {"tags": ["melancholic", "piano", "slow"], "bpm": 60,  "chord": [110.0, 130.81, 164.81]},   # A minor
    "grand":   {"tags": ["epic", "orchestral", "hopeful"], "bpm": 90, "chord": [130.81, 164.81, 196.0]},   # C major
    "mystery": {"tags": ["suspense", "ambient", "dark"], "bpm": 70,  "chord": [116.54, 138.59, 174.61]},  # Bb min-ish
    "neutral": {"tags": ["documentary", "calm", "underscore"], "bpm": 80, "chord": [123.47, 155.56, 185.0]},
}


def write_wav(path: Path, samples: np.ndarray, sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


# ── 내레이션 ──────────────────────────────────────────────────────────

class ElevenLabsTTS:
    API = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, settings: Settings):
        self.s = settings

    def synthesize(self, text: str, mood: str, dest_wav: Path) -> Optional[float]:
        url = f"{self.API}/{self.s.elevenlabs_voice_id}"
        headers = {"xi-api-key": self.s.elevenlabs_api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
        body = {"text": text, "model_id": self.s.elevenlabs_model, "voice_settings": MOOD_VOICE.get(mood, MOOD_VOICE["neutral"])}
        try:
            r = requests.post(url, headers=headers, json=body, timeout=120)
            r.raise_for_status()
        except requests.RequestException as e:
            log.warning("ElevenLabs 합성 실패: %s", e)
            return None
        mp3 = dest_wav.with_suffix(".mp3")
        mp3.write_bytes(r.content)
        from moviepy import AudioFileClip
        with AudioFileClip(str(mp3)) as clip:
            clip.write_audiofile(str(dest_wav), fps=SR, nbytes=2, codec="pcm_s16le", logger=None)
        return wav_duration(dest_wav)


class OfflineTTS:
    """API 없이 타이밍만 재현: 글자 수 기반 길이의 저음량 신호(문장 경계에 숨 쉬는 무음 포함)."""

    def synthesize(self, text: str, mood: str, dest_wav: Path) -> float:
        from .models import split_sentences
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        chunks = []
        for sent in split_sentences(text) or [text]:
            dur = max(1.0, len(sent) / KOREAN_CHARS_PER_SEC)
            n = int(dur * SR)
            env = np.hanning(n) ** 0.3
            voice = rng.normal(0, 0.01, n) * env  # 매우 낮은 잡음 = "말소리" 자리 표시
            chunks += [voice, np.zeros(int(0.35 * SR))]  # 문장 끝 숨 쉬는 구간
        samples = np.concatenate(chunks)
        write_wav(dest_wav, samples)
        return len(samples) / SR


def synthesize_narration(script: Script, settings: Settings, workdir: Path) -> list[NarrationClip]:
    out_dir = workdir / "narration"
    out_dir.mkdir(parents=True, exist_ok=True)
    eleven = ElevenLabsTTS(settings) if settings.can_use_elevenlabs else None
    offline = OfflineTTS()
    clips = []
    for i, sec in enumerate(script.sections):
        dest = out_dir / f"{i:02d}_{sec.part}.wav"
        dur = eleven.synthesize(sec.text(), sec.mood, dest) if eleven else None
        engine = "elevenlabs"
        if dur is None:
            dur = offline.synthesize(sec.text(), sec.mood, dest)
            engine = "offline"
        log.info("내레이션 %d (%s, %s): %.1fs [%s]", i, sec.part, sec.mood, dur, engine)
        clips.append(NarrationClip(i, str(dest), dur, sec.mood, sec.text()))
    return clips


# ── 배경음악 ──────────────────────────────────────────────────────────

class EpidemicSoundMusic:
    """Epidemic Sound Partner API 어댑터 (파트너 계약 필요). 무드 태그로 트랙을 검색해 다운로드."""

    def __init__(self, settings: Settings):
        self.s = settings

    def available(self) -> bool:
        return self.s.can_use_network and bool(self.s.epidemic_api_key and self.s.epidemic_api_base)

    def fetch(self, mood: str, dest: Path) -> Optional[Path]:
        if not self.available():
            return None
        try:
            headers = {"Authorization": f"Bearer {self.s.epidemic_api_key}"}
            r = requests.get(f"{self.s.epidemic_api_base}/tracks/search",
                             params={"moods": ",".join(MOOD_MUSIC[mood]["tags"]), "limit": 1},
                             headers=headers, timeout=self.s.http_timeout)
            r.raise_for_status()
            track = (r.json().get("tracks") or [None])[0]
            if not track:
                return None
            audio = requests.get(track["downloadUrl"], headers=headers, timeout=120)
            audio.raise_for_status()
            dest.write_bytes(audio.content)
            return dest
        except (requests.RequestException, KeyError, ValueError) as e:
            log.warning("Epidemic Sound 조회 실패: %s", e)
            return None


def synth_ambient(mood: str, duration: float, dest: Path) -> Path:
    """무드별 코드 드론 + 템포에 맞춘 완만한 펄스 (저작권 문제 없는 자체 합성 BGM)."""
    p = MOOD_MUSIC.get(mood, MOOD_MUSIC["neutral"])
    n = int(duration * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k, f in enumerate(p["chord"]):
        for harm, amp in ((1, 1.0), (2, 0.35), (3, 0.12)):
            sig += amp / (k + 1) * np.sin(2 * math.pi * f * harm * t + k)
    pulse = 0.75 + 0.25 * np.sin(2 * math.pi * (p["bpm"] / 60.0) * t)  # 템포 펄스
    fade = np.minimum(1.0, np.minimum(t / 3.0, (duration - t) / 3.0))
    sig = sig / np.max(np.abs(sig)) * 0.5 * pulse * np.clip(fade, 0, 1)
    write_wav(dest, sig)
    return dest


def dominant_mood(script: Script) -> str:
    counts = {}
    for s in script.sections:
        counts[s.mood] = counts.get(s.mood, 0) + len(s.text())
    return max(counts, key=counts.get) if counts else "neutral"


def prepare_music(script: Script, total_duration: float, settings: Settings, workdir: Path) -> tuple[Path, str]:
    mood = dominant_mood(script)
    dest = workdir / "music" / f"bgm_{mood}.mp3"
    dest.parent.mkdir(parents=True, exist_ok=True)
    got = EpidemicSoundMusic(settings).fetch(mood, dest)
    if got:
        return got, "epidemic_sound"
    return synth_ambient(mood, total_duration + 2.0, dest.with_suffix(".wav")), "synth"
