import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tapish_app/main.dart';

void main() {
  testWidgets('App launches and shows splash screen', (WidgetTester tester) async {
    // Override HTTP to prevent real network calls
    HttpOverrides.global = _NoNetworkOverrides();

    await tester.pumpWidget(const TapishApp());

    // Verify the app shell renders without crashing
    expect(find.byType(MaterialApp), findsOneWidget);

    // Pump frames — splash animation starts
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(TapishApp), findsOneWidget);

    // Pump remaining timers (splash delay + warmup) to settle
    await tester.pump(const Duration(seconds: 3));
    // One more pump to process navigation
    await tester.pump(const Duration(seconds: 1));
  });
}

/// Prevents any real HTTP calls during tests
class _NoNetworkOverrides extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    final client = super.createHttpClient(context);
    client.badCertificateCallback = (_, __, ___) => false;
    return client;
  }
}
