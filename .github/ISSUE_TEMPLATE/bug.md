---
name: Bug report
about: PlayCue の不具合を報告・修正するための Issue
title: "[Bug]: "
labels: ["type: bug", "needs-spec"]
assignees: ""
---

# Bug: <!-- 不具合名を短く書く -->

## 1. 概要

<!--
発生している不具合を短く書く。
例:
- OBS 未起動時に PlayCue が落ちる
- ゲーム終了後にプレイ時間が記録されない
- 設定ファイルがない状態で起動できない
-->

## 2. 発生環境

<!-- 分かる範囲で記載する。 -->

| 項目 | 内容 |
|---|---|
| OS | Windows  |
| Python |  |
| PlayCue version / branch |  |
| OBS Studio | 使用 / 未使用 |
| OBS WebSocket | 使用 / 未使用 |
| 実行方法 | `python PlayCue.py` / exe / その他 |

## 3. 再現手順

<!--
不具合を再現する手順を書く。
Codex が確認しやすいように、できるだけ具体的に書く。
-->

1. 
2. 
3. 

## 4. 期待する動作

<!--
本来どう動くべきかを書く。
-->

- 

## 5. 実際の動作

<!--
実際に何が起きたかを書く。
エラーメッセージがある場合は、秘密情報を除外して貼る。
-->

- 

## 6. エラーログ / スクリーンショット

<!--
ログやスクリーンショットがある場合は貼る。
ただし、以下は必ず削除する。

- OBS WebSocket パスワード
- 実在するローカル PC の絶対パス
- 個人のゲームパス
- 非公開 URL
- API キー
- 個人情報
-->

```text
<!-- ここにログを貼る。秘密情報は必ず伏せる。 -->
```

## 7. 影響範囲

<!-- 該当するものにチェックを入れる。 -->

- [ ] アプリ起動
- [ ] UI
- [ ] 設定ファイル
- [ ] ゲーム起動
- [ ] プレイ時間記録
- [ ] ログ出力
- [ ] OBS 連携
- [ ] タスクトレイ
- [ ] 自動起動
- [ ] exe 配布
- [ ] テスト
- [ ] ドキュメント
- [ ] セキュリティ

## 8. 原因の推測

<!--
分かる場合のみ書く。
分からない場合は「不明」でよい。
-->

- 

## 9. 修正方針

<!--
Codex に修正させる方針を書く。
未確定の場合は needs-spec ラベルを残す。
-->

- 

## 10. 作業内容

<!--
Codex が実装する具体的な修正作業を書く。
1 Issue = 1 PR で完了できる粒度にする。
-->

- [ ] 
- [ ] 
- [ ] 

## 11. 変更対象

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

## 12. 変更してはいけないもの

- [ ] 個人用 `configs/*.json` を追加・変更・コミットしない
- [ ] `logs/*.csv` を追加・変更・コミットしない
- [ ] OBS WebSocket パスワードをコード、README、テスト、ログに書かない
- [ ] 実在するローカル PC の絶対パスを書かない
- [ ] 非公開 URL、API キー、個人情報を書かない
- [ ] 不具合修正と無関係な機能追加をしない
- [ ] 大規模リファクタを同じ PR に混ぜない

## 13. 受け入れ条件

<!--
修正完了と判断できる条件を書く。
-->

- [ ] 再現手順で不具合が発生しない
- [ ] 期待する動作になっている
- [ ] 既存の起動方法 `python PlayCue.py` が維持されている
- [ ] 既存機能が壊れていない
- [ ] 個人設定ファイル、ログ、OBS パスワード、ローカルパスが含まれていない
- [ ] 必要に応じてテストが追加・更新されている

## 14. 検証コマンド

```bash
python -m py_compile PlayCue.py
python -m unittest discover -s tests
```

追加で必要な検証があれば書く。

```bash
# 例:
# python -m pip install -r requirements.txt
```

## 15. 手動確認項目

<!--
OBS、実ゲーム起動、Windows タスクトレイなど、Codex だけでは確認しにくい項目を書く。
不要な場合は「なし」と書く。
-->

- [ ] アプリが起動する
- [ ] 対象機能が正常に動く
- [ ] OBS 未設定でもアプリが落ちない
- [ ] OBS 設定済みの場合、録画開始・停止に問題がない
- [ ] タスクトレイ最小化に問題がない

## 16. 関連ドキュメント

- `docs/RENEWAL_PLAN.md`
- `docs/CODEX_GUIDE.md`
- `docs/CURRENT_STRUCTURE.md`
- `docs/CONFIG_SPEC.md`
- `docs/LOG_SPEC.md`
- `docs/OBS_SPEC.md`
- `docs/REGRESSION_TEST_V0_2.md`

## 17. 関連 Issue / PR

- Related: #
- Depends on: #
- Blocks: #

## 18. Codex への実装指示

この Issue を修正してください。

条件:

- Issue 本文の範囲だけ対応する
- 不具合修正と無関係な機能追加はしない
- 既存機能を壊さない
- 個人設定、ログ、OBS パスワード、ローカルパスをコミットしない
- 変更は 1 PR でレビューできる粒度にする
- 可能な検証コマンドを実行する
- 実行できなかった検証は、理由を PR 本文に書く
- 変更内容、変更ファイル、検証結果、影響範囲、残課題を PR 本文に書く

## 19. ラベル

推奨ラベル:

- `type: bug`
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
