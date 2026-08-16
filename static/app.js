// The dial angles live in SETTING_TO_ANGLE_MAP in server.py; the UI only knows mode names.
const MODES = ['OFF', 'EXH', 'HEAT', 'LO_COOL'];

const tempEl = document.getElementById('temp');
const slider = document.getElementById('slider');
const targetLabel = document.getElementById('targetLabel');
const modeBtns = [...document.querySelectorAll('#modes button')];
const statusEl = document.getElementById('status');
const cycleOn = document.getElementById('cycleOn');
const cycleMinutes = document.getElementById('cycleMinutes');
const cycleStatusEl = document.getElementById('cycleStatus');

// Must stay in sync with the <option> values in index.html.
const CYCLE_MINUTES = ['1', '30', '60', '120'];

let dragging = false;
let sending = false;
let pollController = null;

function formatMinutes(m) {
  if (m < 60) return `${m} min`;
  const hrs = m / 60;
  return `${Number.isInteger(hrs) ? hrs : hrs.toFixed(1)} hr`;
}

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

  cycleOn.checked = s.cycle.on;
  cycleOn.disabled = false;
  cycleMinutes.disabled = false;
  // Ignore a server value that isn't one of the offered options rather than
  // letting the select silently blank itself.
  const minutes = String(s.cycle.minutes);
  if (CYCLE_MINUTES.includes(minutes)) cycleMinutes.value = minutes;

  if (!s.cycle.on) {
    cycleStatusEl.textContent = '';
  } else {
    const next = mode === 'LO_COOL' ? 'Off' : 'Cool';
    cycleStatusEl.textContent =
      `Switching to ${next} in ${formatMinutes(Math.ceil(s.cycle.next_switch_in / 60))}`;
  }

  if (s.position === null || s.position === undefined) {
    statusEl.textContent = 'Dial position unknown';
  } else {
    statusEl.textContent = 'Dial at ' + s.position + '°';
  }
}

async function load() {
  if (sending) return;  // don't overwrite state mid-command
  const controller = new AbortController();
  pollController = controller;
  try {
    const r = await fetch('/state', { signal: controller.signal });
    if (!r.ok) throw new Error(r.status);
    const s = await r.json();
    if (sending) return;  // a command started while this poll was in flight
    render(s);
  } catch (e) {
    if (e.name === 'AbortError') return;
    statusEl.textContent = 'Lost connection to the Pi';
  } finally {
    if (pollController === controller) pollController = null;
  }
}

async function send(patch) {
  sending = true;
  pollController?.abort();  // a poll already in flight would render pre-command state
  slider.disabled = true;
  cycleOn.disabled = true;
  cycleMinutes.disabled = true;
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
    cycleOn.disabled = false;
    cycleMinutes.disabled = false;
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

function sendCycle() {
  send({ cycle: { on: cycleOn.checked, minutes: Number(cycleMinutes.value) } });
}

cycleOn.addEventListener('change', sendCycle);
cycleMinutes.addEventListener('change', sendCycle);

load();
setInterval(load, 5000);
