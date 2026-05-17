# PlayCue

[日本語](README.md) | [English](README.en.md)

PlayCueは、ゲーム配信・録画者向けの軽量Windowsウィジェットです。  
PCゲームの起動、プレイ時間の記録、攻略リンクの表示、  
OBS録画開始・停止を一画面で管理できます。

ゲームを選んで起動するだけで自動でOBSの録画が開始され  
「いつ、どのゲームを、どれくらいの時間遊んだか」をプレイ履歴を残せます。

## 主な機能

- 登録したゲームをウィジェットから起動
- ゲームごとのプレイ時間を自動記録
- 最後に遊んだゲームを上に表示
- 攻略サイト、メモ、スプレッドシートなどのリンクをゲームごとに表示
- OBS Studioの起動、録画開始、録画停止を自動化
- ゲーム終了時にOBS録画を自動停止
- ウィジェット最小化時にタスクトレイへ常駐
- PC起動時に自動起動する設定

## 必要なもの

- Windows
- Python 3.11以上
- OBS連携を使う場合: OBS Studio

## ダウンロード

1. GitHubのページで `Code` -> `Download ZIP` を選びます。
2. ZIPファイルを好きな場所に展開します。
3. 展開したフォルダを開きます。

## 初回セットアップ

PowerShellでこのフォルダを開き、次を実行します。

```powershell
python -m pip install -r requirements.txt
```

## 起動方法

```powershell
python PlayCue.py
```

初回起動時に管理者権限の確認が出る場合があります。ゲーム起動やOBS連携に必要なため、許可してください。

## ゲームを追加する

1. ウィジェット上部の `設定` を開きます。
2. `ゲーム追加` を選びます。
3. `ゲーム名` を入力します。
4. `ゲームexeパス` の `参照` からゲームの `.exe` を選びます。
5. 必要なら攻略サイトやメモのリンクを追加します。
6. `作成` を押します。

作成したゲームは、すぐにゲーム一覧へ追加されます。

## OBS録画を使う

OBSの録画を自動化したい場合だけ設定してください。

1. OBS Studioを起動します。
2. OBSの `ツール` -> `WebSocketサーバー設定` を開きます。
3. WebSocketサーバーを有効にします。
4. ウィジェットの `設定` -> `OBS設定` を開きます。
5. OBSのexeパス、ポート、パスワードを入力します。
6. `設定更新` を押します。

ゲーム起動時に録画を開始し、ゲーム終了時に録画を停止できます。

## プレイ時間ログ

プレイ履歴は `logs/play_history.csv` に保存されます。

このファイルにはあなたのプレイ履歴が入るため、GitHubへ公開しないでください。このリポジトリでは `.gitignore` で公開対象から外しています。

## GitHubで公開するときの注意

公開してよいもの:

- `PlayCue.py`
- `requirements.txt`
- `README.md`
- `README.en.md`
- `configs/example.json`
- `shorts_agent/`
- `tests/`

公開しないもの:

- `configs/*.json` の個人設定
- `logs/*.csv` のプレイ履歴
- `launchers/*.bat`
- `outputs/`
- OBS WebSocketパスワード
- 自分のPCだけで使うローカルパス

## 動作確認

公開前に次を実行してください。

```powershell
python -m py_compile PlayCue.py
python -m unittest discover -s tests
```

## ライセンス

MIT Licenseです。詳細は [LICENSE](LICENSE) を確認してください。

## exe化したい場合

Pythonを入れていない人に配布したい場合は、PyInstallerでexe化できます。

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed PlayCue.py
```

作成したexeと同じ場所に `configs` フォルダを置いてください。
