# Python Curses Music Player Plan

## Goal
Build a terminal music player in Python that:
- Plays local audio via `ffmpeg`/`ffplay` under the hood
- Uses a `curses` UI for browsing and controls
- Shows animated ASCII art while music plays
- Stays responsive (non-blocking UI + playback process)

## Scope (v1)
- Local file playback only (mp3/flac/wav/ogg/m4a)
- Queue + basic transport controls (play/pause/next/prev/seek)
- Volume control
- Progress bar + elapsed/remaining time
- One ASCII visualizer mode + one static album-art fallback
- Simple config file and keymap

Out of scope (for now):
- Streaming services
- Network control API
- Tag editing
- Cross-device sync

## High-Level Architecture
- `curses` thread/process: input handling + rendering loop
- `player` backend: controls an ffmpeg-family subprocess (`ffplay` easiest start)
- `library` scanner: discovers files and reads metadata
- `visualizer`: generates ASCII frames from audio energy (or simulated for v1 fallback)
- `state` store: central app state shared between UI and player backend

Recommended model:
- Main thread = curses event loop
- Background worker thread = player I/O/events
- Shared state guarded with `threading.Lock` or `queue.Queue` events

## ffmpeg Strategy
### v1 (fastest path)
Use `ffplay` as subprocess:
- Launch with `-nodisp -autoexit`
- Track process lifecycle for play/stop/next
- Pause/seek can be implemented via process restart w/ offset if needed

### v2 (better control)
Use `ffmpeg` decode -> `ffplay`/audio output pipe OR Python audio backend:
- Enables tighter seek/pause and analysis taps
- More complexity

Decision:
- Start with `ffplay` for speed, switch to richer pipeline after core UX works.

## ASCII Visuals Strategy
Three progressive levels:
1. **Fake reactive bars** (time-based animation): unblock UI quickly
2. **Energy-based bars** from audio analysis stream (RMS per window)
3. **FFT visualizer** mapped to ASCII density (` .:-=+*#%@`)

v1 recommendation:
- Implement #1 first, #2 immediately after playback stability

## Suggested Project Layout
```text
rlc/
  PLAN.md
  README.md
  pyproject.toml
  requirements.txt
  rlc/
    __init__.py
    main.py
    app.py
    config.py
    state.py
    ui/
      __init__.py
      curses_app.py
      views.py
      widgets.py
      keymap.py
    player/
      __init__.py
      backend.py
      ffplay_backend.py
      queue.py
    library/
      __init__.py
      scanner.py
      metadata.py
    visualizer/
      __init__.py
      ascii_engine.py
      analyzer.py
      frames.py
    util/
      __init__.py
      paths.py
      logging.py
  tests/
    test_queue.py
    test_state.py
    test_keymap.py
```

## Dependency Plan
Core:
- `ffmpeg` installed on system (`ffplay` available)
- Python 3.11+

Python libs:
- `mutagen` (metadata)
- `rich` (optional logging/debug pretty output outside curses)
- `pytest` (tests)

Optional later:
- `numpy` for FFT/visualization
- `soundfile`/`pydub` depending on analysis approach

## Event Loop Design
Tick loop every ~33ms (30 FPS max):
- Poll input (non-blocking)
- Process queued player events
- Update state/progress
- Render visible regions only

Keep render cheap:
- Avoid full-screen redraw when possible
- Precompute ASCII frames where possible
- Clamp frame rate when terminal is small/slow

## UX / Keybindings (initial)
- `Space`: play/pause
- `n`: next
- `p`: previous
- `h` / `l`: seek -5/+5 sec
- `-` / `=`: volume down/up
- `j` / `k`: move selection
- `Enter`: play selected
- `a`: add selected to queue
- `v`: cycle visualizer mode
- `q`: quit

## Milestones
1. **Bootstrap app shell**
   - Project files, config loader, curses init/cleanup
2. **Playback backend v1**
   - Start/stop/next/prev with `ffplay`
3. **Library browser**
   - Scan directories, list tracks, enqueue
4. **Queue and transport UI**
   - Now playing panel + progress + controls
5. **ASCII visuals v1**
   - Animated bars synced to time/progress
6. **Metadata and polish**
   - Artist/title/duration; better error handling
7. **Tests + packaging**
   - Core state/queue/keymap tests, run script

## Technical Risks + Mitigations
- **Curses flicker/lag**
  - Mitigation: lower FPS, region-based redraw, simple widgets first
- **ffplay control limitations**
  - Mitigation: design backend interface so implementation can be swapped
- **Terminal compatibility issues**
  - Mitigation: test on xterm/alacritty/gnome-terminal; avoid exotic control codes
- **Audio analysis overhead**
  - Mitigation: start with lightweight visuals; move FFT to optional path

## Definition of Done (v1)
- User can scan a folder, select tracks, and play queue continuously
- UI remains responsive while audio plays
- ASCII visual panel animates during playback
- Controls work reliably for pause/next/prev/quit
- No crashes on empty library, missing files, or ffplay missing

## First Build Session Checklist
- [ ] Create package skeleton and entrypoint
- [ ] Implement `PlayerBackend` interface + `FFplayBackend`
- [ ] Build minimal curses layout (library pane, now-playing pane, visual pane)
- [ ] Wire key handlers to backend actions
- [ ] Add basic track scanner (`glob` + extension filter)
- [ ] Add simple animated ASCII bars
- [ ] Write 3-5 unit tests for queue/state transitions

## Quick Start Commands (after scaffold)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m rlc.main --music-dir ~/Music
```

## Next Step
Implement milestone 1 + 2 first; do not start FFT/audio-reactive visuals until transport is stable.
