from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Callable, Iterable

from tellygrab import __version__


OUTPUT_TEMPLATE = "%(title).200B [%(id)s].%(ext)s"
DOWNLOAD_RE = re.compile(r"download:\s*([0-9]+(?:\.[0-9]+)?)%")

TV_ART = (
    "          o                   o\n"
    "           \\\\                 /\n"
    "            \\\\               /\n"
    "   .--------------------------------.\n"
    "  / .--------------------------.    \\\\\n"
    " |  |                          |  () |\n"
    " |  |                          |  () |\n"
    " |  |                          |     |\n"
    " |  '--------------------------'     |\n"
    "  \\\\________________________________/\n"
    "       /_/                    \\\\_\\"
)

PRORES_PROFILES = {
    "proxy": 0,
    "lt": 1,
    "standard": 2,
    "hq": 3,
}


class TellyError(RuntimeError):
    """User-facing command failure."""


def reveal_art(percent: float, art: str = TV_ART) -> str:
    pct = max(0.0, min(100.0, percent))
    drawable = sum(1 for char in art if char not in (" ", "\n"))
    visible = round(drawable * (pct / 100.0))
    seen = 0
    output: list[str] = []

    for char in art:
        if char in (" ", "\n"):
            output.append(char)
            continue

        seen += 1
        output.append(char if seen <= visible else " ")

    return "".join(output)


class RevealDisplay:
    def __init__(self, mode: str, output_dir: Path, stream=None) -> None:
        self.mode = mode
        self.output_dir = output_dir
        self.stream = stream or sys.stdout
        self.interactive = self.stream.isatty() and not os.environ.get("NO_COLOR")
        self.rendered_lines = 0
        self.last_bucket: tuple[str, int] | None = None

    def update(self, percent: float, stage: str, detail: str = "") -> None:
        pct = max(0.0, min(100.0, percent))

        if not self.interactive:
            bucket = int(pct // 10) * 10
            key = (stage, bucket)
            if key != self.last_bucket or pct >= 100:
                self.last_bucket = key
                print(f"{stage:>10} {pct:5.1f}% {detail}".rstrip(), file=self.stream)
            return

        reset = "\033[0m"
        bold = "\033[1m"
        dim = "\033[2m"
        green = "\033[32m"
        cyan = "\033[36m"
        width = 32
        filled = round(width * pct / 100.0)
        bar = f"{green}{'#' * filled}{dim}{'-' * (width - filled)}{reset}"
        lines = [
            f"{bold}tellygrab{reset} {cyan}{self.mode}{reset} {pct:5.1f}%",
            f"[{bar}]",
            f"{dim}stage{reset}  {stage}",
            f"{dim}save{reset}   {self.output_dir}",
        ]
        if detail:
            lines.append(f"{dim}note{reset}   {detail}")
        lines.extend(reveal_art(pct).splitlines())
        block = "\n".join(lines)

        if self.rendered_lines:
            self.stream.write(f"\033[{self.rendered_lines}F\033[J")

        print(block, file=self.stream)
        self.stream.flush()
        self.rendered_lines = len(lines)

    def done(self, message: str) -> None:
        if self.interactive:
            print(message, file=self.stream)
        else:
            print(message, file=self.stream)


def default_output_dir() -> Path:
    return Path.home() / "Downloads"


def find_missing_tools() -> list[str]:
    missing: list[str] = []
    for tool in ("yt-dlp", "ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            missing.append(tool)
    return missing


def ensure_tools() -> None:
    missing = find_missing_tools()
    if not missing:
        return

    packages = brew_packages_for(missing)
    if shutil.which("brew"):
        raise TellyError(
            "Missing required tools: "
            + ", ".join(missing)
            + "\nInstall them with:\n  brew install "
            + " ".join(packages)
        )

    raise TellyError(
        "Missing required tools: "
        + ", ".join(missing)
        + "\nInstall yt-dlp and ffmpeg, then run telly again."
    )


def brew_packages_for(tools: Iterable[str]) -> list[str]:
    packages: list[str] = []
    for tool in tools:
        package = "ffmpeg" if tool == "ffprobe" else tool
        if package not in packages:
            packages.append(package)
    return packages


def parse_download_percent(line: str) -> float | None:
    match = DOWNLOAD_RE.search(line)
    if not match:
        return None
    return float(match.group(1))


def parse_timestamp(value: str) -> float | None:
    parts = value.strip().split(":")
    if len(parts) != 3:
        return None

    try:
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
    except ValueError:
        return None

    return hours * 3600 + minutes * 60 + seconds


def parse_ffmpeg_percent(line: str, duration: float | None) -> float | None:
    if not duration or duration <= 0:
        return 100.0 if line.strip() == "progress=end" else None

    key, _, value = line.strip().partition("=")
    seconds: float | None = None

    if key in {"out_time_us", "out_time_ms"}:
        try:
            seconds = float(value) / 1_000_000.0
        except ValueError:
            return None
    elif key == "out_time":
        seconds = parse_timestamp(value)
    elif key == "progress" and value == "end":
        return 100.0

    if seconds is None:
        return None

    return max(0.0, min(100.0, seconds / duration * 100.0))


def run_process(
    args: list[str],
    display: RevealDisplay,
    stage: str,
    start_percent: float,
    end_percent: float,
    parser: Callable[[str], float | None],
) -> None:
    display.update(start_percent, stage)
    tail: deque[str] = deque(maxlen=18)

    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        bufsize=1,
    )

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip()
        if line:
            tail.append(line)
        parsed = parser(line)
        if parsed is not None:
            overall = start_percent + (end_percent - start_percent) * (parsed / 100.0)
            display.update(overall, stage)

    code = process.wait()
    if code != 0:
        command = " ".join(args)
        recent = "\n".join(tail) if tail else "No output captured."
        raise TellyError(
            f"{stage.capitalize()} failed with exit code {code}.\n"
            f"Command: {command}\n\nRecent output:\n{recent}"
        )

    display.update(end_percent, stage)


def probe_duration(path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def newest_media_file(tmpdir: Path) -> Path:
    ignored_suffixes = {".part", ".ytdl", ".aria2", ".json", ".description"}
    candidates = [
        path
        for path in tmpdir.iterdir()
        if path.is_file() and not any(path.name.endswith(suffix) for suffix in ignored_suffixes)
    ]
    if not candidates:
        raise TellyError(f"No downloaded media file was found in {tmpdir}")

    return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size))


def build_yt_dlp_command(mode: str, url: str, tmpdir: Path) -> list[str]:
    selector = "bv*+ba/b" if mode == "video" else "ba/b"
    return [
        "yt-dlp",
        "--no-playlist",
        "--newline",
        "--progress",
        "--progress-template",
        "download:%(progress._percent_str)s",
        "--paths",
        str(tmpdir),
        "-f",
        selector,
        "-o",
        OUTPUT_TEMPLATE,
        url,
    ]


def video_ffmpeg_command(input_path: Path, output_path: Path, profile: str) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "prores_ks",
        "-profile:v",
        str(PRORES_PROFILES[profile]),
        "-pix_fmt",
        "yuv422p10le",
        "-vendor",
        "apl0",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


def audio_ffmpeg_command(input_path: Path, output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


def convert(
    mode: str,
    input_path: Path,
    output_path: Path,
    display: RevealDisplay,
    profile: str,
) -> None:
    duration = probe_duration(input_path)
    parser = lambda line: parse_ffmpeg_percent(line, duration)
    command = (
        video_ffmpeg_command(input_path, output_path, profile)
        if mode == "video"
        else audio_ffmpeg_command(input_path, output_path)
    )
    run_process(command, display, "converting", 72.0, 100.0, parser)


def run_job(
    mode: str,
    url: str,
    output_dir: Path,
    profile: str = "standard",
    keep_temp: bool = False,
) -> Path:
    ensure_tools()
    output_dir.mkdir(parents=True, exist_ok=True)

    tmpdir = Path(tempfile.mkdtemp(prefix=f"tellygrab-{mode}-"))
    display = RevealDisplay(mode, output_dir)

    try:
        run_process(
            build_yt_dlp_command(mode, url, tmpdir),
            display,
            "downloading",
            0.0,
            72.0,
            parse_download_percent,
        )
        input_path = newest_media_file(tmpdir)
        suffix = ".mov" if mode == "video" else ".wav"
        output_path = output_dir / f"{input_path.stem}{suffix}"
        convert(mode, input_path, output_path, display, profile)
    except Exception:
        print(f"Temporary files kept at: {tmpdir}", file=sys.stderr)
        raise
    else:
        if keep_temp:
            display.done(f"Done: {output_path}\nTemporary files kept at: {tmpdir}")
        else:
            shutil.rmtree(tmpdir)
            display.done(f"Done: {output_path}")
        return output_path


def examples() -> str:
    return (
        "\nExamples:\n"
        '  telly video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"\n'
        '  telly audio "https://www.youtube.com/watch?v=dQw4w9WgXcQ"\n'
        "  telly doctor\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telly",
        description="Tiny YouTube downloader for editor-ready terminal workflows.",
        epilog=examples(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"tellygrab {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    video = subparsers.add_parser("video", help="download a ProRes .mov into ~/Downloads")
    video.add_argument("url", help="YouTube URL")
    video.add_argument("-o", "--output-dir", type=Path, default=default_output_dir())
    video.add_argument(
        "--profile",
        choices=sorted(PRORES_PROFILES),
        default="standard",
        help="ProRes profile; default is standard for a quality/size balance",
    )
    video.add_argument("--keep-temp", action="store_true", help="keep temporary source files")

    audio = subparsers.add_parser("audio", help="download a 48kHz .wav into ~/Downloads")
    audio.add_argument("url", help="YouTube URL")
    audio.add_argument("-o", "--output-dir", type=Path, default=default_output_dir())
    audio.add_argument("--keep-temp", action="store_true", help="keep temporary source files")

    doctor = subparsers.add_parser("doctor", help="check local dependencies")
    doctor.add_argument("--install-command", action="store_true", help="print the Homebrew install command")

    return parser


def run_doctor(install_command: bool = False) -> int:
    missing = find_missing_tools()
    if not missing:
        print("tellygrab is ready: yt-dlp, ffmpeg, and ffprobe are installed.")
        return 0

    print("Missing: " + ", ".join(missing), file=sys.stderr)
    if shutil.which("brew"):
        command = "brew install " + " ".join(brew_packages_for(missing))
        print(command if install_command else f"Install with: {command}", file=sys.stderr)
    else:
        print("Install Homebrew or install yt-dlp and ffmpeg manually.", file=sys.stderr)
    return 1


def main(argv: Iterable[str] | None = None) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()

    if not args_list:
        parser.print_help()
        return 2

    args = parser.parse_args(args_list)

    try:
        if args.command == "video":
            run_job("video", args.url, args.output_dir.expanduser(), args.profile, args.keep_temp)
            return 0
        if args.command == "audio":
            run_job("audio", args.url, args.output_dir.expanduser(), "standard", args.keep_temp)
            return 0
        if args.command == "doctor":
            return run_doctor(args.install_command)

        parser.print_help()
        return 2
    except KeyboardInterrupt:
        print("\nCanceled.", file=sys.stderr)
        return 130
    except TellyError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
