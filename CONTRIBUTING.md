# Contributing

Thanks for helping make `tellygrab` better.

## Project shape

This repo should stay small:

- no GUI
- no background service
- no downloader engine rewrite
- no surprise playlist downloads
- no heavy Python dependencies for core use

## Development

```sh
git clone https://github.com/scwlkr/tellygrab.git
cd tellygrab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
./scripts/check.sh
```

## Pull requests

Before opening a PR:

- run `./scripts/check.sh`
- keep changes focused
- update README examples when behavior changes
- include tests for parser, command-building, or filename behavior when relevant

## Good first issues

- improve terminal rendering on small terminals
- add Linux install notes
- improve failure messages for missing codecs
- add a small demo GIF or terminal screenshot to the README
