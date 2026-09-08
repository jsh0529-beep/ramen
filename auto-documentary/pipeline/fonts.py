"""한글 폰트 탐색 (자막·플레이스홀더용)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Bold.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/unifont/unifont.otf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]


def find_korean_font(preferred: str = "") -> Optional[str]:
    for p in [preferred or os.environ.get("SUBTITLE_FONT", ""), *CANDIDATES]:
        if p and Path(p).exists():
            return p
    return None
