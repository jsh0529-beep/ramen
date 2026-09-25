// 숏폼용 CG 장면 (three.js). 실사 사진 대신 PBR 재질·그림자·피사계 심도로 실제처럼 렌더링.
// render(t) 는 시간 t(초)에 대해 결정적으로 한 프레임을 그린다.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const W = 1080, H = 1920;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ease = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);
const V = (x, y, z) => new THREE.Vector3(x, y, z);
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

let renderer, composer, renderPass, bokeh, camera;
const sets = {};

// ───────────── 텍스처 도우미 ─────────────
function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return [c, c.getContext('2d')]; }
function tex(c, { srgb = true, rep = [1, 1] } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...rep);
  return t;
}
function noiseCanvas(w, h, seed, base, amp) {
  const [c, g] = canvas(w, h); const r = rng(seed); const img = g.createImageData(w, h);
  for (let i = 0; i < w * h; i++) { const v = base + (r() - .5) * amp; img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v; img.data[i * 4 + 3] = 255; }
  g.putImageData(img, 0, 0); return c;
}
function woodCanvas() {
  const [c, g] = canvas(2048, 1024); const r = rng(5);
  g.fillStyle = '#7a4f2e'; g.fillRect(0, 0, 2048, 1024);
  for (let y = 0; y < 1024; y += 1) {
    const k = Math.sin(y * .021) * .5 + Math.sin(y * .067 + 1.3) * .3 + Math.sin(y * .31) * .12;
    g.fillStyle = `rgba(${k > 0 ? '40,22,10' : '160,110,70'},${Math.abs(k) * .22})`; g.fillRect(0, y, 2048, 1);
  }
  for (let i = 0; i < 900; i++) { // 결
    const y = r() * 1024, len = 200 + r() * 900, x = r() * 2048;
    g.strokeStyle = `rgba(35,18,8,${.05 + r() * .12})`; g.lineWidth = .6 + r() * 1.6; g.beginPath();
    for (let s = 0; s <= len; s += 20) g.lineTo(x + s, y + Math.sin((x + s) * .004 + i) * 6);
    g.stroke();
  }
  for (let i = 0; i < 7; i++) { // 판재 이음새
    const y = (i + 1) * 1024 / 7.5 + r() * 20; g.fillStyle = 'rgba(20,10,4,.55)'; g.fillRect(0, y, 2048, 3);
  }
  return c;
}
function fabricCanvas(color) {
  const [c, g] = canvas(512, 512); g.fillStyle = color; g.fillRect(0, 0, 512, 512);
  for (let y = 0; y < 512; y += 2) { g.fillStyle = `rgba(255,255,255,${y % 4 ? .025 : .0})`; g.fillRect(0, y, 512, 1); }
  for (let x = 0; x < 512; x += 2) { g.fillStyle = `rgba(0,0,0,${x % 4 ? .05 : 0})`; g.fillRect(x, 0, 1, 512); }
  return c;
}

// ───────────── 피드 화면 (폰) ─────────────
const FEED = [['[속보] 충격… 결국 이렇게 됐다', 1], ['이거 보면 생각 바뀜', 0], ['AI가 만든 영상, 진짜일까?', 0], ['“확인되지 않은 정보입니다”', 0], ['지금 난리 난 그 사진', 1], ['3초 요약: 모르면 손해', 0], ['삭제된 게시물입니다', 0], ['[단독?] 출처: 커뮤니티', 1], ['당신이 좋아할 만한 영상', 0], ['댓글 9,999+ 폭발', 0], ['조작 논란… 원본은?', 1], ['알고리즘 추천 #37', 0]];
const [feedC, feedG] = canvas(720, 1560);
let feedTex;
function drawFeed(off, flash) {
  const g = feedG; g.fillStyle = '#0c0d12'; g.fillRect(0, 0, 720, 1560);
  const ch = 330, n = FEED.length, total = n * ch;
  for (let i = -1; i < 7; i++) {
    const k = Math.floor(off / ch) + i, y = i * ch - (off % ch) + 110;
    const [tt, hot] = FEED[((k % n) + n) % n];
    const hue = (k * 47) % 360;
    g.fillStyle = '#16181f'; g.beginPath(); g.roundRect(28, y, 664, ch - 26, 26); g.fill();
    const grd = g.createLinearGradient(0, y, 0, y + 190); grd.addColorStop(0, `hsl(${hue},45%,38%)`); grd.addColorStop(1, `hsl(${(hue + 40) % 360},55%,18%)`);
    g.fillStyle = grd; g.beginPath(); g.roundRect(28, y, 664, 190, [26, 26, 0, 0]); g.fill();
    g.fillStyle = 'rgba(255,255,255,.85)'; g.beginPath(); g.moveTo(340, y + 70); g.lineTo(390, y + 95); g.lineTo(340, y + 120); g.fill();
    g.fillStyle = hot ? '#ff5a4e' : '#eceef3'; g.font = '700 38px "Noto Sans KR"'; g.fillText(tt, 56, y + 250);
    g.fillStyle = '#7d8290'; g.font = '400 24px "Noto Sans KR"'; g.fillText(`조회 ${(k * 7919 % 990) + 10}만 · 방금`, 56, y + 288);
  }
  g.fillStyle = '#0c0d12'; g.fillRect(0, 0, 720, 100);
  g.fillStyle = '#fff'; g.font = '700 30px "Noto Sans KR"'; g.fillText('9:41', 60, 64); g.fillText('추천  |  실시간  |  인기', 250, 64);
  if (flash > 0) { g.fillStyle = `rgba(255,255,255,${flash})`; g.fillRect(0, 0, 720, 1560); }
  feedTex.needsUpdate = true;
}

// ───────────── 신문 지면 ─────────────
const BODY = ('하루에도 수천 개의 게시물이 손끝을 스쳐 지나간다. 무엇을 보았는지 떠올리려 하면 기억나는 것은 거의 없다. ' +
  '빠르게 흘러간 것은 빠르게 사라진다. 신문은 다르다. 한 번 찍힌 활자는 지울 수도, 몰래 고칠 수도 없기에 기자는 찍기 전에 묻고 또 확인한다. ' +
  '종이 위의 문장은 우리를 멈춰 세우고, 멈춘 자리에서 생각이 자란다. 알고리즘은 내가 좋아할 것을 보여주지만, 신문은 우리가 알아야 할 것을 보여준다. ' +
  '1946년 대구에서 첫 호를 찍은 이래 매일신문은 대구·경북의 아침을 기록해 왔다. 동네의 작은 변화부터 시청과 도청의 결정까지, 누군가는 끝까지 지켜봐야 한다. ' +
  '감시하는 눈이 사라진 도시에서는 그 비용을 시민이 치른다는 연구도 있다. 그래서 오늘도 신문은 발로 뛰고, 확인하고, 기록한다. ').repeat(8);
function wrapText(g, text, x, y, w, lh, maxLines) {
  let line = '', n = 0, i = 0;
  for (const ch of text) {
    if (g.measureText(line + ch).width > w) { g.fillText(line, x, y + n * lh); line = ch; n++; if (n >= maxLines) return i; } else line += ch; i++;
  }
  g.fillText(line, x, y + n * lh); return i;
}
function halftone(g, x, y, w, h, seed, kind) {
  const r = rng(seed);
  g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.fillStyle = '#f0ebe0'; g.fillRect(x, y, w, h);
  const step = 7;
  for (let yy = 0; yy < h; yy += step) for (let xx = 0; xx < w; xx += step) {
    const u = xx / w, v = yy / h; let d;
    if (kind === 0) { // 도시 스카이라인
      const sky = .25 + .5 * v; const b = Math.floor(u * 14); const bh = .35 + ((b * 73) % 10) / 22; d = v > 1 - bh ? .82 : sky * .5;
      if (v > 1 - bh && ((xx >> 3) % 3 === 0) && ((yy >> 3) % 2 === 0) && r() > .4) d = .2;
    } else { // 사람들 실루엣
      d = .2 + .35 * v; const c = [.2, .38, .55, .72, .86]; for (const cx of c) { const dx = u - cx, dy = v - .55; if (dx * dx * 5 + dy * dy * 1.3 < .03 || (Math.abs(dx) < .07 && v > .6)) d = .85; }
    }
    g.fillStyle = '#1a1712'; g.beginPath(); g.arc(x + xx + 3, y + yy + 3, Math.sqrt(clamp(d)) * step * .56, 0, 7); g.fill();
  }
  g.restore();
}
function newspaperCanvas() {
  const w = 1480, h = 2000; const [c, g] = canvas(w, h);
  g.fillStyle = '#ece6d8'; g.fillRect(0, 0, w, h);
  const ink = '#1a1712'; g.fillStyle = ink; g.textBaseline = 'alphabetic';
  // 제호
  g.font = '900 190px "Noto Serif KR"'; g.textAlign = 'center'; g.fillText('매일신문', w / 2, 230);
  g.font = '700 34px "Noto Serif KR"'; g.fillText('每 日 新 聞', w / 2, 290);
  g.fillRect(70, 318, w - 140, 5); g.fillRect(70, 330, w - 140, 1.5);
  g.font = '400 25px "Noto Sans KR"'; g.textAlign = 'left'; g.fillText('2026년 9월 25일 금요일', 76, 362);
  g.textAlign = 'right'; g.fillText('since 1946 · 대구·경북', w - 76, 362); g.textAlign = 'left';
  g.fillRect(70, 380, w - 140, 1.5);
  // 톱 헤드라인
  g.font = '900 104px "Noto Serif KR"'; g.fillText('스크롤은 흘러가도,', 76, 510); g.fillText('활자는 남는다', 76, 628);
  g.font = '700 38px "Noto Serif KR"'; g.fillStyle = '#3a342a'; g.fillText('숏폼 시대, 다시 종이를 펼치는 2030… “느리게 읽어야 기억난다”', 78, 700); g.fillStyle = ink;
  halftone(g, 76, 740, 820, 520, 11, 0);
  g.font = '400 22px "Noto Sans KR"'; g.fillStyle = '#4a4436'; g.fillText('대구 도심의 아침 풍경.', 76, 1290); g.fillStyle = ink;
  // 본문 칼럼
  g.font = '400 27px "Noto Serif KR"'; let pos = 0;
  const cols = [[930, 740, 480, 19], [76, 1330, 400, 22], [506, 1330, 400, 22]];
  for (const [x, y, cw, lines] of cols) { pos += wrapText(g, BODY.slice(pos), x, y + 26, cw, 42, lines); }
  g.fillRect(912, 740, 1.5, 820); g.fillRect(488, 1320, 1.5, 620); g.fillRect(918, 1320, 1.5, 620);
  // 오른쪽 아래 기사
  g.font = '900 56px "Noto Serif KR"'; g.fillText('대구·경북의 아침,', 940, 1620); g.fillText('80년을 기록하다', 940, 1690);
  halftone(g, 940, 1720, 470, 230, 23, 1);
  // 인쇄 얼룩·주름
  const r = rng(9); for (let i = 0; i < 2500; i++) { g.fillStyle = `rgba(60,50,30,${r() * .05})`; g.fillRect(r() * w, r() * h, 2 + r() * 3, 2 + r() * 3); }
  g.fillStyle = 'rgba(0,0,0,.05)'; g.fillRect(w / 2 - 2, 0, 4, h);
  return c;
}

// ───────────── 인화 사진 (필카) ─────────────
function printCanvas(kind) {
  const [c, g] = canvas(600, 720); g.fillStyle = '#f7f4ee'; g.fillRect(0, 0, 600, 720);
  const x = 36, y = 36, w = 528, h = 528; const grd = g.createLinearGradient(0, y, 0, y + h);
  const pal = [['#f7b267', '#f4845f', '#5b3758'], ['#9ad1d4', '#f6e7cb', '#6a8d73'], ['#2b2d42', '#ef8354', '#f9c784'], ['#ffd6a5', '#fdffb6', '#caffbf']][kind];
  grd.addColorStop(0, pal[0]); grd.addColorStop(.6, pal[1]); grd.addColorStop(1, pal[2]); g.fillStyle = grd; g.fillRect(x, y, w, h);
  g.fillStyle = 'rgba(255,250,220,.9)'; g.beginPath(); g.arc(x + w * (.3 + kind * .12), y + h * .42, 50 + kind * 8, 0, 7); g.fill();
  g.fillStyle = 'rgba(30,25,35,.75)'; g.beginPath(); g.moveTo(x, y + h);
  for (let i = 0; i <= 12; i++) g.lineTo(x + i * w / 12, y + h * (.66 + .08 * Math.sin(i * 1.7 + kind)));
  g.lineTo(x + w, y + h); g.fill();
  const r = rng(kind + 3); const img = g.getImageData(x, y, w, h);
  for (let i = 0; i < img.data.length; i += 4) { const n = (r() - .5) * 28; img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n; }
  g.putImageData(img, x, y);
  g.fillStyle = '#6b6352'; g.font = '400 30px "Nanum Pen Script"'; g.fillText(['여름, 수성못', '동성로 산책', '퇴근길 노을', '주말 브런치'][kind], 50, 640);
  return c;
}

// ───────────── 필사 노트 ─────────────
const [noteC, noteG] = canvas(1050, 1400); let noteTex;
const NOTE = ['천천히 읽고,', '오래 기억하기.', '', '— 오늘 아침 신문에서'];
function drawNote(p) {
  const g = noteG; g.fillStyle = '#f5f1e6'; g.fillRect(0, 0, 1050, 1400);
  g.strokeStyle = 'rgba(90,130,190,.35)'; g.lineWidth = 2; for (let y = 180; y < 1400; y += 78) { g.beginPath(); g.moveTo(0, y); g.lineTo(1050, y); g.stroke(); }
  g.strokeStyle = 'rgba(210,80,80,.45)'; g.beginPath(); g.moveTo(120, 0); g.lineTo(120, 1400); g.stroke();
  g.fillStyle = '#1d2a4a'; g.font = '400 104px "Nanum Pen Script"';
  const totalChars = NOTE.join('').length; let left = Math.floor(p * totalChars); let tip = [150, 400];
  NOTE.forEach((ln, i) => {
    const s = ln.slice(0, Math.max(0, left)); left -= ln.length;
    const y = 400 + i * 156; g.fillText(s, 150, y - 10); if (s.length) tip = [150 + g.measureText(s).width, y - 30];
  });
  noteTex.needsUpdate = true; return tip;
}

// ───────────── 레코드 ─────────────
function recordCanvas() {
  const s = 1024; const [c, g] = canvas(s, s); g.fillStyle = '#0b0b0c'; g.fillRect(0, 0, s, s);
  const r = rng(4);
  for (let rad = 150; rad < 510; rad += 1.5) { g.strokeStyle = `rgba(255,255,255,${.02 + r() * .05})`; g.lineWidth = 1; g.beginPath(); g.arc(s / 2, s / 2, rad, 0, 7); g.stroke(); }
  for (const rad of [240, 330, 420]) { g.strokeStyle = 'rgba(0,0,0,.9)'; g.lineWidth = 5; g.beginPath(); g.arc(s / 2, s / 2, rad, 0, 7); g.stroke(); }
  g.fillStyle = '#c8352b'; g.beginPath(); g.arc(s / 2, s / 2, 150, 0, 7); g.fill();
  g.fillStyle = '#f3e9d8'; g.textAlign = 'center'; g.font = '900 44px "Noto Sans KR"'; g.fillText('SIDE A', s / 2, s / 2 - 50);
  g.font = '400 30px "Noto Sans KR"'; g.fillText('33⅓ RPM · SLOW MORNING', s / 2, s / 2 + 70);
  return c;
}

// ───────────── 세트 1: 밤, 침대 위의 폰 ─────────────
function buildNight() {
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#05060a');
  scene.fog = new THREE.FogExp2('#05060a', .35);
  // 이불 (주름)
  const sg = new THREE.PlaneGeometry(4, 4, 260, 260); const pa = sg.attributes.position;
  for (let i = 0; i < pa.count; i++) { const x = pa.getX(i), y = pa.getY(i); const d = Math.hypot(x, y);
    const z = .012 * Math.sin(x * 9 + Math.sin(y * 3) * 2) + .008 * Math.sin(y * 13 + x * 4) + .02 * Math.sin(x * 2.3 - y * 1.7) * Math.min(1, d * 3) + .004 * Math.sin(x * 31 + y * 17);
    pa.setZ(i, d < .12 ? z * d / .12 : z); }
  sg.computeVertexNormals();
  const sheet = new THREE.Mesh(sg, new THREE.MeshStandardMaterial({ map: tex(fabricCanvas('#252a36'), { rep: [30, 30] }), roughness: .92, color: '#5a6275' }));
  sheet.rotation.x = -Math.PI / 2; sheet.position.y = -.004; sheet.receiveShadow = true; scene.add(sheet);
  // 베개
  const pillow = new THREE.Mesh(new RoundedBoxGeometry(.62, .14, .4, 8, .07), sheet.material);
  pillow.position.set(-.12, .05, -.55); pillow.rotation.y = .25; pillow.scale.y = .8; scene.add(pillow);
  // 폰
  const phone = new THREE.Group();
  const body = new THREE.Mesh(new RoundedBoxGeometry(.075, .0085, .158, 6, .0042), new THREE.MeshPhysicalMaterial({ color: '#1b1c20', metalness: .7, roughness: .28, clearcoat: 1 }));
  phone.add(body);
  feedTex = tex(feedC); drawFeed(0, 0);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(.0705, .1535), new THREE.MeshBasicMaterial({ map: feedTex, toneMapped: false }));
  screen.rotation.x = -Math.PI / 2; screen.position.y = .00435; phone.add(screen);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(.0735, .1565), new THREE.MeshPhysicalMaterial({ color: '#000', roughness: .04, metalness: 0, clearcoat: 1, transparent: true, opacity: .18 }));
  glass.rotation.x = -Math.PI / 2; glass.position.y = .0045; phone.add(glass);
  phone.rotation.y = .18; phone.traverse(o => { o.castShadow = true; }); scene.add(phone);
  // 화면 빛
  RectAreaLightUniformsLib.init();
  const glow = new THREE.RectAreaLight('#b9ccff', 10, .07, .15); glow.position.set(0, .006, 0); glow.lookAt(0, 1, 0); phone.add(glow);
  const spill = new THREE.PointLight('#8fb0ff', .12, 1.2, 2); spill.position.set(0, .08, 0); phone.add(spill);
  // 멀리 보이는 창밖 불빛 (보케)
  const r = rng(21);
  for (let i = 0; i < 40; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(.012 + r() * .01, 8, 8), new THREE.MeshBasicMaterial({ color: new THREE.Color().setHSL(.08 + r() * .06, .8, .55 + r() * .2) }));
    m.position.set((r() - .5) * 2.4, .25 + r() * .5, -1.2 - r() * .6); scene.add(m); }
  scene.add(new THREE.HemisphereLight('#2a3350', '#000', .05));
  sets.night = { scene, env: .04, glow, screen, spill };
}

// ───────────── 세트 2: 아침 테이블 ─────────────
function buildTable() {
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#d9c7ad');
  const wood = tex(woodCanvas(), { rep: [1, 1] });
  const table = new THREE.Mesh(new THREE.BoxGeometry(4, .05, 2.2), new THREE.MeshPhysicalMaterial({ map: wood, roughness: .5, clearcoat: .35, clearcoatRoughness: .4 }));
  table.position.y = -.025; table.receiveShadow = true; scene.add(table);
  // 뒤쪽 벽 + 창
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(8, 4), new THREE.MeshStandardMaterial({ color: '#cdb899', roughness: 1 }));
  wall.position.set(0, 1, -1.4); scene.add(wall);
  const win = new THREE.Mesh(new THREE.PlaneGeometry(1.6, 1.3), new THREE.MeshBasicMaterial({ color: '#fff6e2', toneMapped: false }));
  win.position.set(.9, .95, -1.39); scene.add(win);
  const plant = new THREE.Mesh(new THREE.SphereGeometry(.28, 16, 12), new THREE.MeshStandardMaterial({ color: '#3f5a36', roughness: .9 }));
  plant.position.set(-.9, .3, -1.05); plant.scale.set(1, 1.3, .8); scene.add(plant);
  // 햇빛 + 블라인드 그림자
  const sun = new THREE.DirectionalLight('#ffd7a6', 3.2); sun.castShadow = true;
  sun.shadow.mapSize.set(4096, 4096); Object.assign(sun.shadow.camera, { left: -1.8, right: 1.8, top: 1.4, bottom: -1.4, near: .1, far: 8 });
  sun.shadow.radius = 3; sun.shadow.bias = -.0004; sun.shadow.normalBias = .01; scene.add(sun); scene.add(sun.target);
  const blinds = new THREE.Group(); const bm = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false });
  for (let i = 0; i < 18; i++) { const b = new THREE.Mesh(new THREE.BoxGeometry(3.4, .028, .004), bm); b.position.y = (i - 9) * .06; b.castShadow = true; blinds.add(b); }
  scene.add(blinds);
  scene.add(new THREE.HemisphereLight('#fff1dc', '#6b4a2e', .55));
  const fill = new THREE.PointLight('#ffe2bd', .6, 6, 2); fill.position.set(-1.5, 1.2, 1.5); scene.add(fill);

  // 신문 (살짝 휘어진 종이)
  const ng = new THREE.PlaneGeometry(.37, .5, 60, 80); const np = ng.attributes.position;
  for (let i = 0; i < np.count; i++) { const x = np.getX(i), y = np.getY(i); np.setZ(i, .006 * Math.cos(x * 9) + .004 * Math.sin(y * 7 + 1) + (Math.abs(x) < .004 ? -.002 : 0) + .012 * Math.pow(Math.max(0, x - .12) / .065, 2)); }
  ng.computeVertexNormals();
  const paper = new THREE.Mesh(ng, new THREE.MeshStandardMaterial({ map: tex(newspaperCanvas()), roughness: .92, side: THREE.DoubleSide }));
  paper.rotation.set(-Math.PI / 2, 0, .1); paper.position.set(0, .002, 0); paper.castShadow = paper.receiveShadow = true; scene.add(paper);
  const under = new THREE.Mesh(new THREE.PlaneGeometry(.37, .5), new THREE.MeshStandardMaterial({ color: '#e6dfcf', roughness: .95 }));
  under.rotation.set(-Math.PI / 2, 0, .16); under.position.set(.012, .0008, .008); under.receiveShadow = true; scene.add(under);

  // 커피잔 + 받침
  const ceramic = new THREE.MeshPhysicalMaterial({ color: '#f4f1ea', roughness: .18, clearcoat: 1, clearcoatRoughness: .08 });
  const prof = []; for (let i = 0; i <= 24; i++) { const v = i / 24; prof.push(new THREE.Vector2(.028 + .013 * Math.pow(v, .8), v * .075)); }
  for (let i = 24; i >= 0; i--) { const v = i / 24; prof.push(new THREE.Vector2(.0255 + .013 * Math.pow(v, .8), .003 + v * .072)); }
  const cup = new THREE.Mesh(new THREE.LatheGeometry(prof, 72), ceramic); cup.castShadow = cup.receiveShadow = true;
  const handle = new THREE.Mesh(new THREE.TorusGeometry(.017, .0045, 16, 40, Math.PI * 1.2), ceramic); handle.rotation.z = -Math.PI * .6; handle.position.set(.044, .04, 0); handle.castShadow = true;
  const coffee = new THREE.Mesh(new THREE.CircleGeometry(.0385, 64), new THREE.MeshPhysicalMaterial({ color: '#2a160b', roughness: .05, clearcoat: 1 }));
  coffee.rotation.x = -Math.PI / 2; coffee.position.y = .064;
  const crema = new THREE.Mesh(new THREE.RingGeometry(.03, .0386, 64), new THREE.MeshStandardMaterial({ color: '#6b3d1e', roughness: .4 })); crema.rotation.x = -Math.PI / 2; crema.position.y = .0642;
  const sp = []; for (let i = 0; i <= 20; i++) { const v = i / 20; sp.push(new THREE.Vector2(v * .078, .002 + .008 * Math.pow(v, 3) + (v > .35 && v < .45 ? -.001 : 0))); }
  const saucer = new THREE.Mesh(new THREE.LatheGeometry(sp, 72), ceramic); saucer.castShadow = saucer.receiveShadow = true;
  const cupG = new THREE.Group(); cupG.add(cup, handle, coffee, crema, saucer); cupG.position.set(.27, 0, -.14); cupG.rotation.y = -.6; scene.add(cupG);
  // 김 (steam)
  const [sc, sg2] = canvas(256, 512); const grd = sg2.createRadialGradient(128, 256, 10, 128, 256, 128);
  grd.addColorStop(0, 'rgba(255,255,255,.55)'); grd.addColorStop(1, 'rgba(255,255,255,0)'); sg2.fillStyle = grd; sg2.fillRect(0, 0, 256, 512);
  const steamMat = new THREE.MeshBasicMaterial({ map: tex(sc), transparent: true, depthWrite: false, opacity: .3 });
  const steam = []; for (let i = 0; i < 9; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(.05, .1), steamMat.clone()); scene.add(m); steam.push(m); }

  // 노트 + 만년필
  noteTex = tex(noteC); drawNote(0);
  const note = new THREE.Mesh(new THREE.BoxGeometry(.21, .006, .28), [0, 0, new THREE.MeshStandardMaterial({ map: noteTex, roughness: .95 }), 0, 0, 0].map(m => m || new THREE.MeshStandardMaterial({ color: '#e9e3d4', roughness: .95 })));
  note.position.set(-.62, .003, .12); note.rotation.y = .05; note.castShadow = note.receiveShadow = true; scene.add(note);
  const pen = new THREE.Group();
  const black = new THREE.MeshPhysicalMaterial({ color: '#0d0d10', roughness: .15, clearcoat: 1 });
  const gold = new THREE.MeshStandardMaterial({ color: '#d6b36a', metalness: 1, roughness: .25 });
  const barrel = new THREE.Mesh(new THREE.CylinderGeometry(.0058, .005, .12, 32), black); barrel.position.y = .075;
  const band = new THREE.Mesh(new THREE.CylinderGeometry(.0062, .0062, .004, 32), gold); band.position.y = .02;
  const grip = new THREE.Mesh(new THREE.CylinderGeometry(.005, .0036, .018, 32), black); grip.position.y = .009;
  const nib = new THREE.Mesh(new THREE.ConeGeometry(.0034, .012, 24), gold); nib.rotation.x = Math.PI; nib.position.y = -.004;
  pen.add(barrel, band, grip, nib); pen.traverse(o => o.castShadow = true); scene.add(pen);

  // 필름 카메라 + 인화 사진
  const cam = new THREE.Group();
  const silver = new THREE.MeshStandardMaterial({ color: '#c9ccd0', metalness: 1, roughness: .28 });
  const leather = new THREE.MeshStandardMaterial({ color: '#141414', roughness: .75, map: tex(noiseCanvas(256, 256, 7, 60, 70), { rep: [4, 3] }) });
  const lower = new THREE.Mesh(new RoundedBoxGeometry(.138, .058, .036, 4, .005), leather); lower.position.y = .029;
  const top = new THREE.Mesh(new RoundedBoxGeometry(.14, .024, .037, 4, .005), silver); top.position.y = .068;
  const bottom = new THREE.Mesh(new RoundedBoxGeometry(.14, .006, .037, 4, .002), silver); bottom.position.y = .002;
  const lensRings = [[.024, .006, silver], [.022, .016, new THREE.MeshStandardMaterial({ color: '#111', roughness: .5 })], [.021, .006, silver], [.018, .012, new THREE.MeshStandardMaterial({ color: '#0a0a0a', roughness: .35 })]];
  let lz = .018; const lens = new THREE.Group();
  for (const [r0, h0, m] of lensRings) { const c = new THREE.Mesh(new THREE.CylinderGeometry(r0, r0, h0, 48), m); c.rotation.x = Math.PI / 2; c.position.z = lz + h0 / 2; lz += h0; lens.add(c); }
  const glassL = new THREE.Mesh(new THREE.CircleGeometry(.0165, 48), new THREE.MeshPhysicalMaterial({ color: '#0b1a2a', roughness: 0, metalness: .2, clearcoat: 1, iridescence: .6 }));
  glassL.position.z = lz + .0005; lens.add(glassL); lens.position.set(-.004, .036, 0);
  const vf = new THREE.Mesh(new THREE.PlaneGeometry(.022, .012), new THREE.MeshPhysicalMaterial({ color: '#223', roughness: 0, clearcoat: 1 })); vf.position.set(-.045, .069, .0187);
  const rf = vf.clone(); rf.position.x = .038;
  const dial = new THREE.Mesh(new THREE.CylinderGeometry(.011, .011, .008, 40), silver); dial.position.set(.042, .084, -.004);
  const btn = new THREE.Mesh(new THREE.CylinderGeometry(.004, .004, .006, 24), silver); btn.position.set(.024, .083, .004);
  const knob = new THREE.Mesh(new THREE.CylinderGeometry(.009, .009, .01, 40), silver); knob.position.set(-.05, .085, -.004);
  cam.add(lower, top, bottom, lens, vf, rf, dial, btn, knob); cam.traverse(o => o.castShadow = o.receiveShadow = true);
  cam.position.set(.8, 0, .22); cam.rotation.y = .75; scene.add(cam);
  const prints = [];
  [[.68, .3, .5, 0], [.9, .36, -.35, 1], [.74, .12, .2, 2], [.95, .12, 1.1, 3]].forEach(([x, z, ry, k]) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(.1, .0012, .12), [0, 0, new THREE.MeshStandardMaterial({ map: tex(printCanvas(k)), roughness: .45 }), 0, 0, 0].map(q => q || new THREE.MeshStandardMaterial({ color: '#f2eee6' })));
    m.position.set(x, .0008 + k * .0013, z); m.rotation.y = ry; m.castShadow = m.receiveShadow = true; scene.add(m); prints.push(m);
  });

  // 턴테이블
  const tt = new THREE.Group(); tt.position.set(-1.35, 0, -.25);
  const walnut = new THREE.MeshPhysicalMaterial({ map: wood, color: '#8a5a38', roughness: .45, clearcoat: .6 });
  const plinth = new THREE.Mesh(new RoundedBoxGeometry(.46, .08, .37, 4, .008), walnut); plinth.position.y = .04;
  const platter = new THREE.Mesh(new THREE.CylinderGeometry(.152, .152, .018, 96), silver); platter.position.set(-.05, .089, 0);
  const rec = new THREE.Mesh(new THREE.CylinderGeometry(.151, .151, .002, 128), [new THREE.MeshStandardMaterial({ color: '#050505' }), new THREE.MeshPhysicalMaterial({ map: tex(recordCanvas()), roughness: .28, clearcoat: 1, clearcoatRoughness: .15 }), new THREE.MeshStandardMaterial({ color: '#050505' })]);
  rec.position.set(-.05, .099, 0);
  const spindle = new THREE.Mesh(new THREE.CylinderGeometry(.0035, .0035, .016, 16), silver); spindle.position.set(-.05, .104, 0);
  const pivot = new THREE.Mesh(new THREE.CylinderGeometry(.018, .022, .03, 32), silver); pivot.position.set(.16, .095, -.11);
  const arm = new THREE.Group(); arm.position.set(.16, .112, -.11);
  const tube = new THREE.Mesh(new THREE.CylinderGeometry(.0035, .0035, .22, 16), silver); tube.rotation.z = Math.PI / 2; tube.position.x = -.11; arm.add(tube);
  const head = new THREE.Mesh(new THREE.BoxGeometry(.03, .008, .016), new THREE.MeshStandardMaterial({ color: '#222', roughness: .4 })); head.position.set(-.225, -.006, 0); arm.add(head);
  const cw = new THREE.Mesh(new THREE.CylinderGeometry(.012, .012, .025, 32), silver); cw.rotation.z = Math.PI / 2; cw.position.x = .03; arm.add(cw);
  arm.rotation.y = -.55;
  tt.add(plinth, platter, rec, spindle, pivot, arm); tt.traverse(o => o.castShadow = o.receiveShadow = true); scene.add(tt);
  const lamp = new THREE.PointLight('#ffb870', 2.2, 2.2, 2); lamp.position.set(-1.1, .55, .2); scene.add(lamp);

  sets.table = { scene, env: .5, sun, blinds, steam, cupG, pen, note, rec, tt, paper, lamp };
}

// ───────────── 세트 3: 밤의 도시 ─────────────
function buildCity() {
  const scene = new THREE.Scene();
  const sky = new THREE.Mesh(new THREE.SphereGeometry(900, 32, 16), new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false,
    vertexShader: 'varying vec3 p; void main(){p=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
    fragmentShader: 'varying vec3 p; void main(){float h=normalize(p).y; vec3 c=mix(vec3(.30,.16,.28),vec3(.02,.03,.09),smoothstep(-.02,.35,h)); gl_FragColor=vec4(c,1.);}' }));
  scene.add(sky); scene.fog = new THREE.FogExp2('#1a1426', .0042);
  const [wc, wg] = canvas(256, 512); wg.fillStyle = '#05070c'; wg.fillRect(0, 0, 256, 512);
  const r = rng(31);
  for (let y = 4; y < 512; y += 16) for (let x = 4; x < 256; x += 16) { if (r() < .28) { wg.fillStyle = r() < .7 ? `hsl(${35 + r() * 15},90%,${55 + r() * 25}%)` : `hsl(${200 + r() * 20},60%,${70 + r() * 20}%)`; wg.fillRect(x, y, 9, 10); } }
  const winTex = tex(wc);
  const bmat = new THREE.MeshStandardMaterial({ color: '#0b0e16', roughness: .7, emissiveMap: winTex, emissive: '#ffffff', emissiveIntensity: 1.1, map: winTex });
  const roof = new THREE.MeshStandardMaterial({ color: '#0a0c12', roughness: .9 });
  for (let gx = -14; gx <= 14; gx++) for (let gz = -30; gz <= 6; gz++) {
    if (gx === 0 || gz % 6 === 0 || gx % 5 === 0) continue; // 도로
    if (r() < .12) continue;
    const w = 6 + r() * 6, d = 6 + r() * 6, h = 8 + Math.pow(r(), 2.2) * 90;
    const g = new THREE.BoxGeometry(w, h, d); const uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w / 16 + r() * 0, uv.getY(i) * h / 32);
    const m = new THREE.Mesh(g, [bmat, bmat, roof, roof, bmat, bmat]); m.position.set(gx * 14 + (r() - .5) * 3, h / 2, gz * 14 + (r() - .5) * 3); scene.add(m);
  }
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(2000, 2000), new THREE.MeshStandardMaterial({ color: '#07080c', roughness: 1 })); ground.rotation.x = -Math.PI / 2; scene.add(ground);
  // 타워
  const tower = new THREE.Group();
  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 3.4, 150, 24), new THREE.MeshStandardMaterial({ color: '#1a1d26', roughness: .5, metalness: .3 })); shaft.position.y = 75;
  const deck = new THREE.Mesh(new THREE.CylinderGeometry(9, 7, 10, 40), new THREE.MeshStandardMaterial({ color: '#10131b', emissive: '#6fb6ff', emissiveIntensity: .9, roughness: .4 })); deck.position.y = 150;
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(.5, 1, 30, 12), shaft.material); mast.position.y = 170;
  const tip = new THREE.Mesh(new THREE.SphereGeometry(1.2, 12, 12), new THREE.MeshBasicMaterial({ color: '#ff3b30' })); tip.position.y = 186;
  tower.add(shaft, deck, mast, tip); tower.position.set(40, 0, -330); scene.add(tower);
  // 자동차 불빛 줄기
  const cars = []; const cm = [new THREE.MeshBasicMaterial({ color: '#ffe3b0' }), new THREE.MeshBasicMaterial({ color: '#ff4030' })];
  for (let i = 0; i < 140; i++) { const k = i % 2; const m = new THREE.Mesh(new THREE.BoxGeometry(.9, .6, 5), cm[k]); const lane = r() < .5 ? 0 : 1; m.position.set(lane ? 2 : -2, .6, 0); scene.add(m); cars.push({ m, off: r() * 500, dir: k ? -1 : 1, x: (k ? 2.5 : -2.5) + (r() - .5), road: r() < .6 ? 0 : Math.floor(r() * 5) - 2 }); }
  scene.add(new THREE.HemisphereLight('#3a3160', '#050507', .4));
  sets.city = { scene, env: .1, cars, tip };
}

// ───────────── 샷 정의 ─────────────
// cam/look: [시작, 끝], focus: 초점 대상(월드 좌표) 또는 거리, ap: 조리개
const SHOTS = [
  { t: [0, 2.5], set: 'night', cam: [V(.05, .11, .24), V(.03, .09, .19)], look: [V(0, 0, .06), V(0, 0, .05)], focusAt: V(0, .004, 0), ap: .012, fov: 38 },
  { t: [2.5, 5], set: 'night', cam: [V(.0, .26, .012), V(.0, .225, .008)], look: [V(0, 0, 0), V(0, 0, 0)], up: V(-.18, 0, -1), focusAt: V(0, .004, 0), ap: .05, fov: 40 },
  { t: [5, 7.5], set: 'night', cam: [V(.12, .28, .42), V(.35, .95, 1.15)], look: [V(0, 0, 0), V(0, 0, -.05)], focusAt: V(0, .004, 0), ap: .01, fov: 36 },
  { t: [8.75, 11.25], set: 'table', cam: [V(1.08, .13, .62), V(1.02, .11, .56)], look: [V(.8, .045, .22), V(.8, .04, .22)], focusAt: V(.8, .04, .24), ap: .035, fov: 34 },
  { t: [11.25, 13.75], set: 'table', cam: [V(-1.2, .16, .12), V(-1.3, .15, .08)], look: [V(-1.4, .09, -.25), V(-1.42, .09, -.25)], focusAt: V(-1.37, .1, -.2), ap: .03, fov: 36 },
  { t: [13.75, 16.25], set: 'table', cam: [V(-.58, .33, .3), V(-.6, .3, .27)], look: [V(-.62, 0, .1), V(-.62, 0, .1)], focusAt: V(-.64, .003, .08), ap: .03, fov: 36 },
  { t: [16.25, 20], set: 'table', cam: [V(.40, .17, .03), V(.36, .15, -.0)], look: [V(.27, .045, -.14), V(.24, .035, -.12)], focusAt: V(.27, .05, -.14), focusTo: V(.05, .0, -.02), ap: .04, fov: 34 },
  { t: [20, 25], set: 'table', cam: [V(.1, .3, .45), V(-.01, .38, .17)], look: [V(.0, 0, .08), V(-.01, 0, -.13)], focusAt: V(0, 0, -.14), ap: .03, fov: 36 },
  { t: [25, 30], set: 'table', cam: [V(-.02, .06, .19), V(.06, .058, .19)], look: [V(-.09, 0, .07), V(-.0, 0, .07)], focusAt: V(-.05, 0, .08), ap: .25, fov: 30 },
  { t: [30, 35], set: 'city', cam: [V(-20, 55, 120), V(-14, 48, 40)], look: [V(10, 20, -200), V(25, 25, -260)], focusDist: 260, ap: .00006, fov: 44 },
  { t: [35, 40.2], set: 'table', cam: [V(.42, .42, .62), V(.32, .36, .5)], look: [V(.05, 0, -.03), V(.05, 0, -.03)], focusAt: V(.08, .02, -.05), ap: .02, fov: 36, sweep: true },
];

// ───────────── 초기화 ─────────────
export async function init(canvasEl) {
  await Promise.all(['900 190px "Noto Serif KR"', '700 30px "Noto Serif KR"', '400 27px "Noto Serif KR"', '700 30px "Noto Sans KR"', '400 24px "Noto Sans KR"', '900 44px "Noto Sans KR"', '400 104px "Nanum Pen Script"'].map(f => document.fonts.load(f, '가나다')));
  renderer = new THREE.WebGLRenderer({ canvas: canvasEl, antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  const pmrem = new THREE.PMREMGenerator(renderer); const envTex = pmrem.fromScene(new RoomEnvironment(), .04).texture;
  buildNight(); buildTable(); buildCity();
  for (const s of Object.values(sets)) { s.scene.environment = envTex; s.scene.environmentIntensity = s.env; }
  camera = new THREE.PerspectiveCamera(38, W / H, .005, 2000);
  composer = new EffectComposer(renderer); composer.setPixelRatio(1); composer.setSize(W, H);
  renderPass = new RenderPass(sets.night.scene, camera); composer.addPass(renderPass);
  bokeh = new BokehPass(sets.night.scene, camera, { focus: 1, aperture: .02, maxblur: .012 }); composer.addPass(bokeh);
  composer.addPass(new OutputPass());
}

export function render(t) {
  const sh = SHOTS.find(s => t >= s.t[0] && t < s.t[1]); if (!sh) return false;
  const p = (t - sh.t[0]) / (sh.t[1] - sh.t[0]); const e = ease(p);
  const S = sets[sh.set];
  camera.fov = sh.fov; camera.near = sh.set === 'city' ? 1 : .005; camera.far = sh.set === 'city' ? 2000 : 20; camera.updateProjectionMatrix();
  camera.position.lerpVectors(sh.cam[0], sh.cam[1], e); camera.up.copy(sh.up ? sh.up.clone().normalize() : V(0, 1, 0));
  camera.lookAt(new THREE.Vector3().lerpVectors(sh.look[0], sh.look[1], e));

  if (sh.set === 'night') {
    const off = 60 * t + 38 * t * t * t / 3; // 가속 스크롤
    drawFeed(off, t > 6.6 ? clamp((t - 6.6) / .9) * .0 : 0);
    const flick = .85 + .15 * Math.sin(t * 23) * clamp((t - 5) / 2);
    S.glow.intensity = 10 * flick; S.screen.material.color.setScalar(flick);
  }
  if (sh.set === 'table') {
    // 햇빛 방향 (마지막 샷은 해가 움직이며 블라인드 그림자가 지나감)
    const a = sh.sweep ? lerp(-.35, .15, e) : .0;
    const dir = V(Math.sin(.9 + a) * 1.1, 1.25, -Math.cos(.9 + a) * 1.1 - .6).normalize();
    S.sun.position.copy(dir.clone().multiplyScalar(4)); S.sun.target.position.set(0, 0, 0);
    S.blinds.position.copy(dir.clone().multiplyScalar(1.3)); S.blinds.lookAt(0, 0, 0);
    S.sun.intensity = sh.sweep ? lerp(2.2, 3.6, e) : 3.2;
    // 레코드 회전
    S.rec.rotation.y = -t * 3.49;
    // 필사: 글씨가 써지고 펜이 따라감
    const wp = clamp((t - 13.9) / 2.2); const tip = drawNote(t < 13.75 ? 0 : wp);
    const u = tip[0] / 1050 - .5, v = tip[1] / 1400 - .5; // 노트 로컬 좌표
    const nx = S.note.position.x + u * .21, nz = S.note.position.z + v * .28;
    S.pen.position.set(nx + .0 + Math.sin(t * 30) * .0006, .007 + Math.abs(Math.sin(t * 17)) * .0015, nz);
    S.pen.rotation.set(-.55, .0, -.5);
    if (t >= 16.2) drawNote(1);
    // 김
    S.steam.forEach((m, i) => { const ph = ((t * .35 + i / S.steam.length) % 1);
      m.position.set(S.cupG.position.x + Math.sin(ph * 6 + i) * .012, .07 + ph * .13, S.cupG.position.z + Math.cos(ph * 5 + i) * .01);
      m.scale.setScalar(.6 + ph * 1.4); m.material.opacity = Math.sin(ph * Math.PI) * .22; m.quaternion.copy(camera.quaternion); });
  }
  if (sh.set === 'city') {
    S.cars.forEach(c => { const z = ((c.off + t * 26 * c.dir) % 500 + 500) % 500 - 420; c.m.position.set(c.road * 70 + c.x, .6, z); });
    S.tip.visible = Math.floor(t * 1.2) % 2 === 0;
  }
  // 피사계 심도
  let fd = sh.focusDist;
  if (!fd) { const f = sh.focusTo ? new THREE.Vector3().lerpVectors(sh.focusAt, sh.focusTo, ease((p - .55) / .35)) : sh.focusAt; fd = camera.position.distanceTo(f); }
  bokeh.uniforms.focus.value = fd; bokeh.uniforms.aperture.value = sh.ap;
  bokeh.uniforms.maxblur.value = sh.set === 'city' ? .02 : .05;
  bokeh.uniforms.nearClip.value = camera.near; bokeh.uniforms.farClip.value = camera.far;
  bokeh.uniforms.aspect.value = W / H;
  renderPass.scene = S.scene; bokeh.scene = S.scene;
  composer.render();
  return true;
}
