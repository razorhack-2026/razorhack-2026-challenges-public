# Crew Companion — solution (GM-only)

**Access code:** `HOLD7-AFT-2074`

## Mechanism

`crew-companion.apk` is a debug-signed, non-minified Android app (`rpc.kot.companion`, one
Activity, no third-party libraries). R8 is off, so jadx gives back readable Java with the original
names. No XOR and no bit rotation: those are covered by other rev challenges (Field Diagnostic
uses rotate + transpose). The only skill here is decompiling an app and following its logic.

- **The gate — string reversal.** `unlock(code)` reverses the input and compares it to the
  constant `DOOR_CHECK = "4702-TFA-7DLOH"`. The code is that constant reversed. The literal code
  never appears in the APK.
- **The flag — Base64 split three ways.** `revealDoorCodes()` builds
  `uplinkTag() + getString(R.string.deck_key) + BuildConfig.SHIFT_SIG` and Base64-decodes it.
  The three parts live in three different places:
  1. `<meta-data android:name="rpc.kot.uplink_tag">` in `AndroidManifest.xml`, read by `uplinkTag()`
  2. `R.string.deck_key` in `res/values/strings.xml`
  3. `BuildConfig.SHIFT_SIG`, a `buildConfigField` in `app/build.gradle`

  `flag{` never appears literally anywhere in the APK.

## Intended solve

1. Open the APK in jadx-gui, or run `jadx -d out crew-companion.apk`. apktool plus a dex
   decompiler also works.
2. In `rpc.kot.companion.MainActivity`, read `unlock`: it reverses the input and compares the
   result to `DOOR_CHECK`, so the access code is `DOOR_CHECK` reversed, `HOLD7-AFT-2074`.
3. Read `revealDoorCodes` and follow each of the three terms:
   - `uplinkTag()` reads manifest meta-data `rpc.kot.uplink_tag`, giving `ZmxhZ3trMHRfZDAwcl9`
   - `R.string.deck_key` in `resources/res/values/strings.xml` is `jMGQzc19sMXYzXzFuX3`
   - `BuildConfig.SHIFT_SIG` is `RoM180cHBfMTY5ZH0=`
4. Join the three in that order and Base64-decode the result to get the flag:
   ```python
   import base64
   print(base64.b64decode("ZmxhZ3trMHRfZDAwcl9" + "jMGQzc19sMXYzXzFuX3" + "RoM180cHBfMTY5ZH0=").decode())
   ```
   On a device or emulator, typing `HOLD7-AFT-2074` into the Door Codes panel shows the same flag.
   Players don't need the code or a device: the static solve in step 4 is enough.

`solution/solve.py` automates this from `dist/` only. It runs jadx, parses the gate and the join
order out of the decompiled source, and decodes the result, with nothing hardcoded:

```sh
python3 solution/solve.py          # needs jadx on PATH and Java 11+
```

## Verification (2026-11-04, MacBook, jadx 1.5.6)

- `solve.py` on `dist/crew-companion.apk` prints exactly the `challenge.yml` flag.
- Leak checks are all empty: `grep -a 'flag{'` on the APK, `unzip -p` of every entry piped through
  the same grep, and `aapt dump strings`.
- On an API 34 arm64 emulator, entering `HOLD7-AFT-2075` shows "Access denied. Door codes stay
  locked.", and entering `HOLD7-AFT-2074` shows the flag.
- `aapt dump badging` reports `application-debuggable`, minSdk 24 and targetSdk 34, and jadx shows the
  original method and field names.
- Known and accepted for the easy tier: part 1 alone decodes to the flag's opening
  (`flag{k0t_d00r_`). Parts 2 and 3 don't decode cleanly on their own, so players still need all
  three in the right order.

## Rebuilding

From `src/`, with JDK 17 and the Android SDK (platform 34, build-tools 34.0.0):

```sh
export JAVA_HOME=<jdk17> ANDROID_HOME=<sdk>
./gradlew assembleDebug
cp app/build/outputs/apk/debug/app-debug.apk ../dist/crew-companion.apk
```

To change the flag, run `python3 src/split_flag.py 'flag{...}'`. It prints the three parts and
the file each one goes in. Update `challenge.yml` to match, rebuild, and re-run `solve.py`.
