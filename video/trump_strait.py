"""매일신문 기사 '[속보] 호르무즈가 아니라 트럼프 해협?…트럼프가 올린 지도 한 장'을
1080x1920 세로형 프리미엄 영상으로 만든다. 블랙·플래티넘·샴페인 톤, 명조체, 시네마틱 지도 연출.

사용법: pip install pillow numpy imageio-ffmpeg && python3 video/trump_strait.py
결과물: video/trump-strait-news.mp4, video/trump-strait-news-thumbnail.png
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw

import audio
import make_video as mv
from make_video import W, H, appear, clamp, ease
from xi_visit import serif, tracked

OUT = os.path.join(mv.HERE, "trump-strait-news.mp4")
mv.FADE = 1.0

BLACK = (6, 6, 9)
SEA = (9, 12, 18)
LAND = (46, 44, 42)
PLAT = (228, 226, 220)
CHAMP = (214, 190, 150)
DIM = (130, 128, 122)
CRIMSON = (184, 48, 48)


def rgba(c, a=1.0):
    return (*c[:3], int(255 * clamp(a)))


# ---- 지도 데이터 (경도, 위도) — 단순화한 해안선 ----
IRAN = [(46, 34), (48.3, 30.1), (49.6, 30.0), (50.3, 29.3), (50.8, 28.9), (51.3, 28.0), (52.1, 27.8), (53.0, 27.1),
        (53.8, 26.7), (54.8, 26.5), (55.6, 26.9), (56.3, 27.2), (56.9, 26.9), (57.3, 26.2), (57.8, 25.6),
        (58.9, 25.5), (60.5, 25.3), (61.6, 25.1), (63, 25.2), (63, 34)]
ARABIA = [(46, 30.2), (47.9, 29.9), (48.1, 29.3), (48.6, 28.1), (49.6, 27.0), (50.2, 26.2), (50.6, 25.3),
          (50.8, 24.8), (51.0, 25.6), (51.3, 26.1), (51.6, 25.4), (51.6, 24.6), (52.0, 24.1), (53.5, 24.1),
          (54.4, 24.4), (55.3, 25.2), (55.9, 25.7), (56.1, 26.1), (56.35, 26.4), (56.45, 26.1), (56.35, 25.6),
          (56.4, 24.9), (56.9, 24.2), (57.8, 23.7), (58.6, 23.6), (59.3, 22.8), (59.8, 22.5), (60.5, 21.5),
          (63, 19), (46, 19)]
QESHM = [(55.3, 26.75), (55.7, 26.62), (56.2, 26.85), (56.3, 26.98), (55.9, 26.95), (55.5, 26.85)]
HORMUZ_IS = [(56.42, 27.06), (56.48, 27.02), (56.5, 27.08), (56.45, 27.11)]
LANE = [(50.5, 27.3), (52.5, 26.5), (54.5, 26.1), (55.9, 26.35), (56.45, 26.55), (56.9, 26.3), (57.4, 25.6), (58.5, 24.9), (60.5, 24.3)]


def proj(lon, lat, view):
    clon, clat, s, cy = view
    k = math.cos(math.radians(26))
    return W / 2 + (lon - clon) * s * k, cy - (lat - clat) * s


def view_at(p):
    """p: 0(넓게) → 1(해협으로 줌인)."""
    e = ease(p)
    clon = 54.5 + (56.4 - 54.5) * e
    clat = 26.5 + (26.3 - 26.5) * e
    s = 95 + (235 - 95) * e
    return clon, clat, s, 900


def lane_point(u, view):
    """항로 위 0~1 위치의 화면 좌표."""
    pts = [proj(lo, la, view) for lo, la in LANE]
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    L = sum(segs) * u
    for (a, b), sl in zip(zip(pts, pts[1:]), segs):
        if L <= sl:
            f = L / sl
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        L -= sl
    return pts[-1]


def draw_map(d, t, zoom, a=1.0, ships=True, label="hormuz", label_t=0.0, names=True):
    view = view_at(zoom)
    for poly in (IRAN, ARABIA, QESHM, HORMUZ_IS):
        pts = [proj(lo, la, view) for lo, la in poly]
        d.polygon(pts, fill=rgba(LAND, a))
        d.line(pts + [pts[0]], fill=rgba(CHAMP, 0.7 * a), width=3)
    # 위경도 격자
    for lon in range(46, 64, 2):
        x0, y0 = proj(lon, 19, view)
        x1, y1 = proj(lon, 34, view)
        d.line((x0, y0, x1, y1), fill=rgba(PLAT, 0.04 * a), width=1)
    for lat in range(20, 34, 2):
        x0, y0 = proj(46, lat, view)
        x1, y1 = proj(63, lat, view)
        d.line((x0, y0, x1, y1), fill=rgba(PLAT, 0.04 * a), width=1)
    # 항로 점선
    pts = [proj(lo, la, view) for lo, la in LANE]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / 22))
        for i in range(n):
            if i % 2 == 0:
                f0, f1 = i / n, (i + 1) / n
                d.line((x0 + (x1 - x0) * f0, y0 + (y1 - y0) * f0, x0 + (x1 - x0) * f1, y0 + (y1 - y0) * f1),
                       fill=rgba(CHAMP, 0.35 * a), width=2)
    # 유조선
    if ships:
        for k in range(6):
            u = (t * 0.035 + k / 6) % 1
            x, y = lane_point(u, view)
            r = 5 + 2 * zoom
            d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(PLAT, a * 0.9))
            d.ellipse((x - r * 2.4, y - r * 2.4, x + r * 2.4, y + r * 2.4), outline=rgba(PLAT, a * 0.15), width=1)
    # 지명
    for name, lo, la, sz in [("IRAN", 55.0, 29.0, 34), ("OMAN", 57.6, 22.9, 30), ("UAE", 54.2, 23.4, 28),
                             ("PERSIAN GULF", 51.9, 26.9, 24), ("GULF OF OMAN", 59.2, 24.6, 24)]:
        if not names:
            break
        x, y = proj(lo, la, view)
        tracked(d, x, y, name, serif("r", sz), DIM, a * 0.9, track=8, anchor="c")
    # 해협 이름
    x, y = proj(57.3, 25.85, view)
    if label in ("hormuz", "swap"):
        tracked(d, x, y, "STRAIT OF HORMUZ", serif("b", 34), PLAT, a, track=6, anchor="c")
    if label == "swap":
        f = serif("b", 34)
        wtot = sum(d.textlength(ch, font=f) for ch in "STRAIT OF HORMUZ") + 6 * 15
        sp = ease((label_t - 0.0) / 0.6)
        if sp > 0:
            d.line((x - wtot / 2 - 10, y - 12, x - wtot / 2 - 10 + (wtot + 20) * sp, y - 12), fill=rgba(CRIMSON, a), width=4)
        s = "TRUMP STRAIT"
        n = int(len(s) * clamp((label_t - 0.8) / 1.2))
        if n > 0:
            tracked(d, x, y + 80, s[:n], serif("x", 56), CHAMP, a, track=10, anchor="c")
    if label == "trump":
        tracked(d, x, y, "TRUMP STRAIT", serif("x", 48), CHAMP, a, track=10, anchor="c")
    return view


def make_bg():
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.65)) ** 2)
    vig = np.clip(1.15 - r, 0.0, 1.0)[..., None]
    base = np.array(SEA, np.float32) * vig + np.array(BLACK, np.float32) * (1 - vig)
    g = rng.normal(0, 2.2, (H, W, 1)).astype(np.float32)
    return Image.fromarray(np.clip(base + g, 0, 255).astype(np.uint8))


BG = make_bg()
BAR = 150  # 시네마틱 상·하단 여백


def base(T, total):
    img = BG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    return img, d


def finish(d, T, total):
    """장면 위에 얹는 공통 프레임: 상하 바, 표기, 진행선."""
    d.rectangle((0, 0, W, BAR), fill=BLACK)
    d.rectangle((0, H - BAR, W, H), fill=BLACK)
    d.line((80, BAR, W - 80, BAR), fill=rgba(CHAMP, 0.35), width=1)
    d.line((80, H - BAR, W - 80, H - BAR), fill=rgba(CHAMP, 0.35), width=1)
    tracked(d, 80, BAR - 40, "WORLD  ·  BREAKING", serif("r", 24), CHAMP, 0.9, track=6)
    tracked(d, W - 80, BAR - 40, "2026.09.26", serif("r", 24), DIM, 0.9, track=4, anchor="r")
    d.line((80, H - BAR + 60, W - 80, H - BAR + 60), fill=rgba(PLAT, 0.08), width=2)
    d.line((80, H - BAR + 60, 80 + (W - 160) * clamp(T / total), H - BAR + 60), fill=rgba(CHAMP, 0.7), width=2)


def ft(d, xy, s, f, color, t, start, dur=1.0, rise=20, anchor="mm", a_max=1.0):
    p = appear(t, start, dur)
    if p <= 0:
        return
    x, y = xy
    d.text((x, y + rise * (1 - p)), s, font=f, fill=rgba(color, p * a_max), anchor=anchor)


def veil(d, a):
    """지도 위 텍스트 가독성을 위한 어두운 막."""
    d.rectangle((0, 0, W, H), fill=(0, 0, 0, int(255 * a)))


# ---- 장면 ----
def s_open(d, t, dur):
    draw_map(d, t, 0.0, a=0.35 * appear(t, 0.0, 2.0), label=None, names=False)
    veil(d, 0.35)
    tracked(d, W / 2, 640, "속보", serif("b", 34), CRIMSON, appear(t, 0.6), track=16, anchor="c")
    d.line((W / 2 - 40, 680, W / 2 + 40, 680), fill=rgba(CRIMSON, appear(t, 0.8)), width=2)
    ft(d, (W / 2, 800), "호르무즈가 아니라", serif("r", 68), PLAT, t, 1.0)
    ft(d, (W / 2, 950), "'트럼프 해협'?", serif("x", 124), CHAMP, t, 1.5)
    ft(d, (W / 2, 1110), "트럼프가 올린 지도 한 장", serif("r", 48), DIM, t, 2.2)


def s_map(d, t, dur):
    z = clamp(t / 5.0)
    draw_map(d, t + 6, z, a=1.0, label="swap" if t > 4.2 else ("hormuz" if t > 1.5 else None), label_t=t - 4.2)
    p = appear(t, 0.8)
    d.rectangle((0, H - BAR - 260, W, H - BAR), fill=(0, 0, 0, int(170 * p)))
    ft(d, (W / 2, H - BAR - 180), "9월 26일, 트루스소셜", serif("r", 40), CHAMP, t, 1.0)
    ft(d, (W / 2, H - BAR - 105), "해협 이름을 바꾼 지도를 게시", serif("b", 52), PLAT, t, 1.3)


def s_why(d, t, dur):
    draw_map(d, t + 14, 1.0, a=0.18, label=None, names=False)
    veil(d, 0.25)
    tracked(d, W / 2, 470, "WHY IT MATTERS", serif("r", 28), CHAMP, appear(t, 0.3), track=12, anchor="c")
    # 원형 게이지
    cx, cy, r = W / 2, 820, 230
    g = ease((t - 0.8) / 1.8)
    a = appear(t, 0.5)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(PLAT, 0.1 * a), width=3)
    if g > 0:
        d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * 0.2 * g, fill=rgba(CHAMP, 1), width=6)
        d.text((cx, cy - 10), f"{int(round(20 * g))}%", font=serif("x", 150), fill=rgba(CHAMP, g), anchor="mm")
        d.text((cx, cy + 105), "약", font=serif("r", 36), fill=rgba(DIM, g), anchor="mm")
    ft(d, (W / 2, 1160), "세계 석유 소비량의 약 5분의 1이", serif("r", 46), PLAT, t, 2.2)
    ft(d, (W / 2, 1240), "지나는 바닷길", serif("x", 72), PLAT, t, 2.5)
    ft(d, (W / 2, 1350), "미국 에너지정보청(EIA) 추정", serif("r", 30), DIM, t, 2.9)


def s_offer(d, t, dur):
    tracked(d, W / 2, 380, "IRAN'S OFFER", serif("r", 28), CHAMP, appear(t, 0.2), track=12, anchor="c")
    ft(d, (W / 2, 490), "이란의 제안", serif("x", 84), PLAT, t, 0.4)
    ft(d, (W / 2, 580), "아라그치 외무장관 · 유엔총회 계기", serif("r", 36), DIM, t, 0.7)
    conds = ["미국의 해상 봉쇄 해제", "이란산 석유 수출 제재 면제", "모든 전선에서 휴전"]
    y = 720
    for i, c in enumerate(conds):
        st = 1.2 + i * 0.45
        p = appear(t, st)
        if p <= 0:
            continue
        d.text((140, y), f"0{i + 1}", font=serif("r", 40), fill=rgba(CHAMP, p))
        d.text((240, y), c, font=serif("b", 50), fill=rgba(PLAT, p))
        lp = ease((t - st) / 0.8)
        d.line((140, y + 90, 140 + (W - 280) * lp, y + 90), fill=rgba(PLAT, 0.12), width=1)
        y += 140
    # 화살표 → 결과
    a = appear(t, 2.8)
    if a > 0:
        d.line((W / 2, y + 10, W / 2, y + 90), fill=rgba(CHAMP, a), width=2)
        d.polygon([(W / 2 - 12, y + 80), (W / 2 + 12, y + 80), (W / 2, y + 100)], fill=rgba(CHAMP, a))
    ft(d, (W / 2, y + 180), "7일 안에", serif("r", 48), CHAMP, t, 3.1)
    ft(d, (W / 2, y + 270), "해협 개방 · 핵 협상 재개", serif("x", 64), PLAT, t, 3.4)


def s_answer(d, t, dur):
    draw_map(d, t + 20, 1.0, a=0.55, label="trump", ships=True)
    veil(d, 0.45)
    tracked(d, W / 2, 470, "THE RESPONSE", serif("r", 28), CHAMP, appear(t, 0.2), track=12, anchor="c")
    ft(d, (W / 2, 590), "트럼프의 첫 반응은", serif("r", 56), PLAT, t, 0.5)
    ft(d, (W / 2, 700), "지도 한 장", serif("x", 110), CHAMP, t, 0.9)
    p = appear(t, 2.0)
    if p > 0:
        d.rectangle((0, 1340, W, 1600), fill=(0, 0, 0, int(190 * p)))
    ft(d, (W / 2, 1410), "이란의 해협 통제권을 인정하지 않고", serif("r", 44), PLAT, t, 2.2)
    ft(d, (W / 2, 1490), "제안을 거부하겠다는 뜻으로 풀이", serif("b", 50), PLAT, t, 2.5)


def s_timeline(d, t, dur):
    tracked(d, W / 2, 380, "BUILD-UP", serif("r", 28), CHAMP, appear(t, 0.2), track=12, anchor="c")
    ft(d, (W / 2, 490), "예고된 지도", serif("x", 84), PLAT, t, 0.4)
    x = 200
    lp = ease((t - 0.8) / 2.4)
    d.line((x, 640, x, 640 + 860 * lp), fill=rgba(CHAMP, 0.6), width=2)
    items = [("8월", "'새 미국 영토'로 표기한", "호르무즈 지도 게시"),
             ("9월 2일", "\"호르무즈 해협 이름을", "트럼프 해협으로 바꿔야 할까\""),
             ("9월 26일", "'트럼프 해협' 지도 게시", "")]
    y = 660
    for i, (date, l1, l2) in enumerate(items):
        st = 1.0 + i * 0.8
        p = appear(t, st)
        if p <= 0:
            y += 290
            continue
        last = i == 2
        r = 12 if last else 8
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(CRIMSON if last else CHAMP, p))
        d.text((x + 60, y), date, font=serif("b", 44), fill=rgba(CHAMP, p), anchor="lm")
        d.text((x + 60, y + 80), l1, font=serif("r", 42), fill=rgba(PLAT, p), anchor="lm")
        if l2:
            d.text((x + 60, y + 145), l2, font=serif("r", 42), fill=rgba(PLAT, p), anchor="lm")
        y += 290


def s_end(d, t, dur):
    draw_map(d, t + 30, 1.0 - 0.6 * ease(t / dur), a=0.22, label=None, names=False)
    veil(d, 0.3)
    ft(d, (W / 2, 560), "\"호르무즈 해협은 이란의 것이었고,", serif("r", 44), DIM, t, 0.3)
    ft(d, (W / 2, 630), "앞으로도 이란의 것\"", serif("r", 44), DIM, t, 0.5)
    ft(d, (W / 2, 700), "— 이란 외무차관", serif("r", 32), DIM, t, 0.8)
    ft(d, (W / 2, 900), "공식 명칭은", serif("r", 56), PLAT, t, 1.5)
    ft(d, (W / 2, 1010), "여전히 호르무즈 해협", serif("x", 84), CHAMP, t, 1.9)
    d.line((W / 2 - 120, 1130, W / 2 - 120 + 240 * ease((t - 2.5) / 1.0), 1130), fill=rgba(CHAMP, 0.8), width=2)
    tracked(d, W / 2, 1230, "출처  ·  매일신문", serif("r", 32), DIM, appear(t, 2.9), track=4, anchor="c")


RAW = [(s_open, 6.0), (s_map, 8.5), (s_why, 7.0), (s_offer, 7.5), (s_answer, 7.0), (s_timeline, 7.0), (s_end, 6.5)]
_starts, TOTAL = mv.scene_starts(RAW)


def wrap_scene(fn, idx):
    def inner(d, t, dur):
        fn(d, t, dur)
        finish(d, _starts[idx] + t, TOTAL)
    return inner


SCENES = [(wrap_scene(fn, i), dur) for i, (fn, dur) in enumerate(RAW)]

# D단조 (Dm - Bb - Gm - A)
DARK = ([[62, 65, 69], [58, 62, 65], [55, 58, 62], [57, 61, 64]], [38, 34, 31, 33])


def drone(total):
    t = np.arange(int(total * audio.SR)) / audio.SR
    x = (np.sin(2 * np.pi * 36.7 * t) + 0.6 * np.sin(2 * np.pi * 55.0 * t + 0.3 * np.sin(2 * np.pi * 0.1 * t))
         + 0.3 * np.sin(2 * np.pi * 73.4 * t))
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 9.0) ** 2
    return x * swell * 0.05


def sound(starts, total, path):
    a = audio
    mx = a.Mixer(total)
    put = mx.put
    s0, s1, s2, s3, s4, s5, s6 = starts
    for s in starts[1:]:
        put(a.whoosh(1.2), s - 0.7, 0.2)
    # 도입: 저음 임팩트
    put(a.boom(), s0 + 0.6, 0.6)
    put(a.timpani(38), s0 + 1.5, 0.7)
    put(a.ding(1174.7), s0 + 2.2, 0.15)
    # 지도: 줌인 상승음, 해협 이름 삭선·타이핑
    put(a.rise(4.5), s1 + 0.2, 0.5)
    put(a.ding(880), s1 + 1.5, 0.15)
    put(a.swish(0.6), s1 + 4.2, 0.9, pan=-0.3)
    put(a.timpani(33), s1 + 4.3, 0.6)
    for i in range(12):
        put(a.tick(1800 + 60 * (i % 3), 0.02, 0.2), s1 + 5.0 + i * 0.1, 1.0, pan=0.2)
    put(a.boom(), s1 + 6.2, 0.4)
    # 20% 게이지
    put(a.rise(1.8), s2 + 0.8, 0.4)
    put(a.ding(1318.5), s2 + 2.6, 0.2)
    # 제안 목록
    for i in range(3):
        put(a.ding(987.8 + 120 * i), s3 + 1.2 + 0.45 * i, 0.12)
    put(a.timpani(36), s3 + 3.1, 0.5)
    # 트럼프의 반응
    put(a.timpani(31), s4 + 0.9, 0.8)
    # 타임라인
    for i in range(3):
        put(a.ding(880 + 220 * i), s5 + 1.0 + 0.8 * i, 0.14 if i < 2 else 0.2)
    put(a.boom(), s5 + 2.6, 0.3)
    # 마무리
    put(a.timpani(38), s6 + 1.9, 0.8)
    put(a.chime(), s6 + 2.0, 0.2)
    bgm = a.elegant_music(total, bar=4.0, progression=DARK) * 0.75 + drone(total)
    mx.write(path, bgm)


if __name__ == "__main__":
    mv.render(SCENES, OUT, sound, thumb_at=_starts[1] + 7.5, base=base)
