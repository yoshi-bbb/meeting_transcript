# Meeting Mojiokoshi

Meeting Mojiokoshi 是一个桌面应用，用于录制在线会议音频，在会议结束时使用 CPU 版 Whisper 转写，并将 WAV 和 TXT 文件保存到指定目录。

[日本語](README.md) | [English](README.en.md) | 中文（简体）

## 许可证

本项目使用 `LICENSE` 中记载的自定义 source-available 许可证。你可以查看、修改、再分发源代码，也可以用于商业用途，但商业使用时必须在产品或服务中明确说明使用了 “Meeting Mojiokoshi”，并在合理可行的范围内提供公开仓库链接。本许可证不是 OSI 批准的 Open Source 许可证。

## 隐私与安全

- 录音音频和转写文本会保存在本地。应用不会有意将会议音频或转写结果上传到外部服务。
- 仅在首次获取 Whisper 模型时连接 Hugging Face。该请求会发送普通 HTTPS 通信元数据，例如 IP 地址。
- 模型名称只会映射到应用允许的 Hugging Face 仓库 ID。不接受任意仓库 ID。
- 在 POSIX 环境中，设置、录制的 WAV、临时音轨 WAV、转写 TXT 会被保护为仅所有者可读写。
- 录制的 WAV 和转写 TXT 本身不会加密。请启用设备磁盘加密，并避免将共享文件夹指定为输出目录。
- 如果将 OneDrive、iCloud、Dropbox 等同步目录指定为输出目录，文件可能会按照对应服务的设置同步到外部。
- 在 Windows 上，输出目录会继承现有 ACL。对于敏感录音，请指定只有你自己能访问的文件夹。
- 漏洞报告请参阅 `SECURITY.md`。

## 功能

- 可以作为双击启动的桌面应用进行分发。
- 可从不同设备同时录制会议音频和自己的麦克风，并自动混合成一个 WAV 文件。
- 在 Windows/Linux 上，如果可以看到 loopback/monitor 设备，就能直接录制在线会议的系统音频。
- 在 macOS 上，预期使用 BlackHole 等虚拟音频设备。
- 使用兼容 Whisper 的 `faster-whisper`，以 CPU/int8 模式运行，因此无需 GPU。
- 会保存输出目录、模型、语言和录音设备设置，供下次启动使用。
- 可以在会议前下载并准备 Whisper 模型。

## 注意事项

不同 OS 对系统音频录制的权限和机制不同。本应用采用录制所选 `会议音频设备` 和可选 `麦克风` 的方式。

- Windows: 在 `会议音频` 中选择 WASAPI loopback 设备，在 `麦克风` 中选择正在使用的麦克风。
- Linux: 在 `会议音频` 中选择 PulseAudio/PipeWire 的 monitor source，在 `麦克风` 中选择正在使用的麦克风。
- macOS: 使用 BlackHole 等工具将会议音频显示为输入，并在 `会议音频` 中选择该虚拟设备。为了自己也能听到会议音频，还需要配置 Multi-Output Device。

录音前请按 `模型准备`。Whisper 模型只在首次使用时下载，之后会使用缓存。如果未提前准备就开始录音，停止后应用也会尝试自动获取模型。即使模型获取或转写失败，已经确定写入的 WAV 也不会被删除。

请确认录音相关法律法规和公司内部规定，并在取得参会者同意后使用。

## 文档

各 OS 的详细步骤位于 `docs/` 目录。

- **创建可执行文件、构建与打包**:
  - [Windows](docs/build-windows.md)
  - [macOS](docs/build-macos.md)
  - [Linux](docs/build-linux.md)

- **运行可执行文件，面向最终用户**:
  - [Windows](docs/run-windows.md)
  - [macOS](docs/run-macos.md)
  - [Linux](docs/run-linux.md)

## 公开二进制文件

目前 GitHub Releases 不提供面向一般用户的预构建可执行文件。本公开仓库只发布源代码。如果需要可执行文件，请从源代码运行，或按照各 OS 的构建步骤在自己的环境中构建。

## 在开发环境中启动

如果 Ubuntu/Debian 的系统 Python 中没有 `tkinter`，请先安装。

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

## 应用使用方法

1. 选择输出目录。
2. 在 `会议音频` 中选择接收对方声音的 loopback、monitor 或虚拟设备。
3. 在 `麦克风` 中选择自己的麦克风。不需要时选择 `不使用`。
4. 选择模型并按 `模型准备`。在没有 GPU 的 PC 上，`tiny` 或 `base` 较现实。
5. 按 `开始录音`。
6. 会议结束后按 `停止并转写`。
7. 输出目录中会生成 `meeting_YYYYMMDD_HHMMSS.wav` 和 `meeting_YYYYMMDD_HHMMSS.txt`。

## 构建分发用应用

PyInstaller 会创建 OS 原生可执行文件，因此 Windows 版请在 Windows 上构建，macOS 版请在 macOS 上构建，Linux 版请在 Linux 上构建。

```bash
python -m pip install -c requirements/constraints.txt -e ".[build]"
python scripts/build_desktop.py
```

输出目录:

```text
dist/MeetingMojiokoshi
```

Windows 会生成 `dist/MeetingMojiokoshi.exe`，macOS 会生成 app bundle，Linux 会生成可执行二进制文件。

### 在 Linux 上通过双击或应用菜单启动

出于安全原因，Linux 文件管理器通常不会直接通过双击运行二进制文件。

分发用 `tar.gz` 中包含 `MeetingMojiokoshi.desktop`。

1. 解压 `tar.gz`。
2. 如有需要，执行 `chmod +x MeetingMojiokoshi`。
3. 将 `MeetingMojiokoshi.desktop` 复制到 `~/.local/share/applications/`。
4. 用文本编辑器打开 desktop 文件，将 `Exec=` 行改为实际二进制路径，例如 `Exec=/home/your-user-name/MeetingMojiokoshi-0.2.0-linux-x86_64/MeetingMojiokoshi`。
5. 重启文件管理器，或执行 `update-desktop-database ~/.local/share/applications`。之后应用菜单中会显示 “Meeting Mojiokoshi”，并可像双击应用一样启动。

如果不使用 desktop 文件而直接启动，可以在文件管理器中右键二进制文件，打开 `属性`，进入 `权限`，并在发行版提供该选项时允许作为程序执行。也可以在终端中运行 `./MeetingMojiokoshi`。

构建后的自检和分发归档创建:

```bash
python scripts/smoke_desktop.py
python scripts/package_release.py
```

`release/` 中会生成文件名包含 OS 和 CPU 架构的 ZIP 或 `tar.gz`、SHA-256 文件、`LICENSE` 和 `THIRD_PARTY_NOTICES.md`。

### 第三方许可证

分发归档会包含 `THIRD_PARTY_NOTICES.md`。PyInstaller 创建的可执行文件不仅包含 Python 包，也会包含各 wheel 中的原生共享库。尤其是 PyAV 的 upstream wheel 可能包含 FFmpeg 和 x264/x265。因此，在发布公开二进制文件之前，请确认第三方许可证义务，或使用不包含 GPL 组件的依赖组合重新构建。

### 分发物完整性

每个发布归档都会附带 `.sha256` 校验和。SHA-256 可用于检测文件损坏，但不能证明分发者身份。如果要在组织外分发，请另外建立使用 Windows/macOS 代码签名或 GPG 的签名发布流程。目前的手动分发物没有签名。

PyInstaller 不是交叉编译器。Windows 版在 Windows runner 上生成，macOS 版在 macOS runner 上生成，Linux 版在固定 Docker 环境中生成。GitHub Actions 的 [build.yml](.github/workflows/build.yml) 会验证 Linux x86-64、Windows x86-64 和 macOS Apple Silicon。Linux/Windows 会在生成物上使用 `tiny` 模型执行 CPU 转写测试，macOS 会对未签名 app bundle 执行基本自检。在自己的 macOS 环境中，可以通过 `python scripts/smoke_desktop.py --full` 验证到 CPU 转写。本公开仓库只发布源代码，CI 不会上传二进制 artifact。

目前的手动分发物没有进行代码签名或 Apple notarization。仅有 SHA-256 不足以防止篡改或认证分发者身份。面向组织外分发时，请增加使用 Windows 代码签名证书和 Apple Developer ID 的签名步骤。

## Docker

Docker 用于复现 Linux 构建环境。基础 OS 是 Debian 13 (trixie) 的 Python 3.12 镜像。生成的二进制文件面向同类 glibc 环境，不保证兼容较旧发行版。直接在 Docker 容器中处理 GUI 和音频设备会因 OS 差异而变得复杂，因此日常使用请使用宿主 OS 上的分发应用。

```bash
docker build -t meeting-mojiokoshi .
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/app" \
  meeting-mojiokoshi \
  python scripts/build_desktop.py
```

使用 Docker Compose:

```bash
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
docker compose run --rm builder
```

Docker 用于构建 Linux 分发物。Windows 的 `.exe` 和 macOS 的 `.app` 需要分别在对应 OS 上构建。

## 模型大小参考

- `tiny`: 速度快，精度较低。适合在 CPU PC 上确认运行。
- `base`: 在 CPU 上速度和精度都比较现实。
- `small`: 精度更高，但在 CPU 上耗时较长。
- `medium`: 在 CPU 上会非常慢。
