import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Local notification service for crisis alerts when app is in foreground.
class NotificationService {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  static Future<void> init() async {
    if (_initialized) return;
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
    );
    await _plugin.initialize(settings);
    _initialized = true;
  }

  /// Show a local notification for a crisis event
  static Future<void> showCrisisAlert({
    required String title,
    required String body,
    String? crisisId,
  }) async {
    if (!_initialized) await init();

    const androidDetails = AndroidNotificationDetails(
      'tapish_crisis',
      'Crisis Alerts',
      channelDescription: 'Real-time crisis detection alerts from Tapish',
      importance: Importance.max,
      priority: Priority.max,
      ticker: 'Crisis Alert',
      visibility: NotificationVisibility.public,
      autoCancel: false,
      ongoing: false,
      styleInformation: BigTextStyleInformation(''),
    );
    const darwinDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: darwinDetails,
    );

    await _plugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      details,
      payload: crisisId,
    );
  }
}
