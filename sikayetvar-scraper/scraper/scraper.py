"""
Sikayetvar.com Ana Scraper Modülü
Playwright ile headless tarayıcı kullanarak şikayetleri çeker.
"""
import asyncio
import random
import time
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

# Path fix
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from config import (
    SCRAPER_TARGET_URL, SCRAPER_MAX_PAGES,
    SCRAPER_DELAY_MIN, SCRAPER_DELAY_MAX,
    SCRAPER_HEADLESS, SCRAPER_USER_AGENT
)
from scraper.parser import parse_sikayet_listesi, parse_sikayet_detay
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()


async def _bekle(min_s: float = SCRAPER_DELAY_MIN, max_s: float = SCRAPER_DELAY_MAX):
    """İnsan gibi random bekleme."""
    sure = random.uniform(min_s, max_s)
    await asyncio.sleep(sure)


async def _sayfa_kaydir(page):
    """Tembel yükleme için sayfayı kaydır."""
    await page.evaluate("""
        window.scrollTo({top: document.body.scrollHeight / 2, behavior: 'smooth'});
    """)
    await asyncio.sleep(0.8)
    await page.evaluate("""
        window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
    """)
    await asyncio.sleep(0.5)


async def sayfa_scrape(page, url: str, sayfa_no: int) -> List[Dict]:
    """Tek bir sayfayı scrape eder."""
    try:
        console.print(f"  → Sayfa {sayfa_no} yükleniyor: {url}")
        
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Şikayetlerin yüklenmesini bekle
        try:
            await page.wait_for_selector(
                "article, div.complaint-item, div[class*='card'], li[class*='complaint']",
                timeout=15000
            )
        except PlaywrightTimeout:
            console.print(f"  [UYARI] Sayfa {sayfa_no}: İçerik seçici bulunamadı, devam ediliyor...")

        # Lazy-load için kaydır
        await _sayfa_kaydir(page)
        
        html = await page.content()
        sikayetler = parse_sikayet_listesi(html, url)
        
        console.print(f"  ✓ Sayfa {sayfa_no}: [green]{len(sikayetler)} şikayet[/green] bulundu")
        return sikayetler

    except PlaywrightTimeout:
        console.print(f"  [HATA] Sayfa {sayfa_no} timeout: {url}")
        return []
    except Exception as e:
        console.print(f"  [HATA] Sayfa {sayfa_no}: {e}")
        return []


def _sonraki_sayfa_url(base_url: str, sayfa_no: int) -> str:
    """Pagination URL'sini oluşturur."""
    if sayfa_no == 1:
        return base_url
    # Sikayetvar'ın pagination formatı: ?page=2
    base = base_url.rstrip("/")
    return f"{base}?page={sayfa_no}"


async def scrape_async(max_sayfa: int = SCRAPER_MAX_PAGES) -> List[Dict]:
    """
    Ana async scrape fonksiyonu.
    max_sayfa kadar sayfa traverse eder.
    """
    tum_sikayetler = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=SCRAPER_HEADLESS)
        context = await browser.new_context(
            user_agent=SCRAPER_USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="tr-TR",
            extra_http_headers={
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        page = await context.new_page()

        # Bot tespitini azalt
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        """)

        console.print(f"\n[bold cyan]Scraping başlıyor...[/bold cyan]")
        console.print(f"Hedef: {SCRAPER_TARGET_URL}")
        console.print(f"Max sayfa: {max_sayfa}\n")

        bos_sayfa_sayisi = 0  # Ardışık boş sayfa sayacı

        for sayfa_no in range(1, max_sayfa + 1):
            url = _sonraki_sayfa_url(SCRAPER_TARGET_URL, sayfa_no)
            sikayetler = await sayfa_scrape(page, url, sayfa_no)

            # Boş sayfa kontrolü – 2 ardışık boş sayfa = scraping bitti
            if not sikayetler:
                bos_sayfa_sayisi += 1
                console.print(f"  [yellow]Boş sayfa #{bos_sayfa_sayisi}: {url}[/yellow]")
                if bos_sayfa_sayisi >= 2:
                    console.print(f"\n[bold yellow]2 ardışık boş sayfa → Scraping tamamlandı (sayfa {sayfa_no})[/bold yellow]")
                    break
            else:
                bos_sayfa_sayisi = 0  # Reset

            # Her bir şikayetin detay sayfasını ziyaret et (Tam içerik için)
            for s in sikayetler:
                if s.get("url"):
                    try:
                        console.print(f"    • Detay yükleniyor: [dim]{s['url']}[/dim]")
                        await page.goto(s["url"], wait_until="domcontentloaded", timeout=20000)
                        detail_html = await page.content()
                        # parse_sikayet_detay objeyi yerinde günceller
                        parse_sikayet_detay(detail_html, s)
                        # Kısa bir bekleme (bot tespiti için)
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                    except Exception as de:
                        console.print(f"    [UYARI] Detay sayfası hatası ({s['url']}): {de}")

            tum_sikayetler.extend(sikayetler)

            # Sayfalar arası bekleme
            if sayfa_no < max_sayfa:
                await _bekle()

        await browser.close()

    console.print(f"\n[bold green]Toplam {len(tum_sikayetler)} şikayet toplandı![/bold green]")
    return tum_sikayetler


def scrape(max_sayfa: int = SCRAPER_MAX_PAGES) -> List[Dict]:
    """Senkron wrapper (CLI ve scheduler için)."""
    return asyncio.run(scrape_async(max_sayfa))


if __name__ == "__main__":
    result = scrape(max_sayfa=2)
    for s in result[:3]:
        print(s)
