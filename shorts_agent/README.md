# AI Game Shorts Agent

録画済みゲーム動画から、音量ピークを使って約60秒のショート動画、台本、VOICEVOXずんだもん音声、字幕、完成動画を生成するCLIエージェントです。

## 元動画保護

元動画は読み取り専用入力として扱います。出力は必ず `outputs/` 以下に作成し、処理前後で元動画のサイズとSHA-256を比較します。元動画の削除、移動、上書き、同一パス出力は行いません。

## 必要ソフト

- Python 3.11以上
- FFmpeg / FFprobe
- VOICEVOX ENGINE（音声生成を使う場合）

## セットアップ

```powershell
pip install -r shorts_agent\requirements.txt
```

FFmpegは公式ビルドを導入し、`ffmpeg` と `ffprobe` をPATHへ追加してください。VOICEVOXはENGINEを起動し、既定では `http://127.0.0.1:50021` に接続します。

## 実行例

ドライラン:

```powershell
python shorts_agent\main.py --config shorts_agent\config.example.json --dry-run
```

動画を直接指定:

```powershell
python shorts_agent\main.py --input "D:\Videos\recordings\sample.mkv"
```

ステージ指定:

```powershell
python shorts_agent\main.py --input "D:\Videos\recordings\sample.mkv" --stage detect
python shorts_agent\main.py --input "D:\Videos\recordings\sample.mkv" --stage all
```

## 出力

`outputs/<動画名>/` または既存フォルダがある場合は `outputs/<動画名>_02/` 以下に生成します。

- `source_info.json`: 元動画情報と処理前ハッシュ
- `processing_log.txt`: FFmpegログと処理ログ
- `candidates/volume_candidates.json`: 音量ピーク候補
- `clips/`: 横動画の切り出し
- `vertical/`: YouTube Shorts向け縦動画
- `scripts/`: 台本Markdown
- `voice/`: ずんだもんWAV
- `subtitles/`: SRT/ASS字幕
- `final/`: 音声・字幕付き完成動画
- `summary.json`: 生成結果と元動画保護確認

## よくあるエラー

- `ffmpeg が見つかりません`: FFmpegをPATHへ追加してください。
- `VOICEVOX未接続`: VOICEVOX ENGINEを起動してください。音声なしでも処理は継続します。
- `元動画のハッシュまたはサイズが変化しました`: 重大エラーです。処理中に別アプリが元動画を変更していないか確認してください。

