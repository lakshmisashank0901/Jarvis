# Jarvis.app

Swift 6 MenuBarExtra + HUD. Unsandboxed. Sign with Developer ID before installing to `/Applications`.

Open the sources in Xcode (new macOS App target named `Jarvis`, bundle id `com.jarvis.app`) and add every file under `Sources/Jarvis`. Use `Signing/entitlements.plist`. Do not enable App Sandbox.

Hotkeys: ⌥⌘Space push-to-talk, ⌥⌘Esc cancel.

Requires `jarvisd` on `ws://127.0.0.1:8741/v1` and `brain` on `http://127.0.0.1:8742`.
