0s
Run if ls bin/*.apk 1> /dev/null 2>&1; then
❌ FAILED - Last 200 lines:
                        won't work or aren't desired on Android
  --release             Build your app as a non-debug release build. (Disables
                        gdb debugging among other things)
  --with-debug-symbols  Will keep debug symbols from `.so` files.
  --keystore KEYSTORE   Keystore for JAR signing key, will use jarsigner
                        default if not specified (release build only)
  --signkey SIGNKEY     Key alias to sign PARSER_APK. with (release build
                        only)
  --keystorepw KEYSTOREPW
                        Password for keystore
  --signkeypw SIGNKEYPW
                        Password for key alias

  Whether to force compilation of a new distribution

  --force-build
  --no-force-build      (this is the default)
  --require-perfect-match
  --no-require-perfect-match
                        (this is the default)
  --allow-replace-dist  (this is the default)
  --no-allow-replace-dist
  --copy-libs
  --no-copy-libs        (this is the default)
[WARNING]: prerequisites.py is experimental and does not support all prerequisites yet.
[WARNING]: Please report any issues to the python-for-android issue tracker.
# Check application requirements
# Compile platform
# Run ['/opt/hostedtoolcache/Python/3.11.15/x64/bin/python', '-m', 'pythonforandroid.toolchain', 'create', '--dist_name=nepsetracker', '--bootstrap=sdl2', '--requirements=python3==3.11.6,kivy==2.3.0,requests,certifi,charset-normalizer,idna,urllib3', '--arch=arm64-v8a', '--copy-libs', '--color=always', '--storage-dir=/home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a', '--ndk-api=21', '--ignore-setup-py', '--debug']
# Cwd /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/python-for-android
[WARNING]: prerequisites.py is experimental and does not support all prerequisites yet.
[WARNING]: Please report any issues to the python-for-android issue tracker.
[INFO]:    Recipe python3: version "3.11.6" requested
[INFO]:    Recipe kivy: version "2.3.0" requested
[INFO]:    Will compile for the following archs: arm64-v8a
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/build
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/dists
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/build/bootstrap_builds
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/build/other_builds
[INFO]:    Found Android API target in $ANDROIDAPI: 33
[INFO]:    Available Android APIs are (33)
[INFO]:    Requested API target 33 is available, continuing.
[INFO]:    Found NDK dir in $ANDROIDNDK: /home/runner/.buildozer/android/platform/android-ndk-r25b
[INFO]:    Found NDK version 25b
[INFO]:    Getting NDK API version (i.e. minimum supported API) from user argument
[INFO]:    ccache is missing, the build will not be optimized in the future.
[DEBUG]:   All possible dists: []
[DEBUG]:   Dist matching name and arch: []
[DEBUG]:   Dist matching ndk_api and recipe: []
[INFO]:    No existing dists meet the given requirements!
[INFO]:    No dist exists that meets your requirements, so one will be built.
[INFO]:    Found a single valid recipe set: ['certifi', 'charset-normalizer', 'hostpython3', 'idna', 'libffi', 'openssl', 'requests', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'six', 'sqlite3', 'urllib3', 'python3', 'sdl2', 'pyjnius', 'setuptools', 'android', 'kivy']
[INFO]:    The selected bootstrap is sdl2
[INFO]:    # Creating dist with sdl2 bootstrap
[INFO]:    Dist will have name nepsetracker and requirements (python3, kivy, requests, certifi, charset-normalizer, idna, urllib3)
[INFO]:    Dist contains the following requirements as recipes: ['hostpython3', 'libffi', 'openssl', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'sqlite3', 'python3', 'sdl2', 'pyjnius', 'setuptools', 'android', 'kivy']
[INFO]:    Dist will also contain modules (six, requests, certifi, idna, filetype, charset-normalizer, urllib3, chardet) installed from pip
[INFO]:    Dist will be build in mode debug
[INFO]:    -> directory context /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/build/bootstrap_builds/sdl2
[INFO]:    <- directory context /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/python-for-android
[DEBUG]:   Create directory /home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a/dists/nepsetracker
[INFO]:    Recipe build order is ['hostpython3', 'libffi', 'openssl', 'sdl2_image', 'sdl2_mixer', 'sdl2_ttf', 'sqlite3', 'python3', 'sdl2', 'pyjnius', 'setuptools', 'android', 'kivy']
[INFO]:    The requirements (certifi, chardet, charset-normalizer, filetype, idna, requests, six, urllib3) were not found as recipes, they will be installed with pip.
[INFO]:    # Downloading recipes 
[INFO]:    Downloading hostpython3
[ERROR]:   Build failed: python3 should have same version as hostpython3, 3.11.6 != 3.14.2
# Command failed: ['/opt/hostedtoolcache/Python/3.11.15/x64/bin/python', '-m', 'pythonforandroid.toolchain', 'create', '--dist_name=nepsetracker', '--bootstrap=sdl2', '--requirements=python3==3.11.6,kivy==2.3.0,requests,certifi,charset-normalizer,idna,urllib3', '--arch=arm64-v8a', '--copy-libs', '--color=always', '--storage-dir=/home/runner/work/nepse-tracker/nepse-tracker/.buildozer/android/platform/build-arm64-v8a', '--ndk-api=21', '--ignore-setup-py', '--debug']
# ENVIRONMENT:
#     SHELL = '/bin/bash'
#     SELENIUM_JAR_PATH = '/usr/share/java/selenium-server.jar'
#     CONDA = '/usr/share/miniconda'
#     GITHUB_WORKSPACE = '/home/runner/work/nepse-tracker/nepse-tracker'
#     JAVA_HOME_11_X64 = '/usr/lib/jvm/temurin-11-jdk-amd64'
#     JAVA_HOME_25_X64 = '/usr/lib/jvm/temurin-25-jdk-amd64'
#     PKG_CONFIG_PATH = '/opt/hostedtoolcache/Python/3.11.15/x64/lib/pkgconfig'
#     GITHUB_PATH = '/home/runner/work/_temp/_runner_file_commands/add_path_feb152b2-fd70-434c-b768-fecc2000246c'
#     GITHUB_ACTION = '__run_3'
#     JAVA_HOME = '/opt/hostedtoolcache/Java_Temurin-Hotspot_jdk/17.0.19-10/x64'
#     GITHUB_RUN_NUMBER = '15'
#     RUNNER_NAME = 'GitHub Actions 1000000014'
#     GRADLE_HOME = '/usr/share/gradle-9.6.1'
#     GITHUB_REPOSITORY_OWNER_ID = '86665182'
#     ACTIONS_RUNNER_ACTION_ARCHIVE_CACHE = '/opt/actionarchivecache'
#     XDG_CONFIG_HOME = '/home/runner/.config'
#     Python_ROOT_DIR = '/opt/hostedtoolcache/Python/3.11.15/x64'
#     MEMORY_PRESSURE_WRITE = 'c29tZSAyMDAwMDAgMjAwMDAwMAA='
#     DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
#     ANT_HOME = '/usr/share/ant'
#     JAVA_HOME_8_X64 = '/usr/lib/jvm/temurin-8-jdk-amd64'
#     GITHUB_TRIGGERING_ACTOR = 'TravisWA'
#     pythonLocation = '/opt/hostedtoolcache/Python/3.11.15/x64'
#     GITHUB_REF_TYPE = 'branch'
#     HOMEBREW_CLEANUP_PERIODIC_FULL_DAYS = '3650'
#     ACTIONS_RUNNER_RETURN_JOB_RESULT_FOR_HOSTED = '1'
#     ANDROID_NDK = '/usr/local/lib/android/sdk/ndk/27.3.13750724'
#     BOOTSTRAP_HASKELL_NONINTERACTIVE = '1'
#     PWD = '/home/runner/work/nepse-tracker/nepse-tracker'
#     PIPX_BIN_DIR = '/opt/pipx_bin'
#     LOGNAME = 'runner'
#     GITHUB_ARTIFACTS_LIST = '/home/runner/work/_temp/_runner_file_commands/artifacts_list_feb152b2-fd70-434c-b768-fecc2000246c'
#     GITHUB_REPOSITORY_ID = '1311815102'
#     GITHUB_ACTIONS = 'true'
#     USE_BAZEL_FALLBACK_VERSION = 'silent:'
#     ANDROID_NDK_LATEST_HOME = '/usr/local/lib/android/sdk/ndk/29.0.14206865'
#     SYSTEMD_EXEC_PID = '1969'
#     GITHUB_SHA = 'bdcb5a5f8b98c2c4335ed168f44108ed0172e8cd'
#     GITHUB_WORKFLOW_REF = 'TravisWA/nepse-tracker/.github/workflows/build.yml@refs/heads/main'
#     POWERSHELL_DISTRIBUTION_CHANNEL = 'GitHub-Actions-Linux'
#     RUNNER_ENVIRONMENT = 'github-hosted'
#     DOTNET_MULTILEVEL_LOOKUP = '0'
#     GITHUB_REF = 'refs/heads/main'
#     RUNNER_OS = 'Linux'
#     GITHUB_REF_PROTECTED = 'false'
#     HOME = '/home/runner'
#     GITHUB_API_URL = 'https://api.github.com'
#     LANG = 'C.UTF-8'
#     GOROOT_1_25_X64 = '/opt/hostedtoolcache/go/1.25.12/x64'
#     RUNNER_TRACKING_ID = 'github_370990d7-d77e-4d35-a211-89c0d084c85b'
#     RUNNER_ARCH = 'X64'
#     MEMORY_PRESSURE_WATCH = '/sys/fs/cgroup/system.slice/hosted-compute-agent.service/memory.pressure'
#     RUNNER_TEMP = '/home/runner/work/_temp'
#     GITHUB_STATE = '/home/runner/work/_temp/_runner_file_commands/save_state_feb152b2-fd70-434c-b768-fecc2000246c'
#     EDGEWEBDRIVER = '/usr/local/share/edge_driver'
#     JAVA_HOME_21_X64 = '/usr/lib/jvm/temurin-21-jdk-amd64'
#     GITHUB_ENV = '/home/runner/work/_temp/_runner_file_commands/set_env_feb152b2-fd70-434c-b768-fecc2000246c'
#     GITHUB_EVENT_PATH = '/home/runner/work/_temp/_github_workflow/event.json'
#     INVOCATION_ID = '978640dbd6c24453b33f440d494e2576'
#     GITHUB_EVENT_NAME = 'push'
#     GITHUB_RUN_ID = '30158765914'
#     JAVA_HOME_17_X64 = '/opt/hostedtoolcache/Java_Temurin-Hotspot_jdk/17.0.19-10/x64'
#     ANDROID_NDK_HOME = '/usr/local/lib/android/sdk/ndk/27.3.13750724'
#     GITHUB_STEP_SUMMARY = '/home/runner/work/_temp/_runner_file_commands/step_summary_feb152b2-fd70-434c-b768-fecc2000246c'
#     HOMEBREW_NO_AUTO_UPDATE = '1'
#     GITHUB_ACTOR = 'TravisWA'
#     NVM_DIR = '/home/runner/.nvm'
#     SGX_AESM_ADDR = '1'
#     GITHUB_RUN_ATTEMPT = '1'
#     ANDROID_HOME = '/usr/local/lib/android/sdk'
#     GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'
#     ACCEPT_EULA = 'Y'
#     USER = 'runner'
#     PSModulePath = '/root/.local/share/powershell/Modules:/usr/local/share/powershell/Modules:/opt/microsoft/powershell/7/Modules:/usr/share/az_15.6.1'
#     GITHUB_SERVER_URL = 'https://github.com'
#     PIPX_HOME = '/opt/pipx'
#     GECKOWEBDRIVER = '/usr/local/share/gecko_driver'
#     CHROMEWEBDRIVER = '/usr/local/share/chromedriver-linux64'
#     SHLVL = '1'
#     ANDROID_SDK_ROOT = '/usr/local/lib/android/sdk'
#     VCPKG_INSTALLATION_ROOT = '/usr/local/share/vcpkg'
#     GITHUB_ACTOR_ID = '86665182'
#     ACTIONS_ORCHESTRATION_ID = '273f8d93-4e5e-4275-bea6-4bde12bb7c2b.build.__default'
#     RUNNER_TOOL_CACHE = '/opt/hostedtoolcache'
#     ImageVersion = '20260720.247.2'
#     Python3_ROOT_DIR = '/opt/hostedtoolcache/Python/3.11.15/x64'
#     DOTNET_NOLOGO = '1'
#     GITHUB_ARTIFACTS = '/home/runner/work/_temp/_runner_file_commands/artifacts_feb152b2-fd70-434c-b768-fecc2000246c'
#     GITHUB_WORKFLOW_SHA = 'bdcb5a5f8b98c2c4335ed168f44108ed0172e8cd'
#     GOROOT_1_24_X64 = '/opt/hostedtoolcache/go/1.24.13/x64'
#     GITHUB_REF_NAME = 'main'
#     GITHUB_JOB = 'build'
#     LD_LIBRARY_PATH = '/opt/hostedtoolcache/Python/3.11.15/x64/lib'
#     XDG_RUNTIME_DIR = '/run/user/1001'
#     AZURE_EXTENSION_DIR = '/opt/az/azcliextensions'
#     GOROOT_1_26_X64 = '/opt/hostedtoolcache/go/1.26.5/x64'
#     GITHUB_REPOSITORY = 'TravisWA/nepse-tracker'
#     Python2_ROOT_DIR = '/opt/hostedtoolcache/Python/3.11.15/x64'
#     CHROME_BIN = '/usr/bin/google-chrome'
#     ANDROID_NDK_ROOT = '/usr/local/lib/android/sdk/ndk/27.3.13750724'
#     GITHUB_RETENTION_DAYS = '90'
#     JOURNAL_STREAM = '9:14852'
#     RUNNER_WORKSPACE = '/home/runner/work/nepse-tracker'
#     GITHUB_ACTION_REPOSITORY = ''
#     HCA_CLOUD_PROVIDER = 'azure'
#     PATH = '/home/runner/.buildozer/android/platform/apache-ant-1.9.4/bin:/opt/hostedtoolcache/Java_Temurin-Hotspot_jdk/17.0.19-10/x64/bin:/opt/hostedtoolcache/Python/3.11.15/x64/bin:/opt/hostedtoolcache/Python/3.11.15/x64:/snap/bin:/home/runner/.local/bin:/opt/pipx_bin:/home/runner/.cargo/bin:/home/runner/.config/composer/vendor/bin:/usr/local/.ghcup/bin:/home/runner/.dotnet/tools:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin'
#     GITHUB_BASE_REF = ''
#     GHCUP_INSTALL_BASE_PREFIX = '/usr/local'
#     CI = 'true'
#     SWIFT_PATH = '/usr/share/swift/usr/bin'
#     ImageOS = 'ubuntu24'
#     GITHUB_REPOSITORY_OWNER = 'TravisWA'
#     GITHUB_HEAD_REF = ''
#     GITHUB_ACTION_REF = ''
#     ENABLE_RUNNER_TRACING = 'true'
#     GITHUB_WORKFLOW = 'Build APK'
#     DEBIAN_FRONTEND = 'noninteractive'
#     GITHUB_OUTPUT = '/home/runner/work/_temp/_runner_file_commands/set_output_feb152b2-fd70-434c-b768-fecc2000246c'
#     AGENT_TOOLSDIRECTORY = '/opt/hostedtoolcache'
#     _ = '/opt/hostedtoolcache/Python/3.11.15/x64/bin/buildozer'
#     PACKAGES_PATH = '/home/runner/.buildozer/android/packages'
#     ANDROIDSDK = '/home/runner/.buildozer/android/platform/android-sdk'
#     ANDROIDNDK = '/home/runner/.buildozer/android/platform/android-ndk-r25b'
#     ANDROIDAPI = '33'
#     ANDROIDMINAPI = '21'
# 
# Buildozer failed to execute the last command
# The error might be hidden in the log above this error
# Please read the full log, and search for it before
# raising an issue with buildozer itself.
# In case of a bug report, please add a full log with log_level = 2
Error: Process completed with exit code 1.
