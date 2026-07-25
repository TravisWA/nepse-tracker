[app]

title = NEPSE Tracker
package.name = nepsetracker
package.domain = com.mynepse

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

# CRITICAL: Force Python 3.11 (not 3.14)
requirements = python3==3.11.6,kivy==2.3.0,requests,certifi,charset-normalizer,idna,urllib3

# App settings
orientation = portrait
fullscreen = 0

# Android configuration
android.permissions = INTERNET
android.api = 33
android.minapi = 21

# CRITICAL: Use NDK 25b (works with Python 3.11)
android.ndk = 25b

# Auto-accept licenses
android.accept_sdk_license = True

# ARM64 only (modern phones)
android.archs = arm64-v8a

# Allow backup
android.allow_backup = True

# Python-for-android options
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
