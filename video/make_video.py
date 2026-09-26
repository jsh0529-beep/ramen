"""매일신문 기사 'AI 안경으로 성관계 몰카·시험 부정행위…규제는 뒷북'(2026-09-26)을
1080x1920 세로형 요약 영상으로 만든다.

사용법: pip install pillow imageio-ffmpeg && python3 video/make_video.py
결과물: video/ai-glasses-news.mp4
"""
import os
import subprocess
import tempfile

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ai-glasses-news.mp4")
W, H = 1080, 1920
SLIDE_SEC = 6.0
FADE_SEC = 0.6
FPS = 30

BG_TOP = (14, 17, 28)
BG_BOTTOM = (34, 18, 30)
ACCENT = (255, 94, 77)
TEXT = (245, 245, 250)
MUTED = (160, 165, 185)
CARD = (255, 255, 255, 18)


def font(weight, size):
    name = {"r": "NanumGothic.ttf", "b": "NanumGothicBold.ttf", "x": "NanumGothicExtraBold.ttf"}[weight]
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def wrap(draw, text, fnt, max_w):
    """한글은 글자 단위, 공백 우선으로 줄바꿈."""
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if draw.textlength(trial, font=fnt) <= max_w:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            cur = ""
            for ch in word:
                if draw.textlength(cur + ch, font=fnt) > max_w:
                    lines.append(cur)
                    cur = ""
                cur += ch
        lines.append(cur)
    return lines


def base(idx, total):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        c = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(img, "RGBA")
    # 장식용 원
    d.ellipse((620, -260, 1400, 520), fill=(255, 94, 77, 22))
    d.ellipse((-300, 1500, 400, 2200), fill=(90, 110, 255, 18))
    # 상단 헤더
    d.rectangle((80, 150, 92, 200), fill=ACCENT)
    d.text((112, 150), "이슈 브리핑", font=font("x", 40), fill=TEXT)
    d.text((112, 206), "매일신문 · 2026.09.26", font=font("r", 30), fill=MUTED)
    # 하단 진행 표시
    seg = (W - 160) / total
    for i in range(total):
        x0 = 80 + i * seg + 6
        d.rounded_rectangle((x0, 1790, x0 + seg - 12, 1800), 5,
                            fill=ACCENT if i <= idx else (255, 255, 255, 40))
    return img, d


def text_block(d, y, text, fnt, fill, max_w=W - 160, gap=1.35, x=80):
    for line in wrap(d, text, fnt, max_w):
        d.text((x, y), line, font=fnt, fill=fill)
        y += int(fnt.size * gap)
    return y


def slide_title(idx, total):
    img, d = base(idx, total)
    d.text((80, 560), "AI 안경", font=font("x", 150), fill=ACCENT)
    y = text_block(d, 760, "성관계 몰카·\n시험 부정행위…", font("x", 96), TEXT, gap=1.3)
    y = text_block(d, y + 30, "규제는 뒷북", font("x", 96), TEXT)
    d.rectangle((80, y + 50, 240, y + 58), fill=ACCENT)
    text_block(d, y + 100, "카메라 달린 스마트안경 'AI 글라스'가\n불법 촬영과 부정행위에 악용되자\n정부가 뒤늦게 규제에 나섰다", font("r", 44), MUTED, gap=1.5)
    return img


def slide_market(idx, total):
    img, d = base(idx, total)
    y = text_block(d, 400, "AI 글라스,\n폭발적 성장", font("x", 92), TEXT, gap=1.25)
    text_block(d, y + 20, "전 세계 출하량", font("r", 42), MUTED)
    bars = [("지난해", 870, "870만 대"), ("올해(전망)", 1500, "1,500만 대"), ("2030년(전망)", 3500, "3,500만 대")]
    top = y + 140
    max_len = W - 160 - 20
    for i, (label, v, txt) in enumerate(bars):
        by = top + i * 250
        d.text((80, by), label, font=font("b", 40), fill=MUTED)
        bw = int(max_len * v / 3500)
        d.rounded_rectangle((80, by + 64, 80 + bw, by + 144), 16, fill=ACCENT if i == 0 else (255, 94, 77, 150 - i * 30))
        tw = d.textlength(txt, font=font("x", 48))
        tx = 80 + bw + 24 if 80 + bw + 24 + tw < W - 60 else 80 + bw - tw - 24
        d.text((tx, by + 78), txt, font=font("x", 48), fill=TEXT)
    d.rounded_rectangle((80, top + 790, W - 80, top + 920), 24, fill=CARD)
    d.text((120, top + 826), "지난해 출하량 전년 대비  +322%", font=font("x", 52), fill=ACCENT)
    return img


def bullets_slide(title, items, idx, total, footer=None):
    img, d = base(idx, total)
    y = text_block(d, 380, title, font("x", 88), TEXT, gap=1.25) + 60
    for head, body in items:
        head_h = len(wrap(d, head, font("x", 50), W - 260)) * int(50 * 1.35)
        body_h = len(wrap(d, body, font("r", 40), W - 260)) * int(40 * 1.45)
        bottom = y + 40 + head_h + 6 + body_h + 30
        d.rounded_rectangle((80, y, W - 80, bottom), 28, fill=CARD)
        d.rectangle((80, y + 40, 90, y + 40 + head_h - 12), fill=ACCENT)
        t = text_block(d, y + 40, head, font("x", 50), ACCENT, max_w=W - 260, x=130)
        text_block(d, t + 6, body, font("r", 40), TEXT, max_w=W - 260, x=130, gap=1.45)
        y = bottom + 50
    if footer:
        text_block(d, y + 10, footer, font("b", 40), MUTED)
    return img


def slide_exam(idx, total):
    return bullets_slide("시험장이\n뚫렸다", [
        ("토익", "5월 2명, 6월 1명 적발\n시험지를 촬영해 외부와 통신"),
        ("텝스", "4월, 생성형 AI 스마트안경 쓴\n20대 수험생 적발"),
        ("국가기술자격시험", "광주 소방설비기사 시험 40대 적발\n→ AI 안경 부정행위 첫 약식기소"),
    ], idx, total)


def slide_privacy(idx, total):
    return bullets_slide("몰래 찍는 눈", [
        ("성관계 몰카", "7월, 상대 동의 없이 AI 글라스로\n성관계 장면 촬영한 남성 입건"),
        ("표시등 무력화", "촬영 알림 LED를 스티커로 가리거나\n개조하는 방법이 온라인에 확산"),
        ("제조사 조치", "메타, 표시등 훼손된 수천 대의\n카메라 기능 영구 비활성화"),
    ], idx, total)


def slide_policy(idx, total):
    return bullets_slide("뒤늦은 대책", [
        ("고용노동부", "시험장 소지·사용 시 부정행위 처리\n국가기술자격법 시행규칙 개정 추진"),
        ("교육부", "시험장 반입 금지 물품 포함 공문\n수능 부정 시 최소 2년 응시 제한 검토"),
        ("과기정통부", "AI 글라스 안전 기준·가이드라인 마련\n촬영 표시등 강화 등 기술 지원 논의"),
    ], idx, total)


def slide_end(idx, total):
    img, d = base(idx, total)
    y = text_block(d, 640, "기술은 이미\n일상에 들어왔다", font("x", 92), TEXT, gap=1.3)
    y = text_block(d, y + 40, "규제는 한발 늦었다", font("x", 92), ACCENT)
    text_block(d, y + 80, "편리함과 프라이버시 사이,\n실효성 있는 안전장치가 필요하다", font("r", 46), MUTED, gap=1.5)
    d.text((80, 1680), "출처: 매일신문(2026.09.26) 외 관련 보도 종합", font=font("r", 30), fill=MUTED)
    return img


SLIDES = [slide_title, slide_market, slide_exam, slide_privacy, slide_policy, slide_end]


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    n = len(SLIDES)
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for i, fn in enumerate(SLIDES):
            p = os.path.join(tmp, f"s{i}.png")
            fn(i, n).save(p)
            paths.append(p)

        cmd = [ff, "-y", "-loglevel", "error"]
        for p in paths:
            cmd += ["-loop", "1", "-t", str(SLIDE_SEC), "-framerate", str(FPS), "-i", p]
        total = n * SLIDE_SEC - (n - 1) * FADE_SEC
        # 잔잔한 배경음 (A단조 화음 패드)
        pad = ("0.05*sin(2*PI*220*t)+0.04*sin(2*PI*261.63*t)+0.035*sin(2*PI*329.63*t)"
               "+0.03*sin(2*PI*110*t)")
        pad = f"({pad})*(0.75+0.25*sin(2*PI*0.2*t))"
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", f"aevalsrc='{pad}':s=44100:c=stereo"]

        # 각 슬라이드: 약한 줌인 효과 후 크로스페이드
        chains, last = [], None
        frames = int(SLIDE_SEC * FPS)
        for i in range(n):
            chains.append(
                f"[{i}:v]scale={W*2}:{H*2},zoompan=z='1+0.04*on/{frames}':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
                f"format=yuv420p,setsar=1[v{i}]")
        last = "v0"
        for i in range(1, n):
            off = i * (SLIDE_SEC - FADE_SEC)
            out = f"x{i}"
            chains.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE_SEC}:offset={off:.2f}[{out}]")
            last = out
        chains.append(f"[{n}:a]afade=t=in:d=1.5,afade=t=out:st={total-2:.2f}:d=2,volume=0.8[a]")
        cmd += ["-filter_complex", ";".join(chains), "-map", f"[{last}]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", OUT]
        subprocess.run(cmd, check=True)
        # 미리보기용 썸네일
        Image.open(paths[0]).save(os.path.join(HERE, "thumbnail.png"))
    print("저장:", OUT)


if __name__ == "__main__":
    main()
