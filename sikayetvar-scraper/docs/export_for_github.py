"""
GitHub Pages Export Script
--------------------------
Bu script, TinyDB veritabanından şikayet verilerini okuyarak
GitHub Pages'te yayınlanmak üzere docs/index.html dosyasını üretir.

Çalıştır:
    python docs/export_for_github.py
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "sikayetler.json"
DOCS_DIR  = ROOT / "docs"
OUT_PATH  = DOCS_DIR / "index.html"

def load_complaints():
    if not DATA_PATH.exists():
        print(f"[HATA] {DATA_PATH} bulunamadı.")
        return []
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    # TinyDB formatı: {"sikayetler": {"1": {...}, "2": {...}}}
    sikayetler_raw = raw.get("sikayetler", {})
    return list(sikayetler_raw.values())

def build_html(complaints):
    data_json = json.dumps(complaints, ensure_ascii=False, indent=2)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(complaints)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Şikayetvar Analiz Dashboard – Türkiye Katılım Sigorta</title>
  <meta name="description" content="Türkiye Katılım Sigorta şikayetlerini analiz eden dashboard. {total} şikayet analiz edildi." />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
  <style>
    :root {{
      --bg: #0f172a;
      --bg-card: #1e293b;
      --bg-elevated: #273449;
      --border: rgba(148,163,184,0.12);
      --text: #f1f5f9;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent-blue: #3b82f6;
      --accent-cyan: #06b6d4;
      --accent-green: #10b981;
      --accent-red: #ef4444;
      --accent-orange: #f97316;
      --accent-purple: #8b5cf6;
      --radius: 12px;
      --radius-sm: 8px;
      --shadow: 0 4px 20px rgba(0,0,0,0.4);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }}

    /* HEADER */
    .header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border-bottom: 1px solid var(--border);
      padding: 1rem 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky; top: 0; z-index: 100;
      backdrop-filter: blur(12px);
    }}
    .header-logo {{ display: flex; align-items: center; gap: 1rem; }}
    .logo-icon {{ font-size: 2rem; }}
    .header h1 {{ font-size: 1.2rem; font-weight: 700; }}
    .header h1 .subtitle {{ color: var(--text-secondary); font-weight: 500; font-size: 0.95rem; }}
    .header-meta {{ font-size: 0.8rem; color: var(--text-muted); margin-top: 2px; }}
    .badge-live {{
      background: linear-gradient(135deg, var(--accent-green), #059669);
      color: white; font-size: 0.7rem; font-weight: 600;
      padding: 3px 10px; border-radius: 20px;
      display: flex; align-items: center; gap: 5px;
    }}
    .badge-live::before {{ content:''; width:6px; height:6px; background:#fff; border-radius:50%; animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.4; }} }}

    /* MAIN */
    .main-content {{ max-width: 1400px; margin: 0 auto; padding: 1.5rem 2rem; }}

    /* KPI GRID */
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
    .kpi-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
      position: relative; overflow: hidden;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow); }}
    .kpi-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px; }}
    .kpi-card.blue::before {{ background: linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); }}
    .kpi-card.green::before {{ background: linear-gradient(90deg, var(--accent-green), #34d399); }}
    .kpi-card.red::before {{ background: linear-gradient(90deg, var(--accent-red), #f87171); }}
    .kpi-card.orange::before {{ background: linear-gradient(90deg, var(--accent-orange), #fbbf24); }}
    .kpi-card.purple::before {{ background: linear-gradient(90deg, var(--accent-purple), #c084fc); }}
    .kpi-card.cyan::before {{ background: linear-gradient(90deg, var(--accent-cyan), #22d3ee); }}
    .kpi-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem; }}
    .kpi-label {{ font-size: 0.78rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-icon {{ font-size: 1.4rem; }}
    .kpi-value {{ font-size: 2rem; font-weight: 700; line-height: 1; }}
    .kpi-sub {{ font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem; }}

    /* CHARTS */
    .charts-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
    .charts-grid.three {{ grid-template-columns: 1fr 2fr; }}
    .chart-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.25rem;
    }}
    .chart-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
    .chart-title {{ font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 6px; }}
    .chart-badge {{ background: var(--bg-elevated); color: var(--text-muted); font-size: 0.7rem; padding: 3px 8px; border-radius: 20px; }}
    .chart-canvas-wrap {{ position: relative; height: 220px; }}

    /* KEYWORD CLOUD */
    .keyword-list {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 0.5rem 0; }}
    .keyword-tag {{
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 4px 12px;
      font-size: 0.8rem;
      color: var(--text-secondary);
      cursor: default;
      transition: all 0.2s;
    }}
    .keyword-tag:hover {{ background: var(--accent-blue); color: white; border-color: var(--accent-blue); }}
    .keyword-tag .kcount {{ opacity: 0.7; font-size: 0.7rem; }}

    /* FILTERS */
    .filter-bar {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem 1.25rem;
      display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end;
      margin-bottom: 1rem;
    }}
    .filter-group {{ display: flex; flex-direction: column; gap: 4px; min-width: 120px; }}
    .filter-group label {{ font-size: 0.72rem; color: var(--text-muted); font-weight: 500; text-transform: uppercase; }}
    .filter-group input, .filter-group select {{
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text);
      padding: 7px 10px;
      font-size: 0.82rem;
      outline: none;
      transition: border-color 0.2s;
    }}
    .filter-group input:focus, .filter-group select:focus {{ border-color: var(--accent-blue); }}
    .filter-group.search {{ flex: 1; min-width: 200px; }}
    .btn {{
      padding: 8px 16px; border-radius: var(--radius-sm); font-size: 0.82rem;
      font-weight: 600; cursor: pointer; border: none; transition: all 0.2s;
    }}
    .btn-primary {{ background: var(--accent-blue); color: white; }}
    .btn-primary:hover {{ background: #2563eb; transform: translateY(-1px); }}
    .btn-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text-secondary); }}
    .btn-outline:hover {{ border-color: var(--accent-blue); color: var(--accent-blue); }}
    .filter-actions {{ display: flex; gap: 8px; align-items: flex-end; }}

    /* TABLE */
    .table-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden; margin-bottom: 1.5rem;
    }}
    .table-header {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--border);
    }}
    .table-title {{ font-size: 0.95rem; font-weight: 600; }}
    .table-count {{ background: var(--accent-blue); color: white; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      padding: 10px 12px; text-align: left;
      font-size: 0.75rem; font-weight: 600; color: var(--text-muted);
      text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 1px solid var(--border);
      background: var(--bg-elevated);
      cursor: pointer; user-select: none;
      white-space: nowrap;
    }}
    th:hover {{ color: var(--accent-blue); }}
    td {{ padding: 10px 12px; font-size: 0.82rem; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    tr:hover td {{ background: var(--bg-elevated); cursor: pointer; }}
    .td-baslik {{ max-width: 280px; font-weight: 500; }}
    .td-baslik a {{ color: var(--text); text-decoration: none; }}
    .td-baslik a:hover {{ color: var(--accent-blue); }}

    /* BADGES */
    .badge {{
      display: inline-flex; align-items: center; gap: 4px;
      padding: 3px 10px; border-radius: 20px;
      font-size: 0.7rem; font-weight: 600; white-space: nowrap;
    }}
    .badge-cozuldu   {{ background: rgba(16,185,129,0.15); color: #34d399; }}
    .badge-beklemede {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
    .badge-reddedildi {{ background: rgba(239,68,68,0.15); color: #f87171; }}
    .badge-negatif   {{ background: rgba(239,68,68,0.12); color: #f87171; }}
    .badge-pozitif   {{ background: rgba(16,185,129,0.12); color: #34d399; }}
    .badge-notr      {{ background: rgba(148,163,184,0.12); color: #94a3b8; }}
    .badge-yuksek    {{ background: rgba(239,68,68,0.15); color: #f87171; }}
    .badge-orta      {{ background: rgba(245,158,11,0.15); color: #fbbf24; }}
    .badge-dusuk     {{ background: rgba(16,185,129,0.15); color: #34d399; }}

    /* PAGINATION */
    .pagination {{ display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.25rem; }}
    .pagination-info {{ font-size: 0.8rem; color: var(--text-muted); }}
    .pagination-controls {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .page-btn {{
      padding: 5px 10px; border-radius: var(--radius-sm);
      font-size: 0.78rem; cursor: pointer;
      background: var(--bg-elevated); border: 1px solid var(--border); color: var(--text-secondary);
      transition: all 0.2s;
    }}
    .page-btn:hover, .page-btn.active {{ background: var(--accent-blue); color: white; border-color: var(--accent-blue); }}
    .page-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    /* MODAL */
    .modal-backdrop {{
      position: fixed; inset: 0; background: rgba(0,0,0,0.7);
      z-index: 1000; display: none; backdrop-filter: blur(4px);
    }}
    .modal-backdrop.open {{ display: block; }}
    .modal {{
      position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%) scale(0.95);
      background: var(--bg-card); border: 1px solid var(--border);
      border-radius: var(--radius); width: 90%; max-width: 720px; max-height: 85vh;
      overflow-y: auto; z-index: 1001; opacity: 0;
      transition: all 0.25s cubic-bezier(0.34,1.56,0.64,1);
    }}
    .modal.open {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
    .modal-header {{
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 1.25rem 1.5rem;
      border-bottom: 1px solid var(--border);
      position: sticky; top: 0; background: var(--bg-card);
    }}
    .modal-header-left {{ display: flex; align-items: center; gap: 12px; }}
    .modal-icon {{ font-size: 1.8rem; }}
    .modal-title {{ font-size: 1rem; font-weight: 700; line-height: 1.3; }}
    .modal-date {{ font-size: 0.78rem; color: var(--text-muted); margin-top: 2px; }}
    .modal-close {{
      background: var(--bg-elevated); border: none; color: var(--text-secondary);
      width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 1rem;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: all 0.2s;
    }}
    .modal-close:hover {{ background: var(--accent-red); color: white; }}
    .modal-badges {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 1rem 1.5rem 0; }}
    .modal-body {{ padding: 1rem 1.5rem 1.5rem; }}
    .modal-section {{ margin-bottom: 1.25rem; }}
    .modal-section-label {{ font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
    .modal-content-text {{
      background: var(--bg-elevated); border-radius: var(--radius-sm);
      padding: 1rem; font-size: 0.85rem; line-height: 1.7; color: var(--text-secondary);
      max-height: 240px; overflow-y: auto;
    }}
    .modal-meta-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.25rem; }}
    .modal-meta-item {{ background: var(--bg-elevated); border-radius: var(--radius-sm); padding: 0.75rem; }}
    .modal-meta-label {{ font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; display: block; margin-bottom: 4px; }}
    .modal-meta-value {{ font-size: 0.9rem; font-weight: 600; }}
    .modal-keywords {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .modal-footer {{
      display: flex; justify-content: flex-end; gap: 8px;
      padding: 1rem 1.5rem;
      border-top: 1px solid var(--border);
    }}
    .modal-url a {{ color: var(--accent-blue); font-size: 0.82rem; word-break: break-all; }}

    /* SCORE BAR */
    .score-bar-wrap {{ background: var(--bg); border-radius: 4px; height: 6px; margin: 6px 0; overflow:hidden; }}
    .score-bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.5s; }}

    /* FOOTER */
    footer {{ text-align: center; padding: 2rem; color: var(--text-muted); font-size: 0.78rem; border-top: 1px solid var(--border); }}

    /* RESPONSIVE */
    @media (max-width: 768px) {{
      .main-content {{ padding: 1rem; }}
      .charts-grid {{ grid-template-columns: 1fr; }}
      .charts-grid.three {{ grid-template-columns: 1fr; }}
      .header {{ padding: 0.75rem 1rem; flex-wrap: wrap; gap: 8px; }}
    }}
  </style>
</head>
<body>

<header class="header">
  <div class="header-logo">
    <div class="logo-icon">📊</div>
    <div>
      <h1>Şikayetvar Analiz <span class="subtitle">/ Türkiye Katılım Sigorta</span></h1>
      <div class="header-meta">Son güncelleme: {now} &bull; {total} şikayet &bull; GitHub Pages</div>
    </div>
  </div>
  <div class="badge-live">Canlı Analiz</div>
</header>

<main class="main-content">

  <!-- KPI CARDS -->
  <section class="kpi-grid" id="kpi-grid">
    <div class="kpi-card blue">
      <div class="kpi-header"><span class="kpi-label">Toplam Şikayet</span><div class="kpi-icon">📋</div></div>
      <div class="kpi-value" id="kpi-toplam">—</div>
      <div class="kpi-sub">Toplanan tüm şikayetler</div>
    </div>
    <div class="kpi-card green">
      <div class="kpi-header"><span class="kpi-label">Çözüm Oranı</span><div class="kpi-icon">✅</div></div>
      <div class="kpi-value" id="kpi-cozum">—</div>
      <div class="kpi-sub" id="kpi-cozum-sub">çözülmüş şikayet</div>
    </div>
    <div class="kpi-card red">
      <div class="kpi-header"><span class="kpi-label">Beklemede</span><div class="kpi-icon">⏳</div></div>
      <div class="kpi-value" id="kpi-beklemede">—</div>
      <div class="kpi-sub">Yanıt bekleyen</div>
    </div>
    <div class="kpi-card orange">
      <div class="kpi-header"><span class="kpi-label">Reddedildi</span><div class="kpi-icon">🚫</div></div>
      <div class="kpi-value" id="kpi-reddedildi">—</div>
      <div class="kpi-sub">Reddedilmiş şikayet</div>
    </div>
    <div class="kpi-card purple">
      <div class="kpi-header"><span class="kpi-label">Negatif Duygu</span><div class="kpi-icon">😡</div></div>
      <div class="kpi-value" id="kpi-negatif">—</div>
      <div class="kpi-sub">Olumsuz şikayet oranı</div>
    </div>
    <div class="kpi-card cyan">
      <div class="kpi-header"><span class="kpi-label">Pozitif Duygu</span><div class="kpi-icon">😊</div></div>
      <div class="kpi-value" id="kpi-pozitif">—</div>
      <div class="kpi-sub">Olumlu yorumlar</div>
    </div>
  </section>

  <!-- CHARTS ROW 1 -->
  <div class="charts-grid">
    <div class="chart-card">
      <div class="chart-header">
        <div class="chart-title">📈 Durum Dağılımı</div>
        <span class="chart-badge">Tüm Veriler</span>
      </div>
      <div class="chart-canvas-wrap"><canvas id="chart-durum"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-header">
        <div class="chart-title">😊 Duygu Analizi</div>
        <span class="chart-badge">Ollama Analizi</span>
      </div>
      <div class="chart-canvas-wrap"><canvas id="chart-duygu"></canvas></div>
    </div>
  </div>

  <!-- CHARTS ROW 2 -->
  <div class="charts-grid" style="grid-template-columns:1fr">
    <div class="chart-card">
      <div class="chart-header">
        <div class="chart-title">☁️ En Çok Geçen Konular</div>
        <span class="chart-badge">Top 20</span>
      </div>
      <div class="keyword-list" id="keyword-list"></div>
    </div>
  </div>

  <!-- FILTERS -->
  <section class="filter-bar">
    <div class="filter-group search">
      <label>🔍 Metin Arama</label>
      <input type="text" id="filter-arama" placeholder="Şikayette kelime ara..." oninput="filtreUygula()" />
    </div>
    <div class="filter-group">
      <label>✅ Durum</label>
      <select id="filter-durum" onchange="filtreUygula()">
        <option value="">Tümü</option>
        <option value="çözüldü">Çözüldü</option>
        <option value="beklemede">Beklemede</option>
        <option value="reddedildi">Reddedildi</option>
      </select>
    </div>
    <div class="filter-group">
      <label>😊 Duygu</label>
      <select id="filter-duygu" onchange="filtreUygula()">
        <option value="">Tümü</option>
        <option value="pozitif">Pozitif</option>
        <option value="negatif">Negatif</option>
        <option value="nötr">Nötr</option>
      </select>
    </div>
    <div class="filter-group">
      <label>⚡ Aciliyet</label>
      <select id="filter-aciliyet" onchange="filtreUygula()">
        <option value="">Tümü</option>
        <option value="yüksek">Yüksek</option>
        <option value="orta">Orta</option>
        <option value="düşük">Düşük</option>
      </select>
    </div>
    <div class="filter-actions">
      <button class="btn btn-outline" onclick="filtreTemizle()">Temizle</button>
    </div>
  </section>

  <!-- TABLE -->
  <section class="table-card">
    <div class="table-header">
      <div class="table-title">📋 Şikayet Listesi <span class="table-count" id="table-count"></span></div>
      <select id="table-limit" onchange="updatePageSize()" style="background:var(--bg-elevated);border:1px solid var(--border);color:var(--text-secondary);padding:6px 10px;border-radius:var(--radius-sm);font-size:0.8rem;">
        <option value="25">25 / sayfa</option>
        <option value="50" selected>50 / sayfa</option>
        <option value="100">100 / sayfa</option>
      </select>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th onclick="sortBy('tarih')">Tarih ↕</th>
            <th>Başlık</th>
            <th>Durum</th>
            <th>Duygu</th>
            <th>Aciliyet</th>
            <th onclick="sortBy('begeni_sayisi')">👍 ↕</th>
            <th onclick="sortBy('yorum_sayisi')">💬 ↕</th>
            <th>Konu</th>
          </tr>
        </thead>
        <tbody id="complaint-tbody"></tbody>
      </table>
    </div>
    <div class="pagination">
      <div class="pagination-info" id="pagination-info"></div>
      <div class="pagination-controls" id="pagination-controls"></div>
    </div>
  </section>

</main>

<!-- MODAL -->
<div class="modal-backdrop" id="modal-backdrop" onclick="modalKapat()"></div>
<div class="modal" id="complaint-modal" role="dialog" aria-modal="true">
  <div class="modal-header">
    <div class="modal-header-left">
      <div class="modal-icon">📋</div>
      <div>
        <h2 class="modal-title" id="modal-title">Şikayet Detayı</h2>
        <div class="modal-date" id="modal-date"></div>
      </div>
    </div>
    <button class="modal-close" onclick="modalKapat()">✕</button>
  </div>
  <div class="modal-badges" id="modal-badges"></div>
  <div class="modal-body">
    <div class="modal-section">
      <div class="modal-section-label">📝 Şikayet İçeriği</div>
      <div class="modal-content-text" id="modal-icerik">—</div>
    </div>
    <div class="modal-meta-grid">
      <div class="modal-meta-item"><span class="modal-meta-label">Ana Sorun</span><span class="modal-meta-value" id="modal-ana-sorun">—</span></div>
      <div class="modal-meta-item"><span class="modal-meta-label">Duygu Skoru</span><div class="score-bar-wrap"><div class="score-bar-fill" id="modal-score-bar"></div></div><span class="modal-meta-value" id="modal-duygu-skor">—</span></div>
      <div class="modal-meta-item"><span class="modal-meta-label">Beğeni</span><span class="modal-meta-value" id="modal-begeni">—</span></div>
      <div class="modal-meta-item"><span class="modal-meta-label">Yorum</span><span class="modal-meta-value" id="modal-yorum">—</span></div>
      <div class="modal-meta-item"><span class="modal-meta-label">Analiz Yöntemi</span><span class="modal-meta-value" id="modal-yontem">—</span></div>
    </div>
    <div class="modal-section modal-url">
      <div class="modal-section-label">🔗 Şikayet Bağlantısı</div>
      <div class="modal-content-text" style="padding:0.5rem 0.75rem;background:var(--bg-elevated);">
        <a href="#" id="modal-url-link" target="_blank" rel="noopener">—</a>
      </div>
    </div>
    <div class="modal-section">
      <div class="modal-section-label">🏷️ Anahtar Kelimeler</div>
      <div class="modal-keywords" id="modal-keywords"></div>
    </div>
  </div>
  <div class="modal-footer">
    <a class="btn btn-primary" id="modal-ext-link" href="#" target="_blank" rel="noopener">🔗 Sikayetvar'da Görüntüle</a>
    <button class="btn btn-outline" onclick="modalKapat()">Kapat</button>
  </div>
</div>

<footer>
  <p>TKS Şikayetvar Analiz Dashboard &bull; Türkiye Katılım Sigorta &bull; {now} tarihi itibarıyla {total} şikayet analiz edilmiştir.</p>
  <p style="margin-top:6px;">Veriler <a href="https://www.sikayetvar.com/turkiye-katilim-sigorta" target="_blank" style="color:var(--accent-blue);">sikayetvar.com</a>'dan toplanmıştır.</p>
</footer>

<script>
// ── EMBEDDED DATA ──────────────────────────────────────────────
const ALL_DATA = {data_json};

// ── STATE ──────────────────────────────────────────────────────
let state = {{
  page: 1,
  pageSize: 50,
  sortKey: 'tarih',
  sortAsc: false,
  filtered: [],
  filter: {{ arama:'', durum:'', duygu:'', aciliyet:'' }},
}};

// ── INIT ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {{
  state.filtered = [...ALL_DATA];
  renderKPI(ALL_DATA);
  renderCharts(ALL_DATA);
  renderKeywords(ALL_DATA);
  renderTable();
}});

// ── KPI ───────────────────────────────────────────────────────
function renderKPI(data) {{
  const total    = data.length;
  const cozuldu  = data.filter(s => s.durum === 'çözüldü').length;
  const bekle    = data.filter(s => s.durum === 'beklemede').length;
  const red      = data.filter(s => s.durum === 'reddedildi').length;
  const neg      = data.filter(s => s.duygu === 'negatif').length;
  const pos      = data.filter(s => s.duygu === 'pozitif').length;

  set('kpi-toplam',    total);
  set('kpi-cozum',     total > 0 ? `%${{Math.round(cozuldu/total*100)}}` : '—');
  set('kpi-cozum-sub', `${{cozuldu}} çözülmüş şikayet`);
  set('kpi-beklemede', bekle);
  set('kpi-reddedildi',red);
  set('kpi-negatif',   total > 0 ? `%${{Math.round(neg/total*100)}}` : '—');
  set('kpi-pozitif',   total > 0 ? `%${{Math.round(pos/total*100)}}` : '—');
}}

// ── CHARTS ────────────────────────────────────────────────────
let charts = {{}};

function renderCharts(data) {{
  // Durum Pie
  const durum = {{ çözüldü:0, beklemede:0, reddedildi:0, diğer:0 }};
  data.forEach(s => {{
    if (s.durum === 'çözüldü') durum['çözüldü']++;
    else if (s.durum === 'beklemede') durum['beklemede']++;
    else if (s.durum === 'reddedildi') durum['reddedildi']++;
    else durum['diğer']++;
  }});

  destroyChart('chart-durum');
  charts['chart-durum'] = new Chart(document.getElementById('chart-durum'), {{
    type: 'doughnut',
    data: {{
      labels: ['Çözüldü', 'Beklemede', 'Reddedildi'],
      datasets: [{{ data: [durum['çözüldü'], durum['beklemede'], durum['reddedildi']],
        backgroundColor: ['#10b981','#f59e0b','#ef4444'],
        borderWidth: 0, hoverOffset: 8 }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#94a3b8', boxWidth:12 }} }} }} }}
  }});

  // Duygu Bar
  const duygu = {{ negatif:0, nötr:0, pozitif:0 }};
  data.forEach(s => {{ if (s.duygu in duygu) duygu[s.duygu]++; }});

  destroyChart('chart-duygu');
  charts['chart-duygu'] = new Chart(document.getElementById('chart-duygu'), {{
    type: 'bar',
    data: {{
      labels: ['Negatif', 'Nötr', 'Pozitif'],
      datasets: [{{ data: [duygu['negatif'], duygu['nötr'], duygu['pozitif']],
        backgroundColor: ['rgba(239,68,68,0.7)','rgba(148,163,184,0.5)','rgba(16,185,129,0.7)'],
        borderRadius: 6, borderWidth: 0 }}]
    }},
    options: {{
      responsive:true, maintainAspectRatio:false,
      plugins:{{ legend:{{ display:false }} }},
      scales:{{ x:{{ grid:{{ display:false }}, ticks:{{ color:'#94a3b8' }} }}, y:{{ grid:{{ color:'rgba(148,163,184,0.1)' }}, ticks:{{ color:'#94a3b8' }} }} }}
    }}
  }});
}}

function destroyChart(id) {{
  if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }}
}}

// ── KEYWORDS ──────────────────────────────────────────────────
function renderKeywords(data) {{
  const freq = {{}};
  data.forEach(s => {{
    (s.anahtar_kelimeler || []).forEach(k => {{
      freq[k] = (freq[k] || 0) + 1;
    }});
  }});
  const sorted = Object.entries(freq).sort((a,b) => b[1]-a[1]).slice(0,20);
  const max = sorted[0]?.[1] || 1;
  const el = document.getElementById('keyword-list');
  el.innerHTML = sorted.map(([k,c]) => {{
    const size = 0.75 + (c/max)*0.6;
    return `<span class="keyword-tag" style="font-size:${{size.toFixed(2)}}rem" onclick="filterByKeyword('${{k}}')">${{k}} <span class="kcount">(${{c}})</span></span>`;
  }}).join('');
}}

function filterByKeyword(k) {{
  document.getElementById('filter-arama').value = k;
  filtreUygula();
}}

// ── FILTER ────────────────────────────────────────────────────
function filtreUygula() {{
  const arama    = document.getElementById('filter-arama').value.toLowerCase();
  const durum    = document.getElementById('filter-durum').value;
  const duygu    = document.getElementById('filter-duygu').value;
  const aciliyet = document.getElementById('filter-aciliyet').value;

  state.filter = {{ arama, durum, duygu, aciliyet }};
  state.page   = 1;

  state.filtered = ALL_DATA.filter(s => {{
    if (arama && !(
      (s.baslik||'').toLowerCase().includes(arama) ||
      (s.icerik||'').toLowerCase().includes(arama) ||
      (s.anahtar_kelimeler||[]).join(' ').toLowerCase().includes(arama)
    )) return false;
    if (durum    && s.durum    !== durum)    return false;
    if (duygu    && s.duygu    !== duygu)    return false;
    if (aciliyet && s.aciliyet !== aciliyet) return false;
    return true;
  }});

  renderTable();
}}

function filtreTemizle() {{
  document.getElementById('filter-arama').value = '';
  document.getElementById('filter-durum').value = '';
  document.getElementById('filter-duygu').value = '';
  document.getElementById('filter-aciliyet').value = '';
  state.filtered = [...ALL_DATA];
  state.page = 1;
  renderTable();
}}

// ── SORT ──────────────────────────────────────────────────────
function sortBy(key) {{
  if (state.sortKey === key) state.sortAsc = !state.sortAsc;
  else {{ state.sortKey = key; state.sortAsc = false; }}
  renderTable();
}}

// ── TABLE ─────────────────────────────────────────────────────
function renderTable() {{
  const data = [...state.filtered].sort((a, b) => {{
    let va = a[state.sortKey] ?? '';
    let vb = b[state.sortKey] ?? '';
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    return state.sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  }});

  const total    = data.length;
  const start    = (state.page - 1) * state.pageSize;
  const pageData = data.slice(start, start + state.pageSize);

  set('table-count', total);

  const tbody = document.getElementById('complaint-tbody');
  if (!pageData.length) {{
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:2rem;color:#64748b;">Filtreye uyan şikayet bulunamadı.</td></tr>`;
  }} else {{
    tbody.innerHTML = pageData.map((s, i) => `
      <tr onclick="modalAc(${{start + i}}, ${{JSON.stringify(s).replace(/"/g,'&quot;')}})" style="cursor:pointer;">
        <td>${{s.tarih || '—'}}</td>
        <td class="td-baslik">${{escHtml(s.baslik || '—')}}</td>
        <td>${{durumBadge(s.durum)}}</td>
        <td>${{duyguBadge(s.duygu)}}</td>
        <td>${{aciliyetBadge(s.aciliyet)}}</td>
        <td>${{s.begeni_sayisi ?? 0}}</td>
        <td>${{s.yorum_sayisi ?? 0}}</td>
        <td style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#64748b;font-size:0.75rem;">${{escHtml((s.anahtar_kelimeler||[]).slice(0,3).join(', '))}}</td>
      </tr>`).join('');
  }}

  // Pagination
  const totalPages = Math.ceil(total / state.pageSize);
  set('pagination-info', `${{start+1}}–${{Math.min(start+state.pageSize, total)}} / ${{total}} kayıt`);

  const ctrl = document.getElementById('pagination-controls');
  let pages = '';
  for (let p = 1; p <= totalPages; p++) {{
    if (totalPages > 10 && Math.abs(p - state.page) > 2 && p !== 1 && p !== totalPages) {{
      if (p === state.page - 3 || p === state.page + 3) pages += `<span style="color:#64748b;padding:0 4px;">…</span>`;
      continue;
    }}
    pages += `<button class="page-btn${{p===state.page?' active':''}}" onclick="goPage(${{p}})">${{p}}</button>`;
  }}
  ctrl.innerHTML = `
    <button class="page-btn" onclick="goPage(${{state.page-1}})" ${{state.page<=1?'disabled':''}}>‹</button>
    ${{pages}}
    <button class="page-btn" onclick="goPage(${{state.page+1}})" ${{state.page>=totalPages?'disabled':''}}>›</button>`;
}}

function goPage(p) {{
  const max = Math.ceil(state.filtered.length / state.pageSize);
  if (p < 1 || p > max) return;
  state.page = p;
  renderTable();
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

function updatePageSize() {{
  state.pageSize = parseInt(document.getElementById('table-limit').value);
  state.page = 1;
  renderTable();
}}

// ── MODAL ─────────────────────────────────────────────────────
let _currentData = null;

function modalAc(idx, s) {{
  if (typeof s === 'string') {{ try {{ s = JSON.parse(s); }} catch(e) {{ return; }} }}
  _currentData = s;

  set('modal-title',   s.baslik || '—');
  set('modal-date',    `📅 ${{s.tarih || '—'}} &nbsp;|&nbsp; 🆔 ${{s.sikayet_id || '—'}}`);
  set('modal-icerik',  escHtml(s.icerik || '—'));
  set('modal-ana-sorun', s.ana_sorun || '—');
  set('modal-duygu-skor', s.duygu_skoru != null ? s.duygu_skoru.toFixed(2) : '—');
  set('modal-begeni',  s.begeni_sayisi ?? 0);
  set('modal-yorum',   s.yorum_sayisi ?? 0);
  set('modal-yontem',  s.analiz_yontemi || '—');

  // Score bar
  const bar = document.getElementById('modal-score-bar');
  const skor = parseFloat(s.duygu_skoru) || 0;
  const pct  = ((skor + 1) / 2 * 100).toFixed(0);
  bar.style.width = `${{pct}}%`;
  bar.style.background = skor < -0.3 ? '#ef4444' : skor > 0.3 ? '#10b981' : '#64748b';

  // Badges
  document.getElementById('modal-badges').innerHTML = [
    durumBadge(s.durum), duyguBadge(s.duygu), aciliyetBadge(s.aciliyet)
  ].join(' ');

  // URL
  const url = s.url || '';
  const urlEl = document.getElementById('modal-url-link');
  urlEl.href = url || '#';
  urlEl.textContent = url || 'Bağlantı bulunamadı';

  const extLink = document.getElementById('modal-ext-link');
  extLink.href = url || '#';

  // Keywords
  const kw = (s.anahtar_kelimeler || []);
  document.getElementById('modal-keywords').innerHTML = kw.length
    ? kw.map(k => `<span class="badge badge-notr">${{escHtml(k)}}</span>`).join(' ')
    : '<span style="color:#64748b;font-size:0.8rem;">Anahtar kelime yok</span>';

  document.getElementById('modal-backdrop').classList.add('open');
  document.getElementById('complaint-modal').classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function modalKapat() {{
  document.getElementById('modal-backdrop').classList.remove('open');
  document.getElementById('complaint-modal').classList.remove('open');
  document.body.style.overflow = '';
}}

document.addEventListener('keydown', e => {{ if (e.key === 'Escape') modalKapat(); }});

// ── BADGES ───────────────────────────────────────────────────
function durumBadge(d) {{
  const map = {{ 'çözüldü':'cozuldu', 'beklemede':'beklemede', 'reddedildi':'reddedildi' }};
  const emoji = {{ 'çözüldü':'✅', 'beklemede':'⏳', 'reddedildi':'🚫' }};
  const cls = map[d] || 'notr';
  return `<span class="badge badge-${{cls}}">${{emoji[d]||''}} ${{d||'—'}}</span>`;
}}
function duyguBadge(d) {{
  const cls = d === 'negatif' ? 'negatif' : d === 'pozitif' ? 'pozitif' : 'notr';
  const emoji = {{ negatif:'😡', pozitif:'😊', 'nötr':'😐' }};
  return `<span class="badge badge-${{cls}}">${{emoji[d]||''}} ${{d||'—'}}</span>`;
}}
function aciliyetBadge(a) {{
  const cls = a === 'yüksek' ? 'yuksek' : a === 'orta' ? 'orta' : 'dusuk';
  return `<span class="badge badge-${{cls}}">${{a||'—'}}</span>`;
}}

// ── HELPERS ───────────────────────────────────────────────────
function set(id, val) {{ const el = document.getElementById(id); if (el) el.innerHTML = val; }}
function escHtml(s) {{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
</script>
</body>
</html>"""

def main():
    print("📦 Veriler okunuyor...")
    complaints = load_complaints()

    if not complaints:
        print("[UYARI] Hiç şikayet bulunamadı. Önce scraper çalıştırın.")
        # Demo ile devam et
        complaints = []

    print(f"✅ {len(complaints)} şikayet bulundu.")
    print("🔨 HTML oluşturuluyor...")

    DOCS_DIR.mkdir(exist_ok=True)
    html = build_html(complaints)
    OUT_PATH.write_text(html, encoding="utf-8")

    print(f"✨ Çıktı: {OUT_PATH}")
    print(f"\n📌 GitHub Pages için sonraki adımlar:")
    print(f"   1. git add docs/")
    print(f"   2. git commit -m 'GitHub Pages dashboard güncellendi'")
    print(f"   3. git push")
    print(f"   4. GitHub repo → Settings → Pages → Source: 'Deploy from branch' → Branch: main / docs")

if __name__ == "__main__":
    main()
