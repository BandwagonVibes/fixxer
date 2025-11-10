#!/usr/bin/env python3
"""
Minimal Ollama Test - Uses exact same approach as PhotoSort
"""

import requests
import json
import base64
from pathlib import Path

# EXACT same config as PhotoSort
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "openbmb/minicpm-v2.6:q4_K_M"
TEST_IMAGE = Path.home() / "Downloads/photosortproject/Testing/staging/_1370867.jpeg"

print("Testing Ollama with PhotoSort's exact configuration...\n")

# Encode image
print(f"1. Encoding image: {TEST_IMAGE.name}")
with open(TEST_IMAGE, 'rb') as f:
    base64_image = base64.b64encode(f.read()).decode('utf-8')
print(f"   ✅ Encoded: {len(base64_image)} bytes\n")

# Build request (EXACT same as PhotoSort)
print("2. Building request...")
prompt = """What is in this image? Describe it concisely for a file name.
{
  "description": "<your 2-4 word description>"
}"""

payload = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": prompt,
            "images": [base64_image]
        }
    ],
    "stream": False,
}

print(f"   Model: {MODEL_NAME}")
print(f"   URL: {OLLAMA_URL}\n")

# Make request
print("3. Calling Ollama...")
try:
    response = requests.post(OLLAMA_URL, json=payload, timeout=60)
    print(f"   Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ SUCCESS!\n")
        
        result = response.json()
        content = result['message']['content'].strip()
        
        print("4. Response:")
        print(f"   Raw: {content}\n")
        
        # Try to parse as JSON
        try:
            data = json.loads(content)
            print("   ✅ Valid JSON!")
            print(f"   Description: \"{data.get('description', 'N/A')}\"\n")
        except json.JSONDecodeError as e:
            print(f"   ❌ Not valid JSON: {e}")
            print(f"   (But we got a response!)\n")
    else:
        print(f"   ❌ FAILED!")
        print(f"   Error: {response.text}\n")
        
except requests.exceptions.ConnectionError:
    print("   ❌ Cannot connect to Ollama!")
    print("   Is it running? Try: ollama serve\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

print("Done!")
