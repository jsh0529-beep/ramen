"""매일신문 홍보영상 사운드트랙 합성 (numpy 만 사용) → soundtrack.wav
장면 타이밍은 scene.html 과 맞춰져 있다."""
import wave
import numpy as np

SR = 48000
DUR = 104.0
N = int(SR * DUR)
rng = np.random.default_rng(1946)
mix = np.zeros((N, 2))


def idx(t):
    return int(t * SR)


def add(sig, t0, gain=1.0, pan=0.0):
    i0 = idx(t0)
    if i0 >= N:
        return
    sig = sig[: N - i0]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i0:i0 + len(sig), 0] += sig * gain * l
    mix[i0:i0 + len(sig), 1] += sig * gain * r


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def piano(freq, dur=4.0, vel=1.0):
    t = np.arange(int(SR * dur)) / SR
    s = np.zeros_like(t)
    for k in range(1, 8):
        s += np.sin(2 * np.pi * freq * k * (1 + 0.0004 * k * k) * t) / k ** 1.6 * np.exp(-t * (1.1 + 0.9 * k))
    s *= np.minimum(1, t / 0.004)
    s[-2000:] *= np.linspace(1, 0, 2000)
    return s * vel * 0.25


def pad(freqs, dur, attack=1.5, release=1.5):
    t = np.arange(int(SR * dur)) / SR
    s = np.zeros_like(t)
    for f in freqs:
        for d in (-0.15, 0.0, 0.17):
            s += np.sin(2 * np.pi * (f + d) * t + rng.random() * 6) + 0.3 * np.sin(2 * np.pi * 2 * (f + d) * t)
    env = np.minimum(1, t / attack) * np.minimum(1, (dur - t) / release)
    return s * env / (len(freqs) * 3) * 0.12


def noise(dur):
    return rng.standard_normal(int(SR * dur))


def lp_fft(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def bp_fft(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1 / (1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    return np.fft.irfft(X, len(x))


# ── 1. 피드 홍수 (0 ~ 10.9s): 점점 촘촘해지는 알림음 + 부풀어 오르는 소음 ──
CUT = 10.9
t = 0.3
while t < CUT - 0.05:
    rate = 2.5 + (t / CUT) ** 2 * 38
    f = rng.choice([988, 1175, 1319, 1568, 1760, 2093]) * (1 + (t / CUT) * rng.uniform(-0.03, 0.03))
    tt = np.arange(int(SR * 0.12)) / SR
    ping = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt * 38)
    add(ping, t, 0.10 + 0.08 * (t / CUT), pan=rng.uniform(-0.8, 0.8))
    t += rng.exponential(1 / rate)

sw = noise(CUT)
tt = np.arange(len(sw)) / SR
swell = lp_fft(sw, 1800) * (tt / CUT) ** 2.5 * 0.35
drone = np.sin(2 * np.pi * (55 * (1 + tt / CUT)) * tt) * (tt / CUT) ** 1.5 * 0.25
tick = np.zeros_like(tt)
for b in np.arange(0.5, CUT, 0.5):
    i = int(b * SR)
    k = np.arange(1200) / SR
    tick[i:i + 1200] += np.sin(2 * np.pi * 60 * k) * np.exp(-k * 40)
add(swell + drone + tick * 0.35, 0.0)
# 컷: 10.9s 이후 무음 (5ms 페이드)
c = idx(CUT)
mix[c - 240:c] *= np.linspace(1, 0, 240)[:, None]
mix[c:] = 0

# ── 2. 암전 속 한 음 ──
add(piano(midi(57), 5.0, 0.8), 11.5, 0.9)

# ── 3. 종이가 내려앉는 소리 (15.9 ~ 17.5) ──
w = bp_fft(noise(1.8), 500, 5000)
tw = np.arange(len(w)) / SR
w *= np.exp(-((tw - 1.35) / 0.35) ** 2) * 0.35
thump = np.sin(2 * np.pi * 70 * np.arange(6000) / SR) * np.exp(-np.arange(6000) / SR * 30) * 0.5
add(w, 15.9)
add(thump, 17.35)

# ── 피아노 진행 ──
CHORDS = {
    'Am': [45, 57, 60, 64], 'F': [41, 57, 60, 65], 'C': [48, 55, 60, 64], 'G': [43, 55, 59, 62],
    'Em': [40, 55, 59, 64], 'Dm': [38, 57, 62, 65], 'E': [40, 56, 59, 64], 'Cmaj': [36, 55, 60, 64, 67, 72],
}


def arp(name, t0, span=4.0, vel=0.8, pattern=(0, 1, 2, 3, 2, 1), step=None):
    notes = CHORDS[name]
    step = step or span / len(pattern)
    add(piano(midi(notes[0]), span + 1.5, vel * 1.1), t0, 1.0, -0.2)
    for j, p in enumerate(pattern):
        n = notes[1 + p % (len(notes) - 1)] + (12 if p >= len(notes) - 1 else 0)
        add(piano(midi(n), 3.0, vel * 0.7), t0 + j * step, 1.0, rng.uniform(-0.4, 0.4))
    add(pad([midi(x) for x in notes[:3]], span + 1.0, 1.2, 1.2), t0, 0.9)


# 종이 파트 (17.5 ~ 46)
t0 = 17.5
for ch in ['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'G']:
    arp(ch, t0, 3.6, 0.7)
    t0 += 3.6
arp('Am', t0, 4.0, 0.6, pattern=(0, 1, 2))  # ~46.3 까지 여운

# 역사 파트 (46.2 ~ 70.2)
t0 = 46.4
for ch in ['F', 'C', 'G', 'Am']:
    arp(ch, t0, 2.4, 0.75)
    t0 += 2.4
# 56 ~ 64: 1946 — 윤전기 리듬
for b in np.arange(56.0, 64.0, 0.5):
    k = np.arange(4000) / SR
    clack = bp_fft(noise(4000 / SR), 1500, 7000) * np.exp(-k * 55) * 0.18
    clunk = np.sin(2 * np.pi * 95 * k) * np.exp(-k * 25) * 0.25
    add(clack + clunk, b, 0.9 if (b * 2) % 2 == 0 else 0.6)
for ch in ['Am', 'F', 'C', 'G']:
    arp(ch, t0, 2.0, 0.7, pattern=(0, 1, 2, 3))
    t0 += 2.0
# 64 ~ 70.2: 1955 사설 — 긴장
for ch, dur in [('Dm', 2.0), ('Am', 2.0), ('E', 2.2)]:
    arp(ch, t0, dur, 0.7, pattern=(0, 1, 2, 1))
    t0 += dur
# 70.2: 습격 — 타격음, 음악 정지
HIT = 70.2
mix[idx(HIT):] = 0  # 이전 음 모두 끊기
k = np.arange(int(SR * 2.5)) / SR
boom = np.sin(2 * np.pi * (30 + 60 * np.exp(-k * 6)) * k) * np.exp(-k * 1.6) * 0.9
crash = lp_fft(noise(2.5), 3000) * np.exp(-k * 3.5) * 0.35
add(boom + crash, HIT, 0.55)
# 71.7 ~ 74.6: 낮은 단조 여운
add(pad([midi(38), midi(45), midi(53)], 3.2, 0.8, 1.0), 71.6, 1.2)
add(piano(midi(50), 3.0, 0.7), 71.8)
# 74.6: 그러나 펜은 꺾이지 않았다 — 밝게
arp('C', 74.6, 4.0, 0.9, pattern=(0, 1, 2, 3))
# 78.6 ~ 86: 2·28 행진 — 북 + 상승 진행
for b in np.arange(78.6, 86.0, 60 / 100):
    k = np.arange(int(SR * 0.5)) / SR
    drum = np.sin(2 * np.pi * (60 + 40 * np.exp(-k * 30)) * k) * np.exp(-k * 9) * 0.35
    add(drum, b)
t0 = 78.6
for ch in ['F', 'G', 'Am', 'C']:
    arp(ch, t0, 1.85, 0.8, pattern=(0, 1, 2, 3))
    t0 += 1.85

# ── 결론 (86.2 ~) ──
t0 = 86.4
for ch in ['F', 'G', 'Em', 'Am']:
    arp(ch, t0, 2.1, 0.65, pattern=(0, 1, 2))
    t0 += 2.1
arp('G', t0, 1.6, 0.6, pattern=(0, 1))  # 94.8 까지
# 95: 로고 — 최종 화음
for n in CHORDS['Cmaj']:
    add(piano(midi(n), 8.5, 1.5), 95.0 + 0.03 * CHORDS['Cmaj'].index(n), 1.0, rng.uniform(-0.3, 0.3))
add(pad([midi(48), midi(55), midi(64), midi(72)], 9.0, 1.5, 4.0), 95.0, 2.4)
add(piano(midi(79), 6.0, 0.9), 97.0, 1.0, 0.3)

# ── 리버브 (지수 감쇠 노이즈 IR, FFT 컨볼루션) ──
irlen = int(SR * 2.4)
ki = np.arange(irlen) / SR
wet = np.zeros_like(mix)
dry_src = mix.copy()
dry_src[:idx(CUT)] = 0  # 피드 구간은 리버브 없이 (컷 직후 잔향이 남지 않게)
for ch in range(2):
    ir = rng.standard_normal(irlen) * np.exp(-ki * 2.6)
    ir = lp_fft(ir, 6000)
    ir /= np.sqrt((ir ** 2).sum())
    L = N + irlen
    wet[:, ch] = np.fft.irfft(np.fft.rfft(dry_src[:, ch], L) * np.fft.rfft(ir, L), L)[:N]
out = mix * 0.85 + wet * 0.35

# 마스터: 정규화, 끝 페이드
tail = idx(102.4)
out[tail:] *= np.linspace(1, 0, N - tail)[:, None] ** 2
out /= np.max(np.abs(out))
out = np.tanh(out * 2.4) / np.tanh(2.4) * 0.9  # 부드러운 리미터로 전체 음량 확보
pcm = (np.clip(out, -1, 1) * 32767).astype('<i2')
with wave.open('soundtrack.wav', 'wb') as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes(pcm.tobytes())
print('soundtrack.wav', DUR, 's')
