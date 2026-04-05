import sys
import os
from pathlib import Path

# Windows encoding fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Proje kök dizinini Python path'e ekle
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console(force_terminal=True, highlight=False)


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]Sikayetvar Analiz Platformu[/bold cyan]\n"
        "[dim]Turkiye Katilim Sigorta - Sikayet Scraper & Dashboard[/dim]",
        border_style="blue"
    ))


@click.group()
def cli():
    """Şikayetvar Scraper & Dashboard CLI"""
    pass


@cli.command()
@click.option("--pages", default=None, type=int, help="Kaç sayfa scrape edilsin (varsayılan: config'deki SCRAPER_MAX_PAGES)")
@click.option("--no-analysis", is_flag=True, help="Duygu analizini atla")
def scrape(pages, no_analysis):
    """Şikayetleri topla ve veritabanına yaz."""
    print_banner()
    from config import SCRAPER_MAX_PAGES
    from scraper.scraper import scrape as do_scrape
    from database.db import SikayetDB
    from nlp.sentiment import sikayet_analiz_et, ollama_hazir_mi
    
    pages = pages or SCRAPER_MAX_PAGES

    # Ollama kontrolü
    if not no_analysis:
        if ollama_hazir_mi():
            console.print("✅ [green]Ollama bağlantısı başarılı[/green] – Qwen analizi aktif")
        else:
            console.print("⚠️  [yellow]Ollama bağlantısı yok[/yellow] – Keyword analizi kullanılacak")

    # Scrape
    console.print(f"\n📡 {pages} sayfa scrape başlıyor...\n")
    sikayetler = do_scrape(max_sayfa=pages)

    if not sikayetler:
        console.print("[red]Hiç şikayet bulunamadı! Site yapısı değişmiş olabilir.[/red]")
        return

    # DB'ye yaz
    db = SikayetDB()
    try:
        sonuc = db.bulk_insert(sikayetler)
        console.print(f"\n💾 Veritabanı: [green]{sonuc['eklenen']} yeni[/green], "
                      f"[dim]{sonuc['atlanan']} zaten mevcut[/dim]")

        # Duygu analizi
        if not no_analysis:
            tum = db.sikayetler.all()
            analiz_edilmemis = [s for s in tum if s.get("duygu") == "analiz edilmedi"]
            
            if analiz_edilmemis:
                console.print(f"\n🤖 {len(analiz_edilmemis)} şikayet için duygu analizi yapılıyor...")
                
                for i, s in enumerate(analiz_edilmemis, 1):
                    console.print(f"  [{i}/{len(analiz_edilmemis)}] {s.get('baslik', '')[:60]}...")
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
        stats = db.istatistikler()
        
        # Özet tablo
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metrik", style="dim")
        table.add_column("Değer", justify="right", style="bold")
        table.add_row("Toplam Şikayet", str(stats["toplam"]))
        table.add_row("Çözüldü", str(stats["cozuldu"]))
        table.add_row("Beklemede", str(stats["beklemede"]))
        table.add_row("Reddedildi", str(stats["reddedildi"]))
        table.add_row("Çözüm Oranı", f"%{stats['cozum_orani']}")
        table.add_row("Negatif Duygu", str(stats["negatif"]))
        console.print("\n", table)

    finally:
        db.kapat()

    console.print("\n[bold green]✅ Scraping tamamlandı![/bold green]")
    console.print("Dashboard için: [cyan]python main.py serve[/cyan]\n")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host adresi")
@click.option("--port", default=5050, help="Port numarası")
def serve(host, port):
    """Web dashboard'u başlat."""
    print_banner()
    from app.app import create_app
    app = create_app()
    console.print(f"\n🚀 Dashboard: [link=http://localhost:{port}]http://localhost:{port}[/link]")
    console.print("Durdurmak için [bold]Ctrl+C[/bold]\n")
    app.run(host=host, port=port, debug=False)


@cli.command()
def auto():
    """Otomatik periyodik scraper başlat."""
    print_banner()
    from scraper.scheduler import basla
    basla()


@cli.command()
@click.option("--pages", default=None, type=int, help="Başlangıç scrape sayfa sayısı")
@click.option("--port", default=5050, help="Port numarası")
def all(pages, port):
    """Scrape yap, sonra dashboard başlat."""
    print_banner()
    import threading
    from config import SCRAPER_MAX_PAGES
    pages = pages or SCRAPER_MAX_PAGES

    def _serve():
        from app.app import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    # Önce scrape (main thread)
    from scraper.scraper import scrape as do_scrape
    from database.db import SikayetDB
    from nlp.sentiment import sikayet_analiz_et

    console.print(f"\n📡 {pages} sayfa scrape başlıyor...")
    sikayetler = do_scrape(max_sayfa=pages)

    db = SikayetDB()
    try:
        sonuc = db.bulk_insert(sikayetler)
        console.print(f"💾 {sonuc['eklenen']} yeni şikayet eklendi")
        
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

    # Serve (background thread)
    t = threading.Thread(target=_serve, daemon=True)
    t.start()
    console.print(f"\n🚀 Dashboard: [link=http://localhost:{port}]http://localhost:{port}[/link]")
    
    try:
        t.join()
    except KeyboardInterrupt:
        console.print("\n👋 Dashboard durduruldu.")


if __name__ == "__main__":
    cli()
