import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/data_mode_provider.dart';
import 'app_colors.dart';

/// Reusable frosted glass card — the core building block of Glassmorphism 2026.
class GlassCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final double borderRadius;
  final Color? borderColor;
  final Color? fillColor;
  final double blurSigma;
  final VoidCallback? onTap;
  final List<BoxShadow>? glow;

  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.borderRadius = 16,
    this.borderColor,
    this.fillColor,
    this.blurSigma = 20,
    this.onTap,
    this.glow,
  });

  @override
  Widget build(BuildContext context) {
    final card = ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: Container(
          padding: padding ?? const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: fillColor ?? AppColors.glassFill,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(
              color: borderColor ?? AppColors.glassBorder,
              width: 1,
            ),
            boxShadow: glow,
          ),
          child: child,
        ),
      ),
    );

    final wrapped = margin != null
        ? Padding(padding: margin!, child: card)
        : card;

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: wrapped);
    }
    return wrapped;
  }
}

/// Glass card with a colored left accent border (for trace logs, alerts)
class GlassAccentCard extends StatelessWidget {
  final Widget child;
  final Color accentColor;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;

  const GlassAccentCard({
    super.key,
    required this.child,
    required this.accentColor,
    this.padding,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin ?? const EdgeInsets.only(bottom: 10),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
          child: Container(
            padding: padding ?? const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.glassFill,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.glassBorder),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 3,
                  height: 50,
                  decoration: BoxDecoration(
                    color: accentColor,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(child: child),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Ambient glow background — wraps screens with purple/blue glow
class AmbientGlowBackground extends StatelessWidget {
  final Widget child;
  final Color glowColor;
  final Alignment glowPosition;

  const AmbientGlowBackground({
    super.key,
    required this.child,
    this.glowColor = AppColors.glowPurple,
    this.glowPosition = Alignment.topRight,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.deepBlack,
        gradient: RadialGradient(
          center: glowPosition,
          radius: 1.2,
          colors: [
            glowColor.withValues(alpha: 0.08),
            AppColors.deepBlack,
          ],
        ),
      ),
      child: child,
    );
  }
}

/// LIVE/DEMO badge widget — tappable toggle synced with backend
class LiveBadge extends StatelessWidget {
  const LiveBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<DataModeProvider>(
      builder: (context, dm, _) {
        final isLive = dm.isLive;
        final color = isLive ? AppColors.live : const Color(0xFF00B8D4);
        final label = isLive ? 'LIVE' : 'DEMO';

        return GestureDetector(
          onTap: dm.isLoading ? null : () => dm.toggle(),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: color.withValues(alpha: 0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (dm.isLoading)
                  SizedBox(width: 8, height: 8,
                    child: CircularProgressIndicator(strokeWidth: 1.5, color: color))
                else
                  Container(
                    width: 6, height: 6,
                    decoration: BoxDecoration(color: color, shape: BoxShape.circle),
                  ),
                const SizedBox(width: 5),
                Text(label,
                  style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w700, letterSpacing: 1)),
              ],
            ),
          ),
        );
      },
    );
  }
}
