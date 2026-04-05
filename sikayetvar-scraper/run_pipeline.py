"""
Şikayetvar Scraper & Analiz Pipeline (Manuel Çalıştırma Scripti)
Bu script, belirlenen sayfa kadar şikayeti toplar ve veritabanına kaydederek analiz eder.

Kullanım:
    python run_pipeline.py             # 50 sayfa, Gemini analiz (default)
    python run_pipeline.py 5           # 5 sayfa çek (test)
    python run_pipeline.py --keyword   # Gemini kotası doluysa → keyword analizi kullan
    python run_pipeline.py --reanaliz  # Tüm şikayetleri yeniden analiz et (scrape yok)
"""
import sys
import os
from pathlib import Path

# Proje kök dizinini Python path'e ekle
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Gerekli modülleri içe aktar
try:
    from scraper.scraper import scrape as do_scrape
    from database.db import SikayetDB
    from nlp.sentiment import sikayet_analiz_et, ollama_hazir_mi
    from rich.console import Console
    from rich.panel import Panel
except ImportError as e:
    print(f"❌ Hata: Gerekli kütüphaneler bulunamadı: {e}")
    print("Lütfen 'pip install -r requirements.txt' komutunu çalıştırın.")
    sys.exit(1)

console = Console()


def run_pipeline(page_count: int = 50, use_keyword: bool = False, reanaliz: bool = False):
    """Scrape yapar, sonuçları DB'ye ekler ve analiz eder."""

    # Keyword modu seçildiyse env'i ayarla (Gemini bypass)
    if use_keyword:
        os.environ["ANALYSIS_MODE"] = "keyword"
        console.print("⚙️  [yellow]Keyword analizi modu aktif[/yellow] – Gemini kullanılmayacak.")

    console.print(Panel.fit(
        "[bold cyan]TKS Şikayetvar Analiz Pipeline[/bold cyan]\n"
        "[dim]Scraping + Duygu Analizi + DB Güncelleme[/dim]",
        border_style="blue"
    ))

    # 1. Ollama Kontrolü
    if ollama_hazir_mi():
        console.print("✅ [green]Ollama (Qwen) aktif[/green] – Derin analiz yapılacak.")
    else:
        console.print("⚠️ [yellow]Ollama/Qwen bulunamadı[/yellow] – Gemini veya keyword analizi kullanılacak.")

    # 2. Scrape Et (--reanaliz modunda atla)
    if not reanaliz:
        console.print(f"\n📡 [bold blue]{page_count} sayfa[/bold blue] taranıyor...\n")
        try:
            sikayetler = do_scrape(max_sayfa=page_count)
        except Exception as e:
            console.print(f"❌ [red]Scraping sırasında hata oluştu:[/red] {e}")
            return

        if not sikayetler:
            console.print("❌ [red]Hiç şikayet toplanamadı. Site yapısı değişmiş olabilir.[/red]")
            return
    else:
        console.print("\n🔄 [yellow]--reanaliz modu:[/yellow] Scraping atlandı, mevcut veriler yeniden analiz edilecek.")
        sikayetler = []

    # 3. Veritabanına Yaz
    db = SikayetDB()
    try:
        if sikayetler:
            console.print(f"\n💾 Veriler işleniyor...")
            sonuc = db.bulk_insert(sikayetler)
            console.print(f"   - [bold green]{sonuc['eklenen']} yeni şikayet[/bold green] eklendi.")
            console.print(f"   - [dim]{sonuc['atlanan']} şikayet[/dim] zaten mevcut.")

        # 4. Analiz Bekleyenleri Bul ve İşle
        tum = db.sikayetler.all()

        if reanaliz:
            # Tümünü yeniden analiz et
            analiz_bekleyen = tum
            console.print(f"\n🔄 Tüm {len(analiz_bekleyen)} şikayet yeniden analiz edilecek...")
        else:
            # Sadece analiz edilmemişleri işle
            analiz_bekleyen = [s for s in tum if s.get("duygu") == "analiz edilmedi"]

        if analiz_bekleyen:
            console.print(f"\n🤖 [bold cyan]{len(analiz_bekleyen)} şikayet[/bold cyan] analiz ediliyor...")

            for i, s in enumerate(analiz_bekleyen, 1):
                p_text = f"[{i}/{len(analiz_bekleyen)}] {s.get('baslik', '')[:50]}..."
                console.print(f"   {p_text}", end="\r")

                analiz = sikayet_analiz_et(s.get("baslik", ""), s.get("icerik", ""))

                db.sikayet_guncelle(s["sikayet_id"], {
                    "duygu":             analiz.get("duygu", "nötr"),
                    "duygu_skoru":       analiz.get("duygu_skoru", 0.0),
                    "ana_sorun":         analiz.get("ana_sorun", ""),
                    "anahtar_kelimeler": analiz.get("anahtar_kelimeler", []),
                    "aciliyet":          analiz.get("aciliyet", "düşük"),
                    "analiz_yontemi":    analiz.get("yontem", "keyword")
                })

            console.print(f"\n✅ Analiz tamamlandı!")
        else:
            console.print("\n✨ Analizi bekleyen yeni şikayet yok.")

        db.scrape_say()
        console.print(f"\n[bold green]Pipeline başarıyla tamamlandı![/bold green]\n")
        console.print("Verileri görmek için Dashboard'u yenileyin: http://localhost:5050")

    finally:
        db.kapat()


if __name__ == "__main__":
    args = sys.argv[1:]
    use_keyword = "--keyword" in args
    reanaliz = "--reanaliz" in args

    # Sayısal argüman → sayfa sayısı
    sayfa_sayisi = 50
    for a in args:
        try:
            sayfa_sayisi = int(a)
            break
        except ValueError:
            pass

    run_pipeline(sayfa_sayisi, use_keyword=use_keyword, reanaliz=reanaliz)
