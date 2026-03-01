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
curl -fsSL https://raw.githubusercontent.com/ryangerardwilson/rlc/main/install.sh | bash -s -- --version 0.1.0
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
rlc --music-dir ~/Music   # scan and load tracks from a specific directory
rlc --fps 30              # set UI render rate
rlc --version             # print version
rlc --help                # show usage summary
```

---

## Keyboard shortcuts

- `j` / `k` - move track selection down/up
- `Enter` - play selected track
- `s` - stop playback
- `q` - quit

---

## Requirements

- Linux `x86_64` (for current prebuilt installer)
- `ffplay` and `ffmpeg` available in `PATH`

If `ffplay` is missing, playback will not start.

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
