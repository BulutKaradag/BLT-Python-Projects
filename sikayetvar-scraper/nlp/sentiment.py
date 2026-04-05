"""
Ollama Duygu Analizi Modülü — gpt-oss:120b-cloud
Her şikayet metni için pozitif/negatif/nötr sınıflandırması,
anahtar kelime çıkarımı ve aciliyet tespiti yapar.

Analiz hiyerarşisi:
  1. Ollama (gpt-oss:120b-cloud) — Ana motor
  2. Keyword Fallback             — Ollama ulaşılamazsa
"""

import requests
import json
import re
import time
from typing import Dict, List, Optional
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


# ─── Ollama ulaşılabilirlik durumu (session boyunca cache) ────────────────────
_OLLAMA_CHECKED: Optional[bool] = None


def ollama_hazir_mi() -> bool:
    """Ollama servisi ayakta mı kontrol et (ilk çağrıda kontrol, sonra cache)."""
    global _OLLAMA_CHECKED
    if _OLLAMA_CHECKED is not None:
        return _OLLAMA_CHECKED
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        _OLLAMA_CHECKED = r.status_code == 200
    except Exception:
        _OLLAMA_CHECKED = False
    return _OLLAMA_CHECKED


def ollama_cache_sifirla():
    """Ollama durumunu sıfırla (yeniden kontrol için)."""
    global _OLLAMA_CHECKED
    _OLLAMA_CHECKED = None


# ─── Prompt ──────────────────────────────────────────────────────────────────

def _prompt_olustur(metin: str) -> str:
    return f"""Aşağıdaki Türkçe sigorta şikayetini analiz et. Sadece JSON formatında yanıt ver, başka hiçbir şey ekleme.

Şikayet metni:
\"\"\"{metin[:1000]}\"\"\"

Döndüreceğin JSON:
{{
  "duygu": "negatif" | "nötr" | "pozitif",
  "duygu_skoru": <-1.0 ile 1.0 arasında float>,
  "ana_sorun": "<en fazla 10 kelimelik özet>",
  "anahtar_kelimeler": ["<kelime1>", "<kelime2>", "<kelime3>", "<kelime4>", "<kelime5>"],
  "aciliyet": "yüksek" | "orta" | "düşük"
}}

Kurallar:
- duygu_skoru: -1.0 = çok negatif, 0.0 = nötr, 1.0 = çok pozitif
- anahtar_kelimeler: sigorta ile ilgili konular (hasar, ödeme, iptal vb.)
- aciliyet: "yüksek" = maddi zarar veya acil durum, "orta" = gecikme, "düşük" = genel şikayet
- Sadece JSON döndür."""


# ─── Keyword Fallback ─────────────────────────────────────────────────────────

def _keyword_fallback(metin: str) -> Dict:
    """Ollama erişilemezse basit anahtar kelime bazlı analiz."""
    metin_lower = metin.lower()

    negatif_kelimeler = [
        "kötü", "berbat", "rezalet", "mağdur", "mağduriyet", "zarar", "iade",
        "ödemedi", "yanıltıcı", "haksız", "sorun", "problem", "şikayet",
        "çözülmedi", "cevap vermedi", "bekletildi", "iptal", "reddetti",
        "gecikme", "gecikiyor", "oyalama", "belirsizlik", "dolandırıcı",
        "hayal kırıklığı", "pişman", "mahkeme", "dava", "tazminat"
    ]
    pozitif_kelimeler = [
        "teşekkür", "memnun", "iyi", "harika", "mükemmel", "çözüldü",
        "yardımcı", "hızlı", "güzel", "başarılı", "olumlu", "tatmin"
    ]

    neg_skor = sum(1 for k in negatif_kelimeler if k in metin_lower)
    pos_skor = sum(1 for k in pozitif_kelimeler if k in metin_lower)

    if neg_skor > pos_skor:
        duygu = "negatif"
        skor = -min(neg_skor / 5.0, 1.0)
    elif pos_skor > neg_skor:
        duygu = "pozitif"
        skor = min(pos_skor / 3.0, 1.0)
    else:
        duygu = "nötr"
        skor = 0.0

    sigorta_kelimeleri = [
        "hasar", "poliçe", "prim", "tazminat", "ödeme", "iptal", "yenileme",
        "acente", "sigortalı", "kasko", "trafik", "sağlık", "hayat",
        "konut", "çağrı merkezi", "müşteri hizmetleri", "hesap", "iade",
        "faiz", "kredi", "kart"
    ]
    anahtar = [k for k in sigorta_kelimeleri if k in metin_lower][:5]

    acil_kelimeler = ["acil", "derhal", "hemen", "ivedi", "mahkeme", "dava", "avukat"]
    aciliyet = (
        "yüksek" if any(k in metin_lower for k in acil_kelimeler)
        else "orta" if neg_skor >= 3
        else "düşük"
    )

    return {
        "duygu": duygu,
        "duygu_skoru": round(skor, 2),
        "ana_sorun": "Keyword analizi (Ollama bağlantısı yok)",
        "anahtar_kelimeler": anahtar if anahtar else ["sigorta"],
        "aciliyet": aciliyet,
        "yontem": "keyword"
    }


# ─── Ollama Analiz ───────────────────────────────────────────────────────────

def _ollama_analiz_et(metin: str, deneme: int = 1) -> Optional[Dict]:
    """Ollama gpt-oss:120b-cloud ile analiz yapar. Hata durumunda retry uygular."""
    global _OLLAMA_CHECKED

    if not ollama_hazir_mi():
        return None

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": _prompt_olustur(metin),
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 600
            }
        }

        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

        if r.status_code == 200:
            yanit = r.json().get("response", "")
            # JSON bloğunu çıkar
            json_match = re.search(r'\{.*?\}', yanit, re.DOTALL)
            if json_match:
                try:
                    analiz = json.loads(json_match.group())
                    analiz["yontem"] = "ollama"
                    return analiz
                except json.JSONDecodeError:
                    print(f"  [UYARI] Ollama JSON parse hatası. Yanıt: {yanit[:100]}")
        else:
            print(f"  [UYARI] Ollama HTTP {r.status_code}: {r.text[:100]}")

    except requests.exceptions.ReadTimeout:
        print(f"  [ZAMAN AŞIMI] Ollama ({OLLAMA_MODEL}) {OLLAMA_TIMEOUT}s içinde yanıt vermedi.")
        if deneme <= 2:
            print(f"  Yeniden deneniyor ({deneme}/2)...")
            time.sleep(5)
            return _ollama_analiz_et(metin, deneme + 1)
        else:
            # Ollama ulaşılamıyor, cache'i sıfırla
            _OLLAMA_CHECKED = False

    except requests.exceptions.ConnectionError:
        print(f"  [HATA] Ollama'ya bağlanılamadı ({OLLAMA_BASE_URL}). Keyword analizine geçiliyor.")
        _OLLAMA_CHECKED = False

    except Exception as e:
        print(f"  [UYARI] Ollama hatası: {e}")

    return None


# ─── Ana Analiz Fonksiyonu ────────────────────────────────────────────────────

def sikayet_analiz_et(baslik: str, icerik: str) -> Dict:
    """
    Şikayeti analiz eder.
    1. Ollama (gpt-oss:120b-cloud) ile dener.
    2. Başarısız olursa keyword fallback kullanır.
    """
    metin = f"{baslik}\n\n{icerik}".strip()
    if not metin:
        return _keyword_fallback("sigorta şikayeti")

    # Ollama ile dene
    analiz = _ollama_analiz_et(metin)

    # Fallback
    if not analiz:
        analiz = _keyword_fallback(metin)

    return analiz


# ─── Toplu Analiz (DB ile) ────────────────────────────────────────────────────

def toplu_analiz(sikayetler: List[dict], db=None) -> int:
    """
    Veritabanındaki duygu analizi yapılmamış şikayetleri analiz eder.
    Kaç tane işlendiğini döner.
    """
    islenen = 0
    for s in sikayetler:
        if s.get("duygu") and s["duygu"] not in ("analiz edilmedi", ""):
            continue

        analiz = sikayet_analiz_et(s.get("baslik", ""), s.get("icerik", ""))

        if db:
            db.sikayet_guncelle(s["sikayet_id"], {
                "duygu":             analiz.get("duygu", "nötr"),
                "duygu_skoru":       analiz.get("duygu_skoru", 0.0),
                "ana_sorun":         analiz.get("ana_sorun", ""),
                "anahtar_kelimeler": analiz.get("anahtar_kelimeler", []),
                "aciliyet":          analiz.get("aciliyet", "düşük"),
                "analiz_yontemi":    analiz.get("yontem", "keyword")
            })

        islenen += 1
    return islenen
