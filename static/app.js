const tempEl = document.getElementById('temp');
const slider = document.getElementById('slider');
const targetLabel = document.getElementById('targetLabel');
const scaleMin = document.getElementById('scaleMin');
const scaleMax = document.getElementById('scaleMax');
const powerBtn = document.getElementById('power');
const statusEl = document.getElementById('status');

let dragging = false;
let sending = false;

function render(s) {
  tempEl.textContent = s.temp === null ? '--' : s.temp.toFixed(1);
  slider.min = s.min_temp;
  slider.max = s.max_temp;
  scaleMin.textContent = s.min_temp + '°';
  scaleMax.textContent = s.max_temp + '°';
  if (!dragging) {
    slider.value = s.target;
    targetLabel.textContent = Number(s.target).toFixed(1);
  }
  slider.disabled = false;
  powerBtn.disabled = false;
  powerBtn.setAttribute('aria-pressed', String(s.power));
  powerBtn.textContent = s.power ? 'On' : 'Off';
  statusEl.textContent = s.power
    ? 'Dial at ' + Number(s.position).toFixed(0) + '°'
    : 'Idle';
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
  slider.disabled = powerBtn.disabled = true;
  statusEl.textContent = 'Adjusting…';
  try {
    const r = await fetch('/state', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(patch),
    });
    if (!r.ok) throw new Error(r.status);
    render(await r.json());
  } catch (e) {
    statusEl.textContent = 'Command failed';
    slider.disabled = powerBtn.disabled = false;
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
  send({target: Number(slider.value)});
});

powerBtn.addEventListener('click', () => {
  send({power: powerBtn.getAttribute('aria-pressed') !== 'true'});
});

load();
setInterval(load, 5000);
