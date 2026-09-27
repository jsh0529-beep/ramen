"""'요즘 버전' 쇼릴 사운드트랙: 140BPM 저지 클럽풍 (numpy 합성) → young/soundtrack.wav
타이밍은 young/scene.html 과 같다. 1박 = 60/140 s, 1마디 = 4박."""
import os
import wave
import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
B = 60 / 140
BAR = 4 * B
rng = np.random.default_rng(140)
drums = np.zeros((N, 2))
music = np.zeros((N, 2))
fx = np.zeros((N, 2))
duck = np.ones(N)


def bar(x):
    return x * BAR


def ts(d):
    return np.arange(int(SR * d)) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def filt(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    if lo:
        X *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        X *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X, len(x))


def put(bus, sig, t0, g=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if i0 >= N or i0 < 0:
        return
    sig = sig[: N - i0]
    l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
    bus[i0:i0 + len(sig), 0] += sig * g * l
    bus[i0:i0 + len(sig), 1] += sig * g * r


def sidechain(t0, depth=.2, length=.16):
    i0 = int(t0 * SR)
    n = min(int(length * SR), N - i0)
    if n > 0:
        duck[i0:i0 + n] = np.minimum(duck[i0:i0 + n], np.linspace(depth, 1, n) ** 1.3)


# ── 음색 ──
def kick():
    t = ts(.35)
    s = np.sin(2 * np.pi * (50 * t + 170 / 35 * (1 - np.exp(-t * 35)))) * np.exp(-t * 9)
    return np.tanh(s * 2.2 + filt(rng.standard_normal(len(t)), 2500) * np.exp(-t * 250) * .4) * .8


def clap():
    t = ts(.3)
    n = filt(rng.standard_normal(len(t)), 1000, 8000)
    env = sum(np.exp(-np.maximum(t - d, 0) * 70) * (t >= d) for d in (0, .007, .015)) / 3 + np.exp(-t * 16) * .5
    return n * env * .6


def hat(o=False):
    t = ts(.22 if o else .04)
    return filt(rng.standard_normal(len(t)), 8000) * np.exp(-t * (14 if o else 110)) * .22


def e808(n, dur, glide=0):
    t = ts(dur)
    f = midi(n) * (1 + glide * np.exp(-t * 12))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.tanh(np.sin(ph) * 2.5) * np.minimum(1, t / .004) * np.exp(-t * 1.4) * np.minimum(1, (dur - t) / .02)
    return s * .5


def saw(f, t):
    s = np.zeros_like(t)
    k = 1
    while k * f < 12000 and k < 30:
        s += np.sin(2 * np.pi * f * k * t) / k
        k += 1
    return s * .6


def pluck(n, dur=.3, bright=7000):
    t = ts(dur)
    s = (saw(midi(n), t) + saw(midi(n) * 1.004, t)) * .5 * np.exp(-t * 11)
    return filt(s, 250, bright) * .5


def pad(notes, dur):
    t = ts(dur)
    s = sum(saw(midi(n) * (1 + d), t) for n in notes for d in (-.003, .003))
    env = np.minimum(1, t / .05) * np.minimum(1, (dur - t) / .2)
    return filt(s * env / (2 * len(notes)), 200, 3000) * .5


def ding(f=1318, dur=.5):
    t = ts(dur)
    return (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 8)) * np.exp(-t * 7) * .3


def popfx():
    t = ts(.12)
    return np.sin(2 * np.pi * (300 + 900 * t / .12) * t) * np.exp(-t * 30) * .5


def type_tick():
    t = ts(.03)
    return filt(rng.standard_normal(len(t)), 2000, 9000) * np.exp(-t * 300) * .35


def swoosh(dur=.3, up=True):
    t = ts(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = int(SR * .015)
    for i in range(0, len(t), seg):
        k = i / len(t)
        c = 500 * (16 ** (k if up else 1 - k))
        out[i:i + seg] = filt(n[i:i + seg * 2], c * .6, c * 2.5)[:len(n[i:i + seg])]
    return out * np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2 * .6


def riser(dur):
    t = ts(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = int(SR * .04)
    for i in range(0, len(t), seg):
        c = 300 * (40 ** (i / len(t)))
        out[i:i + seg] = filt(n[i:i + seg * 2], c * .5, c * 2)[:len(n[i:i + seg])]
    return out * (t / dur) ** 2 * .4


def impact():
    t = ts(1.8)
    s = np.sin(2 * np.pi * (35 + 100 * np.exp(-t * 9)) * t) * np.exp(-t * 2.2)
    s += filt(rng.standard_normal(len(t)), 80, 5000) * np.exp(-t * 6) * .5
    return np.tanh(s * 1.6) * .8


def scratch():
    t = ts(.25)
    n = rng.standard_normal(len(t))
    return filt(n, 1500, 6000) * (np.abs(np.sin(2 * np.pi * 22 * t)) ** 3) * .5


# 코드 진행 (A단조 느낌의 밝은 진행): Fmaj7 - G - Am - Em
CH = [([53, 57, 60, 64], 41), ([55, 59, 62, 67], 43), ([57, 60, 64, 69], 45), ([52, 55, 59, 64], 40)]
MEL = [76, 74, 72, 74, 76, 79, 76, 72]   # 8분 플럭 멜로디 (마디마다 조금씩 바뀜)

# 저지 클럽 킥 패턴 (16분 격자): 1, 2, 3, 3+, 4+ 느낌의 바운스
KICKS = [0, 4, 8, 10, 13]


def groove(b0, b1, *, full=True, melody=True, hats=True, kicks=True):
    for bi in range(b0, b1):
        t0 = bar(bi)
        chord, root = CH[bi % 4]
        if kicks:
            for s in KICKS + ([14] if bi % 2 else []):
                tk = t0 + s * B / 4
                put(drums, kick(), tk, 1.0)
                sidechain(tk)
            put(drums, clap(), t0 + B, .8)
            put(drums, clap(), t0 + 3 * B, .8)
            if bi % 2:
                put(drums, clap(), t0 + 3.75 * B, .45)
        if hats:
            for s in range(8):
                put(drums, hat(), t0 + s * B / 2 + B / 4, .7, .3)
            if bi % 4 == 3:  # 셋잇단 롤
                for s in range(6):
                    put(drums, hat(), t0 + 3 * B + s * B / 6, .5, -.3)
        # 808
        put(music, e808(root - 12, B * 1.4, glide=.6), t0, 1.0)
        put(music, e808(root - 12 + (7 if bi % 2 else 12), B * .9), t0 + 2.5 * B, .8)
        if full:
            put(music, pad(chord, BAR * .98), t0, .45)
        if melody:
            for s in range(8):
                n = MEL[(s + bi * 3) % 8] - (0 if bi % 4 < 2 else 2)
                if (s + bi) % 3 != 2:
                    put(music, pluck(n), t0 + s * B / 2, .5, (s % 2 - .5) * .6)


# ── 0 ~ 1마디: 잠금화면 — 알림음 + 필터 걸린 인트로 ──
for i in range(3):
    put(fx, ding([1318, 1568, 1760][i]), (i + 1) * B, .9)
put(music, pad(CH[0][0], BAR), 0, .35)
put(fx, riser(BAR * .9), BAR * .1, .8)

# ── 1 ~ 16마디: 본 비트 ──
put(fx, impact(), bar(1), 1.0)
groove(1, 4, full=True, melody=False)            # POV, 신문=아재→힙
put(fx, scratch(), bar(1) + 2 * B, .8)            # "안 봄?" 글리치
put(fx, popfx(), bar(1) + 3 * B, 1.0)             # 👀
put(fx, swoosh(.35), bar(2) + 2 * B, .8)          # 마커 낙서
put(fx, popfx(), bar(2) + 3 * B, 1.2)             # 힙 스티커
for i in range(4):
    put(fx, popfx(), bar(3) + 2 * B + i * B / 2, .8, (i % 2 - .5))
put(fx, swoosh(.25, True), bar(4) - .25, .9)

groove(4, 6)                                      # 벤토 위젯
for i in range(6):
    put(fx, popfx(), bar(4) + B * i, .8, (i % 2 - .5) * .5)
put(fx, swoosh(.35, True), bar(6) - .35, .9)

groove(6, 8, full=True, melody=False)             # 채팅
for at in (bar(6) + B * .5, bar(6) + B * 2, bar(6) + B * 3.2, bar(7) + B * .4):
    for k in range(5):
        put(fx, type_tick(), at - B * .85 + k * .06, .6, .3)
    put(fx, ding(1760, .25), at, .45)
put(fx, ding(2093, .4), bar(7) + B * 1.3, .5)
put(fx, popfx(), bar(7) + B * 3, 1.0)

groove(8, 10)                                     # 스와이프
for i in range(8):
    put(fx, swoosh(.2, i % 2 == 0), bar(8) + i * B / 2, .7, (1 if i % 2 else -1) * .7)
put(fx, impact(), bar(9), .8)

groove(10, 12, full=True, melody=True)            # 갓생 루틴 체크
for i in range(4):
    put(fx, ding(1568 + i * 196, .3), bar(10) + B + i * B * 1.5, .5)
    put(fx, popfx(), bar(10) + B + i * B * 1.5, .8)

groove(12, 13)                                    # 빌드업
groove(13, 14, kicks=False, full=False)
for k in range(16):                               # 스네어 롤 가속
    put(drums, clap(), bar(13) + k * B / 4, .3 + .04 * k)
for k in range(8):
    put(drums, clap(), bar(13) + 3 * B + k * B / 8, .8)
put(fx, riser(BAR * 2), bar(12), 1.1)
g0, g1 = int((bar(14) - B / 2) * SR), int(bar(14) * SR)   # 드롭 직전 반 박 정적
for bus in (drums, music, fx):
    bus[g0:g1] *= (np.linspace(1, 0, g1 - g0) ** 6)[:, None]

put(fx, impact(), bar(14), 1.3)                   # 드롭
groove(14, 16)
for i in range(4):
    put(fx, popfx(), bar(15) + i * B / 2, 1.0, (i % 2 - .5))

# ── 16마디 ~ 끝: 엔딩 ──
put(fx, impact(), bar(16), 1.0)
put(music, pad([57, 60, 64, 69, 72], 30 - bar(16)), bar(16), .7)
put(music, e808(33, 2.0, glide=.8), bar(16), 1.0)
for i, n in enumerate([81, 84, 88]):
    put(music, pluck(n, .5), bar(16) + B * (i + 1), .6)
put(fx, popfx(), bar(16) + B, .9)
put(fx, popfx(), bar(16) + 2 * B, .9)
put(fx, ding(2637, .6), bar(16) + 3.5 * B, .6)   # 탭

# ── 믹스 ──
music[:, 0] *= duck
music[:, 1] *= duck
mix = drums * .9 + music + fx * .85
irlen = int(SR * 1.2)
ki = np.arange(irlen) / SR
out = mix.copy()
for ch in range(2):
    ir = filt(rng.standard_normal(irlen), 300, 7000) * np.exp(-ki * 4.5)
    ir /= np.sqrt((ir ** 2).sum())
    Lz = N + irlen
    wet = np.fft.irfft(np.fft.rfft((music + fx)[:, ch], Lz) * np.fft.rfft(ir, Lz), Lz)[:N]
    out[:, ch] += wet * .15
tail = int(29.4 * SR)
out[tail:] *= np.linspace(1, 0, N - tail)[:, None] ** 1.5
out /= np.max(np.abs(out))
out = np.tanh(out * 1.7) / np.tanh(1.7) * .92
pcm = (np.clip(out, -1, 1) * 32767).astype('<i2')
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.wav')
with wave.open(path, 'wb') as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print(path)
