import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';
import 'alerts_screen.dart';
import 'stakeholder_screen.dart';
import 'impact_screen.dart';

/// "More" hub — groups secondary screens (Alerts, Stakeholders, Impact)
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowPurple,
        glowPosition: const Alignment(0, -0.5),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  children: [
                    const Text('⚙️ ', style: TextStyle(fontSize: 20)),
                    Text('مزید ', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                    const Text('More', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
                  ],
                ),
              ),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _navCard(
                      context,
                      icon: Icons.notifications_active,
                      color: AppColors.heatOrange,
                      titleUrdu: 'الرٹس',
                      titleEn: 'Crisis Alerts',
                      subtitle: 'Real-time crisis notifications & FCM alerts',
                      screen: const AlertsScreen(),
                    ),
                    const SizedBox(height: 12),
                    _navCard(
                      context,
                      icon: Icons.campaign,
                      color: AppColors.accentPurple,
                      titleUrdu: 'پیغامات',
                      titleEn: 'Stakeholder Messages',
                      subtitle: 'Notifications to hospitals, mosques & government',
                      screen: const StakeholderScreen(),
                    ),
                    const SizedBox(height: 12),
                    _navCard(
                      context,
                      icon: Icons.assessment,
                      color: AppColors.success,
                      titleUrdu: 'اثرات ڈیش بورڈ',
                      titleEn: 'Impact Dashboard',
                      subtitle: 'System metrics, agent performance & crisis stats',
                      screen: const ImpactScreen(),
                    ),
                    const SizedBox(height: 24),
                    // App info card
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.local_fire_department, color: AppColors.heatOrange, size: 20),
                              const SizedBox(width: 8),
                              Text('تپش', style: AppTheme.urduStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                              const SizedBox(width: 4),
                              const Text('TAPISH', style: TextStyle(fontSize: 12, color: AppColors.textMuted, letterSpacing: 3)),
                            ],
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Agentic Crisis Response for Lahore',
                            style: TextStyle(fontSize: 11, color: AppColors.textMuted),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Google ADK • Gemini 2.5 Flash • 5 Agents • 19 Tools',
                            style: TextStyle(fontSize: 9, color: AppColors.textMuted.withValues(alpha: 0.5)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              // Logout button
              const SizedBox(height: 16),
              GlassCard(
                onTap: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.remove('nigraan_session');
                  await prefs.remove('admin_jwt');
                  if (context.mounted) {
                    Navigator.of(context).pushNamedAndRemoveUntil('/', (_) => false);
                  }
                },
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                child: Row(
                  children: [
                    Icon(Icons.logout, color: AppColors.error, size: 22),
                    const SizedBox(width: 12),
                    Text('Logout — لاگ آؤٹ',
                      style: TextStyle(color: AppColors.error, fontSize: 14, fontWeight: FontWeight.w500)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _navCard(BuildContext context, {
    required IconData icon, required Color color, required String titleUrdu,
    required String titleEn, required String subtitle, required Widget screen,
  }) {
    return GlassCard(
      onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen)),
      borderColor: color.withValues(alpha: 0.2),
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: color.withValues(alpha: 0.2)),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(titleUrdu, style: AppTheme.urduStyle(fontSize: 15, fontWeight: FontWeight.w700)),
              const SizedBox(width: 6),
              Text(titleEn, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
            ]),
            const SizedBox(height: 4),
            Text(subtitle, style: const TextStyle(color: AppColors.textMuted, fontSize: 10)),
          ])),
          Icon(Icons.chevron_right, color: color.withValues(alpha: 0.5)),
        ],
      ),
    );
  }
}
