# Meeting Mojiokoshi

Meeting Mojiokoshi is a desktop app that records online meeting audio, transcribes it with CPU-based Whisper when the meeting ends, and saves WAV and TXT files to a selected directory.

[日本語](README.md) | English | [中文（简体）](README.zh-CN.md)

## License

This project is released under the custom source-available license described in `LICENSE`. You may view, modify, redistribute, and use the source commercially, but commercial use requires clear attribution that the product or service uses "Meeting Mojiokoshi" and, where reasonably possible, a link to the public repository. This is not an OSI-approved Open Source license.

## Privacy And Security

- Recorded audio and transcripts are saved locally. The app does not intentionally upload meeting audio or transcript results to external services.
- The app connects to Hugging Face only when downloading a Whisper model for the first time. Normal HTTPS metadata, such as the IP address, is sent during that request.
- Model names are mapped only to Hugging Face repository IDs allowed by the app. Arbitrary repository IDs are not accepted.
- Settings, recorded WAV files, temporary track WAV files, and transcript TXT files are protected on POSIX systems so that only the owner can read and write them.
- Recorded WAV files and transcript TXT files are not encrypted. Enable disk encryption on your device and do not use a shared folder as the output directory.
- If you choose a folder synced by OneDrive, iCloud, Dropbox, or a similar service, files may be synced externally according to that service's settings.
- On Windows, the output directory inherits its existing ACLs. For sensitive recordings, choose a folder that only you can access.
- See `SECURITY.md` for vulnerability reporting.

## Features

- Can be distributed as a double-clickable desktop app.
- Records meeting audio and your microphone from separate devices at the same time, then automatically mixes them into one WAV file.
- On Windows and Linux, online meeting system audio can be recorded directly when a loopback or monitor device is available.
- On macOS, the expected setup is to select a virtual audio device such as BlackHole.
- Uses the Whisper-compatible `faster-whisper` engine with CPU/int8 so it can run without a GPU.
- Saves output directory, model, language, and recording device settings for the next launch.
- Lets you download and prepare the Whisper model before a meeting.

## Important Notes

Each OS has different permissions and mechanisms for recording system audio. This app records the selected `meeting audio device` and an optional microphone.

- Windows: Select a WASAPI loopback device for `Meeting audio` and your current microphone for `Microphone`.
- Linux: Select a PulseAudio/PipeWire monitor source for `Meeting audio` and your current microphone for `Microphone`.
- macOS: Use BlackHole or a similar tool to expose meeting audio as an input, then select that virtual device for `Meeting audio`. You also need a Multi-Output Device setup so you can still hear the meeting audio yourself.

Press `Prepare model` before recording. The Whisper model is downloaded only the first time, and the cached model is used after that. If you record without preparing the model, the app will still try to download it after recording stops. If model download or transcription fails, finalized WAV files are not deleted.

Check applicable laws and internal rules for recording, and use the app only after obtaining participant consent.

## Documentation

Detailed OS-specific guides are available in the `docs/` directory.

- **Creating executables, builds, and packages**:
  - [Windows](docs/build-windows.md)
  - [macOS](docs/build-macos.md)
  - [Linux](docs/build-linux.md)

- **Running executables, for end users**:
  - [Windows](docs/run-windows.md)
  - [macOS](docs/run-macos.md)
  - [Linux](docs/run-linux.md)

## Public Binaries

GitHub Releases currently does not provide prebuilt executables for general users. This public repository publishes source code only. If you need an executable, run from source or build it in your own environment by following the build guide for your OS.

## Run In A Development Environment

If `tkinter` is not available in the system Python on Ubuntu/Debian, install it first.

```bash
sudo apt-get install python3-tk libpulse0 libasound2
```

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "pip==26.1.2"
python -m pip install -c requirements/constraints.txt -e ".[build]"
python -m meeting_mojiokoshi
```

## How To Use The App

1. Choose an output directory.
2. For `Meeting audio`, choose the loopback, monitor, or virtual device that receives the other participants' audio.
3. For `Microphone`, choose your own microphone. If you do not need it, choose `Do not use`.
4. Choose a model and press `Prepare model`. On PCs without a GPU, `tiny` or `base` is realistic.
5. Press `Start recording`.
6. After the meeting ends, press `Stop and transcribe`.
7. `meeting_YYYYMMDD_HHMMSS.wav` and `meeting_YYYYMMDD_HHMMSS.txt` are created in the output directory.

## Build A Distribution App

PyInstaller creates OS-native executables, so build the Windows version on Windows, the macOS version on macOS, and the Linux version on Linux.

```bash
python -m pip install -c requirements/constraints.txt -e ".[build]"
python scripts/build_desktop.py
```

Output:

```text
dist/MeetingMojiokoshi
```

On Windows, this creates `dist/MeetingMojiokoshi.exe`. On macOS, it creates an app bundle. On Linux, it creates an executable binary.

### Launching From Double Click Or An App Menu On Linux

For security reasons, Linux file managers often do not directly run binaries by double click.

The distribution `tar.gz` includes `MeetingMojiokoshi.desktop`.

1. Extract the `tar.gz`.
2. Run `chmod +x MeetingMojiokoshi` if needed.
3. Copy `MeetingMojiokoshi.desktop` to `~/.local/share/applications/`.
4. Open the desktop file in a text editor and update the `Exec=` line to the actual binary path, for example `Exec=/home/your-user-name/MeetingMojiokoshi-0.2.0-linux-x86_64/MeetingMojiokoshi`.
5. Restart your file manager or run `update-desktop-database ~/.local/share/applications`. `Meeting Mojiokoshi` will then appear in the app menu and can be launched like a double-clickable app.

If you want to run the binary directly without a desktop file, right-click the binary in the file manager, open `Properties`, go to `Permissions`, and enable execution as a program if your distribution provides that option. You can also run `./MeetingMojiokoshi` from a terminal.

Self-check and release archive creation after the build:

```bash
python scripts/smoke_desktop.py
python scripts/package_release.py
```

The `release/` directory will contain a ZIP or `tar.gz` file with OS and CPU architecture in the filename, a SHA-256 file, `LICENSE`, and `THIRD_PARTY_NOTICES.md`.

### Third-Party Licenses

Distribution archives include `THIRD_PARTY_NOTICES.md`. Executables created with PyInstaller include native shared libraries contained in wheels, not just Python packages. In particular, upstream PyAV wheels may include FFmpeg and x264/x265. Before distributing public binaries, confirm the third-party license obligations or rebuild with a dependency set that does not include GPL components.

### Release Integrity

Each release archive includes a `.sha256` checksum. SHA-256 is useful for detecting file corruption, but it does not prove the identity of the distributor. For distribution outside your organization, set up a signed release process using code signing on Windows/macOS or GPG. Current manual distribution files are not signed.

PyInstaller is not a cross-compiler. Build Windows releases on a Windows runner, macOS releases on a macOS runner, and Linux releases in the pinned Docker environment. GitHub Actions [build.yml](.github/workflows/build.yml) validates Linux x86-64, Windows x86-64, and macOS Apple Silicon. Linux and Windows CI run CPU transcription with the `tiny` model on the built artifact. macOS CI runs a basic self-check on the unsigned app bundle. On your own macOS machine, you can run CPU transcription with `python scripts/smoke_desktop.py --full`. This public repository publishes source code only, and CI does not upload binary artifacts.

Current manual distribution files do not use code signing or Apple notarization. SHA-256 alone is not enough to prevent tampering or authenticate the distributor. Before distributing outside your organization, add signing steps using a Windows code signing certificate and an Apple Developer ID.

## Docker

Docker is used to reproduce the Linux build environment. The base OS is the Python 3.12 image for Debian 13 (trixie). The generated binary targets similar glibc environments, and compatibility with older distributions in general is not guaranteed. Handling GUI and audio devices directly inside Docker differs significantly by OS, so normal use should rely on the host OS distribution app.

```bash
docker build -t meeting-mojiokoshi .
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/app" \
  meeting-mojiokoshi \
  python scripts/build_desktop.py
```

Using Docker Compose:

```bash
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
docker compose run --rm builder
```

Docker is for building the Linux distribution. Windows `.exe` and macOS `.app` files are built on their respective OSes.

## Model Size Guide

- `tiny`: Fast, with modest accuracy. Good for checking operation on CPU PCs.
- `base`: Practical speed and accuracy on CPU.
- `small`: Better accuracy, but slower on CPU.
- `medium`: Very slow on CPU.
