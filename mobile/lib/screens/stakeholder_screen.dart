import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class StakeholderScreen extends StatefulWidget {
  const StakeholderScreen({super.key});
  @override
  State<StakeholderScreen> createState() => _StakeholderScreenState();
}

class _StakeholderScreenState extends State<StakeholderScreen> with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  List<dynamic> _msgs = [];
  bool _loading = true;
  String? _error;

  static const _audiences = [
    {'key':'all','label':'سب','icon':Icons.groups,'subtitle':'All','color':AppColors.accentPurple},
    {'key':'citizen','label':'عوام','icon':Icons.people,'subtitle':'Public','color':AppColors.info},
    {'key':'rescue_1122','label':'ریسکیو','icon':Icons.local_hospital,'subtitle':'Rescue','color':AppColors.error},
    {'key':'government','label':'حکومت','icon':Icons.account_balance,'subtitle':'Govt','color':AppColors.accentPurple},
    {'key':'hospital','label':'ہسپتال','icon':Icons.medical_services,'subtitle':'Hospital','color':AppColors.success},
    {'key':'mosque','label':'مسجد','icon':Icons.mosque,'subtitle':'Mosque','color':AppColors.warning},
    {'key':'lesco','label':'لیسکو','icon':Icons.bolt,'subtitle':'LESCO','color':AppColors.heatOrange},
  ];

  @override
  void initState() { super.initState(); _tabCtrl = TabController(length: _audiences.length, vsync: this); _load(); }
  @override
  void dispose() { _tabCtrl.dispose(); super.dispose(); }

  Future<void> _load() async {
    try { final m = await ApiService.getStakeholderMessages(); if (mounted) setState(() { _msgs = m; _loading = false; _error = null; }); }
    catch (e) { if (mounted) setState(() { _loading = false; _error = e.toString(); }); }
  }

  List<dynamic> _filtered(String aud) => aud == 'all' ? _msgs : _msgs.where((m) => (m['audience'] ?? '').toString().toLowerCase().contains(aud.toLowerCase())).toList();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowPurple,
        glowPosition: const Alignment(-0.7, -0.3),
        child: SafeArea(child: Column(children: [
          Padding(padding: const EdgeInsets.fromLTRB(20, 16, 20, 8), child: Row(children: [
            const Icon(Icons.campaign, color: AppColors.accentPurple, size: 24),
            const SizedBox(width: 10),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('پیغامات', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const Text('Stakeholder Messages', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
            ]),
            const Spacer(),
            IconButton(icon: const Icon(Icons.refresh, size: 20, color: AppColors.textMuted), onPressed: () { setState(() => _loading = true); _load(); }),
          ])),
          // Tabs
          SizedBox(height: 40, child: TabBar(controller: _tabCtrl, isScrollable: true, tabAlignment: TabAlignment.start,
            indicatorColor: AppColors.accentPurple, indicatorSize: TabBarIndicatorSize.label,
            labelColor: AppColors.accentPurple, unselectedLabelColor: AppColors.textMuted,
            labelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
            dividerColor: Colors.transparent,
            tabs: _audiences.map((a) => Tab(child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon(a['icon'] as IconData, size: 16), const SizedBox(width: 4), Text(a['subtitle'] as String)]))).toList())),
          const SizedBox(height: 8),
          Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator(color: AppColors.accentPurple))
            : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: AppColors.error)))
              : TabBarView(controller: _tabCtrl, children: _audiences.map((a) {
                  final f = _filtered(a['key'] as String);
                  if (f.isEmpty) { return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.inbox_outlined, size: 48, color: AppColors.textMuted.withValues(alpha: 0.3)),
                    const SizedBox(height: 12), Text('No ${a['subtitle']} messages yet', style: const TextStyle(color: AppColors.textMuted, fontSize: 14))])); }
                  return RefreshIndicator(onRefresh: _load, color: AppColors.accentPurple,
                    child: ListView.builder(padding: const EdgeInsets.all(16), itemCount: f.length,
                      itemBuilder: (_, i) => _MsgCard(message: f[i], groupColor: a['color'] as Color)));
                }).toList())),
        ])),
      ),
    );
  }
}

class _MsgCard extends StatelessWidget {
  final dynamic message;
  final Color groupColor;
  const _MsgCard({required this.message, required this.groupColor});

  @override
  Widget build(BuildContext context) {
    final aud = (message['audience'] ?? 'unknown').toString();
    final chan = (message['channel'] ?? '').toString();
    final lang = (message['language'] ?? '').toString();
    final content = (message['content'] ?? '').toString();
    final urgency = (message['urgency'] ?? 'info').toString();
    final urgColor = _uColor(urgency);

    return Padding(padding: const EdgeInsets.only(bottom: 12), child: ClipRRect(
      borderRadius: BorderRadius.circular(14),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.glassFill,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: groupColor.withValues(alpha: 0.3)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(color: groupColor.withValues(alpha: 0.08),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(14))),
            child: Row(children: [
              Icon(_audIcon(aud), color: groupColor, size: 18),
              const SizedBox(width: 8),
              Text(aud.toUpperCase().replaceAll('_', ' '),
                style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: groupColor, letterSpacing: 0.5)),
              const Spacer(),
              Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(color: urgColor.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(4)),
                child: Text(urgency.toUpperCase(), style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: urgColor))),
              if (chan.isNotEmpty) ...[const SizedBox(width: 6),
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: AppColors.glassFill, borderRadius: BorderRadius.circular(4), border: Border.all(color: AppColors.glassBorder)),
                  child: Text(chan == 'loudspeaker_tts' ? '🕌 TTS' : '📱 Push',
                    style: const TextStyle(fontSize: 9, color: AppColors.textMuted)))],
            ]),
          ),
          // Content
          Padding(padding: const EdgeInsets.all(14),
            child: Text(content, style: TextStyle(fontSize: aud == 'mosque' ? 16 : 13,
              color: AppColors.textSecondary, height: 1.5,
              fontWeight: aud == 'mosque' ? FontWeight.w600 : FontWeight.normal))),
          // Footer
          Padding(padding: const EdgeInsets.only(left: 14, right: 14, bottom: 10), child: Row(children: [
            if (lang.isNotEmpty) Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: AppColors.glassFill, borderRadius: BorderRadius.circular(4), border: Border.all(color: AppColors.glassBorder)),
              child: Text(lang.toUpperCase(), style: const TextStyle(fontSize: 9, color: AppColors.textMuted))),
            const Spacer(),
            Text('Delivered ✅', style: TextStyle(fontSize: 9, color: AppColors.success.withValues(alpha: 0.7))),
          ])),
        ]),
      ),
    ));
  }

  Color _uColor(String u) { switch (u.toLowerCase()) { case 'emergency': return AppColors.error; case 'urgent': return AppColors.heatOrange; case 'advisory': return AppColors.warning; default: return AppColors.info; } }
  IconData _audIcon(String a) { switch (a.toLowerCase()) { case 'public': return Icons.people; case 'rescue_1122': return Icons.local_hospital; case 'hospital': return Icons.medical_services; case 'mosque': return Icons.mosque; case 'lesco': return Icons.bolt; default: return Icons.message; } }
}
