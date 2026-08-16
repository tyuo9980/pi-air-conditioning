// The dial angles live in SETTING_TO_ANGLE_MAP in server.py; the UI only knows mode names.
const MODES = ['OFF', 'EXH', 'HEAT', 'LO_COOL'];

const tempEl = document.getElementById('temp');
const slider = document.getElementById('slider');
const targetLabel = document.getElementById('targetLabel');
const modeBtns = [...document.querySelectorAll('#modes button')];
const statusEl = document.getElementById('status');

let dragging = false;
let sending = false;

function render(s) {
  tempEl.textContent = s.temp === null ? '--' : s.temp.toFixed(1);
  if (!dragging) {
    slider.value = s.target;
    targetLabel.textContent = Number(s.target).toFixed(1);
  }
  slider.disabled = false;

  const mode = MODES.includes(s.mode) ? s.mode : null;
  for (const btn of modeBtns) {
    btn.disabled = false;
    btn.setAttribute('aria-pressed', String(btn.dataset.mode === mode));
  }

  if (s.position === null || s.position === undefined) {
    statusEl.textContent = 'Dial position unknown';
  } else {
    statusEl.textContent = 'Dial at ' + s.position + '°';
  }
}

async function load() {
  if (sending) return;  // don't overwrite state mid-command
  try {
    const r = await fetch('/state');
    if (!r.ok) throw new Error(r.status);
    render(await r.json());
  } catch (e) {
    statusEl.textContent = 'Lost connection to the Pi';
  }
}

async function send(patch) {
  sending = true;
  slider.disabled = true;
  for (const btn of modeBtns) btn.disabled = true;
  statusEl.textContent = 'Adjusting…';
  try {
    const r = await fetch('/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!r.ok) throw new Error(r.status);
    render(await r.json());
  } catch (e) {
    statusEl.textContent = 'Command failed';
    slider.disabled = false;
    for (const btn of modeBtns) btn.disabled = false;
  } finally {
    sending = false;
  }
}

slider.addEventListener('pointerdown', () => { dragging = true; });
slider.addEventListener('input', () => {
  dragging = true;
  targetLabel.textContent = Number(slider.value).toFixed(1);
});
slider.addEventListener('change', () => {
  dragging = false;
  send({ target: Number(slider.value) });
});

for (const btn of modeBtns) {
  btn.addEventListener('click', () => send({ mode: btn.dataset.mode }));
}

load();
setInterval(load, 5000);
