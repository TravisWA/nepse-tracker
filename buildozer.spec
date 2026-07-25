[app]

title = NEPSE Tracker
package.name = nepsetracker
package.domain = com.mynepse

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

# Simpler requirements - more stable
requirements = python3,kivy,requests,urllib3,charset-normalizer,idna,certifi,beautifulsoup4,soupsieve

orientation = portrait
fullscreen = 0

# Android settings
android.permissions = android.permission.INTERNET
android.api = 31
android.minapi = 21
android.ndk = 23b
android.accept_sdk_license = True

# Only ARM64 (most modern phones) - faster build
android.archs = arm64-v8a

# APK output
android.release_artifact = apk

# Icon (optional)
# icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 1
warn_on_root = 0
