#!/usr/bin/env python3
"""
Critique Prompt Tester for PhotoSort v9.0
Test different AI critique prompts without running the full workflow.

Usage:
  python test_critique_prompt.py <image_path> [model_name]
  
Example:
  python test_critique_prompt.py test.jpg qwen2.5vl:3b
  python test_critique_prompt.py test.jpg minicpm-v2.6
"""

import sys
import json
import base64
import requests
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
TIMEOUT = 120

# =============================================================================
# PROMPT VERSIONS - Edit these to test different approaches!
# =============================================================================

PROMPT_V1_ORIGINAL = """
You are a professional Creative Director and magazine photo editor. Your job is to provide ambitious, artistic, and creative feedback to elevate a photo from "good" to "great."

**CREATIVE TOOLBOX (Use these for your suggestion):**
* **Mood & Atmosphere:** (e.g., 'cinematic,' 'moody,' 'ethereal,' 'nostalgic,' 'dramatic')
* **Color Grading:** (e.g., 'filmic teal-orange,' 'warm vintage,' 'cool desaturation,' 'split-toning')
* **Light & Shadow:** (e.g., 'crushed blacks,' 'soft, lifted shadows,' 'localized dodging/burning,' 'a subtle vignette')
* **Texture:** (e.g., 'add fine-grain film,' 'soften the focus,' 'increase clarity')

**YOUR TASK:**
Analyze the provided image by following these steps *internally*:
1.  **Composition:** Analyze balance, guiding principles (thirds, lines), and subject placement. Rate it 1-10.
2.  **Lighting & Exposure:** Analyze quality, direction, temperature, and any blown highlights or crushed shadows.
3.  **Color & Style:** Analyze the color palette, white balance, and current post-processing style.

After your analysis, you MUST return **ONLY a single, valid JSON object**. Do not provide *any* other text, preamble, or conversation. Your response must be 100% valid JSON, formatted *exactly* like this template:

```json
{
  "composition_score": <an integer from 1 to 10>,
  "composition_critique": "<A brief, one-sentence critique of the composition.>",
  "lighting_critique": "<A brief, one-sentence critique of the lighting and exposure.>",
  "color_critique": "<A brief, one-sentence critique of the color and current style.>",
  "final_verdict": "<A one-sentence summary of what works and what doesn't.>",
  "creative_mood": "<The single, most ambitious 'Creative Mood' this photo could have, chosen from the toolbox.>",
  "creative_suggestion": "<Your single, ambitious, artistic post-processing suggestion to achieve that mood. This must be a detailed, actionable paragraph.>"
}
```
"""

PROMPT_V2_PHOTOGRAPHY_EXPERT = """
You are an award-winning photography post-processing expert. You specialize in Lightroom and Photoshop workflows.

Analyze this image and provide SPECIFIC, ACTIONABLE post-processing guidance.

Think through these aspects:
1. **Exposure & Tones**: Highlights, shadows, whites, blacks, midtones
2. **Color Science**: White balance, vibrance, saturation, HSL adjustments
3. **Detail & Clarity**: Sharpening, texture, clarity, noise reduction
4. **Creative Grading**: LUTs, color grading, film emulation, mood

Return ONLY valid JSON with this structure:

{
  "composition_score": <1-10>,
  "technical_assessment": "<What's working technically, what needs fixing>",
  "lightroom_settings": {
    "exposure": "<specific adjustment like '+0.5 stops'>",
    "highlights": "<like '-30'>",
    "shadows": "<like '+40'>",
    "whites": "<like '-10'>",
    "blacks": "<like '-15'>",
    "color_temp": "<like 'warm +200K' or 'cool -300K'>",
    "key_hsl_adjustments": "<like 'Orange -10 saturation, Blue +20 luminance'>"
  },
  "creative_direction": "<One specific creative vision for this image>",
  "post_processing_steps": "<Detailed step-by-step workflow to achieve that vision>"
}
"""

PROMPT_V3_INSTAGRAM_STYLE = """
You are a professional Instagram photographer with 500K followers. You know what makes photos POP on social media.

Analyze this photo and tell me:
1. What EMOTION does it evoke?
2. What POST-PROCESSING would make it viral-worthy?
3. What specific ADJUSTMENTS in Lightroom/VSCO would maximize engagement?

Be SPECIFIC with settings. Don't say "warm it up" - say "Add +300K color temp, increase orange saturation by 15".

Return ONLY this JSON structure:

{
  "composition_score": <1-10>,
  "vibe": "<one word: moody/bright/vintage/dramatic/etc>",
  "emotion": "<what feeling this should convey>",
  "instagram_appeal_score": <1-10>,
  "processing_recipe": {
    "primary_adjustment": "<the ONE most important change>",
    "color_work": "<specific color temp/tint/HSL changes>",
    "tone_curve": "<describe the curve: lifted shadows? crushed blacks?>",
    "effects": "<grain, vignette, clarity, texture values>",
    "final_look": "<describe the end result>"
  },
  "hashtag_suggestion": "<#aesthetic or #style that fits>"
}
"""

# =============================================================================
# Select which prompt to test (change this!)
# =============================================================================
ACTIVE_PROMPT = PROMPT_V2_PHOTOGRAPHY_EXPERT  # <-- CHANGE THIS TO TEST DIFFERENT PROMPTS

# =============================================================================
# Test Functions
# =============================================================================

def encode_image(image_path: Path) -> str:
    """Convert image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def test_critique(image_path: Path, model_name: str = "qwen2.5vl:3b"):
    """Test the active prompt against an image"""
    print(f"\n{'='*70}")
    print(f" 🧪 CRITIQUE PROMPT TESTER")
    print(f"{'='*70}")
    print(f" Image: {image_path.name}")
    print(f" Model: {model_name}")
    print(f" Active Prompt: {ACTIVE_PROMPT[:50]}...")
    print(f"{'='*70}\n")
    
    # Encode image
    print(" 📸 Encoding image...")
    base64_image = encode_image(image_path)
    
    # Build request
    payload = {
        "model": model_name,
        "messages": [{
            "role": "user",
            "content": ACTIVE_PROMPT,
            "images": [base64_image]
        }],
        "stream": False,
        "format": "json"
    }
    
    # Send to Ollama
    print(f" 🤖 Sending to {model_name}...")
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        
        result = response.json()
        json_string = result['message']['content'].strip()
        
        # Clean markdown fences if present
        if json_string.startswith("```json"):
            json_string = json_string.strip("```json\n")
        if json_string.endswith("```"):
            json_string = json_string.strip("```\n")
        
        # Parse and pretty print
        data = json.loads(json_string)
        
        print(f"\n{'='*70}")
        print(" ✅ SUCCESS - Model returned valid JSON")
        print(f"{'='*70}\n")
        print(json.dumps(data, indent=2))
        print(f"\n{'='*70}")
        
        # Save to file
        output_file = image_path.with_suffix('.critique_test.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f" 💾 Saved to: {output_file}")
        
        return data
        
    except requests.exceptions.Timeout:
        print(" ❌ TIMEOUT - Model took too long to respond")
        return None
    except json.JSONDecodeError as e:
        print(f" ❌ INVALID JSON - Model response couldn't be parsed")
        print(f"\n Raw response:\n{json_string}\n")
        return None
    except Exception as e:
        print(f" ❌ ERROR: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_critique_prompt.py <image_path> [model_name]")
        print("\nExample:")
        print("  python test_critique_prompt.py test.jpg")
        print("  python test_critique_prompt.py test.jpg minicpm-v2.6")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"❌ Error: Image not found: {image_path}")
        sys.exit(1)
    
    model_name = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5vl:3b"
    
    result = test_critique(image_path, model_name)
    
    if result:
        print("\n 🎯 PROMPT TEST SUCCESSFUL")
        print(" 💡 To use this prompt in PhotoSort, replace AI_CRITIC_PROMPT in photosort.py")
    else:
        print("\n 🔧 PROMPT TEST FAILED")
        print(" 💡 Try tweaking the prompt or using a different model")

if __name__ == "__main__":
    main()
