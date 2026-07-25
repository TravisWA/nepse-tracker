[app]

title = NEPSE Tracker
package.name = nepsetracker
package.domain = com.mynepse

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

# UPDATED requirements - proven versions
requirements = python3,kivy==2.3.0,requests,certifi,charset-normalizer,idna,urllib3

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a

# Important: Don't use release, use debug
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
