# Meeting Mojiokoshi

オンラインミーティングの音声を録音し、終了時に CPU 版 Whisper で文字起こしして、指定ディレクトリへ WAV と TXT を保存するデスクトップアプリです。

## ライセンス

このプロジェクトは `LICENSE` に記載のカスタム source-available ライセンスです。ソースの閲覧・改変・再配布・商用利用は可能ですが、商用利用時は製品またはサービス内に「Meeting Mojiokoshi」を利用している旨の明示と、可能な範囲での公開リポジトリへのリンクが必要です。OSI 承認の Open Source ライセンスではありません。

## プライバシーとセキュリティ

- 録音音声と文字起こしはローカルに保存されます。アプリは会議音声や文字起こし結果を意図的に外部へアップロードしません。
- 初回の Whisper モデル取得時のみ Hugging Face へ接続し、通常の HTTPS 通信メタデータ（IP アドレスなど）が送信されます。
- モデル名はアプリ内で許可済みの Hugging Face リポジトリ ID にのみマップされます。任意のリポジトリ ID は受け付けません。
- 設定・録音 WAV・一時トラック WAV・文字起こし TXT は POSIX 環境で所有者のみ読み書きできるよう保護します。
- 録音 WAV と文字起こし TXT 自体は暗号化しません。端末のディスク暗号化を有効にし、共有フォルダを出力先にしないでください。
- OneDrive、iCloud、Dropbox などの同期対象を出力先にすると、各サービスの設定に従ってファイルが外部へ同期されます。
- Windows では出力先ディレクトリの既存 ACL を継承します。機密性の高い録音には、自分だけがアクセスできるフォルダを指定してください。
- 脆弱性報告は `SECURITY.md` を参照してください。

## できること

- ダブルクリックで起動できるデスクトップアプリとして配布できます。
- 会議音声と自分のマイクを別々のデバイスから同時録音し、1つの WAV に自動ミックスします。
- Windows/Linux では loopback/monitor デバイスが見えていればオンライン会議のシステム音声を直接録音できます。
- macOS では BlackHole などの仮想オーディオデバイスを選ぶ構成を想定しています。
- GPU なしで動くように、Whisper 互換の `faster-whisper` を CPU/int8 で実行します。
- 出力先・モデル・言語・録音デバイスの設定を次回起動時まで保存します。
- 会議前に Whisper モデルをダウンロードして準備できます。

## 注意点

OS はシステム音声の録音権限と仕組みがそれぞれ違います。このアプリは「選択した会議音声デバイス」と「任意のマイク」を録音する方式です。

- Windows: `会議音声` に WASAPI loopback デバイス、`マイク` に使用中のマイクを選択してください。
- Linux: `会議音声` に PulseAudio/PipeWire の monitor source、`マイク` に使用中のマイクを選択してください。
- macOS: BlackHole などでミーティング音声を入力として見せ、`会議音声` にその仮想デバイスを選択してください。自分にも会議音声が聞こえるよう Multi-Output Device の設定が必要です。

録音前に `モデル準備` を押してください。初回だけ Whisper モデルをダウンロードし、2 回目以降はキャッシュを使います。準備せず録音した場合も、停止後に自動取得を試みます。モデル取得や文字起こしに失敗しても、確定済みの WAV は削除しません。

録音に関する法令や社内規定を確認し、参加者の同意を得た上で使用してください。

## ドキュメント

各 OS ごとの詳細な手順書を `docs/` ディレクトリに用意しています。

- **実行ファイル作成用（ビルド・パッケージング）**:
  - [Windows](docs/build-windows.md)
  - [macOS](docs/build-macos.md)
  - [Linux](docs/build-linux.md)

- **実行ファイルの実行用（エンドユーザー向け）**:
  - [Windows](docs/run-windows.md)
  - [macOS](docs/run-macos.md)
  - [Linux](docs/run-linux.md)

## 開発環境で起動

Ubuntu/Debian のシステム Python で `tkinter` がない場合は先に入れてください。

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

## アプリの使い方

1. 出力先ディレクトリを選びます。
2. `会議音声` に相手側の音声が流れる loopback/monitor/仮想デバイスを選びます。
3. `マイク` に自分のマイクを選びます。不要なら `使用しない` を選びます。
4. モデルを選び、`モデル準備` を押します。GPU なし PC では `tiny` または `base` が現実的です。
5. `録音開始` を押します。
6. ミーティング終了後に `停止して文字起こし` を押します。
7. 出力先に `meeting_YYYYMMDD_HHMMSS.wav` と `meeting_YYYYMMDD_HHMMSS.txt` が作成されます。

## 配布用アプリを作る

PyInstaller は OS ネイティブの実行ファイルを作るため、Windows 版は Windows 上、macOS 版は macOS 上、Linux 版は Linux 上でビルドしてください。

```bash
python -m pip install -c requirements/constraints.txt -e ".[build]"
python scripts/build_desktop.py
```

出力先:

```text
dist/MeetingMojiokoshi
```

Windows では `dist/MeetingMojiokoshi.exe`、macOS では app bundle、Linux では実行バイナリが生成されます。

### Linux で「ダブルクリック」やアプリメニューから起動したい場合

Linux のファイルマネージャーはセキュリティ上の理由から、バイナリをダブルクリックで直接実行しないことが多いです。

配布用 tar.gz には `MeetingMojiokoshi.desktop` も同梱されています。

1. tar.gz を展開します。
2. 必要なら `chmod +x MeetingMojiokoshi` を実行します。
3. `MeetingMojiokoshi.desktop` を `~/.local/share/applications/` にコピーします。
4. デスクトップファイルをテキストエディタで開き、`Exec=` の行を実際のバイナリのパスに書き換えます（例: `Exec=/home/ユーザ名/MeetingMojiokoshi-0.2.0-linux-x86_64/MeetingMojiokoshi`）。
5. ファイルマネージャーを再起動するか、`update-desktop-database ~/.local/share/applications` を実行すると、アプリメニューに「Meeting Mojiokoshi」が表示され、ダブルクリック相当の操作で起動できるようになります。

デスクトップファイルを使わずに直接起動したい場合は、ファイルマネージャーでバイナリを右クリック → 「プロパティ」→「アクセス権」→「プログラムとして実行を許可する」にチェックを入れる（ディストリビューションによる）、またはターミナルから `./MeetingMojiokoshi` を実行してください。

ビルド後の自己診断と配布アーカイブ作成:

```bash
python scripts/smoke_desktop.py
python scripts/package_release.py
```

`release/` にOS・CPUアーキテクチャ入りの ZIP または `tar.gz`、SHA-256 ファイル、`LICENSE`、`THIRD_PARTY_NOTICES.md` が生成されます。

### 第三者ライセンス

配布アーカイブには `THIRD_PARTY_NOTICES.md` を同梱します。PyInstaller で作成した実行ファイルは Python パッケージだけでなく、各 wheel に含まれるネイティブ共有ライブラリも同梱します。特に PyAV の upstream wheel は FFmpeg と x264/x265 を含む場合があるため、公開バイナリを配布する前に第三者ライセンス義務を確認するか、GPL コンポーネントを含まない依存構成で再ビルドしてください。

### 配布物の整合性

各リリースアーカイブには `.sha256` チェックサムが付きます。SHA-256 はファイル破損の検出には有効ですが、配布者の身元を証明するものではありません。組織外へ配布する場合は、コード署名（Windows/macOS）や GPG などの署名付きリリース手順を別途整備してください。現在の手動配布物は署名されていません。

PyInstaller はクロスコンパイラではありません。Windows版はWindows runner、macOS版はmacOS runner、Linux版は固定Docker環境で生成します。GitHub Actions の [build.yml](.github/workflows/build.yml) は Linux x86-64、Windows x86-64、macOS Intel、macOS Apple Silicon の4環境をビルドします。Linux/Windows は成果物上で `tiny` モデルによるCPU文字起こしまで、macOS は署名なし app bundle の基本自己診断までCIで確認します。macOS でも手元では `python scripts/smoke_desktop.py --full` でCPU文字起こしまで確認できます。公開リポジトリ上の CI は、第三者ライセンス確認が完了するまでバイナリアーティファクトをアップロードしません。

現在の手動配布物はコード署名・Apple notarization を行いません。SHA-256 だけでは改ざん防止や配布者認証には不十分です。組織外へ配布する場合は、Windows コード署名証明書と Apple Developer ID を用いた署名工程を追加してください。

## Docker

Docker は Linux ビルド環境の再現に使います。ベース OS は Debian 13 (trixie) の Python 3.12 イメージです。生成バイナリは同系 glibc 環境向けであり、古いディストリビューション全般との互換性は保証しません。GUI と音声デバイスを Docker コンテナ内で直接扱うのは OS ごとの差が大きいため、通常利用はホスト OS 上の配布アプリを使ってください。

```bash
docker build -t meeting-mojiokoshi .
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/app" \
  meeting-mojiokoshi \
  python scripts/build_desktop.py
```

Docker Compose を使う場合:

```bash
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
docker compose run --rm builder
```

DockerはLinux配布物のビルド用途です。Windowsの `.exe` とmacOSの `.app` は、それぞれのOS上でビルドします。

## モデルサイズの目安

- `tiny`: 速い、精度は控えめ。CPU PC での動作確認向け。
- `base`: CPU でも現実的な速度と精度。
- `small`: 精度は上がりますが、CPU では時間がかかります。
- `medium`: CPU ではかなり遅くなります。
