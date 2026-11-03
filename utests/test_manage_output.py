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


class TestRouteMsg_TimeStamps(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)

    def test_off_by_default(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg("plain")
        self.assertEqual(stderr_buffer.getvalue(), "plain\n")

    def test_prefix_when_enabled(
        self,
    ) -> None:
        _manage_output.set_params(
            tool_params=params.ToolParams(),
            output_params=params.OutputParams(show_time_stamps=True),
        )
        stderr_buffer = io.StringIO()
        with mock.patch.object(_manage_output, "_get_time_stamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(stderr_buffer):
                _manage_output.route_msg("stamped")
        self.assertEqual(stderr_buffer.getvalue(), "[2026-01-02 03:04:05] stamped\n")


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
            output_params=params.OutputParams(log_file_path=self.log_file_path),
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

    def test_not_written_in_dry_run(
        self,
    ) -> None:
        self._start_logging(dry_run=True)
        with contextlib.redirect_stderr(io.StringIO()):
            _manage_output.route_msg("nothing happens")
        self.assertFalse(self.log_file_path.exists())

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
