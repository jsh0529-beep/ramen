"""매일신문 기사 'TK는 왜 광주냐 했는데, 반도체 품은 전남광주, 실은 토허제에 한숨?'을
1080x1920 세로형 모션그래픽 영상(내레이션 없음, 효과음·배경음 포함)으로 만든다.

사용법: pip install pillow numpy imageio-ffmpeg && python3 video/gwangju_land.py
결과물: video/gwangju-land-news.mp4, video/gwangju-land-news-thumbnail.png
"""
import math
import os

import audio
import make_video as mv
from make_video import (ACCENT, MUTED, TEXT, W, appear, back, card, clamp, ease, font,
                        ic_badge, lines, rgba, text)

mv.HEADER = "매일신문"
OUT = os.path.join(mv.HERE, "gwangju-land-news.mp4")
GREY = (120, 125, 145)


# ---- 아이콘 ----
def chip(d, cx, cy, s, a, t):
    """반도체 칩. s=배율."""
    if a <= 0:
        return
    half = 150 * s
    glow = 0.5 + 0.5 * math.sin(t * 3)
    for k in range(3):
        g = half + (20 + k * 22) * s
        d.rounded_rectangle((cx - g, cy - g, cx + g, cy + g), int(40 * s), outline=rgba(ACCENT, a * 0.15 * glow), width=max(1, int(4 * s)))
    # 핀
    for i in range(6):
        off = -half + (i + 0.5) * (2 * half / 6)
        L, pw = 40 * s, 10 * s
        for (x0, y0, x1, y1) in [(cx + off - pw / 2, cy - half - L, cx + off + pw / 2, cy - half),
                                 (cx + off - pw / 2, cy + half, cx + off + pw / 2, cy + half + L),
                                 (cx - half - L, cy + off - pw / 2, cx - half, cy + off + pw / 2),
                                 (cx + half, cy + off - pw / 2, cx + half + L, cy + off + pw / 2)]:
            d.rectangle((x0, y0, x1, y1), fill=rgba(MUTED, a))
    d.rounded_rectangle((cx - half, cy - half, cx + half, cy + half), int(26 * s), fill=rgba((40, 44, 64), a), outline=rgba(TEXT, a), width=max(2, int(8 * s)))
    inner = half * 0.55
    d.rounded_rectangle((cx - inner, cy - inner, cx + inner, cy + inner), int(12 * s), outline=rgba(ACCENT, a), width=max(2, int(6 * s)))
    # 회로선에 흐르는 빛
    for k in range(4):
        ph = (t * 0.8 + k / 4) % 1
        ang = k * math.pi / 2
        r0, r1 = inner, half
        r = r0 + (r1 - r0) * ph
        px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
        d.ellipse((px - 7 * s, py - 7 * s, px + 7 * s, py + 7 * s), fill=rgba(ACCENT, a * (1 - ph)))


def lock(d, cx, cy, s, a, open_=0.0):
    if a <= 0:
        return
    bw, bh = 120 * s, 100 * s
    lift = 40 * s * open_
    d.arc((cx - 70 * s, cy - bh / 2 - 90 * s - lift, cx + 70 * s, cy - bh / 2 + 50 * s - lift), 180, 360,
          fill=rgba(TEXT, a), width=max(2, int(18 * s)))
    d.line((cx - 61 * s, cy - bh / 2 - 20 * s - lift, cx - 61 * s, cy - bh / 2 + 4 * s), fill=rgba(TEXT, a), width=max(2, int(18 * s)))
    d.line((cx + 61 * s, cy - bh / 2 - 20 * s - lift, cx + 61 * s, cy - bh / 2 + 4 * s - lift * 0), fill=rgba(TEXT, a), width=max(2, int(18 * s)))
    d.rounded_rectangle((cx - bw, cy - bh / 2, cx + bw, cy + bh), int(22 * s), fill=rgba(ACCENT, a))
    d.ellipse((cx - 16 * s, cy + 10 * s, cx + 16 * s, cy + 42 * s), fill=rgba((40, 20, 30), a))
    d.rectangle((cx - 6 * s, cy + 30 * s, cx + 6 * s, cy + 70 * s), fill=rgba((40, 20, 30), a))


def pin(d, cx, cy, s, color, a, label=None):
    if a <= 0:
        return
    r = 60 * s
    d.polygon([(cx - r * 0.85, cy - r * 0.5), (cx + r * 0.85, cy - r * 0.5), (cx, cy + r * 1.3)], fill=rgba(color, a))
    d.ellipse((cx - r, cy - r * 2, cx + r, cy), fill=rgba(color, a))
    d.ellipse((cx - r * 0.4, cy - r * 1.4, cx + r * 0.4, cy - r * 0.6), fill=rgba((20, 22, 34), a))
    if label:
        d.text((cx, cy + r * 1.3 + 30), label, font=font("x", 48), fill=rgba(TEXT, a), anchor="mt")


def arrow(d, x0, y0, x1, y1, p, color, w=10):
    if p <= 0:
        return
    xe, ye = x0 + (x1 - x0) * p, y0 + (y1 - y0) * p
    # 점선
    n = 14
    for i in range(n):
        a0, a1 = i / n, (i + 0.55) / n
        if a0 > p:
            break
        a1 = min(a1, p)
        d.line((x0 + (x1 - x0) * a0, y0 + (y1 - y0) * a0, x0 + (x1 - x0) * a1, y0 + (y1 - y0) * a1), fill=rgba(color, 1), width=w)
    ang = math.atan2(y1 - y0, x1 - x0)
    L = 34
    d.polygon([(xe, ye), (xe - L * math.cos(ang - 0.5), ye - L * math.sin(ang - 0.5)),
               (xe - L * math.cos(ang + 0.5), ye - L * math.sin(ang + 0.5))], fill=rgba(color, 1))


def bubble(d, cx, cy, s, a, label):
    if a <= 0:
        return
    w, h = 120 * s, 90 * s
    d.rounded_rectangle((cx - w, cy - h, cx + w, cy + h), int(40 * s), fill=rgba(TEXT, a))
    d.polygon([(cx - 20 * s, cy + h - 4), (cx + 20 * s, cy + h - 4), (cx, cy + h + 36 * s)], fill=rgba(TEXT, a))
    d.text((cx, cy), label, font=font("x", max(1, int(60 * s))), fill=rgba((30, 30, 45), a), anchor="mm")


def ic_house(d, cx, cy, a, t):
    d.polygon([(cx - 44, cy), (cx, cy - 40), (cx + 44, cy)], fill=rgba(TEXT, a))
    d.rectangle((cx - 32, cy, cx + 32, cy + 40), outline=rgba(TEXT, a), width=5)
    d.rectangle((cx - 9, cy + 16, cx + 9, cy + 40), fill=rgba(ACCENT, a))


def ic_down(d, cx, cy, a, t):
    bob = 6 * math.sin(t * 5)
    d.rectangle((cx - 12, cy - 40 + bob, cx + 12, cy + 6 + bob), fill=rgba(ACCENT, a))
    d.polygon([(cx - 36, cy + 4 + bob), (cx + 36, cy + 4 + bob), (cx, cy + 46 + bob)], fill=rgba(ACCENT, a))


def ic_lock(d, cx, cy, a, t):
    lock(d, cx, cy + 4, 0.3, a)


def ic_calendar(d, cx, cy, a, t):
    d.rounded_rectangle((cx - 40, cy - 34, cx + 40, cy + 40), 8, outline=rgba(TEXT, a), width=5)
    d.rectangle((cx - 40, cy - 34, cx + 40, cy - 14), fill=rgba(ACCENT, a))
    for i in range(3):
        for j in range(2):
            d.rectangle((cx - 26 + i * 20, cy - 2 + j * 18, cx - 16 + i * 20, cy + 8 + j * 18), fill=rgba(MUTED, a))


def ic_ruler(d, cx, cy, a, t):
    d.rounded_rectangle((cx - 44, cy - 16, cx + 44, cy + 16), 4, outline=rgba(TEXT, a), width=5)
    for i in range(7):
        x = cx - 34 + i * 11
        d.line((x, cy - 16, x, cy - 16 + (14 if i % 2 == 0 else 8)), fill=rgba(TEXT, a), width=3)


def ic_tweezers(d, cx, cy, a, t, s=1.0):
    """핀셋: 끝이 오므라들었다 벌어짐."""
    g = (10 + 10 * math.sin(t * 4)) * s
    w = max(3, int(12 * s))
    d.line((cx - 40 * s, cy - 60 * s, cx - 6 * s - g / 2, cy + 60 * s), fill=rgba(TEXT, a), width=w)
    d.line((cx + 40 * s, cy - 60 * s, cx + 6 * s + g / 2, cy + 60 * s), fill=rgba(TEXT, a), width=w)
    d.line((cx - 40 * s, cy - 60 * s, cx + 40 * s, cy - 60 * s), fill=rgba(TEXT, a), width=w)
    d.ellipse((cx - 10 * s, cy + 60 * s, cx + 10 * s, cy + 80 * s), fill=rgba(ACCENT, a))


# ---- 장면 ----
def s_title(d, t, dur):
    p = back((t - 0.1) / 0.8)
    chip(d, W // 2, 560, 1.15 * max(p, 0.01), clamp(p), t)
    # 칩 위로 자물쇠가 떨어짐
    lp = clamp((t - 2.0) / 0.35)
    if lp > 0:
        lock(d, W // 2, 380 + 180 * ease(lp), 0.9, lp)
    text(d, (80, 870), "TK는 '왜 광주냐' 했는데…", ("b", 50), MUTED, appear(t, 0.5))
    y = lines(d, 80, 960, ["반도체 품은"], ("x", 100), TEXT, t, 0.8)
    text(d, (80, y), "전남광주,", ("x", 100), ACCENT, appear(t, 1.0))
    y = lines(d, 80, y + 130, ["실은 토허제에"], ("x", 100), TEXT, t, 1.3)
    sp = back((t - 1.7) / 0.45)
    if sp > 0:
        f = font("x", int(130 * max(sp, 0.1)))
        d.text((80, y + 10), "한숨?", font=f, fill=rgba(ACCENT, clamp(sp)))
        # 한숨 입김
        for k in range(3):
            ph = ((t - 1.9) * 0.7 + k / 3) % 1
            if t > 1.9:
                x = 460 + ph * 180
                yy = y + 60 - ph * 60 + 10 * math.sin(ph * 8)
                r = 14 + ph * 26
                d.ellipse((x - r, yy - r, x + r, yy + r), fill=rgba(MUTED, (1 - ph) * 0.5))


def s_cluster(d, t, dur):
    y = lines(d, 80, 360, ["800조 반도체", "메가 클러스터"], ("x", 92), TEXT, t, 0.1, 0.15, 1.25)
    chip(d, 880, 440, 0.45 * max(appear(t, 0.2), 0.01), appear(t, 0.2), t)
    # 큰 카운터
    g = ease((t - 0.6) / 1.4)
    if g > 0:
        cy = y + 60
        d.rounded_rectangle((80, cy, W - 80, cy + 300), 36, fill=(255, 94, 77, int(34 * g)))
        d.text((120, cy + 40), "투자 규모", font=font("b", 42), fill=rgba(MUTED, g))
        d.text((W - 120, cy + 250), f"{int(800 * g)}조 원", font=font("x", 150), fill=rgba(ACCENT, g), anchor="rs")
    y += 420
    g2 = ease((t - 1.6) / 1.2)
    if g2 > 0:
        d.text((80, y), "광주 군공항 부지", font=font("b", 44), fill=rgba(MUTED, g2))
        d.text((W - 80, y + 120), f"{int(250 * g2)}만 평", font=font("x", 110), fill=rgba(TEXT, g2), anchor="rs")
        # 면적 채워지는 막대
        d.rounded_rectangle((80, y + 150, W - 80, y + 170), 10, fill=(255, 255, 255, 30))
        d.rounded_rectangle((80, y + 150, 80 + (W - 160) * g2, y + 170), 10, fill=rgba(ACCENT, g2))
    y += 240
    card(d, y, t, 2.6, "7월, 국가산단 후보지 지정", ["삼성전자·SK하이닉스", "반도체 팹 투자 수요 반영"], ic_badge("산단"))


PIN_TK = (290, 1020)
PIN_GJ = (790, 1200)


def s_tk(d, t, dur):
    lines(d, 80, 360, ["TK는", "'왜 광주냐'"], ("x", 100), TEXT, t, 0.1, 0.18, 1.25)
    p1 = back((t - 0.5) / 0.5)
    pin(d, *PIN_TK, max(p1, 0.01), GREY, clamp(p1), "대구·경북")
    p2 = back((t - 0.8) / 0.5)
    pin(d, *PIN_GJ, max(p2, 0.01), ACCENT, clamp(p2), "광주")
    arrow(d, PIN_TK[0] + 90, PIN_TK[1] - 60, PIN_GJ[0] - 90, PIN_GJ[1] - 90, ease((t - 1.2) / 0.8), ACCENT)
    # 반도체 칩이 광주로 이동
    cp = ease((t - 1.2) / 0.8)
    if cp > 0:
        x = PIN_TK[0] + 90 + (PIN_GJ[0] - PIN_TK[0] - 180) * cp
        yy = PIN_TK[1] - 60 + (PIN_GJ[1] - PIN_TK[1] - 30) * cp - 60
        chip(d, x, yy - 40, 0.18, 1 if cp < 1 else max(0, 1 - (t - 2.0) * 3), t)
    bp = back((t - 2.2) / 0.4)
    bubble(d, PIN_TK[0], PIN_TK[1] - 250, max(bp, 0.01), clamp(bp), "왜?")
    card(d, 1430, t, 2.8, "구미 등 TK의 불만", ["반도체 기업·전력·용수 인프라", "갖췄는데 유치 실패"], ic_badge("TK"))


def s_land(d, t, dur):
    lines(d, 80, 360, ["토허제로", "묶였다"], ("x", 100), TEXT, t, 0.1, 0.18, 1.25)
    # 지도 그리드
    x0, y0, x1, y1 = 80, 640, W - 80, 1160
    a = appear(t, 0.3)
    if a > 0:
        d.rounded_rectangle((x0, y0, x1, y1), 28, fill=(255, 255, 255, int(14 * a)))
        for i in range(1, 9):
            x = x0 + i * (x1 - x0) / 9
            d.line((x, y0 + 10, x, y1 - 10), fill=(255, 255, 255, int(22 * a)), width=2)
        for j in range(1, 6):
            y = y0 + j * (y1 - y0) / 6
            d.line((x0 + 10, y, x1 - 10, y), fill=(255, 255, 255, int(22 * a)), width=2)
        # 도로
        d.line((x0 + 40, y1 - 80, x1 - 60, y0 + 70), fill=(255, 255, 255, int(45 * a)), width=10)
        d.line((x0 + 120, y0 + 40, x0 + 300, y1 - 30), fill=(255, 255, 255, int(45 * a)), width=8)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    rp = ease((t - 0.8) / 1.2)
    if rp > 0:
        r = 230 * rp
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 94, 77, 50), outline=rgba(ACCENT, 1), width=6)
        # 퍼지는 파동
        ph = (t * 0.8) % 1
        rr = 230 + ph * 60
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=rgba(ACCENT, (1 - ph) * 0.6 * rp), width=3)
        d.text((cx + r * 0.72, cy - r * 0.72 - 10), "반경 10km", font=font("b", 34), fill=rgba(TEXT, rp), anchor="lb")
    lp = back((t - 1.9) / 0.4)
    lock(d, cx, cy - 10, 0.7 * max(lp, 0.01), clamp(lp))
    # 면적 카운터
    g = ease((t - 2.1) / 1.2)
    if g > 0:
        d.text((80, 1200), "지정 면적", font=font("b", 42), fill=rgba(MUTED, g))
        d.text((W - 80, 1310), f"{364.19 * g:,.2f}㎢", font=font("x", 110), fill=rgba(ACCENT, g), anchor="rs")
    rows = [("광주 5개 구 + 나주·장성·화순", ic_lock),
            ("2026.7.14 ~ 2028.7.13 (2년)", ic_calendar),
            ("주거 60㎡·상업·공업 150㎡ 초과 시 허가", ic_ruler)]
    for i, (s, ic) in enumerate(rows):
        p = appear(t, 3.0 + i * 0.35)
        if p <= 0:
            continue
        yy = 1380 + i * 110
        dx = 80 * (1 - p)
        ic(d, 130 + dx, yy + 30, p, t)
        d.text((200 + dx, yy + 8), s, font=font("b", 40), fill=rgba(TEXT, p))


def s_sigh(d, t, dur):
    lines(d, 80, 360, ["현장은", "한숨"], ("x", 100), TEXT, t, 0.1, 0.18, 1.25)
    # 떨어지는 그래프 화살표
    a = appear(t, 0.3)
    if a > 0:
        pts = [(560, 400), (660, 470), (740, 440), (840, 560), (960, 640)]
        g = ease((t - 0.4) / 1.0)
        n = len(pts) - 1
        upto = g * n
        for i in range(n):
            if upto <= i:
                break
            f = min(1, upto - i)
            (xa, ya), (xb, yb) = pts[i], pts[i + 1]
            d.line((xa, ya, xa + (xb - xa) * f, ya + (yb - ya) * f), fill=rgba(ACCENT, a), width=12)
        if g >= 1:
            (xa, ya), (xb, yb) = pts[-2], pts[-1]
            ang = math.atan2(yb - ya, xb - xa)
            d.polygon([(xb + 20 * math.cos(ang), yb + 20 * math.sin(ang)),
                       (xb - 30 * math.cos(ang - 0.6), yb - 30 * math.sin(ang - 0.6)),
                       (xb - 30 * math.cos(ang + 0.6), yb - 30 * math.sin(ang + 0.6))], fill=rgba(ACCENT, a))
    y = 780
    y = card(d, y, t, 1.2, "거래 급감", ["광주·나주·장성·화순", "주택·상가 거래 뚝"], ic_down)
    y = card(d, y, t, 1.8, "실수요자도 발 묶여", ["투기 막으려다", "실수요 거래까지 막혀 불만"], ic_house)
    card(d, y, t, 2.4, "정부 입장", ["투기성 거래만 제한", "실사용 목적이면 허가 가능"], ic_badge("정부"))


def s_pinset(d, t, dur):
    lines(d, 80, 360, ["'핀셋' 규제", "완화 요구"], ("x", 100), TEXT, t, 0.1, 0.18, 1.25)
    a = appear(t, 0.3)
    if a > 0:
        ic_tweezers(d, 880, 440, a, t, s=1.6)
    # 인용 박스
    q = appear(t, 0.8, 0.6)
    if q > 0:
        y0 = 700
        d.rounded_rectangle((80, y0 + 40 * (1 - q), W - 80, y0 + 520 + 40 * (1 - q)), 36, fill=(255, 255, 255, int(20 * q)))
        d.text((130, y0 + 60 + 40 * (1 - q)), "발언 요지", font=font("b", 40), fill=rgba(ACCENT, q))
        lines(d, 130, y0 + 190, ["반도체 호재가", "주민 발목을 잡지 않고", "지역 활성화로 이어져야"], ("x", 58), TEXT, t, 1.0, 0.25, 1.35)
        text(d, (130, y0 + 430), "정진욱 의원(민주당), 9월 25일", ("b", 38), MUTED, appear(t, 1.8))
    card(d, 1300, t, 2.4, "규제 완화 추진", ["산단 사업이 '종이 위 계획'에", "머물지 않도록 지역경제 활성화"], ic_badge("국회"))


def s_end(d, t, dur):
    p = back((t - 0.1) / 0.7)
    chip(d, W // 2, 560, 1.0 * max(p, 0.01), clamp(p), t)
    op = ease((t - 1.0) / 0.6)
    lock(d, W // 2, 560, 0.75 * max(p, 0.01), clamp(p) * (1 - 0.3 * op), open_=op)
    y = lines(d, 80, 920, ["800조 반도체,"], ("x", 92), TEXT, t, 0.8)
    text(d, (80, y + 10), "호재인가 족쇄인가", ("x", 92), ACCENT, appear(t, 1.3))
    lines(d, 80, y + 200, ["투기는 막고 실수요는 살리는", "정교한 규제가 필요하다"], ("r", 46), MUTED, t, 2.0, 0.2, 1.5)
    text(d, (80, 1690), "출처: 매일신문", ("r", 32), MUTED, appear(t, 2.5))


SCENES = [(s_title, 5.5), (s_cluster, 7.0), (s_tk, 7.0), (s_land, 8.0), (s_sigh, 7.0), (s_pinset, 7.0), (s_end, 5.5)]

# C단조 계열 (Cm - Ab - Eb - Bb)
PROGRESSION = ([[60, 63, 67], [56, 60, 63], [55, 58, 63], [58, 62, 65]], [36, 44, 39, 46])


def sound(starts, total, path):
    a = audio
    mx = a.Mixer(total)
    put = mx.put
    s0, s1, s2, s3, s4, s5, s6 = starts
    for s in starts[1:]:
        put(a.whoosh(), s - 0.35, 0.5, pan=0.3)

    # 1. 타이틀: 칩 팝 + 전자음, 제목 슉, 자물쇠 쿵, 한숨
    put(a.pop(), s0 + 0.2, 0.8)
    put(a.beep(1600, 0.06, 0.1), s0 + 0.45)
    put(a.beep(2000, 0.06, 0.1), s0 + 0.55)
    for k, at in enumerate([0.5, 0.8, 1.0, 1.3]):
        put(a.swish(), s0 + at, 0.6, pan=-0.3 + 0.2 * k)
    put(a.pop(), s0 + 1.75, 0.6)
    put(a.stamp(), s0 + 2.3, 1.0)
    put(a.knock(), s0 + 2.32, 0.5)
    put(a.whoosh(1.2), s0 + 2.0, 0.25, pan=0.4)  # 한숨

    # 2. 클러스터: 카운트 틱 + 상승음 + 차임
    put(a.rise(1.4), s1 + 0.6, 0.9)
    for q in range(14):
        put(a.tick(1700 + 40 * q), s1 + 0.6 + q * 0.1, 0.5)
    put(a.chime(), s1 + 2.0, 0.8)
    put(a.rise(1.2), s1 + 1.6, 0.6, pan=0.3)
    for q in range(12):
        put(a.tick(2000 + 30 * q), s1 + 1.6 + q * 0.1, 0.35)
    put(a.swish(0.35), s1 + 2.6, 0.9, pan=0.5)

    # 3. TK: 핀 팝, 칩 이동 휙, 물음표 부저
    put(a.pop(), s2 + 0.55, 0.7, pan=-0.5)
    put(a.pop(), s2 + 0.85, 0.7, pan=0.5)
    put(a.whoosh(0.8), s2 + 1.2, 0.6, pan=0.6)
    put(a.ding(1046.5), s2 + 2.0, 0.6, pan=0.5)
    put(a.buzzer(0.3), s2 + 2.25, 0.8, pan=-0.5)
    put(a.swish(0.35), s2 + 2.8, 0.9, pan=0.5)

    # 4. 토허제: 반경 확장음, 자물쇠 쿵, 면적 카운트, 목록 슉
    put(a.rise(1.2), s3 + 0.8, 0.8)
    put(a.stamp(), s3 + 1.95, 1.0)
    put(a.knock(), s3 + 2.0, 0.6)
    for q in range(12):
        put(a.tick(1900 + 30 * q), s3 + 2.1 + q * 0.1, 0.35)
    for k in range(3):
        put(a.swish(), s3 + 3.0 + 0.35 * k, 0.7, pan=0.4)
        put(a.pop(), s3 + 3.2 + 0.35 * k, 0.25)

    # 5. 한숨: 하강음 + 카드
    put(a._sweep(900, 200, 1.0) * a._decay(int(1.0 * a.SR), 0.5) * 0.12, s4 + 0.4, 1.0)
    for at in [1.2, 1.8, 2.4]:
        put(a.swish(0.35), s4 + at, 0.9, pan=0.5)
    put(a.buzzer(0.3), s4 + 1.4, 0.6)

    # 6. 핀셋: 인용 등장 + 카드
    put(a.swish(0.45), s5 + 0.8, 0.8)
    for k in range(3):
        put(a.swish(), s5 + 1.0 + 0.25 * k, 0.5)
    put(a.ding(1318.5), s5 + 1.8, 0.4)
    put(a.swish(0.35), s5 + 2.4, 0.9, pan=0.5)

    # 7. 마무리: 칩 팝, 자물쇠 풀림(찰칵), 여운
    put(a.pop(), s6 + 0.15, 0.7)
    put(a.shutter(), s6 + 1.0, 0.8)
    put(a.chime(), s6 + 1.3, 0.7)
    for at in [0.8, 1.3, 2.0, 2.2, 2.5]:
        put(a.swish(), s6 + at, 0.5)

    mx.write(path, a.music(total, drums_in=s0 + 2.3, drums_out=s6 + 1.0, bpm=96, progression=PROGRESSION))


if __name__ == "__main__":
    mv.render(SCENES, OUT, sound, thumb_at=4.0)
