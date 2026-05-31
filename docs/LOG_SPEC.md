# PlayCue ログ仕様書

## 参照日

2026-05-25

## 1. このドキュメントの目的

このドキュメントは、PlayCue のログ出力仕様を定義する。

目的は以下。

- `logs/` 配下の役割を明確にする
- プレイ履歴CSVの保存形式を定義する
- Codex がログ関連の Issue を安全に実装できるようにする
- 個人のプレイ履歴やローカルパスが GitHub に混入することを防ぐ
- 将来的なプレイ履歴分析や録画セッション管理に備える

## 2. 基本方針

PlayCue のログは、ユーザーの個人利用履歴である。

そのため、ログファイルは Git 管理しない。

GitHub に含めてよいのは、ログ仕様書、テスト用ダミーデータ、または個人情報を含まないサンプルのみである。

## 3. ディレクトリ方針

```text
logs/
├─ play_history.csv
└─ *.log
```

| ファイル | 役割 | Git管理 |
|---|---|---|
| `logs/play_history.csv` | プレイ履歴 | 不可 |
| `logs/*.csv` | 各種CSVログ | 不可 |
| `logs/*.log` | 実行ログ | 不可 |
| `tests/fixtures/*.csv` | テスト用ダミーデータ | 可 |

## 4. `.gitignore` ルール

最低限、以下を `.gitignore` に含める。

```gitignore
# Logs
logs/*.csv
logs/*.log
```

既に追跡されているログがある場合は、以下を実行する。

```bash
git rm --cached logs/play_history.csv
git commit -m "Remove play history log from tracking"
```

## 5. ログ種別

| ログ | 内容 | 優先度 |
|---|---|---:|
| プレイ履歴ログ | ゲーム開始・終了・プレイ時間を記録 | 高 |
| アプリ実行ログ | 起動、設定読み込み、エラー等を記録 | 中 |
| OBS連携ログ | OBS接続、録画開始、録画停止を記録 | 中 |
| デバッグログ | 開発中の調査用 | 低 |

初期段階では、プレイ履歴ログを最優先で安定化する。

## 6. プレイ履歴CSV仕様

## 6.1 保存先

標準保存先は以下。

```text
logs/play_history.csv
```

設定ファイルで変更できる場合も、デフォルトはこのパスとする。

## 6.2 エンコーディング

推奨:

```text
UTF-8 with BOM なし
```

ただし、Excelでの閲覧性を優先する場合は UTF-8 with BOM を検討してよい。

どちらを採用するかは、専用Issueで決定する。

## 6.3 改行コード

Windows利用が前提のため、CSV出力時はPythonの `newline=""` を使い、CSVライブラリに任せることを推奨する。

## 6.4 推奨カラム

```csv
session_id,game_id,game_name,process_name,start_time,end_time,duration_seconds,duration_minutes,obs_recording_started,obs_recording_stopped,error
```

| カラム | 型 | 内容 |
|---|---|---|
| `session_id` | string | プレイセッション識別子 |
| `game_id` | string | 設定上のゲームID |
| `game_name` | string | 表示用ゲーム名 |
| `process_name` | string | 監視対象プロセス名 |
| `start_time` | string | ISO 8601形式の開始時刻 |
| `end_time` | string | ISO 8601形式の終了時刻 |
| `duration_seconds` | number | プレイ秒数 |
| `duration_minutes` | number | プレイ分数 |
| `obs_recording_started` | boolean | OBS録画開始を試みたか |
| `obs_recording_stopped` | boolean | OBS録画停止を試みたか |
| `error` | string | セッション中のエラー概要 |

## 7. 時刻仕様

時刻は、ローカルタイムで保存する。

推奨形式:

```text
YYYY-MM-DDTHH:MM:SS
```

例:

```text
2026-05-25T21:30:00
```

将来的にタイムゾーンを含める場合は、専用 Issue で扱う。

## 8. プレイ時間計算

基本方針:

```text
duration_seconds = end_time - start_time
duration_minutes = duration_seconds / 60
```

注意:

- マイナス値になった場合はログ破損として扱う
- 秒数を主データとし、分数は表示・集計用とする
- 丸め方はUI表示側で行う
- CSVには可能な限り生データを残す

## 9. ログ出力タイミング

プレイ履歴は、原則としてゲーム終了時に1行追記する。

```text
ゲーム開始
↓
start_time を保持
↓
ゲーム終了
↓
end_time を取得
↓
duration を計算
↓
CSV に1行追記
```

ゲーム開始時点では、未完了セッションをファイルへ書かない方針を基本とする。

ただし、クラッシュ対策として未完了セッション保存を導入する場合は、別Issueで扱う。

## 10. ログファイルが存在しない場合

`logs/play_history.csv` が存在しない場合は、自動作成する。

作成時にはヘッダー行を書き込む。

想定ヘッダー:

```csv
session_id,game_id,game_name,process_name,start_time,end_time,duration_seconds,duration_minutes,obs_recording_started,obs_recording_stopped,error
```

## 11. ログ書き込み失敗時の挙動

| 状況 | 推奨挙動 |
|---|---|
| `logs/` が存在しない | 自動作成する |
| CSVが存在しない | ヘッダー付きで作成する |
| 書き込み権限がない | エラー表示し、アプリ全体は落とさない |
| ファイルがロックされている | エラー表示し、次回再試行可能にする |
| カラム不一致 | 互換性方針に従い、必要なら新規ファイル作成を検討 |

## 12. ログに出してはいけない情報

以下はログに出力しない。

- OBS WebSocket パスワード
- 実在する詳細なローカル絶対パス
- APIキー
- トークン
- 非公開URL
- 個人情報
- スプレッドシートの非公開URL
- 設定ファイル全文

ログに出す場合は、必要に応じて伏せる。

例:

```text
C:\Users\...\Games\Example\game.exe
```

## 13. OBS関連ログ

OBS連携に関するログは、プレイ履歴CSVでは簡潔に扱う。

プレイ履歴CSVでは以下の程度に留める。

| カラム | 内容 |
|---|---|
| `obs_recording_started` | 録画開始を試みたか |
| `obs_recording_stopped` | 録画停止を試みたか |
| `error` | エラー概要 |

詳細なOBS接続ログを残す場合は、別ファイルとし、パスワードを含めない。

## 14. 互換性方針

ログ形式は、できるだけ破壊的に変更しない。

カラム追加は原則として末尾に追加する。

既存カラムの削除・名前変更は、専用Issueで扱う。

方針:

- 既存CSVを読めるようにする
- カラム追加は後方互換を維持する
- ログ形式変更時は `docs/LOG_SPEC.md` を更新する
- 必要ならログ移行スクリプトを別Issueで作る

## 15. テスト方針

ログ関連では、以下のテストを追加する。

| テスト | 内容 |
|---|---|
| 初回作成 | `logs/play_history.csv` がない場合に作成される |
| ヘッダー出力 | 初回作成時にヘッダーが出る |
| 1行追記 | プレイセッション終了時に1行追記される |
| 時間計算 | 秒数・分数が正しい |
| OBS列 | OBS未使用でもCSV列が壊れない |
| 書き込み失敗 | 書き込み不能時にアプリ全体が落ちない |
| 秘密情報 | パスワードや実パスがログに出ない |

## 16. Codex 実装時の注意

Codex はログ関連の実装で以下を守る。

- `logs/*.csv` をコミットしない
- `logs/*.log` をコミットしない
- テストには `tests/fixtures/` などのダミーデータを使う
- 実ゲーム名や実プレイ履歴を含めない
- OBS パスワードをログに出さない
- CSVカラム変更は必ず仕様書とセットで行う
- ログ変更とUI大改修を同じPRに混ぜない

## 17. 結論

PlayCue のログは、ユーザーの個人履歴であるため、公開してはいけない。

最重要ルールは以下。

1. `logs/*.csv` と `logs/*.log` は Git 管理しない
2. プレイ履歴CSVの形式を固定する
3. ログファイルがなくても安全に作成する
4. 書き込み失敗でアプリ全体を落とさない
5. OBSパスワード、非公開URL、個人情報をログに出さない
