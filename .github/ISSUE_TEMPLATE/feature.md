---
name: Feature request
about: PlayCue に新機能を追加するための Issue
title: "[Feature]: "
labels: ["type: feature", "needs-spec"]
assignees: ""
---

# Feature: <!-- 機能名を短く書く -->

## 1. 目的

<!--
この機能で何を実現したいかを書く。
例:
- ゲームごとのメモを編集できるようにする
- OBS 接続状態を UI に表示する
- プレイ履歴をゲーム別に集計できるようにする
-->

## 2. 背景

<!--
なぜこの機能が必要かを書く。
現状の不便な点、リニューアル計画上の位置づけ、関連する既存機能を書く。
-->

## 3. 対象ユーザー

<!--
誰のための機能かを書く。
例:
- 自分用
- ゲーム配信者
- 録画しながらゲームを遊ぶユーザー
- PlayCue の開発者
-->

## 4. 作業内容

<!--
Codex が実装する具体的な作業を書く。
1 Issue = 1 PR で完了できる粒度にする。
-->

- [ ] 
- [ ] 
- [ ] 

## 5. 変更対象

<!--
想定される変更ファイルを書く。
不明な場合は「Codex が既存構成を確認して最小変更で対応」と書く。
-->

想定ファイル:

```text
PlayCue.py
tests/
docs/
```

新規作成する可能性があるファイル:

```text
<!-- 例: playcue/config/loader.py -->
```

## 6. 変更してはいけないもの

<!--
この Issue で触ってはいけないものを書く。
特に個人設定、ログ、秘密情報に注意する。
-->

- [ ] 個人用 `configs/*.json` を追加・変更・コミットしない
- [ ] `logs/*.csv` を追加・変更・コミットしない
- [ ] OBS WebSocket パスワードをコード、README、テスト、ログに書かない
- [ ] 実在するローカル PC の絶対パスを書かない
- [ ] 非公開 URL、API キー、個人情報を書かない
- [ ] Issue に書かれていない機能を追加しない
- [ ] 大規模リファクタを同じ PR に混ぜない

## 7. 仕様

<!--
機能の仕様を具体的に書く。
未確定の場合は「未確定」と書き、needs-spec ラベルを残す。
-->

### 7.1 基本動作

- 

### 7.2 UI 仕様

<!-- UI に関係しない場合は「UI 変更なし」と書く。 -->

- 

### 7.3 設定仕様

<!-- 設定ファイルに関係しない場合は「設定変更なし」と書く。 -->

- 

### 7.4 ログ仕様

<!-- ログに関係しない場合は「ログ変更なし」と書く。 -->

- 

### 7.5 OBS 連携仕様

<!-- OBS に関係しない場合は「OBS 変更なし」と書く。 -->

- 

## 8. 受け入れ条件

<!--
この Issue が完了したと判断できる条件を書く。
Codex が迷わないよう、確認可能な条件にする。
-->

- [ ] 
- [ ] 
- [ ] 既存の起動方法 `python PlayCue.py` が維持されている
- [ ] 既存機能が壊れていない
- [ ] 個人設定ファイル、ログ、OBS パスワード、ローカルパスが含まれていない

## 9. 検証コマンド

<!--
Codex が実行すべき検証コマンドを書く。
実行できないものがある場合は、PR に理由を書く。
-->

```bash
python -m py_compile PlayCue.py
python -m unittest discover -s tests
```

追加で必要な検証があれば書く。

```bash
# 例:
# python -m pip install -r requirements.txt
```

## 10. 手動確認項目

<!--
OBS、実ゲーム起動、Windows タスクトレイなど、Codex だけでは確認しにくい項目を書く。
不要な場合は「なし」と書く。
-->

- [ ] アプリが起動する
- [ ] ゲームを起動できる
- [ ] プレイ時間が記録される
- [ ] OBS 未設定でもアプリが落ちない
- [ ] OBS 設定済みの場合、録画開始・停止に問題がない
- [ ] タスクトレイ最小化に問題がない

## 11. 影響範囲

<!--
この機能が影響する領域にチェックを入れる。
-->

- [ ] UI
- [ ] 設定ファイル
- [ ] ゲーム起動
- [ ] プレイ時間記録
- [ ] ログ出力
- [ ] OBS 連携
- [ ] タスクトレイ
- [ ] 自動起動
- [ ] テスト
- [ ] ドキュメント
- [ ] 配布・exe 化
- [ ] セキュリティ

## 12. 関連ドキュメント

<!--
関連する docs を残す。
存在しない場合は、今後作成予定として扱う。
-->

- `docs/RENEWAL_PLAN.md`
- `docs/CODEX_GUIDE.md`
- `docs/CURRENT_STRUCTURE.md`
- `docs/CONFIG_SPEC.md`
- `docs/LOG_SPEC.md`
- `docs/OBS_SPEC.md`
- `docs/REGRESSION_TEST_V0_2.md`

## 13. 関連 Issue / PR

<!--
関連する Issue や PR があれば書く。
-->

- Related: #
- Depends on: #
- Blocks: #

## 14. Codex への実装指示

<!--
Codex にそのまま渡す前提の指示。
必要に応じて編集する。
-->

この Issue を実装してください。

条件:

- Issue 本文の範囲だけ対応する
- 仕様外の機能追加はしない
- 既存機能を壊さない
- 個人設定、ログ、OBS パスワード、ローカルパスをコミットしない
- 変更は 1 PR でレビューできる粒度にする
- 可能な検証コマンドを実行する
- 実行できなかった検証は、理由を PR 本文に書く
- 変更内容、変更ファイル、検証結果、影響範囲、残課題を PR 本文に書く

## 15. ラベル

<!--
Issue 作成後、必要に応じて labels を調整する。
needs-spec が不要になったら外し、codex-ready を付ける。
-->

推奨ラベル:

- `type: feature`
- `needs-spec`

仕様確定後に追加:

- `codex-ready`

必要に応じて追加:

- `area: ui`
- `area: config`
- `area: launcher`
- `area: tracking`
- `area: logs`
- `area: obs`
- `area: tray`
- `area: startup`
- `area: packaging`
- `area: security`
- `priority: high`
- `priority: medium`
- `priority: low`
- `needs-human-check`
- `regression-risk`
