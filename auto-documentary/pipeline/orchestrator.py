"""5단계 파이프라인 오케스트레이터: 한 번의 호출로 mp4 + 메타데이터까지."""
from __future__ import annotations

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Optional

from .config import Settings
from .llm import get_llm
from .models import dump_json, slugify, to_dict
from .stage1_brain import find_topic_entry, write_script
from .stage2_eyes import collect_assets
from .stage3_voice import prepare_music, synthesize_narration
from .stage4_editor import render
from .stage5_publisher import build_metadata, upload_youtube

log = logging.getLogger(__name__)


def run_pipeline(topic: str, settings: Settings, publish: bool = False) -> dict:
    t0 = time.time()
    slug = slugify(topic)
    workdir = settings.output_dir / slug
    workdir.mkdir(parents=True, exist_ok=True)
    entry = find_topic_entry(topic)
    llm = get_llm(settings)
    report: dict = {"topic": topic, "workdir": str(workdir), "mode": "offline" if settings.offline else "online", "timings": {}}

    def step(name):
        report["timings"][name] = round(time.time() - t0, 1)
        log.info("── %s 완료 (누적 %.1fs)", name, time.time() - t0)

    # 1단계 The Brain
    script = write_script(topic, settings, llm, entry)
    dump_json(script, workdir / "script.json")
    dump_json({"facts": script.facts, "unverified_claims": script.unverified_claims, "sources": script.sources,
               "note": "오프라인 모드에서는 외부 출처가 없어 교차 검증이 불가능합니다." if settings.offline else ""},
              workdir / "factcheck_report.json")
    step("1_script")

    # 2단계 The Eyes
    assets = collect_assets(script, settings, workdir, entry)
    dump_json(assets, workdir / "assets.json")
    step("2_visuals")

    # 3단계 The Voice & Sound
    narration = synthesize_narration(script, settings, workdir)
    total = sum(c.duration for c in narration) + 0.4 * len(narration) + 2
    music_path, music_source = prepare_music(script, total, settings, workdir)
    dump_json({"clips": narration, "music": str(music_path), "music_source": music_source}, workdir / "narration.json")
    step("3_audio")

    # 4단계 The Editor
    result = render(script, assets, narration, music_path, settings, workdir, "render")
    dump_json(result, workdir / "render.json")
    step("4_render")

    # 5단계 The Publisher
    meta = build_metadata(script, result, assets, entry, llm)
    final_video = workdir / f"[완성본]{slug}.mp4"
    shutil.copyfile(result.video_path, final_video)
    shutil.copyfile(result.srt_path, final_video.with_suffix(".srt"))
    if publish:
        if settings.offline:
            log.warning("오프라인 모드에서는 업로드를 건너뜁니다.")
        else:
            meta.youtube_video_id = upload_youtube(final_video, meta, settings)
    dump_json(meta, workdir / "metadata.json")
    step("5_publish")

    report.update({"video": str(final_video), "subtitles": str(final_video.with_suffix('.srt')),
                   "duration_sec": result.duration, "metadata": str(workdir / "metadata.json"),
                   "unverified_claims": script.unverified_claims, "youtube_video_id": meta.youtube_video_id})
    (workdir / "run_report.json").write_text(json.dumps(to_dict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return report
