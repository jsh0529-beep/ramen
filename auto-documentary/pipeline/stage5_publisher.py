"""5단계: SEO 최적화 및 배포 엔진 (The Publisher)

- 포털/유튜브 검색 최적화 제목·부제·설명·태그·챕터 타임스탬프 생성 (LLM 또는 템플릿)
- 시각 자료 출처·라이선스 크레딧을 설명글에 자동 삽입
- YouTube Data API v3 업로드 (--publish, OAuth 클라이언트 시크릿 필요)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .config import Settings
from .llm import LLM, parse_json_block
from .models import PublishMetadata, RenderResult, Script, VisualAsset

log = logging.getLogger(__name__)

SEO_SYSTEM = """당신은 한국 포털·유튜브 검색 최적화(SEO) 전문 편집자입니다.
과장·낚시성 어휘를 배제하고, 명확한 정보 전달로 클릭을 유도하는 기사형 제목을 씁니다.
출력은 JSON 하나만 반환합니다."""
SEO_PROMPT = """영상 주제: {topic}
대본 요약:
{summary}

다음 JSON 스키마로 작성하세요:
{{"title": "메인 제목(60자 이내)", "subtitle": "포털 노출 부제목(80자 이내)",
  "description": "설명글 3~5문장", "tags": ["태그1", "태그2", ...(10~15개)]}}"""


def _ts(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"


def build_metadata(script: Script, render: RenderResult, assets: list[VisualAsset],
                   entry: Optional[dict], llm: Optional[LLM]) -> PublishMetadata:
    title = (entry or {}).get("title") or script.title
    subtitle = (entry or {}).get("subtitle", "")
    description = (entry or {}).get("summary", "").strip() or script.sections[0].text()
    tags = list((entry or {}).get("keywords", [])) + ["신비한 건축사전", "건축 다큐멘터리", "한국 건축", "역사"]

    if llm is not None:
        try:
            data = parse_json_block(llm.complete(SEO_SYSTEM, SEO_PROMPT.format(
                topic=script.topic, summary="\n".join(f"- {s.heading}: {s.text()[:200]}" for s in script.sections))))
            if data:
                title, subtitle = data.get("title", title), data.get("subtitle", subtitle)
                description = data.get("description", description)
                tags = list(dict.fromkeys([*data.get("tags", []), *tags]))
        except Exception as e:
            log.warning("SEO 메타데이터 LLM 생성 실패, 템플릿 사용: %s", e)

    chapters = [{"time": _ts(sc["start"]), "seconds": sc["start"], "heading": script.sections[sc["index"]].heading}
                for sc in render.scenes]
    credits = sorted({f"{a.credit} ({a.license})" + (f" {a.page_url}" if a.page_url else "") for a in assets})
    src_lines = [f"- [{s['source']}] {s['title']} {s['url']}" for s in script.sources if s["source"] != "topic_db"]

    full_desc = "\n".join([
        subtitle, "", description, "",
        "📌 타임라인", *[f"{c['time']} {c['heading']}" for c in chapters], "",
        "📚 참고 자료", *(src_lines or ["- 편집부 자료"]), "",
        "🖼️ 시각 자료 출처 (퍼블릭 도메인/자체 생성)", *[f"- {c}" for c in credits], "",
        "#" + " #".join(t.replace(" ", "") for t in tags[:8]),
    ])
    return PublishMetadata(title=title[:100], subtitle=subtitle, description=full_desc, tags=tags[:30], chapters=chapters)


def upload_youtube(video_path: Path, meta: PublishMetadata, settings: Settings) -> Optional[str]:
    """YouTube Data API v3 resumable upload. google-api-python-client, google-auth-oauthlib 필요."""
    try:
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
        from googleapiclient.http import MediaFileUpload  # type: ignore
    except ImportError:
        log.error("유튜브 업로드 라이브러리 미설치: pip install google-api-python-client google-auth-oauthlib")
        return None
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    token_file = Path(settings.youtube_client_secret).with_name("youtube_token.json")
    creds = Credentials.from_authorized_user_file(str(token_file), scopes) if token_file.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(settings.youtube_client_secret, scopes).run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": meta.title, "description": meta.description, "tags": meta.tags, "categoryId": "27",
                        "defaultLanguage": "ko"},
            "status": {"privacyStatus": settings.youtube_privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True))
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            log.info("업로드 %d%%", int(status.progress() * 100))
    video_id = response.get("id")
    log.info("유튜브 업로드 완료: https://youtu.be/%s", video_id)
    return video_id
