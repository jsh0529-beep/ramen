"""매일신문 브랜드 쇼릴 사운드트랙 (30s, 120BPM, F단조) — numpy 합성 → reel/soundtrack.wav
화면 큐(reel/scene.html)와 같은 타이밍: 1박 = 0.5s."""
import os
import wave
import numpy as np

SR = 48000
DUR = 30.0
N = int(SR * DUR)
B = 0.5
rng = np.random.default_rng(80)
L = np.zeros(N)
R = np.zeros(N)
duck = np.ones(N)        # 사이드체인 (킥에 맞춰 음악 버스를 눌러줌)
music = np.zeros((N, 2))  # 사이드체인 대상 버스


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


def put(sig, t0, g=1.0, pan=0.0, bus=None):
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    sig = sig[: N - i0]
    l, r = np.cos((pan + 1) * np.pi / 4) * 1.414, np.sin((pan + 1) * np.pi / 4) * 1.414
    if bus is None:
        L[i0:i0 + len(sig)] += sig * g * l
        R[i0:i0 + len(sig)] += sig * g * r
    else:
        bus[i0:i0 + len(sig), 0] += sig * g * l
        bus[i0:i0 + len(sig), 1] += sig * g * r


# ── 드럼 ──
def kick(pitch=1.0, dur=0.5):
    t = ts(dur)
    ph = 2 * np.pi * (45 * pitch * t + 150 * pitch / 30 * (1 - np.exp(-t * 30)))
    s = np.sin(ph) * np.exp(-t * 6.5)
    s += filt(rng.standard_normal(len(t)), 2000) * np.exp(-t * 200) * .3
    return np.tanh(s * 1.8) * .85


def clap():
    t = ts(0.35)
    n = filt(rng.standard_normal(len(t)), 900, 7000)
    env = sum(np.exp(-np.maximum(t - d, 0) * 60) * (t >= d) for d in (0, .008, .017)) / 3 + np.exp(-t * 14) * .6
    return n * env * .55


def hat(open_=False):
    t = ts(0.3 if open_ else 0.05)
    return filt(rng.standard_normal(len(t)), 7500) * np.exp(-t * (10 if open_ else 90)) * .25


def tick():
    t = ts(0.02)
    return filt(rng.standard_normal(len(t)), 3000) * np.exp(-t * 400) * .5


# ── 신스 ──
def saw(f, t):
    # 대역 제한 톱니파 (가산)
    s = np.zeros_like(t)
    k = 1
    while k * f < 12000 and k < 40:
        s += np.sin(2 * np.pi * f * k * t) / k
        k += 1
    return s * .6


def supersaw(notes, dur, att=.01, rel=.25, bright=4000):
    t = ts(dur)
    s = np.zeros_like(t)
    for n in notes:
        for d in (-.12, -.05, 0, .06, .13):
            s += saw(midi(n) * (1 + d / 100 * 3), t + rng.random() * .01)
    env = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel)
    return filt(s * env / (len(notes) * 5), 120, bright) * .9


def bass(n, dur):
    t = ts(dur)
    f = midi(n)
    s = np.sin(2 * np.pi * f * t) + .5 * np.tanh(3 * np.sin(2 * np.pi * f * t))
    return s * np.minimum(1, t / .005) * np.minimum(1, (dur - t) / .03) * .45


def pluck(n, dur=.25):
    t = ts(dur)
    s = saw(midi(n), t) * np.exp(-t * 14)
    return filt(s, 300, 6000) * .5


def riser(dur, f0=200, f1=6000):
    t = ts(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = int(SR * .05)
    for i in range(0, len(t), seg):  # 구간마다 필터를 올린다
        k = i / len(t)
        c = f0 * (f1 / f0) ** k
        out[i:i + seg] = filt(n[i:i + seg * 2], c * .5, c * 2)[:len(n[i:i + seg])]
    return out * (t / dur) ** 2 * .35


def whoosh(dur=.45, up=True):
    t = ts(dur)
    n = rng.standard_normal(len(t))
    out = np.zeros_like(n)
    seg = int(SR * .02)
    for i in range(0, len(t), seg):
        k = i / len(t)
        c = 400 * (20 ** (k if up else 1 - k))
        out[i:i + seg] = filt(n[i:i + seg * 2], c * .6, c * 2.5)[:len(n[i:i + seg])]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return out * env * .5


def impact(big=1.0):
    t = ts(2.5)
    sub = np.sin(2 * np.pi * (30 + 90 * np.exp(-t * 8)) * t) * np.exp(-t * 1.8)
    body = filt(rng.standard_normal(len(t)), 60, 4000) * np.exp(-t * 5) * .6
    crack = filt(rng.standard_normal(len(t)), 3000) * np.exp(-t * 30) * .5
    return np.tanh((sub + body + crack) * 1.5) * .9 * big


def beep(f=1760, dur=.12):
    t = ts(dur)
    return np.sin(2 * np.pi * f * t) * np.minimum(1, (dur - t) / .02) * .25


def reverse_swell(notes, dur=1.0):
    s = supersaw(notes, dur, att=.005, rel=.005, bright=3000)
    t = ts(dur)
    return s * (t / dur) ** 3


# F단조: Fm - Db - Ab - Eb  (1마디 = 2초)
PROG = [([65, 68, 72], 41), ([61, 65, 68], 37), ([63, 68, 72], 44), ([63, 67, 70], 39)]

# ── 0~2: 콜드 오픈 — 심장박동 서브 + 인쇄기 틱 ──
for k in range(4):
    put(kick(.8, .4), k * B, .55)
    put(np.sin(2 * np.pi * 41 * ts(.45)) * np.exp(-ts(.45) * 5) * .35, k * B)
for k in range(16):
    put(tick(), k * B / 4 + .02, .35 if k % 4 else .6, (k % 2 - .5) * .6)
put(riser(1.5, 300, 9000), .5, 1.0)
put(reverse_swell(PROG[0][0], 1.0), 1.0, .8, bus=music)


def groove(t0, bars, *, hats=True, clapson=True, openhat=True, stabs=False, arp=False, full=True):
    for b in range(bars):
        tb = t0 + b * 4 * B
        chord, root = PROG[int(round((tb - 2) / 2)) % 4]
        for k in range(4):
            tk = tb + k * B
            put(kick(), tk, 1.0)
            duck[int(tk * SR):int(tk * SR) + int(.22 * SR)] = np.minimum(duck[int(tk * SR):int(tk * SR) + int(.22 * SR)], np.linspace(.25, 1, int(.22 * SR)) ** 1.5)
            if clapson and k in (1, 3):
                put(clap(), tk, .8)
            if hats:
                put(hat(), tk + B / 2, .7, .3)
                put(hat(), tk + B / 4 * 3, .35, -.3)
            if openhat and k % 2 == 1:
                put(hat(True), tk + B / 2, .35, .2)
            # 베이스: 8분 오프비트
            put(bass(root, B / 2 * .9), tk + B / 2, .9, bus=music)
            put(bass(root + 12 if k == 3 else root, B / 2 * .8), tk, .6, bus=music)
        if full:
            put(supersaw(chord, 4 * B * .98, bright=5000 if stabs else 2600), tb, .55, bus=music)
        if stabs:
            for k in range(8):
                if k in (0, 3, 6):
                    put(supersaw([n + 12 for n in chord], .18, att=.003, rel=.08, bright=8000), tb + k * B / 2, .5, bus=music)
        if arp:
            seq = [chord[0], chord[1], chord[2], chord[1] + 12, chord[2] + 12, chord[1], chord[0] + 12, chord[2]]
            for k in range(8):
                put(pluck(seq[k] + 12), tb + k * B / 2, .45, (k % 2 - .5) * .7, bus=music)


# ── 2: 드롭 인 '매' ──
put(impact(.9), 2.0)
put(impact(.5), 2.5)
put(whoosh(.5, True), 3.05, .8)
put(whoosh(.45, False), 3.55, .7)
groove(2.0, 3, stabs=False, arp=True)                       # 2~8
# 4: 연도 카운터 — 빠른 틱 롤
for k in range(int(1.4 / .025)):
    put(tick(), 4.05 + k * .025, .25 + .2 * k / 56, (k % 2 - .5) * .8)
put(beep(1568, .18), 5.5, 1.0)
put(impact(.6), 6.0)
# 6~8: '80' — 스탭 강조
for at in (6.5, 7.0, 7.5):
    put(supersaw([77, 80, 84], .2, att=.002, rel=.1, bright=9000), at, .45, bus=music)
put(whoosh(.3, True), 7.72, .9)

# ── 8~12: 스플릿 플랩 — 플립 클릭 16분 ──
groove(8.0, 2, stabs=True, arp=True)
for k in range(32):
    put(tick(), 8 + k * B / 2 + .01, .5, (k % 3 - 1) * .7)
    put(tick(), 8 + k * B / 2 + .035, .3, -(k % 3 - 1) * .7)
put(impact(.45), 10.0)
put(impact(.45), 11.0)

# ── 12~14: 티커 밴드 ──
groove(12.0, 1, stabs=True, arp=False)
for i, at in enumerate((12.0, 12.12, 12.24)):
    put(whoosh(.5, True), at, .8, (i - 1) * .8)
put(riser(.5, 800, 12000), 13.5, 1.1)

# ── 14~16: PICK ──
groove(14.0, 1, stabs=False, arp=True)
for k, at in enumerate((14.45, 14.59, 14.73, 14.87)):
    put(beep(1175 + k * 150, .06), at, .8, (k % 2 - .5))
put(beep(2349, .25), 15.0, 1.0)
put(whoosh(.25, True), 15.25, .8)
put(impact(1.0), 15.5)

# ── 16~18: 하프타임 — 1955 사설 ──
for at, n in ((16.0, 41), (16.5, 37), (17.0, 36)):
    put(kick(.7, .7), at, 1.0)
    put(supersaw([n + 24, n + 27, n + 31], 1.2, att=.005, rel=.9, bright=2200), at, .5, bus=music)
    put(np.sin(2 * np.pi * midi(n) * ts(1.0)) * np.exp(-ts(1.0) * 2.5) * .5, at)
put(clap(), 17.0, 1.2)
glass = filt(rng.standard_normal(int(SR * 1.2)), 2500) * np.exp(-ts(1.2) * 4) * .5
put(glass + impact(.9)[:len(glass)], 17.5)

# ── 18~20: 할 말은 한다 ──
put(impact(.8), 18.0)
groove(18.0, 1, stabs=True, arp=True)
put(impact(.6), 18.75)
put(whoosh(.4, False), 19.6, .8)

# ── 20~24: 빌드업 ──
groove(20.0, 1, stabs=False, arp=True, openhat=False)
groove(22.0, 1, stabs=False, arp=True, openhat=False, clapson=False)
for k in range(8):                              # 22~23: 8분 스네어
    put(clap(), 22 + k * B / 2, .4 + .03 * k)
for k in range(8):                              # 23~23.5: 16분 → 32분
    put(clap(), 23 + k * B / 8 * 1.0, .6 + .04 * k)
for k in range(8):
    put(clap(), 23.25 + k * B / 16, .8)
put(riser(3.4, 150, 14000), 20.1, 1.3)
# 23.5~24: 정적 (갭)
g0, g1 = int(23.5 * SR), int(24.0 * SR)
L[g0:g1] *= np.linspace(1, 0, g1 - g0) ** 8
R[g0:g1] *= np.linspace(1, 0, g1 - g0) ** 8
music[g0:g1] *= (np.linspace(1, 0, g1 - g0) ** 8)[:, None]
put(reverse_swell([77, 80, 84, 89], .45), 23.55, .7, bus=music)

# ── 24~27: 드롭 — 해 뜨는 사시 ──
put(impact(1.3), 24.0)
groove(24.0, 1, stabs=True, arp=True)
groove(26.0, 1, stabs=True, arp=True)
put(supersaw([77, 80, 84, 89], 2.8, att=.4, rel=1.0, bright=7000), 24.0, .4, bus=music)
put(whoosh(.4, True), 26.6, .9)

# ── 27~30: 로고 ──
put(impact(1.1), 27.0)
put(supersaw([53, 65, 68, 72, 77], 3.0, att=.01, rel=1.8, bright=6000), 27.0, .6, bus=music)
for k in range(10):   # 스트립 조립 틱
    put(tick(), 27.0 + k * .035, .6, (k % 2 - .5))
put(beep(1397, .1), 28.2, .6)
put(beep(2093, .1), 28.5, .5)
put(impact(.9), 29.0)
put(supersaw([56, 60, 63, 68, 72, 75], 1.0, att=.005, rel=.8, bright=8000), 29.0, .55, bus=music)

# ── 믹스: 음악 버스 사이드체인 + 리버브 ──
music[:, 0] *= duck
music[:, 1] *= duck
mix = np.stack([L, R], 1) + music
irlen = int(SR * 2.0)
ki = np.arange(irlen) / SR
out = mix.copy()
for ch in range(2):
    ir = filt(rng.standard_normal(irlen), 200, 6000) * np.exp(-ki * 3.2)
    ir /= np.sqrt((ir ** 2).sum())
    Lz = N + irlen
    wet = np.fft.irfft(np.fft.rfft(mix[:, ch], Lz) * np.fft.rfft(ir, Lz), Lz)[:N]
    out[:, ch] = mix[:, ch] + wet * .18
tail = int(29.5 * SR)
out[tail:] *= np.linspace(1, 0, N - tail)[:, None] ** 1.5
out /= np.max(np.abs(out))
out = np.tanh(out * 1.6) / np.tanh(1.6) * .92
pcm = (np.clip(out, -1, 1) * 32767).astype('<i2')
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.wav')
with wave.open(path, 'wb') as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print(path)
