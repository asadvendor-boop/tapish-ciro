"""
Credibility scoring tool — called by Observer Agent.
Scores signal credibility based on specificity, emotional amplification, viral intent, source authority.
"""

import json


def score_credibility(
    text: str,
    follower_count: int,
    verified: bool,
    geo_hint: str,
) -> str:
    """Scores the credibility of a social media signal.
    Returns JSON with credibility_factors and overall credibility_score.
    
    Args:
        text: The raw text of the social media post
        follower_count: Number of followers of the poster
        verified: Whether the account is verified
        geo_hint: Geographic location hint from the post
    """
    try:
        factors = {}

        # Specificity: specific locations, numbers, details increase credibility
        specificity_markers = [
            "gate", "road", "hospital", "market", "mohalla", "gali",
            "block", "phase", "sector", "colony", "chowk",
        ]
        text_lower = text.lower()
        specificity_hits = sum(1 for m in specificity_markers if m in text_lower)
        has_numbers = any(c.isdigit() for c in text)
        factors["specificity_score"] = min(1.0, (specificity_hits * 0.2) + (0.2 if has_numbers else 0) + (0.2 if geo_hint else 0))

        # Emotional amplification: excessive punctuation, caps, emojis reduce credibility
        exclamation_count = text.count("!")
        caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        emoji_markers = ["🚨", "⚠️", "💀", "😱", "🔥", "❗"]
        emoji_count = sum(text.count(e) for e in emoji_markers)
        factors["emotional_amplification"] = min(1.0, (exclamation_count * 0.15) + (caps_ratio * 2) + (emoji_count * 0.2))

        # Viral intent: "share karo", "RT", "breaking", high follower count
        viral_phrases = ["share karo", "rt karo", "breaking", "viral", "jaldi", "share karein"]
        viral_hits = sum(1 for p in viral_phrases if p in text_lower)
        follower_viral = 1.0 if follower_count > 10000 else (0.5 if follower_count > 5000 else 0.0)
        factors["viral_intent_score"] = min(1.0, (viral_hits * 0.3) + (follower_viral * 0.3))

        # Source authority: verified accounts, known orgs, low-follower locals
        if verified:
            factors["source_authority"] = 0.85
        elif follower_count < 500:
            # Low-follower local accounts are often more credible (plan Section 8.1)
            factors["source_authority"] = 0.6
        elif follower_count < 2000:
            factors["source_authority"] = 0.5
        else:
            factors["source_authority"] = 0.3

        # Overall score: high specificity + low emotional + low viral + high authority = credible
        credibility = (
            factors["specificity_score"] * 0.35
            + (1.0 - factors["emotional_amplification"]) * 0.20
            + (1.0 - factors["viral_intent_score"]) * 0.20
            + factors["source_authority"] * 0.25
        )
        credibility = round(min(1.0, max(0.0, credibility)), 2)

        return json.dumps({
            "credibility_score": credibility,
            "credibility_factors": {k: round(v, 2) for k, v in factors.items()},
        })
    except Exception as e:
        return json.dumps({"error": "CREDIBILITY_SCORING_FAILURE", "details": str(e)})
