# tellygrab

[![check](https://github.com/scwlkr/tellygrab/actions/workflows/check.yml/badge.svg)](https://github.com/scwlkr/tellygrab/actions/workflows/check.yml)

Tiny terminal YouTube downloads for editors.

`tellygrab` is a small wrapper around `yt-dlp` and `ffmpeg` that turns a YouTube URL into files that are comfortable in Premiere-style editing workflows:

- `tg video URL` saves a ProRes `.mov` in `~/Downloads`
- `tg audio URL` saves a 48kHz `.wav` in `~/Downloads`
- `tg info URL` previews title, id, duration, and output filenames
- `tg recent` lists recent `.mov` and `.wav` outputs
- filenames use the YouTube title plus video ID
- playlists are disabled by default
- progress reveals a tiny ASCII TV as the job completes

It is not trying to replace `yt-dlp`. It is a friendly two-lane workflow for people who want edit-ready files without remembering codec flags.

## Install

macOS one-liner:

```sh
curl -fsSL https://raw.githubusercontent.com/scwlkr/tellygrab/main/install.sh | bash
```

Manual install:

```sh
brew install yt-dlp ffmpeg pipx
pipx install git+https://github.com/scwlkr/tellygrab.git
```

Local development install:

```sh
git clone https://github.com/scwlkr/tellygrab.git
cd tellygrab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

## Usage

Download video as ProRes 422 `.mov`:

```sh
tg video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Download audio as 48kHz `.wav`:

```sh
tg audio "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Preview metadata and expected output names without downloading:

```sh
tg info "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

List recent tellygrab outputs:

```sh
tg recent
```

Check dependencies:

```sh
tg doctor
```

Choose a different output folder:

```sh
tg video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --output-dir ~/Desktop
```

Choose a different ProRes profile:

```sh
tg video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --profile lt
tg video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --profile hq
```

The default profile is `standard`, which maps to ProRes 422 and balances quality and file size for everyday editing.

`telly` and `tellygrab` are kept as compatibility aliases, but `tg` is the primary command.

## Why MOV/WAV?

YouTube often serves efficient delivery codecs such as VP9 or AV1. Those are good for streaming, but they are not as comfortable for editing timelines. `tellygrab` downloads the best available source, then converts video to ProRes 422 in a QuickTime `.mov` with 48kHz PCM audio. Audio-only downloads become 48kHz PCM `.wav` files instead of MP3 so you avoid extra loss before editing.

## Requirements

- macOS or another Unix-like shell
- Python 3.10+
- `yt-dlp`
- `ffmpeg` and `ffprobe`

The installer uses Homebrew on macOS to install missing command-line dependencies.

## Be responsible

Only download media you own, have permission to use, or are otherwise allowed to download. Respect YouTube's terms and creator rights.

## Contributing

Small improvements are welcome. Good first contributions:

- clearer terminal output
- safer dependency checks
- better docs for non-macOS users
- tests around progress parsing and file naming
- small install improvements

See [CONTRIBUTING.md](CONTRIBUTING.md).
