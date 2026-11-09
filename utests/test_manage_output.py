## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

## local
from huginn import _manage_output

##
## === TEST SUITE
##


class TestBuiltInParams_Defaults(unittest.TestCase):

    def test_every_flag_is_off(
        self,
    ) -> None:
        built_in_params = _manage_output.BuiltInParams()
        self.assertFalse(built_in_params.dry_run)
        self.assertFalse(built_in_params.hide_actions)


class TestBuiltInParams_FromParsedArguments(unittest.TestCase):

    def test_fields_fill_from_flags_of_the_same_name(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(
            dry_run=True,
            hide_actions=False,
            cmd="go",
        )
        self.assertEqual(
            _manage_output.BuiltInParams.from_parsed_args(parsed_args),
            _manage_output.BuiltInParams(dry_run=True),
        )

    def test_field_with_no_flag_raises(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(dry_run=False)
        with self.assertRaises(AttributeError):
            _manage_output.BuiltInParams.from_parsed_args(parsed_args)


class TestRouteMsg_Streams(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_active_state()
        self.addCleanup(_manage_output.reset_active_state)

    def test_narration_goes_to_stderr(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg("narration")
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("narration", stderr_buffer.getvalue())

    def test_returns_always_go_to_stdout(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(io.StringIO()):
            _manage_output.route_msg(
                "returned",
                is_return=True,
            )
        self.assertIn("returned", stdout_buffer.getvalue())

    def test_terminal_lines_have_no_time_stamp(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg("plain")
        self.assertEqual(stderr_buffer.getvalue(), "plain\n")

    def test_narration_outside_a_terminal_is_never_wrapped(
        self,
    ) -> None:
        long_narration = " ".join(f"word{_word_index}" for _word_index in range(40))
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_output.route_msg(long_narration)
        self.assertEqual(stderr_buffer.getvalue(), f"{long_narration}\n")


class TestRouteMsg_Log(unittest.TestCase):

    log_file_path: Path

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_active_state()
        self.addCleanup(_manage_output.reset_active_state)
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.log_file_path = Path(temporary_directory.name) / "logs" / "tool.log"
        argv_patch = mock.patch.object(sys, "argv", ["/usr/bin/tool", "go", "fix [bold]"])
        argv_patch.start()
        self.addCleanup(argv_patch.stop)

    def _start_logging(
        self,
        *,
        dry_run: bool,
    ) -> None:
        _manage_output.set_built_in_params(_manage_output.BuiltInParams(dry_run=dry_run))
        _manage_output.set_log_file_path(log_file_path=self.log_file_path)

    def test_appends_the_invoked_cmd_then_plain_lines(
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
                "[2026-01-02 03:04:05] $ tool go 'fix [bold]'",
                "[2026-01-02 03:04:05] ○ first",
                "[2026-01-02 03:04:05] second",
            ],
        )

    def test_unset_log_file_path_raises_before_the_terminal_shows_anything(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with (
                mock.patch.object(_manage_output._active_state, "log_file_path_is_set", False),
                contextlib.redirect_stderr(stderr_buffer),
                self.assertRaises(_manage_output.LogFileError),
        ):
            _manage_output.route_msg("→ git push")
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_append_writes_the_log_file_only(
        self,
    ) -> None:
        self._start_logging(dry_run=False)
        stderr_buffer = io.StringIO()
        with mock.patch.object(_manage_output, "_get_time_stamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(stderr_buffer):
                _manage_output.append_to_log_file("[bold]only in the log[/bold]")
        self.assertEqual(stderr_buffer.getvalue(), "")
        self.assertEqual(
            self.log_file_path.read_text().splitlines()[1:],
            ["[2026-01-02 03:04:05] only in the log"],
        )

    def test_not_written_in_dry_run(
        self,
    ) -> None:
        self._start_logging(dry_run=True)
        with contextlib.redirect_stderr(io.StringIO()):
            _manage_output.append_to_log_file("not logged")
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

    def test_none_logs_nothing(
        self,
    ) -> None:
        _manage_output.set_log_file_path(log_file_path=None)
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
