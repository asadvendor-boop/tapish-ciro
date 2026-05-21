import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:convert';

import 'config/app_config.dart';
import 'theme/app_theme.dart';
import 'theme/app_colors.dart';

import 'services/api_service.dart';
import 'services/ws_service.dart';
import 'providers/alerts_provider.dart';
import 'providers/trace_provider.dart';
import 'providers/pipeline_provider.dart';
import 'providers/data_mode_provider.dart';
import 'services/notification_service.dart';
import 'screens/alerts_screen.dart';
import 'screens/inject_screen.dart';
import 'screens/map_screen.dart';
import 'screens/trace_screen.dart';
import 'screens/more_screen.dart';
import 'screens/operator_login_screen.dart';
import 'screens/google_login_screen.dart';
import 'screens/citizen_home_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Lock to portrait
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
  ]);

  // Status bar style
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: AppColors.surfaceCard,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  // Initialize Firebase
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint('[Firebase] Init error: $e');
  }

  // Initialize local notifications
  await NotificationService.init();

  // Register background FCM handler (must be before _setupFCMGlobal)
  FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

  // Setup FCM for BOTH build types (moved out of MainShell)
  _setupFCMGlobal();

  runApp(const TapishApp());
}

/// Global FCM setup — runs for both Nigraan and Awaaz
void _setupFCMGlobal() async {
  try {
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);
    await messaging.subscribeToTopic('crisis_alerts');
    debugPrint('[FCM] Subscribed to crisis_alerts topic');
    final token = await messaging.getToken();
    debugPrint('[FCM] Token: ${token?.substring(0, 20)}...');

    // Store foreground messages for Awaaz alerts inbox
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('[FCM] Foreground message: ${message.notification?.title}');
      _storeAlertLocally(message);
    });
  } catch (e) {
    debugPrint('[FCM] Setup error: $e');
  }
}

/// Background FCM handler — stores notifications for alerts inbox
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  await _storeAlertLocally(message);
}

Future<void> _storeAlertLocally(RemoteMessage message) async {
  try {
    final prefs = await SharedPreferences.getInstance();
    final alerts = prefs.getStringList('alerts') ?? [];
    alerts.insert(0, jsonEncode({
      'title': message.notification?.title ?? 'Crisis Alert',
      'body': message.notification?.body ?? '',
      'data': message.data,
      'time': DateTime.now().toIso8601String(),
    }));
    // Keep only last 50 alerts
    await prefs.setStringList('alerts', alerts.take(50).toList());
  } catch (_) {}
}

class TapishApp extends StatelessWidget {
  const TapishApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => WsService()),
        ChangeNotifierProvider(create: (_) => AlertsProvider()),
        ChangeNotifierProvider(create: (_) => TraceProvider()),
        ChangeNotifierProvider(create: (_) => PipelineProvider()),
        ChangeNotifierProvider(create: (_) {
          final dm = DataModeProvider();
          dm.fetchMode(); // fetch current mode from backend on startup
          return dm;
        }),
      ],
      child: MaterialApp(
        title: appName,
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        home: const SplashScreen(),
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════
// SPLASH SCREEN — Glassmorphism 2026
// ═══════════════════════════════════════════════════════════

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _fadeController;
  late final Animation<double> _fadeAnimation;
  String _warmupStatus = 'بیک اینڈ گرم ہو رہا ہے...';

  @override
  void initState() {
    super.initState();

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _fadeController.forward();

    // Warmup backend then navigate
    _warmupAndNavigate();
  }

  Future<void> _warmupAndNavigate() async {
    try {
      ApiService.setBaseUrl('https://tapish-backend-163379998754.asia-south1.run.app');
      await ApiService.get('/api/warmup');
      if (mounted) setState(() => _warmupStatus = '✅ بیک اینڈ تیار ہے');
    } catch (_) {
      if (mounted) setState(() => _warmupStatus = '⚠️ آف لائن موڈ');
    }

    // Wait at least 2s total for splash branding
    await Future.delayed(const Duration(milliseconds: 500));
    if (mounted) {
      Navigator.of(context).pushReplacement(
        PageRouteBuilder(
          pageBuilder: (_, __, ___) => const AuthGate(),
          transitionDuration: const Duration(milliseconds: 600),
          transitionsBuilder: (_, anim, __, child) {
            return FadeTransition(opacity: anim, child: child);
          },
        ),
      );
    }
  }

  @override
  void dispose() {
    _fadeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.deepBlack,
      body: Container(
        // Ambient purple + blue glow
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.3),
            radius: 1.0,
            colors: [
              Color(0xFF1A0A30), // Purple tint
              AppColors.deepBlack,
            ],
          ),
        ),
        child: Center(
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Fire icon in frosted glass circle
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [
                        Color(0x33FF6D00),
                        Color(0x337C3AED),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    border: Border.all(
                      width: 2,
                      color: AppColors.heatOrange.withValues(alpha: 0.4),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.heatOrange.withValues(alpha: 0.2),
                        blurRadius: 40,
                        spreadRadius: 8,
                      ),
                      BoxShadow(
                        color: AppColors.accentPurple.withValues(alpha: 0.15),
                        blurRadius: 60,
                        spreadRadius: 15,
                      ),
                    ],
                  ),
                  child: Icon(
                    isOperatorBuild ? Icons.shield : Icons.campaign,
                    size: 48,
                    color: AppColors.heatOrange,
                  ),
                ),
                const SizedBox(height: 28),

                // Title — Urdu
                Text(
                  appNameUrdu,
                  style: AppTheme.urduStyle(
                    fontSize: 46,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  isOperatorBuild ? 'N I G R A A N' : 'A W A A Z',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w300,
                    color: AppColors.textMuted,
                    letterSpacing: 8,
                  ),
                ),
                const SizedBox(height: 20),

                // Tagline
                Text(
                  appTagline,
                  style: TextStyle(
                    fontSize: 13,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: 32),

                // Warmup status
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 12, height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.5,
                        color: AppColors.accentPurple.withValues(alpha: 0.5),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _warmupStatus,
                      style: AppTheme.urduStyle(
                        fontSize: 11,
                        color: AppColors.textMuted.withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════
// AUTH GATE — Routes to Login or MainShell based on build type
// ═════════════════════════════════════════════════════════════

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  bool _checking = true;
  bool _authed = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    if (isOperatorBuild) {
      // Operator: check SharedPreferences session
      final prefs = await SharedPreferences.getInstance();
      final hasSession = prefs.getBool('nigraan_session') ?? false;
      setState(() { _authed = hasSession; _checking = false; });
    } else {
      // Citizen: check FirebaseAuth
      final user = FirebaseAuth.instance.currentUser;
      setState(() { _authed = user != null; _checking = false; });
    }
  }

  void _onLoginSuccess() {
    setState(() => _authed = true);
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        backgroundColor: Color(0xFF0D0221),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (!_authed && isOperatorBuild) {
      return OperatorLoginScreen(onLoginSuccess: _onLoginSuccess);
    }

    if (!_authed && !isOperatorBuild) {
      return GoogleLoginScreen(onLoginSuccess: _onLoginSuccess);
    }

    // Authed: route to the correct home
    if (isOperatorBuild) {
      return const MainShell();
    } else {
      return const CitizenHomePage();
    }
  }
}

// ═════════════════════════════════════════════════════════════
// MAIN SHELL (Bottom Navigation) — Operator Only
// ═════════════════════════════════════════════════════════════

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _currentIndex = 0;

  // Operator tabs: Inject, Map, Alerts, Trace, More (no Report)
  final _screens = const [
    InjectScreen(),
    MapScreen(),
    AlertsScreen(),
    TraceScreen(),
    MoreScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _initServices();
  }

  Future<void> _initServices() async {
    // Connect WebSockets
    final wsService = context.read<WsService>();
    wsService.connectAll();

    // Wire providers to WebSocket streams
    context.read<AlertsProvider>().listenToWs(wsService);
    context.read<TraceProvider>().listenToWs(wsService);
    context.read<PipelineProvider>().listenToWs(wsService);

    // Show foreground FCM messages as snackbars (operator context)
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message.notification?.title ?? 'New alert'),
            backgroundColor: AppColors.accentPurple,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            action: SnackBarAction(
              label: 'View',
              textColor: Colors.white,
              onPressed: () {
                setState(() => _currentIndex = 2); // Switch to Alerts tab
              },
            ),
          ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          border: Border(
            top: BorderSide(
              color: AppColors.glassBorder,
              width: 1,
            ),
          ),
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            HapticFeedback.lightImpact();
            setState(() => _currentIndex = index);
          },
          height: 72,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.science_outlined),
              selectedIcon: Icon(Icons.science),
              label: 'اندراج',
            ),
            NavigationDestination(
              icon: Icon(Icons.map_outlined),
              selectedIcon: Icon(Icons.map),
              label: 'نقشہ',
            ),
            NavigationDestination(
              icon: Icon(Icons.notifications_outlined),
              selectedIcon: Icon(Icons.notifications),
              label: 'اطلاع',
            ),
            NavigationDestination(
              icon: Icon(Icons.terminal_outlined),
              selectedIcon: Icon(Icons.terminal),
              label: 'ٹریس',
            ),
            NavigationDestination(
              icon: Icon(Icons.more_horiz_outlined),
              selectedIcon: Icon(Icons.more_horiz),
              label: 'مزید',
            ),
          ],
        ),
      ),
    );
  }
}
