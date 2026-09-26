"""매일신문 기사 '트럼프 극진한 예우 받고 돌아간 시진핑…美 국빈 방문 마치고 귀국'을
1080x1920 세로형 영상으로 만든다. 짙은 남색 바탕 + 금색 라인 + 명조체의 절제된 에디토리얼 스타일,
피아노·현악 배경음.

사용법: pip install pillow numpy imageio-ffmpeg && python3 video/xi_visit.py
결과물: video/xi-visit-news.mp4, video/xi-visit-news-thumbnail.png
"""
import math
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import audio
import make_video as mv
from make_video import W, H, appear, clamp, ease

OUT = os.path.join(mv.HERE, "xi-visit-news.mp4")
mv.FADE = 0.9

BG_C = (11, 13, 20)
IVORY = (236, 230, 216)
GOLD = (201, 169, 110)
DIM = (138, 134, 126)
M = 70  # 액자 여백


@lru_cache(None)
def serif(weight, size):
    name = {"r": "NanumMyeongjo.ttf", "b": "NanumMyeongjoBold.ttf", "x": "NanumMyeongjoExtraBold.ttf"}[weight]
    return ImageFont.truetype(os.path.join(mv.HERE, "fonts", name), size)


def rgba(c, a=1.0):
    return (*c[:3], int(255 * clamp(a)))


def make_backgrounds(k=4):
    """비네팅 + 필름 그레인을 입힌 배경 몇 장을 미리 만든다."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.42) / (H * 0.7)) ** 2)
    vig = np.clip(1.25 - r, 0.35, 1.0)[..., None]
    base = np.array([22, 26, 40], np.float32) * vig + np.array(BG_C, np.float32) * (1 - vig)
    rng = np.random.default_rng(3)
    out = []
    for _ in range(k):
        g = rng.normal(0, 2.5, (H, W, 1)).astype(np.float32)
        out.append(Image.fromarray(np.clip(base + g, 0, 255).astype(np.uint8)))
    return out


BGS = make_backgrounds(1)


def base(T, total):
    img = BGS[0].copy()  # 그레인은 고정 (프레임마다 바꾸면 용량이 폭증)
    d = ImageDraw.Draw(img, "RGBA")
    # 금색 액자: 처음 2초간 그려지고 이후 유지
    p = ease(T / 2.0)
    per = 2 * (W - 2 * M) + 2 * (H - 2 * M)
    L = per * p
    segs = [((M, M), (W - M, M)), ((W - M, M), (W - M, H - M)), ((W - M, H - M), (M, H - M)), ((M, H - M), (M, M))]
    for (x0, y0), (x1, y1) in segs:
        seg = math.hypot(x1 - x0, y1 - y0)
        f = clamp(L / seg)
        if f > 0:
            d.line((x0, y0, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f), fill=rgba(GOLD, 0.55), width=2)
        L -= seg
    # 상단 표기
    a = appear(T, 0.8, 1.0)
    tracked(d, W / 2, M + 60, "INTERNATIONAL", serif("r", 26), GOLD, a, track=8, anchor="c")
    # 하단 진행 (얇은 금선)
    d.line((W / 2 - 120, H - M - 50, W / 2 + 120, H - M - 50), fill=rgba(DIM, 0.25), width=2)
    d.line((W / 2 - 120, H - M - 50, W / 2 - 120 + 240 * clamp(T / total), H - M - 50), fill=rgba(GOLD, 0.8), width=2)
    return img, d


def tracked(d, x, y, s, f, color, a, track=4, anchor="l"):
    """자간을 넓힌 텍스트."""
    if a <= 0:
        return
    widths = [d.textlength(ch, font=f) for ch in s]
    total = sum(widths) + track * (len(s) - 1)
    if anchor == "c":
        x -= total / 2
    elif anchor == "r":
        x -= total
    for ch, w in zip(s, widths):
        d.text((x, y), ch, font=f, fill=rgba(color, a), anchor="ls")
        x += w + track


def fade_text(d, xy, s, f, color, t, start, dur=0.9, rise=24, anchor="la"):
    p = appear(t, start, dur)
    if p <= 0:
        return
    x, y = xy
    d.text((x, y + rise * (1 - p)), s, font=f, fill=rgba(color, p), anchor=anchor)


def gold_rule(d, x, y, w, t, start, dur=0.9, center=False):
    p = ease((t - start) / dur)
    if p <= 0:
        return
    if center:
        d.line((x - w / 2 * p, y, x + w / 2 * p, y), fill=rgba(GOLD, 0.9), width=2)
    else:
        d.line((x, y, x + w * p, y), fill=rgba(GOLD, 0.9), width=2)


def chapter(d, t, num, label):
    tracked(d, W / 2, 330, num, serif("r", 44), GOLD, appear(t, 0.2, 0.9), track=6, anchor="c")
    gold_rule(d, W / 2, 360, 80, t, 0.4, center=True)
    tracked(d, W / 2, 420, label, serif("r", 28), DIM, appear(t, 0.5, 0.9), track=10, anchor="c")


def diamond(d, cx, cy, r, a, fill=True):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if fill:
        d.polygon(pts, fill=rgba(GOLD, a))
    else:
        d.polygon(pts, outline=rgba(GOLD, a))


# ---- 장면 ----
def s_open(d, t, dur):
    tracked(d, W / 2, 560, "STATE VISIT", serif("r", 32), GOLD, appear(t, 0.8, 1.2), track=14, anchor="c")
    fade_text(d, (W / 2, 720), "트럼프의", serif("r", 64), IVORY, t, 1.2, anchor="mm")
    fade_text(d, (W / 2, 860), "극진한 예우", serif("x", 118), IVORY, t, 1.5, anchor="mm")
    fade_text(d, (W / 2, 1010), "받고 돌아간 시진핑", serif("b", 76), IVORY, t, 1.9, anchor="mm")
    gold_rule(d, W / 2, 1130, 260, t, 2.5, center=True)
    fade_text(d, (W / 2, 1220), "미국 국빈 방문 마치고 귀국", serif("r", 46), DIM, t, 2.8, anchor="mm")
    diamond(d, W / 2, 1330, 8, appear(t, 3.2))


def s_eleven(d, t, dur):
    chapter(d, t, "I", "ELEVEN YEARS")
    g = ease((t - 0.8) / 1.6)
    if g > 0:
        n = max(1, int(round(11 * g)))
        d.text((W / 2, 820), f"{n}", font=serif("x", 380), fill=rgba(GOLD, clamp(g * 1.5)), anchor="mm")
    fade_text(d, (W / 2, 1080), "년 만의 국빈 방문", serif("b", 70), IVORY, t, 1.8, anchor="mm")
    gold_rule(d, W / 2, 1180, 200, t, 2.3, center=True)
    fade_text(d, (W / 2, 1270), "2026. 9. 23 — 25  ·  워싱턴", serif("r", 42), IVORY, t, 2.6, anchor="mm")
    fade_text(d, (W / 2, 1350), "2015년 이후 처음, 올해 두 번째 대면 회담", serif("r", 36), DIM, t, 3.0, anchor="mm")


def jet(d, x, y, s, a, kind="f22"):
    if kind == "b2":
        pts = [(0, -10), (60, 20), (40, 26), (20, 18), (0, 26), (-20, 18), (-40, 26), (-60, 20)]
    else:
        pts = [(0, -34), (8, -10), (30, 10), (30, 16), (8, 10), (12, 28), (0, 24), (-12, 28), (-8, 10), (-30, 16), (-30, 10), (-8, -10)]
    # 오른쪽으로 비행하도록 90도 회전
    rot = [(x - py * s, y + px * s) for px, py in pts]
    d.polygon(rot, fill=rgba(IVORY, a))


def s_runway(d, t, dur):
    chapter(d, t, "II", "ON THE RUNWAY")
    # 활주로 원근선
    a = appear(t, 0.3, 1.2)
    vx, vy = W / 2, 1480
    if a > 0:
        for dx in (-460, 460):
            d.line((vx, vy, vx + dx, H - M - 90), fill=rgba(GOLD, 0.35 * a), width=2)
        for k in range(8):
            ph = ((k / 8) + t * 0.18) % 1
            z = ph ** 2.2
            y0 = vy + (H - M - 90 - vy) * z
            y1 = vy + (H - M - 90 - vy) * min(1, (ph + 0.05) ** 2.2)
            d.line((vx, y0, vx, y1), fill=rgba(IVORY, 0.5 * a * ph), width=max(1, int(8 * ph)))
    # 편대 비행: B-2 1대 + F-22 4대
    fp = (t - 1.0) / 4.5
    if 0 < fp < 1.2:
        bx = -250 + (W + 500) * fp
        by = 600 - 60 * fp
        fa = clamp(min(fp * 4, (1.2 - fp) * 4)) * 0.9
        jet(d, bx, by, 1.4, fa, "b2")
        for i, (ox, oy) in enumerate([(-120, -70), (-120, 70), (-220, -130), (-220, 130)]):
            jet(d, bx + ox, by + oy, 0.9, fa, "f22")
    fade_text(d, (W / 2, 820), "B-2 폭격기 1대 · F-22 전투기 4대", serif("r", 36), DIM, t, 1.6, anchor="mm")
    fade_text(d, (W / 2, 1180), "트럼프 대통령,", serif("r", 54), IVORY, t, 2.2, anchor="mm")
    fade_text(d, (W / 2, 1290), "활주로에서 직접 영접", serif("x", 84), IVORY, t, 2.5, anchor="mm")
    fade_text(d, (W / 2, 1400), "앤드루스 합동기지", serif("r", 38), GOLD, t, 2.9, anchor="mm")


def s_protocol(d, t, dur):
    chapter(d, t, "III", "CEREMONY")
    fade_text(d, (W / 2, 640), "사흘간", serif("r", 54), IVORY, t, 0.8, anchor="mm")
    g = ease((t - 1.0) / 1.0)
    if g > 0:
        d.text((W / 2, 800), f"{max(1, int(round(4 * g)))}", font=serif("x", 220), fill=rgba(GOLD, g), anchor="mm")
    fade_text(d, (W / 2, 960), "차례의 만남", serif("b", 64), IVORY, t, 1.4, anchor="mm")
    rows = [("의장대 사열", "군악·의장 공연으로 맞이"),
            ("국빈 만찬", "미국 주요 기업 CEO들 초청"),
            ("공항 영접", "외국 정상에 대한 이례적 예우")]
    y = 1110
    for i, (h, b) in enumerate(rows):
        st = 1.9 + i * 0.45
        diamond(d, 190, y + 22, 7, appear(t, st))
        fade_text(d, (230, y), h, serif("b", 46), IVORY, t, st)
        fade_text(d, (230, y + 64), b, serif("r", 34), DIM, t, st + 0.15)
        if i < 2:
            p = appear(t, st + 0.3)
            d.line((230, y + 130, W - 180, y + 130), fill=rgba(DIM, 0.25 * p), width=1)
        y += 160


def s_result(d, t, dur):
    chapter(d, t, "IV", "BEHIND THE POMP")
    fade_text(d, (W / 2, 620), "화려한 의전,", serif("r", 60), IVORY, t, 0.8, anchor="mm")
    fade_text(d, (W / 2, 730), "성과는 절제됐다", serif("x", 84), IVORY, t, 1.1, anchor="mm")
    gold_rule(d, W / 2, 830, 200, t, 1.5, center=True)
    # 핵심 합의
    p = appear(t, 1.8, 1.0)
    if p > 0:
        box = (150, 900 + 20 * (1 - p), W - 150, 1210 + 20 * (1 - p))
        d.rectangle(box, outline=rgba(GOLD, 0.7 * p), width=2)
        tracked(d, W / 2, box[1] + 70, "AGREED", serif("r", 28), GOLD, p, track=10, anchor="c")
        d.text((W / 2, box[1] + 150), "무역 휴전 2개월 연장", font=serif("x", 64), fill=rgba(IVORY, p), anchor="mm")
        d.text((W / 2, box[1] + 240), "내년 1월 10일까지", font=serif("r", 42), fill=rgba(DIM, p), anchor="mm")
    fade_text(d, (W / 2, 1320), "대만 · AI · 이란 · 우크라이나 논의", serif("r", 40), IVORY, t, 2.6, anchor="mm")
    fade_text(d, (W / 2, 1390), "구체적 합의는 제한적이었다는 평가", serif("r", 36), DIM, t, 2.9, anchor="mm")


def s_farewell(d, t, dur):
    chapter(d, t, "V", "FAREWELL")
    fade_text(d, (W / 2, 600), "9월 25일 정오,", serif("r", 50), IVORY, t, 0.8, anchor="mm")
    fade_text(d, (W / 2, 700), "국립문서기록관리청 앞 작별 악수", serif("b", 56), IVORY, t, 1.1, anchor="mm")
    fade_text(d, (W / 2, 790), "앤드루스 기지에서 전용기로 귀국", serif("r", 38), DIM, t, 1.4, anchor="mm")
    # 다음 만남 타임라인
    tracked(d, W / 2, 960, "NEXT", serif("r", 30), GOLD, appear(t, 2.0), track=12, anchor="c")
    lp = ease((t - 2.2) / 1.2)
    x0, x1, y = 300, W - 300, 1070
    if lp > 0:
        d.line((x0, y, x0 + (x1 - x0) * lp, y), fill=rgba(GOLD, 0.8), width=2)
    for i, (x, date, place) in enumerate([(x0, "11월 18 — 19일", "중국 선전 · APEC"), (x1, "12월 14 — 15일", "마이애미 · G20")]):
        st = 2.4 + i * 0.7
        p = appear(t, st)
        if p <= 0:
            continue
        d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=rgba(GOLD, p))
        d.text((x, y + 60), date, font=serif("b", 40), fill=rgba(IVORY, p), anchor="mm")
        d.text((x, y + 125), place, font=serif("r", 36), fill=rgba(DIM, p), anchor="mm")
    fade_text(d, (W / 2, 1360), "성사되면 올해만 네 차례 정상회담", serif("r", 42), IVORY, t, 3.8, anchor="mm")


def s_end(d, t, dur):
    fade_text(d, (W / 2, 780), "예우는 극진했고,", serif("r", 72), IVORY, t, 0.5, anchor="mm")
    fade_text(d, (W / 2, 920), "과제는 남았다", serif("x", 104), GOLD, t, 1.3, anchor="mm")
    gold_rule(d, W / 2, 1060, 260, t, 2.0, center=True)
    tracked(d, W / 2, 1170, "출처  ·  매일신문", serif("r", 34), DIM, appear(t, 2.4), track=4, anchor="c")


SCENES = [(s_open, 6.0), (s_eleven, 6.5), (s_runway, 7.0), (s_protocol, 7.0),
          (s_result, 7.0), (s_farewell, 7.5), (s_end, 5.5)]


def sound(starts, total, path):
    a = audio
    mx = a.Mixer(total)
    put = mx.put
    s0, s1, s2, s3, s4, s5, s6 = starts
    put(a.timpani(38), s0 + 1.45, 0.8)
    put(a.ding(1174.7), s0 + 3.2, 0.25)
    for s in starts[1:]:
        put(a.whoosh(1.0), s - 0.6, 0.18)
        put(a.ding(880), s + 0.2, 0.18)   # 장 번호 등장
    # I. 숫자
    put(a.timpani(33), s1 + 2.4, 0.7)
    # II. 편대 비행
    put(a.jet_pass(4.0), s2 + 1.0, 0.55, pan=-0.4)
    put(a.jet_pass(3.0), s2 + 2.4, 0.35, pan=0.5)
    # III. 목록
    for i in range(3):
        put(a.ding(1318.5 + 150 * i), s3 + 1.9 + 0.45 * i, 0.14)
    # IV. 합의 박스
    put(a.timpani(36), s4 + 1.8, 0.6)
    # V. 타임라인 점
    put(a.ding(987.8), s5 + 2.4, 0.2, pan=-0.4)
    put(a.ding(1318.5), s5 + 3.1, 0.2, pan=0.4)
    # 마무리
    put(a.timpani(38), s6 + 1.3, 0.8)
    put(a.chime(), s6 + 1.4, 0.25)
    mx.write(path, a.elegant_music(total) * 0.9)


if __name__ == "__main__":
    mv.render(SCENES, OUT, sound, thumb_at=4.5, base=base)
