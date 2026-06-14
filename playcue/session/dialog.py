"""終了時メモ入力ダイアログ（指示書 5.4 / 8.3）。

要件:
- キャンセル可能。キャンセル時も安全なデフォルト値を返す（result=unknown）。
- メモ未入力でもエラーにしない。長文メモでも落ちない。
- 入力値は dict で返す（``sessions`` テーブルのカラム名に対応）。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from playcue.ui import i18n

from .session import VALID_PRIVACY_LEVELS, VALID_RESULTS

RESULT_CHOICES = VALID_RESULTS
PRIVACY_CHOICES = VALID_PRIVACY_LEVELS

_LABELS = {
    "ja": {
        "title": "プレイ記録",
        "heading": "今回のプレイを記録しますか？（未入力でもOK）",
        "mode": "プレイモード",
        "build": "使用デッキ/ビルド",
        "result": "結果",
        "score": "スコア/報酬",
        "advice": "AI助言ID",
        "memo": "メモ",
        "privacy": "外部送信可否",
        "save": "保存",
        "cancel": "キャンセル",
    },
    "en": {
        "title": "Play Record",
        "heading": "Record this play? (all fields optional)",
        "mode": "Mode",
        "build": "Deck / Build",
        "result": "Result",
        "score": "Score / Reward",
        "advice": "Advice ID",
        "memo": "Memo",
        "privacy": "External sharing",
        "save": "Save",
        "cancel": "Cancel",
    },
}


def default_memo() -> dict[str, object]:
    """キャンセル時・未入力時の安全なデフォルト値。"""
    return {
        "mode": "",
        "build_or_deck_id": "",
        "result": "unknown",
        "score": "",
        "advice_id": "",
        "memo": "",
        "privacy_level": "local_only",
        "cancelled": True,
    }


def _labels() -> dict[str, str]:
    return _LABELS.get(getattr(i18n, "UI_LANGUAGE", "ja"), _LABELS["ja"])


def ask_session_memo(parent: tk.Misc, game_name: str = "") -> dict[str, object]:
    """終了時メモ入力ダイアログを表示し、入力値 dict を返す。

    キャンセル（×ボタン/キャンセルボタン/Esc）時は :func:`default_memo` を返す。
    """
    labels = _labels()
    result: dict[str, object] = default_memo()

    win = tk.Toplevel(parent)
    win.title(labels["title"])
    win.transient(parent)
    win.resizable(False, False)

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    heading = labels["heading"]
    if game_name:
        heading = f"{game_name}\n{heading}"
    ttk.Label(frame, text=heading, justify=tk.LEFT).grid(
        row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8)
    )

    mode_var = tk.StringVar()
    build_var = tk.StringVar()
    result_var = tk.StringVar(value="unknown")
    score_var = tk.StringVar()
    advice_var = tk.StringVar()
    privacy_var = tk.StringVar(value="local_only")

    def _add_entry(row: int, label: str, var: tk.StringVar) -> None:
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        ttk.Entry(frame, textvariable=var, width=28).grid(
            row=row, column=1, sticky=tk.EW, pady=2
        )

    _add_entry(1, labels["mode"], mode_var)
    _add_entry(2, labels["build"], build_var)

    ttk.Label(frame, text=labels["result"]).grid(row=3, column=0, sticky=tk.W, pady=2)
    ttk.Combobox(
        frame,
        textvariable=result_var,
        values=list(RESULT_CHOICES),
        state="readonly",
        width=26,
    ).grid(row=3, column=1, sticky=tk.EW, pady=2)

    _add_entry(4, labels["score"], score_var)
    _add_entry(5, labels["advice"], advice_var)

    ttk.Label(frame, text=labels["memo"]).grid(row=6, column=0, sticky=tk.NW, pady=2)
    memo_text = tk.Text(frame, width=28, height=4, wrap=tk.WORD)
    memo_text.grid(row=6, column=1, sticky=tk.EW, pady=2)

    ttk.Label(frame, text=labels["privacy"]).grid(row=7, column=0, sticky=tk.W, pady=2)
    ttk.Combobox(
        frame,
        textvariable=privacy_var,
        values=list(PRIVACY_CHOICES),
        state="readonly",
        width=26,
    ).grid(row=7, column=1, sticky=tk.EW, pady=2)

    button_row = ttk.Frame(frame)
    button_row.grid(row=8, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0))

    def on_save() -> None:
        result.update(
            {
                "mode": mode_var.get().strip(),
                "build_or_deck_id": build_var.get().strip(),
                "result": result_var.get().strip() or "unknown",
                "score": score_var.get().strip(),
                "advice_id": advice_var.get().strip(),
                # 長文・改行を含むメモでも落ちないよう、Text 全体を取得する。
                "memo": memo_text.get("1.0", tk.END).strip(),
                "privacy_level": privacy_var.get().strip() or "local_only",
                "cancelled": False,
            }
        )
        win.destroy()

    def on_cancel() -> None:
        # result は default_memo のまま（cancelled=True, result=unknown）。
        win.destroy()

    ttk.Button(button_row, text=labels["cancel"], command=on_cancel).pack(
        side=tk.RIGHT
    )
    ttk.Button(
        button_row, text=labels["save"], command=on_save, style="Accent.TButton"
    ).pack(side=tk.RIGHT, padx=(0, 6))

    win.protocol("WM_DELETE_WINDOW", on_cancel)
    win.bind("<Escape>", lambda _e: on_cancel())
    frame.columnconfigure(1, weight=1)

    try:
        win.grab_set()
    except tk.TclError:
        pass
    win.wait_window()
    return result
