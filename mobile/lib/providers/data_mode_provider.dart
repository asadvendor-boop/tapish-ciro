import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

/// Manages LIVE vs DEMO data mode, synced with backend
class DataModeProvider extends ChangeNotifier {
  String _mode = 'demo'; // default to demo
  bool _loading = false;

  String get mode => _mode;
  bool get isLive => _mode == 'live';
  bool get isLoading => _loading;

  /// Fetch current mode from backend
  Future<void> fetchMode() async {
    try {
      final data = await ApiService.getDataMode();
      _mode = data['mode']?.toString() ?? 'demo';
      notifyListeners();
    } catch (_) {
      // Keep current mode if fetch fails
    }
  }

  /// Toggle between live and demo
  Future<void> toggle() async {
    if (_loading) return;
    _loading = true;
    notifyListeners();

    final newMode = _mode == 'live' ? 'demo' : 'live';
    try {
      final data = await ApiService.setDataMode(newMode);
      _mode = data['mode']?.toString() ?? newMode;
    } catch (_) {
      // Revert on error
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
