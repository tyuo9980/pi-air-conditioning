// The dial angles live in DIAL_TO_ANGLE_MAP in server.py; the UI only knows names.
const SETTINGS = ['COOL', 'HEAT'];
const MODES = ['OFF', 'CONSTANT', 'CYCLE', 'AUTO'];

const tempEl = document.getElementById('temp');
const slider = document.getElementById('slider');
const targetLabel = document.getElementById('targetLabel');
const settingBtns = [...document.querySelectorAll('#setting button')];
const modeBtns = [...document.querySelectorAll('#mode button')];
const modeStatusEl = document.getElementById('modeStatus');
const statusEl = document.getElementById('status');
const cycleCard = document.getElementById('cycleCard');
const cycleOnMinutes = document.getElementById('cycleOnMinutes');
const cycleOffMinutes = document.getElementById('cycleOffMinutes');
const cycleSelects = [cycleOnMinutes, cycleOffMinutes];
const cycleNow = document.getElementById('cycleNow');

// Must stay in sync with the <option> values in index.html.
const CYCLE_MINUTES = ['1', '15', '30', '45', '60', '90', '120'];

let dragging = false;
let sending = false;
let pollController = null;

function setControlsDisabled(disabled) {
  slider.disabled = disabled;
  for (const btn of settingBtns) btn.disabled = disabled;
  for (const btn of modeBtns) btn.disabled = disabled;
  for (const sel of cycleSelects) sel.disabled = disabled;
  cycleNow.disabled = disabled;
}

function formatMinutes(m) {
  if (m < 60) return `${m} min`;
  const hrs = m / 60;
  return `${Number.isInteger(hrs) ? hrs : hrs.toFixed(1)} hr`;
}

const VERB = { COOL: 'Cooling', HEAT: 'Heating' };
const NAME = { OFF: 'Off', COOL: 'Cool', HEAT: 'Heat' };

function modeStatus(s) {
  const setting = s.setting;
  const on = s.dial === setting;
  const target = Number(s.target);
  switch (s.mode) {
    case 'CONSTANT':
      return `${VERB[setting]} constantly`;
    case 'CYCLE': {
      const next = on ? 'Off' : NAME[setting];
      return `Switching to ${next} in ${formatMinutes(Math.ceil(s.cycle.next_switch_in / 60))}`;
    }
    case 'AUTO': {
      if (!on) return `Waiting for ${target.toFixed(1)}°C`;
      if (setting === 'COOL') return `Cooling until below ${(target - s.sway).toFixed(1)}°C`;
      return `Heating until above ${(target + s.sway).toFixed(1)}°C`;
    }
    default:
      return '';
  }
}

function render(s) {
  tempEl.textContent = s.temp === null ? '--' : s.temp.toFixed(1);
  if (!dragging) {
    slider.value = s.target;
    targetLabel.textContent = Number(s.target).toFixed(1);
  }

  const setting = SETTINGS.includes(s.setting) ? s.setting : null;
  for (const btn of settingBtns) {
    btn.setAttribute('aria-pressed', String(btn.dataset.setting === setting));
  }
  const mode = MODES.includes(s.mode) ? s.mode : null;
  for (const btn of modeBtns) {
    btn.setAttribute('aria-pressed', String(btn.dataset.mode === mode));
  }
  modeStatusEl.textContent = modeStatus(s);

  cycleCard.hidden = mode !== 'CYCLE';
  // Ignore a server value that isn't one of the offered options rather than
  // letting the select silently blank itself.
  const onMinutes = String(s.cycle.on_minutes);
  if (CYCLE_MINUTES.includes(onMinutes)) cycleOnMinutes.value = onMinutes;
  const offMinutes = String(s.cycle.off_minutes);
  if (CYCLE_MINUTES.includes(offMinutes)) cycleOffMinutes.value = offMinutes;

  setControlsDisabled(false);

  if (s.position === null || s.position === undefined) {
    statusEl.textContent = 'Dial position unknown';
  } else {
    statusEl.textContent = `Dial at ${s.position}° (${NAME[s.dial] ?? s.dial})`;
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
  setControlsDisabled(true);
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
    setControlsDisabled(false);
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

for (const btn of settingBtns) {
  btn.addEventListener('click', () => send({ setting: btn.dataset.setting }));
}
for (const btn of modeBtns) {
  btn.addEventListener('click', () => send({ mode: btn.dataset.mode }));
}

function sendCycleMinutes() {
  send({
    cycle: {
      on_minutes: Number(cycleOnMinutes.value),
      off_minutes: Number(cycleOffMinutes.value),
    },
  });
}
for (const sel of cycleSelects) sel.addEventListener('change', sendCycleMinutes);
cycleNow.addEventListener('click', () => send({ cycle_now: true }));

load();
setInterval(load, 5000);
