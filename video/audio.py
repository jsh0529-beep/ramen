"""영상용 배경음악과 효과음을 numpy로 합성한다 (외부 음원 없음)."""
import wave

import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def _t(sec):
    return np.arange(int(sec * SR)) / SR


def _decay(n, sec):
    return np.exp(-np.arange(n) / (sec * SR))


def _lowpass(x, alpha):
    """단순 1극 로우패스. alpha는 스칼라 또는 샘플별 배열(0~1, 클수록 밝음)."""
    y = np.empty_like(x)
    a = np.broadcast_to(alpha, x.shape)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _highpass(x):
    return np.diff(x, prepend=0.0)


def _sweep(f0, f1, sec):
    f = np.geomspace(f0, f1, int(sec * SR))
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def _note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# ---- 효과음 ----
def whoosh(sec=0.55):
    n = int(sec * SR)
    x = rng.standard_normal(n)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    cutoff = 0.02 + 0.25 * np.sin(np.pi * np.linspace(0, 1, n)) ** 3
    return _lowpass(x, cutoff) * shape * 0.9


def swish(sec=0.3):
    n = int(sec * SR)
    x = _highpass(rng.standard_normal(n))
    return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 3 * 0.08


def pop():
    s = _sweep(380, 950, 0.09) * _decay(int(0.09 * SR), 0.03)
    return s * 0.8


def tick(f=2200, sec=0.025, v=0.35):
    t = _t(sec)
    return np.sin(2 * np.pi * f * t) * _decay(len(t), sec / 4) * v


def stamp():
    n = int(0.6 * SR)
    body = _sweep(140, 38, 0.6) * _decay(n, 0.12)
    noise = _lowpass(rng.standard_normal(n), 0.08) * _decay(n, 0.05) * 2
    return (body + noise) * 0.9


def ding(f=1318.5):
    t = _t(1.6)
    x = (np.sin(2 * np.pi * f * t) * _decay(len(t), 0.5)
         + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * _decay(len(t), 0.18)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * _decay(len(t), 0.08))
    return x * 0.35


def chime():
    out = np.zeros(int(1.9 * SR))
    for k, m in enumerate([76, 79, 84]):
        d = ding(_note(m))
        o = int(k * 0.09 * SR)
        out[o:o + len(d)] += d * 0.8
    return out


def shutter():
    def click(sec):
        n = int(sec * SR)
        return _highpass(rng.standard_normal(n)) * _decay(n, sec / 5)
    out = np.zeros(int(0.2 * SR))
    a, b = click(0.04), click(0.06)
    out[:len(a)] += a * 0.35
    o = int(0.075 * SR)
    out[o:o + len(b)] += b * 0.3
    return out


def beep(f=1000, sec=0.12, v=0.18):
    t = _t(sec)
    env = np.minimum(1, np.minimum(t / 0.005, (sec - t) / 0.01))
    return np.sin(2 * np.pi * f * t) * env * v


def rise(sec=1.2):
    n = int(sec * SR)
    return _sweep(250, 900, sec) * np.linspace(0, 1, n) ** 1.5 * (1 - np.linspace(0, 1, n) ** 8) * 0.35


def knock():
    n = int(0.25 * SR)
    return (_sweep(260, 120, 0.25) * _decay(n, 0.04) + _lowpass(rng.standard_normal(n), 0.3) * _decay(n, 0.01)) * 0.5


def clock_tick(high):
    n = int(0.05 * SR)
    x = _highpass(rng.standard_normal(n)) * _decay(n, 0.006)
    return x * (0.1 if high else 0.07)


def boom():
    n = int(2.2 * SR)
    body = _sweep(90, 28, 2.2) * _decay(n, 0.5)
    rumble = _lowpass(rng.standard_normal(n), 0.01) * _decay(n, 0.6) * 6
    return (body + rumble) * 0.9


def blip(f=880, sec=0.09, v=0.3):
    """메신저 알림처럼 짧게 올라가는 음."""
    return _sweep(f, f * 1.5, sec) * _decay(int(sec * SR), sec / 3) * v


def boing():
    n = int(0.35 * SR)
    f = 300 + 250 * np.sin(np.linspace(0, 3 * np.pi, n)) * np.exp(-np.linspace(0, 4, n))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _decay(n, 0.12) * 0.5


def buzzer(sec=0.35):
    t = _t(sec)
    sq = np.sign(np.sin(2 * np.pi * 150 * t)) + 0.5 * np.sign(np.sin(2 * np.pi * 155 * t))
    env = np.minimum(1, (sec - t) / 0.05)
    return _lowpass(sq * env, 0.15) * 0.3


# ---- 배경음악 ----
# Am - F - Dm - E (긴장감 있는 뉴스 톤)
TENSE = ([[57, 60, 64], [53, 57, 60], [50, 53, 57], [52, 56, 59]], [45, 41, 38, 40])


# C - G - Am - F (밝은 팝)
POP = ([[60, 64, 67], [59, 62, 67], [57, 60, 64], [57, 60, 65]], [36, 43, 45, 41])


def music(total, drums_in, drums_out, bpm=104, progression=TENSE, style="news"):
    """style="pop"이면 4비트 킥·박수·아르페지오가 들어간 경쾌한 트랙."""
    n = int(total * SR)
    out = np.zeros(n)
    beat = 60 / bpm
    bar = beat * 4
    chords, roots = progression

    # 패드
    t = _t(total)
    pad = np.zeros(n)
    for b in range(int(total / bar) + 1):
        c = chords[b % 4]
        s0, s1 = int(b * bar * SR), min(n, int((b + 1) * bar * SR))
        tt = t[s0:s1] - b * bar
        seg = np.zeros(s1 - s0)
        for m in c:
            f = _note(m)
            for det in (-0.6, 0.6):
                seg += np.sin(2 * np.pi * (f + det) * tt) + 0.3 * np.sin(2 * np.pi * 2 * (f + det) * tt)
        edge = np.minimum(1, np.minimum(tt / 0.25, (bar - tt) / 0.25))
        pad[s0:s1] = seg * edge
    pad = _lowpass(pad, 0.08) * 0.05
    out += pad * (0.8 + 0.2 * np.sin(2 * np.pi * 0.25 * t))

    def put(x, at, v=1.0):
        i = int(at * SR)
        if i >= n:
            return
        j = min(n, i + len(x))
        out[i:j] += x[:j - i] * v

    step = beat / 2
    k_n = int(0.4 * SR)
    kick = _sweep(150, 45, 0.4) * _decay(k_n, 0.09)
    h_n = int(0.06 * SR)
    for i in range(int(total / step)):
        at = i * step
        b = int(at / bar)
        # 베이스 (8분음표 펄스)
        if at < drums_out + 1:
            f = _note(roots[b % 4])
            bt = _t(step * 0.9)
            bs = sum(np.sin(2 * np.pi * f * h * bt) / h for h in range(1, 6))
            put(bs * _decay(len(bt), 0.12), at, 0.07 if at >= drums_in else 0.03)
        if not (drums_in <= at < drums_out):
            continue
        hat = _highpass(_highpass(rng.standard_normal(h_n))) * _decay(h_n, 0.012)
        clap = _lowpass(rng.standard_normal(int(0.18 * SR)), 0.4) * _decay(int(0.18 * SR), 0.04)
        if style == "pop":
            if i % 2 == 0:
                put(kick, at, 0.5)
            if i % 4 == 2:
                put(clap, at, 0.3)
            put(hat, at, 0.12 if i % 2 else 0.03)
            # 반짝이는 아르페지오
            c = chords[b % 4]
            m = c[i % 3] + 12 + (12 if i % 8 >= 6 else 0)
            pt = _t(step * 0.8)
            f = _note(m)
            pl = (np.sin(2 * np.pi * f * pt) + 0.3 * np.sin(2 * np.pi * 2 * f * pt)) * _decay(len(pt), 0.07)
            put(pl, at, 0.05)
            continue
        if i % 4 == 0:
            put(kick, at, 0.55)
        if i % 4 == 2 and i % 8 == 6:
            put(clap, at, 0.25)
        put(hat, at, 0.09 if i % 2 else 0.04)
    fade = np.ones(n)
    fi, fo = int(1.0 * SR), int(2.5 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    return out * fade


class Mixer:
    def __init__(self, total):
        self.total = total
        self.n = int(total * SR)
        self.sfx = np.zeros((self.n, 2))

    def put(self, x, at, v=1.0, pan=0.0):
        n, sfx = self.n, self.sfx
        i = int(at * SR)
        if i < 0 or i >= n:
            return
        j = min(n, i + len(x))
        l, r = np.sqrt((1 - pan) / 2), np.sqrt((1 + pan) / 2)
        sfx[i:j, 0] += x[:j - i] * v * l * 1.41
        sfx[i:j, 1] += x[:j - i] * v * r * 1.41

    def write(self, path, bgm):
        mix = self.sfx + bgm[:, None]
        mix = np.tanh(mix * 1.2) / np.tanh(1.2)
        mix /= max(1e-9, np.abs(mix).max()) / 0.9
        data = (mix * 32767).astype("<i2")
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(data.tobytes())


def build(starts, total, path):
    """AI 안경 영상용: 장면 애니메이션 타이밍에 맞춰 효과음 배치."""
    mx = Mixer(total)

    put = mx.put

    s0, s1, s2, s3, s4, s5 = starts
    # 장면 전환 휙
    for s in starts[1:]:
        put(whoosh(), s - 0.35, 0.5, pan=0.3)

    # 1. 타이틀
    put(shutter(), s0 + 0.15, 0.8)
    put(pop(), s0 + 0.25, 0.7)
    for k, at in enumerate([0.5, 0.8, 1.0, 1.3]):
        put(swish(), s0 + at, 0.6, pan=-0.3 + 0.2 * k)
    put(swish(0.45), s0 + 1.6, 0.8, pan=0.4)
    put(stamp(), s0 + 2.35, 1.0)
    for k in range(3):
        put(swish(), s0 + 2.6 + 0.15 * k, 0.4)

    # 2. 시장 성장: 막대 상승음 + 숫자 카운트 틱 + 차임
    for k in range(3):
        st = s1 + 0.6 + 0.5 * k
        put(rise(), st, 0.9, pan=-0.2 + 0.2 * k)
        for q in range(10):
            put(tick(1800 + 150 * k + 40 * q), st + q * 0.1, 0.5)
    put(chime(), s1 + 2.65, 0.9)

    # 3. 시험장: 스캐너 삐 + 카드 휙 + 판사봉
    for q in range(10):
        put(beep(1400, 0.04, 0.08), s2 + 0.3 + q * 0.6)
    for k, at in enumerate([0.8, 1.4, 2.0]):
        put(swish(0.35), s2 + at, 0.9, pan=0.5)
    put(buzzer(), s2 + 1.0, 0.8)
    put(knock(), s2 + 2.3, 1.0)
    put(knock(), s2 + 2.5, 0.8)

    # 4. 몰래 찍는 눈: 셔터 + 녹화 삐 + 카드
    put(shutter(), s3 + 0.05, 1.0)
    put(beep(1000, 0.15, 0.2), s3 + 0.25)
    for q in range(1, 7):
        put(beep(1000, 0.05, 0.06), s3 + q)
    for k, at in enumerate([0.7, 1.3, 1.9]):
        put(swish(0.35), s3 + at, 0.9, pan=0.5)
    put(shutter(), s3 + 0.9, 0.6)
    put(shutter(), s3 + 1.5, 0.5)

    # 5. 뒤늦은 대책: 시계 초침 + 카드
    q = 0
    at = 0.3
    while at < 6.7:
        put(clock_tick(q % 2 == 0), s4 + at, 0.9)
        q += 1
        at += 0.35
    for k, at in enumerate([0.6, 1.2, 1.8]):
        put(swish(0.35), s4 + at, 0.9, pan=0.5)
        put(pop(), s4 + at + 0.25, 0.3)

    # 6. 마무리: 팝 + 금지 표시 붐 + 텍스트
    put(pop(), s5 + 0.15, 0.7)
    put(boom(), s5 + 0.8, 1.0)
    put(buzzer(0.5), s5 + 0.8, 0.6)
    for at in [1.0, 1.2, 1.6, 2.2, 2.4]:
        put(swish(), s5 + at, 0.5)

    mx.write(path, music(total, drums_in=s0 + 2.35, drums_out=s5 + 0.8))


# ---- 클래식풍 배경음 (피아노 아르페지오 + 현악 패드) ----
def piano(midi, sec=2.2, v=1.0):
    f = _note(midi)
    t = _t(sec)
    x = np.zeros(len(t))
    for k in range(1, 7):
        x += np.sin(2 * np.pi * f * k * t * (1 + 0.0004 * k * k)) / k ** 1.6 * np.exp(-t * (1.2 + 0.9 * k))
    att = np.minimum(1, t / 0.004)
    return x * att * v * 0.5


def strings(midis, sec):
    t = _t(sec)
    x = np.zeros(len(t))
    for m in midis:
        f = _note(m)
        for det in (-0.35, 0.0, 0.35):
            vib = 0.004 * np.sin(2 * np.pi * 5.2 * t)
            ph = 2 * np.pi * np.cumsum(f * (1 + det / 100 + vib)) / SR
            x += sum(np.sin(k * ph) / k for k in range(1, 6))
    env = np.minimum(1, np.minimum(t / 0.9, (sec - t) / 0.9))
    return _lowpass(x * env, 0.05) * 0.018


# D - Bm - G - A (품격 있는 장조 진행)
NOBLE = ([[62, 66, 69], [59, 62, 66], [55, 59, 62], [57, 61, 64]], [38, 35, 31, 33])


def elegant_music(total, bar=3.4, progression=NOBLE):
    n = int(total * SR)
    out = np.zeros(n)
    chords, roots = progression

    def put(x, at, v=1.0):
        i = int(at * SR)
        if i < 0:
            x, i = x[-i:], 0
        if i >= n:
            return
        j = min(n, i + len(x))
        out[i:j] += x[:j - i] * v

    nbars = int(total / bar) + 1
    for b in range(nbars):
        c, r = chords[b % 4], roots[b % 4]
        at = b * bar
        put(strings([m - 12 for m in c], bar + 0.9), at - 0.45, 1.0)
        put(piano(r, 3.5), at, 0.9)
        put(piano(r + 12, 3.0), at, 0.4)
        # 오르내리는 아르페지오 (8분음표)
        seq = [c[0], c[1], c[2], c[0] + 12, c[1] + 12, c[0] + 12, c[2], c[1]]
        step = bar / 8
        for i, m in enumerate(seq):
            put(piano(m, 2.2), at + i * step, 0.55 if i % 4 == 0 else 0.4)
        # 두 마디마다 고음 멜로디 한 음
        if b % 2 == 1:
            put(piano(c[2] + 24, 2.5), at + bar * 0.5, 0.25)
    fade = np.ones(n)
    fi, fo = int(2.0 * SR), int(3.0 * SR)
    fade[:fi] = np.linspace(0, 1, fi)
    fade[-fo:] = np.linspace(1, 0, fo)
    return out * fade


def jet_pass(sec=3.0):
    """멀리서 다가왔다 지나가는 제트기 소리."""
    n = int(sec * SR)
    x = _lowpass(rng.standard_normal(n), 0.04 + 0.08 * np.sin(np.pi * np.linspace(0, 1, n)) ** 2)
    return x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 1.5


def timpani(midi=38):
    n = int(2.0 * SR)
    f = _note(midi)
    t = _t(2.0)
    body = np.sin(2 * np.pi * f * t) * _decay(n, 0.6) + 0.4 * np.sin(2 * np.pi * f * 1.5 * t) * _decay(n, 0.3)
    hit = _lowpass(rng.standard_normal(n), 0.1) * _decay(n, 0.02)
    return (body + hit) * 0.5
