#!/usr/bin/env bash
# 쇼릴 렌더: 120fps 로 4구간 병렬 캡처 → 이어붙임 → 서브프레임 블렌딩(모션 블러)으로 30fps → 사운드 합치기
set -euo pipefail
cd "$(dirname "$0")/.."
FFMPEG=${FFMPEG:-ffmpeg}; FPS=120; TOTAL=$((30*FPS)); JOBS=${JOBS:-4}
mkdir -p frames/reel; : > frames/reel/list.txt
step=$(( (TOTAL + JOBS - 1) / JOBS ))
for ((j=0; j<JOBS; j++)); do
  SCENE=reel/scene.html FRAMES=$((j*step)):$(((j+1)*step)) CRF=12 FFMPEG=$FFMPEG node render.mjs frames/reel/s$j.mp4 $FPS > frames/reel/log$j.txt 2>&1 &
  echo "file 's$j.mp4'" >> frames/reel/list.txt
done
wait
$FFMPEG -y -loglevel error -f concat -safe 0 -i frames/reel/list.txt -c copy frames/reel_120.mp4
python3 reel/audio.py
# 3 서브프레임 평균(셔터 270°) → 30fps
$FFMPEG -y -loglevel error -i frames/reel_120.mp4 -i reel/soundtrack.wav \
  -vf "tmix=frames=3:weights='1 1 1',fps=30" -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -shortest -movflags +faststart reel/maeil_reel.mp4
echo done
