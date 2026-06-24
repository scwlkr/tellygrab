#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${TELLYGRAB_SOURCE:-git+https://github.com/scwlkr/tellygrab.git}"

need() {
  command -v "$1" >/dev/null 2>&1
}

if ! need brew; then
  cat >&2 <<'MSG'
Homebrew is required for the one-line macOS installer.

Install Homebrew first:
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Then rerun the tellygrab installer.
MSG
  exit 1
fi

packages=()
need yt-dlp || packages+=("yt-dlp")
need ffmpeg || packages+=("ffmpeg")
need ffprobe || packages+=("ffmpeg")
need python3 || packages+=("python")
need pipx || packages+=("pipx")

if ((${#packages[@]})); then
  unique_packages=()
  for package in "${packages[@]}"; do
    [[ " ${unique_packages[*]} " == *" $package "* ]] || unique_packages+=("$package")
  done
  brew install "${unique_packages[@]}"
fi

pipx ensurepath
pipx install --force "$REPO_URL"

cat <<'MSG'

tellygrab installed.

Try:
  tg video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  tg audio "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  tg info "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

If this is your first pipx install, open a new terminal before running tg.
MSG
