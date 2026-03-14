# rlc

rlc is a **terminal-native, curses-based local music player** with a clean
ASCII visualizer and ffmpeg/ffplay-powered playback.

It is designed for keyboard-first use in the terminal with minimal UI overhead
and explicit controls.

---

## Installation

### Prebuilt binary (Linux x86_64)

The fastest way to install `rlc` is the prebuilt release bundle:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/rlc/main/install.sh | bash
```

Install a specific version:

```bash
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/rlc/main/install.sh | bash -s -- -v 0.1.0
```

### From source

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m rlc.main
```

By default, `rlc` scans `~/Music`.

---

## Command-line usage

```bash
rlc /path/to/song.mp3     # open rlc and auto-play this track (with visualizer)
rlc /path/to/music_dir    # open rlc using this directory for this run
rlc -f 30                 # set UI render rate
rlc -c ~/.config/rlc/config.json  # explicit config path
rlc -v                    # print version
rlc -u                    # upgrade to latest release
rlc -h                    # show usage summary
```

Config defaults to:
- `$XDG_CONFIG_HOME/rlc/config.json` if `XDG_CONFIG_HOME` is set
- `~/.config/rlc/config.json` otherwise

On first run, if `music_dir` is not configured, `rlc` prompts for a music
directory and saves it into the config file.

Supported config keys:
```json
{
  "music_dir": "/home/you/Music",
  "fps": 20
}
```

---

## Keyboard shortcuts

- `j` / `k` - move track selection down/up
- `Ctrl+j` / `Ctrl+k` - move selected track down/up in playlist order
- `l` - play selected track
- `Space` - pause/resume current track
- `f` / `b` - seek forward/backward by 10 seconds (rapid taps are batched)
- `dd` - delete selected track (press `d` twice quickly)
- `s` - shuffle playlist/library order
- `:` - open command bar
- `/` - open search prompt
- `x` - stop playback
- `n` / `N` - next/previous search result (after `/` search)
- `?` - toggle shortcuts screen
- `q` - quit

Command bar actions:
- `:name.mp3 https://...` - download YouTube audio into music directory
- `/query` - startswith, then contains, then fuzzy fallback

Command-bar editing:
- Arrow keys - move cursor left/right
- `Ctrl+W` - delete previous word
- `Alt+b` / `Alt+f` - move cursor backward/forward by word

Playback behavior:
- By default, when a track ends, `rlc` plays the next track in the current library order.

---

## Requirements

- Linux `x86_64` (for current prebuilt installer)
- `ffplay` and `ffmpeg` available in `PATH`
- `yt-dlp` available in `PATH` (for `:` YouTube downloads)

If `ffplay` is missing, playback will not start.

---

## Version And Upgrade

```bash
rlc -v
rlc -u
```

`rlc -v` prints the installed app version from the runtime `_version.py`
module. Source checkouts keep a placeholder `0.0.0`; tagged release builds
stamp the shipped artifact with the real version.

---

## Project layout

- `rlc/main.py` - CLI entrypoint and argument parsing
- `rlc/ui/` - curses UI rendering and input loop
- `rlc/player/` - ffplay backend and queue primitives
- `rlc/library/` - local music scanning and metadata display helpers
- `rlc/visualizer/` - spectrum analyzer and ASCII rendering

---

## Philosophy

- Terminal-native interface
- Keyboard-first interaction
- Minimal, readable ASCII output
- Explicit local-file playback flow
