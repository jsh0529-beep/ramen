// scene.html 을 프레임 단위로 캡처해 ffmpeg 로 인코딩
// 사용법: node render.mjs [out.mp4] [fps]   |   node render.mjs --stills 3,20,60
// SCENE=shorts/scene.html 로 다른 장면 파일 지정 (크기는 window.SIZE, 기본 1920x1080)
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const FFMPEG = process.env.FFMPEG || 'ffmpeg';
const args = process.argv.slice(2);

// ES 모듈(three.js) 로딩을 위해 file:// 대신 로컬 http 로 제공
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.ttf': 'font/ttf', '.jpg': 'image/jpeg', '.png': 'image/png', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const f = path.join(dir, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const scene = process.env.SCENE || 'scene.html';
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
page.on('pageerror', e => console.error('[pageerror]', e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/${scene}`);
const size = await page.evaluate(() => window.SIZE || [1920, 1080]);
await page.setViewportSize({ width: size[0], height: size[1] });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(() => window.READY);
await page.evaluate(() => Promise.all([...document.images].map(i => i.decode().catch(() => {}))));

if (args[0] === '--stills') {
  for (const t of args[1].split(',').map(Number)) {
    await page.evaluate(t => window.render(t), t);
    await page.screenshot({ path: path.join(dir, 'frames', `still_${t}.jpg`), type: 'jpeg', quality: 85 });
  }
  await browser.close();
  server.close();
  process.exit(0);
}

const out = args[0] || 'video.mp4';
const fps = Number(args[1] || 30);
const dur = await page.evaluate(() => window.DURATION);
const n = Math.round(dur * fps);
// FRAMES=시작:끝 으로 일부 구간만 렌더 (병렬 렌더 후 이어붙이기용)
const [f0, f1] = (process.env.FRAMES || `0:${n}`).split(':').map(Number);
const ff = spawn(FFMPEG, ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', path.join(dir, out)],
  { stdio: ['pipe', 'inherit', 'inherit'] });
for (let i = f0; i < Math.min(f1, n); i++) {
  await page.evaluate(t => window.render(t), i / fps);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % 50 === 0) console.error(`frame ${i}/${n}`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
server.close();
