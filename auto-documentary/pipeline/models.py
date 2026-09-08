"""파이프라인 전 단계가 공유하는 데이터 모델."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

PARTS = ("intro", "development", "crisis", "resolution")
PART_LABELS = {
    "intro": "도입 (의문 제기)",
    "development": "전개 (역사적 배경)",
    "crisis": "위기 (문제 발생)",
    "resolution": "결말 (현재의 모습)",
}
MOODS = ("neutral", "mystery", "tragic", "grand")


@dataclass
class SourceDoc:
    """신뢰할 수 있는 출처에서 가져온 원문."""
    source: str            # wikipedia | khs | topic_db | ...
    title: str
    url: str
    text: str
    license: str = ""


@dataclass
class Fact:
    """교차 검증 대상이 되는 사실 단위(연도, 수치 등)."""
    key: str               # 정규화된 키 ("1974년", "1000톤")
    statement: str         # 원문에서 발췌한 문장
    sources: list[str]     # 이 사실을 언급한 출처 이름
    verified: bool         # 서로 다른 출처 2곳 이상에서 확인되면 True


@dataclass
class ScriptSection:
    part: str              # PARTS 중 하나
    heading: str
    sentences: list[str]
    mood: str = "neutral"
    visual_query: str = "" # 시각 자료 검색어 (영문 권장)

    def text(self) -> str:
        return " ".join(s.strip() for s in self.sentences if s.strip())


@dataclass
class Script:
    topic: str
    title: str
    sections: list[ScriptSection]
    facts: list[Fact] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)

    def full_text(self) -> str:
        return "\n\n".join(s.text() for s in self.sections)


@dataclass
class VisualAsset:
    section_index: int
    kind: str              # photo | broll | placeholder
    path: str
    source: str            # wikimedia_commons | gongu | runway | offline
    license: str
    credit: str
    prompt: str = ""
    page_url: str = ""


@dataclass
class NarrationClip:
    section_index: int
    path: str              # WAV
    duration: float
    mood: str
    text: str


@dataclass
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


@dataclass
class RenderResult:
    video_path: str
    srt_path: str
    duration: float
    scenes: list[dict]


@dataclass
class PublishMetadata:
    title: str
    subtitle: str
    description: str
    tags: list[str]
    chapters: list[dict]
    youtube_video_id: Optional[str] = None


# ── 유틸 ──────────────────────────────────────────────────────────────

def slugify(text: str, max_len: int = 60) -> str:
    """한글을 유지하는 파일명 안전 슬러그."""
    text = unicodedata.normalize("NFC", text).strip()
    text = re.sub(r"[\\/:*?\"<>|'‘’“”]+", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:max_len] or "untitled"


def to_dict(obj: Any) -> Any:
    """dataclass / dict / list / Path 를 재귀적으로 JSON 직렬화 가능한 형태로 변환."""
    if hasattr(obj, "__dataclass_fields__"):
        return to_dict(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dict(o) for o in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def dump_json(obj: Any, path: Path | str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(to_dict(obj), ensure_ascii=False, indent=2), encoding="utf-8")


def split_sentences(text: str) -> list[str]:
    """한국어 문장 분리(마침표/물음표/느낌표 기준)."""
    parts = re.split(r"(?<=[.!?。])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]
