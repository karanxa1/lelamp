import requests
import json

def test_music_search():
    query = "Pathaan"
    search_engine = "gaama"
    url = f"https://musicapi.x007.workers.dev/search?q={query}&searchEngine={search_engine}"
    
    print(f"🎵 Testing Music API Search...")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ API Response Success!")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ API Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_music_search()
