"""
Şikayetvar Scraper - Konfigürasyon Dosyası
"""
import os
from pathlib import Path

# Proje kök dizini
BASE_DIR = Path(__file__).parent

# Database
TINYDB_PATH = BASE_DIR / "data" / "sikayetler.json"

# Scraper ayarları
SCRAPER_TARGET_URL = "https://www.sikayetvar.com/turkiye-katilim-sigorta"
SCRAPER_MAX_PAGES = 50   # 539 şikayet ≈ 45 sayfa → 50 ile buffer
SCRAPER_DELAY_MIN = 2.0   # saniye
SCRAPER_DELAY_MAX = 5.0   # saniye (hız artırıldı)
SCRAPER_HEADLESS = True
SCRAPER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# NLP / AI Modeli Ayarları
ANALYSIS_MODE = os.getenv("ANALYSIS_MODE", "ollama")  # Seçenekler: gemini, ollama, keyword

# Google Gemini (Tavsiye edilen)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyCJRqbXNCtbEfsGA3Ds30_8lJimFfXdJ-Y")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Ollama (Yerel yedek)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b-cloud")
OLLAMA_TIMEOUT = 120  # saniye (Zaman aşımı 120s yapıldı)

# Flask
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5050
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# APScheduler
SCHEDULER_INTERVAL_HOURS = 24  # Her 24 saatte bir scrape
