# PlayCue 設定ファイル仕様書

## 参照日

2026-05-25

## 1. このドキュメントの目的

このドキュメントは、PlayCue の設定ファイル仕様を定義する。

目的は以下。

- `configs/` 配下の役割を明確にする
- 公開してよい設定ファイルと公開してはいけない設定ファイルを区別する
- Codex が設定関連の Issue を安全に実装できるようにする
- 既存設定との互換性を壊さずにリニューアルを進める
- OBS WebSocket パスワード、ゲームパス、非公開URLなどの秘密情報混入を防ぐ

## 2. 基本方針

PlayCue の設定ファイルは、ローカルPC上でのみ使用する個人設定である。

そのため、原則として実運用用の `configs/*.json` は Git 管理しない。

Git 管理してよいのは、ダミー値のみを含むサンプル設定ファイルである。

## 3. ディレクトリ方針

```text
configs/
├─ example.json
└─ *.json
```

| ファイル | 役割 | Git管理 |
|---|---|---|
| `configs/example.json` | 公開用サンプル設定 | 可 |
| `configs/*.example.json` | 公開用サンプル設定 | 可 |
| `configs/*.json` | 個人用設定 | 不可 |

## 4. `.gitignore` ルール

最低限、以下を `.gitignore` に含める。

```gitignore
# Personal configs
configs/*.json
!configs/example.json
!configs/*.example.json
```

注意:

すでに Git 管理されている個人設定ファイルは、`.gitignore` に追加しても自動では除外されない。

既に追跡されている場合は、以下を実行する。

```bash
git rm --cached configs/your_config.json
git commit -m "Remove personal config from tracking"
```

## 5. 設定ファイルに含まれる情報

PlayCue の設定ファイルは、以下の情報を扱う可能性がある。

| 種類 | 内容 | 公開可否 |
|---|---|---|
| ゲーム名 | 表示用ゲーム名 | ダミーなら可 |
| ゲームexeパス | 実行ファイルの絶対パス | 不可 |
| プロセス名 | 監視対象プロセス名 | ダミーなら可 |
| 攻略リンク | 攻略サイト、メモ、スプレッドシート等 | 非公開URLは不可 |
| OBS設定 | host、port、password等 | passwordは不可 |
| 自動起動設定 | PC起動時の挙動 | 可 |
| UI設定 | ウィンドウ位置、表示設定等 | 個人環境依存なら不可 |

## 6. 推奨設定構造

今後の安定化に向け、以下の構造を推奨する。

```json
{
  "version": 1,
  "games": [
    {
      "id": "example-game",
      "display_name": "Example Game",
      "executable_path": "C:\\Path\\To\\Game\\game.exe",
      "process_name": "game.exe",
      "launch_args": [],
      "working_directory": "C:\\Path\\To\\Game",
      "links": [
        {
          "label": "Official Site",
          "url": "https://example.com"
        }
      ],
      "memo": "Sample memo",
      "tags": ["sample"],
      "enabled": true
    }
  ],
  "obs": {
    "enabled": false,
    "auto_launch": false,
    "executable_path": "C:\\Path\\To\\OBS\\obs64.exe",
    "websocket_host": "127.0.0.1",
    "websocket_port": 4455,
    "websocket_password": "CHANGE_ME",
    "auto_start_recording": false,
    "auto_stop_recording": false
  },
  "app": {
    "start_minimized": false,
    "minimize_to_tray": true,
    "launch_on_startup": false
  },
  "logging": {
    "play_history_path": "logs/play_history.csv"
  }
}
```

## 7. 設定項目仕様

## 7.1 ルート項目

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `version` | number | 必須 | 設定ファイルのバージョン |
| `games` | array | 必須 | 登録ゲーム一覧 |
| `obs` | object | 任意 | OBS連携設定 |
| `app` | object | 任意 | アプリ全体設定 |
| `logging` | object | 任意 | ログ出力設定 |

## 7.2 `games[]`

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `id` | string | 必須 | ゲーム識別子 |
| `display_name` | string | 必須 | UI表示名 |
| `executable_path` | string | 必須 | ゲーム起動用exeパス |
| `process_name` | string | 必須 | 監視するプロセス名 |
| `launch_args` | array | 任意 | 起動引数 |
| `working_directory` | string | 任意 | 作業ディレクトリ |
| `links` | array | 任意 | 攻略リンク等 |
| `memo` | string | 任意 | メモ |
| `tags` | array | 任意 | 分類タグ |
| `enabled` | boolean | 任意 | 表示・起動対象にするか |

## 7.3 `games[].links[]`

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `label` | string | 必須 | UIに表示するリンク名 |
| `url` | string | 必須 | 開くURL |

注意:

非公開スプレッドシート、個人メモ、限定公開URLは公開用サンプルに含めない。

## 7.4 `obs`

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

注意:

`websocket_password` の実値は Git 管理しない。サンプルでは必ず `CHANGE_ME` を使う。

## 7.5 `app`

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `start_minimized` | boolean | 任意 | 起動時に最小化するか |
| `minimize_to_tray` | boolean | 任意 | 最小化時にタスクトレイへ入れるか |
| `launch_on_startup` | boolean | 任意 | PC起動時に自動起動するか |

## 7.6 `logging`

| 項目 | 型 | 必須 | 内容 |
|---|---|---:|---|
| `play_history_path` | string | 任意 | プレイ履歴CSVの保存先 |

## 8. バリデーション方針

設定読み込み時は、以下を検証する。

| チェック | 方針 |
|---|---|
| JSONとして読めるか | 読めない場合はユーザーに分かるエラーを出す |
| `version` があるか | なければ旧形式として扱うか、デフォルト補完する |
| `games` が配列か | 不正なら空配列として扱うか、エラー表示する |
| `display_name` が空でないか | 空なら対象ゲームを無効扱いにする |
| `executable_path` が空でないか | 空なら起動不可としてUIに表示する |
| `process_name` が空でないか | 空なら監視不可として扱う |
| OBS設定が不完全でないか | OBS無効扱い、または明示的に警告する |
| ログ保存先が書き込み可能か | 書き込み失敗時にエラー表示する |

## 9. 読み込み失敗時の挙動

| 状況 | 推奨挙動 |
|---|---|
| 設定ファイルが存在しない | 初期状態で起動し、設定作成を促す |
| JSONが壊れている | アプリ全体を落とさず、エラーを表示する |
| ゲーム設定が不正 | 該当ゲームのみ無効扱いにする |
| OBS設定が不正 | OBS連携のみ無効扱いにする |
| ログパスが不正 | デフォルト `logs/play_history.csv` にフォールバックする |

## 10. 互換性方針

既存の設定形式がある場合は、リニューアル時にいきなり破壊しない。

方針:

- 既存形式を読み込めるようにする
- 新形式への移行は専用 Issue で行う
- 移行前にバックアップを作る
- 設定ファイルのバージョンを持つ
- 破壊的変更は `docs/CONFIG_SPEC.md` を更新してから行う

## 11. Codex 実装時の注意

Codex は設定関連の実装で以下を守る。

- 個人用 `configs/*.json` をコミットしない
- `configs/example.json` にはダミー値のみ書く
- 実在する `C:\Users\...` パスを書かない
- OBS WebSocket パスワードの実値を書かない
- 既存設定を読めなくしない
- 設定読み込み失敗でアプリ全体を落とさない
- 設定変更とUI大改修を同じPRに混ぜない

## 12. テスト方針

設定関連では、以下のテストを追加する。

| テスト | 内容 |
|---|---|
| サンプル設定読み込み | `configs/example.json` が読み込める |
| 設定ファイルなし | 設定なしでもアプリが落ちない |
| JSON破損 | 壊れたJSONで安全にエラーになる |
| OBS無効 | OBS設定なしでも起動できる |
| ゲーム設定不備 | 不正ゲームが全体を壊さない |
| ダミーパス | 実在パスに依存しない |

## 13. 結論

設定ファイルは PlayCue の個人環境に強く依存するため、公開版・開発版を問わず慎重に扱う。

最重要ルールは以下。

1. 実運用の `configs/*.json` は Git 管理しない
2. 公開するのは `configs/example.json` だけにする
3. OBS パスワード、実ゲームパス、非公開URLを含めない
4. 設定不備でアプリ全体を落とさない
5. 既存設定との互換性を維持する
