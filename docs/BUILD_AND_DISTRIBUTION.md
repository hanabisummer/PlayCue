# PlayCue exe 化・配布手順

Python がインストールされていないユーザーへ配布する場合の手順です。

---

## 自動ビルド（推奨）

`v*` タグを push すると GitHub Actions が自動で exe をビルドし、  
GitHub Releases に `PlayCue-<version>.zip` を添付します。

```powershell
git tag v1.0.0
git push origin v1.0.0
```

`.github/workflows/build-release.yml` がこの処理を担います。

---

## 手動ビルド

ローカルで exe を手動ビルドしたい場合の手順です。

**前提**

- Windows
- Python 3.11 以上
- PowerShell

**手順**

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name PlayCue PlayCue.py
```

ビルドが完了すると `dist/PlayCue.exe` が生成されます。

**オプション説明**

| オプション | 意味 |
|---|---|
| `--onefile` | 単一の exe ファイルにまとめる |
| `--windowed` | コンソールウィンドウを表示しない（GUI アプリ向け） |
| `--name PlayCue` | 出力ファイル名を `PlayCue.exe` にする |

---

## 配布パッケージの作成

```powershell
$tag = "v1.0.0"
$dist = "PlayCue-$tag"
New-Item -ItemType Directory -Force -Path $dist
Copy-Item dist\PlayCue.exe $dist\
Copy-Item README.md $dist\
Copy-Item README.en.md $dist\
Copy-Item LICENSE $dist\
New-Item -ItemType Directory -Force -Path $dist\configs
Copy-Item configs\example.json $dist\configs\
Compress-Archive -Path $dist\* -DestinationPath "PlayCue-$tag.zip"
```

---

## 配布物の確認

同梱してよいもの:

- `PlayCue.exe`
- `configs/example.json`（`configs/` フォルダごと）
- `README.md` / `README.en.md`
- `LICENSE`

同梱してはいけないもの:

- 個人用 `configs/*.json`（実ゲームパス・OBS パスワードが含まれる）
- `logs/*.csv`（プレイ履歴が含まれる）
- `launchers/*.bat`（実ローカルパスが含まれる可能性）
- `outputs/`（録画データ等が含まれる可能性）

---

## exe 版の動作確認

公開前に以下を実機で確認してください:

- [ ] `PlayCue.exe` をダブルクリックで起動できる
- [ ] `configs/example.json` を読み込める
- [ ] ゲーム設定を追加できる
- [ ] `logs/play_history.csv` にログが保存される
- [ ] OBS 未使用（`obs.enabled: false`）でも落ちない
- [ ] OBS 使用時に WebSocket 接続できる

---

## 注意事項

- PyInstaller でビルドした exe はウイルス対策ソフトに誤検知される場合があります。  
  ソースコードを公開しており問題ないことを README に記載しています。
- `pytesseract` のログインボーナス OCR 機能は、ユーザーが Tesseract OCR を別途インストールした場合のみ動作します。  
  未インストールでも起動・その他の機能には影響しません。
- exe 版では Python のインストールは不要ですが、`configs/` フォルダは exe と同じ場所に置く必要があります。

---

## 関連ドキュメント

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — 困ったときの対処法
