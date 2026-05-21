import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'package:record/record.dart';
import 'package:path_provider/path_provider.dart' show getTemporaryDirectory;
import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class ReportScreen extends StatefulWidget {
  const ReportScreen({super.key});
  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  final _textCtrl = TextEditingController();
  final _picker = ImagePicker();
  final _recorder = AudioRecorder();
  String _mode = 'text';
  File? _mediaFile;
  String? _mediaB64;
  bool _submitting = false, _submitted = false, _recording = false, _locating = true;
  String? _resultText;
  double? _lat, _lng;
  String _locLabel = 'مقام حاصل ہو رہا ہے...';
  int _recSec = 0;

  @override
  void initState() { super.initState(); _getLoc(); }

  Future<void> _getLoc() async {
    try {
      var p = await Geolocator.checkPermission();
      if (p == LocationPermission.denied) p = await Geolocator.requestPermission();
      if (p == LocationPermission.deniedForever) { setState(() { _locLabel = '📍 مقام کی اجازت نہیں'; _locating = false; }); return; }
      final pos = await Geolocator.getCurrentPosition(locationSettings: const LocationSettings(accuracy: LocationAccuracy.high));
      setState(() { _lat = pos.latitude; _lng = pos.longitude; _locLabel = '📍 ${pos.latitude.toStringAsFixed(4)}, ${pos.longitude.toStringAsFixed(4)}'; _locating = false; });
    } catch (_) { setState(() { _locLabel = '📍 مقام دستیاب نہیں'; _locating = false; }); }
  }

  Future<void> _pickImg() async {
    final p = await _picker.pickImage(source: ImageSource.camera, maxWidth: 1280, imageQuality: 80);
    if (p != null) { final b = await p.readAsBytes(); setState(() { _mediaFile = File(p.path); _mediaB64 = base64Encode(b); _mode = 'image'; }); }
  }

  Future<void> _pickVid() async {
    final p = await _picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: 15));
    if (p != null) { final b = await p.readAsBytes(); setState(() { _mediaFile = File(p.path); _mediaB64 = base64Encode(b); _mode = 'video'; }); }
  }

  Future<void> _toggleRec() async {
    if (_recording) {
      final path = await _recorder.stop();
      if (path != null) { final b = await File(path).readAsBytes(); setState(() { _mediaFile = File(path); _mediaB64 = base64Encode(b); _mode = 'audio'; _recording = false; _recSec = 0; }); }
    } else {
      if (await _recorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        await _recorder.start(const RecordConfig(encoder: AudioEncoder.aacLc), path: '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a');
        setState(() { _recording = true; _recSec = 0; });
        _startRecTimer();
      }
    }
  }

  Timer? _recTimer;

  void _startRecTimer() {
    _recTimer?.cancel();
    _recTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted || !_recording) { _recTimer?.cancel(); return; }
      setState(() => _recSec++);
      if (_recSec >= 30) { _recTimer?.cancel(); _toggleRec(); }
    });
  }

  Future<void> _submit() async {
    if (_submitting) return;
    if (_mode == 'text' && _textCtrl.text.trim().isEmpty) { _err('براہ کرم اپنی رپورٹ لکھیں'); return; }
    if ((_mode == 'image' || _mode == 'video' || _mode == 'audio') && _mediaB64 == null) { _err('پہلے میڈیا ریکارڈ کریں'); return; }
    HapticFeedback.heavyImpact();
    setState(() { _submitting = true; _submitted = false; });
    try {
      // Get FCM token for targeted post-pipeline notification
      String? fcmToken;
      try { fcmToken = await FirebaseMessaging.instance.getToken(); } catch (_) {}
      final resp = await ApiService.ingestMultimodal({'type': _mode, 'content': _textCtrl.text.trim(), 'media_base64': _mediaB64 ?? '', 'lat': _lat, 'lng': _lng, 'context': _textCtrl.text.trim(), 'fcm_device_token': fcmToken});
      setState(() { _submitting = false; _submitted = true; _resultText = resp['message'] ?? 'آپ کی رپورٹ موصول ہو گئی'; });
      HapticFeedback.mediumImpact();
      Future.delayed(const Duration(seconds: 5), () { if (mounted) setState(() { _submitted = false; _resultText = null; _mediaFile = null; _mediaB64 = null; _textCtrl.clear(); _mode = 'text'; }); });
    } catch (e) { setState(() => _submitting = false); _err('رپورٹ بھیجنے میں خرابی'); }
  }

  void _err(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: AppColors.error, behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AmbientGlowBackground(
        glowColor: AppColors.glowOrange,
        glowPosition: const Alignment(0, -0.6),
        child: SafeArea(child: _submitted ? _successView() : _formView()),
      ),
    );
  }

  Widget _successView() => Center(child: Padding(padding: const EdgeInsets.all(32), child: Column(mainAxisSize: MainAxisSize.min, children: [
    Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.1), shape: BoxShape.circle, border: Border.all(color: AppColors.success.withValues(alpha: 0.3))),
      child: const Icon(Icons.check_circle, color: AppColors.success, size: 64)),
    const SizedBox(height: 24),
    Text('آپ کی اطلاع موصول ہو گئی', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
    const SizedBox(height: 8),
    const Text('Your report has been received', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
    if (_resultText != null) ...[const SizedBox(height: 16), GlassCard(child: Text(_resultText!, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary), textAlign: TextAlign.center))],
    const SizedBox(height: 12),
    const Text('6-agent pipeline processing...', style: TextStyle(color: AppColors.heatOrange, fontSize: 11)),
  ])));

  Widget _formView() => Column(children: [
    Padding(padding: const EdgeInsets.fromLTRB(20, 16, 20, 8), child: Row(children: [
      const Text('🚨 ', style: TextStyle(fontSize: 20)),
      Text('خطرے کی اطلاع ', style: AppTheme.urduStyle(fontSize: 18, fontWeight: FontWeight.w700)),
      const Text('Report', style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
    ])),
    Expanded(child: SingleChildScrollView(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      // Location bar
      GlassCard(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10), child: Row(children: [
        if (_locating) const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.accentPurple))
        else const Icon(Icons.location_on, color: AppColors.heatOrange, size: 18),
        const SizedBox(width: 8),
        Expanded(child: Text(_locLabel, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary))),
        IconButton(icon: const Icon(Icons.refresh, size: 16, color: AppColors.textMuted), onPressed: () { setState(() => _locating = true); _getLoc(); }, padding: EdgeInsets.zero, constraints: const BoxConstraints()),
      ])),
      const SizedBox(height: 20),
      Text('رپورٹ کا طریقہ چُنیں', style: AppTheme.urduStyle(fontSize: 14, fontWeight: FontWeight.w700)),
      const Text('Select report mode', style: TextStyle(fontSize: 10, color: AppColors.textMuted)),
      const SizedBox(height: 12),
      // Mode cards 2x2
      Row(children: [
        _modeCard('📸', 'تصویر', 'Photo', 'image', _pickImg),
        const SizedBox(width: 10),
        _disabledModeCard('📹', 'ویڈیو', 'Video'),
      ]),
      const SizedBox(height: 10),
      Row(children: [
        _modeCard('🎙️', 'آواز', 'Voice', 'audio', _toggleRec),
        const SizedBox(width: 10),
        _modeCard('📝', 'تحریر', 'Text', 'text', () => setState(() { _mode = 'text'; _mediaFile = null; _mediaB64 = null; })),
      ]),
      const SizedBox(height: 16),
      // Recording indicator
      if (_recording) GlassCard(borderColor: AppColors.error.withValues(alpha: 0.4), fillColor: AppColors.error.withValues(alpha: 0.06), child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Container(width: 12, height: 12, decoration: const BoxDecoration(color: AppColors.error, shape: BoxShape.circle)),
        const SizedBox(width: 10),
        Text('ریکارڈنگ  $_recSec/30s', style: const TextStyle(color: AppColors.error, fontWeight: FontWeight.bold, fontSize: 14)),
        const Spacer(),
        ElevatedButton.icon(onPressed: _toggleRec, icon: const Icon(Icons.stop, size: 16), label: Text('رکیں', style: AppTheme.urduStyle(fontSize: 12)), style: ElevatedButton.styleFrom(backgroundColor: AppColors.error, foregroundColor: Colors.white)),
      ])),
      // Preview
      if (_mediaFile != null && !_recording) ...[
        ClipRRect(borderRadius: BorderRadius.circular(14),
          child: _mode == 'image' ? Image.file(_mediaFile!, height: 200, width: double.infinity, fit: BoxFit.cover)
            : GlassCard(child: Center(child: Icon(_mode == 'audio' ? Icons.mic : Icons.videocam, color: AppColors.heatOrange, size: 40)))),
        TextButton.icon(onPressed: () => setState(() { _mediaFile = null; _mediaB64 = null; }),
          icon: const Icon(Icons.close, size: 14), label: Text('ہٹائیں', style: AppTheme.urduStyle(fontSize: 11)),
          style: TextButton.styleFrom(foregroundColor: AppColors.error)),
      ],
      const SizedBox(height: 8),
      // Quick-fill Punjabi Shahmukhi examples
      if (_mode == 'text') ...[
        Text('مثالیں — Examples', style: AppTheme.urduStyle(fontSize: 11, color: AppColors.textMuted)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, runSpacing: 6, children: [
          _exChip('🔥 ساڈے محلے وچ اگ لگ گئی اے، فوری مدد چاہیدی اے'),
          _exChip('🌡️ بھاٹی گیٹ وچ گرمی نال لوک بے ہوش ہو رہے نے'),
          _exChip('🌊 نہر دا پانی سڑک تے آ گیا، گڈیاں پھسیاں ہوئیاں نے'),
        ]),
        const SizedBox(height: 12),
      ],
      // Text input
      GlassCard(padding: const EdgeInsets.all(4), child: TextField(controller: _textCtrl, maxLines: 3,
        style: const TextStyle(fontSize: 14),
        decoration: InputDecoration(
          hintText: _mode == 'text' ? 'کیا ہوا ہے؟ تفصیل لکھیں...\nDescribe what you see...' : 'اضافی تفصیل (اختیاری)',
          hintStyle: AppTheme.urduStyle(fontSize: 12, color: AppColors.textMuted),
          border: InputBorder.none, contentPadding: const EdgeInsets.all(12)))),
      const SizedBox(height: 20),
      // Submit
      SizedBox(height: 52, child: ElevatedButton(onPressed: _submitting ? null : _submit,
        style: ElevatedButton.styleFrom(backgroundColor: AppColors.heatOrange, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
        child: _submitting
          ? const Row(mainAxisSize: MainAxisSize.min, children: [SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)), SizedBox(width: 10), Text('بھیج رہے ہیں...')])
          : Row(mainAxisSize: MainAxisSize.min, children: [const Text('🔥', style: TextStyle(fontSize: 18)), const SizedBox(width: 8), Text('ابھی بھیجیں — Submit Now', style: AppTheme.urduStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white))]))),
      const SizedBox(height: 16),
      // Info
      GlassCard(fillColor: AppColors.info.withValues(alpha: 0.04), borderColor: AppColors.info.withValues(alpha: 0.15), padding: const EdgeInsets.all(12),
        child: Column(children: [
          Text('آپ کی رپورٹ 6 ایجنٹ پائپ لائن سے گزرے گی:', style: AppTheme.urduStyle(fontSize: 10, color: AppColors.textMuted)),
          const SizedBox(height: 4),
          const Text('👁 Observer → 🧠 Analyst → ⚖️ Strategist → ⚡ Operator → ✅ Auditor', style: TextStyle(fontSize: 9, color: AppColors.textMuted)),
        ])),
    ])))
  ]);

  Widget _modeCard(String emoji, String urdu, String en, String mode, VoidCallback onTap) {
    final sel = _mode == mode && (_mediaFile != null || mode == 'text');
    return Expanded(child: GlassCard(
      onTap: onTap,
      borderColor: sel ? AppColors.accentPurple : AppColors.glassBorder,
      fillColor: sel ? AppColors.accentPurple.withValues(alpha: 0.08) : AppColors.glassFill,
      borderRadius: 14,
      padding: const EdgeInsets.symmetric(vertical: 16),
      glow: sel ? [BoxShadow(color: AppColors.accentPurple.withValues(alpha: 0.2), blurRadius: 12)] : null,
      child: Column(children: [
        Text(emoji, style: const TextStyle(fontSize: 28)),
        const SizedBox(height: 6),
        Text(urdu, style: AppTheme.urduStyle(fontSize: 12, fontWeight: FontWeight.w700, color: sel ? AppColors.accentPurple : AppColors.textSecondary)),
        Text(en, style: const TextStyle(fontSize: 9, color: AppColors.textMuted)),
      ]),
    ));
  }

  Widget _disabledModeCard(String emoji, String urdu, String en) {
    return Expanded(child: Opacity(opacity: 0.4, child: GlassCard(
      borderColor: AppColors.glassBorder,
      fillColor: AppColors.glassFill,
      borderRadius: 14,
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(children: [
        Text(emoji, style: const TextStyle(fontSize: 28)),
        const SizedBox(height: 6),
        Text(urdu, style: AppTheme.urduStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppColors.textMuted)),
        Text(en, style: const TextStyle(fontSize: 9, color: AppColors.textMuted)),
        const SizedBox(height: 4),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(color: AppColors.glassFill, borderRadius: BorderRadius.circular(8), border: Border.all(color: AppColors.glassBorder)),
          child: const Text('جلد آرہا ہے', style: TextStyle(fontSize: 8, color: AppColors.textMuted)),
        ),
      ]),
    )));
  }

  Widget _exChip(String text) => GestureDetector(
    onTap: () => setState(() => _textCtrl.text = text),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.glassFill,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.glassBorder),
      ),
      child: Text(text, style: AppTheme.urduStyle(fontSize: 10, color: AppColors.textSecondary)),
    ),
  );

  @override
  void dispose() { _textCtrl.dispose(); if (_recording) { _recorder.stop().then((_) => _recorder.dispose()); } else { _recorder.dispose(); } super.dispose(); }
}
