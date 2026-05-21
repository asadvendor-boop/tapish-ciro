import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/ws_service.dart';

/// Manages the streaming agent trace events
class TraceProvider extends ChangeNotifier {
  final List<Map<String, dynamic>> _events = [];
  bool _autoScroll = true;
  String _activeFilter = 'all';
  StreamSubscription? _wsSub;

  List<Map<String, dynamic>> get events => List.unmodifiable(_events);
  bool get autoScroll => _autoScroll;
  String get activeFilter => _activeFilter;
  int get count => _events.length;

  /// Filtered events based on active filter
  List<Map<String, dynamic>> get filteredEvents {
    if (_activeFilter == 'all') return events;
    return _events
        .where((e) =>
            (e['agent'] ?? e['event'] ?? '').toString().toLowerCase() ==
            _activeFilter.toLowerCase())
        .toList();
  }

  /// Start listening to WebSocket trace events
  void listenToWs(WsService wsService) {
    _wsSub?.cancel();
    _wsSub = wsService.traceStream.listen((data) {
      // Bug 9 fix: Append (chronological order) — oldest at top, newest at bottom
      _events.add(data);
      // Cap at 200 events in memory
      if (_events.length > 200) {
        _events.removeRange(0, _events.length - 200);
      }
      notifyListeners();
    });
  }

  void setFilter(String filter) {
    _activeFilter = filter;
    notifyListeners();
  }

  void toggleAutoScroll() {
    _autoScroll = !_autoScroll;
    notifyListeners();
  }

  void clear() {
    _events.clear();
    notifyListeners();
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    super.dispose();
  }
}
