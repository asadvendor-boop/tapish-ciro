import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Full-screen detail view for a single crisis alert notification.
class AlertDetailScreen extends StatelessWidget {
  final Map<String, dynamic> alert;
  const AlertDetailScreen({super.key, required this.alert});

  Color _severityColor(String? severity) {
    switch (severity?.toLowerCase()) {
      case 'critical': return Colors.red;
      case 'high': return Colors.orange;
      case 'medium': return Colors.amber;
      default: return Colors.teal;
    }
  }

  @override
  Widget build(BuildContext context) {
    final severity = alert['data']?['severity'] as String?;
    final color = _severityColor(severity);
    final location = alert['data']?['location'] as String?;

    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      appBar: AppBar(
        backgroundColor: AppColors.surfaceCard,
        title: Text(
          'الرٹ تفصیل',
          style: AppTheme.urduStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Severity badge
            if (severity != null)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: color.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.warning_amber, color: color, size: 18),
                    const SizedBox(width: 6),
                    Text(
                      severity.toUpperCase(),
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: color,
                        letterSpacing: 1,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 20),

            // Title
            Text(
              alert['title'] ?? 'Crisis Alert',
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 16),

            // Location
            if (location != null) ...[
              Row(
                children: [
                  const Icon(Icons.location_on, color: AppColors.accentPurple, size: 18),
                  const SizedBox(width: 6),
                  Text(
                    location,
                    style: const TextStyle(
                      fontSize: 14,
                      color: AppColors.accentPurple,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],

            // Body
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.glassFill,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.glassBorder),
              ),
              child: Text(
                alert['body'] ?? 'No details available',
                style: const TextStyle(
                  fontSize: 15,
                  color: AppColors.textSecondary,
                  height: 1.6,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Timestamp
            if (alert['time'] != null)
              Row(
                children: [
                  Icon(Icons.access_time, size: 14,
                      color: AppColors.textMuted.withValues(alpha: 0.5)),
                  const SizedBox(width: 6),
                  Text(
                    _formatTimeFull(alert['time']),
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.textMuted.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),

            const SizedBox(height: 40),

            // Safety instructions
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.teal.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.teal.withValues(alpha: 0.2)),
              ),
              child: Column(
                children: [
                  Text(
                    'حفاظتی ہدایات',
                    style: AppTheme.urduStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.teal,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '• محفوظ مقام پر رہیں\n• ریسکیو 1122 سے رابطہ کریں\n• سرکاری ہدایات پر عمل کریں',
                    style: AppTheme.urduStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                    ),
                    textAlign: TextAlign.right,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Dismiss button
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: () => Navigator.of(context).pop(),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.teal.shade700,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  'Stay Safe 🙏 محفوظ رہیں',
                  style: AppTheme.urduStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimeFull(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year} ${dt.hour}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return '';
    }
  }
}
