## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

## local
from huginn import _manage_output, params

##
## === TEST SUITE
##


class TestRouteMsg_Streams(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)

    def test_narration_goes_to_stderr(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg("narration")
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("narration", stderr_buffer.getvalue())

    def test_results_always_go_to_stdout(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(io.StringIO()):
            _manage_output.route_msg(
                "result",
                is_result=True,
            )
        self.assertIn("result", stdout_buffer.getvalue())

    def test_terminal_lines_have_no_time_stamp(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg("plain")
        self.assertEqual(stderr_buffer.getvalue(), "plain\n")


class TestRouteMsg_Log(unittest.TestCase):

    log_file_path: Path

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.log_file_path = Path(temporary_directory.name) / "logs" / "tool.log"

    def _start_logging(
        self,
        *,
        dry_run: bool,
    ) -> None:
        _manage_output.set_params(
            tool_params=params.ToolParams(dry_run=dry_run),
            log_file_path=self.log_file_path,
        )

    def test_appends_plain_lines(
        self,
    ) -> None:
        self._start_logging(dry_run=False)
        with mock.patch.object(_manage_output, "_get_time_stamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(io.StringIO()):
                _manage_output.route_msg("[#A660D0]○ first[/]")
                _manage_output.route_msg("[bold]second[/bold]")
        self.assertEqual(
            self.log_file_path.read_text().splitlines(),
            [
                "[2026-01-02 03:04:05] ○ first",
                "[2026-01-02 03:04:05] second",
            ],
        )

    def test_run_header_is_the_cmd_as_typed(
        self,
    ) -> None:
        self._start_logging(dry_run=False)
        with mock.patch.object(_manage_output, "_get_time_stamp", return_value="2026-01-02 03:04:05"):
            _manage_output.log_run_header(["tool", "commit", "-m", "a message"])
        self.assertEqual(
            self.log_file_path.read_text().splitlines(),
            ["[2026-01-02 03:04:05] $ tool commit -m 'a message'"],
        )

    def test_run_header_keeps_square_brackets(
        self,
    ) -> None:
        self._start_logging(dry_run=False)
        with mock.patch.object(_manage_output, "_get_time_stamp", return_value="2026-01-02 03:04:05"):
            _manage_output.log_run_header(["tool", "commit", "-m", "fix [bold] and [/x]"])
        self.assertEqual(
            self.log_file_path.read_text().splitlines(),
            ["[2026-01-02 03:04:05] $ tool commit -m 'fix [bold] and [/x]'"],
        )

    def test_not_written_in_dry_run(
        self,
    ) -> None:
        self._start_logging(dry_run=True)
        with contextlib.redirect_stderr(io.StringIO()):
            _manage_output.log_run_header(["tool", "go"])
            _manage_output.route_msg("nothing happens")
        self.assertFalse(self.log_file_path.exists())

    def test_unwritable_log_raises_before_the_terminal_shows_anything(
        self,
    ) -> None:
        self.log_file_path.parent.write_text("a file where the log folder should be")
        self._start_logging(dry_run=False)
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(_manage_output.LogFileError):
            _manage_output.route_msg("→ git push")
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_off_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            _manage_output.route_msg("nowhere")
        self.assertFalse(self.log_file_path.exists())


class TestEscapeMarkup_Text(unittest.TestCase):

    def test_brackets_print_literally(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg(_manage_output.escape_markup("[bold]x[/bold]"))
        self.assertEqual(stderr_buffer.getvalue(), "[bold]x[/bold]\n")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
