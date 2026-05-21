import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';
import 'alert_detail_screen.dart';

/// Alerts inbox for Tapish Awaaz — fetches from server + local FCM cache.
class AlertsInboxScreen extends StatefulWidget {
  const AlertsInboxScreen({super.key});

  @override
  State<AlertsInboxScreen> createState() => AlertsInboxScreenState();
}

class AlertsInboxScreenState extends State<AlertsInboxScreen> {
  List<Map<String, dynamic>> _alerts = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadAlerts();
  }

  /// Public reload method — called by parent when tab becomes visible
  void reload() => _loadAlerts();

  Future<void> _loadAlerts() async {
    final List<Map<String, dynamic>> combined = [];

    // 1. Fetch from backend (citizen-facing stakeholder messages)
    try {
      final resp = await ApiService.get('/api/stakeholder/messages');
      final messages = (resp['messages'] as List?) ?? [];
      for (final m in messages) {
        final audience = (m['audience'] ?? '').toString().toLowerCase();
        // Only show citizen/public alerts
        if (audience == 'citizens' || audience == 'public') {
          combined.add({
            'title': m['title'] ?? 'Crisis Alert',
            'body': m['body'] ?? m['content'] ?? '',
            'time': m['timestamp'] ?? m['created_at'] ?? '',
            'data': {'severity': m['severity'] ?? 'medium', 'source': 'server'},
          });
        }
      }
    } catch (_) {
      // Server unreachable — use local cache only
    }

    // 2. Load local FCM notifications
    try {
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getStringList('alerts') ?? [];
      for (final s in raw) {
        try {
          final m = jsonDecode(s) as Map<String, dynamic>;
          if (m.isNotEmpty) combined.add(m);
        } catch (_) {}
      }
    } catch (_) {}

    // 3. Deduplicate by title+body, sort by time (newest first)
    final seen = <String>{};
    final unique = <Map<String, dynamic>>[];
    for (final a in combined) {
      final key = '${a['title']}|${a['body']}';
      if (seen.add(key)) unique.add(a);
    }
    unique.sort((a, b) => (b['time'] ?? '').compareTo(a['time'] ?? ''));

    if (mounted) {
      setState(() {
        _alerts = unique;
        _loading = false;
      });
    }
  }

  Color _severityColor(String? severity) {
    switch (severity?.toLowerCase()) {
      case 'critical': return Colors.red;
      case 'high': return Colors.orange;
      case 'medium': return Colors.amber;
      default: return Colors.teal;
    }
  }

  String _formatTime(String? iso) {
    if (iso == null) return '';
    try {
      final dt = DateTime.parse(iso);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inMinutes < 1) return 'ابھی';
      if (diff.inMinutes < 60) return '${diff.inMinutes} منٹ پہلے';
      if (diff.inHours < 24) return '${diff.inHours} گھنٹے پہلے';
      return '${diff.inDays} دن پہلے';
    } catch (_) {
      return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: _loadAlerts,
                child: _alerts.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      SizedBox(height: MediaQuery.of(context).size.height * 0.3),
                      Center(child: Icon(Icons.notifications_none,
                          size: 64, color: AppColors.textMuted.withValues(alpha: 0.3))),
                      const SizedBox(height: 16),
                      Center(child: Text(
                        'کوئی الرٹ نہیں',
                        style: AppTheme.urduStyle(fontSize: 18, color: AppColors.textMuted),
                      )),
                      const SizedBox(height: 8),
                      Center(child: Text(
                        'بحران کے الرٹس یہاں نظر آئیں گے',
                        style: AppTheme.urduStyle(fontSize: 13, color: AppColors.textMuted.withValues(alpha: 0.5)),
                      )),
                    ],
                  )
                : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: _alerts.length + 1, // +1 for header
                      itemBuilder: (context, index) {
                        if (index == 0) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: Row(
                              children: [
                                const Icon(Icons.notifications_active,
                                    color: AppColors.accentPurple, size: 22),
                                const SizedBox(width: 8),
                                Text(
                                  'بحران الرٹس',
                                  style: AppTheme.urduStyle(
                                    fontSize: 20,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                                const Spacer(),
                                Text(
                                  '${_alerts.length}',
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: AppColors.textMuted.withValues(alpha: 0.5),
                                  ),
                                ),
                              ],
                            ),
                          );
                        }

                        final alert = _alerts[index - 1];
                        final severity = alert['data']?['severity'] as String?;
                        final color = _severityColor(severity);

                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: GlassCard(
                            onTap: () {
                              Navigator.of(context).push(
                                MaterialPageRoute(
                                  builder: (_) => AlertDetailScreen(alert: alert),
                                ),
                              );
                            },
                            padding: const EdgeInsets.all(14),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  width: 4,
                                  height: 48,
                                  decoration: BoxDecoration(
                                    color: color,
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          if (severity != null) ...[
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                  horizontal: 6, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: color.withValues(alpha: 0.2),
                                                borderRadius: BorderRadius.circular(4),
                                              ),
                                              child: Text(
                                                severity.toUpperCase(),
                                                style: TextStyle(
                                                  fontSize: 9,
                                                  fontWeight: FontWeight.w700,
                                                  color: color,
                                                ),
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                          ],
                                          Expanded(
                                            child: Text(
                                              alert['title'] ?? 'Alert',
                                              style: const TextStyle(
                                                fontSize: 14,
                                                fontWeight: FontWeight.w600,
                                                color: AppColors.textPrimary,
                                              ),
                                              maxLines: 1,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        alert['body'] ?? '',
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: AppColors.textMuted.withValues(alpha: 0.7),
                                        ),
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        _formatTime(alert['time']),
                                        style: TextStyle(
                                          fontSize: 10,
                                          color: AppColors.textMuted.withValues(alpha: 0.4),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right,
                                    color: AppColors.textMuted, size: 20),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
      ),
    );
  }
}
