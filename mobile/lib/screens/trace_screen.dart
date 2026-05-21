import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/trace_provider.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class TraceScreen extends StatefulWidget {
  const TraceScreen({super.key});
  @override
  State<TraceScreen> createState() => _TraceScreenState();
}

class _TraceScreenState extends State<TraceScreen> {
  final _scrollCtrl = ScrollController();
  bool _autoScroll = true;

  @override
  void dispose() { _scrollCtrl.dispose(); super.dispose(); }

  void _scrollEnd() {
    if (_autoScroll && _scrollCtrl.hasClients) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scrollCtrl.hasClients) {
          _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowPurple,
        glowPosition: const Alignment(-0.5, -0.8),
        child: SafeArea(
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  children: [
                    const Icon(Icons.terminal, color: AppColors.accentPurple, size: 24),
                    const SizedBox(width: 10),
                    Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('ٹریس', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                      const Text('Agent Trace', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    ]),
                    const Spacer(),
                    const LiveBadge(),
                    const SizedBox(width: 8),
                    GestureDetector(
                      onTap: () => setState(() => _autoScroll = !_autoScroll),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: _autoScroll ? AppColors.accentPurple.withValues(alpha: 0.15) : AppColors.glassFill,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: _autoScroll ? AppColors.accentPurple.withValues(alpha: 0.4) : AppColors.glassBorder),
                        ),
                        child: Icon(Icons.vertical_align_bottom, size: 16,
                          color: _autoScroll ? AppColors.accentPurple : AppColors.textMuted),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Consumer<TraceProvider>(builder: (context, tp, _) {
                  if (tp.events.isEmpty) {
                    return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.hourglass_empty, size: 48, color: AppColors.textMuted.withValues(alpha: 0.3)),
                      const SizedBox(height: 12),
                      Text('پائپ لائن کا انتظار...', style: AppTheme.urduStyle(fontSize: 14, color: AppColors.textMuted)),
                      const Text('Inject a signal to see traces', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    ]));
                  }
                  _scrollEnd();
                  // Filter out empty events (system lifecycle events with no content)
                  final visibleEvents = tp.events.where((e) {
                    final content = e['content']?.toString() ?? '';
                    final reasoning = e['reasoning']?.toString() ?? '';
                    return content.isNotEmpty || reasoning.isNotEmpty;
                  }).toList();
                  if (visibleEvents.isEmpty) {
                    return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.hourglass_empty, size: 48, color: AppColors.textMuted.withValues(alpha: 0.3)),
                      const SizedBox(height: 12),
                      Text('پائپ لائن کا انتظار...', style: AppTheme.urduStyle(fontSize: 14, color: AppColors.textMuted)),
                      const Text('Inject a signal to see traces', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                    ]));
                  }
                  return ListView.builder(
                    controller: _scrollCtrl,
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    itemCount: visibleEvents.length,
                    itemBuilder: (_, i) => _LogEntry(trace: visibleEvents[i]),
                  );
                }),
              ),
              if (_autoScroll)
                Padding(padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Text('↕ Auto-scrolling', style: TextStyle(fontSize: 10, color: AppColors.textMuted.withValues(alpha: 0.5)))),
            ],
          ),
        ),
      ),
    );
  }
}

class _LogEntry extends StatelessWidget {
  final Map<String, dynamic> trace;
  const _LogEntry({required this.trace});

  @override
  Widget build(BuildContext context) {
    final agent = (trace['agent'] ?? 'system').toString().toLowerCase();
    final content = trace['content']?.toString() ?? '';
    final ts = trace['timestamp']?.toString() ?? '';
    final color = AgentColors.forAgent(agent);
    String time = '';
    if (ts.length > 18) { try { final d = DateTime.parse(ts).toUtc().add(const Duration(hours: 5)); time = '${d.hour.toString().padLeft(2,'0')}:${d.minute.toString().padLeft(2,'0')}:${d.second.toString().padLeft(2,'0')}'; } catch(_) {} }

    return GlassAccentCard(accentColor: color, child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(children: [
          Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
            child: Text('[${agent.toUpperCase()}]', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color, fontFamily: 'monospace'))),
          const Spacer(),
          Text(time, style: TextStyle(fontSize: 9, color: AppColors.textMuted.withValues(alpha: 0.5), fontFamily: 'monospace')),
        ]),
        if (content.isNotEmpty) ...[const SizedBox(height: 6),
          Text(content.length > 200 ? '${content.substring(0, 200)}...' : content,
            style: const TextStyle(fontSize: 12, color: AppColors.textSecondary, height: 1.4))],
      ],
    ));
  }
}
