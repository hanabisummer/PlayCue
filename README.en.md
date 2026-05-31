# PlayCue

[日本語](README.md) | [English](README.en.md)

PlayCue is a lightweight Windows widget for game streamers and recorders.  
It manages game launching, play time tracking, guide links, and OBS recording automation in a single window.

Just select a game and launch it — OBS recording starts automatically and PlayCue logs when, which game, and how long you played.

## Features

- Launch registered games from the widget
- Automatically track play time from game process start to exit
- Show recently played games near the top
- Show game-specific links such as guides, notes, or spreadsheets
- Automatically launch OBS, start recording on game start, and stop on game exit
- Stay in the task tray when minimized
- Optional auto-start with Windows

---

## Download

Download `PlayCue.zip` from the [Releases page](../../releases/latest).

1. Download `PlayCue.zip`.
2. Extract the ZIP file anywhere you like.
3. Open the extracted folder.

---

## Start the Widget

Double-click `PlayCue.exe` inside the extracted folder.

> Windows may ask for administrator permission on first launch.  
> **Click "Yes"** — it is needed for game launching and OBS integration to work reliably.

> **If your antivirus shows a warning**  
> Executables built with PyInstaller are sometimes flagged as false positives.  
> PlayCue is open source — you can review the [source code](../../) to verify it is safe.

---

## Add a Game

The setup wizard opens automatically on first launch since no games are registered yet.

1. Open `Settings` at the top of the widget.
2. Select `Add Game`.
3. Enter the game name (e.g., `Genshin Impact`).
4. Click `Browse` and select the `.exe` used to start the game.  
   If the game has a launcher, select the launcher exe.
5. In `Process Name`, enter the actual game process name (e.g., `GenshinImpact.exe`).  
   You can find the process name in Task Manager under the `Processes` tab.
6. If the game launches via a launcher, enter the real game process name in `Active Process Name`.  
   Play time tracking will start when this process appears, not when the launcher starts.
7. Add guide, note, or spreadsheet links if needed.
8. Press `Create`.

---

## OBS Recording (Optional)

OBS is not required. Skip this section if you do not use OBS recording.

To automate OBS recording:

1. Start OBS Studio.
2. Open `Tools` → `WebSocket Server Settings`.
3. Enable the WebSocket server.
4. In the widget, open `Settings` → `OBS Settings`.
5. Enter the OBS exe path, port, and password.
6. Press `Update Settings`.

After setup, OBS recording starts automatically when the registered game process starts  
and stops automatically when it exits.

---

## View Play History

Open the `Summary` menu at the top of the widget.

| Menu | Description |
|---|---|
| Last 1 / 7 / 30 days | Total play time per game for the period |
| Total | All-time play time totals with CSV export |
| History List | Per-session start, end, and duration list |
| Calendar | Daily play time calendar view |

Play history is automatically saved to `logs/play_history.csv`.

---

## FAQ

**Q. Play time is not tracked after launching the game**  
A. Check the `Process Name` setting. Open Task Manager, find the running game in the `Processes` tab,  
   and enter that process name (e.g., `Game.exe`) in the `Process Name` field.

**Q. Cannot connect to OBS**  
A. Make sure the WebSocket server is enabled in OBS.  
   Confirm the port and password match what you entered in the widget settings.  
   See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) for more details.

**Q. Antivirus shows a warning**  
A. Executables built with PyInstaller are sometimes flagged as false positives.  
   PlayCue is open source — review the [source code](../../) to verify it is safe.  
   If you are still concerned, use the source-based launch method described below.

**Q. Login bonus auto-check is not available**  
A. This feature requires Tesseract OCR to be installed separately.  
   Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) to enable it.

---

## Run From Source (Developers / Advanced Users)

If you have a Python environment, you can run directly from source.

**Requirements**

- Windows
- Python 3.11 or later

**Setup**

```powershell
python -m pip install -r requirements.txt
```

**Launch**

```powershell
python PlayCue.py
```

---

## License

MIT License. See [LICENSE](LICENSE).
