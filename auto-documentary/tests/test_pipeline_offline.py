"""API 키·네트워크 없이 5단계 파이프라인이 끝까지 도는지 검증 (저해상도, 수십 초 소요)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.config import Settings
from pipeline.orchestrator import run_pipeline
from pipeline.stage1_brain import cross_check, extract_fact_keys, find_topic_entry
from pipeline.stage2_eyes import license_allowed
from pipeline.stage4_editor import snap_cut
from pipeline.models import SourceDoc


def test_fact_keys_and_cross_check():
    keys = extract_fact_keys("1975년 완공된 의사당의 돔은 1,000톤이다. 1960년대 말 계획.")
    assert "1975년" in keys and "1000톤" in keys and "1960년" not in keys
    facts = cross_check([SourceDoc("wikipedia", "a", "u", "1975년 완공"), SourceDoc("khs", "b", "u", "1975년 준공"),
                         SourceDoc("topic_db", "c", "u", "2008년 화재")])
    by = {f.key: f for f in facts}
    assert by["1975년"].verified and not by["2008년"].verified


def test_license_filter():
    assert license_allowed("Public domain") and license_allowed("CC0") and license_allowed("PD-old-70")
    assert not license_allowed("CC BY-SA 4.0") and not license_allowed("Fair use")


def test_snap_cut():
    assert abs(snap_cut(10.0, [(10.2, 10.6)]) - 10.4) < 1e-9
    assert snap_cut(10.0, [(12.0, 12.5)]) == 10.0  # window 밖 → 그대로


def test_topic_lookup():
    assert find_topic_entry("숭례문 복원")["id"] == "sungnyemun_restoration"
    assert find_topic_entry("전혀 관계없는 주제") is None


def test_offline_end_to_end(tmp_path):
    settings = Settings.from_env(offline=True, width=320, height=180, fps=8, output_dir=tmp_path)
    report = run_pipeline("신설동 유령역", settings)
    video, srt = Path(report["video"]), Path(report["subtitles"])
    assert video.exists() and video.stat().st_size > 10_000
    assert srt.exists() and "-->" in srt.read_text(encoding="utf-8")
    assert report["duration_sec"] > 30
    assert (Path(report["workdir"]) / "factcheck_report.json").exists()
    assert (Path(report["workdir"]) / "metadata.json").exists()
