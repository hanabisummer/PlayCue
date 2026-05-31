# PlayCue OBS 連携仕様書

## 参照日

2026-05-25

## 1. このドキュメントの目的

このドキュメントは、PlayCue の OBS Studio 連携仕様を定義する。

目的は以下。

- OBS 連携の責務を明確にする
- OBS 未設定時でも PlayCue が安全に動作するようにする
- OBS WebSocket パスワードの混入を防ぐ
- 録画開始・停止の条件を明文化する
- Codex が OBS 関連 Issue を安全に実装できるようにする

## 2. 基本方針

OBS 連携は PlayCue の便利機能であり、必須機能ではない。

そのため、OBS が未設定・未起動・接続失敗の状態でも、PlayCue 本体は起動し、ゲーム起動・プレイ時間記録などの基本機能を継続できる必要がある。

## 3. OBS 連携の対象

PlayCue が扱う OBS 連携は以下。

| 機能 | 内容 |
|---|---|
| OBS起動 | OBS Studio の実行ファイルを起動する |
| OBS接続 | OBS WebSocket に接続する |
| 録画開始 | ゲーム開始時に録画開始する |
| 録画停止 | ゲーム終了時に録画停止する |
| 状態表示 | OBS接続状態・録画状態をUIに表示する |
| エラー表示 | 接続失敗・録画失敗を分かりやすく表示する |

## 4. OBS 連携の前提

| 項目 | 内容 |
|---|---|
| OBS Studio | ユーザーが別途インストールする |
| OBS WebSocket | OBS Studio 側で有効化する |
| host | 通常 `127.0.0.1` |
| port | 通常 `4455` |
| password | ユーザーのローカル設定でのみ保持する |
| PlayCue側 | OBS未使用でも起動できる |

## 5. 設定項目

OBS設定は `configs/*.json` に保存される想定。

推奨構造:

```json
{
  "obs": {
    "enabled": false,
    "auto_launch": false,
    "executable_path": "C:\\Path\\To\\OBS\\obs64.exe",
    "websocket_host": "127.0.0.1",
    "websocket_port": 4455,
    "websocket_password": "CHANGE_ME",
    "auto_start_recording": false,
    "auto_stop_recording": false
  }
}
```

## 6. 設定項目仕様

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `enabled` | boolean | 任意 | OBS連携を使うか |
| `auto_launch` | boolean | 任意 | PlayCueからOBSを起動するか |
| `executable_path` | string | 任意 | OBS実行ファイルパス |
| `websocket_host` | string | 任意 | OBS WebSocket host |
| `websocket_port` | number | 任意 | OBS WebSocket port |
| `websocket_password` | string | 任意 | OBS WebSocket password |
| `auto_start_recording` | boolean | 任意 | ゲーム開始時に録画開始するか |
| `auto_stop_recording` | boolean | 任意 | ゲーム終了時に録画停止するか |

## 7. 秘密情報ルール

OBS WebSocket パスワードは秘密情報として扱う。

以下に実値を書いてはいけない。

- Git管理ファイル
- README
- docs
- tests
- logs
- GitHub Issue
- Pull Request本文
- GitHub Actionsログ

サンプル値は必ず以下を使う。

```text
CHANGE_ME
```

## 8. 状態定義

OBS 連携では、以下の状態を扱う。

| 状態 | 内容 |
|---|---|
| `disabled` | OBS連携が無効 |
| `not_configured` | OBS設定が不足 |
| `not_running` | OBSが起動していない |
| `launching` | OBS起動中 |
| `connecting` | WebSocket接続中 |
| `connected` | WebSocket接続済み |
| `recording` | 録画中 |
| `error` | 接続または録画制御エラー |

UIでは、少なくとも「未使用」「未接続」「接続済み」「録画中」「エラー」が分かればよい。

## 9. OBS起動仕様

## 9.1 起動条件

OBSをPlayCueから起動する条件。

- `obs.enabled` が `true`
- `obs.auto_launch` が `true`
- `obs.executable_path` が設定されている
- 指定パスが存在する

## 9.2 起動失敗時

| 状況 | 挙動 |
|---|---|
| exeパス未設定 | OBS起動をスキップし、警告表示 |
| exeパス不存在 | OBS起動をスキップし、警告表示 |
| 起動失敗 | エラー表示し、PlayCue本体は継続 |
| 既に起動済み | 二重起動しない |

## 10. OBS WebSocket 接続仕様

## 10.1 接続条件

WebSocket接続を試みる条件。

- `obs.enabled` が `true`
- host と port が設定されている
- OBS が起動している、または接続可能である

## 10.2 接続失敗時

接続失敗しても、PlayCue本体は落とさない。

推奨挙動:

- UIに「OBS未接続」または「OBS接続失敗」を表示
- ゲーム起動は継続
- プレイ時間記録は継続
- 録画開始・停止だけスキップ

## 11. 録画開始仕様

## 11.1 録画開始条件

録画開始を試みる条件。

- `obs.enabled` が `true`
- `obs.auto_start_recording` が `true`
- OBS WebSocket に接続済み
- ゲームプロセス開始を検知した
- OBS が録画可能状態である

## 11.2 すでに録画中の場合

すでに録画中の場合は、二重に録画開始しない。

推奨挙動:

- 録画開始処理をスキップ
- 状態は `recording` とする
- 必要ならログに「already recording」と記録する

## 11.3 録画開始失敗時

録画開始に失敗しても、ゲーム起動とプレイ時間記録は継続する。

推奨挙動:

- UIに録画開始失敗を表示
- プレイ履歴ログの `error` に概要を記録
- パスワードや接続詳細をログに出さない

## 12. 録画停止仕様

## 12.1 録画停止条件

録画停止を試みる条件。

- `obs.enabled` が `true`
- `obs.auto_stop_recording` が `true`
- OBS WebSocket に接続済み
- ゲームプロセス終了を検知した
- OBS が録画中である

## 12.2 録画中でない場合

録画中でない場合は、停止処理をスキップする。

## 12.3 録画停止失敗時

録画停止に失敗しても、PlayCue本体は落とさない。

推奨挙動:

- UIに録画停止失敗を表示
- プレイ履歴ログの `error` に概要を記録
- 人間がOBS側で確認できるようにする

## 13. ゲーム起動との関係

OBS 連携は、ゲーム起動処理に対して補助的に動作する。

```text
ゲーム起動
↓
ゲームプロセス検知
↓
OBS録画開始を試行
↓
ゲーム終了検知
↓
OBS録画停止を試行
↓
プレイ履歴保存
```

OBS処理に失敗しても、ゲーム起動とプレイ履歴保存は継続する。

## 14. ログ出力方針

OBS関連情報は、プレイ履歴CSVでは簡潔に扱う。

推奨カラム:

```csv
obs_recording_started,obs_recording_stopped,error
```

詳細ログを作る場合も、以下を出力しない。

- WebSocket password
- 接続URLに含まれる秘密情報
- 設定ファイル全文
- 実在する詳細ローカルパス

## 15. UI表示方針

最低限、以下を表示できるようにする。

| 表示 | 内容 |
|---|---|
| OBS未使用 | OBS連携が無効 |
| OBS未接続 | OBS連携有効だが接続なし |
| OBS接続済み | 接続成功 |
| 録画中 | 録画中 |
| OBSエラー | 接続・録画制御に失敗 |

UI改善は専用Issueで行う。

OBS内部処理のリファクタとUI大改修を同じPRに混ぜない。

## 16. テスト方針

OBS実機を使わないテストを優先する。

| テスト | 内容 |
|---|---|
| OBS無効 | `enabled=false` で何もしない |
| 設定不足 | host/port/password不足で安全にスキップ |
| 接続失敗 | 接続失敗時にアプリが落ちない |
| 録画開始スキップ | 未接続時に録画開始しない |
| 録画停止スキップ | 未接続時に録画停止しない |
| パスワード保護 | ログやエラーにpasswordが出ない |

OBS実機テストは手動確認項目とする。

## 17. 手動確認項目

OBS関連PRでは、必要に応じて以下を確認する。

- [ ] OBS未設定でPlayCueが起動する
- [ ] OBS無効設定でゲーム起動できる
- [ ] OBS起動済みで接続できる
- [ ] ゲーム開始時に録画開始できる
- [ ] ゲーム終了時に録画停止できる
- [ ] すでに録画中の場合に二重開始しない
- [ ] 接続失敗時にPlayCue本体が落ちない
- [ ] OBSパスワードがログに出ない

## 18. Codex 実装時の注意

Codex は OBS 関連の実装で以下を守る。

- OBS パスワードの実値を書かない
- OBS 未設定でもアプリが落ちないようにする
- OBS接続失敗をアプリ全体の失敗にしない
- 実機確認できない場合はPRに未検証と書く
- OBS変更とUI大改修を同じPRに混ぜない
- OBS変更とログ形式変更を同じPRに混ぜない
- テストではモックやダミー設定を使う

## 19. 結論

OBS 連携は PlayCue の重要機能だが、必須機能ではない。

最重要ルールは以下。

1. OBS未設定でもPlayCue本体を起動できる
2. OBS接続失敗でもゲーム起動・プレイ時間記録を継続する
3. OBSパスワードをGitHub、ログ、テスト、READMEに出さない
4. 録画開始・停止の失敗を分かりやすく表示する
5. 実機確認が必要な項目は `needs-human-check` として扱う
