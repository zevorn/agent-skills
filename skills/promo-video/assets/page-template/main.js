// SPDX-FileCopyrightText: Copyright (c) 2026 Process Mission
// SPDX-License-Identifier: MIT

// Page contract read by scripts/render_frames.py:
//   window.FPS, window.DURATION, window.ready, window.renderFrame(frame) -> Promise
//   window.getCues() for sound effects, window.getSubtitles() for SRT export, window.qaText() for text checks.
// Everything on screen is a pure function of the frame number: no timers, no CSS transitions, no unseeded random.

const TIMELINE = await (await fetch('timeline.json')).json();
const FPS = TIMELINE.fps;
const DURATION = TIMELINE.duration;
const params = new URLSearchParams(location.search);
const SCALE = Number(params.get('scale') || 1);

const tl = gsap.timeline({ paused: true });
const hooks = [];
const pending = [];
const cues = [];
const scenesRoot = document.getElementById('scenes');

const T = Object.fromEntries(TIMELINE.scenes.map((scene, index) => {
  const next = TIMELINE.scenes[index + 1];
  return [scene.id, [scene.start, next ? next.start + TIMELINE.overlap : DURATION]];
}));

function add(parent, html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  const node = template.content.firstElementChild;
  parent.appendChild(node);
  return node;
}

const lines = texts => texts.map(text => `<span class="mask"><span>${text}</span></span>`).join('');
const masked = node => node.querySelectorAll('.mask > span');

function rise(targets, at, options = {}) {
  tl.from(targets, { yPercent: 115, duration: .9, ease: 'power3.out', stagger: .09, ...options }, at);
}

function fade(targets, at, options = {}) {
  tl.from(targets, { autoAlpha: 0, y: 24, duration: .7, ease: 'power2.out', stagger: .08, ...options }, at);
}

function scene(id, { fadeIn = .4, fadeOut = .4 } = {}) {
  const [start, end] = T[id];
  const node = add(scenesRoot, `<section class="scene" data-scene="${id}"></section>`);
  tl.fromTo(node, { autoAlpha: 0 }, { autoAlpha: 1, duration: fadeIn, ease: 'power1.out', immediateRender: false }, start);
  if (end < DURATION) tl.to(node, { autoAlpha: 0, duration: fadeOut, ease: 'power1.in' }, end - fadeOut);
  return { node, start, end };
}

// Register a sound-effect cue at an exact picture time; the audio pipeline reads them through getCues().
function cue(type, t, extra = {}) {
  cues.push({ type, t: Math.round(t * 1000) / 1000, ...extra });
}

// Show frame N of an image sequence; dir holds 00000.jpg, 00001.jpg, ... rendered at the target scale.
function sequence(image, dir, count, start, range, { rate = 1, offset = 0 } = {}) {
  hooks.push(time => {
    if (time < range[0] - .5 || time > range[1] + .5) return;
    const index = Math.max(0, Math.min(count - 1, Math.floor((time - start) * FPS * rate + 1e-4) + offset));
    const source = `${dir}/${String(index).padStart(5, '0')}.jpg`;
    if (image.getAttribute('src') !== source) {
      image.setAttribute('src', source);
      pending.push(image.decode().catch(() => {}));
    }
  });
}

function text(node, value) {
  if (node.textContent !== value) node.textContent = value;
}

/* Scene: title */
{
  const { node, start } = scene('title');
  const block = add(node, `<div class="abs" style="left:140px;top:300px">
    <div class="kicker">Process Mission</div>
    <div class="headline" style="margin-top:34px">${lines(['用代码逐帧渲染的', '宣传片'])}</div>
    <div class="subhead" style="margin-top:28px">画面、数据、配乐共用同一条时间轴</div></div>`);
  fade(block.querySelector('.kicker'), start + .3);
  rise(masked(block), start + .5);
  fade(block.querySelector('.subhead'), start + 1.4);
  cue('impact', start + .5, { size: .9 });
}

/* Scene: data points */
{
  const { node, start, end } = scene('points');
  const points = [[0.707, 's', '控制就绪时间'], [101.5, 'Hz', '实际控制频率'], [1.57, 's', '推倒后恢复站立']];
  const head = add(node, `<div class="abs" style="left:140px;top:150px"><div class="headline" style="font-size:64px">${lines(['三项实测'])}</div></div>`);
  rise(masked(head), start + .2);
  points.forEach(([value, unit, label], index) => {
    const card = add(node, `<div class="card" style="left:${140 + index * 560}px;top:360px;width:520px;height:330px">
      <b data-value="${value}" data-digits="${String(value).split('.')[1]?.length || 0}">0</b><span>${label} · ${unit}</span></div>`);
    const at = start + .8 + index * .9;
    fade(card, at, { y: 40 });
    cue('blip', at, { pitch: 1400 + index * 300 });
    const number = card.querySelector('b');
    hooks.push(time => {
      if (time < start - .5 || time > end + .5) return;
      const progress = gsap.parseEase('power2.out')(Math.max(0, Math.min(1, (time - at - .2) / 1.2)));
      text(number, (value * progress).toFixed(Number(number.dataset.digits)));
    });
  });
}

/* Scene: close */
{
  const { node, start } = scene('close');
  const block = add(node, `<div class="abs" style="left:0;right:0;top:400px;text-align:center">
    <div class="headline" style="font-size:110px">${lines(['Process Mission'])}</div>
    <div class="subhead" style="margin-top:24px">进程使命</div></div>`);
  rise(masked(block), start + .4, { duration: 1.1 });
  fade(block.querySelector('.subhead'), start + 1.1);
  cue('impact', start + .4, { size: 1 });
}

/* Subtitles: one full sentence at a time, faded in and out. */
{
  const holder = document.getElementById('subtitles');
  const span = holder.querySelector('span');
  hooks.push(time => {
    const current = TIMELINE.subtitles.find(([a, b]) => time >= a - .25 && time <= b + .25);
    if (!current) { holder.style.opacity = '0'; return; }
    const [a, b, line] = current;
    text(span, line);
    holder.style.opacity = String(Math.max(0, Math.min(1, (time - a + .25) / .25, (b + .25 - time) / .25)));
  });
}

async function renderFrame(frame) {
  const time = frame / FPS;
  tl.time(time, false);
  for (const hook of hooks) hook(time);
  await Promise.all(pending.splice(0));
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

// Text geometry over a time range: overlapping text, text leaving the frame, text on screen too briefly to read.
async function qaText(t0 = 0, t1 = DURATION, step = .1, selector = '.headline, .subhead, .kicker, .card, #subtitles span') {
  const stage = document.getElementById('stage').getBoundingClientRect();
  const elements = [...document.querySelectorAll(selector)];
  const visible = element => {
    let alpha = 1;
    for (let node = element; node && node.id !== 'stage'; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') return 0;
      alpha *= Number(style.opacity);
    }
    return alpha;
  };
  const name = element => `${element.className || element.tagName}「${(element.textContent || '').trim().slice(0, 16)}」`;
  const life = new Map(), overlaps = new Map(), offscreen = new Map();
  for (let time = t0; time <= t1 + 1e-6; time += step) {
    await renderFrame(Math.round(time * FPS));
    const shown = [];
    for (const element of elements) {
      if (visible(element) < .3 || !(element.textContent || '').trim()) continue;
      const r = element.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) continue;
      const box = { element, x0: r.left - stage.left, y0: r.top - stage.top, x1: r.right - stage.left, y1: r.bottom - stage.top };
      shown.push(box);
      const seen = life.get(element) || { first: time, last: time };
      seen.last = time;
      life.set(element, seen);
      if (box.x0 < -4 || box.y0 < -4 || box.x1 > stage.width + 4 || box.y1 > stage.height + 4) {
        const record = offscreen.get(element) || { at: time, to: time };
        record.to = time;
        offscreen.set(element, record);
      }
    }
    for (let i = 0; i < shown.length; i++) for (let j = i + 1; j < shown.length; j++) {
      const a = shown[i], b = shown[j];
      if (a.element.contains(b.element) || b.element.contains(a.element)) continue;
      const w = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0), h = Math.min(a.y1, b.y1) - Math.max(a.y0, b.y0);
      if (w <= 2 || h <= 2) continue;
      const key = `${name(a.element)} × ${name(b.element)}`;
      const record = overlaps.get(key) || { at: time, to: time };
      record.to = time;
      overlaps.set(key, record);
    }
  }
  const round = value => Math.round(value * 100) / 100;
  return {
    overlaps: [...overlaps].map(([pair, r]) => ({ pair, at: round(r.at), to: round(r.to) })),
    offscreen: [...offscreen].map(([element, r]) => ({ element: name(element), at: round(r.at), to: round(r.to) })),
    brief: [...life].filter(([, r]) => r.last - r.first + step < .8).map(([element, r]) => ({ element: name(element), at: round(r.first) })),
    never: elements.filter(element => !life.has(element) && (element.textContent || '').trim()).map(name),
  };
}

window.FPS = FPS;
window.DURATION = DURATION;
window.SCALE = SCALE;
window.renderFrame = renderFrame;
window.getCues = () => [...cues].sort((a, b) => a.t - b.t);
window.getSubtitles = () => TIMELINE.subtitles;
window.qaText = qaText;

const sample = document.getElementById('stage').textContent + TIMELINE.subtitles.map(row => row[2]).join('') + '0123456789.';
await Promise.all(['400', '500', '800'].map(weight => document.fonts.load(`${weight} 40px "Noto Sans SC Variable"`, sample)));
await document.fonts.load('600 40px "JetBrains Mono Variable"', '0123456789.');
await document.fonts.ready;
await renderFrame(params.has('t') ? Math.round(Number(params.get('t')) * FPS) : 0);
window.ready = true;

if (params.has('dev') && !params.has('render')) {
  const dev = document.getElementById('dev');
  const scrub = document.getElementById('scrub');
  const clock = document.getElementById('clock');
  const play = document.getElementById('play');
  dev.hidden = false;
  scrub.max = DURATION;
  let time = Number(params.get('t') || 0);
  let playing = false;
  let last = 0;
  const go = async value => {
    time = Math.max(0, Math.min(DURATION, value));
    scrub.value = time;
    clock.textContent = time.toFixed(2);
    await renderFrame(Math.round(time * FPS));
  };
  scrub.addEventListener('input', () => go(Number(scrub.value)));
  play.addEventListener('click', () => { playing = !playing; play.textContent = playing ? '❚❚' : '▶'; last = performance.now(); });
  const loop = async now => {
    if (playing) { await go(time + (now - last) / 1000); last = now; }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
  go(time);
}
