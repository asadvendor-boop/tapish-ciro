import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';

/// Tracks pipeline execution state during signal injection
class PipelineProvider extends ChangeNotifier {
  bool _isRunning = false;
  String _currentAgent = '';
  final Set<String> _completedAgents = {};
  final List<Map<String, dynamic>> _pipelineTraces = [];
  Map<String, dynamic>? _result;
  String? _error;
  DateTime? _startTime;
  StreamSubscription? _wsSub;
  Timer? _timeoutTimer;

  bool get isRunning => _isRunning;
  String get currentAgent => _currentAgent;
  Set<String> get completedAgents => Set.unmodifiable(_completedAgents);
  List<Map<String, dynamic>> get pipelineTraces =>
      List.unmodifiable(_pipelineTraces);
  Map<String, dynamic>? get result => _result;
  String? get error => _error;
  Duration get elapsed => _startTime != null
      ? DateTime.now().difference(_startTime!)
      : Duration.zero;

  static const agentOrder = [
    'observer',
    'analyst',
    'strategist',
    'operator',
    'auditor',
  ];

  /// Start listening to trace events to track pipeline progress
  void listenToWs(WsService wsService) {
    _wsSub?.cancel();
    _wsSub = wsService.traceStream.listen(_onTraceEvent);
  }

  void _onTraceEvent(Map<String, dynamic> data) {
    if (!_isRunning) return;

    final event = data['event']?.toString() ?? '';
    final agent = data['agent']?.toString().toLowerCase() ?? '';

    // Track which agent is currently active
    if (agent.isNotEmpty && agentOrder.contains(agent)) {
      if (_currentAgent != agent) {
        if (_currentAgent.isNotEmpty) {
          _completedAgents.add(_currentAgent);
        }
        _currentAgent = agent;
        notifyListeners();
      }
    }

    // Routing decision events
    if (event == 'routing_decision') {
      _pipelineTraces.add(data);
      notifyListeners();
    }

    // Pipeline complete
    if (event == 'pipeline_complete') {
      _completedAgents.add(_currentAgent);
      _isRunning = false;
      _timeoutTimer?.cancel();
      _result = data;
      notifyListeners();
    }

    // Pipeline error — backend crashed mid-pipeline
    if (event == 'pipeline_error') {
      _isRunning = false;
      _timeoutTimer?.cancel();
      _error = data['error']?.toString() ?? 'Pipeline failed on server';
      notifyListeners();
    }
  }

  /// Inject a signal and track the pipeline
  Future<void> injectSignal(String text, {String? source, String? geoHint}) async {
    _isRunning = true;
    _currentAgent = '';
    _completedAgents.clear();
    _pipelineTraces.clear();
    _result = null;
    _error = null;
    _startTime = DateTime.now();
    notifyListeners();

    // Bug #26: Safety timeout — if WS never delivers pipeline_complete
    _timeoutTimer?.cancel();
    _timeoutTimer = Timer(const Duration(seconds: 300), () {
      if (_isRunning) {
        _isRunning = false;
        _error = 'Pipeline timed out (5min). Check backend logs.';
        notifyListeners();
      }
    });

    try {
      await ApiService.ingestSignal(text, source: source, geoHint: geoHint);
      // The WS trace events will drive the UI updates
    } catch (e) {
      _isRunning = false;
      _timeoutTimer?.cancel();
      _error = e.toString();
      notifyListeners();
    }
  }

  void reset() {
    _isRunning = false;
    _currentAgent = '';
    _completedAgents.clear();
    _pipelineTraces.clear();
    _result = null;
    _error = null;
    _startTime = null;
    _timeoutTimer?.cancel();
    notifyListeners();
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    _timeoutTimer?.cancel();
    super.dispose();
  }
}
