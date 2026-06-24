import unittest
import os
from pathlib import Path

from tellygrab import __version__
from tellygrab import cli


class TellygrabTests(unittest.TestCase):
    def test_reveal_art_reaches_full_tv(self):
        self.assertEqual(cli.reveal_art(100), cli.TV_ART)

    def test_reveal_art_hides_chars_at_zero(self):
        revealed = cli.reveal_art(0)
        self.assertNotIn("()", revealed)
        self.assertEqual(len(revealed), len(cli.TV_ART))

    def test_download_percent_parser(self):
        self.assertEqual(cli.parse_download_percent("download: 42.5%"), 42.5)
        self.assertIsNone(cli.parse_download_percent("[download] Destination: file.webm"))

    def test_timestamp_parser(self):
        self.assertEqual(cli.parse_timestamp("00:01:30.500000"), 90.5)

    def test_ffmpeg_percent_parser(self):
        self.assertAlmostEqual(cli.parse_ffmpeg_percent("out_time=00:00:05.000000", 10), 50.0)
        self.assertEqual(cli.parse_ffmpeg_percent("progress=end", 10), 100.0)

    def test_download_command_uses_safe_defaults(self):
        command = cli.build_yt_dlp_command("video", "https://example.com/watch?v=abc", Path("/tmp/telly"))
        self.assertIn("--no-playlist", command)
        self.assertIn("bv*+ba/b", command)
        self.assertIn(cli.OUTPUT_TEMPLATE, command)

    def test_brew_packages_are_deduped(self):
        self.assertEqual(cli.brew_packages_for(["yt-dlp", "ffmpeg", "ffprobe"]), ["yt-dlp", "ffmpeg"])

    def test_filename_helpers(self):
        self.assertEqual(cli.clean_filename("a/b: c"), "a-b- c")
        self.assertEqual(cli.output_stem("Title", "abc123"), "Title [abc123]")

    def test_format_helpers(self):
        self.assertEqual(cli.format_duration(90), "1:30")
        self.assertEqual(cli.format_duration(3671), "1:01:11")
        self.assertEqual(cli.format_upload_date("20260624"), "2026-06-24")

    def test_recent_files_filters_and_sorts(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "Old [abcdef12345].wav"
            new = root / "New [abcdef12345].mov"
            skip = root / "plain.mov"
            old.write_text("old")
            new.write_text("new")
            skip.write_text("skip")
            os.utime(old, (1, 1))
            os.utime(new, (2, 2))

            self.assertEqual(cli.recent_files(root, 5), [new, old])

    def test_video_conversion_targets_prores_mov_style(self):
        command = cli.video_ffmpeg_command(Path("in.webm"), Path("out.mov"), "standard")
        self.assertIn("prores_ks", command)
        self.assertIn("pcm_s16le", command)
        self.assertIn("48000", command)
        self.assertIn("2", command)

    def test_audio_conversion_targets_wav_style(self):
        command = cli.audio_ffmpeg_command(Path("in.webm"), Path("out.wav"))
        self.assertIn("pcm_s16le", command)
        self.assertIn("48000", command)
        self.assertIn("-vn", command)

    def test_version_is_set(self):
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_parser_uses_tg_examples(self):
        parser = cli.build_parser()
        self.assertEqual(parser.prog, "tg")
        help_text = parser.format_help()
        self.assertIn("tg video", help_text)
        self.assertIn("info", help_text)
        self.assertIn("recent", help_text)


if __name__ == "__main__":
    unittest.main()
