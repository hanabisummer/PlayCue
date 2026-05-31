from __future__ import annotations

THEME: dict[str, str] = {
    "bg": "#10141f",
    "panel": "#171d2b",
    "panel_alt": "#20283a",
    "text": "#edf3ff",
    "muted": "#9aa9c4",
    "accent": "#21d4fd",
    "accent_active": "#55e6ff",
    "danger": "#ff4d6d",
    "danger_active": "#ff7891",
    "border": "#31405c",
    "warning": "#f5c542",
}

OBS_STATUS_COLOR: dict[str, str] = {
    "disabled":            "muted",
    "not_configured":      "warning",
    "not_running":         "warning",
    "starting":            "text",
    "connecting":          "text",
    "connected":           "accent",
    "recording":           "danger",
    "recording_not_ready": "warning",
    "disconnected":        "muted",
    "error":               "danger",
}
