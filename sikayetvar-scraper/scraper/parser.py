"""
Sikayetvar.com HTML Parser
Playwright tarafından alınan ham HTML'yi parse eder ve
normalize edilmiş şikayet objelerine dönüştürür.
"""
from bs4 import BeautifulSoup
from datetime import datetime
import re
import hashlib
from typing import List, Dict, Optional


def _tarih_parse(tarih_str: str) -> str:
    """
    Sikayetvar tarih formatlarını ISO 8601'e çevirir.
    Örnek: "3 Nisan 2024", "2 gün önce", "bugün"
    """
    if not tarih_str:
        return datetime.now().strftime("%Y-%m-%d")

    tarih_str = tarih_str.strip().lower()

    # "bugün" veya "dün"
    now = datetime.now()
    if "bugün" in tarih_str or "today" in tarih_str:
        return now.strftime("%Y-%m-%d")
    if "dün" in tarih_str or "yesterday" in tarih_str:
        from datetime import timedelta
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")

    # "X gün önce", "X ay önce", "X yıl önce"
    gun = re.search(r"(\d+)\s*gün önce", tarih_str)
    if gun:
        from datetime import timedelta
        return (now - timedelta(days=int(gun.group(1)))).strftime("%Y-%m-%d")
    ay = re.search(r"(\d+)\s*ay önce", tarih_str)
    if ay:
        from datetime import timedelta
        return (now - timedelta(days=int(ay.group(1)) * 30)).strftime("%Y-%m-%d")
    yil = re.search(r"(\d+)\s*yıl önce", tarih_str)
    if yil:
        from datetime import timedelta
        return (now - timedelta(days=int(yil.group(1)) * 365)).strftime("%Y-%m-%d")

    # "3 Nisan 2024" formatı
    ay_map = {
        "ocak": "01", "şubat": "02", "mart": "03", "nisan": "04",
        "mayıs": "05", "haziran": "06", "temmuz": "07", "ağustos": "08",
        "eylül": "09", "ekim": "10", "kasım": "11", "aralık": "12"
    }
    for ay_adi, ay_no in ay_map.items():
        if ay_adi in tarih_str:
            mat = re.search(r"(\d{1,2})\s*" + ay_adi + r"\s*(\d{4})", tarih_str)
            if mat:
                return f"{mat.group(2)}-{ay_no}-{mat.group(1).zfill(2)}"

    # ISO format doğrudan
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", tarih_str)
    if iso:
        return iso.group(0)

    # Fallback
    return now.strftime("%Y-%m-%d")


def _sikayet_id_olustur(url: str) -> str:
    """URL'den benzersiz ID üretir."""
    # URL son parçasını al
    parca = url.rstrip("/").split("/")[-1]
    if parca and len(parca) > 3:
        return parca
    # Hash fallback
    return hashlib.md5(url.encode()).hexdigest()[:12]


def _temizle(metin: str) -> str:
    """Metni temizler: HTML entities, fazla boşluk, newline."""
    if not metin:
        return ""
    metin = re.sub(r'\s+', ' ', metin)
    metin = metin.strip()
    return metin


def _durum_belirle(soup_element) -> str:
    """Şikayetin çözüm durumunu belirler."""
    # Sikayetvar'daki CSS class veya badge tipinden durum çıkarmaya çalış
    tum_metin = str(soup_element).lower()
    
    if any(k in tum_metin for k in ["çözüldü", "cozuldu", "solved", "resolved", "çözüm bulundu"]):
        return "çözüldü"
    if any(k in tum_metin for k in ["reddedildi", "reddedilmiş", "rejected"]):
        return "reddedildi"
    return "beklemede"


def parse_sikayet_listesi(html: str, base_url: str = "") -> List[Dict]:
    """
    Şikayet listesi sayfasının HTML'ini parse eder.
    Her şikayet için özet verilerini döner.
    """
    soup = BeautifulSoup(html, "lxml")
    sikayetler = []

    # Sikayetvar'ın şikayet kart elemanları
    # Olası selector'lar (site güncellenirse değişebilir)
    kart_selectors = [
        "article.complaint-item",
        "div.complaint-item",
        "li.complaint-item",
        "article[class*='complaint']",
        "div[class*='brand-slug-card']",
        "div.card-v2",
        "article.card-v2",
    ]

    kartlar = []
    for sel in kart_selectors:
        kartlar = soup.select(sel)
        if kartlar:
            break

    # Hiçbir selector çalışmazsa generic arama
    if not kartlar:
        kartlar = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"complaint|sikayet|card", re.I))

    for kart in kartlar:
        try:
            # Başlık
            baslik_el = (
                kart.select_one("h2") or
                kart.select_one("h3") or
                kart.select_one("a.complaint-title") or
                kart.select_one("[class*='title']") or
                kart.select_one("a")
            )
            baslik = _temizle(baslik_el.get_text()) if baslik_el else "Başlıksız"

            # İçerik özeti
            icerik_el = (
                kart.select_one("p.complaint-desc") or
                kart.select_one("p[class*='desc']") or
                kart.select_one("p[class*='content']") or
                kart.select_one("p") or
                kart.select_one("div[class*='text']")
            )
            icerik = _temizle(icerik_el.get_text()) if icerik_el else ""

            # URL
            link_el = kart.select_one("a.complaint-layer") or kart.select_one("a[href*='/sikayet/'], a[href*='/complaint/']") or baslik_el
            url = ""
            if link_el:
                # Eğer element <a> değilse, içindeki ilk <a> etiketini bulmayı dene
                final_link = link_el if link_el.name == "a" else link_el.find("a")
                
                if final_link and final_link.get("href"):
                    href = final_link.get("href", "")
                    # Göreceli linkleri mutlak hale getir
                    if href.startswith("/"):
                        url = "https://www.sikayetvar.com" + href
                    else:
                        url = href


            sikayet_id = _sikayet_id_olustur(url or baslik)

            # ── Tarih ─────────────────────────────────────────────────
            # Öncelik sırası:
            #   1. time.post-time[datetime]  – ISO format direkt
            #   2. time.post-time[title]     – "3 Nisan 2024 16:57"
            #   3. Herhangi bir time[datetime]
            #   4. [class*='date'], [class*='tarih'] vb.
            tarih_raw = ""
            # 1 & 2: Sikayetvar'ın kendi time.post-time elementi
            pt = kart.select_one("time.post-time, time[class*='post-time'], time[class*='date']")
            if pt:
                tarih_raw = (
                    pt.get("datetime", "")
                    or pt.get("title", "")
                    or pt.get_text()
                )
            if not tarih_raw:
                # 3: Herhangi time[datetime]
                t = kart.select_one("time[datetime]")
                if t:
                    tarih_raw = t.get("datetime", "") or t.get_text()
            if not tarih_raw:
                # 4: Generic class-based
                tarih_el = (
                    kart.select_one("[class*='post-time']") or
                    kart.select_one("[class*='date']") or
                    kart.select_one("[class*='tarih']") or
                    kart.select_one("[class*='time']") or
                    kart.select_one("time")
                )
                if tarih_el:
                    tarih_raw = (
                        tarih_el.get("datetime", "")
                        or tarih_el.get("title", "")
                        or tarih_el.get_text()
                    )

            tarih = _tarih_parse(tarih_raw)


            # Beğeni / yorum sayısı
            def sayi_al(class_pattern):
                el = kart.select_one(f"[class*='{class_pattern}']")
                if el:
                    mat = re.search(r"\d+", el.get_text())
                    return int(mat.group()) if mat else 0
                return 0

            begeni = sayi_al("like") or sayi_al("helpful") or sayi_al("vote")
            yorum = sayi_al("comment") or sayi_al("reply") or sayi_al("answer")

            # Durum
            durum = _durum_belirle(kart)

            sikayetler.append({
                "sikayet_id": sikayet_id,
                "baslik": baslik,
                "icerik": icerik,
                "tarih": tarih,
                "durum": durum,
                "begeni_sayisi": begeni,
                "yorum_sayisi": yorum,
                "url": url,
                "duygu": "analiz edilmedi",
                "duygu_skoru": 0.0,
                "ana_sorun": "",
                "anahtar_kelimeler": [],
                "aciliyet": "orta",
                "analiz_yontemi": None
            })

        except Exception as e:
            print(f"  [UYARI] Kart parse hatası: {e}")
            continue

    return sikayetler


def parse_sikayet_detay(html: str, mevcut: dict) -> dict:
    """
    Tek bir şikayet detay sayfasını parse eder.
    Mevcut özet verisini zenginleştirir.
    """
    soup = BeautifulSoup(html, "lxml")

    # Tam içerik
    icerik_el = (
        soup.select_one("div.complaint-detail-description") or
        soup.select_one("div[class*='complaint-text']") or
        soup.select_one("div[class*='detail-text']") or
        soup.select_one("div[itemprop='description']") or
        soup.select_one("section.complaint-body")
    )
    if icerik_el:
        mevcut["icerik"] = _temizle(icerik_el.get_text())

    return mevcut
