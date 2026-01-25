import requests
import json
import os

def search_web(query):
    api_key = "994d8826d49aa3396315688419398c824ed722c0"
    print(f"Testing API Key: {api_key}")
    
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print("Raw JSON Response keys:", results.keys())
            
            summary = []
            if "answerBox" in results:
                print("Found answerBox")
                summary.append(f"Direct Answer: {results['answerBox'].get('answer') or results['answerBox'].get('snippet')}")
            
            if "organic" in results:
                print(f"Found {len(results['organic'])} organic results")
                for i, item in enumerate(results["organic"][:3]):
                    summary.append(f"{i+1}. {item.get('title')}: {item.get('snippet')}")
            
            final_result = "\n".join(summary)
            print("\nParsed Result:")
            print(final_result)
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    search_web("current weather in New York")
