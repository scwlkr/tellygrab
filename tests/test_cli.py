import io
import os
import time
import unittest
from pathlib import Path
from unittest import mock

from tellygrab import __version__
from tellygrab import cli


class TtyBuffer(io.StringIO):
    def isatty(self):
        return True


class TellygrabTests(unittest.TestCase):
    def test_reveal_art_reaches_full_tv(self):
        self.assertEqual(cli.reveal_art(100), cli.TV_ART)

    def test_reveal_art_hides_chars_at_zero(self):
        revealed = cli.reveal_art(0)
        self.assertNotIn("()", revealed)
        self.assertEqual(len(revealed), len(cli.TV_ART))

    def test_reveal_art_moves_from_top_to_bottom(self):
        revealed = cli.reveal_art(40).splitlines()
        self.assertTrue(revealed[0].strip())
        self.assertTrue(revealed[7].strip())
        self.assertFalse(revealed[-1].strip())

    def test_reveal_art_uses_soft_scanline_between_rows(self):
        revealed = cli.reveal_art(1, frame=0).splitlines()
        self.assertTrue(revealed[0].strip())
        self.assertNotEqual(revealed[0], cli.TV_ART.splitlines()[0])
        self.assertFalse(revealed[1].strip())

    def test_tv_art_keeps_fixed_proportions(self):
        lines = cli.TV_ART.splitlines()
        self.assertEqual(len(lines), 19)
        self.assertEqual({len(line) for line in lines}, {62})
        self.assertEqual(cli.TV_SCREEN_WIDTH, 34)
        self.assertEqual(cli.TV_SCREEN_HEIGHT, 8)

    def test_tv_static_changes_between_frames(self):
        frame_one = cli.render_tv_art(1)
        frame_two = cli.render_tv_art(2)
        self.assertNotEqual(frame_one, frame_two)
        self.assertEqual([len(line) for line in frame_one.splitlines()], [62] * 19)
        self.assertEqual([len(line) for line in frame_two.splitlines()], [62] * 19)

    def test_non_async_display_advances_static_frames(self):
        stream = TtyBuffer()
        frames = []
        percents = []

        def fake_reveal(percent, art=None, frame=0):
            frames.append(frame)
            percents.append(percent)
            return f"frame {frame}"

        with mock.patch.dict(os.environ, {"NO_COLOR": ""}):
            with mock.patch.object(cli, "reveal_art", side_effect=fake_reveal):
                display = cli.RevealDisplay("video", Path("/tmp/out"), stream=stream)
                display.update(50, "downloading")
                display.update(51, "downloading")

        self.assertEqual(frames, [0, 1])
        self.assertEqual(percents, [50, 51])

    def test_async_display_animates_between_progress_events(self):
        stream = TtyBuffer()
        percents = []

        display = cli.RevealDisplay("video", Path("/tmp/out"), stream=stream)
        display.async_animation = True

        def fake_render(percent, stage, detail=""):
            percents.append(percent)

        with mock.patch.object(cli, "TV_FRAME_INTERVAL_SECONDS", 0.005):
            with mock.patch.object(display, "_render_interactive", side_effect=fake_render):
                display.update(80, "downloading")
                time.sleep(0.03)
                display.close(render_final=True)

        self.assertGreaterEqual(len(percents), 4)
        self.assertGreater(percents[1], percents[0])
        self.assertLess(percents[0], 80)
        self.assertEqual(percents[-1], 80)

    def test_no_color_keeps_interactive_tv_without_color_codes(self):
        stream = TtyBuffer()
        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            display = cli.RevealDisplay("video", Path("/tmp/out"), stream=stream)
            display.update(100, "downloading")

        output = stream.getvalue()
        self.assertIn("tg video 100.0%", output)
        self.assertIn(".--------------------------------------------.", output)
        self.assertNotIn("\033[32m", output)

    def test_download_percent_parser(self):
        self.assertEqual(cli.parse_download_percent("download: 42.5%"), 42.5)
        self.assertEqual(cli.parse_download_percent("[download]  42.5% of 10MiB"), 42.5)
        self.assertIsNone(cli.parse_download_percent("[download] Destination: file.webm"))

    def test_timestamp_parser(self):
        self.assertEqual(cli.parse_timestamp("00:01:30.500000"), 90.5)

    def test_ffmpeg_percent_parser(self):
        self.assertAlmostEqual(cli.parse_ffmpeg_percent("out_time=00:00:05.000000", 10), 50.0)
        self.assertEqual(cli.parse_ffmpeg_percent("progress=end", 10), 100.0)

    def test_download_command_uses_safe_defaults(self):
        command = cli.build_yt_dlp_command("video", "https://example.com/watch?v=abc", Path("/tmp/telly"))
        self.assertIn("--no-playlist", command)
        self.assertIn("--concurrent-fragments", command)
        self.assertIn("bv*+ba/b", command)
        self.assertIn(cli.OUTPUT_TEMPLATE, command)

    def test_brew_packages_are_deduped(self):
        self.assertEqual(cli.brew_packages_for(["yt-dlp", "ffmpeg", "ffprobe"]), ["yt-dlp", "ffmpeg"])

    def test_filename_helpers(self):
        self.assertEqual(cli.clean_filename("a/b: c"), "a-b- c")
        self.assertEqual(cli.clean_filename("a|b"), "a\uff5cb")
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

    def test_video_conversion_can_use_videotoolbox_prores(self):
        command = cli.video_ffmpeg_command(
            Path("in.webm"),
            Path("out.mov"),
            "standard",
            "prores_videotoolbox",
        )
        self.assertIn("prores_videotoolbox", command)
        self.assertIn("standard", command)
        self.assertIn("p210le", command)

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
