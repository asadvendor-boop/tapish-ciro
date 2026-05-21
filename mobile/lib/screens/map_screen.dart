import 'dart:async';
import 'dart:convert';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/glass_card.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});
  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  GoogleMapController? _mapCtrl;
  final Set<Marker> _markers = {};
  final Set<Circle> _circles = {};
  bool _loading = true;
  String? _error;
  Timer? _timer;
  String _filter = 'all';
  List<Map<String, dynamic>> _crises = [];

  static const _lahoreCenter = LatLng(31.5204, 74.3587);

  @override
  void initState() { super.initState(); _load(); _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load()); }

  @override
  void dispose() { _timer?.cancel(); _mapCtrl?.dispose(); super.dispose(); }

  Future<void> _load() async {
    try {
      final r = await Future.wait([ApiService.getCrises(), ApiService.getResources()]);
      final crises = r[0] as List; final resData = r[1] as Map<String, dynamic>; final resources = resData['resources'] as List? ?? [];
      final markers = <Marker>{}; _crises = [];
      for (final c in crises) {
        final id = c['id']?.toString() ?? ''; final loc = c['primary_location']?.toString() ?? '';
        final type = c['type']?.toString() ?? 'unknown'; final sev = c['severity']?.toString() ?? 'medium';
        final status = c['status']?.toString() ?? 'detected'; final conf = (c['confidence'] ?? 0).toDouble();
        final lat = _extractLat(c); final lng = _extractLng(c); if (lat == null || lng == null) continue;
        _crises.add({'type': type, 'location': loc, 'severity': sev, 'status': status, 'confidence': conf});
        if (_filter != 'all' && type != _filter) continue;
        markers.add(Marker(markerId: MarkerId('c_$id'), position: LatLng(lat, lng),
          infoWindow: InfoWindow(title: '${_emoji(type)} $loc', snippet: '${type.toUpperCase()} • $sev • ${(conf*100).toInt()}%'),
          icon: BitmapDescriptor.defaultMarkerWithHue(
            status == 'retracted' ? BitmapDescriptor.hueViolet : sev == 'critical' ? BitmapDescriptor.hueRed : sev == 'high' ? BitmapDescriptor.hueOrange : BitmapDescriptor.hueYellow)));
      }
      // Build heatmap circles for crisis locations
      final heatCircles = <Circle>{};
      int ci = 0;
      for (final c in crises) {
        final lat = _extractLat(c); final lng = _extractLng(c); if (lat == null || lng == null) continue;
        final type = c['type']?.toString() ?? ''; final sev = c['severity']?.toString() ?? '';
        final status = c['status']?.toString() ?? '';
        if (status == 'retracted') continue;
        if (_filter != 'all' && type != _filter) continue;
        final hColor = sev == 'critical' ? Colors.red : sev == 'high' ? Colors.orange : Colors.yellow;
        // Outer glow
        heatCircles.add(Circle(circleId: CircleId('heat_outer_$ci'), center: LatLng(lat, lng), radius: 1500,
          fillColor: hColor.withValues(alpha: 0.08), strokeColor: hColor.withValues(alpha: 0.15), strokeWidth: 1));
        // Inner glow
        heatCircles.add(Circle(circleId: CircleId('heat_inner_$ci'), center: LatLng(lat, lng), radius: 700,
          fillColor: hColor.withValues(alpha: 0.18), strokeColor: hColor.withValues(alpha: 0.25), strokeWidth: 1));
        ci++;
      }
      for (final r in resources) {
        final id = r['id']?.toString() ?? ''; final type = r['type']?.toString() ?? ''; final status = r['status']?.toString() ?? '';
        Map<String, dynamic>? locMap; final raw = r['current_location'];
        if (raw is String) { try { locMap = jsonDecode(raw); } catch (_) {} } else if (raw is Map) { locMap = Map<String, dynamic>.from(raw); }
        if (locMap == null) continue;
        final lat = (locMap['lat'] ?? locMap['latitude'])?.toDouble(); final lng = (locMap['lng'] ?? locMap['longitude'])?.toDouble();
        if (lat == null || lng == null) continue;
        markers.add(Marker(markerId: MarkerId('r_$id'), position: LatLng(lat, lng),
          infoWindow: InfoWindow(title: '${_resEmoji(type)} $id', snippet: '$type • $status'),
          icon: BitmapDescriptor.defaultMarkerWithHue(status == 'dispatched' ? BitmapDescriptor.hueGreen : BitmapDescriptor.hueAzure)));
      }
      if (mounted) setState(() { _markers..clear()..addAll(markers); _circles..clear()..addAll(heatCircles); _loading = false; _error = null; });
    } catch (e) { if (mounted) setState(() { _loading = false; _error = e.toString(); }); }
  }

  // Geocoding helpers
  double? _extractLat(Map<String, dynamic> c) { if (c['lat'] != null) return (c['lat'] as num).toDouble(); if (c['latitude'] != null) return (c['latitude'] as num).toDouble(); return _geoLat(c['primary_location']?.toString() ?? ''); }
  double? _extractLng(Map<String, dynamic> c) { if (c['lng'] != null) return (c['lng'] as num).toDouble(); if (c['longitude'] != null) return (c['longitude'] as num).toDouble(); return _geoLng(c['primary_location']?.toString() ?? ''); }

  static const _locs = {'bhati gate':(31.578,74.318),'liberty market':(31.515,74.345),'model town':(31.475,74.335),'gulberg':(31.51,74.35),
    'misri shah':(31.57,74.32),'anarkali':(31.56,74.33),'mall road':(31.55,74.34),'badshahi mosque':(31.5882,74.3105),
    'data darbar':(31.57,74.315),'shah alam':(31.571,74.305),'ichhra':(31.523,74.338),'garden town':(31.508,74.334),
    'dha':(31.45,74.4),'dha phase 5':(31.45,74.405),'johar town':(31.47,74.37),'township':(31.452,74.315),
    'walled city':(31.58,74.32),'shadman':(31.535,74.335),'canal road':(31.5,74.34),'ferozepur road':(31.49,74.36)};

  // Longest-match geocoding (consistent with backend)
  double? _geoLat(String l) { final k = l.toLowerCase().trim(); if (k.isEmpty) return null; String bestKey = ''; double? bestVal; for (final e in _locs.entries) { if ((k.contains(e.key)||e.key.contains(k)) && e.key.length > bestKey.length) { bestKey = e.key; bestVal = e.value.$1; } } return bestVal; }
  double? _geoLng(String l) { final k = l.toLowerCase().trim(); if (k.isEmpty) return null; String bestKey = ''; double? bestVal; for (final e in _locs.entries) { if ((k.contains(e.key)||e.key.contains(k)) && e.key.length > bestKey.length) { bestKey = e.key; bestVal = e.value.$2; } } return bestVal; }

  String _emoji(String t) => const {'heatwave':'🔥','power_outage':'⚡','flood':'🌊','accident':'🚨','infrastructure':'🏗️','protest':'📢','disease_cluster':'🦠'}[t] ?? '⚠️';
  String _resEmoji(String t) => const {'ambulance':'🚑','generator':'⚡','water_tanker':'💧','rescue_team':'🦺'}[t] ?? '📦';

  @override
  Widget build(BuildContext context) {
    final activeCrises = _crises.where((c) => c['status'] != 'retracted').toList();
    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      body: SafeArea(child: Column(children: [
        // App bar
        Padding(padding: const EdgeInsets.fromLTRB(20, 16, 20, 8), child: Row(children: [
          const Icon(Icons.map, color: AppColors.accentPurple, size: 24),
          const SizedBox(width: 10),
          Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('نقشہ', style: AppTheme.urduStyle(fontSize: 20, fontWeight: FontWeight.w700)),
            const Text('Crisis Map', style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
          ]),
          const Spacer(),
          const LiveBadge(),
          const SizedBox(width: 8),
          GestureDetector(onTap: _load, child: Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(color: AppColors.accentPurple.withValues(alpha: 0.15), shape: BoxShape.circle, border: Border.all(color: AppColors.accentPurple.withValues(alpha: 0.3))),
            child: const Icon(Icons.refresh, size: 16, color: AppColors.accentPurple),
          )),
        ])),
        // Filter chips
        SizedBox(height: 36, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 16),
          children: [
            _chip('All', 'all'), const SizedBox(width: 8),
            _chip('🔥 Heatwave', 'heatwave'), const SizedBox(width: 8),
            _chip('🌊 Flood', 'flood'), const SizedBox(width: 8),
            _chip('⚡ Power', 'power_outage'), const SizedBox(width: 8),
            _chip('🚨 Accident', 'accident'), const SizedBox(width: 8),
            _chip('🏗️ Infra', 'infrastructure'), const SizedBox(width: 8),
            _chip('📢 Protest', 'protest'), const SizedBox(width: 8),
            _chip('🦠 Disease', 'disease_cluster'),
          ])),
        const SizedBox(height: 8),
        // Map
        Expanded(child: Stack(children: [
          ClipRRect(borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            child: GoogleMap(initialCameraPosition: const CameraPosition(target: _lahoreCenter, zoom: 10.5),
              markers: _markers, circles: _circles, mapType: MapType.normal, myLocationEnabled: false,
              zoomControlsEnabled: false, mapToolbarEnabled: false, style: _darkStyle,
              onMapCreated: (c) => _mapCtrl = c)),
          if (_loading) Container(color: AppColors.deepBlack.withValues(alpha: 0.7),
            child: const Center(child: CircularProgressIndicator(color: AppColors.accentPurple))),
          if (_error != null) Positioned(top: 8, left: 12, right: 12,
            child: GlassCard(fillColor: AppColors.error.withValues(alpha: 0.15), borderColor: AppColors.error.withValues(alpha: 0.4),
              padding: const EdgeInsets.all(10), child: Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 12)))),
          // Legend button
          Positioned(top: 10, right: 10, child: GestureDetector(
            onTap: () => _showLegend(context),
            child: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: AppColors.deepBlack.withValues(alpha: 0.75), shape: BoxShape.circle,
                border: Border.all(color: AppColors.glassBorder)),
              child: const Icon(Icons.info_outline, size: 18, color: AppColors.textSecondary),
            ),
          )),
        ])),
        // Bottom sheet
        _buildBottomSheet(activeCrises),
      ])),
    );
  }

  void _showLegend(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0f1225),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Center(child: Text('MAP LEGEND', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.textMuted, letterSpacing: 2))),
          const SizedBox(height: 16),
          const Text('Crisis Pins', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          _legendRow(Colors.red, 'Critical severity crisis'),
          _legendRow(Colors.orange, 'High severity crisis'),
          _legendRow(Colors.yellow, 'Medium severity crisis'),
          _legendRow(Colors.purple, 'Retracted (false alarm)'),
          const SizedBox(height: 14),
          const Text('Resource Pins', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          _legendRow(Colors.green, 'Dispatched resource'),
          _legendRow(Colors.blue, 'Available resource'),
          const SizedBox(height: 14),
          const Text('Heat Zones', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary)),
          const SizedBox(height: 8),
          _legendRow(Colors.red.withValues(alpha: 0.3), 'Critical crisis zone radius'),
          _legendRow(Colors.orange.withValues(alpha: 0.3), 'High crisis zone radius'),
          const SizedBox(height: 16),
        ]),
      ),
    );
  }

  Widget _legendRow(Color color, String label) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(children: [
      Container(width: 14, height: 14, decoration: BoxDecoration(color: color, shape: BoxShape.circle, border: Border.all(color: Colors.white24))),
      const SizedBox(width: 10),
      Text(label, style: const TextStyle(fontSize: 12, color: AppColors.textSecondary)),
    ]),
  );

  Widget _chip(String label, String value) {
    final sel = _filter == value;
    return GestureDetector(onTap: () { setState(() => _filter = value); _load(); },
      child: Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        decoration: BoxDecoration(color: sel ? AppColors.accentPurple.withValues(alpha: 0.2) : AppColors.glassFill,
          borderRadius: BorderRadius.circular(20), border: Border.all(color: sel ? AppColors.accentPurple : AppColors.glassBorder)),
        child: Text(label, style: TextStyle(fontSize: 12, fontWeight: sel ? FontWeight.w600 : FontWeight.w400,
          color: sel ? AppColors.accentPurple : AppColors.textSecondary))));
  }

  Widget _buildBottomSheet(List<Map<String, dynamic>> crises) {
    return ClipRRect(
      child: BackdropFilter(filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          decoration: BoxDecoration(color: AppColors.glassFill, border: Border(top: BorderSide(color: AppColors.glassBorder))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Row(children: [
              Text('Active Crises: ', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
              Text('${crises.length}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: AppColors.heatOrange)),
            ]),
            const SizedBox(height: 8),
            if (crises.isEmpty)
              Text('کوئی فعال بحران نہیں', style: AppTheme.urduStyle(fontSize: 12, color: AppColors.textMuted))
            else
              ...crises.take(3).map((c) => Padding(padding: const EdgeInsets.only(bottom: 6), child: Row(children: [
                Container(width: 8, height: 8, decoration: BoxDecoration(shape: BoxShape.circle, color: SeverityColors.forSeverity(c['severity'] ?? ''))),
                const SizedBox(width: 8),
                Expanded(child: Text('${c['type']} — ${c['location']}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondary), overflow: TextOverflow.ellipsis)),
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: SeverityColors.forSeverity(c['severity'] ?? '').withValues(alpha: 0.15), borderRadius: BorderRadius.circular(4)),
                  child: Text(c['severity'] ?? '', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w600, color: SeverityColors.forSeverity(c['severity'] ?? '')))),
              ]))),
          ]),
        ),
      ),
    );
  }

  static const _darkStyle = '''[{"elementType":"geometry","stylers":[{"color":"#0D0D18"}]},{"elementType":"labels.text.fill","stylers":[{"color":"#6B7280"}]},{"elementType":"labels.text.stroke","stylers":[{"color":"#080810"}]},{"featureType":"water","elementType":"geometry.fill","stylers":[{"color":"#0A0A1A"}]},{"featureType":"road","elementType":"geometry","stylers":[{"color":"#1A1A2E"}]},{"featureType":"road","elementType":"geometry.stroke","stylers":[{"color":"#2A2A40"}]},{"featureType":"poi","elementType":"geometry","stylers":[{"color":"#12121E"}]},{"featureType":"transit","elementType":"geometry","stylers":[{"color":"#12121E"}]}]''';
}
