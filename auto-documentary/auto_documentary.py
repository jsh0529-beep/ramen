#!/usr/bin/env python3
"""신비한 건축사전 — 완전 자동화 다큐멘터리 생성기

사용법:
  python auto_documentary.py --topic "여의도 국회의사당 돔 지붕의 비밀"
  python auto_documentary.py --topic "숭례문 복원" --offline --size 1280x720   # API 키 없이 파이프라인 검증
  python auto_documentary.py --list-topics
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.config import Settings  # noqa: E402
from pipeline.orchestrator import run_pipeline  # noqa: E402
from pipeline.stage1_brain import load_topic_db  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="신비한 건축사전 자동 다큐멘터리 파이프라인")
    p.add_argument("--topic", help="영상 주제 (topics/recommended_topics.yaml의 제목·별칭 또는 자유 주제)")
    p.add_argument("--list-topics", action="store_true", help="추천 주제 목록 출력")
    p.add_argument("--offline", action="store_true", help="외부 API/네트워크 없이 실행 (플레이스홀더·무음 내레이션)")
    p.add_argument("--minutes", type=float, help="목표 분량(분), 기본 5")
    p.add_argument("--size", help="해상도 WxH (기본 1920x1080)")
    p.add_argument("--fps", type=int, help="프레임레이트 (기본 24)")
    p.add_argument("--out", help="출력 폴더 (기본 ./output)")
    p.add_argument("--publish", action="store_true", help="렌더링 후 유튜브 업로드")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")

    if args.list_topics:
        for t in load_topic_db():
            print(f"[{t['id']}]\n  제목: {t['title']}\n  부제: {t['subtitle']}\n")
        return 0
    if not args.topic:
        p.error("--topic 또는 --list-topics 가 필요합니다.")

    overrides = {"target_minutes": args.minutes, "fps": args.fps}
    if args.size:
        w, h = args.size.lower().split("x")
        overrides.update(width=int(w), height=int(h))
    if args.out:
        overrides["output_dir"] = Path(args.out).resolve()
    settings = Settings.from_env(offline=args.offline, **overrides)

    report = run_pipeline(args.topic, settings, publish=args.publish)
    print("\n=== 완료 ===")
    print(f"영상:     {report['video']}")
    print(f"자막:     {report['subtitles']}")
    print(f"메타데이터: {report['metadata']}")
    print(f"길이:     {report['duration_sec']}s  (모드: {report['mode']})")
    if report["unverified_claims"]:
        print(f"⚠ 교차 검증되지 않은 연도/수치: {', '.join(report['unverified_claims'])} → factcheck_report.json 확인")
    return 0


if __name__ == "__main__":
    sys.exit(main())
