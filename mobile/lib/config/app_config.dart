/// Build-time configuration for Tapish mobile apps.
/// Uses --dart-define=IS_OPERATOR=true/false to differentiate builds.
library;

const bool isOperatorBuild =
    bool.fromEnvironment('IS_OPERATOR', defaultValue: true);

const String appName = isOperatorBuild ? 'Tapish Nigraan' : 'Tapish Awaaz';
const String appNameUrdu = isOperatorBuild ? 'تپش نگران' : 'تپش آواز';
const String appTagline = isOperatorBuild
    ? 'CIRO Operator Command Center'
    : 'اپنی بات پہنچائیں — Your Voice in Crisis';
