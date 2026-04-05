"""
TinyDB Veritabanı Katmanı
Şikayetleri yerel JSON dosyasında saklar, okuma/yazma/arama işlemleri yapar.
"""
from tinydb import TinyDB, Query, where
from tinydb.operations import set as tdb_set
from datetime import datetime
from pathlib import Path
from config import TINYDB_PATH
from typing import Optional, Dict, List, Any


class SikayetDB:
    def __init__(self):
        Path(TINYDB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(TINYDB_PATH, encoding="utf-8", ensure_ascii=False)
        self.sikayetler = self.db.table("sikayetler")
        self.meta = self.db.table("meta")
        self._ensure_indexes()

    def _ensure_indexes(self):
        """İlk çalıştırmada meta bilgisini yaz."""
        if not self.meta.all():
            self.meta.insert({
                "created_at": datetime.now().isoformat(),
                "total_scrapes": 0
            })

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def sikayet_var_mi(self, sikayet_id: str) -> bool:
        """Verilen ID ile şikayet zaten kayıtlı mı?"""
        Sikayet = Query()
        return bool(self.sikayetler.search(Sikayet.sikayet_id == sikayet_id))

    def sikayet_ekle(self, sikayet: dict) -> Optional[int]:
        """Yeni şikayet ekle. Zaten varsa None döner."""
        if self.sikayet_var_mi(sikayet["sikayet_id"]):
            return None
        sikayet["scrape_tarihi"] = datetime.now().isoformat()
        return self.sikayetler.insert(sikayet)

    def bulk_insert(self, sikayetler: List[dict]) -> Dict[str, int]:
        """Toplu ekleme. Kaç tane eklendi / atlandı raporlar."""
        eklenen = 0
        atlanan = 0
        for s in sikayetler:
            result = self.sikayet_ekle(s)
            if result:
                eklenen += 1
            else:
                atlanan += 1
        return {"eklenen": eklenen, "atlanan": atlanan}

    def sikayet_guncelle(self, sikayet_id: str, alanlar: dict):
        """Mevcut şikayeti güncelle (örn. duygu ekleme)."""
        Sikayet = Query()
        self.sikayetler.update(alanlar, Sikayet.sikayet_id == sikayet_id)

    def tum_sikayetler(
        self,
        durum: Optional[str] = None,
        duygu: Optional[str] = None,
        arama: Optional[str] = None,
        tarih_baslangic: Optional[str] = None,
        tarih_bitis: Optional[str] = None,
        siralama: str = "tarih",
        artan: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Filtrelenmiş şikayet listesi döner."""
        sonuclar = self.sikayetler.all()

        # Filtreler
        if durum:
            sonuclar = [s for s in sonuclar if s.get("durum") == durum]
        if duygu:
            sonuclar = [s for s in sonuclar if s.get("duygu") == duygu]
        if arama:
            arama_lower = arama.lower()
            sonuclar = [
                s for s in sonuclar
                if arama_lower in (s.get("baslik") or "").lower()
                or arama_lower in (s.get("icerik") or "").lower()
            ]
        if tarih_baslangic:
            sonuclar = [s for s in sonuclar if s.get("tarih", "") >= tarih_baslangic]
        if tarih_bitis:
            sonuclar = [s for s in sonuclar if s.get("tarih", "") <= tarih_bitis]

        # Sıralama
        reverse = not artan
        if siralama == "tarih":
            sonuclar.sort(key=lambda x: x.get("tarih", ""), reverse=reverse)
        elif siralama == "begeni":
            sonuclar.sort(key=lambda x: x.get("begeni_sayisi", 0), reverse=reverse)
        elif siralama == "yorum":
            sonuclar.sort(key=lambda x: x.get("yorum_sayisi", 0), reverse=reverse)

        total = len(sonuclar)
        return {
            "total": total,
            "data": sonuclar[offset: offset + limit]
        }

    def istatistikler(self) -> Dict[str, Any]:
        """Dashboard için özet istatistikler."""
        tumumu = self.sikayetler.all()
        toplam = len(tumumu)

        if toplam == 0:
            return {
                "toplam": 0, "cozuldu": 0, "beklemede": 0, "reddedildi": 0,
                "cozum_orani": 0, "pozitif": 0, "negatif": 0, "notr": 0,
                "durum_dagilimi": {}, "duygu_dagilimi": {},
                "aylik_trend": [], "anahtar_kelimeler": []
            }

        # Durum dağılımı
        durum_sayilari = {}
        for s in tumumu:
            d = s.get("durum", "bilinmiyor")
            durum_sayilari[d] = durum_sayilari.get(d, 0) + 1

        cozuldu = durum_sayilari.get("çözüldü", 0)
        beklemede = durum_sayilari.get("beklemede", 0)
        reddedildi = durum_sayilari.get("reddedildi", 0)

        # Duygu dağılımı
        duygu_sayilari = {}
        for s in tumumu:
            dy = s.get("duygu", "analiz edilmedi")
            duygu_sayilari[dy] = duygu_sayilari.get(dy, 0) + 1

        # Aylık trend
        aylik = {}
        for s in tumumu:
            tarih_str = s.get("tarih", "")
            if tarih_str and len(tarih_str) >= 7:
                ay = tarih_str[:7]  # "YYYY-MM"
                aylik[ay] = aylik.get(ay, 0) + 1
        aylik_trend = sorted([{"ay": k, "sayi": v} for k, v in aylik.items()], key=lambda x: x["ay"])

        # Anahtar kelimeler (Defensive check)
        kw_sayilari = {}
        for s in tumumu:
            keywords = s.get("anahtar_kelimeler")
            if keywords and isinstance(keywords, list):
                for kw in keywords:
                    if kw:
                        kw_sayilari[kw] = kw_sayilari.get(kw, 0) + 1
        
        top_keywords = sorted(kw_sayilari.items(), key=lambda x: x[1], reverse=True)[:20]

        return {
            "toplam": toplam,
            "cozuldu": cozuldu,
            "beklemede": beklemede,
            "reddedildi": reddedildi,
            "cozum_orani": round((cozuldu / toplam) * 100, 1) if toplam > 0 else 0,
            "pozitif": duygu_sayilari.get("pozitif", 0),
            "negatif": duygu_sayilari.get("negatif", 0),
            "notr": duygu_sayilari.get("nötr", 0),
            "durum_dagilimi": durum_sayilari,
            "duygu_dagilimi": duygu_sayilari,
            "aylik_trend": aylik_trend,
            "anahtar_kelimeler": [{"kelime": k, "sayi": v} for k, v in top_keywords],
            "son_scrape": self._son_scrape_tarihi()
        }

    def _son_scrape_tarihi(self) -> Optional[str]:
        tumumu = self.sikayetler.all()
        if not tumumu:
            return None
        tarihler = [s.get("scrape_tarihi", "") for s in tumumu if s.get("scrape_tarihi")]
        return max(tarihler) if tarihler else None

    def scrape_say(self):
        """Scrape sayacını artır."""
        Sikayet = Query()
        kayit = self.meta.all()
        if kayit:
            self.meta.update(
                {"total_scrapes": kayit[0].get("total_scrapes", 0) + 1,
                 "last_scrape": datetime.now().isoformat()}
            )

    def kapat(self):
        self.db.close()
