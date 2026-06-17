# macOS 版 実行ファイル作成手順（開発者・配布者向け）

このドキュメントでは、macOS 上で Meeting Mojiokoshi の macOS 配布用アプリ（.app バンドル）を作成する方法を説明します。

**重要**: PyInstaller は OS ネイティブの実行ファイルを作成するため、macOS 版は必ず macOS 環境でビルドしてください。

## 前提条件
- macOS 11 以降（Apple Silicon）
- Python 3.12（python.org の公式インストーラー推奨。tkinter を含む）
- Xcode Command Line Tools（`xcode-select --install`）
- Git

現在の固定依存セットでは macOS Intel を public CI の対象外にしています。Python 3.12 / macOS x86_64 では `onnxruntime` の配布 wheel がなく、`faster-whisper` の依存解決が失敗するためです。Intel Mac 向けに配布する場合は、互換性のある依存バージョンを別途検証してください。

## 手順

1. リポジトリをクローン
   ```bash
   git clone https://github.com/yoshi-bbb/meeting_transcript.git
   cd meeting_transcript
   ```

2. 仮想環境を作成・有効化
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（ビルド用）
   ```bash
   python -m pip install "pip==26.1.2"
   python -m pip install -c requirements/constraints.txt -e ".[build]"
   ```

4. アプリケーションをビルド
   ```bash
   python scripts/build_desktop.py
   ```

   ビルド完了後、`dist/MeetingMojiokoshi.app` が生成されます。

5. （推奨）自己診断を実行
   ```bash
   python scripts/smoke_desktop.py
   ```
   または完全版:
   ```bash
   python scripts/smoke_desktop.py --full
   ```

6. 配布用パッケージを作成
   ```bash
   python scripts/package_release.py
   ```

   `release/` に `MeetingMojiokoshi-0.2.0-macos-*.zip` と SHA256 ファイルが生成されます（アーキテクチャにより x86_64 または arm64）。パッケージには README.md、LICENSE、THIRD_PARTY_NOTICES.md が含まれます。

## 出力物
- `dist/MeetingMojiokoshi.app` : アプリバンドル
- `release/*.zip` : 配布用アーカイブ（README.md、LICENSE、THIRD_PARTY_NOTICES.md 同梱）

## 注意事項
- 初回ビルド時はセキュリティ警告が出る場合があります（右クリック → 開く）。
- GitHub Actions は Apple Silicon（arm64）の macOS ビルドのみ検証します。
- 公開リポジトリではソースコードのみを公開し、GitHub Actions はバイナリアーティファクトをアップロードしません。手動ビルドは主にローカル検証用です。
- **System Tray（タスクトレイ / メニューバー）対応**: pystray + Pillow を依存に追加し、PyInstaller でバンドルしています。ウィンドウを閉じるとメニューバートレイに最小化され、クリックメニューから録音制御が可能です。
- 配布時は Apple Developer ID での署名・公証（notarization）を推奨します（現在の CI では未実施）。

詳細はプロジェクトルートの README.md も参照してください。
