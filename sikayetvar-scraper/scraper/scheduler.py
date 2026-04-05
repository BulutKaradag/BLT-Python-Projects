"""
APScheduler ile otomatik periyodik scraping.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from rich.console import Console

from scraper.scraper import scrape
from database.db import SikayetDB
from nlp.sentiment import sikayet_analiz_et
from config import SCHEDULER_INTERVAL_HOURS

console = Console()


def scrape_ve_kaydet():
    """Tüm pipeline: Scrape → Kaydet → Analiz et."""
    console.print(f"\n[bold cyan]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} – Otomatik scraping başlıyor...[/bold cyan]")

    db = SikayetDB()
    try:
        # 1. Scrape
        sikayetler = scrape()
        if not sikayetler:
            console.print("[UYARI] Hiç şikayet bulunamadı.")
            return

        # 2. DB'ye yaz
        sonuc = db.bulk_insert(sikayetler)
        console.print(f"DB: {sonuc['eklenen']} yeni, {sonuc['atlanan']} zaten mevcut")

        # 3. Duygu analizi (yeni eklenenler için)
        tum = db.sikayetler.all()
        analiz_edilmemis = [s for s in tum if s.get("duygu") == "analiz edilmedi"]
        console.print(f"Duygu analizi: {len(analiz_edilmemis)} şikayet işlenecek...")

        for s in analiz_edilmemis:
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
        console.print("[bold green]Scraping tamamlandı![/bold green]")

    finally:
        db.kapat()


def basla():
    """Scheduler'ı başlat."""
    scheduler = BlockingScheduler(timezone="Europe/Istanbul")
    scheduler.add_job(
        scrape_ve_kaydet,
        trigger=IntervalTrigger(hours=SCHEDULER_INTERVAL_HOURS),
        next_run_time=datetime.now()  # Hemen başlat
    )
    console.print(f"[bold]Scheduler başladı – Her {SCHEDULER_INTERVAL_HOURS} saatte bir çalışacak[/bold]")
    console.print("Durdurmak için Ctrl+C\n")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        console.print("\nScheduler durduruldu.")
