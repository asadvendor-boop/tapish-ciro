import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';

/// Manages crisis alerts from both WebSocket and REST API
class AlertsProvider extends ChangeNotifier {
  final List<Map<String, dynamic>> _alerts = [];
  bool _isLoading = false;
  StreamSubscription? _wsSub;

  List<Map<String, dynamic>> get alerts => List.unmodifiable(_alerts);
  bool get isLoading => _isLoading;
  int get count => _alerts.length;

  /// Start listening to WebSocket alerts
  void listenToWs(WsService wsService) {
    _wsSub?.cancel();
    _wsSub = wsService.alertsStream.listen((data) {
      _alerts.insert(0, data);
      // Cap at 100 alerts in memory
      if (_alerts.length > 100) {
        _alerts.removeRange(100, _alerts.length);
      }
      notifyListeners();
    });
  }

  /// Fetch existing crises from REST API
  Future<void> fetchCrises() async {
    _isLoading = true;
    notifyListeners();

    try {
      final crises = await ApiService.getCrises();
      // Bug #15: Normalize crisis_id for dedup — use a helper to extract ID consistently
      final existingIds = _alerts
          .map((a) => _extractCrisisId(a))
          .where((id) => id.isNotEmpty)
          .toSet();
      for (final crisis in crises) {
        final id = crisis['id'] ?? '';
        if (id.isNotEmpty && !existingIds.contains(id)) {
          _alerts.add({
            'event': 'crisis_detected',
            'crisis': crisis,
            'crisis_id': id,  // Normalize: always set top-level crisis_id
            'timestamp': crisis['created_at'] ?? '',
          });
        }
      }
      _alerts.sort((a, b) {
        final ta = a['timestamp']?.toString() ?? '';
        final tb = b['timestamp']?.toString() ?? '';
        return tb.compareTo(ta);
      });
    } catch (e) {
      debugPrint('[AlertsProvider] fetchCrises error: $e');
    }

    _isLoading = false;
    notifyListeners();
  }

  /// Consistent crisis ID extraction across WS and REST formats
  static String _extractCrisisId(Map<String, dynamic> a) {
    return a['crisis_id']?.toString() ?? (a['crisis'] as Map<String, dynamic>?)?['id']?.toString() ?? '';
  }

  void clear() {
    _alerts.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    super.dispose();
  }
}
