# Project Agent Notes

## Android APK build
- The Android project is in `android-app`.
- This repo does not currently include `gradlew.bat`.
- Use the cached Gradle 9.0.0 binary on this machine:
  `C:\Users\MECHREVO\.gradle\wrapper\dists\gradle-9.0.0-bin\d6wjpkvcgsg3oed0qlfss3wgl\gradle-9.0.0\bin\gradle.bat`
- Set Android SDK environment variables before building:
  `ANDROID_HOME=C:\Users\MECHREVO\AppData\Local\Android\Sdk`
  `ANDROID_SDK_ROOT=C:\Users\MECHREVO\AppData\Local\Android\Sdk`
- Build debug APK from `android-app`:
  `gradle.bat :app:assembleDebug --console=plain`
- Output APK:
  `android-app\app\build\outputs\apk\debug\app-debug.apk`

## Notes
- Gradle 8.9 is too old for the configured Android Gradle Plugin `8.13.2`.
- Gradle 9.0.0 has been verified to build `:app:assembleDebug` on this machine.
