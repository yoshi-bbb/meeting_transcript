# Linux 版 実行ファイルの使い方（エンドユーザー向け）

このドキュメントでは、Linux で配布された Meeting Mojiokoshi 実行ファイル（バイナリ）を実行する方法を説明します。

## 入手方法
- GitHub Releases から最新の `MeetingMojiokoshi-*-linux-*.tar.gz` をダウンロード。
- またはソースから自分でビルドした `dist/MeetingMojiokoshi` を使用。

## 実行手順（基本）

1. tar.gz を任意のディレクトリに展開します。
   ```bash
   tar xzf MeetingMojiokoshi-0.2.0-linux-x86_64.tar.gz
   cd MeetingMojiokoshi-0.2.0-linux-x86_64   # または展開したフォルダ
   ```

2. 実行権限を付与（初回のみ必要）
   ```bash
   chmod +x MeetingMojiokoshi
   ```

3. 実行
   ```bash
   ./MeetingMojiokoshi
   ```

## System Tray（タスクトレイ）機能

アプリをバックグラウンドで動作させたい場合に便利です。

- メインウィンドウを閉じると、自動的にシステムトレイ（通知領域）に最小化されます。アプリは終了せず、録音を継続できます。
- トレイアイコンを右クリックするとメニューが表示されます：
  - 「ウィンドウを開く」：メイン画面を表示
  - 「録音開始」：録音を開始（状態に応じて有効/無効）
  - 「停止して文字起こし」：録音を停止して文字起こし（状態に応じて有効/無効）
  - 「終了」：アプリを完全に終了
- トレイアイコンは常に表示されます（ウィンドウを開いていてもOK）。
- 録音中はトレイから素早く操作可能で、デスクトップをすっきり保てます。

**注意**: 一部のLinuxデスクトップ環境（特にGNOME）では、トレイ表示に追加のシステムパッケージ（例: libayatana-appindicator 系）が必要な場合があります。表示されない場合はディストリビューションのパッケージマネージャでインストールを試してください。

## より使いやすくする（推奨）

配布パッケージには `MeetingMojiokoshi.desktop` ファイルが同梱されています。

### アプリメニューに登録して起動しやすくする
1. 展開したフォルダ全体を好きな場所に置きます（例: `~/.local/share/MeetingMojiokoshi/`）。
2. `MeetingMojiokoshi.desktop` を `~/.local/share/applications/` にコピー。
3. テキストエディタで `.desktop` ファイルを開き、`Exec=` の行を実際のバイナリパスに修正：
   ```
   Exec=/home/あなたのユーザ名/.local/share/MeetingMojiokoshi/MeetingMojiokoshi
   ```
4. デスクトップデータベースを更新:
   ```bash
   update-desktop-database ~/.local/share/applications
   ```

これでアプリメニューに「Meeting Mojiokoshi」が表示され、検索やドックへのピン留めが可能になります。

### 直接ダブルクリックで起動したい場合
- ファイルマネージャー（Nautilus, Dolphin, Thunar など）でバイナリを右クリック → 「プロパティ」→「アクセス権」→「プログラムとして実行を許可する」にチェックを入れる（ディストリビューションにより表示が異なります）。
- 一部の環境では右クリックメニューに「実行」または「開く」が出る場合があります。

## 注意点
- 初回は「モデル準備」で Whisper モデルをダウンロードします（インターネット接続が必要）。
- 録音には参加者の同意を必ず得てください。
- 音声デバイス（PulseAudio / PipeWire の monitor source など）の選択が必要です。詳細は同梱 README.md を参照。
- アンインストール時は展開したフォルダを削除するだけです（設定ファイルは `~/.config/MeetingMojiokoshi/` などに残る場合があります）。

## トラブルシューティング
- 「Permission denied」: `chmod +x` を実行。
- 音声デバイスが見えない: `pavucontrol` などで monitor ソースを確認。
- GUI が出ない: 必要なライブラリ（libxcb-cursor0 など）が不足している可能性があります。ディストリビューションのパッケージマネージャでインストールを試してください。

詳細は同梱の README.md も参照してください。
