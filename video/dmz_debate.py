"""매일신문 기사 '김병주 모르면 입 좀 닥쳐요 vs 한동훈 시간 끌다 北 증거조작하면?'을
메신저 단톡방 화면처럼 재구성한 1080x1920 세로형 영상으로 만든다.

사용법: pip install pillow numpy imageio-ffmpeg && python3 video/dmz_debate.py
결과물: video/dmz-debate-news.mp4, video/dmz-debate-news-thumbnail.png
"""
import math
import os

from PIL import Image, ImageDraw

import audio
import make_video as mv
from make_video import W, H, clamp, ease, font

OUT = os.path.join(mv.HERE, "dmz-debate-news.mp4")

CHAT_BG = (178, 199, 218)
HEAD_BG = (170, 192, 212)
INK = (25, 25, 25)
SUB = (80, 88, 100)
WHITE = (255, 255, 255)
YELLOW = (254, 229, 0)
PILL = (0, 0, 0, 38)

TOP, BAR_H = 190, 150          # 채팅 영역: TOP ~ H - BAR_H
CHAT_BOTTOM = H - BAR_H - 30
MSG = ("r", 44)
LINE = 60
PROFILE = {"김병주": (150, 175, 215), "한동훈": (225, 165, 175)}

# (종류, 보낸 사람, 내용). 종류: date, sys, me, other, card
SCRIPT = [
    ("sys", None, "※ 보도된 발언을 재구성한 화면입니다"),
    ("date", None, "2026년 9월 21일 월요일"),
    ("me", None, "서부전선 DMZ에서 지뢰 추정 폭발이 있었어"),
    ("me", None, "간부 포함 장병 3명이 다쳤대"),
    ("other", "한동훈", "민주당 똥별"),
    ("other", "김병주", "'똥별'은 국가를 위해 평생을 헌신한 장성들을 비하하는 단어"),
    ("date", None, "2026년 9월 24일 목요일"),
    ("me", None, "군은 현장조사를 추석 이후로 잡았고, 한동훈 의원은 국방부 앞에서 1인 시위"),
    ("other", "한동훈", "'지뢰 폭발' 즉시 조사하라"),
    ("other", "한동훈", "비가 와서 증거 없어지면 당신들이 책임질 것인가"),
    ("other", "한동훈", "시간 끌다가 북한이 증거 조작하면 막을 수 있느냐"),
    ("date", None, "2026년 9월 25일 금요일"),
    ("other", "김병주", "정쟁을 이유로 우리 장병들을 지뢰가 깔린 밭으로 뛰어들라고 하나"),
    ("other", "김병주", "전투와 사고 현장 감식은 전혀 다른 일"),
    ("other", "김병주", "제발 모르면 입 좀 닥치고 있어요"),
    ("other", "한동훈", "똥별은 우리 군이 아니라 당신 같은 사람들을 말하는 것"),
    ("me", None, "결국 쟁점은 조사 타이밍"),
    ("me", None, "장병 안전이 먼저냐, 증거 확보가 먼저냐"),
    ("card", None, "김병주 '모르면 입 좀 닥쳐요' vs 한동훈 '시간 끌다 北 증거조작하면?'"),
]


def wrap(s, f, max_w):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
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


def type_time(s):
    return min(1.6, 0.4 + len(s) * 0.045)


def layout():
    """각 메시지의 등장 시각·위치·높이를 계산한다."""
    items, y, T, prev = [], TOP + 30, 0.8, None
    for kind, who, text in SCRIPT:
        it = {"kind": kind, "who": who, "text": text}
        if kind == "me":
            it["type_start"] = T
            T += type_time(text)
        it["t"] = T
        if kind in ("date", "sys"):
            h = 60
            y += 30
        elif kind == "card":
            it["rows"] = wrap(text, font("b", 42), 620)
            h = 170 + len(it["rows"]) * 56 + 90
        else:
            max_w = 700 if kind == "other" else 740
            it["rows"] = wrap(text, font(*MSG), max_w)
            h = len(it["rows"]) * LINE + 44
            it["first"] = kind == "other" and not (prev and prev["kind"] == "other" and prev["who"] == who)
            if it["first"]:
                h += 50
                y += 16
        it["y"], it["h"] = y, h
        y += h + 18
        items.append(it)
        # 다음 메시지까지 읽는 시간
        T += {"date": 0.7, "sys": 1.0}.get(kind, 0.9 + len(text) * 0.035)
        if kind == "card":
            T += 1.5
        prev = it
    return items, T


ITEMS, TOTAL = layout()


def scroll_at(T):
    bottom, prev = TOP, TOP
    for it in ITEMS:
        if it["t"] > T:
            break
        prev, bottom = bottom, it["y"] + it["h"]
        last_t = it["t"]
    if bottom == TOP:
        return 0
    b = prev + (bottom - prev) * ease((T - last_t) / 0.3)
    return max(0, b - CHAT_BOTTOM)


def base(T, total):
    img = Image.new("RGB", (W, H), CHAT_BG)
    return img, ImageDraw.Draw(img, "RGBA")


def profile_icon(d, x, y, who):
    col = PROFILE[who]
    s = 96
    d.rounded_rectangle((x, y, x + s, y + s), 36, fill=col)
    # 기본 프로필 실루엣
    d.ellipse((x + 30, y + 18, x + 66, y + 54), fill=(255, 255, 255, 230))
    d.chord((x + 16, y + 58, x + 80, y + 122), 180, 360, fill=(255, 255, 255, 230))


def bubble(d, x0, y0, x1, y1, fill, tail):
    d.rounded_rectangle((x0, y0, x1, y1), 26, fill=fill)
    if tail == "left":
        d.polygon([(x0 + 4, y0 + 14), (x0 - 16, y0 + 6), (x0 + 4, y0 + 40)], fill=fill)
    elif tail == "right":
        d.polygon([(x1 - 4, y0 + 14), (x1 + 16, y0 + 6), (x1 - 4, y0 + 40)], fill=fill)


def draw_item(d, it, y, p):
    dy = int(18 * (1 - p))
    y += dy
    kind = it["kind"]
    if kind in ("date", "sys"):
        f = font("r", 32)
        tw = d.textlength(it["text"], font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 28, y, W / 2 + tw / 2 + 28, y + 56), 28, fill=PILL)
        d.text((W / 2, y + 28), it["text"], font=f, fill=WHITE, anchor="mm")
        return
    f = font(*MSG)
    if kind == "other":
        bx = 160
        if it["first"]:
            profile_icon(d, 36, y, it["who"])
            d.text((bx, y), it["who"], font=font("r", 34), fill=SUB)
            y += 50
        tw = max(d.textlength(r, font=f) for r in it["rows"])
        bubble(d, bx, y, bx + tw + 52, y + it["h"] - (50 if it["first"] else 0), WHITE, "left" if it["first"] else None)
        for i, r in enumerate(it["rows"]):
            d.text((bx + 26, y + 20 + i * LINE), r, font=f, fill=INK)
    elif kind == "me":
        tw = max(d.textlength(r, font=f) for r in it["rows"])
        x1 = W - 40
        bubble(d, x1 - tw - 52, y, x1, y + it["h"], YELLOW, "right")
        for i, r in enumerate(it["rows"]):
            d.text((x1 - tw - 26, y + 20 + i * LINE), r, font=f, fill=INK)
    elif kind == "card":
        x1, x0 = W - 40, W - 40 - 700
        d.rounded_rectangle((x0, y, x1, y + it["h"]), 24, fill=WHITE)
        # 썸네일 영역
        d.rounded_rectangle((x0, y, x1, y + 150), 24, fill=(35, 38, 52))
        d.rectangle((x0, y + 120, x1, y + 150), fill=(35, 38, 52))
        d.text((x0 + 40, y + 75), "매일신문", font=font("x", 56), fill=WHITE, anchor="lm")
        d.text((x1 - 40, y + 75), "정치", font=font("b", 34), fill=(170, 175, 190), anchor="rm")
        yy = y + 180
        for r in it["rows"]:
            d.text((x0 + 36, yy), r, font=font("b", 42), fill=INK)
            yy += 56
        d.text((x0 + 36, yy + 20), "imaeil.com", font=font("r", 32), fill=(140, 140, 150))


def chrome(d, T):
    # 상단 바
    d.rectangle((0, 0, W, TOP), fill=HEAD_BG)
    d.text((60, 30), "9:41", font=font("b", 34), fill=INK)
    d.rounded_rectangle((W - 130, 36, W - 70, 64), 6, outline=INK, width=3)
    d.rectangle((W - 126, 40, W - 86, 60), fill=INK)
    d.line((50, 125, 80, 100), fill=INK, width=6)
    d.line((50, 125, 80, 150), fill=INK, width=6)
    d.text((120, 125), "DMZ 지뢰 공방", font=font("b", 46), fill=INK, anchor="lm")
    tw = d.textlength("DMZ 지뢰 공방", font=font("b", 46))
    d.text((140 + tw, 127), "3", font=font("r", 40), fill=SUB, anchor="lm")
    # 검색·메뉴 아이콘
    d.ellipse((W - 220, 100, W - 180, 140), outline=INK, width=5)
    d.line((W - 186, 134, W - 170, 150), fill=INK, width=6)
    for k in range(3):
        d.line((W - 120, 105 + k * 18, W - 76, 105 + k * 18), fill=INK, width=5)
    # 하단 입력창
    y0 = H - BAR_H
    d.rectangle((0, y0, W, H), fill=WHITE)
    d.line((58, y0 + 60, 98, y0 + 60), fill=(150, 150, 150), width=5)
    d.line((78, y0 + 40, 78, y0 + 80), fill=(150, 150, 150), width=5)
    box = (130, y0 + 22, W - 150, y0 + 98)
    d.rounded_rectangle(box, 38, fill=(245, 245, 245))
    typing = ""
    for it in ITEMS:
        if it["kind"] == "me" and it["type_start"] <= T < it["t"]:
            n = int(len(it["text"]) * clamp((T - it["type_start"]) / (it["t"] - it["type_start"] - 0.15)))
            typing = it["text"][:n]
    f = font("r", 40)
    if typing:
        shown = typing
        while d.textlength(shown, font=f) > box[2] - box[0] - 80:
            shown = shown[1:]
        d.text((box[0] + 34, y0 + 60), shown, font=f, fill=INK, anchor="lm")
        cx = box[0] + 38 + d.textlength(shown, font=f)
        if int(T * 3) % 2 == 0:
            d.line((cx, y0 + 38, cx, y0 + 82), fill=INK, width=3)
    # 전송 버튼
    d.rounded_rectangle((W - 130, y0 + 22, W - 40, y0 + 98), 30, fill=YELLOW if typing else (235, 235, 235))
    d.polygon([(W - 102, y0 + 44), (W - 62, y0 + 60), (W - 102, y0 + 76), (W - 94, y0 + 60)],
              fill=INK if typing else (180, 180, 180))


def s_chat(d, t, dur):
    sc = scroll_at(t)
    for it in ITEMS:
        if it["t"] > t:
            break
        y = it["y"] - sc
        if y + it["h"] < TOP - 80 or y > H:
            continue
        draw_item(d, it, y, ease((t - it["t"]) / 0.25))
    chrome(d, t)


SCENES = [(s_chat, TOTAL)]


def sound(starts, total, path):
    a = audio
    mx = a.Mixer(total)
    put = mx.put
    for it in ITEMS:
        t, kind = it["t"], it["kind"]
        if kind == "me":
            # 타자 소리
            k = it["type_start"]
            while k < t - 0.15:
                put(a.tick(2600 + 400 * math.sin(k * 37), 0.015, 0.08), k, 1.0, pan=0.3)
                k += 0.07 + 0.03 * abs(math.sin(k * 13))
            put(a.blip(1200, 0.06, 0.18), t, 1.0, pan=0.3)
        elif kind == "other":
            put(a.blip(784, 0.07, 0.3), t, 1.0, pan=-0.2)
            put(a.blip(1175, 0.08, 0.22), t + 0.08, 1.0, pan=-0.2)
        elif kind == "card":
            put(a.blip(1200, 0.06, 0.18), t, 1.0)
            put(a.chime(), t + 0.3, 0.35)
        else:
            put(a.swish(0.3), t, 0.4)
    # 잔잔한 배경음 (Fmaj7 - Em7 - Dm7 - Cmaj7 느낌)
    prog = ([[57, 60, 64], [55, 59, 62], [53, 57, 60], [52, 55, 59]], [41, 40, 38, 36])
    bgm = a.music(total, drums_in=1.0, drums_out=total - 1.5, bpm=88, progression=prog, style="pop") * 0.6
    mx.write(path, bgm)


if __name__ == "__main__":
    mv.render(SCENES, OUT, sound, thumb_at=TOTAL - 1.0, base=base)
