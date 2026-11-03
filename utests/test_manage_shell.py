## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

## local
from huginn import _manage_output, manage_shell, params

##
## === HELPERS
##


def _turn_on_dry_run() -> None:
    _manage_output.set_params(
        tool_params=params.ToolParams(dry_run=True),
        log_file_path=None,
    )


##
## === TEST SUITE
##


class TestPrintedCmds_Quoting(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)

    def _print_query(
        self,
        cmd_parts: list[str],
    ) -> str:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(
                stdout="",
                returncode=0,
            )
            manage_shell.query_cmd_and_capture_output(cmd_parts=cmd_parts)
        return stderr_buffer.getvalue()

    def test_arg_with_spaces_is_quoted(
        self,
    ) -> None:
        self.assertEqual(
            self._print_query(["git", "commit", "-m", "a message"]),
            "→ git commit -m 'a message'\n",
        )

    def test_brackets_in_args_print_literally(
        self,
    ) -> None:
        self.assertEqual(self._print_query(["ls", "[red]"]), "→ ls '[red]'\n")


class TestRunners_KeywordOnly(unittest.TestCase):

    def test_positional_args_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            manage_shell.query_cmd_and_capture_output(["true"])  # pyright: ignore[reportCallIssue]
        with self.assertRaises(TypeError):
            manage_shell.query_cmd_and_discard_output(["true"])  # pyright: ignore[reportCallIssue]


class TestRunCmdAndShowOutput_Behaviour(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)

    def test_dry_run_skips_logs_and_counts_as_success(
        self,
    ) -> None:
        _turn_on_dry_run()
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            cmd_has_succeeded = manage_shell.run_cmd_and_show_output(cmd_parts=["git", "push"])
        mock_run.assert_not_called()
        self.assertTrue(cmd_has_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ (dry-run) skipped: git push\n")

    def test_dry_run_line_uses_the_change_symbol_in_the_skipped_colour(
        self,
    ) -> None:
        _turn_on_dry_run()
        with mock.patch.object(_manage_output, "route_msg") as mock_route_msg:
            manage_shell.run_cmd_and_show_output(cmd_parts=["git", "push"])
        msg_rendered = mock_route_msg.call_args.args[0]
        self.assertEqual(msg_rendered, "[#B86B00]→ (dry-run) skipped: git push[/]")

    def test_logs_and_executes_when_not_dry_run(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(returncode=0)
            cmd_has_succeeded = manage_shell.run_cmd_and_show_output(cmd_parts=["git", "status"])
        mock_run.assert_called_once()
        self.assertTrue(cmd_has_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ git status\n")

    def test_failure_raises_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            manage_shell.run_cmd_and_show_output(cmd_parts=["false"])

    def test_failure_returns_false_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_has_succeeded = manage_shell.run_cmd_and_show_output(
                cmd_parts=["false"],
                raise_error=False,
            )
        self.assertFalse(cmd_has_succeeded)


class TestRunCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_params()
        self.addCleanup(_manage_output.reset_params)

    def test_returns_empty_string_in_dry_run(
        self,
    ) -> None:
        _turn_on_dry_run()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            captured_output = manage_shell.run_cmd_and_capture_output(
                cmd_parts=["git", "rev-list", "--count", "HEAD"],
            )
        mock_run.assert_not_called()
        self.assertEqual(captured_output, "")

    def test_strips_and_passes_working_directory(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            mock_run.return_value = mock.MagicMock(
                stdout="3\n",
                returncode=0,
            )
            captured_output = manage_shell.run_cmd_and_capture_output(
                cmd_parts=["git", "rev-list", "--count", "HEAD"],
                working_directory=Path("/tmp"),
            )
        self.assertEqual(captured_output, "3")
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


class TestQueryCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def test_raises_on_failure_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            manage_shell.query_cmd_and_capture_output(cmd_parts=["false"])

    def test_returns_empty_string_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            query_output = manage_shell.query_cmd_and_capture_output(
                cmd_parts=["false"],
                raise_error=False,
            )
        self.assertEqual(query_output, "")

    def test_passes_working_directory(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            mock_run.return_value = mock.MagicMock(
                stdout="main\n",
                returncode=0,
            )
            manage_shell.query_cmd_and_capture_output(
                cmd_parts=["git", "branch", "--show-current"],
                working_directory=Path("/tmp"),
            )
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


class TestQueryCmdAndCaptureOutcome_Outcome(unittest.TestCase):

    working_directory: Path

    def setUp(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.working_directory = Path(temporary_directory.name)

    def test_records_cmd_output_and_exit_code(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_outcome = manage_shell.query_cmd_and_capture_outcome(
                cmd_parts=["echo", "a b"],
                working_directory=self.working_directory,
            )
        self.assertEqual(cmd_outcome.cmd, "echo 'a b'")
        self.assertEqual(cmd_outcome.working_directory, self.working_directory)
        self.assertEqual(cmd_outcome.stdout, "a b\n")
        self.assertTrue(cmd_outcome.has_succeeded)

    def test_does_not_raise_on_failure(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_outcome = manage_shell.query_cmd_and_capture_outcome(cmd_parts=["false"])
        self.assertFalse(cmd_outcome.has_succeeded)

    def test_missing_program_is_exit_status_127(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_outcome = manage_shell.query_cmd_and_capture_outcome(
                cmd_parts=["huginn-no-such-program"],
            )
        self.assertEqual(cmd_outcome.exit_code, 127)
        self.assertEqual(cmd_outcome.stderr, "command not found: `huginn-no-such-program`.")


class TestQueryCmdAndDiscardOutput_Behaviour(unittest.TestCase):

    def test_prints_nothing_and_returns_the_exit_code(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            exit_code = manage_shell.query_cmd_and_discard_output(cmd_parts=["false"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_passes_working_directory(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            manage_shell.query_cmd_and_discard_output(
                cmd_parts=["true"],
                working_directory=Path("/tmp"),
            )
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
