import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../providers/alerts_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});
  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  String _filter = 'all';

  @override
  void initState() { super.initState(); Future.microtask(() { if (mounted) context.read<AlertsProvider>().fetchCrises(); }); }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowOrange,
        glowPosition: const Alignment(0.5, -0.5),
        child: SafeArea(child: Column(children: [
          // App bar
          Padding(padding: const EdgeInsets.fromLTRB(20, 16, 20, 8), child: Row(children: [
            const Icon(Icons.notifications_active, color: AppColors.heatOrange, size: 24),
            const SizedBox(width: 10),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('الرٹس', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const Text('Crisis Alerts', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
            ]),
            const Spacer(),
            Consumer<AlertsProvider>(builder: (_, p, __) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: AppColors.heatOrange.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
              child: Text('${p.count}', style: const TextStyle(color: AppColors.heatOrange, fontWeight: FontWeight.w700, fontSize: 14)),
            )),
          ])),
          // Filter chips
          SizedBox(height: 36, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16),
            children: [_fChip('All', 'all'), const SizedBox(width: 8), _fChip('Critical', 'critical'), const SizedBox(width: 8), _fChip('Active', 'active'), const SizedBox(width: 8), _fChip('Resolved', 'resolved')])),
          const SizedBox(height: 8),
          // Alerts list
          Expanded(child: Consumer<AlertsProvider>(builder: (ctx, p, _) {
            if (p.isLoading && p.alerts.isEmpty) return const Center(child: CircularProgressIndicator(color: AppColors.accentPurple));
            if (p.alerts.isEmpty) return _empty();
            final filtered = _applyFilter(p.alerts);
            return RefreshIndicator(color: AppColors.accentPurple, onRefresh: p.fetchCrises,
              child: ListView.builder(padding: const EdgeInsets.fromLTRB(16, 0, 16, 100), itemCount: filtered.length,
                itemBuilder: (_, i) => _AlertCard(alert: filtered[i])));
          })),
        ])),
      ),
    );
  }

  List<Map<String, dynamic>> _applyFilter(List<Map<String, dynamic>> alerts) {
    if (_filter == 'all') return alerts;
    return alerts.where((a) {
      final crisis = a['crisis'] as Map<String, dynamic>? ?? {};
      final sev = crisis['severity']?.toString() ?? '';
      final status = crisis['status']?.toString() ?? '';
      final event = a['event']?.toString() ?? '';
      if (_filter == 'critical') return sev == 'critical';
      if (_filter == 'active') return event != 'crisis_retracted' && status != 'resolved';
      if (_filter == 'resolved') return event == 'crisis_retracted' || status == 'resolved';
      return true;
    }).toList();
  }

  Widget _fChip(String label, String value) {
    final sel = _filter == value;
    return GestureDetector(onTap: () => setState(() => _filter = value),
      child: Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(color: sel ? AppColors.accentPurple.withValues(alpha: 0.2) : AppColors.glassFill,
          borderRadius: BorderRadius.circular(20), border: Border.all(color: sel ? AppColors.accentPurple : AppColors.glassBorder)),
        child: Text(label, style: TextStyle(fontSize: 12, fontWeight: sel ? FontWeight.w600 : FontWeight.w400,
          color: sel ? AppColors.accentPurple : AppColors.textSecondary))));
  }

  Widget _empty() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
    Icon(Icons.shield_outlined, size: 64, color: AppColors.textMuted.withValues(alpha: 0.2)),
    const SizedBox(height: 16),
    Text('کوئی الرٹ نہیں', style: AppTheme.urduStyle(fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
    const SizedBox(height: 4), const Text('No active alerts', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
  ]));
}

class _AlertCard extends StatefulWidget {
  final Map<String, dynamic> alert;
  const _AlertCard({required this.alert});
  @override
  State<_AlertCard> createState() => _AlertCardState();
}

class _AlertCardState extends State<_AlertCard> {
  bool _expanded = false;

  @override
  void initState() { super.initState(); HapticFeedback.mediumImpact(); }

  @override
  Widget build(BuildContext context) {
    final a = widget.alert;
    final event = a['event']?.toString() ?? '';
    final isRet = event == 'crisis_retracted';
    final crisis = a['crisis'] as Map<String, dynamic>? ?? {};
    final type = isRet ? 'Retracted Alert' : crisis['type']?.toString() ?? 'Unknown';
    final sev = isRet ? 'retracted' : crisis['severity']?.toString() ?? 'medium';
    final loc = isRet ? a['crisis_id']?.toString() ?? '' : crisis['primary_location']?.toString() ?? '';
    final conf = isRet ? 0.0 : (crisis['confidence'] ?? a['confidence'] ?? 0).toDouble();
    final ts = a['timestamp']?.toString() ?? '';
    final sevColor = isRet ? Colors.grey : SeverityColors.forSeverity(sev);
    String time = '';
    try { var d = DateTime.parse(ts).toUtc().add(const Duration(hours: 5)); time = DateFormat('hh:mm a').format(d); } catch (_) { time = ts; }
    final typeMap = {'heatwave':'🔥 شدید گرمی','power_outage':'⚡ بجلی بند','flood':'🌊 سیلاب','accident':'🚨 حادثہ'};
    final headline = isRet ? '↩️ Alert Retracted' : (typeMap[type.toLowerCase()] ?? '⚠️ $type');
    final status = crisis['status']?.toString() ?? 'detected';
    final needsVerification = !isRet && (status == 'investigate' || (status == 'detected' && conf < 0.5));

    return Padding(padding: const EdgeInsets.only(bottom: 10), child: GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: ClipRRect(borderRadius: BorderRadius.circular(14),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.glassFill,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.glassBorder),
          ),
          child: IntrinsicHeight(child: Row(children: [
            // Severity strip
            Container(width: 4, decoration: BoxDecoration(color: sevColor,
              borderRadius: const BorderRadius.only(topLeft: Radius.circular(14), bottomLeft: Radius.circular(14)))),
            Expanded(child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: sevColor.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(6)),
                  child: Text(isRet ? 'RETRACTED' : sev.toUpperCase(), style: TextStyle(color: sevColor, fontSize: 10, fontWeight: FontWeight.w700))),
                const Spacer(),
                Text(time, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
              ]),
              // Investigation banner
              if (needsVerification) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                  ),
                  child: Row(children: [
                    Icon(Icons.hourglass_empty, size: 14, color: Colors.amber.shade600),
                    const SizedBox(width: 6),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('⏳ Awaiting Nigraan Verification — ${(conf * 100).toInt()}%',
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.amber.shade600)),
                      Text('نگران تصدیق باقی', style: AppTheme.urduStyle(fontSize: 10, color: Colors.amber.shade400)),
                    ])),
                  ]),
                ),
              ],
              const SizedBox(height: 10),
              Text('$headline — $loc', style: AppTheme.urduStyle(fontSize: 15, fontWeight: FontWeight.w600,
                color: isRet ? AppColors.textMuted : AppColors.textPrimary)),
              const SizedBox(height: 6),
              Row(children: [
                const Icon(Icons.location_on, size: 14, color: AppColors.textMuted), const SizedBox(width: 4),
                Expanded(child: Text(loc.isNotEmpty ? loc : 'Unknown', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))),
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: AppColors.glassFill, borderRadius: BorderRadius.circular(4), border: Border.all(color: AppColors.glassBorder)),
                  child: Text('${(conf*100).toInt()}%', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: AppColors.textSecondary))),
              ]),
              if (isRet && a['retraction_message'] != null) ...[const SizedBox(height: 8),
                GlassCard(fillColor: AppColors.error.withValues(alpha: 0.06), borderColor: AppColors.error.withValues(alpha: 0.2), padding: const EdgeInsets.all(8),
                  child: Row(children: [const Icon(Icons.cancel, size: 14, color: AppColors.error), const SizedBox(width: 6),
                    Expanded(child: Text(a['retraction_message'].toString(), style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)))]))],
              if (_expanded) ...[const SizedBox(height: 10),
                GlassCard(padding: const EdgeInsets.all(10), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [const Icon(Icons.smart_toy, size: 14, color: AppColors.accentPurple), const SizedBox(width: 6),
                    const Text('Agent Trace', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.accentPurple))]),
                  const SizedBox(height: 6),
                  if (!isRet) ...[_tr('Observer','👁 OBSERVE','Credibility: ${(conf*100).toInt()}%'), _tr('Analyst','🧠 REASON','Severity: ${sev.toUpperCase()}'),
                    _tr('Strategist','⚖️ DECIDE','Resource allocation'), _tr('Operator','⚡ ACT','Dispatch executed'), _tr('Auditor','✅ EVALUATE','Verification')]
                  else ...[_tr('Auditor','✅ EVALUATE','RETRACT — false alarm')],
                ]))],
              Center(child: Icon(_expanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down, size: 16, color: AppColors.textMuted)),
            ])))
          ])),
        ),
      ),
    ));
  }

  Widget _tr(String agent, String phase, String detail) {
    final c = AgentColors.forAgent(agent.toLowerCase());
    return Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(children: [
      SizedBox(width: 65, child: Text(agent, style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: c))),
      Container(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(3)),
        child: Text(phase, style: TextStyle(fontSize: 8, fontWeight: FontWeight.w700, color: c))),
      const SizedBox(width: 6),
      Expanded(child: Text(detail, style: const TextStyle(fontSize: 10, color: AppColors.textMuted))),
    ]));
  }
}
