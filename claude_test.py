# test_api.py
from dotenv import load_dotenv
import os
import anthropic

load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')
print(f"API Key: {api_key[:20]}..." if api_key else "No API key found")

try:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3-5-sonnet-20241220",
        max_tokens=20,
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("✅ API key works!")
    print(f"Response: {response.content[0].text}")
except Exception as e:
    print(f"❌ Error: {e}")