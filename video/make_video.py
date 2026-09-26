"""매일신문 기사 'AI 안경으로 성관계 몰카·시험 부정행위…규제는 뒷북'(2026-09-26)을
1080x1920 세로형 모션그래픽 영상(음성 없음)으로 만든다.

사용법: pip install pillow imageio-ffmpeg && python3 video/make_video.py
결과물: video/ai-glasses-news.mp4, video/thumbnail.png
"""
import math
import os
import subprocess
from functools import lru_cache

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ai-glasses-news.mp4")
W, H = 1080, 1920
FPS = 30
FADE = 0.5

BG_TOP = (14, 17, 28)
BG_BOTTOM = (38, 16, 30)
ACCENT = (255, 94, 77)
BLUE = (110, 140, 255)
TEXT = (245, 245, 250)
MUTED = (160, 165, 185)


@lru_cache(None)
def font(weight, size):
    name = {"r": "NanumGothic.ttf", "b": "NanumGothicBold.ttf", "x": "NanumGothicExtraBold.ttf"}[weight]
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back(x):
    """살짝 튀어나왔다 돌아오는 이징."""
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def appear(t, start, dur=0.5):
    return ease((t - start) / dur)


def rgba(c, a):
    return (*c[:3], int(255 * clamp(a)))


def make_bg():
    mask = Image.linear_gradient("L").resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), BG_BOTTOM), Image.new("RGB", (W, H), BG_TOP), mask)


BG = make_bg()


def text(d, xy, s, fnt, color, p=1.0, dy=40, dx=0, anchor="la"):
    """p(0~1)에 따라 페이드 + 슬라이드인."""
    if p <= 0:
        return
    x, y = xy
    d.text((x + dx * (1 - p), y + dy * (1 - p)), s, font=font(*fnt), fill=rgba(color, p), anchor=anchor)


def lines(d, x, y, rows, fnt, color, t, start, step=0.15, gap=1.3):
    for i, s in enumerate(rows):
        text(d, (x, y), s, fnt, color, appear(t, start + i * step))
        y += int(fnt[1] * gap)
    return y


def frame_base(T, total):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    # 천천히 떠다니는 장식 원
    ox = 60 * math.sin(T * 0.4)
    oy = 40 * math.cos(T * 0.3)
    d.ellipse((600 + ox, -280 + oy, 1400 + ox, 520 + oy), fill=(255, 94, 77, 24))
    d.ellipse((-320 - ox, 1480 - oy, 420 - ox, 2220 - oy), fill=(110, 140, 255, 20))
    # 헤더
    d.rectangle((80, 150, 92, 200), fill=ACCENT)
    d.text((112, 150), "이슈 브리핑", font=font("x", 40), fill=TEXT)
    d.text((112, 206), "매일신문 · 2026.09.26", font=font("r", 30), fill=MUTED)
    # 전체 진행 바
    d.rounded_rectangle((80, 1792, W - 80, 1800), 4, fill=(255, 255, 255, 40))
    d.rounded_rectangle((80, 1792, 80 + (W - 160) * clamp(T / total), 1800), 4, fill=ACCENT)
    return img, d


def glasses(d, cx, cy, s, a, t, rec=True):
    """스마트안경 아이콘. s=배율, a=투명도."""
    col = rgba(TEXT, a)
    lw = max(2, int(10 * s))
    lw_ = int(150 * s)
    lh = int(105 * s)
    gap = int(40 * s)
    lx0 = cx - gap // 2 - lw_
    rx0 = cx + gap // 2
    d.rounded_rectangle((lx0, cy - lh // 2, lx0 + lw_, cy + lh // 2), int(34 * s), outline=col, width=lw)
    d.rounded_rectangle((rx0, cy - lh // 2, rx0 + lw_, cy + lh // 2), int(34 * s), outline=col, width=lw)
    # 렌즈 반사광
    d.line((lx0 + 30 * s, cy - 20 * s, lx0 + 60 * s, cy - 35 * s), fill=rgba(TEXT, a * 0.5), width=max(2, int(6 * s)))
    d.line((rx0 + 30 * s, cy - 20 * s, rx0 + 60 * s, cy - 35 * s), fill=rgba(TEXT, a * 0.5), width=max(2, int(6 * s)))
    # 브릿지, 다리
    d.arc((cx - gap, cy - 40 * s, cx + gap, cy + 10 * s), 200, 340, fill=col, width=lw)
    d.line((lx0, cy - lh // 2 + 14 * s, lx0 - 70 * s, cy - lh // 2 + 4 * s), fill=col, width=lw)
    d.line((rx0 + lw_, cy - lh // 2 + 14 * s, rx0 + lw_ + 70 * s, cy - lh // 2 + 4 * s), fill=col, width=lw)
    # 카메라 모듈
    cam = (lx0 + 6 * s, cy - lh // 2 - 26 * s)
    d.ellipse((cam[0] - 14 * s, cam[1] - 14 * s, cam[0] + 14 * s, cam[1] + 14 * s), fill=rgba((40, 44, 60), a), outline=col, width=max(1, int(4 * s)))
    if rec and int(t * 2) % 2 == 0:
        r = 9 * s
        d.ellipse((cam[0] + 30 * s - r, cam[1] - r, cam[0] + 30 * s + r, cam[1] + r), fill=rgba(ACCENT, a))
        # 촬영 파동
        for k in range(3):
            ph = (t * 1.2 + k / 3) % 1
            rr = 20 * s + ph * 70 * s
            d.ellipse((cam[0] - rr, cam[1] - rr, cam[0] + rr, cam[1] + rr), outline=rgba(ACCENT, a * (1 - ph) * 0.8), width=max(1, int(3 * s)))


def rec_badge(d, x, y, t, a=1.0):
    if int(t * 2) % 2 == 0:
        d.ellipse((x, y + 6, x + 30, y + 36), fill=rgba(ACCENT, a))
    d.text((x + 44, y), "REC", font=font("x", 38), fill=rgba(TEXT, a))
    sec = int(t)
    fr = int((t - sec) * FPS)
    d.text((x + 150, y + 4), f"00:00:{sec:02d}:{fr:02d}", font=font("r", 32), fill=rgba(MUTED, a))


def viewfinder(d, box, a, L=70, w=8):
    x0, y0, x1, y1 = box
    c = rgba(TEXT, a * 0.8)
    for (x, y, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.line((x, y, x + sx * L, y), fill=c, width=w)
        d.line((x, y, x, y + sy * L), fill=c, width=w)


def card(d, y, t, start, tag, body, icon_fn=None):
    """오른쪽에서 밀려 들어오는 카드. 끝 y 반환."""
    p = appear(t, start, 0.6)
    if p <= 0:
        return y + 40 + 72 + len(body) * 56 + 40 + 40
    dx = int(120 * (1 - p))
    h = 40 + 72 + len(body) * 56 + 40
    d.rounded_rectangle((80 + dx, y, W - 80 + dx, y + h), 28, fill=(255, 255, 255, int(20 * p)))
    d.rounded_rectangle((80 + dx, y, 92 + dx, y + h), 6, fill=rgba(ACCENT, p))
    tx = 130 + dx
    if icon_fn:
        icon_fn(d, 160 + dx, y + 70, p, t)
        tx = 230 + dx
    d.text((tx, y + 40), tag, font=font("x", 50), fill=rgba(ACCENT, p))
    for i, s in enumerate(body):
        d.text((tx, y + 40 + 72 + i * 56), s, font=font("r", 40), fill=rgba(TEXT, p))
    return y + h + 40


# ---- 아이콘 ----
def ic_paper(d, cx, cy, a, t):
    d.rounded_rectangle((cx - 34, cy - 44, cx + 34, cy + 44), 8, outline=rgba(TEXT, a), width=5)
    for k in range(3):
        d.line((cx - 20, cy - 22 + k * 20, cx + 20, cy - 22 + k * 20), fill=rgba(MUTED, a), width=4)
    d.line((cx + 6, cy + 18, cx + 44, cy + 56), fill=rgba(ACCENT, a), width=8)
    d.line((cx + 44, cy + 18, cx + 6, cy + 56), fill=rgba(ACCENT, a), width=8)


def ic_glasses(d, cx, cy, a, t):
    glasses(d, cx, cy + 6, 0.22, a, t)


def ic_gavel(d, cx, cy, a, t):
    ang = math.radians(-35 + 12 * math.sin(t * 6))
    d.line((cx, cy, cx - 50 * math.sin(ang) + 10, cy + 50 * math.cos(ang)), fill=rgba(TEXT, a), width=8)
    d.polygon([(cx - 30 * math.cos(ang) - 10 * math.sin(ang), cy - 30 * math.sin(ang) + 10 * math.cos(ang)),
               (cx + 30 * math.cos(ang) - 10 * math.sin(ang), cy + 30 * math.sin(ang) + 10 * math.cos(ang)),
               (cx + 30 * math.cos(ang) + 14 * math.sin(ang), cy + 30 * math.sin(ang) - 14 * math.cos(ang)),
               (cx - 30 * math.cos(ang) + 14 * math.sin(ang), cy - 30 * math.sin(ang) - 14 * math.cos(ang))],
              fill=rgba(ACCENT, a))
    d.rectangle((cx - 40, cy + 44, cx + 20, cy + 54), fill=rgba(MUTED, a))


def ic_led(d, cx, cy, a, t):
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=rgba(ACCENT, a * (0.5 + 0.5 * math.sin(t * 6))))
    d.rounded_rectangle((cx - 44, cy - 16, cx + 44, cy + 16), 6, fill=rgba((230, 200, 120), a))  # 가림 스티커
    d.line((cx - 44, cy - 16, cx + 44, cy + 16), fill=rgba((180, 150, 80), a), width=3)


def ic_block(d, cx, cy, a, t):
    d.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), outline=rgba(ACCENT, a), width=8)
    d.line((cx - 28, cy + 28, cx + 28, cy - 28), fill=rgba(ACCENT, a), width=8)


def ic_badge(label):
    def f(d, cx, cy, a, t):
        d.ellipse((cx - 44, cy - 44, cx + 44, cy + 44), fill=rgba(ACCENT, a * 0.25), outline=rgba(ACCENT, a), width=4)
        d.text((cx, cy), label, font=font("x", 30), fill=rgba(TEXT, a), anchor="mm")
    return f


# ---- 장면 ----
def s_title(d, t, dur):
    p = back((t - 0.1) / 0.8)
    glasses(d, W // 2, 600, 1.3 * max(p, 0.01), clamp(p), t)
    text(d, (80, 840), "AI 안경", ("x", 150), ACCENT, appear(t, 0.5))
    y = lines(d, 80, 1040, ["성관계 몰카·", "시험 부정행위…"], ("x", 96), TEXT, t, 0.8, 0.2)
    text(d, (80, y + 30), "규제는 뒷북", ("x", 96), TEXT, appear(t, 1.3))
    w = 360 * ease((t - 1.6) / 0.6)
    if w > 0:
        d.rectangle((80, y + 170, 80 + w, y + 180), fill=ACCENT)
    # 도장
    sp = back((t - 2.3) / 0.4)
    if sp > 0:
        cx, cy = 820, y + 90
        r = 120 * (2 - sp) if sp < 1 else 120
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(ACCENT, clamp(sp)), width=8)
        d.text((cx, cy), "뒷북", font=font("x", 64), fill=rgba(ACCENT, clamp(sp)), anchor="mm")
    lines(d, 80, y + 250, ["카메라 달린 스마트안경 'AI 글라스'가", "불법 촬영·부정행위에 악용되자", "정부가 뒤늦게 규제에 나섰다"],
          ("r", 44), MUTED, t, 2.6, 0.15, 1.5)


def s_market(d, t, dur):
    y = lines(d, 80, 360, ["AI 글라스,", "폭발적 성장"], ("x", 92), TEXT, t, 0.1, 0.15, 1.25)
    text(d, (80, y + 20), "전 세계 출하량", ("r", 42), MUTED, appear(t, 0.4))
    bars = [("지난해", 870), ("올해(전망)", 1500), ("2030년(전망)", 3500)]
    top = y + 130
    max_len = W - 160
    for i, (label, v) in enumerate(bars):
        st = 0.6 + i * 0.5
        by = top + i * 240
        text(d, (80, by), label, ("b", 40), MUTED, appear(t, st))
        g = ease((t - st) / 1.2)
        bw = int(max_len * v / 3500 * g)
        if bw > 8:
            d.rounded_rectangle((80, by + 60, 80 + bw, by + 150), 16, fill=rgba(ACCENT, 1 - i * 0.2))
        if g > 0:
            txt = f"{int(v * g):,}만 대"
            f = font("x", 52)
            tw = d.textlength(txt, font=f)
            tx = 80 + bw + 24 if 80 + bw + 24 + tw < W - 60 else 80 + bw - tw - 24
            d.text((tx, by + 78), txt, font=f, fill=rgba(TEXT, g))
    # +322% 팝업
    sp = back((t - 2.6) / 0.5)
    if sp > 0:
        cy = top + 850
        d.rounded_rectangle((80, cy, W - 80, cy + 170), 30, fill=(255, 94, 77, int(40 * clamp(sp))))
        d.text((120, cy + 30), "지난해 전년 대비", font=font("b", 40), fill=rgba(MUTED, clamp(sp)))
        f = font("x", int(80 * max(sp, 0.1)))
        d.text((W - 120, cy + 120), f"+{int(322 * ease((t - 2.6) / 1.0))}%", font=f, fill=rgba(ACCENT, clamp(sp)), anchor="rs")
        # 상승 화살표
        ax = 560
        d.polygon([(ax, cy + 130), (ax + 40, cy + 70), (ax + 80, cy + 130)], fill=rgba(ACCENT, clamp(sp)))


def s_exam(d, t, dur):
    y = lines(d, 80, 360, ["시험장이", "뚫렸다"], ("x", 96), TEXT, t, 0.1, 0.15, 1.25)
    # 시험지 위 스캔 라인
    sx0, sy0, sx1, sy1 = 700, 330, 960, 640
    a = appear(t, 0.3)
    if a > 0:
        d.rounded_rectangle((sx0, sy0, sx1, sy1), 14, fill=(255, 255, 255, int(28 * a)), outline=rgba(TEXT, a * 0.6), width=4)
        for k in range(7):
            d.line((sx0 + 30, sy0 + 50 + k * 36, sx1 - 30 - (k % 3) * 30, sy0 + 50 + k * 36), fill=rgba(MUTED, a * 0.6), width=6)
        scan = sy0 + 20 + ((t * 0.6) % 1) * (sy1 - sy0 - 40)
        d.rectangle((sx0 + 8, scan - 3, sx1 - 8, scan + 3), fill=rgba(ACCENT, a))
        d.rectangle((sx0 + 8, scan - 30, sx1 - 8, scan), fill=rgba(ACCENT, a * 0.12))
    y += 80
    y = card(d, y, t, 0.8, "토익", ["5월 2명, 6월 1명 적발", "시험지 촬영 후 외부와 통신"], ic_paper)
    y = card(d, y, t, 1.4, "텝스", ["4월, 생성형 AI 스마트안경", "착용한 20대 수험생 적발"], ic_glasses)
    card(d, y, t, 2.0, "국가기술자격시험", ["광주 소방설비기사 시험 40대", "→ AI 안경 부정행위 첫 기소"], ic_gavel)


def s_privacy(d, t, dur):
    a = appear(t, 0.0, 0.4)
    viewfinder(d, (60, 290, W - 60, 1740), a)
    rec_badge(d, 100, 320, t, a)
    y = lines(d, 80, 440, ["몰래 찍는 눈"], ("x", 96), TEXT, t, 0.2)
    y += 60
    y = card(d, y, t, 0.7, "성관계 몰카", ["7월, 동의 없이 AI 글라스로", "성관계 장면 촬영한 남성 입건"], ic_glasses)
    y = card(d, y, t, 1.3, "표시등 무력화", ["촬영 알림 LED를 스티커로", "가리거나 개조하는 법 확산"], ic_led)
    card(d, y, t, 1.9, "제조사 조치", ["메타, 표시등 훼손된 수천 대", "카메라 기능 영구 비활성화"], ic_block)


def s_policy(d, t, dur):
    y = lines(d, 80, 360, ["뒤늦은 대책"], ("x", 96), TEXT, t, 0.1)
    # 달려오는 시계 아이콘 (뒷북)
    a = appear(t, 0.3)
    if a > 0:
        cx, cy, r = 880, 420, 80
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(ACCENT, a), width=8)
        ang = t * 4
        d.line((cx, cy, cx + 55 * math.sin(ang), cy - 55 * math.cos(ang)), fill=rgba(TEXT, a), width=8)
        d.line((cx, cy, cx + 35 * math.sin(ang / 12), cy - 35 * math.cos(ang / 12)), fill=rgba(TEXT, a), width=10)
    y += 120
    y = card(d, y, t, 0.6, "고용노동부", ["시험장 소지·사용 시 부정행위", "국가기술자격법 규칙 개정 추진"], ic_badge("노동"))
    y = card(d, y, t, 1.2, "교육부", ["시험장 반입 금지 물품 지정", "수능 부정 시 2년 응시 제한 검토"], ic_badge("교육"))
    card(d, y, t, 1.8, "과기정통부", ["AI 글라스 안전 기준 마련", "촬영 표시등 강화 등 지원"], ic_badge("과기"))


def s_end(d, t, dur):
    p = back((t - 0.1) / 0.7)
    glasses(d, W // 2, 560, 1.1 * max(p, 0.01), clamp(p), t, rec=False)
    sp = ease((t - 0.8) / 0.5)
    if sp > 0:
        cx, cy, r = W // 2, 560, 250
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(ACCENT, sp), width=16)
        e = 250 * 0.707
        d.line((cx - e, cy + e, cx - e + 2 * e * sp, cy + e - 2 * e * sp), fill=rgba(ACCENT, sp), width=16)
    y = lines(d, 80, 920, ["기술은 이미", "일상에 들어왔다"], ("x", 92), TEXT, t, 1.0, 0.2)
    text(d, (80, y + 30), "규제는 한발 늦었다", ("x", 92), ACCENT, appear(t, 1.6))
    lines(d, 80, y + 200, ["편리함과 프라이버시 사이,", "실효성 있는 안전장치가 필요하다"], ("r", 46), MUTED, t, 2.2, 0.2, 1.5)
    text(d, (80, 1690), "출처: 매일신문(2026.09.26) 외 관련 보도 종합", ("r", 30), MUTED, appear(t, 2.6))


SCENES = [(s_title, 5.0), (s_market, 6.5), (s_exam, 7.0), (s_privacy, 7.0), (s_policy, 7.0), (s_end, 5.5)]


def main():
    starts, T = [], 0.0
    for _, dur in SCENES:
        starts.append(T)
        T += dur - FADE
    total = T + FADE
    nframes = int(total * FPS)

    def render(i, T):
        fn, dur = SCENES[i]
        img, d = frame_base(T, total)
        fn(d, T - starts[i], dur)
        return img

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.Popen(
        [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
        stdin=subprocess.PIPE)
    for f in range(nframes):
        T = f / FPS
        active = [i for i, (_, dur) in enumerate(SCENES) if starts[i] <= T < starts[i] + dur]
        img = render(active[0], T)
        if len(active) > 1:
            img = Image.blend(img, render(active[1], T), clamp((T - starts[active[1]]) / FADE))
        if f == int((starts[0] + 3.2) * FPS):
            img.save(os.path.join(HERE, "thumbnail.png"))
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"저장: {OUT} ({total:.1f}초, {nframes}프레임)")


if __name__ == "__main__":
    main()
