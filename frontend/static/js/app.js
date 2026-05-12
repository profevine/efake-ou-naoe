'use strict';

const VERDICT_ICON = { credible: '✅', suspicious: '⚠️', fake: '🔴' };

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'tab-history') loadHistory();
  });
});

// Analyze form
const form = document.getElementById('analyze-form');
const inputEl = document.getElementById('news-input');
const resultEl = document.getElementById('result');
const errorEl = document.getElementById('error-msg');
const submitBtn = document.getElementById('submit-btn');
const spinner = document.getElementById('spinner');

form.addEventListener('submit', async e => {
  e.preventDefault();
  const input = inputEl.value.trim();
  if (!input) return;

  setLoading(true);
  resultEl.style.display = 'none';
  errorEl.style.display = 'none';

  try {
    const resp = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Erro ${resp.status}`);
    }
    const data = await resp.json();
    renderResult(data);
  } catch (err) {
    errorEl.textContent = `Erro ao analisar: ${err.message}`;
    errorEl.style.display = 'block';
  } finally {
    setLoading(false);
  }
});

function setLoading(on) {
  submitBtn.disabled = on;
  spinner.style.display = on ? 'block' : 'none';
}

function renderResult(d) {
  const v = d.verdict;

  // Banner
  const banner = document.getElementById('verdict-banner');
  banner.className = `verdict-banner ${v}`;
  document.getElementById('verdict-icon').textContent = VERDICT_ICON[v] || '❓';
  const labelEl = document.getElementById('verdict-label');
  labelEl.className = `verdict-label ${v}`;
  labelEl.textContent = d.label;
  document.getElementById('verdict-score-text').textContent =
    `Score de risco: ${d.score}/100${d.cached ? '' : ''}`;
  if (d.cached) {
    const badge = document.createElement('span');
    badge.className = 'cache-badge';
    badge.textContent = 'do cache';
    document.getElementById('verdict-score-text').appendChild(badge);
  }

  // Score bar
  const fill = document.getElementById('score-bar-fill');
  fill.className = `score-bar-fill ${v}`;
  fill.style.width = '0%';
  setTimeout(() => { fill.style.width = `${d.score}%`; }, 50);

  // Fact checkers
  const fcList = document.getElementById('fc-list');
  fcList.innerHTML = '';
  if (d.signals.fact_checkers.length === 0) {
    fcList.innerHTML = '<p class="empty-note">Nenhum resultado encontrado nos fact-checkers.</p>';
  } else {
    d.signals.fact_checkers.forEach(fc => {
      const item = document.createElement('div');
      item.className = 'fc-item';
      item.innerHTML = `
        <span class="fc-badge ${fc.result}">${fc.result}</span>
        <div class="fc-info">
          <div class="fc-source">${esc(fc.source)}</div>
          <div class="fc-title"><a href="${esc(fc.url)}" target="_blank" rel="noopener">${esc(fc.title)}</a></div>
        </div>`;
      fcList.appendChild(item);
    });
  }

  // Signals
  const grid = document.getElementById('signals-grid');
  grid.innerHTML = '';
  addSignal(grid, 'Domínio na lista negra',
    d.signals.domain_blacklisted ? 'Sim' : 'Não',
    d.signals.domain_blacklisted ? 'positive' : 'negative');
  addSignal(grid, 'Idade do domínio',
    d.signals.domain_age_days !== null ? `${d.signals.domain_age_days} dias` : 'N/A',
    d.signals.domain_age_days !== null && d.signals.domain_age_days < 90 ? 'positive' : 'negative');
  addSignal(grid, 'Palavras sensacionalistas',
    d.signals.sensationalist_words.length > 0
      ? d.signals.sensationalist_words.slice(0, 4).join(', ')
      : 'Nenhuma',
    d.signals.sensationalist_words.length >= 3 ? 'positive' : 'negative');
  addSignal(grid, 'URL suspeita',
    d.signals.suspicious_url_pattern ? 'Sim' : 'Não',
    d.signals.suspicious_url_pattern ? 'positive' : 'negative');

  resultEl.style.display = 'block';
  resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addSignal(container, key, val, cls) {
  const el = document.createElement('div');
  el.className = 'signal-item';
  el.innerHTML = `<div class="signal-key">${esc(key)}</div><div class="signal-val ${cls}">${esc(val)}</div>`;
  container.appendChild(el);
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function loadHistory() {
  const list = document.getElementById('history-list');
  list.innerHTML = '<p class="empty-note">Carregando...</p>';
  try {
    const resp = await fetch('/history');
    const data = await resp.json();
    if (!data.length) {
      list.innerHTML = '<p class="empty-note">Nenhuma análise realizada ainda.</p>';
      return;
    }
    list.innerHTML = '';
    data.forEach(item => {
      const el = document.createElement('div');
      el.className = 'history-item';
      const date = new Date(item.analyzed_at + 'Z').toLocaleString('pt-BR');
      el.innerHTML = `
        <div class="history-dot ${item.verdict}"></div>
        <div class="history-text">
          <div class="history-input">${esc(item.input)}</div>
          <div class="history-meta">${esc(date)} &middot; ${esc(item.label)}</div>
        </div>
        <div class="history-score ${item.verdict}">${item.score}/100</div>`;
      list.appendChild(el);
    });
  } catch {
    list.innerHTML = '<p class="empty-note">Erro ao carregar histórico.</p>';
  }
}
