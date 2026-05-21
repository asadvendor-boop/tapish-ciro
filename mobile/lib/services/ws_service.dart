import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:audioplayers/audioplayers.dart';
import 'api_service.dart';
import 'notification_service.dart';

enum WsConnectionState { disconnected, connecting, connected }

/// Manages WebSocket connections to trace and alerts channels
class WsService extends ChangeNotifier {
  WebSocketChannel? _traceChannel;
  WebSocketChannel? _alertsChannel;
  bool _disposed = false;

  // Mosque TTS audio player
  final AudioPlayer _ttsPlayer = AudioPlayer();

  WsConnectionState _traceState = WsConnectionState.disconnected;
  WsConnectionState _alertsState = WsConnectionState.disconnected;

  final _traceController = StreamController<Map<String, dynamic>>.broadcast();
  final _alertsController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get traceStream => _traceController.stream;
  Stream<Map<String, dynamic>> get alertsStream => _alertsController.stream;

  WsConnectionState get traceState => _traceState;
  WsConnectionState get alertsState => _alertsState;

  // Bug 6 fix: Separate reconnect counters per channel
  int _traceReconnectAttempts = 0;
  int _alertsReconnectAttempts = 0;
  static const _maxReconnectDelay = 30; // seconds

  String get _wsBase {
    // Convert http://host:port to ws://host:port
    return ApiService.baseUrl.replaceFirst('http', 'ws');
  }

  /// Connect to both WebSocket channels
  void connectAll() {
    connectTrace();
    connectAlerts();
  }

  /// Connect to the trace WebSocket channel
  void connectTrace() {
    if (_traceState == WsConnectionState.connecting || _disposed) return;

    // Bug 4 fix: Stay in "connecting" until first message or ready event
    _traceState = WsConnectionState.connecting;
    // Defer notification to avoid setState-during-build crash
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!_disposed) notifyListeners();
    });

    try {
      _traceChannel = WebSocketChannel.connect(
        Uri.parse('$_wsBase/ws/trace'),
      );

      _traceChannel!.stream.listen(
        (message) {
          // Bug 4 fix: Only set connected on first successful message
          if (_traceState != WsConnectionState.connected) {
            _traceState = WsConnectionState.connected;
            _traceReconnectAttempts = 0;
            notifyListeners();
          }
          try {
            final data = jsonDecode(message as String);
            if (data is Map<String, dynamic>) {
              _traceController.add(data);

              // Mosque TTS auto-play: when Operator generates TTS, play on phone
              _checkAndPlayTTS(data);
            }
          } catch (_) {}
        },
        onDone: () {
          _traceState = WsConnectionState.disconnected;
          notifyListeners();
          _scheduleReconnect(connectTrace, isTrace: true);
        },
        onError: (_) {
          _traceState = WsConnectionState.disconnected;
          notifyListeners();
          _scheduleReconnect(connectTrace, isTrace: true);
        },
      );

      // If the connection is established but no messages flow yet,
      // we mark it connected after a short delay as a fallback.
      Future.delayed(const Duration(seconds: 2), () {
        if (!_disposed && _traceState == WsConnectionState.connecting) {
          _traceState = WsConnectionState.connected;
          _traceReconnectAttempts = 0;
          notifyListeners();
        }
      });
    } catch (e) {
      _traceState = WsConnectionState.disconnected;
      notifyListeners();
      _scheduleReconnect(connectTrace, isTrace: true);
    }
  }

  /// Connect to the alerts WebSocket channel
  void connectAlerts() {
    if (_alertsState == WsConnectionState.connecting || _disposed) return;

    _alertsState = WsConnectionState.connecting;
    // Defer notification to avoid setState-during-build crash
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!_disposed) notifyListeners();
    });

    try {
      _alertsChannel = WebSocketChannel.connect(
        Uri.parse('$_wsBase/ws/alerts'),
      );

      _alertsChannel!.stream.listen(
        (message) {
          // Bug 4 fix: Only set connected on first successful message
          if (_alertsState != WsConnectionState.connected) {
            _alertsState = WsConnectionState.connected;
            _alertsReconnectAttempts = 0;
            notifyListeners();
          }
          try {
            final data = jsonDecode(message as String);
            if (data is Map<String, dynamic>) {
              _alertsController.add(data);

              // Citizen notification — ONLY after pipeline completes with dispatch
              if (data['event'] == 'citizen_public_alert') {
                final type = data['type']?.toString() ?? 'Unknown';
                final location = data['location']?.toString() ?? '';
                final severity = data['severity']?.toString() ?? '';
                final elapsed = data['elapsed_ms'] ?? 0;

                NotificationService.showCrisisAlert(
                  title: '⚠️ ${severity.toUpperCase()} $type — Verified & Dispatched',
                  body: location.isNotEmpty
                    ? '📍 $location • Resources dispatched (${(elapsed / 1000).toStringAsFixed(0)}s)'
                    : 'Crisis verified — resources dispatched',
                  crisisId: data['crisis_id']?.toString(),
                );
              }
            }
          } catch (_) {}
        },
        onDone: () {
          _alertsState = WsConnectionState.disconnected;
          notifyListeners();
          _scheduleReconnect(connectAlerts, isTrace: false);
        },
        onError: (_) {
          _alertsState = WsConnectionState.disconnected;
          notifyListeners();
          _scheduleReconnect(connectAlerts, isTrace: false);
        },
      );

      Future.delayed(const Duration(seconds: 2), () {
        if (!_disposed && _alertsState == WsConnectionState.connecting) {
          _alertsState = WsConnectionState.connected;
          _alertsReconnectAttempts = 0;
          notifyListeners();
        }
      });
    } catch (e) {
      _alertsState = WsConnectionState.disconnected;
      notifyListeners();
      _scheduleReconnect(connectAlerts, isTrace: false);
    }
  }

  /// Exponential backoff reconnect — per-channel counters
  void _scheduleReconnect(VoidCallback reconnectFn, {required bool isTrace}) {
    if (_disposed) return;
    if (isTrace) {
      _traceReconnectAttempts++;
      final delay = (_traceReconnectAttempts * 2).clamp(1, _maxReconnectDelay);
      Future.delayed(Duration(seconds: delay), () {
        if (!_disposed) reconnectFn();
      });
    } else {
      _alertsReconnectAttempts++;
      final delay = (_alertsReconnectAttempts * 2).clamp(1, _maxReconnectDelay);
      Future.delayed(Duration(seconds: delay), () {
        if (!_disposed) reconnectFn();
      });
    }
  }

  /// Disconnect all channels
  void disconnectAll() {
    _traceChannel?.sink.close();
    _alertsChannel?.sink.close();
    _traceState = WsConnectionState.disconnected;
    _alertsState = WsConnectionState.disconnected;
    notifyListeners();
  }

  /// Resolve a TTS URL — handles both absolute and relative paths
  String _resolveTtsUrl(String url) {
    if (url.startsWith('http')) return url;
    // Relative URL like /tts/tts_abc123.mp3 → resolve against base
    final base = ApiService.baseUrl;
    if (url.startsWith('/')) return '$base$url';
    return '$base/$url';
  }

  /// Check trace events for mosque TTS audio URLs and auto-play
  void _checkAndPlayTTS(Map<String, dynamic> data) {
    try {
      final content = data['content']?.toString() ?? '';

      // Look for TTS URL in operator output (absolute or relative)
      if (data['agent'] == 'operator' && content.contains('tts_audio_url')) {
        // Match absolute URLs
        var urlMatch = RegExp(r'https?://[^\s"]+\.mp3').firstMatch(content);
        if (urlMatch != null) {
          _playTtsAudio(urlMatch.group(0)!);
          return;
        }
        // Match relative /tts/ paths
        urlMatch = RegExp(r'/tts/[^\s"]+\.mp3').firstMatch(content);
        if (urlMatch != null) {
          _playTtsAudio(_resolveTtsUrl(urlMatch.group(0)!));
          return;
        }
      }

      // Also check direct tts_url field
      final ttsUrl = data['tts_audio_url']?.toString() ?? '';
      if (ttsUrl.isNotEmpty) {
        _playTtsAudio(_resolveTtsUrl(ttsUrl));
      }
    } catch (_) {
      // TTS playback is best-effort — don't crash on failure
    }
  }

  /// Play a TTS audio URL through the phone speaker
  Future<void> _playTtsAudio(String url) async {
    try {
      debugPrint('🕌 Playing mosque TTS: $url');
      await _ttsPlayer.play(UrlSource(url));
    } catch (e) {
      debugPrint('TTS playback error: $e');
    }
  }

  @override
  void dispose() {
    _disposed = true;
    disconnectAll();
    _ttsPlayer.dispose();
    _traceController.close();
    _alertsController.close();
    super.dispose();
  }
}
