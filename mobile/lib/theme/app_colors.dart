import 'package:flutter/material.dart';

/// ─────────────────────────────────────────────────
/// GLASSMORPHISM 2026 — Design Tokens
/// ─────────────────────────────────────────────────

/// Agent color assignments — each agent gets a unique, vivid color
class AgentColors {
  static const observer = Color(0xFF42A5F5);   // Blue
  static const analyst = Color(0xFFEC407A);    // Pink
  static const strategist = Color(0xFFFFCA28); // Yellow
  static const operator_ = Color(0xFF66BB6A);  // Green
  static const auditor = Color(0xFFAB47BC);    // Purple

  static Color forAgent(String name) {
    switch (name.toLowerCase()) {
      case 'observer':
        return observer;
      case 'analyst':
        return analyst;
      case 'strategist':
        return strategist;
      case 'operator':
        return operator_;
      case 'auditor':
        return auditor;
      default:
        return Colors.grey;
    }
  }

  static IconData iconForAgent(String name) {
    switch (name.toLowerCase()) {
      case 'observer':
        return Icons.visibility;
      case 'analyst':
        return Icons.analytics;
      case 'strategist':
        return Icons.psychology;
      case 'operator':
        return Icons.send;
      case 'auditor':
        return Icons.verified;
      default:
        return Icons.smart_toy;
    }
  }
}

/// Severity color map
class SeverityColors {
  static const critical = Color(0xFFFF1744);
  static const high = Color(0xFFFF6D00);
  static const medium = Color(0xFFFFAB00);
  static const low = Color(0xFF00C853);

  static Color forSeverity(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'emergency':
        return critical;
      case 'high':
        return high;
      case 'medium':
      case 'moderate':
        return medium;
      case 'low':
        return low;
      default:
        return Colors.grey;
    }
  }
}

/// Main app colors — Glassmorphism 2026
class AppColors {
  // ── Core Palette ──
  static const heatOrange = Color(0xFFFF6D00);
  static const accentPurple = Color(0xFF7C3AED);
  static const coolCyan = Color(0xFF00E5FF);

  // ── Backgrounds ──
  static const deepBlack = Color(0xFF080810);
  static const surfaceDark = Color(0xFF0D0D18);
  static const surfaceCard = Color(0xFF12121E);
  static const surfaceElevated = Color(0xFF1A1A2E);

  // ── Glass effect colors ──
  static const glassFill = Color(0x0FFFFFFF);       // 6% white
  static const glassBorder = Color(0x1AFFFFFF);      // 10% white
  static const glassHighlight = Color(0x0DFFFFFF);   // 5% white

  // ── Ambient glow ──
  static const glowPurple = Color(0xFF7C3AED);
  static const glowOrange = Color(0xFFFF6D00);
  static const glowBlue = Color(0xFF3B82F6);

  // ── Text ──
  static const textPrimary = Color(0xFFF5F5F5);
  static const textSecondary = Color(0xFFBDBDBD);
  static const textMuted = Color(0xFF6B7280);

  // ── Status ──
  static const success = Color(0xFF00C853);
  static const warning = Color(0xFFFFAB00);
  static const error = Color(0xFFFF1744);
  static const info = Color(0xFF2196F3);
  static const live = Color(0xFF00E676);

  // ── Agent phase colors ──
  static const observerColor = Color(0xFF42A5F5);
  static const analystColor = Color(0xFFEC407A);
  static const predictorColor = Color(0xFF26C6DA);   // Cyan for Predictor
  static const strategistColor = Color(0xFFFFCA28);
  static const operatorColor = Color(0xFF66BB6A);
  static const auditorColor = Color(0xFFAB47BC);
}
