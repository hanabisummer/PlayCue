# PlayCue

[日本語](README.md) | [English](README.en.md)

PlayCue is a Windows widget for launching PC games, tracking play time, showing useful links, and controlling OBS recording.

It is designed so regular gamers can use it without technical knowledge: choose a game, launch it, and the widget records when and how long you played.

## Features

- Launch registered games from the widget
- Automatically track play time per game
- Show recently played games near the top
- Show game-specific links such as guides, notes, or spreadsheets
- Automatically launch OBS Studio and start/stop recording
- Stop OBS recording automatically when the game exits
- Stay in the task tray when minimized
- Optional startup when Windows starts

## Requirements

- Windows
- Python 3.11 or later
- OBS Studio, only if you use OBS integration

## Download

1. On GitHub, select `Code` -> `Download ZIP`.
2. Extract the ZIP file anywhere you like.
3. Open the extracted folder.

## First Setup

Open PowerShell in this folder and run:

```powershell
python -m pip install -r requirements.txt
```

## Start the Widget

```powershell
python PlayCue.py
```

Windows may ask for administrator permission on first launch. Allow it if you want game launching and OBS integration to work reliably.

## Add a Game

1. Open `Settings` at the top of the widget.
2. Select `Add Game`.
3. Enter the game name.
4. Use `Browse` next to `Game exe Path` and select the game's `.exe` file.
5. Add guide, note, or spreadsheet links if needed.
6. Press `Create`.

The new game appears in the game list immediately.

## Use OBS Recording

Set this up only if you want automatic OBS recording.

1. Start OBS Studio.
2. Open `Tools` -> `WebSocket Server Settings`.
3. Enable the WebSocket server.
4. In the widget, open `Settings` -> `OBS Settings`.
5. Enter the OBS exe path, port, and password.
6. Press `Update Settings`.

The widget can start recording when a game launches and stop recording when the game exits.

## Play Time Logs

Play history is saved to `logs/play_history.csv`.

This file contains your personal play history. Do not publish it to GitHub. This repository excludes it with `.gitignore`.

## AI Shorts Helper

`shorts_agent/` contains a helper CLI for creating short videos from recorded gameplay.

It requires FFmpeg/FFprobe. VOICEVOX narration is optional. The tool is designed not to overwrite source videos, but outputs should always stay under `outputs/`.

See [shorts_agent/README.md](shorts_agent/README.md) for details.

## Before Publishing to GitHub

Safe to publish:

- `PlayCue.py`
- `requirements.txt`
- `README.md`
- `README.en.md`
- `configs/example.json`
- `shorts_agent/`
- `tests/`

Do not publish:

- Personal `configs/*.json` files
- `logs/*.csv` play history
- `launchers/*.bat`
- `outputs/`
- OBS WebSocket passwords
- Local paths that only exist on your PC

## Verification

Before publishing, run:

```powershell
python -m py_compile PlayCue.py
python -m unittest discover -s tests
```

## License

MIT License. See [LICENSE](LICENSE).

## Build an exe

If you want to share the widget with people who do not have Python installed, you can build an exe with PyInstaller.

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed PlayCue.py
```

Place the `configs` folder next to the generated exe.
