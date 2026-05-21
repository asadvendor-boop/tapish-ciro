import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:tapish_app/config/app_config.dart';

/// Exception thrown when the backend returns a non-2xx status code.
class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiService {
  // Use 10.0.2.2 for Android emulator, machine IP for real device
  static String _baseUrl = 'http://10.0.2.2:8000';

  static void setBaseUrl(String url) {
    _baseUrl = url;
  }

  static String get baseUrl => _baseUrl;

  /// Generic POST request
  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return _parseResponse(response) as Map<String, dynamic>;
  }

  /// Generic GET request
  static Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(Uri.parse('$_baseUrl$path'));
    return _parseResponse(response) as Map<String, dynamic>;
  }

  /// Parse response, throwing ApiException on non-2xx status codes.
  static dynamic _parseResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    }
    // Try to extract error message from JSON body
    String errorMsg;
    try {
      final body = jsonDecode(response.body);
      errorMsg = body['detail']?.toString() ?? body['error']?.toString() ?? response.body;
    } catch (_) {
      errorMsg = response.body;
    }
    throw ApiException(response.statusCode, errorMsg);
  }

  // ─── Auth Headers ───────────────────────────────────────
  /// Get auth headers for operator (JWT Bearer) or citizen (Firebase Bearer)
  static Future<Map<String, String>> _authHeaders() async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (isOperatorBuild) {
      // Operator: use JWT from /api/admin/login (stored after login)
      final prefs = await SharedPreferences.getInstance();
      var jwt = prefs.getString('admin_jwt') ?? '';
      if (jwt.isNotEmpty) {
        // Check if JWT needs refresh (within 1 hour of expiry)
        jwt = await _maybeRefreshJwt(jwt, prefs);
        headers['Authorization'] = 'Bearer $jwt';
      }
    } else {
      // Citizen: attach Firebase ID token
      try {
        final user = _getCurrentUser();
        if (user != null) {
          final idToken = await user.getIdToken();
          if (idToken != null) {
            headers['Authorization'] = 'Bearer $idToken';
          }
        }
      } catch (_) {}
    }
    return headers;
  }

  /// Auto-refresh JWT if it's within 1 hour of expiry
  static bool _isRefreshing = false;
  static Future<String> _maybeRefreshJwt(String jwt, SharedPreferences prefs) async {
    try {
      // Decode JWT payload (base64)
      final parts = jwt.split('.');
      if (parts.length != 3) return jwt;
      final payload = parts[1];
      // Pad base64
      final normalized = base64Url.normalize(payload);
      final decoded = utf8.decode(base64Url.decode(normalized));
      final map = jsonDecode(decoded) as Map<String, dynamic>;
      final exp = (map['exp'] as num?)?.toInt() ?? 0;
      final nowSec = DateTime.now().millisecondsSinceEpoch ~/ 1000;

      // If expired → can't refresh, need re-login
      if (nowSec > exp) return jwt;

      // If within 1 hour of expiry → refresh silently
      if (exp - nowSec < 3600 && !_isRefreshing) {
        _isRefreshing = true;
        try {
          final response = await http.post(
            Uri.parse('$_baseUrl/api/admin/refresh'),
            headers: {'Authorization': 'Bearer $jwt'},
          );
          if (response.statusCode == 200) {
            final data = jsonDecode(response.body);
            final newJwt = data['token'] as String;
            await prefs.setString('admin_jwt', newJwt);
            return newJwt;
          }
        } catch (_) {
          // Silent fail — current token still valid
        } finally {
          _isRefreshing = false;
        }
      }
    } catch (_) {
      // JWT decode failed — return as-is
    }
    return jwt;
  }

  /// Get current Firebase user for citizen auth
  static User? _getCurrentUser() {
    try {
      return FirebaseAuth.instance.currentUser;
    } catch (_) {
      return null;
    }
  }

  // ─── Signal Ingestion ───────────────────────────────────
  static Future<Map<String, dynamic>> ingestSignal(String text, {String? source, String? geoHint}) async {
    final headers = await _authHeaders();
    final body = <String, dynamic>{'raw_text': text};
    if (source != null) body['source'] = source;
    if (geoHint != null) body['geo_hint'] = geoHint;
    final response = await http.post(
      Uri.parse('$_baseUrl/api/signals/ingest'),
      headers: headers,
      body: jsonEncode(body),
    );
    return _parseResponse(response);
  }

  // ─── Crises ─────────────────────────────────────────────
  static Future<List<dynamic>> getCrises() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/crises'));
    final data = _parseResponse(response);
    return data['crises'] ?? [];
  }

  static Future<Map<String, dynamic>> getCrisisDetail(String id) async {
    final response = await http.get(Uri.parse('$_baseUrl/api/crises/$id'));
    return _parseResponse(response);
  }

  static Future<List<dynamic>> getCrisisTrace(String id) async {
    final response = await http.get(Uri.parse('$_baseUrl/api/crises/$id/trace'));
    final data = _parseResponse(response);
    return data['traces'] ?? [];
  }

  // ─── Resources ──────────────────────────────────────────
  static Future<Map<String, dynamic>> getResources() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/resources'));
    return _parseResponse(response);
  }

  // ─── Simulation ─────────────────────────────────────────
  static Future<Map<String, dynamic>> getSimulationStatus() async {
    final response =
        await http.get(Uri.parse('$_baseUrl/api/simulation/status'));
    return _parseResponse(response);
  }

  static Future<Map<String, dynamic>> startSimulation(
      String scenarioId) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/simulation/start'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'scenario_id': scenarioId}),
    );
    return _parseResponse(response);
  }

  static Future<Map<String, dynamic>> resetSimulation() async {
    final headers = await _authHeaders();
    final response = await http.post(
      Uri.parse('$_baseUrl/api/simulation/reset'),
      headers: headers,
    );
    return _parseResponse(response);
  }

  // ─── Auto Demo (admin only) ─────────────────────────────
  static Future<Map<String, dynamic>> autoDemo() async {
    final headers = await _authHeaders();
    final response = await http.post(
      Uri.parse('$_baseUrl/api/simulation/auto-demo'),
      headers: headers,
    );
    return _parseResponse(response);
  }

  // ─── Data Mode (live/demo toggle) ──────────────────────
  static Future<Map<String, dynamic>> getDataMode() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/data-mode'));
    return _parseResponse(response);
  }

  static Future<Map<String, dynamic>> setDataMode(String mode) async {
    final headers = await _authHeaders();
    final response = await http.post(
      Uri.parse('$_baseUrl/api/data-mode'),
      headers: headers,
      body: jsonEncode({'mode': mode}),
    );
    return _parseResponse(response);
  }

  // ─── Citizen Management ─────────────────────────────────
  static Future<Map<String, dynamic>> registerCitizen(String idToken) async {
    final response = await http.post(
      Uri.parse('$_baseUrl/api/citizens/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'id_token': idToken}),
    );
    return _parseResponse(response);
  }

  static Future<Map<String, dynamic>> ingestMultimodal(Map<String, dynamic> body) async {
    final headers = await _authHeaders();
    final response = await http.post(
      Uri.parse('$_baseUrl/api/signals/ingest/multimodal'),
      headers: headers,
      body: jsonEncode(body),
    );
    return _parseResponse(response);
  }

  // ─── Scenarios ──────────────────────────────────────────
  static Future<List<dynamic>> getScenarios() async {
    final response =
        await http.get(Uri.parse('$_baseUrl/api/admin/scenarios'));
    final data = _parseResponse(response);
    return data['scenarios'] ?? [];
  }

  // ─── Health ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> getHealth() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/admin/health'));
    return _parseResponse(response);
  }

  // ─── Stakeholder Messages ──────────────────────────────
  static Future<List<dynamic>> getStakeholderMessages() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/stakeholder/messages'));
    final data = _parseResponse(response);
    return data['messages'] ?? [];
  }

  // ─── Baseline Comparison (system-wide) ──────────────────
  static Future<Map<String, dynamic>> getBaselineComparison() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/baseline/compare'));
    return _parseResponse(response);
  }

  // ─── Signal Streams ────────────────────────────────────
  static Future<Map<String, dynamic>> getStreamStatus() async {
    final response = await http.get(Uri.parse('$_baseUrl/api/streams/status'));
    return _parseResponse(response);
  }
}
