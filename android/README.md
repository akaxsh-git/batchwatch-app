# BatchWatch Android App (Consumer Household Edition)

BatchWatch is a lightweight, consumer-only Android application designed for household users (patients and caregivers) to verify medicine strips against official drug alert databases (such as India's CDSCO alerts for Not of Standard Quality / Spurious medicines).

---

## Key Principles & Guardrails
1. **Never claims a medicine is "safe"**: When no records match, the app strictly reports **"Not found in published alerts"**.
2. **No medical advice**: No dosage instructions, substitution recommendations, or clinical directives are ever provided.
3. **Data-driven verdicts**: Every verdict is produced by the data layer (or remote server). The UI never invents or alters any determination.
4. **No secrets or credentials**: Zero API keys or secrets embedded. Base URLs are configured through standard build configs (`BuildConfig.BASE_URL`). Cleartext HTTP is restricted to debug builds only.
5. **One-handed ergonomics**: Clean Jetpack Compose UI with bottom-aligned thumb-friendly actions, high-contrast Material 3 tokens, dark/light theme support, and TalkBack accessibility labels.

---

## Demo Scenarios (`BuildConfig.USE_DEMO = true`)

When running with `USE_DEMO = true` (the default configuration), no backend server is required. Every result screen displays a clear yellow banner: `Demo mode: sample data`.

1. **Cefixime Strip**:
   - **Batch**: `CFX2024B1`
   - **Verdict**: **FLAGGED** (found in 2 separate CDSCO alerts for assay failure and counterfeit packaging).
   - Shows plain language explanation, official alert citations, and generic next steps.
2. **Pantoprazole Strip (OCR Confusable Correction Flow)**:
   - Initial OCR read produces `BCV4OO1DZ` (confidence: 62%).
   - Character analyzer identifies confusable pairs (`O` vs `0`).
   - **Verdict**: **POSSIBLE** (alert match flagged pending batch verification).
   - User corrects the batch in the editor to `BCV4001DZ` -> **FLAGGED**.
3. **Telmisartan Strip (Background Re-Check Simulation)**:
   - **Batch**: `TLM8821`
   - Initial check -> **NOT FOUND IN PUBLISHED ALERTS**.
   - User saves medicine to "My Medicines".
   - Open Settings/Debug screen -> tap **"Simulate new monthly alert"**.
   - Next re-check (or WorkManager background sync) marks the medicine as **FLAGGED** and issues a local system notification.
4. **Manual Search**:
   - Type any of the above batch numbers (or random numbers) directly without using the camera.

---

## Switching Between Demo Mode and Real API

In [android/app/build.gradle.kts](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/build.gradle.kts):

```kotlin
buildTypes {
    debug {
        // Toggle Demo Mode:
        buildConfigField("boolean", "USE_DEMO", "true")  // Set to false for live backend
        buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:8000/\"") // Android Emulator host loopback
    }
    release {
        buildConfigField("boolean", "USE_DEMO", "false")
        buildConfigField("String", "BASE_URL", "\"https://api.batchwatch.org/\"")
    }
}
```

When `USE_DEMO = false`, [RemoteRepository](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/src/main/java/org/batchwatch/app/data/repository/RemoteRepository.kt) talks to the REST API endpoints:
- `POST /v1/scan` (multipart photo) -> extracted text, batch, expiry, confidence.
- `POST /v1/check` -> verdict, matched alerts, explanation, next steps.
- `POST /v1/recheck` -> batch list verification.
- `GET /v1/alerts/version` -> version tag for background WorkManager polling.

---

## Running the App

### Requirements
- **JDK 21**
- **Android SDK** with `compileSdk 36`, `minSdk 26` (Android 8.0+)
- Android Studio Ladybug / Meerkat (or Gradle CLI)

### 1. Run via Gradle CLI

#### Assemble Debug APK:
```bash
cd android
./gradlew assembleDebug
```
The APK is generated at:
`android/app/build/outputs/apk/debug/app-debug.apk`

#### Install & Launch on Connected Device / Emulator:
```bash
# Check connected devices
adb devices

# Install APK
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Launch Main Activity
adb shell am start -n org.batchwatch.app/.MainActivity
```

### 2. Run in Android Studio
1. Open Android Studio.
2. Select **Open** and choose the `batchwatch-app/android` directory.
3. Allow Gradle to sync.
4. Select your target device (AVD Emulator or connected USB phone with USB Debugging enabled).
5. Click **Run 'app'** (Shift + F10).

---

## Running Unit Tests

Run all unit tests via Gradle:
```bash
cd android
./gradlew testDebugUnitTest
```
Tests cover:
- [DemoRepositoryTest](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/src/test/java/org/batchwatch/app/data/DemoRepositoryTest.kt): Validates all 4 demo scenarios, ensuring no "safe" claims exist in explanations.
- [ConfusableCharsTest](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/src/test/java/org/batchwatch/app/domain/ConfusableCharsTest.kt): Lookalike character warnings (`0`/`O`, `1`/`I`, `5`/`S`, `8`/`B`, `2`/`Z`).
- [ExpiryCalculatorTest](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/src/test/java/org/batchwatch/app/domain/ExpiryCalculatorTest.kt): On-device expiry computation and formatting across date formats.
- [HomeViewModelTest](file:///c:/Users/K%20Sai%20Satvik/batchwatch-app/android/app/src/test/java/org/batchwatch/app/ui/HomeViewModelTest.kt): UI state loading, cabinet counts, and verdict mappings.

---

## Architecture Overview

```
org.batchwatch.app/
├── data/
│   ├── local/            # Room Database, MedicineDao, MedicineEntity, UserPreferences
│   ├── remote/           # Retrofit BatchWatchApi, Moshi DTOs
│   ├── repository/       # MedicineRepository, DemoRepository, RemoteRepository, Provider
│   └── worker/           # AlertRecheckWorker (WorkManager periodic background check)
├── domain/
│   ├── model/            # CheckVerdict, MatchedAlert, Medicine, ScanDraft
│   └── util/             # ConfusableChars, ExpiryCalculator, ImageCompressor
└── ui/
    ├── components/       # DemoBanner, VerdictCard, ConfusableBatchText, CameraTips
    ├── navigation/       # Pure Compose state-based navigation (Screen sealed class)
    ├── screens/
    │   ├── onboarding/   # Disclaimer, purpose, photo privacy disclosure
    │   ├── home/         # Large scan button, search button, cabinet preview
    │   ├── scan/         # CameraX preview, permission handling, gallery picker
    │   ├── confirm/      # Zoomable preview, confusable highlighter, editable batch
    │   ├── result/       # Verdict card, explanation, next steps, save button
    │   ├── cabinet/      # My Medicines Room list, expiry badges, swipe-to-delete
    │   ├── search/       # Manual batch/product search
    │   └── settings/     # Demo info & "Simulate new monthly alert" button
    └── theme/            # Material 3 clinical color palette, typography, shapes
```

---

## Limitations
- **Consumer Information Only**: Not a regulatory enforcement tool or diagnostic instrument.
- **Alert Frequency**: Public CDSCO alerts are issued periodically (typically monthly); a batch absent from alerts does not guarantee standard compliance.
- **Photo Uploads**: In live mode (`USE_DEMO = false`), photos are processed on the server to read batch stamps under varied lighting and foil curvature. Photos are downscaled to max 1600px / JPEG 85% before transmission.
