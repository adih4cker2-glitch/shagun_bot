[app]
title = Aira AI Companion
package.name = aira
package.domain = com.example
source.dir = .
source.include_exts = py,kv,png,jpg,json
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS,RECORD_AUDIO,WAKE_LOCK,FOREGROUND_SERVICE,POST_NOTIFICATIONS
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
