
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path.cwd()))

from scraper.scraper import scrape

def test():
    print("Scraping 1 page...")
    result = scrape(max_sayfa=1)
    
    print(f"\nTotal complaints: {len(result)}")
    has_url = [s for s in result if s.get('url')]
    print(f"Complaints with URL: {len(has_url)}")
    
    if len(result) > 0:
        print("\nSample URLs extracted:")
        for s in result[:5]:
            print(f"- {s.get('baslik', 'No Title')[:50]}... -> {s.get('url', 'MISSING')}")
            
    if len(result) == len(has_url) and len(result) > 0:
        print("\n✅ SUCCESS: All complaints have URLs.")
    else:
        print("\n❌ FAILURE: Some complaints are missing URLs.")

if __name__ == "__main__":
    test()
