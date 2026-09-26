"""매일신문 기사 '김병주 모르면 입 좀 닥쳐요 vs 한동훈 시간 끌다 北 증거조작하면?'을
1080x1920 세로형 영상으로 만든다. 밝은 파스텔 + 굵은 외곽선(네오브루탈) 스타일, 경쾌한 배경음.

사용법: pip install pillow numpy imageio-ffmpeg && python3 video/dmz_debate.py
결과물: video/dmz-debate-news.mp4, video/dmz-debate-news-thumbnail.png
"""
import math
import os

from PIL import Image, ImageDraw

import audio
import make_video as mv
from make_video import W, H, appear, back, clamp, ease, font

OUT = os.path.join(mv.HERE, "dmz-debate-news.mp4")

BG = (246, 243, 255)
INK = (22, 22, 34)
WHITE = (255, 255, 255)
BLUE = (61, 123, 255)    # 김병주
PINK = (255, 61, 127)    # 한동훈
LIME = (198, 255, 61)
YELLOW = (255, 225, 77)
PURPLE = (124, 77, 255)
GREY = (120, 118, 140)

KIM = ("김", "김병주", "민주당 · 육군 대장 출신", BLUE)
HAN = ("한", "한동훈", "무소속", PINK)

SCENE_COUNT = 7


def rgba(c, a=1.0):
    return (*c[:3], int(255 * clamp(a)))


def make_bg():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 48):
        for x in range(0, W, 48):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(222, 216, 245))
    return img


BG_IMG = make_bg()
_starts = []


def base(T, total):
    img = BG_IMG.copy()
    d = ImageDraw.Draw(img, "RGBA")
    # 떠다니는 블롭
    ox, oy = 50 * math.sin(T * 0.6), 40 * math.cos(T * 0.5)
    d.ellipse((700 + ox, -200 + oy, 1300 + ox, 400 + oy), fill=(198, 255, 61, 90))
    d.ellipse((-260 - ox, 1560 - oy, 340 - ox, 2160 - oy), fill=(255, 61, 127, 50))
    # 인스타 스토리식 진행 바
    n = SCENE_COUNT
    gap, x0, x1 = 10, 40, W - 40
    seg = (x1 - x0 - gap * (n - 1)) / n
    cur = max(i for i, s in enumerate(_starts) if s <= T) if _starts else 0
    for i in range(n):
        sx = x0 + i * (seg + gap)
        d.rounded_rectangle((sx, 60, sx + seg, 70), 5, fill=(22, 22, 34, 40))
        if i < cur:
            fill = seg
        elif i == cur:
            nxt = _starts[i + 1] if i + 1 < len(_starts) else total
            fill = seg * clamp((T - _starts[i]) / max(0.1, nxt - _starts[i]))
        else:
            fill = 0
        if fill > 0:
            d.rounded_rectangle((sx, 60, sx + fill, 70), 5, fill=INK)
    # 상단 출처 칩
    d.rounded_rectangle((40, 100, 250, 160), 30, fill=INK)
    d.text((145, 130), "매일신문", font=font("x", 32), fill=WHITE, anchor="mm")
    d.rounded_rectangle((264, 100, 470, 160), 30, fill=LIME, outline=INK, width=4)
    d.text((367, 130), "정치 공방", font=font("x", 30), fill=INK, anchor="mm")
    return img, d


# ---- 컴포넌트 ----
def neo(d, box, fill, r=28, shadow=10, width=5, a=1.0):
    x0, y0, x1, y1 = box
    d.rounded_rectangle((x0 + shadow, y0 + shadow, x1 + shadow, y1 + shadow), r, fill=rgba(INK, a))
    d.rounded_rectangle(box, r, fill=rgba(fill, a), outline=rgba(INK, a), width=width)


def avatar(d, cx, cy, r, who, a=1.0):
    ini, _, _, col = who
    d.ellipse((cx - r + 6, cy - r + 6, cx + r + 6, cy + r + 6), fill=rgba(INK, a))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rgba(col, a), outline=rgba(INK, a), width=5)
    d.text((cx, cy), ini, font=font("x", int(r * 1.0)), fill=rgba(WHITE, a), anchor="mm")


def sticker(d, cx, cy, s, fill, angle, a=1.0, size=64, fg=INK, pad=(36, 20)):
    """회전된 스티커 라벨을 붙인다."""
    if a <= 0:
        return
    f = font("x", size)
    tw = int(d.textlength(s, font=f))
    w, h = tw + pad[0] * 2, size + pad[1] * 2
    im = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0))
    sd = ImageDraw.Draw(im)
    sd.rounded_rectangle((8, 8, w + 8, h + 8), 22, fill=rgba(INK, a))
    sd.rounded_rectangle((0, 0, w, h), 22, fill=rgba(fill, a), outline=rgba(INK, a), width=5)
    sd.text((w / 2, h / 2), s, font=f, fill=rgba(fg, a), anchor="mm")
    im = im.rotate(angle, expand=True, resample=Image.BICUBIC)
    d.img.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)


def headline(d, x, y, rows, t, start, size=96, color=INK, step=0.12):
    for i, s in enumerate(rows):
        p = back((t - start - i * step) / 0.45)
        if p > 0:
            d.text((x, y + 30 * (1 - p)), s, font=font("x", size), fill=rgba(color, clamp(p)))
        y += int(size * 1.25)
    return y


def wrap_rows(d, s, f, max_w):
    out, cur = [], ""
    for word in s.split(" "):
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = word
    out.append(cur)
    return out


def chat(d, y, t, start, who, msg, side="left", size=56):
    """메신저 말풍선. 등장 전 0.5초간 '입력 중…' 점 표시. 다음 y 반환."""
    col = who[3]
    f = font("b", size)
    max_w = 720
    rows = wrap_rows(d, msg, f, max_w)
    tw = max(d.textlength(r, font=f) for r in rows)
    bw, bh = tw + 70, len(rows) * int(size * 1.4) + 50
    if side == "left":
        ax, bx0 = 110, 190
    else:
        ax, bx0 = W - 110, W - 190 - bw
    if t < start - 0.5:
        return y + bh + 60
    avatar(d, ax, y + 45, 42, who)
    if t < start:
        # 입력 중 점 3개
        tb = (bx0 if side == "left" else W - 190 - 150, y, (bx0 if side == "left" else W - 190 - 150) + 150, y + 90)
        neo(d, tb, WHITE, r=40, shadow=6)
        for k in range(3):
            ph = math.sin(t * 10 - k * 0.8)
            cx = tb[0] + 45 + k * 30
            d.ellipse((cx - 9, y + 45 - 9 - 6 * ph, cx + 9, y + 45 + 9 - 6 * ph), fill=GREY)
        return y + bh + 60
    p = back((t - start) / 0.35)
    dy = int(20 * (1 - clamp(p)))
    fill = col if side == "left" else col
    neo(d, (bx0, y + dy, bx0 + bw, y + bh + dy), fill, r=36, shadow=8)
    for i, r in enumerate(rows):
        d.text((bx0 + 35, y + 25 + dy + i * int(size * 1.4)), r, font=f, fill=WHITE)
    return y + bh + 60


def sys_chip(d, y, t, start, s):
    p = appear(t, start, 0.3)
    if p <= 0:
        return y + 90
    f = font("b", 34)
    tw = d.textlength(s, font=f)
    x0 = (W - tw) / 2 - 30
    d.rounded_rectangle((x0, y, x0 + tw + 60, y + 60), 30, fill=(22, 22, 34, int(200 * p)))
    d.text((W / 2, y + 30), s, font=f, fill=rgba(WHITE, p), anchor="mm")
    return y + 90


def profile(d, y, t, start, who):
    p = back((t - start) / 0.45)
    if p <= 0:
        return
    dx = int(-120 * (1 - clamp(p)))
    neo(d, (60 + dx, y, W - 70 + dx, y + 170), WHITE, r=36)
    avatar(d, 150 + dx, y + 85, 55, who)
    d.text((240 + dx, y + 30), who[1] + " 의원", font=font("x", 58), fill=INK)
    d.text((240 + dx, y + 105), who[2], font=font("b", 36), fill=GREY)


# ---- 장면 ----
def s_title(d, t, dur):
    # 두 아바타가 양쪽에서 날아와 VS
    pk = ease((t - 0.1) / 0.5)
    ph = ease((t - 0.25) / 0.5)
    shake = 0
    if 0.75 < t < 1.1:
        shake = 14 * math.sin(t * 90) * (1.1 - t) / 0.35
    avatar(d, -200 + 460 * pk + shake, 620, 150, KIM, clamp(pk))
    avatar(d, W + 200 - 460 * ph + shake, 620, 150, HAN, clamp(ph))
    vp = back((t - 0.7) / 0.35)
    if vp > 0:
        sticker(d, W / 2 + shake, 620, "VS", YELLOW, -8, clamp(vp), size=int(110 * max(vp, 0.3)))
    a = appear(t, 0.9, 0.3)
    if a > 0:
        d.text((260, 810), "김병주", font=font("x", 44), fill=rgba(INK, a), anchor="mm")
        d.text((W - 260, 810), "한동훈", font=font("x", 44), fill=rgba(INK, a), anchor="mm")
    y = headline(d, 70, 930, ["추석 연휴", "DMZ 지뢰 공방"], t, 1.1, size=104)
    sticker(d, 330, y + 90, "모르면 입 좀 닥쳐요", BLUE, 4, appear(t, 1.8, 0.25), size=48, fg=WHITE)
    sticker(d, 640, y + 260, "시간 끌다 北 증거조작하면?", PINK, -4, appear(t, 2.2, 0.25), size=48, fg=WHITE)


def s_what(d, t, dur):
    sticker(d, 270, 300, "무슨 일이냐면", LIME, -5, back((t - 0.1) / 0.35), size=56)
    items = [
        ("9.21", "서부전선 DMZ에서\n지뢰 추정 폭발", YELLOW),
        ("부상", "간부 포함\n장병 3명 다쳐", PINK),
        ("군", "현장조사는\n\"추석 이후\"", BLUE),
        ("야당", "\"증거 사라진다\"\n즉시 조사 촉구", PURPLE),
    ]
    y = 460
    # 타임라인 세로선
    lp = ease((t - 0.3) / 1.6)
    d.line((150, y + 40, 150, y + 40 + 1100 * lp), fill=INK, width=8)
    for i, (tag, body, col) in enumerate(items):
        st = 0.4 + i * 0.45
        p = back((t - st) / 0.4)
        if p > 0:
            r = 44 * max(p, 0.1)
            d.ellipse((150 - r, y + 40 - r, 150 + r, y + 40 + r), fill=rgba(col), outline=INK, width=5)
            d.text((150, y + 40), tag, font=font("x", 26 if len(tag) > 2 else 30), fill=INK if col in (YELLOW, LIME) else WHITE, anchor="mm")
            dx = int(80 * (1 - clamp(p)))
            neo(d, (230 + dx, y - 20, W - 70 + dx, y + 200), WHITE, r=30, shadow=8, a=clamp(p))
            for k, line in enumerate(body.split("\n")):
                d.text((270 + dx, y + 12 + k * 72), line, font=font("x" if k == 0 else "b", 52 if k == 0 else 44),
                       fill=rgba(INK if k == 0 else GREY, clamp(p)))
        y += 280


def s_han(d, t, dur):
    profile(d, 230, t, 0.1, HAN)
    y = 500
    y = sys_chip(d, y, t, 0.5, "9.24 · 국방부 앞 1인 시위")
    y = chat(d, y, t, 1.2, HAN, "'지뢰 폭발' 즉시 조사하라", side="right")
    y = chat(d, y, t, 2.3, HAN, "비가 와서 증거 없어지면 당신들이 책임질 것인가", side="right")
    chat(d, y, t, 3.5, HAN, "시간 끌다가 북한이 증거 조작하면 막을 수 있느냐", side="right")


def s_kim(d, t, dur):
    profile(d, 230, t, 0.1, KIM)
    y = 500
    y = sys_chip(d, y, t, 0.5, "9.25 · 페이스북")
    y = chat(d, y, t, 1.2, KIM, "정쟁을 이유로 우리 장병들을 지뢰가 깔린 밭으로 뛰어들라고 하나", side="left")
    y = chat(d, y, t, 2.3, KIM, "전투와 사고 현장 감식은 전혀 다른 일", side="left")
    chat(d, y, t, 3.4, KIM, "제발 모르면 입 좀 닥치고 있어요", side="left", size=64)


def s_round1(d, t, dur):
    sticker(d, 300, 300, "ROUND 1 · 9.21", YELLOW, -4, back((t - 0.1) / 0.35), size=54)
    headline(d, 70, 420, ["앞서 '똥별' 공방도"], t, 0.3, size=80)
    y = 640
    y = chat(d, y, t, 1.1, HAN, "민주당 똥별", side="right", size=72)
    y = chat(d, y, t, 2.0, KIM, "'똥별'은 평생 헌신한 장성들을 비하하는 단어", side="left")
    chat(d, y, t, 3.1, HAN, "똥별은 우리 군이 아니라 당신 같은 사람들을 말하는 것", side="right")


def s_issue(d, t, dur):
    headline(d, 70, 280, ["핵심 쟁점은", "조사 타이밍"], t, 0.1, size=96)
    # 시소
    cx, cy = W / 2, 1000
    a = appear(t, 0.5, 0.3)
    tilt = 0.14 * math.sin(t * 2.2) * clamp((t - 0.8) / 0.5)
    L = 400
    if a > 0:
        d.polygon([(cx, cy), (cx - 60, cy + 110), (cx + 60, cy + 110)], fill=rgba(INK, a))
        x0, y0 = cx - L * math.cos(tilt), cy - L * math.sin(tilt)
        x1, y1 = cx + L * math.cos(tilt), cy + L * math.sin(tilt)
        d.line((x0, y0, x1, y1), fill=rgba(INK, a), width=18)
        avatar(d, x0 + 20, y0 - 80, 60, KIM, a)
        avatar(d, x1 - 20, y1 - 80, 60, HAN, a)
    # 양쪽 입장 카드
    for i, (who, head, body, x) in enumerate([
            (KIM, "안전 먼저", "지뢰밭 감식은\n신중해야", 60),
            (HAN, "증거 먼저", "늦으면 증거\n훼손 우려", W / 2 + 15)]):
        p = back((t - 1.2 - i * 0.3) / 0.4)
        if p <= 0:
            continue
        dy = int(60 * (1 - clamp(p)))
        box = (x, 1200 + dy, x + W / 2 - 75, 1560 + dy)
        neo(d, box, who[3], r=34, a=clamp(p))
        d.text((box[0] + 36, box[1] + 36), who[1], font=font("b", 36), fill=rgba(WHITE, p))
        d.text((box[0] + 36, box[1] + 96), head, font=font("x", 62), fill=rgba(WHITE, p))
        for k, line in enumerate(body.split("\n")):
            d.text((box[0] + 36, box[1] + 200 + k * 58), line, font=font("b", 42), fill=rgba(WHITE, p))


def s_end(d, t, dur):
    headline(d, 70, 420, ["여러분", "생각은?"], t, 0.1, size=150)
    for i, (label, col, x) in enumerate([("안전 먼저", BLUE, 90), ("증거 먼저", PINK, W / 2 + 20)]):
        p = back((t - 0.8 - i * 0.2) / 0.4)
        if p <= 0:
            continue
        pulse = 6 * math.sin(t * 5 + i * 1.5) if t > 1.5 else 0
        box = (x, 1000 - pulse, x + W / 2 - 110, 1150 - pulse)
        neo(d, box, col, r=75, a=clamp(p))
        d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, font=font("x", 54), fill=rgba(WHITE, p), anchor="mm")
    sticker(d, W / 2, 1320, "댓글로 알려줘요", LIME, -3, back((t - 1.5) / 0.35), size=56)
    a = appear(t, 2.0)
    if a > 0:
        d.text((70, 1700), "출처: 매일신문", font=font("b", 34), fill=rgba(GREY, a))


SCENES = [(s_title, 4.5), (s_what, 5.5), (s_han, 6.0), (s_kim, 6.5), (s_round1, 6.0), (s_issue, 5.5), (s_end, 4.5)]
assert len(SCENES) == SCENE_COUNT


def sound(starts, total, path):
    a = audio
    mx = a.Mixer(total)
    put = mx.put
    s0, s1, s2, s3, s4, s5, s6 = starts
    for s in starts[1:]:
        put(a.whoosh(0.4), s - 0.3, 0.45, pan=-0.6)

    # 1. 타이틀: 양쪽에서 휙, VS 쾅, 스티커 보잉
    put(a.whoosh(0.5), s0 + 0.0, 0.5, pan=-0.8)
    put(a.whoosh(0.5), s0 + 0.15, 0.5, pan=0.8)
    put(a.stamp(), s0 + 0.75, 1.0)
    put(a.chime(), s0 + 0.8, 0.4)
    put(a.pop(), s0 + 1.15, 0.6)
    put(a.pop(), s0 + 1.27, 0.6)
    put(a.boing(), s0 + 1.8, 0.8, pan=-0.3)
    put(a.boing(), s0 + 2.2, 0.8, pan=0.3)

    # 2. 무슨 일: 스티커, 타임라인 팝
    put(a.boing(), s1 + 0.1, 0.7)
    for i in range(4):
        put(a.pop(), s1 + 0.4 + i * 0.45, 0.7)
        put(a.blip(700 + 120 * i), s1 + 0.45 + i * 0.45, 0.6)

    # 3·4. 채팅: 프로필 휙, 말풍선 알림음
    for s, times, pan in [(s2, [1.2, 2.3, 3.5], 0.5), (s3, [1.2, 2.3, 3.4], -0.5)]:
        put(a.swish(0.35), s + 0.1, 0.8, pan=pan)
        put(a.blip(600, 0.06, 0.2), s + 0.5, 1.0)
        for at in times:
            put(a.tick(3000, 0.02, 0.15), at + s - 0.45, 1.0, pan=pan)
            put(a.tick(3200, 0.02, 0.15), at + s - 0.3, 1.0, pan=pan)
            put(a.blip(988, 0.08, 0.35), s + at, 1.0, pan=pan)
            put(a.blip(1319, 0.08, 0.25), s + at + 0.07, 1.0, pan=pan)
    put(a.stamp(), s3 + 3.4, 0.6)

    # 5. 라운드 1: 공 울림 + 말풍선
    put(a.ding(660), s4 + 0.1, 0.9)
    put(a.ding(660), s4 + 0.35, 0.6)
    put(a.swish(), s4 + 0.3, 0.6)
    for at, pan in [(1.1, 0.5), (2.0, -0.5), (3.1, 0.5)]:
        put(a.blip(988, 0.08, 0.35), s4 + at, 1.0, pan=pan)
        put(a.blip(1319, 0.08, 0.25), s4 + at + 0.07, 1.0, pan=pan)
    put(a.buzzer(0.25), s4 + 1.15, 0.5)

    # 6. 쟁점: 시소 삐걱, 카드 팝
    put(a.swish(), s5 + 0.1, 0.6)
    put(a.pop(), s5 + 0.5, 0.6)
    for k in range(4):
        put(a._sweep(420, 380, 0.25) * a._decay(int(0.25 * a.SR), 0.1) * 0.12, s5 + 0.9 + k * 1.43, 1.0, pan=(-1) ** k * 0.5)
    put(a.boing(), s5 + 1.2, 0.7, pan=-0.5)
    put(a.boing(), s5 + 1.5, 0.7, pan=0.5)

    # 7. 마무리
    put(a.swish(), s6 + 0.1, 0.6)
    put(a.pop(), s6 + 0.8, 0.7, pan=-0.4)
    put(a.pop(), s6 + 1.0, 0.7, pan=0.4)
    put(a.chime(), s6 + 1.5, 0.7)

    mx.write(path, a.music(total, drums_in=s0 + 0.75, drums_out=s6 + 3.0, bpm=124,
                           progression=a.POP, style="pop"))


if __name__ == "__main__":
    _starts[:] = mv.scene_starts(SCENES)[0]
    mv.render(SCENES, OUT, sound, thumb_at=3.0, base=base, transition="slide")
