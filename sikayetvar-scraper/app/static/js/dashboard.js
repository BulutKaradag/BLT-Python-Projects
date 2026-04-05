/**
 * Şikayetvar Dashboard – Ana JavaScript Modülü
 * Chart.js tabanlı, tamamen reactive, filtrelenebilir analiz dashboardı
 */

'use strict';

// ══════════════════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════════════════
const STATE = {
  currentPage: 1,
  pageSize: 50,
  totalRecords: 0,
  sortKey: 'tarih',
  sortAsc: false,
  filter: {
    arama: '',
    durum: '',
    duygu: '',
    aciliyet: '',
    tarih_baslangic: '',
    tarih_bitis: '',
  },
  scraping: false,
  charts: {},
  complaints: []   // cached for modal
};

// ══════════════════════════════════════════════════════════
// API HELPERS
// ══════════════════════════════════════════════════════════
const API = {
  base: '',

  async get(path) {
    const res = await fetch(this.base + path);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${path}`);
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(this.base + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return res.json();
  },

  /** Complaint list with current state filters */
  complaintsUrl() {
    const p = new URLSearchParams({
      limit:  STATE.pageSize,
      offset: (STATE.currentPage - 1) * STATE.pageSize,
      siralama: STATE.sortKey,
      artan: STATE.sortAsc,
      ...(STATE.filter.arama           && { arama: STATE.filter.arama }),
      ...(STATE.filter.durum           && { durum: STATE.filter.durum }),
      ...(STATE.filter.duygu           && { duygu: STATE.filter.duygu }),
      ...(STATE.filter.tarih_baslangic && { tarih_baslangic: STATE.filter.tarih_baslangic }),
      ...(STATE.filter.tarih_bitis     && { tarih_bitis:     STATE.filter.tarih_bitis }),
    });
    return `/api/complaints?${p}`;
  }
};

// ══════════════════════════════════════════════════════════
// CHART DEFAULTS
// ══════════════════════════════════════════════════════════
Chart.defaults.color = '#64748b';
Chart.defaults.borderColor = 'rgba(0,0,0,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;

const COLORS = {
  blue:   '#2563eb',
  cyan:   '#0891b2',
  purple: '#7c3aed',
  green:  '#059669',
  orange: '#d97706',
  red:    '#dc2626',
  muted:  '#94a3b8',
};

function destroyChart(key) {
  if (STATE.charts[key]) {
    STATE.charts[key].destroy();
    delete STATE.charts[key];
  }
}

// ══════════════════════════════════════════════════════════
// KPI RENDERING
// ══════════════════════════════════════════════════════════
function renderKPIs(stats) {
  animateNumber('kpi-toplam',     stats.toplam      || 0);
  animateNumber('kpi-beklemede',  stats.beklemede   || 0);
  animateNumber('kpi-reddedildi', stats.reddedildi  || 0);
  animateNumber('kpi-negatif',    stats.negatif     || 0);
  animateNumber('kpi-pozitif',    stats.pozitif     || 0);

  const oran = stats.cozum_orani || 0;
  document.getElementById('kpi-cozum').textContent = `%${oran}`;
  document.getElementById('kpi-cozum-sub').textContent =
    `${stats.cozuldu || 0} şikayet çözüldü`;
}

function animateNumber(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseInt(el.textContent) || 0;
  const duration = 600;
  const startTime = performance.now();

  function step(now) {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(start + (target - start) * ease).toLocaleString('tr-TR');
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ══════════════════════════════════════════════════════════
// TREND CHART (Line)
// ══════════════════════════════════════════════════════════
function renderTrendChart(aylikTrend) {
  destroyChart('trend');
  const ctx = document.getElementById('chart-trend');
  if (!ctx) return;

  const labels = aylikTrend.map(d => {
    const [y, m] = d.ay.split('-');
    return new Date(y, m - 1, 1).toLocaleDateString('tr-TR', { month: 'short', year: 'numeric' });
  });
  const data = aylikTrend.map(d => d.sayi);

  STATE.charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Şikayet Sayısı',
        data,
        borderColor: COLORS.blue,
        backgroundColor: 'rgba(59,130,246,0.08)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: COLORS.blue,
        pointRadius: 4,
        pointHoverRadius: 7,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#475569',
          borderColor: 'rgba(37,99,235,0.2)',
          borderWidth: 1,
          padding: 12,
          callbacks: {
            label: ctx => ` ${ctx.parsed.y} şikayet`
          }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' } },
        y: {
          grid: { color: 'rgba(0,0,0,0.05)' },
          ticks: { stepSize: 1 }
        }
      }
    }
  });

  document.getElementById('trend-badge').textContent = `${aylikTrend.length} Ay`;
}

// ══════════════════════════════════════════════════════════
// DURUM CHART (Doughnut)
// ══════════════════════════════════════════════════════════
function renderDurumChart(durumDagilimi) {
  destroyChart('durum');
  const ctx = document.getElementById('chart-durum');
  if (!ctx) return;

  const labels = Object.keys(durumDagilimi);
  const data   = Object.values(durumDagilimi);
  const colorMap = {
    'çözüldü':   COLORS.green,
    'beklemede': COLORS.orange,
    'reddedildi':COLORS.red,
    'bilinmiyor':COLORS.muted,
  };
  const colors = labels.map(l => colorMap[l] || COLORS.muted);

  STATE.charts.durum = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.map(c => c + '33'),
        borderColor: colors,
        borderWidth: 2,
        hoverOffset: 8,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 12, boxWidth: 12, font: { size: 11 } }
        },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#475569',
          borderColor: 'rgba(0,0,0,0.1)',
          borderWidth: 1,
        }
      }
    }
  });
}

// ══════════════════════════════════════════════════════════
// DUYGU CHART (Bar horizontal)
// ══════════════════════════════════════════════════════════
function renderDuyguChart(duyguDagilimi) {
  destroyChart('duygu');
  const ctx = document.getElementById('chart-duygu');
  if (!ctx) return;

  const labels = Object.keys(duyguDagilimi);
  const data   = Object.values(duyguDagilimi);
  const colorMap = {
    'pozitif': COLORS.green,
    'negatif': COLORS.red,
    'nötr':    COLORS.muted,
    'analiz edilmedi': '#334155',
  };
  const colors = labels.map(l => colorMap[l] || COLORS.blue);

  STATE.charts.duygu = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.map(c => c + '44'),
        borderColor: colors,
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#ffffff',
          titleColor: '#0f172a',
          bodyColor: '#475569',
          borderColor: 'rgba(0,0,0,0.1)',
          borderWidth: 1,
        }
      },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { stepSize: 1 } },
        y: { grid: { display: false } }
      }
    }
  });
}

// ══════════════════════════════════════════════════════════
// KEYWORD BARS
// ══════════════════════════════════════════════════════════
function renderKeywords(keywords) {
  const container = document.getElementById('keyword-list');
  if (!container) return;

  if (!keywords || keywords.length === 0) {
    container.innerHTML = `
      <div class="empty-state" style="padding:1rem;">
        <span class="empty-icon">🔍</span>
        <p>Anahtar kelime verisi bulunamadı.</p>
      </div>`;
    return;
  }

  const maxVal = keywords[0]?.sayi || 1;
  container.innerHTML = keywords.slice(0, 15).map(kw => `
    <div class="keyword-item">
      <span class="keyword-label">${kw.kelime}</span>
      <div class="keyword-bar-wrap">
        <div class="keyword-bar-fill" style="width:${(kw.sayi / maxVal) * 100}%"></div>
      </div>
      <span class="keyword-count">${kw.sayi}</span>
    </div>
  `).join('');
}

// ══════════════════════════════════════════════════════════
// COMPLAINT TABLE
// ══════════════════════════════════════════════════════════
function renderTable(result) {
  const tbody = document.getElementById('complaint-tbody');
  const { total, data } = result;
  STATE.totalRecords = total;

  document.getElementById('table-count').textContent = `(${total.toLocaleString('tr-TR')} kayıt)`;

  if (!data || data.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="8">
        <div class="empty-state">
          <div class="empty-icon">📭</div>
          <h3>Şikayet bulunamadı</h3>
          <p>Filtreleri değiştirin veya önce scraping başlatın.</p>
        </div>
      </td></tr>`;
    renderPagination(0);
    return;
  }

  STATE.complaints = data;

  tbody.innerHTML = data.map((s, i) => `
    <tr class="clickable" onclick="modalAc(${i})">
      <td style="white-space:nowrap;font-family:'JetBrains Mono',monospace;font-size:0.78rem;">
        ${s.tarih || '—'}
      </td>
      <td class="td-baslik">
        <a href="javascript:void(0)">${escHtml(s.baslik)}</a>
      </td>
      <td>${durumBadge(s.durum)}</td>
      <td>${duyguBadge(s.duygu)}</td>
      <td>${aciliyetBadge(s.aciliyet)}</td>
      <td style="text-align:center;">${s.begeni_sayisi || 0}</td>
      <td style="text-align:center;">${s.yorum_sayisi || 0}</td>
      <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:0.78rem;color:var(--text-muted);">
        ${escHtml(s.ana_sorun || '—')}
      </td>
    </tr>
  `).join('');

  renderPagination(total);
}

// ─── Badge helpers ────────────────────────────────────────
function escHtml(str) {
  return String(str || '')
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

function durumBadge(durum) {
  const map = {
    'çözüldü':   ['badge-cozuldu',   '✅ Çözüldü'],
    'beklemede': ['badge-beklemede', '⏳ Beklemede'],
    'reddedildi':['badge-reddedildi','🚫 Reddedildi'],
  };
  const [cls, label] = map[durum] || ['badge-bilinmiyor', '❓ Bilinmiyor'];
  return `<span class="badge ${cls}">${label}</span>`;
}

function duyguBadge(duygu) {
  const map = {
    'pozitif': ['badge-pozitif', '😊 Pozitif'],
    'negatif': ['badge-negatif', '😡 Negatif'],
    'nötr':    ['badge-notr',    '😐 Nötr'],
  };
  const [cls, label] = map[duygu] || ['badge-bilinmiyor', '⏳ Analiz edilmedi'];
  return `<span class="badge ${cls}">${label}</span>`;
}

function aciliyetBadge(aciliyet) {
  const map = {
    'yüksek': ['badge-yuksek', '🔴 Yüksek'],
    'orta':   ['badge-orta',   '🟡 Orta'],
    'düşük':  ['badge-dusuk',  '🟢 Düşük'],
  };
  const [cls, label] = map[aciliyet] || ['badge-bilinmiyor', '—'];
  return `<span class="badge ${cls}">${label}</span>`;
}

// ══════════════════════════════════════════════════════════
// COMPLAINT DETAIL MODAL
// ══════════════════════════════════════════════════════════
function modalAc(idx) {
  const s = STATE.complaints[idx];
  if (!s) return;
  modalDoldur(s);
  document.getElementById('complaint-modal').classList.add('open');
  document.getElementById('modal-backdrop').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function modalKapat() {
  document.getElementById('complaint-modal').classList.remove('open');
  document.getElementById('modal-backdrop').classList.remove('open');
  document.body.style.overflow = '';
}

function modalDoldur(s) {
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
    return el;
  };

  const setHtml = (id, html) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = html;
  };

  // Title & date
  setEl('modal-title', s.baslik || 'Başlıksız');
  setEl('modal-date', s.tarih ? `📅 ${s.tarih}` : '');

  // Badges
  setHtml('modal-badges',
    durumBadge(s.durum) + ' ' +
    duyguBadge(s.duygu) + ' ' +
    aciliyetBadge(s.aciliyet)
  );

  // İçerik
  setEl('modal-icerik', s.icerik || 'İçerik mevcut değil.');

  // Meta
  setEl('modal-ana-sorun', s.ana_sorun || '—');
  setEl('modal-begeni', (s.begeni_sayisi || 0).toLocaleString('tr-TR'));
  setEl('modal-yorum', (s.yorum_sayisi || 0).toLocaleString('tr-TR'));
  
  const yontemLabel = s.analiz_yontemi === 'gemini' ? '✨ Google Gemini' :
    s.analiz_yontemi === 'ollama' ? '🤖 Ollama/Qwen' :
    s.analiz_yontemi === 'keyword' ? '🔑 Keyword' : '—';
  setEl('modal-yontem', yontemLabel);

  // Duygu skoru bar
  const skor = parseFloat(s.duygu_skoru) || 0;
  const pct = Math.round((skor + 1) / 2 * 100);
  const barEl = document.getElementById('modal-score-bar');
  if (barEl) {
    const color = skor < -0.1 ? '#dc2626' : skor > 0.1 ? '#059669' : '#94a3b8';
    barEl.style.cssText = `width:${pct}%;background:${color};left:0;`;
  }
  setEl('modal-duygu-skor', `${skor >= 0 ? '+' : ''}${skor.toFixed(2)}`);

  // Anahtar kelimeler
  const kws = s.anahtar_kelimeler || [];
  const kwsSec = document.getElementById('modal-keywords-section');
  if (kwsSec) {
    if (kws.length) {
      const kwsEl = document.getElementById('modal-keywords');
      if (kwsEl) kwsEl.innerHTML = kws.map(k => `<span class="kw-chip">#${escHtml(k)}</span>`).join('');
      kwsSec.style.display = 'flex';
    } else {
      kwsSec.style.display = 'none';
    }
  }

  // External link
  const linkEl = document.getElementById('modal-link');
  const urlSec = document.getElementById('modal-url-section');
  const urlText = document.getElementById('modal-url-text');
  
  if (s.url) {
    if (linkEl) {
      linkEl.href = s.url;
      linkEl.style.display = 'inline-flex';
    }
    if (urlText) {
      urlText.textContent = s.url;
      urlText.href = s.url;
    }
    if (urlSec) urlSec.style.display = 'flex';
  } else {
    if (linkEl) linkEl.style.display = 'none';
    if (urlSec) urlSec.style.display = 'none';
  }
}

// ESC to close
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') modalKapat();
});

// ══════════════════════════════════════════════════════════
// PAGINATION
// ══════════════════════════════════════════════════════════
function renderPagination(total) {
  const totalPages = Math.ceil(total / STATE.pageSize);
  const cur = STATE.currentPage;

  document.getElementById('pagination-info').textContent =
    `${((cur - 1) * STATE.pageSize) + 1}–${Math.min(cur * STATE.pageSize, total)} / ${total.toLocaleString('tr-TR')} kayıt`;

  const ctrl = document.getElementById('pagination-controls');
  if (totalPages <= 1) { ctrl.innerHTML = ''; return; }

  const pages = buildPageRange(cur, totalPages);
  ctrl.innerHTML = `
    <button class="page-btn" onclick="goPage(${cur - 1})" ${cur <= 1 ? 'disabled' : ''}>‹</button>
    ${pages.map(p => p === '…'
      ? `<button class="page-btn" disabled>…</button>`
      : `<button class="page-btn ${p === cur ? 'active' : ''}" onclick="goPage(${p})">${p}</button>`
    ).join('')}
    <button class="page-btn" onclick="goPage(${cur + 1})" ${cur >= totalPages ? 'disabled' : ''}>›</button>
  `;
}

function buildPageRange(cur, total) {
  if (total <= 7) return Array.from({length: total}, (_, i) => i + 1);
  if (cur <= 4)   return [1, 2, 3, 4, 5, '…', total];
  if (cur >= total - 3) return [1, '…', total-4, total-3, total-2, total-1, total];
  return [1, '…', cur-1, cur, cur+1, '…', total];
}

function goPage(page) {
  const totalPages = Math.ceil(STATE.totalRecords / STATE.pageSize);
  if (page < 1 || page > totalPages) return;
  STATE.currentPage = page;
  loadComplaints();
}

// ══════════════════════════════════════════════════════════
// SORT
// ══════════════════════════════════════════════════════════
function toggleSort(key) {
  if (STATE.sortKey === key) {
    STATE.sortAsc = !STATE.sortAsc;
  } else {
    STATE.sortKey = key;
    STATE.sortAsc = false;
  }
  STATE.currentPage = 1;

  // Update header arrows
  document.querySelectorAll('thead th').forEach(th => th.classList.remove('active'));
  const thId = { tarih: 'th-tarih', begeni: 'th-begeni', yorum: 'th-yorum' };
  const el = document.getElementById(thId[key]);
  if (el) {
    el.classList.add('active');
    el.querySelector('.sort-arrow').textContent = STATE.sortAsc ? '↑' : '↓';
  }
  loadComplaints();
}

// ══════════════════════════════════════════════════════════
// FILTERS
// ══════════════════════════════════════════════════════════
function filtreUygula() {
  STATE.filter.arama           = document.getElementById('filter-arama').value.trim();
  STATE.filter.durum           = document.getElementById('filter-durum').value;
  STATE.filter.duygu           = document.getElementById('filter-duygu').value;
  STATE.filter.tarih_baslangic = document.getElementById('filter-baslangic').value;
  STATE.filter.tarih_bitis     = document.getElementById('filter-bitis').value;
  STATE.pageSize               = parseInt(document.getElementById('table-limit').value);
  STATE.currentPage            = 1;
  loadComplaints();
}

function filtreTemizle() {
  document.getElementById('filter-arama').value       = '';
  document.getElementById('filter-durum').value       = '';
  document.getElementById('filter-duygu').value       = '';
  document.getElementById('filter-baslangic').value   = '';
  document.getElementById('filter-bitis').value       = '';
  STATE.filter = { arama:'', durum:'', duygu:'', aciliyet:'', tarih_baslangic:'', tarih_bitis:'' };
  STATE.currentPage = 1;
  loadComplaints();
}

// Enter key on search
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('filter-arama')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') filtreUygula();
  });
});

// ══════════════════════════════════════════════════════════
// SCRAPER
// ══════════════════════════════════════════════════════════
async function scrapeBaslat() {
  if (STATE.scraping) return;
  STATE.scraping = true;

  const btn = document.getElementById('btn-scrape');
  btn.disabled = true;
  btn.textContent = '⏳ Çalışıyor...';
  document.getElementById('scraper-running').style.display = 'flex';

  toast('Scraping başlatıldı! Arka planda devam ediyor.', 'info');

  try {
    await API.post('/api/scraper/run');
    toast('Scraping komutu gönderildi. Tamamlandığında veriler güncellenir.', 'success');

    // Poll every 8 seconds
    const poll = setInterval(async () => {
      try {
        const status = await API.get('/api/scraper/status');
        if (status.toplam_sikayet > 0) {
          clearInterval(poll);
          STATE.scraping = false;
          btn.disabled = false;
          btn.textContent = '🕷️ Scrape Başlat';
          document.getElementById('scraper-running').style.display = 'none';
          await yenile();
          toast(`${status.toplam_sikayet} şikayet yüklendi!`, 'success');
        }
      } catch (_) {}
    }, 8000);

    // Auto-stop poll after 5 min
    setTimeout(() => {
      clearInterval(poll);
      STATE.scraping = false;
      btn.disabled = false;
      btn.textContent = '🕷️ Scrape Başlat';
      document.getElementById('scraper-running').style.display = 'none';
    }, 300000);

  } catch (err) {
    toast('Scraper başlatılamadı: ' + err.message, 'error');
    STATE.scraping = false;
    btn.disabled = false;
    btn.textContent = '🕷️ Scrape Başlat';
    document.getElementById('scraper-running').style.display = 'none';
  }
}

// ══════════════════════════════════════════════════════════
// LOAD DATA
// ══════════════════════════════════════════════════════════
async function loadStats() {
  const stats = await API.get('/api/stats/overview');
  renderKPIs(stats);
  renderTrendChart(stats.aylik_trend || []);
  renderDurumChart(stats.durum_dagilimi || {});
  renderDuyguChart(stats.duygu_dagilimi || {});
  renderKeywords(stats.anahtar_kelimeler || []);

  // Last scrape time
  if (stats.son_scrape) {
    const d = new Date(stats.son_scrape);
    document.getElementById('scraper-last-run').textContent =
      `Son çalışma: ${d.toLocaleString('tr-TR')}`;
  }
}

async function loadComplaints() {
  const result = await API.get(API.complaintsUrl());
  renderTable(result);
}

async function yenile() {
  try {
    document.getElementById('btn-refresh').textContent = '⏳';
    await Promise.all([loadStats(), loadComplaints()]);
    updateStatusBadge(true);
    toast('Veriler güncellendi', 'success');
  } catch (err) {
    updateStatusBadge(false);
    toast('Veri yüklenemedi: ' + err.message, 'error');
  } finally {
    document.getElementById('btn-refresh').textContent = '🔄 Yenile';
  }
}

// ══════════════════════════════════════════════════════════
// STATUS BADGE
// ══════════════════════════════════════════════════════════
function updateStatusBadge(ok) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (ok) {
    dot.style.background  = 'var(--accent-green)';
    dot.style.boxShadow   = '0 0 8px var(--accent-green)';
    text.textContent      = 'Bağlantı OK';
  } else {
    dot.style.background  = 'var(--accent-red)';
    dot.style.boxShadow   = '0 0 8px var(--accent-red)';
    text.textContent      = 'Bağlantı Hatası';
  }
}

// ══════════════════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════════════════
function toast(msg, type = 'info') {
  const typeIcons = { success: '✅', error: '❌', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${typeIcons[type] || ''}</span><span>${msg}</span>`;

  const container = document.getElementById('toast-container');
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(40px)';
    el.style.transition = 'all 0.3s ease';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}


// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
async function init() {
  const overlay = document.getElementById('loading-overlay');

  try {
    // Health check
    await API.get('/api/health');
    updateStatusBadge(true);

    // Load all data
    await Promise.all([loadStats(), loadComplaints()]);

  } catch (err) {
    updateStatusBadge(false);
    console.warn('İlk yükleme hatası:', err.message);
    // Still render empty state
    renderTable({ total: 0, data: [] });
  } finally {
    overlay.classList.add('hidden');
  }
}

// Auto-refresh every 60 seconds
setInterval(async () => {
  try {
    await loadStats();
  } catch (_) {}
}, 60000);

window.addEventListener('DOMContentLoaded', init);
