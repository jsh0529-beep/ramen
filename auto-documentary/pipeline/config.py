"""환경 변수(.env) 기반 설정."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass
class Settings:
    # 1단계
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    khs_api_base: str = "https://www.khs.go.kr/cha"
    # 2단계
    gongu_api_key: str = ""
    gongu_api_base: str = ""
    runway_api_key: str = ""
    runway_api_base: str = "https://api.dev.runwayml.com/v1"
    # 3단계
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model: str = "eleven_multilingual_v2"
    epidemic_api_key: str = ""
    epidemic_api_base: str = ""
    # 4단계
    width: int = 1920
    height: int = 1080
    fps: int = 24
    target_minutes: float = 5.0
    subtitle_font: str = ""
    # 5단계
    youtube_client_secret: str = "client_secret.json"
    youtube_privacy: str = "private"
    # 실행
    offline: bool = False
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output")
    http_timeout: int = 20

    @classmethod
    def from_env(cls, offline: bool = False, **overrides) -> "Settings":
        if load_dotenv:
            load_dotenv(PROJECT_ROOT / ".env")
        s = cls(
            gemini_api_key=_env("GEMINI_API_KEY"),
            gemini_model=_env("GEMINI_MODEL", "gemini-1.5-pro"),
            khs_api_base=_env("KHS_API_BASE", "https://www.khs.go.kr/cha"),
            gongu_api_key=_env("GONGU_API_KEY"),
            gongu_api_base=_env("GONGU_API_BASE"),
            runway_api_key=_env("RUNWAY_API_KEY"),
            runway_api_base=_env("RUNWAY_API_BASE", "https://api.dev.runwayml.com/v1"),
            elevenlabs_api_key=_env("ELEVENLABS_API_KEY"),
            elevenlabs_voice_id=_env("ELEVENLABS_VOICE_ID"),
            elevenlabs_model=_env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            epidemic_api_key=_env("EPIDEMIC_SOUND_API_KEY"),
            epidemic_api_base=_env("EPIDEMIC_SOUND_API_BASE"),
            width=int(_env("VIDEO_WIDTH", "1920")),
            height=int(_env("VIDEO_HEIGHT", "1080")),
            fps=int(_env("VIDEO_FPS", "24")),
            target_minutes=float(_env("TARGET_MINUTES", "5")),
            subtitle_font=_env("SUBTITLE_FONT"),
            youtube_client_secret=_env("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json"),
            youtube_privacy=_env("YOUTUBE_PRIVACY", "private"),
            offline=offline,
        )
        for k, v in overrides.items():
            if v is not None:
                setattr(s, k, v)
        return s

    # 각 단계가 "실제 API를 쓸 수 있는가"를 판단하는 도우미
    @property
    def can_use_gemini(self) -> bool:
        return not self.offline and bool(self.gemini_api_key)

    @property
    def can_use_elevenlabs(self) -> bool:
        return not self.offline and bool(self.elevenlabs_api_key and self.elevenlabs_voice_id)

    @property
    def can_use_runway(self) -> bool:
        return not self.offline and bool(self.runway_api_key)

    @property
    def can_use_network(self) -> bool:
        return not self.offline
