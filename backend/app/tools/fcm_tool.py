"""
FCM push notification tool — sends REAL Firebase Cloud Messaging notifications.
Called by Operator Agent.
"""

import json
import os
from pathlib import Path

_firebase_initialized = False


def _init_firebase():
    """Initialize Firebase Admin SDK (lazy, once)."""
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials

        # If database.py already initialized Firebase, reuse it
        if firebase_admin._apps:
            _firebase_initialized = True
            return
        
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
        if not cred_path or not Path(cred_path).exists():
            # Try relative path from backend dir
            backend_dir = Path(__file__).resolve().parent.parent.parent
            for f in backend_dir.parent.parent.glob("tapish-crisis-firebase-adminsdk*.json"):
                cred_path = str(f)
                break
        
        if cred_path and Path(cred_path).exists():
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
        else:
            print(f"[FCM] Warning: Firebase credentials not found. FCM will use mock mode.")
    except Exception as e:
        print(f"[FCM] Firebase init error: {e}. Using mock mode.")


def send_fcm_notification(
    title: str,
    body: str,
    topic: str,
    crisis_id: str,
    severity: str,
) -> str:
    """Send a Firebase Cloud Messaging push notification to subscribed devices.
    
    Args:
        title: Notification title (e.g. '🔴 Heat Emergency - Walled City')
        body: Notification body text
        topic: FCM topic to send to (e.g. 'crisis_alerts', 'rescue_1122', 'public')
        crisis_id: Related crisis event ID
        severity: Alert severity level ('info', 'advisory', 'urgent', 'emergency')
    """
    _init_firebase()
    
    try:
        if _firebase_initialized:
            from firebase_admin import messaging
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    "crisis_id": crisis_id,
                    "severity": severity,
                    "type": "crisis_alert",
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                },
                topic=topic,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        icon="ic_alert",
                        color="#FF1744",
                        sound="default",
                        channel_id="crisis_alerts",
                    ),
                ),
            )
            response = messaging.send(message)
            return json.dumps({
                "status": "sent",
                "message_id": response,
                "topic": topic,
                "title": title,
            })
        else:
            # Mock mode
            return json.dumps({
                "status": "mock_sent",
                "topic": topic,
                "title": title,
                "body": body,
                "note": "Firebase not initialized. Notification simulated.",
            })
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "note": "FCM send failed. Alert logged but not delivered."})
