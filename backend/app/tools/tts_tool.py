"""
Google Cloud TTS tool — generates REAL Urdu audio announcements.
Called by Operator Agent for mosque loudspeaker announcements.
"""

import json
import uuid
import os
from pathlib import Path


TTS_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "tts_output"
TTS_OUTPUT_DIR.mkdir(exist_ok=True)

_tts_client = None
_tts_mock_mode = False


def _init_tts():
    """Initialize Google Cloud TTS client (lazy)."""
    global _tts_client, _tts_mock_mode
    if _tts_client is not None or _tts_mock_mode:
        return
    try:
        from google.cloud import texttospeech
        
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
        if cred_path and Path(cred_path).exists():
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", cred_path)
        
        _tts_client = texttospeech.TextToSpeechClient()
    except Exception as e:
        print(f"[TTS] Init error: {e}. Using mock mode.")
        _tts_mock_mode = True


def generate_urdu_tts(text: str, voice_name: str = "ur-IN-Wavenet-A") -> str:
    """Generate Urdu audio from text using Google Cloud Text-to-Speech.
    Returns URL to the generated audio file.
    
    Args:
        text: Urdu text to convert to speech
        voice_name: Google TTS voice name (default: ur-IN-Wavenet-A for high-quality female Urdu voice)
    """
    _init_tts()
    
    try:
        file_id = uuid.uuid4().hex[:8]
        filename = f"tts_{file_id}.mp3"
        filepath = TTS_OUTPUT_DIR / filename
        
        if _tts_client is not None and not _tts_mock_mode:
            from google.cloud import texttospeech
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="ur-IN",
                name=voice_name,
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.9,  # Slightly slower for clarity
                pitch=0.0,
            )
            
            response = _tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            
            with open(filepath, "wb") as f:
                f.write(response.audio_content)
            
            audio_url = f"/tts/{filename}"
            return json.dumps({
                "status": "generated",
                "audio_url": audio_url,
                "filename": filename,
                "voice": voice_name,
                "text_length": len(text),
            })
        else:
            # Mock mode — return null audio URL instead of fake bytes
            audio_url = None
            return json.dumps({
                "status": "mock_generated",
                "audio_url": audio_url,
                "filename": filename,
                "note": "TTS client not available. No audio file created.",
            })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "note": "TTS generation failed."})
