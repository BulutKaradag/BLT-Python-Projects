"""
Flask REST API Routes
Dashboard için tüm veri endpoint'leri.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, jsonify, request
from database.db import SikayetDB

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_db():
    return SikayetDB()


# ── Genel İstatistikler ───────────────────────────────────────────────────────

@api_bp.route("/stats/overview", methods=["GET"])
def stats_overview():
    """Dashboard özet istatistikleri."""
    db = get_db()
    try:
        return jsonify(db.istatistikler())
    finally:
        db.kapat()


# ── Şikayet Listesi ───────────────────────────────────────────────────────────

@api_bp.route("/complaints", methods=["GET"])
def complaints():
    """
    Filtrelenebilir şikayet listesi.
    Query params: durum, duygu, arama, tarih_baslangic, tarih_bitis,
                  siralama, artan, limit, offset
    """
    db = get_db()
    try:
        return jsonify(db.tum_sikayetler(
            durum=request.args.get("durum"),
            duygu=request.args.get("duygu"),
            arama=request.args.get("arama"),
            tarih_baslangic=request.args.get("tarih_baslangic"),
            tarih_bitis=request.args.get("tarih_bitis"),
            siralama=request.args.get("siralama", "tarih"),
            artan=request.args.get("artan", "false").lower() == "true",
            limit=int(request.args.get("limit", 50)),
            offset=int(request.args.get("offset", 0)),
        ))
    finally:
        db.kapat()


# ── Scraper Tetikleme ─────────────────────────────────────────────────────────

@api_bp.route("/scraper/run", methods=["POST"])
def run_scraper():
    """Manuel scraper tetikle (arka planda çalışır)."""
    import threading
    from scraper.scraper import scrape
    from nlp.sentiment import sikayet_analiz_et

    def _pipeline():
        db = SikayetDB()
        try:
            sikayetler = scrape()
            sonuc = db.bulk_insert(sikayetler)
            tum = db.sikayetler.all()
            for s in tum:
                if s.get("duygu") == "analiz edilmedi":
                    analiz = sikayet_analiz_et(s.get("baslik", ""), s.get("icerik", ""))
                    db.sikayet_guncelle(s["sikayet_id"], {
                        "duygu": analiz.get("duygu", "nötr"),
                        "duygu_skoru": analiz.get("duygu_skoru", 0.0),
                        "ana_sorun": analiz.get("ana_sorun", ""),
                        "anahtar_kelimeler": analiz.get("anahtar_kelimeler", []),
                        "aciliyet": analiz.get("aciliyet", "düşük"),
                        "analiz_yontemi": analiz.get("yontem", "keyword")
                    })
            db.scrape_say()
        finally:
            db.kapat()

    t = threading.Thread(target=_pipeline, daemon=True)
    t.start()
    return jsonify({"status": "ok", "mesaj": "Scraping arka planda başlatıldı."})


@api_bp.route("/scraper/status", methods=["GET"])
def scraper_status():
    """DB durumunu döner."""
    db = get_db()
    try:
        stats = db.istatistikler()
        return jsonify({
            "toplam_sikayet": stats["toplam"],
            "son_scrape": stats.get("son_scrape"),
        })
    finally:
        db.kapat()


# ── Sağlık Kontrolü ───────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health():
    db = get_db()
    try:
        stats = db.istatistikler()
        return jsonify({"status": "ok", "version": "1.0.0", "toplam": stats["toplam"]})
    finally:
        db.kapat()


# ── Veritabanı Temizle ────────────────────────────────────────────────────────

@api_bp.route("/database/clear", methods=["POST"])
def database_clear():
    """Tüm şikayetleri veritabanından siler."""
    db = get_db()
    try:
        db.sikayetler.truncate()
        # Meta tablosunu da sıfırla
        if hasattr(db, "meta"):
            db.meta.truncate()
        return jsonify({"status": "ok", "mesaj": "Veritabanı temizlendi."})
    except Exception as e:
        return jsonify({"status": "error", "mesaj": str(e)}), 500
    finally:
        db.kapat()


# ── Ollama Analiz Tetikle ─────────────────────────────────────────────────────

_analiz_durumu = {"calisıyor": False, "tamamlanan": 0, "toplam": 0}


@api_bp.route("/analysis/run", methods=["POST"])
def run_analysis():
    """Analiz edilmemiş şikayetler için Ollama/Qwen analizi başlatır (arka planda)."""
    global _analiz_durumu

    if _analiz_durumu["calisıyor"]:
        return jsonify({"status": "busy", "mesaj": "Analiz zaten devam ediyor.",
                        "durum": _analiz_durumu})

    import threading
    from nlp.sentiment import sikayet_analiz_et, ollama_hazir_mi

    def _analiz():
        global _analiz_durumu
        _analiz_durumu["calisıyor"] = True
        _analiz_durumu["tamamlanan"] = 0

        db = SikayetDB()
        try:
            tum = db.sikayetler.all()
            bekleyenler = [s for s in tum if s.get("duygu") in ("analiz edilmedi", None, "")]
            _analiz_durumu["toplam"] = len(bekleyenler)

            for s in bekleyenler:
                analiz = sikayet_analiz_et(s.get("baslik", ""), s.get("icerik", ""))
                db.sikayet_guncelle(s["sikayet_id"], {
                    "duygu":           analiz.get("duygu", "nötr"),
                    "duygu_skoru":     analiz.get("duygu_skoru", 0.0),
                    "ana_sorun":       analiz.get("ana_sorun", ""),
                    "anahtar_kelimeler": analiz.get("anahtar_kelimeler", []),
                    "aciliyet":        analiz.get("aciliyet", "düşük"),
                    "analiz_yontemi":  analiz.get("yontem", "keyword"),
                })
                _analiz_durumu["tamamlanan"] += 1
        finally:
            db.kapat()
            _analiz_durumu["calisıyor"] = False

    t = threading.Thread(target=_analiz, daemon=True)
    t.start()

    db_tmp = get_db()
    try:
        toplam_bekleyen = len([s for s in db_tmp.sikayetler.all()
                               if s.get("duygu") in ("analiz edilmedi", None, "")])
    finally:
        db_tmp.kapat()

    return jsonify({
        "status": "ok",
        "mesaj": f"{toplam_bekleyen} şikayet için analiz başlatıldı.",
        "bekleyen": toplam_bekleyen
    })


@api_bp.route("/analysis/status", methods=["GET"])
def analysis_status():
    """Analiz ilerlemesini döner."""
    return jsonify(_analiz_durumu)
