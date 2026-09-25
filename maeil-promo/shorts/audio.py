"""숏폼 사운드트랙: 96BPM 로파이 비트 (numpy 합성) → shorts/soundtrack.wav
타이밍은 shorts/scene.html 과 맞춰져 있다. 1박 = 0.625s, 1마디 = 2.5s."""
import os
import wave
import numpy as np

SR = 48000
DUR = 48.0
N = int(SR * DUR)
BEAT = 60 / 96
rng = np.random.default_rng(2026)
mix = np.zeros((N, 2))


def add(sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N or i0 < 0:
        return
    sig = sig[: N - i0]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i0:i0 + len(sig), 0] += sig * gain * l
    mix[i0:i0 + len(sig), 1] += sig * gain * r


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


def kick():
    t = ts(0.45)
    return np.sin(2 * np.pi * (48 * t + 110 / 28 * (1 - np.exp(-t * 28)))) * np.exp(-t * 7) * 0.9


def snare():
    t = ts(0.3)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.4
    return body + filt(rng.standard_normal(len(t)), 1200, 9000) * np.exp(-t * 16) * 0.45


def hat(open_=False):
    t = ts(0.25 if open_ else 0.06)
    return filt(rng.standard_normal(len(t)), 7000) * np.exp(-t * (12 if open_ else 70)) * 0.22


def keys(freq, dur, vel=1.0):
    """로즈 느낌의 전자피아노."""
    t = ts(dur)
    s = np.sin(2 * np.pi * freq * t + 0.8 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 3))
    s += 0.25 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 2)
    s *= np.exp(-t * 0.9) * np.minimum(1, t / 0.006) * (1 + 0.08 * np.sin(2 * np.pi * 4.5 * t))
    s[-1200:] *= np.linspace(1, 0, 1200)
    return s * 0.12 * vel


def bass(freq, dur):
    t = ts(dur)
    s = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return s * np.minimum(1, t / 0.01) * np.exp(-t * 1.2) * np.minimum(1, (dur - t) / 0.05) * 0.35


# 코드 진행 (Fmaj7 - Em7 - Dm7 - Cmaj7), 마디당 1코드
PROG = [([53, 57, 60, 64], 41), ([52, 55, 59, 62], 40), ([50, 53, 57, 60], 38), ([48, 52, 55, 59], 36)]


def bar(t0, bar_i, drums=True, full=True, vel=1.0):
    notes, root = PROG[bar_i % 4]
    for j, n in enumerate(notes):
        add(keys(midi(n), 2.4, vel), t0 + j * 0.012, 1.0, (j - 1.5) * 0.25)
    add(bass(midi(root), BEAT * 2.8), t0, 1.0 if full else 0.0)
    add(bass(midi(root + 7), BEAT * 0.9), t0 + BEAT * 3, 0.8 if full else 0.0)
    if not drums:
        return
    swing = 0.035
    for b in range(4):
        tb = t0 + b * BEAT
        if b in (0, 2):
            add(kick(), tb)
        if b == 2:
            add(kick(), tb + BEAT * 0.75, 0.6)
        if b in (1, 3):
            add(snare(), tb + 0.01, 0.8)
        add(hat(), tb, 0.8, 0.3)
        add(hat(), tb + BEAT / 2 + swing, 0.5, 0.3)
    if full:
        add(hat(True), t0 + 3.5 * BEAT + swing, 0.4, -0.3)


# 0 ~ 7.5: 차가운 도입 — 드럼만 점점, 알림음 섞기
t = 0.0
for i in range(3):
    bar(t, i, drums=True, full=(i > 0), vel=0.7)
    t += 2.5
for k in range(18):
    tt = rng.uniform(0.2, 7.3)
    f = rng.choice([1319, 1568, 1760, 2093])
    p = ts(0.1)
    add(np.sin(2 * np.pi * f * p) * np.exp(-p * 40) * 0.12, tt, 1.0, rng.uniform(-0.7, 0.7))

# 7.5: 로그아웃 — 전부 끊고 '딸깍'
cut = int(7.5 * SR)
mix[cut:] = 0
c = ts(0.03)
add(filt(rng.standard_normal(len(c)), 2000) * np.exp(-c * 200) * 0.6, 7.5)
add(np.sin(2 * np.pi * 60 * ts(0.15)) * np.exp(-ts(0.15) * 30) * 0.4, 7.5)

# 8.75 ~ 40.2: 따뜻한 로파이 (필카·LP·필사 → 신문)
t = 8.75
i = 0
while t < 40.2 - 0.01:
    drums = not (20.0 <= t < 22.5)          # "다음 텍스트힙은," 에서 잠시 드럼 빠짐 → 빌드
    bar(t, i, drums=drums, full=True, vel=1.0)
    t += 2.5
    i += 1
# 20 ~ 22.5 빌드업: 상승 노이즈 + 스네어 롤
b = ts(2.5)
add(filt(rng.standard_normal(len(b)), 800, 9000) * (b / 2.5) ** 2 * 0.3, 20.0)
for k in range(16):
    add(snare(), 21.25 + k * (1.25 / 16), 0.25 + 0.5 * k / 16)
# 22.5 "신문." 임팩트
add(kick(), 22.5, 1.3)
add(filt(rng.standard_normal(int(SR * 1.5)), 200, 6000) * np.exp(-ts(1.5) * 3) * 0.3, 22.5)

# LP 크래클 (8.75 ~ 끝)
cr = np.zeros(N)
idx = rng.integers(int(8.75 * SR), N, 2600)
cr[idx] = rng.uniform(-1, 1, len(idx))
cr = filt(cr, 1500, 8000) * 0.5 + filt(rng.standard_normal(N), 300, 3000) * 0.008
mix[:, 0] += cr
mix[:, 1] += cr

# 40.2 엔딩: 임팩트 + 마무리 화음
for k in (40.2,):
    add(kick(), k, 1.2)
    add(filt(rng.standard_normal(int(SR * 2)), 300, 7000) * np.exp(-ts(2) * 2.5) * 0.25, k)
for j, n in enumerate([41, 53, 57, 60, 64, 67]):
    add(keys(midi(n), 7.0, 1.3), 40.2 + j * 0.03, 1.0, (j - 2.5) * 0.2)
for j, n in enumerate([48, 55, 60, 64, 67, 72]):
    add(keys(midi(n), 4.5, 1.2), 43.3 + j * 0.03, 1.0, (j - 2.5) * 0.2)

# 간단한 리버브 + 마스터
irlen = int(SR * 1.6)
ki = np.arange(irlen) / SR
out = mix.copy()
for ch in range(2):
    ir = filt(rng.standard_normal(irlen), None, 5000) * np.exp(-ki * 3.5)
    ir /= np.sqrt((ir ** 2).sum())
    L = N + irlen
    wet = np.fft.irfft(np.fft.rfft(mix[:, ch], L) * np.fft.rfft(ir, L), L)[:N]
    out[:, ch] = mix[:, ch] + wet * 0.22
tail = int(46.8 * SR)
out[tail:] *= np.linspace(1, 0, N - tail)[:, None] ** 2
out /= np.max(np.abs(out))
out = np.tanh(out * 2.0) / np.tanh(2.0) * 0.9
pcm = (np.clip(out, -1, 1) * 32767).astype('<i2')
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'soundtrack.wav')
with wave.open(path, 'wb') as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print(path)
