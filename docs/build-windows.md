# Windows 版 実行ファイル作成手順（開発者・配布者向け）

このドキュメントでは、Windows 上で Meeting Mojiokoshi の Windows 配布用実行ファイル（.exe）を作成する方法を説明します。

**重要**: PyInstaller は OS ネイティブの実行ファイルを作成するため、Windows 版は必ず Windows 環境でビルドしてください。クロスビルドはサポートされていません。

## 前提条件
- Windows 10 以降（64bit）
- Python 3.12（公式インストーラー推奨。tkinter を含むフルインストールを選択）
- Git（ソース取得用）

## 手順

1. リポジトリをクローン
   ```powershell
   git clone https://github.com/OWNER/REPOSITORY.git
   cd REPOSITORY
   ```

2. 仮想環境を作成・有効化
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. 依存パッケージをインストール（ビルド用）
   ```powershell
   python -m pip install "pip==26.1.2"
   python -m pip install -c requirements/constraints.txt -e ".[build]"
   ```

4. アプリケーションをビルド
   ```powershell
   python scripts/build_desktop.py
   ```

   ビルド完了後、`dist/MeetingMojiokoshi.exe` が生成されます。

5. （推奨）自己診断を実行
   ```powershell
   python scripts/smoke_desktop.py
   ```
   または完全版（tiny モデルをダウンロードして文字起こしテスト）:
   ```powershell
   python scripts/smoke_desktop.py --full
   ```

6. 配布用パッケージを作成
   ```powershell
   python scripts/package_release.py
   ```

   `release/` ディレクトリに `MeetingMojiokoshi-0.2.0-windows-x86_64.zip` と SHA256 ファイルが生成されます。

## 出力物
- `dist/MeetingMojiokoshi.exe` : 実行ファイル
- `release/*.zip` : 配布用アーカイブ（README.md 同梱）

## 注意事項
- ビルドにはある程度の時間とディスク容量が必要です（依存ライブラリを含む）。
- GitHub Actions では Windows runner 上で自動ビルドされます。手動ビルドは主にローカルテスト用です。
- **System Tray（タスクトレイ）対応**: pystray + Pillow を依存に追加し、PyInstaller でバンドルしています。ウィンドウを閉じるとトレイに最小化され、右クリックメニューから録音開始/停止/終了が可能です。
- 配布時はコード署名を検討してください（現在の CI では行っていません）。

詳細はプロジェクトルートの README.md も参照してください。
