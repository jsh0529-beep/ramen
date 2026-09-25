#!/usr/bin/env bash
# Google Fonts에서 Noto Serif KR / Noto Sans KR (TTF)을 받아 fonts/ 에 저장
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p fonts && cd fonts
: > fonts.css
for fam in "Noto+Serif+KR:wght@400;700;900" "Noto+Sans+KR:wght@300;400;700"; do
  curl -s -A "Mozilla/4.0" "https://fonts.googleapis.com/css2?family=$fam" >> fonts.css
done
python3 - <<'PY'
import re, subprocess
css = open('fonts.css').read()
for fam, w, url in re.findall(r"font-family: '([^']+)';\s*font-style: normal;\s*font-weight: (\d+);\s*src: url\(([^)]+)\)", css):
    fn = fam.replace(' ', '') + '-' + w + '.ttf'
    subprocess.run(['curl', '-s', '-o', fn, url], check=True)
    css = css.replace(url, fn)
open('fonts.css', 'w').write(css)
PY
