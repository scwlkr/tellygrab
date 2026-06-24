# Product notes

## Niche

Most YouTube download helpers optimize for delivery files such as MP4 video and MP3 audio. `tellygrab` is deliberately narrower: paste a YouTube URL, get editor-friendly files in `~/Downloads`.

## Product bets

- Stay tiny. Use `yt-dlp` for extraction and `ffmpeg` for conversion instead of reimplementing either job.
- Make the happy path memorable: `telly video URL` and `telly audio URL`.
- Prefer editing formats: ProRes 422 `.mov` and 48kHz PCM `.wav`.
- Avoid playlist surprises with `--no-playlist`.
- Make progress feel fun with an ASCII TV reveal, inspired by the reference TV image.
- Keep the repo community-friendly with a one-line installer, issue templates, contribution guide, and MIT license.

## Research notes

- `yt-dlp` is the maintained, feature-rich downloader layer and supports output templates, format selection, and progress output.
- FFmpeg includes the `prores_ks` encoder and supports standard ProRes profiles.
- Adobe documents Apple ProRes video, MOV containers, and WAV audio as supported import formats in Premiere-family tools.
- Existing lightweight downloader CLIs often focus on MP4/MP3, which leaves room for a small editor-first wrapper.
