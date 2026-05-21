"""
Vision Tool — Gemini 2.5 Flash multimodal image analysis for crisis assessment.
Accepts base64-encoded images and returns structured crisis assessment.
"""

import base64
import json
import os
from google.adk.tools import FunctionTool
from google import genai

def _detect_mime_type(b64_data: str) -> str:
    """Sniff mime type from base64 header bytes."""
    try:
        header = base64.b64decode(b64_data[:32])
        if header[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        if header[:4] == b'\x00\x00\x00\x18' or header[:4] == b'\x00\x00\x00\x1c' or header[4:8] == b'ftyp':
            return "video/mp4"
    except Exception:
        pass
    return "image/jpeg"  # safe default


def analyze_crisis_image(image_base64: str, context: str = "") -> dict:
    """Analyze a crisis scene image using Gemini Vision.

    Args:
        image_base64: Base64-encoded image data (JPEG/PNG).
        context: Optional text context from the reporter.

    Returns:
        dict with keys: crisis_detected (bool), crisis_type, severity,
        description, people_visible (int), damage_level, recommended_action.
    """
    mime = _detect_mime_type(image_base64)
    return analyze_crisis_media(image_base64, context, mime_type=mime)


def analyze_crisis_media(media_base64: str, context: str = "", mime_type: str = "image/jpeg") -> dict:
    """Analyze crisis scene media (image or video) using Gemini multimodal.

    Args:
        media_base64: Base64-encoded media data.
        context: Optional text context from the reporter.
        mime_type: MIME type of the media (image/jpeg, image/png, video/mp4).

    Returns:
        dict with crisis assessment fields.
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        media_label = "video clip" if mime_type.startswith("video") else "photo"
        prompt = f"""You are an emergency crisis analyst examining a field {media_label} from Lahore, Pakistan.
Analyze this {media_label} for any crisis or emergency situation.

{f'Reporter context: {context}' if context else ''}

Respond ONLY with valid JSON (no markdown):
{{
  "crisis_detected": true/false,
  "crisis_type": "heatwave|flood|power_outage|accident|infrastructure|fire|medical_emergency|none",
  "severity": "critical|high|medium|low|none",
  "description": "Brief description of what you see",
  "people_visible": 0,
  "injuries_visible": true/false,
  "damage_level": "severe|moderate|minor|none",
  "environmental_hazards": ["list of hazards"],
  "recommended_action": "Brief recommended response"
}}"""

        media_bytes = base64.b64decode(media_base64)
        media_part = genai.types.Part.from_bytes(data=media_bytes, mime_type=mime_type)

        # Retry on transient Gemini errors (429/503)
        import time as _time
        from app.services import degraded_mode
        response = None
        for attempt in range(3):
            try:
                # Degraded mode: simulate a 429 on the first attempt
                if attempt == 0 and degraded_mode.should_simulate_rate_limit():
                    raise Exception("Simulated 429 RESOURCE_EXHAUSTED (degraded mode test)")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, media_part],
                )
                break
            except Exception as retry_err:
                err_str = str(retry_err).lower()
                if attempt < 2 and ("429" in err_str or "503" in err_str or "resource exhausted" in err_str):
                    _time.sleep((attempt + 1) * 2)
                    continue
                raise

        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)

        # Normalize keys — LLM may return slight variations
        EXPECTED_KEYS = {
            "crisis_detected": False, "crisis_type": "none", "severity": "none",
            "description": "", "people_visible": 0, "injuries_visible": False,
            "damage_level": "none", "environmental_hazards": [],
            "recommended_action": "",
        }
        # Handle common LLM key variations
        if "type" in result and "crisis_type" not in result:
            result["crisis_type"] = result.pop("type")
        if "action" in result and "recommended_action" not in result:
            result["recommended_action"] = result.pop("action")

        # Fill missing keys with defaults
        for key, default in EXPECTED_KEYS.items():
            result.setdefault(key, default)

        return result

    except Exception as e:
        return {
            "crisis_detected": False,
            "crisis_type": "none",
            "severity": "none",
            "description": f"Media analysis failed: {str(e)}",
            "people_visible": 0,
            "injuries_visible": False,
            "damage_level": "none",
            "environmental_hazards": [],
            "recommended_action": "Manual review required",
        }


vision_tool = FunctionTool(func=analyze_crisis_image)
