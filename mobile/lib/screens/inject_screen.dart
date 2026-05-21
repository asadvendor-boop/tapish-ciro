import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../providers/pipeline_provider.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class InjectScreen extends StatefulWidget {
  const InjectScreen({super.key});

  @override
  State<InjectScreen> createState() => _InjectScreenState();
}

class _InjectScreenState extends State<InjectScreen> with TickerProviderStateMixin {
  final _textController = TextEditingController();
  late final Map<String, AnimationController> _pulseControllers;

  static const _exampleTweets = [
    'Bhati Gate mein bachay behosh ho rahe hain, garmi bohat zyada hai 🔥',
    'Misri Shah bijli 3 ghante se gayab, burhay log behosh',
    'Liberty Market mein emergency bol rahe hain lekin kuch nahi hua lagta fake hai',
    'Model Town ka AC nahi chal raha gas bhi nahi aa rahi',
    'Gulberg mein ambulance chahiye fori tor par, heatstroke ke patient hain',
    'DHA Phase 5 mein pani ka tanker nahi aaya 2 din se',
  ];

  @override
  void initState() {
    super.initState();
    _pulseControllers = {};
    for (final agent in PipelineProvider.agentOrder) {
      _pulseControllers[agent] = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 800),
      );
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    for (final c in _pulseControllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowPurple,
        glowPosition: const Alignment(0.8, -0.5),
        child: SafeArea(
          child: Column(
            children: [
              // ── App Bar ──
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  children: [
                    const Icon(Icons.science, color: AppColors.heatOrange, size: 24),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('اندراج', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                        const Text('Inject Signal', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
                      ],
                    ),
                    const Spacer(),
                    const LiveBadge(),
                  ],
                ),
              ),

              // ── Content ──
              Expanded(
                child: Consumer<PipelineProvider>(
                  builder: (context, pipeline, _) {
                    _updateAnimations(pipeline);
                    return SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Agent pipeline badges
                          _buildAgentBadgeRow(pipeline),
                          const SizedBox(height: 20),

                          // Input field
                          GlassCard(
                            padding: const EdgeInsets.all(4),
                            child: TextField(
                              controller: _textController,
                              maxLines: 3,
                              enabled: !pipeline.isRunning,
                              style: const TextStyle(fontSize: 15, color: AppColors.textPrimary),
                              decoration: InputDecoration(
                                hintText: 'کوئی بھی ٹویٹ ٹائپ کریں...\nType any Roman Urdu tweet...',
                                hintStyle: AppTheme.urduStyle(fontSize: 13, color: AppColors.textMuted),
                                hintMaxLines: 2,
                                border: InputBorder.none,
                                contentPadding: const EdgeInsets.all(14),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // Send button
                          SizedBox(
                            height: 52,
                            child: ElevatedButton(
                              onPressed: pipeline.isRunning ? null : _onSend,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppColors.heatOrange,
                                foregroundColor: Colors.white,
                                disabledBackgroundColor: AppColors.heatOrange.withValues(alpha: 0.3),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                              ),
                              child: pipeline.isRunning
                                  ? const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        SizedBox(width: 18, height: 18,
                                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)),
                                        SizedBox(width: 10),
                                        Text('Pipeline Running...', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                                      ],
                                    )
                                  : const Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        Icon(Icons.local_fire_department, size: 22),
                                        SizedBox(width: 8),
                                        Text('Send to Pipeline 🔥', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                                      ],
                                    ),
                            ),
                          ),

                          const SizedBox(height: 12),

                          // Auto Demo — 7 scenario selector (matches web dashboard)
                          SizedBox(
                            width: double.infinity,
                            height: 48,
                            child: OutlinedButton(
                              onPressed: pipeline.isRunning ? null : () => _showScenarioPicker(context),
                              style: OutlinedButton.styleFrom(
                                side: BorderSide(color: AppColors.accentPurple.withValues(alpha: 0.5)),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.play_arrow, color: AppColors.accentPurple, size: 20),
                                  SizedBox(width: 8),
                                  Text('خودکار ڈیمو — Auto Demo',
                                    style: TextStyle(fontSize: 14, color: AppColors.accentPurple)),
                                  SizedBox(width: 6),
                                  Text('▾', style: TextStyle(fontSize: 10, color: AppColors.accentPurple)),
                                ],
                              ),
                            ),
                          ),

                          // Error display
                          if (pipeline.error != null) ...[
                            const SizedBox(height: 12),
                            GlassCard(
                              borderColor: AppColors.error.withValues(alpha: 0.3),
                              fillColor: AppColors.error.withValues(alpha: 0.08),
                              padding: const EdgeInsets.all(12),
                              child: Row(
                                children: [
                                  const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                                  const SizedBox(width: 8),
                                  Expanded(child: Text(pipeline.error!, style: const TextStyle(color: AppColors.error, fontSize: 13))),
                                ],
                              ),
                            ),
                          ],

                          // Result card
                          if (pipeline.result != null) ...[
                            const SizedBox(height: 16),
                            _buildResultCard(pipeline.result!),
                          ],

                          // Example tweets
                          const SizedBox(height: 28),
                          Text('مثالیں — Quick Examples',
                            style: AppTheme.urduStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
                          const SizedBox(height: 10),
                          ..._exampleTweets.map(_buildExampleChip),
                        ],
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildAgentBadgeRow(PipelineProvider pipeline) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      child: Column(
        children: [
          const Text('5-Agent System',
            style: TextStyle(fontSize: 12, color: AppColors.textMuted, letterSpacing: 1)),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: PipelineProvider.agentOrder.asMap().entries.map((entry) {
              final index = entry.key;
              final agent = entry.value;
              final isCompleted = pipeline.completedAgents.contains(agent);
              final isActive = pipeline.currentAgent == agent;
              // Detect skipped: pipeline finished, agent not completed, but a later agent was completed
              final isSkipped = !pipeline.isRunning && !isCompleted && !isActive &&
                  pipeline.completedAgents.isNotEmpty &&
                  PipelineProvider.agentOrder.indexOf(agent) < PipelineProvider.agentOrder.lastIndexWhere(
                    (a) => pipeline.completedAgents.contains(a));

              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _AgentBadge(
                    name: agent,
                    isActive: isActive,
                    isCompleted: isCompleted,
                    isPending: !isCompleted && !isActive && !isSkipped,
                    isSkipped: isSkipped,
                    pulseController: _pulseControllers[agent]!,
                  ),
                  if (index < PipelineProvider.agentOrder.length - 1)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: Icon(Icons.arrow_forward_ios, size: 10,
                        color: isCompleted
                            ? AgentColors.forAgent(agent).withValues(alpha: 0.6)
                            : AppColors.textMuted.withValues(alpha: 0.2)),
                    ),
                ],
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildResultCard(Map<String, dynamic> result) {
    final elapsed = result['elapsed_ms'] ?? 0;
    final path = result['pipeline_path']?.toString() ?? '';
    final dispatched = result['dispatch_executed'] == true;

    return GlassCard(
      borderColor: AppColors.success.withValues(alpha: 0.3),
      fillColor: AppColors.success.withValues(alpha: 0.06),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: AppColors.success, size: 20),
              const SizedBox(width: 8),
              const Text('Pipeline Complete',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.success)),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.glassFill,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.glassBorder),
                ),
                child: Text('${elapsed}ms',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
              ),
            ],
          ),
          if (path.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text('Path: $path', style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
          ],
          const SizedBox(height: 6),
          Text(dispatched ? '✅ Resources dispatched' : '❌ Dispatch blocked',
            style: TextStyle(fontSize: 13, color: dispatched ? AppColors.success : AppColors.warning)),
        ],
      ),
    );
  }

  Widget _buildExampleChip(String tweet) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: GlassCard(
        padding: const EdgeInsets.all(12),
        borderRadius: 12,
        onTap: () {
          HapticFeedback.selectionClick();
          _textController.text = tweet;
        },
        child: Text(tweet, style: const TextStyle(fontSize: 13, color: AppColors.textSecondary)),
      ),
    );
  }

  // ── Auto Demo Scenarios (matches web dashboard) ──
  static const _scenarios = [
    {'id': 'heatwave', 'icon': '🔥', 'label': 'Heatwave', 'desc': 'Punjabi tweet — Bhati Gate, 40+ fainted',
     'source': 'twitter', 'geo': 'Bhati Gate, Walled City, Lahore', 'expected': 'dispatch',
     'text': 'بھاٹی گیٹ والڈ سٹی وچ گرمی نال 40 توں زیادہ لوک بے ہوش، ریسکیو 1122 دا نمبر بند، فوری مدد چاہیدی اے'},
    {'id': 'flood_false', 'icon': '🌊', 'label': 'Flood', 'desc': 'Viral panic tweet — no location, no evidence',
     'source': 'twitter', 'geo': '', 'expected': 'retract',
     'text': 'OMG LAHORE IS SINKING!!! Massive flood EVERYWHERE 😱😱🌊 Share before they DELETE this!! #LahoreFloods #Breaking'},
    {'id': 'power_outage', 'icon': '⚡', 'label': 'Power Outage', 'desc': 'LESCO transformer failure — Model Town',
     'source': 'rescue_1122', 'geo': 'Model Town, Lahore', 'expected': 'dispatch',
     'text': 'EMERGENCY: Complete power failure across Model Town Blocks C and D. LESCO transformer exploded at main feeder. 8 calls reporting elderly trapped in elevators. UPS backup failing in nursing homes.'},
    {'id': 'accident', 'icon': '🚨', 'label': 'Road Accident', 'desc': 'Multi-vehicle crash — Gulberg',
     'source': 'twitter', 'geo': 'Gulberg III, Lahore', 'expected': 'dispatch',
     'text': 'Gulberg Main Boulevard par bari accident ho gayi, 3 gariyan aur ek bus takra gayi. Sadak band hai, logon ne khud injured ko utha ke le ja rahe hain. Koi ambulance nahi aa rahi!'},
    {'id': 'infrastructure_false', 'icon': '🏗️', 'label': 'Infrastructure', 'desc': 'Forwarded WhatsApp hoax — no specifics',
     'source': 'twitter', 'geo': '', 'expected': 'retract',
     'text': '🚨🚨 BREAKING!! Building has COLLAPSED somewhere in Lahore!! Many DEAD!! Govt is HIDING this!! Forward to everyone you know!! 🚨🚨 #PrayForLahore #BuildingCollapse'},
    {'id': 'protest', 'icon': '📢', 'label': 'Protest', 'desc': 'Road blockage — Cantt area, traffic jammed',
     'source': 'twitter', 'geo': 'Cantt, Mall Road, Lahore', 'expected': 'dispatch',
     'text': 'Mall Road Cantt par dharna shuru ho gaya hai, hazaron log sadak par baithe hain. Tamam traffic ruki hui hai, ambulances bhi nahi guzar sakti. Police force deployed but no clearance yet.'},
    {'id': 'disease_false', 'icon': '🦠', 'label': 'Disease Cluster', 'desc': 'WhatsApp rumor — unverified cholera panic',
     'source': 'twitter', 'geo': '', 'expected': 'retract',
     'text': 'Guys CHOLERA has SPREAD in Lahore water supply!! 😰😰 My cousin\'s friend is doctor he said dont drink tap water AT ALL!! Bohat log admit hain hospitals mein! Share karo sab ko batao!! 🏥💀'},
  ];

  void _showScenarioPicker(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0f1225),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Text('SELECT SCENARIO',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: AppColors.textMuted, letterSpacing: 2)),
          ),
          const Divider(height: 1, color: AppColors.glassBorder),
          Flexible(
            child: ListView.builder(
              shrinkWrap: true,
              itemCount: _scenarios.length,
              itemBuilder: (_, i) {
                final s = _scenarios[i];
                final isRetract = s['expected'] == 'retract';
                return ListTile(
                  leading: Text(s['icon']!, style: const TextStyle(fontSize: 22)),
                  title: Row(
                    children: [
                      Text(s['label']!, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: AppColors.textPrimary)),
                      const SizedBox(width: 6),
                      if (isRetract) Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(color: AppColors.error.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
                        child: const Text('FALSE ALARM', style: TextStyle(fontSize: 7, fontWeight: FontWeight.w700, color: AppColors.error)),
                      ),
                      const SizedBox(width: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(
                          color: s['source'] == 'rescue_1122'
                            ? AppColors.success.withValues(alpha: 0.12)
                            : AppColors.accentPurple.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(s['source'] == 'rescue_1122' ? 'Rescue 1122' : 'Twitter',
                          style: TextStyle(fontSize: 7, fontWeight: FontWeight.w600,
                            color: s['source'] == 'rescue_1122' ? AppColors.success : AppColors.accentPurple)),
                      ),
                    ],
                  ),
                  subtitle: Text(s['desc']!, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
                  onTap: () {
                    Navigator.pop(ctx);
                    _runScenario(s);
                  },
                );
              },
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  void _runScenario(Map<String, String> scenario) {
    HapticFeedback.heavyImpact();
    _textController.text = scenario['text'] ?? '';
    // Use the regular pipeline provider to inject (same as manual send)
    context.read<PipelineProvider>().injectSignal(
      scenario['text'] ?? '',
      source: scenario['source'],
      geoHint: (scenario['geo']?.isNotEmpty ?? false) ? scenario['geo'] : null,
    );
  }

  void _onSend() {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    HapticFeedback.heavyImpact();
    context.read<PipelineProvider>().injectSignal(text);
  }

  void _updateAnimations(PipelineProvider pipeline) {
    for (final agent in PipelineProvider.agentOrder) {
      final controller = _pulseControllers[agent]!;
      if (pipeline.currentAgent == agent && pipeline.isRunning) {
        if (!controller.isAnimating) controller.repeat(reverse: true);
      } else {
        if (controller.isAnimating) { controller.stop(); controller.reset(); }
      }
    }
  }
}

class _AgentBadge extends StatelessWidget {
  final String name;
  final bool isActive;
  final bool isCompleted;
  final bool isPending;
  final bool isSkipped;
  final AnimationController pulseController;

  const _AgentBadge({
    required this.name, required this.isActive, required this.isCompleted,
    required this.isPending, this.isSkipped = false, required this.pulseController,
  });

  @override
  Widget build(BuildContext context) {
    final color = AgentColors.forAgent(name);
    final icon = AgentColors.iconForAgent(name);

    return AnimatedBuilder(
      animation: pulseController,
      builder: (context, child) {
        final scale = isActive ? 1.0 + pulseController.value * 0.15 : 1.0;
        final glowOpacity = isActive ? 0.3 + pulseController.value * 0.4 : 0.0;

        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Transform.scale(
              scale: scale,
              child: Container(
                width: 42, height: 42,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isCompleted ? color.withValues(alpha: 0.2)
                      : isActive ? color.withValues(alpha: 0.25)
                      : isSkipped ? AppColors.textMuted.withValues(alpha: 0.05)
                      : AppColors.glassFill,
                  border: Border.all(
                    color: isCompleted || isActive ? color
                        : isSkipped ? AppColors.textMuted.withValues(alpha: 0.15)
                        : AppColors.glassBorder,
                    width: isActive ? 2 : 1,
                  ),
                  boxShadow: isActive ? [
                    BoxShadow(color: color.withValues(alpha: glowOpacity), blurRadius: 14, spreadRadius: 2),
                  ] : null,
                ),
                child: Icon(
                  isCompleted ? Icons.check
                      : isSkipped ? Icons.remove
                      : icon, size: 20,
                  color: isCompleted || isActive ? color
                      : isSkipped ? AppColors.textMuted.withValues(alpha: 0.25)
                      : AppColors.textMuted.withValues(alpha: 0.4),
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              isSkipped ? 'Skip'
                  : const {'observer': 'Obs', 'analyst': 'Anly', 'strategist': 'Strt', 'operator': 'Opr', 'auditor': 'Aud'}[name] ?? name,
              style: TextStyle(
                fontSize: 9,
                fontWeight: isActive ? FontWeight.w700 : FontWeight.w400,
                color: isActive ? color : isCompleted ? AppColors.textSecondary
                    : isSkipped ? AppColors.textMuted.withValues(alpha: 0.3)
                    : AppColors.textMuted.withValues(alpha: 0.5),
              ),
            ),
          ],
        );
      },
    );
  }
}
