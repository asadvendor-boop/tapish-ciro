"""
Speech Tool — Gemini multimodal audio transcription for Urdu voice reports.
Accepts base64-encoded audio and returns Urdu transcription with crisis analysis.
"""

import base64
import json
import os
from google.adk.tools import FunctionTool
from google import genai


def transcribe_urdu_audio(audio_base64: str) -> dict:
    """Transcribe Urdu audio using Gemini multimodal.

    Uses Gemini's native audio understanding instead of a separate STT API,
    keeping the stack unified on Gemini.

    Args:
        audio_base64: Base64-encoded audio data (WAV/M4A/OGG).

    Returns:
        dict with keys: transcription (str), language (str),
        confidence (float), crisis_keywords (list).
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

        prompt = """You are transcribing an emergency voice report from Lahore, Pakistan.
The audio is likely in Urdu, Roman Urdu, or Punjabi.

Transcribe the audio and analyze it for crisis-related content.

Respond ONLY with valid JSON (no markdown):
{
  "transcription": "Full transcription in original language",
  "transcription_english": "English translation",
  "language": "urdu|roman_urdu|punjabi|english",
  "confidence": 0.0 to 1.0,
  "crisis_keywords": ["list", "of", "crisis", "related", "words"],
  "urgency": "critical|high|medium|low",
  "summary": "One-line English summary of what the person is reporting"
}"""

        audio_bytes = base64.b64decode(audio_base64)
        # Detect audio format: M4A (AAC) from iOS, OGG from Android, WAV fallback
        mime = "audio/wav"
        if audio_bytes[:4] == b'\x00\x00\x00\x18' or audio_bytes[4:8] == b'ftyp':
            mime = "audio/mp4"  # M4A/AAC
        elif audio_bytes[:4] == b'OggS':
            mime = "audio/ogg"
        audio_part = genai.types.Part.from_bytes(data=audio_bytes, mime_type=mime)

        # Retry on transient Gemini errors (429/503)
        import time as _time
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt, audio_part],
                )
                break
            except Exception as retry_err:
                err_str = str(retry_err).lower()
                if attempt < 2 and ("429" in err_str or "503" in err_str or "resource exhausted" in err_str):
                    _time.sleep((attempt + 1) * 2)
                    continue
                raise

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        return json.loads(text)

    except Exception as e:
        return {
            "transcription": "",
            "transcription_english": "",
            "language": "unknown",
            "confidence": 0.0,
            "crisis_keywords": [],
            "urgency": "low",
            "summary": f"Audio transcription failed: {str(e)}",
        }


speech_tool = FunctionTool(func=transcribe_urdu_audio)
