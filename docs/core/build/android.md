# Android emulator

This experimental port runs the T2T1 firmware on Android, either headless
through `adb shell`, or as an APK that shows the Trezor screen and accepts touch
input. It includes frozen MicroPython modules, Bitcoin support, and debuglink.
It uses the existing software emulator drivers, without secure elements. It is
a development emulator, with the emulator's deterministic RNG.

Android USB gadget support is outside this port; communication uses the
existing UDP emulator transport.

## Build

Initialize the submodules as described in [the build setup](index.md), then run
from the repository root:

```sh
nix-shell tools/android/shell.nix
uv sync
bash tools/android/build.sh arm64-v8a
```

The shell supplies NDK r28c, the Android SDK build tools, a JDK, and the pinned
SDL3 and SDL3_image sources. The script builds the SDL libraries for Android and
cross-compiles the firmware with `xtask --emulator-target aarch64-linux-android`.
The minimum Android API is 28. Build tools and `mpy-cross` run on the host,
independently of the Android target.

For an x86_64 Android virtual device, use:

```sh
bash tools/android/build.sh x86_64
```

The model defaults to T2T1; pass another one as the second argument, e.g.
`bash tools/android/build.sh x86_64 T3W1`. The build always disables Optiga and
Tropic, as Android has neither the secure elements nor the Tropic model server.

On Android, the firmware is linked as `libmain.so`, which exports only
`SDL_main`. Each ABI's build is collected under `core/build/android/<ABI>/`:

- `dist/` holds `libmain.so`, the SDL libraries, `udp-relay`, and
  `firmware-emu`, a launcher which runs `libmain.so` for `adb shell`.
- `trezor-emulator.apk` packages `libmain.so` with SDL's Java `SDLActivity`.
  It is built with the SDK tools directly, without Gradle, and signed with a
  debug key generated in `core/build/android/debug.keystore`.

## Run on an Android virtual device

On a Linux host with KVM, a single command enters the Nix shell, creates and
boots an Android 9 virtual device when needed, and runs the firmware on it:

```sh
tools/android/start.sh --apk   # without --apk, the firmware runs headless
```

Stop it with Ctrl-C, which leaves the virtual device running, or with
`tools/android/stop.sh`, which also stops the virtual device. See
`tools/android/start.sh --help` for the options. The steps below do the same
manually.

Enter the shell with the optional Android emulator and Android 9 system image:

```sh
nix-shell tools/android/shell.nix --arg withEmulator true
avdmanager create avd --name trezor-android \
  --package 'system-images;android-28;default;x86_64' --device pixel
emulator -avd trezor-android -port 5580 -no-window -no-audio \
  -no-boot-anim -no-snapshot -gpu swiftshader -memory 1024 -cores 2
```

Omit `-no-window` to see the Android screen. In another terminal, in the same
Nix shell:

```sh
adb -s emulator-5580 wait-for-device
uv run python tools/android/run.py --serial emulator-5580 --port 31344
```

Add `--apk` to install and start the APK instead, which shows the Trezor screen
on the device. Without it, the firmware runs headless with SDL's dummy video
driver. In both modes, the runner prints the firmware's log; the APK writes it
to `files/firmware.log` in its data directory.

Like `emu.py --headless`, the headless firmware always runs without animations,
which device tests need: a click during an animation is lost. The APK keeps its
animations, unless `--disable-animation` is passed to `run.py` or `start.sh`.

The runner makes the firmware's seven UDP ports available on the host's
`127.0.0.1`. `adb forward` carries only TCP, and the Android emulator's UDP
redirection does not return replies to the host. The runner therefore relays
each port's datagrams over `adb forward`, through `udp-relay` on the device. It
restarts firmware after a firmware reboot, preserves the profile between runs,
and stops its own device processes and removes its forwarding rules when
interrupted. The headless firmware stores its flash image in
`/data/local/tmp/trezor-android-31344/profile/`; the APK stores it in its app
data directory.

Run clients from another terminal, always selecting the runner's port:

```sh
export TREZOR_PATH=udp:127.0.0.1:31344
uv run trezorctl get-features
uv run pytest tests/device_tests/test_msg_ping.py
```

Models with THP, such as T3W1, ask for pairing on the device's screen when
`trezorctl` connects. Confirm it on the APK's screen; the headless firmware
cannot show it, so `trezorctl` waits until it times out. Device tests pair
through debuglink and work in both modes.

Stop the runner and the Android virtual device; like `start.sh`, the script
enters the Nix shell when needed:

```sh
tools/android/stop.sh emulator-5580
```

For a physical phone's serial, the script stops only the runner.

## Run on a physical phone

Enable USB debugging, build `arm64-v8a`, and pass the phone's explicit serial
from `adb devices` to the runner. It selects the matching ABI automatically.
Clients use the same `TREZOR_PATH` as with the virtual device, relayed over adb.
The headless firmware's UDP sockets are also bound to all device interfaces, so
a client with network access to the phone can connect to it directly.

## Implementation notes

Persistent storage, the task scheduler, and firmware application code use the
existing Unix emulator implementations. Android windows fill the screen, so the
display driver always scales the emulator's frame to the window, which also maps
touch coordinates back. SDL turns finger touches into the mouse events the
emulator handles. The touch driver keeps only the latest unread event, so
synthetic `adb shell input tap` events are too short; use
`input swipe <x> <y> <x> <y> 150` instead.

The APK's `TrezorActivity` sets the firmware's environment before SDL starts it,
and exits its process when the firmware stops, because the firmware's state is
static. In headless mode, the startup marks SDL ready without SDLActivity and
skips Java-dependent haptics for the dummy video driver. Without SDLActivity,
SDL never creates its lifecycle event semaphore, and SDL's event pump would spin
forever. `tools/android/sdl3-headless.patch` makes SDL treat the missing
semaphore as having no events. The build omits `-lpthread` because Bionic
provides pthreads in libc.
