"""
Simple script to test OpenRouter API connection.
Run with: uv run python test_api.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    """Test OpenRouter API with xiaomi/mimo model."""
    from openai import OpenAI
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    site_url = os.getenv("OPENROUTER_SITE_URL", "")
    site_name = os.getenv("OPENROUTER_SITE_NAME", "")
    
    print("="*50)
    print("OpenRouter API Test")
    print("="*50)
    
    if not api_key:
        print("❌ ERROR: OPENROUTER_API_KEY not found in .env file")
        print("\nCreate a .env file with:")
        print("OPENROUTER_API_KEY=sk-or-v1-your-key-here")
        return False
    
    print(f"✓ API Key found: {api_key[:20]}...")
    
    # Check key format
    if not api_key.startswith("sk-or-"):
        print(f"⚠ WARNING: Key doesn't start with 'sk-or-'. May be invalid.")
        print(f"  Your key starts with: {api_key[:10]}...")
        print(f"  Valid OpenRouter keys start with: sk-or-v1-...")
    
    print("\nTesting API connection...")
    
    try:
        # Build optional headers for app attribution
        default_headers = {}
        if site_url:
            default_headers["HTTP-Referer"] = site_url
        if site_name:
            default_headers["X-Title"] = site_name
        
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers=default_headers if default_headers else None,
        )
        
        response = client.chat.completions.create(
            model="nvidia/nemotron-nano-9b-v2",
            messages=[
                {"role": "user", "content": "Say hello in one sentence."}
            ],
            max_tokens=50,
        )
        
        result = response.choices[0].message.content
        print(f"\n✓ API Response: {result}")
        print("\n" + "="*50)
        print("✓ OpenRouter API is working!")
        print("="*50)
        return True
        
    except Exception as e:
        print(f"\n❌ API Error: {e}")
        print("\n" + "="*50)
        print("Troubleshooting:")
        print("1. Get a valid key from: https://openrouter.ai/keys")
        print("2. Key should start with: sk-or-v1-...")
        print("3. Update .env file with the correct key")
        print("="*50)
        return False


def test_livekit():
    """Test LiveKit credentials."""
    print("\n" + "="*50)
    print("LiveKit Credentials Check")
    print("="*50)
    
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    if url:
        print(f"✓ LIVEKIT_URL: {url}")
    else:
        print("❌ LIVEKIT_URL: Not found")
    
    if api_key:
        print(f"✓ LIVEKIT_API_KEY: {api_key[:15]}...")
    else:
        print("❌ LIVEKIT_API_KEY: Not found")
    
    if api_secret:
        print(f"✓ LIVEKIT_API_SECRET: {api_secret[:15]}...")
    else:
        print("❌ LIVEKIT_API_SECRET: Not found")
    
    if all([url, api_key, api_secret]):
        print("\n✓ All LiveKit credentials found!")
        return True
    else:
        print("\n⚠ LiveKit credentials incomplete.")
        print("Get credentials from: https://cloud.livekit.io")
        return False


if __name__ == "__main__":
    print("\n")
    
    # Test OpenRouter
    openrouter_ok = test_openrouter()
    
    # Test LiveKit
    livekit_ok = test_livekit()
    
    print("\n" + "="*50)
    print("Summary")
    print("="*50)
    print(f"OpenRouter API: {'✓ Working' if openrouter_ok else '❌ Failed'}")
    print(f"LiveKit Creds:  {'✓ Found' if livekit_ok else '❌ Missing'}")
    print("="*50)
