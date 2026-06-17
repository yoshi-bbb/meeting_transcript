# Linux 版 実行ファイル作成手順（開発者・配布者向け）

このドキュメントでは、Linux 上で Meeting Mojiokoshi の Linux 配布用実行ファイルを作成する方法を説明します。

**重要**: PyInstaller は OS ネイティブの実行ファイルを作成するため、Linux 版は Linux 環境でビルドしてください。GitHub Actions では Debian 13 (trixie) ベースの Docker イメージを使用して再現性の高いビルドを行っています。

## 前提条件
- Ubuntu/Debian 系推奨（他のディストリビューションでも動作する可能性あり）
- Python 3.12
- Git

## 手順（ネイティブビルド）

1. システムパッケージをインストール
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-tk libpulse0 libasound2 libxcb-cursor0
   ```

2. リポジトリをクローン
   ```bash
   git clone https://github.com/yoshi-bbb/meeting_transcript.git
   cd meeting_transcript
   ```

3. 仮想環境を作成・有効化
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. 依存パッケージをインストール（ビルド用）
   ```bash
   python -m pip install "pip==26.1.2"
   python -m pip install -c requirements/constraints.txt -e ".[build]"
   ```

5. アプリケーションをビルド
   ```bash
   python scripts/build_desktop.py
   ```

   ビルド完了後、`dist/MeetingMojiokoshi` （実行可能バイナリ）が生成されます。

6. （推奨）自己診断を実行
   ```bash
   python scripts/smoke_desktop.py
   ```
   または完全版:
   ```bash
   python scripts/smoke_desktop.py --full
   ```

7. 配布用パッケージを作成
   ```bash
   python scripts/package_release.py
   ```

   `release/` に `MeetingMojiokoshi-0.2.0-linux-x86_64.tar.gz`（または arm64）と SHA256 ファイルが生成されます。パッケージには実行バイナリ、README.md、LICENSE、THIRD_PARTY_NOTICES.md、`.desktop` ファイルが含まれます。

## Docker を使用した再現性ビルド（推奨）
プロジェクトでは Linux バイナリの再現性を確保するため、Docker によるビルドを推奨しています。生成物は Debian 13 (trixie) 相当の glibc 環境向けです。

```bash
docker build -t meeting-mojiokoshi .
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD:/app" \
  meeting-mojiokoshi \
  python scripts/build_desktop.py
```

Docker Compose の場合:
```bash
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
docker compose run --rm builder
```

## 出力物
- `dist/MeetingMojiokoshi` : 実行可能バイナリ
- `release/*.tar.gz` : 配布用アーカイブ（LICENSE、THIRD_PARTY_NOTICES.md、.desktop ファイル同梱）

## 注意事項
- バイナリは Debian 13 (trixie) ベースの Docker イメージでビルドされます。古い glibc 環境では動作しない場合があります。
- 実行権限: パッケージング時に 0o755 が設定されますが、展開後に `chmod +x` が必要になる場合があります。
- **System Tray（タスクトレイ）対応**: pystray + Pillow を依存に追加し、PyInstaller でバンドルしています。トレイアイコン（青い円に白い「M」）が表示され、ウィンドウを閉じてもバックグラウンド動作 + 右クリックメニューで録音制御が可能になります。Linux では一部環境で `libayatana-appindicator` 系パッケージが必要な場合があります（実行時に自動フォールバック）。
- 公開リポジトリではソースコードのみを公開し、GitHub Actions は Linux ビルドのバイナリアーティファクトをアップロードしません。手動ビルドは主にローカルテスト用です。

詳細はプロジェクトルートの README.md も参照してください。
