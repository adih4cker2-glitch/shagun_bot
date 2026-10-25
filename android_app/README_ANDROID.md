# Aira Android starter — advanced UI

Features in this starter: in-app OpenRouter API settings, editable assistant name, four code-drawn avatar styles, RGB glow theme selector, custom command entries (allowlisted actions), one-shot Android speech recognition, opening WhatsApp if installed, and opening YouTube search results for a requested song.

## Build
Build in a supported Linux environment (Ubuntu/WSL/cloud Linux), not reliably on Android Termux itself:
```bash
pip install buildozer
buildozer android debug
```
The APK should appear under `bin/`.

## Important limitations
- This is starter source, not a compiled APK.
- Voice button uses Android's speech-recognition UI for one command at a time. It does **not** implement an always-listening wake word or a persistent background microphone service. Android restricts background microphone use; a robust always-on assistant needs a native foreground service, explicit consent/notification, and battery handling.
- YouTube opens search results; whether playback starts automatically depends on YouTube/app behavior.
- WhatsApp launch only opens the app; it does not read/send messages.
- The avatar faces are simple code-drawn demo faces, not photorealistic models. RGB is an on-screen animation effect, not physical phone LED control.
- Custom commands are limited to allowlisted actions in this starter; arbitrary shell commands are intentionally not executed.

## API setup
Open Settings inside the app, enter OpenRouter base URL, API key, and model ID. Default model ID is an example; check availability/pricing on OpenRouter. Key is stored in app-private storage, but this is not hardware-backed secret storage. Never share your key.
