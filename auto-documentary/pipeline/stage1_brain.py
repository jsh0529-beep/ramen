"""1단계: 주제 발굴 및 대본 작성 엔진 (The Brain)

- 공공 데이터(국가유산청 Open API, 한국어 위키백과, 주제 DB)에서 원문 수집
- 크로스 체크 알고리즘: 연도·수치 단위의 사실을 출처 간 교차 검증
- 스토리텔링 모듈: 도입-전개-위기-결말 4막 구조로 대본 정렬
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Optional

import requests
import yaml

from .config import PROJECT_ROOT, Settings
from .llm import LLM, parse_json_block
from .models import MOODS, PART_LABELS, PARTS, Fact, Script, ScriptSection, SourceDoc, split_sentences

log = logging.getLogger(__name__)
TOPIC_DB = PROJECT_ROOT / "topics" / "recommended_topics.yaml"
UA = {"User-Agent": "auto-documentary/0.1 (educational; contact: repo owner)"}


# ── 주제 DB ───────────────────────────────────────────────────────────

def load_topic_db(path: Path = TOPIC_DB) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["topics"]


def find_topic_entry(topic: str, db: Optional[list[dict]] = None) -> Optional[dict]:
    db = db or load_topic_db()
    norm = re.sub(r"\s+", "", topic)
    for entry in db:
        names = [entry["id"], entry["title"], *entry.get("aliases", [])]
        for n in names:
            n2 = re.sub(r"\s+", "", n)
            if norm == n2 or norm in n2 or n2 in norm:
                return entry
    # 키워드 부분 일치
    for entry in db:
        if any(k and k in topic for k in entry.get("keywords", [])):
            return entry
    return None


# ── 출처 수집 ─────────────────────────────────────────────────────────

class WikipediaSource:
    API = "https://ko.wikipedia.org/w/api.php"

    def __init__(self, settings: Settings):
        self.s = settings

    def fetch(self, terms: list[str], limit: int = 2) -> list[SourceDoc]:
        docs: list[SourceDoc] = []
        for term in terms[:3]:
            try:
                r = requests.get(self.API, params={"action": "query", "list": "search", "srsearch": term,
                                                   "srlimit": limit, "format": "json"},
                                 headers=UA, timeout=self.s.http_timeout)
                r.raise_for_status()
                hits = r.json().get("query", {}).get("search", [])
                ids = [str(h["pageid"]) for h in hits]
                if not ids:
                    continue
                r = requests.get(self.API, params={"action": "query", "prop": "extracts", "explaintext": 1,
                                                   "pageids": "|".join(ids), "format": "json"},
                                 headers=UA, timeout=self.s.http_timeout)
                r.raise_for_status()
                for pid, page in r.json().get("query", {}).get("pages", {}).items():
                    text = page.get("extract", "")
                    if len(text) < 200:
                        continue
                    docs.append(SourceDoc("wikipedia", page["title"],
                                          f"https://ko.wikipedia.org/?curid={pid}", text, "CC BY-SA 4.0"))
            except requests.RequestException as e:
                log.warning("위키백과 조회 실패(%s): %s", term, e)
        return docs


class KhsSource:
    """국가유산청 문화유산 정보 Open API (XML, 키 불필요)."""

    def __init__(self, settings: Settings):
        self.s = settings

    def fetch(self, names: list[str]) -> list[SourceDoc]:
        docs: list[SourceDoc] = []
        for name in names:
            try:
                r = requests.get(f"{self.s.khs_api_base}/SearchKindOpenapiList.do",
                                 params={"ccbaMnm1": name, "pageUnit": 3}, headers=UA, timeout=self.s.http_timeout)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                for item in root.iter("item"):
                    kdcd, asno, ctcd = (item.findtext(k, "") for k in ("ccbaKdcd", "ccbaAsno", "ccbaCtcd"))
                    if not (kdcd and asno and ctcd):
                        continue
                    d = requests.get(f"{self.s.khs_api_base}/SearchKindOpenapiDt.do",
                                     params={"ccbaKdcd": kdcd, "ccbaAsno": asno, "ccbaCtcd": ctcd},
                                     headers=UA, timeout=self.s.http_timeout)
                    d.raise_for_status()
                    droot = ET.fromstring(d.content)
                    content = droot.findtext(".//content", "") or ""
                    title = droot.findtext(".//ccbaMnm1", name) or name
                    if content.strip():
                        docs.append(SourceDoc("khs", title, d.url, re.sub(r"<[^>]+>", "", content), "공공누리"))
            except (requests.RequestException, ET.ParseError) as e:
                log.warning("국가유산청 API 조회 실패(%s): %s", name, e)
        return docs


class TopicDBSource:
    """저장소에 동봉된 편집 노트. 단독으로는 '검증된 사실'이 되지 못합니다."""

    def fetch(self, entry: Optional[dict]) -> list[SourceDoc]:
        if not entry:
            return []
        text = entry["summary"] + " " + " ".join(
            s for part in entry["outline"].values() for s in part["sentences"])
        return [SourceDoc("topic_db", entry["title"], "topics/recommended_topics.yaml", text, "editorial")]


def collect_sources(topic: str, entry: Optional[dict], settings: Settings) -> list[SourceDoc]:
    docs = TopicDBSource().fetch(entry)
    if settings.can_use_network:
        terms = (entry or {}).get("search_terms") or [topic]
        docs += WikipediaSource(settings).fetch(terms)
        docs += KhsSource(settings).fetch((entry or {}).get("khs_names", []))
    log.info("수집된 출처 %d건: %s", len(docs), [f"{d.source}:{d.title}" for d in docs])
    return docs


# ── 크로스 체크 알고리즘 ──────────────────────────────────────────────

YEAR_RE = re.compile(r"(?<!\d)(1[0-9]{3}|20[0-9]{2})년(?!대)")
NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(톤|미터|m|층|명|개|km|㎡|평|년간|배)")


def extract_fact_keys(text: str) -> dict[str, str]:
    """텍스트에서 (정규화 키 → 근거 문장) 추출."""
    keys: dict[str, str] = {}
    for sent in split_sentences(text):
        for m in YEAR_RE.finditer(sent):
            keys.setdefault(f"{m.group(1)}년", sent)
        for m in NUM_RE.finditer(sent):
            keys.setdefault(f"{m.group(1).replace(',', '')}{m.group(2)}", sent)
    return keys


def cross_check(docs: list[SourceDoc]) -> list[Fact]:
    """서로 다른 출처 2곳 이상에서 등장한 키만 verified=True."""
    by_key: dict[str, dict] = defaultdict(lambda: {"sources": set(), "statement": ""})
    for d in docs:
        for key, sent in extract_fact_keys(d.text).items():
            by_key[key]["sources"].add(d.source)
            if d.source != "topic_db" or not by_key[key]["statement"]:
                by_key[key]["statement"] = sent
    facts = [Fact(key=k, statement=v["statement"], sources=sorted(v["sources"]),
                  verified=len(v["sources"]) >= 2) for k, v in by_key.items()]
    facts.sort(key=lambda f: (not f.verified, f.key))
    return facts


def audit_script(script: Script) -> list[str]:
    """대본에 등장하지만 교차 검증되지 않은 연도·수치를 보고."""
    verified = {f.key for f in script.facts if f.verified}
    claims = extract_fact_keys(script.full_text())
    return sorted(k for k in claims if k not in verified)


# ── 스토리텔링 모듈 ───────────────────────────────────────────────────

MOOD_KEYWORDS = {
    "tragic": ["화재", "붕괴", "소실", "비극", "방치", "폐쇄", "논란", "충돌", "반대", "박락", "사고", "철거"],
    "grand": ["복원", "완공", "웅장", "준공", "상징", "증언", "자리 잡", "되살"],
    "mystery": ["비밀", "미스터리", "의문", "유령", "왜", "어떻게 된", "없었다", "닫힌"],
}


def detect_mood(text: str) -> str:
    scores = {m: sum(text.count(k) for k in ks) for m, ks in MOOD_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


SYSTEM_PROMPT = """당신은 건축·역사 다큐멘터리 '신비한 건축사전'의 수석 작가입니다.
원칙:
1. 제공된 [검증된 사실] 목록에 있는 연도·수치만 사용합니다. 목록에 없는 연도·수치는 절대 지어내지 않습니다.
2. 과장된 어휘를 피하고, 명확한 정보 전달 위주의 담담한 다큐멘터리 톤으로 씁니다.
3. 반드시 '도입(의문 제기) - 전개(역사적 배경) - 위기(문제 발생) - 결말(현재의 모습)' 4막 구조를 지킵니다.
4. 출력은 JSON 하나만, 다른 설명 없이 반환합니다."""

USER_PROMPT = """주제: {topic}
목표 분량: 약 {minutes}분 (한국어 낭독 기준 약 {chars}자)

[검증된 사실]
{verified}

[미검증 사실 — 사용 금지 또는 '~로 알려져 있다'로 완화]
{unverified}

[참고 원문]
{sources}

다음 JSON 스키마로 작성하세요:
{{
  "title": "영상 제목",
  "sections": [
    {{"part": "intro", "heading": "소제목", "mood": "mystery|tragic|grand|neutral",
      "visual_query": "영문 이미지 검색어", "sentences": ["문장1", "문장2", ...]}},
    {{"part": "development", ...}}, {{"part": "crisis", ...}}, {{"part": "resolution", ...}}
  ]
}}"""

KOREAN_CHARS_PER_SEC = 5.5  # 다큐 내레이션 평균 속도(공백 포함)


def _template_script(topic: str, entry: Optional[dict], docs: list[SourceDoc]) -> tuple[str, list[ScriptSection]]:
    if entry:
        sections = []
        for part in PARTS:
            o = entry["outline"][part]
            sections.append(ScriptSection(part, o["heading"], list(o["sentences"]),
                                          o.get("mood") or detect_mood(" ".join(o["sentences"])),
                                          o.get("visual_query", "")))
        return entry["title"], sections
    # 주제 DB에 없는 주제: 원문 문장을 4막에 균등 배분 (LLM 키가 있으면 이 경로를 타지 않음)
    sents = [s for d in docs if d.source != "topic_db" for s in split_sentences(d.text)][:16]
    if not sents:
        sents = [f"'{topic}'에 대한 원문을 찾지 못했습니다. GEMINI_API_KEY를 설정하거나 topics/recommended_topics.yaml에 주제를 추가하세요."] * 4
    per = max(1, len(sents) // 4)
    sections = []
    for i, part in enumerate(PARTS):
        chunk = sents[i * per:(i + 1) * per] if i < 3 else sents[3 * per:]
        sections.append(ScriptSection(part, PART_LABELS[part], chunk or ["(내용 없음)"],
                                      detect_mood(" ".join(chunk)), topic))
    return topic, sections


def _llm_script(topic: str, docs: list[SourceDoc], facts: list[Fact], llm: LLM, minutes: float) -> Optional[tuple[str, list[ScriptSection]]]:
    verified = "\n".join(f"- {f.key}: {f.statement} (출처: {', '.join(f.sources)})" for f in facts if f.verified) or "- (없음)"
    unverified = "\n".join(f"- {f.key} (출처: {', '.join(f.sources)})" for f in facts if not f.verified) or "- (없음)"
    sources = "\n\n".join(f"### [{d.source}] {d.title}\n{d.text[:2500]}" for d in docs)
    prompt = USER_PROMPT.format(topic=topic, minutes=minutes, chars=int(minutes * 60 * KOREAN_CHARS_PER_SEC),
                                verified=verified, unverified=unverified, sources=sources)
    data = parse_json_block(llm.complete(SYSTEM_PROMPT, prompt))
    if not data or "sections" not in data:
        return None
    sections = []
    for sec in data["sections"]:
        part = sec.get("part") if sec.get("part") in PARTS else PARTS[min(len(sections), 3)]
        mood = sec.get("mood") if sec.get("mood") in MOODS else detect_mood(" ".join(sec.get("sentences", [])))
        sections.append(ScriptSection(part, sec.get("heading", PART_LABELS[part]),
                                      [str(s) for s in sec.get("sentences", []) if str(s).strip()],
                                      mood, sec.get("visual_query", topic)))
    if len(sections) < 4:
        return None
    return data.get("title", topic), sections


def write_script(topic: str, settings: Settings, llm: Optional[LLM] = None,
                 entry: Optional[dict] = None) -> Script:
    entry = entry or find_topic_entry(topic)
    docs = collect_sources(topic, entry, settings)
    facts = cross_check(docs)
    result = None
    if llm is not None:
        try:
            result = _llm_script(topic, docs, facts, llm, settings.target_minutes)
        except Exception as e:  # API 오류는 템플릿으로 폴백
            log.warning("LLM 대본 생성 실패, 템플릿 모드로 전환: %s", e)
    if result is None:
        result = _template_script(topic, entry, docs)
    title, sections = result
    script = Script(topic=topic, title=title, sections=sections, facts=facts,
                    sources=[{"source": d.source, "title": d.title, "url": d.url, "license": d.license} for d in docs])
    script.unverified_claims = audit_script(script)
    if script.unverified_claims:
        log.warning("교차 검증되지 않은 주장 %d건: %s", len(script.unverified_claims), script.unverified_claims)
    return script
