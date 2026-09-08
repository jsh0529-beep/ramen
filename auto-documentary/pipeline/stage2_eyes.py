"""2단계: 합법적 시각 자료 수집 및 생성 엔진 (The Eyes)

- Wikimedia Commons API에서 퍼블릭 도메인/CC0 자료만 필터링
- 한국저작권위원회 공유마당 API 어댑터 (키·엔드포인트는 .env로 주입)
- 자료가 없는 섹션은 Runway 프롬프트를 자동 생성해 B롤 영상 요청, 오프라인 시 플레이스홀더 생성
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFilter

from .config import Settings
from .fonts import find_korean_font
from .models import Script, ScriptSection, VisualAsset

log = logging.getLogger(__name__)
UA = {"User-Agent": "auto-documentary/0.1 (educational; contact: repo owner)"}

# 법적 리스크 0%를 목표로 하는 허용 라이선스 (Commons extmetadata의 LicenseShortName 기준, 소문자 부분 일치)
ALLOWED_LICENSE_TOKENS = ("public domain", "cc0", "pd-", "pd ", "no restrictions")


def license_allowed(short_name: str) -> bool:
    s = (short_name or "").lower().strip()
    return any(tok in s for tok in ALLOWED_LICENSE_TOKENS) or s == "pd"


class WikimediaCommonsSource:
    API = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, settings: Settings):
        self.s = settings

    def search(self, query: str, limit: int = 8) -> list[dict]:
        params = {"action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
                  "gsrlimit": limit, "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
                  "iiurlwidth": max(self.s.width, 1280), "format": "json"}
        try:
            r = requests.get(self.API, params=params, headers=UA, timeout=self.s.http_timeout)
            r.raise_for_status()
            pages = r.json().get("query", {}).get("pages", {})
        except requests.RequestException as e:
            log.warning("Commons 검색 실패(%s): %s", query, e)
            return []
        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            if not info.get("mime", "").startswith("image/") or info.get("mime") == "image/svg+xml":
                continue
            meta = info.get("extmetadata", {})
            lic = meta.get("LicenseShortName", {}).get("value", "") or meta.get("License", {}).get("value", "")
            if not license_allowed(lic):
                continue
            results.append({
                "title": page.get("title", ""),
                "url": info.get("thumburl") or info.get("url"),
                "page_url": info.get("descriptionurl", ""),
                "license": lic,
                "credit": _strip_html(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons",
            })
        return results

    def download(self, url: str, dest: Path) -> bool:
        try:
            r = requests.get(url, headers=UA, timeout=self.s.http_timeout * 2)
            r.raise_for_status()
            dest.write_bytes(r.content)
            Image.open(dest).verify()
            return True
        except Exception as e:
            log.warning("이미지 다운로드 실패 %s: %s", url, e)
            return False


class GonguSource:
    """공유마당(gongu.copyright.or.kr) Open API 어댑터.

    공유마당 API는 발급 키와 카테고리별 엔드포인트가 필요합니다. .env에 GONGU_API_BASE를
    지정하면 해당 URL에 serviceKey/query를 붙여 호출하고, 응답의 'items' 목록에서
    imageUrl/title/license 필드를 읽습니다. 실제 계약 스펙에 맞춰 parse()를 조정하세요.
    """

    def __init__(self, settings: Settings):
        self.s = settings

    def available(self) -> bool:
        return self.s.can_use_network and bool(self.s.gongu_api_key and self.s.gongu_api_base)

    def search(self, query: str) -> list[dict]:
        if not self.available():
            return []
        try:
            r = requests.get(self.s.gongu_api_base, params={"serviceKey": self.s.gongu_api_key, "query": query,
                                                             "numOfRows": 5, "type": "json"},
                             headers=UA, timeout=self.s.http_timeout)
            r.raise_for_status()
            return self.parse(r.json())
        except (requests.RequestException, ValueError) as e:
            log.warning("공유마당 조회 실패(%s): %s", query, e)
            return []

    @staticmethod
    def parse(data: dict) -> list[dict]:
        items = data.get("items") or data.get("response", {}).get("body", {}).get("items", []) or []
        out = []
        for it in items:
            url = it.get("imageUrl") or it.get("imgUrl")
            if url and license_allowed(it.get("license", "public domain")):
                out.append({"title": it.get("title", ""), "url": url, "page_url": it.get("detailUrl", ""),
                            "license": it.get("license", "공유마당(만료저작물)"), "credit": it.get("author", "공유마당")})
        return out


class RunwayBroll:
    """Runway Gen-3 API 어댑터 (text→video는 계정별 모델 가용성이 달라 실제 스펙 확인 필요)."""

    def __init__(self, settings: Settings):
        self.s = settings

    def generate(self, prompt: str, dest: Path, duration: int = 5) -> Optional[Path]:
        if not self.s.can_use_runway:
            return None
        headers = {"Authorization": f"Bearer {self.s.runway_api_key}", "X-Runway-Version": "2024-11-06",
                   "Content-Type": "application/json"}
        try:
            r = requests.post(f"{self.s.runway_api_base}/text_to_video", headers=headers,
                              json={"model": "gen3a_turbo", "promptText": prompt, "duration": duration, "ratio": "1280:768"},
                              timeout=self.s.http_timeout)
            r.raise_for_status()
            task_id = r.json()["id"]
            for _ in range(60):  # 최대 5분 폴링
                time.sleep(5)
                t = requests.get(f"{self.s.runway_api_base}/tasks/{task_id}", headers=headers, timeout=self.s.http_timeout).json()
                if t.get("status") == "SUCCEEDED":
                    video_url = t["output"][0]
                    dest.write_bytes(requests.get(video_url, timeout=120).content)
                    return dest
                if t.get("status") in ("FAILED", "CANCELLED"):
                    break
        except (requests.RequestException, KeyError, ValueError) as e:
            log.warning("Runway B롤 생성 실패: %s", e)
        return None


# ── 프롬프트 생성 및 플레이스홀더 ─────────────────────────────────────

MOOD_STYLE = {
    "mystery": "dim light, fog, slow dolly, mysterious atmosphere",
    "tragic": "overcast sky, desaturated, somber, slow push-in",
    "grand": "golden hour, wide establishing shot, majestic",
    "neutral": "soft daylight, documentary style, steady camera",
}


def build_broll_prompt(section: ScriptSection, topic: str) -> str:
    subject = section.visual_query or topic
    return f"{subject}, archival documentary B-roll, {MOOD_STYLE.get(section.mood, MOOD_STYLE['neutral'])}, cinematic 4K, no text, no people faces"


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip()


def make_placeholder(dest: Path, heading: str, prompt: str, size: tuple[int, int], mood: str = "neutral") -> Path:
    """오프라인/자료 부족 시 사용하는 플레이스홀더 이미지 (그라데이션 + 소제목 + 프롬프트)."""
    w, h = size
    palette = {"mystery": ((18, 22, 40), (70, 60, 110)), "tragic": ((30, 18, 18), (110, 50, 40)),
               "grand": ((40, 30, 10), (170, 120, 40)), "neutral": ((20, 30, 35), (60, 90, 100))}
    c0, c1 = palette.get(mood, palette["neutral"])
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        col = tuple(int(c0[i] * (1 - t) + c1[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = col
    img = img.filter(ImageFilter.GaussianBlur(2))
    draw = ImageDraw.Draw(img)
    font_path = find_korean_font()
    from PIL import ImageFont
    big = ImageFont.truetype(font_path, int(h * 0.07)) if font_path else ImageFont.load_default()
    small = ImageFont.truetype(font_path, int(h * 0.025)) if font_path else ImageFont.load_default()
    draw.text((w * 0.08, h * 0.40), heading, font=big, fill=(245, 240, 230))
    draw.text((w * 0.08, h * 0.52), "[PLACEHOLDER] " + prompt[:90], font=small, fill=(200, 200, 200))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, quality=90)
    return dest


# ── 수집 파이프라인 ───────────────────────────────────────────────────

def collect_assets(script: Script, settings: Settings, workdir: Path, entry: Optional[dict] = None) -> list[VisualAsset]:
    assets_dir = workdir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    commons = WikimediaCommonsSource(settings)
    gongu = GonguSource(settings)
    runway = RunwayBroll(settings)
    extra_queries = list((entry or {}).get("commons_queries", []))
    used_urls: set[str] = set()
    assets: list[VisualAsset] = []

    for i, sec in enumerate(script.sections):
        asset: Optional[VisualAsset] = None
        queries = [q for q in [sec.visual_query, *extra_queries] if q]

        if settings.can_use_network:
            # 1) 실존 역사 자료 우선 (퍼블릭 도메인/CC0만)
            for q in queries:
                for cand in gongu.search(q) + commons.search(q):
                    if cand["url"] in used_urls:
                        continue
                    dest = assets_dir / f"{i:02d}_photo{Path(cand['url']).suffix or '.jpg'}"
                    if commons.download(cand["url"], dest):
                        used_urls.add(cand["url"])
                        asset = VisualAsset(i, "photo", str(dest), "wikimedia_commons" if "wikimedia" in cand["url"] else "gongu",
                                            cand["license"], cand["credit"], page_url=cand["page_url"])
                        break
                if asset:
                    break
            # 2) 자료가 없으면 AI B롤 생성
            if asset is None:
                prompt = build_broll_prompt(sec, script.topic)
                video = runway.generate(prompt, assets_dir / f"{i:02d}_broll.mp4")
                if video:
                    asset = VisualAsset(i, "broll", str(video), "runway", "AI generated (Runway)", "Runway Gen-3", prompt)

        if asset is None:
            prompt = build_broll_prompt(sec, script.topic)
            dest = make_placeholder(assets_dir / f"{i:02d}_placeholder.jpg", sec.heading, prompt,
                                    (settings.width, settings.height), sec.mood)
            asset = VisualAsset(i, "placeholder", str(dest), "offline", "generated", "auto-documentary", prompt)
        log.info("섹션 %d 시각 자료: %s (%s, %s)", i, asset.kind, asset.source, asset.license)
        assets.append(asset)
    return assets
