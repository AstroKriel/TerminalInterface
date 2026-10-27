## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import contextlib
import dataclasses
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

## local
from huginn import _manage_terminal, manage_shell

##
## === TEST SUITE
##


class TestRunParams_Defaults(unittest.TestCase):

    def test_dry_run_is_false(
        self,
    ) -> None:
        self.assertFalse(manage_shell.RunParams().dry_run)

    def test_subclass_passes_through_runners(
        self,
    ) -> None:

        @dataclasses.dataclass(frozen=True)
        class ToolRunParams(manage_shell.RunParams):
            allow_dirty: bool = False

        tool_run_params = ToolRunParams(
            dry_run=True,
            allow_dirty=True,
        )
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            manage_shell.run_cmd_and_show_output(
                run_params=tool_run_params,
                cmd=["git", "push"],
            )
        mock_run.assert_not_called()


class TestPrintedCmds_Quoting(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def _print_query(
        self,
        cmd: list[str],
    ) -> str:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(
                stdout="",
                returncode=0,
            )
            manage_shell.query_cmd_and_capture_output(cmd=cmd)
        return stderr_buffer.getvalue()

    def test_argument_with_spaces_is_quoted(
        self,
    ) -> None:
        self.assertEqual(
            self._print_query(["git", "commit", "-m", "a message"]),
            "→ git commit -m 'a message'\n",
        )

    def test_brackets_in_arguments_print_literally(
        self,
    ) -> None:
        self.assertEqual(self._print_query(["ls", "[red]"]), "→ ls '[red]'\n")


class TestRunners_KeywordOnly(unittest.TestCase):

    def test_positional_arguments_are_rejected(
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
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def test_dry_run_skips_logs_and_counts_as_success(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            cmd_succeeded = manage_shell.run_cmd_and_show_output(
                run_params=manage_shell.RunParams(dry_run=True),
                cmd=["git", "push"],
            )
        mock_run.assert_not_called()
        self.assertTrue(cmd_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ (dry-run) skipped: git push\n")

    def test_dry_run_line_uses_the_change_symbol_in_the_skipped_colour(
        self,
    ) -> None:
        with (
                mock.patch.object(_manage_terminal, "render_line", wraps=_manage_terminal.render_line) as
                mock_render_line,
                contextlib.redirect_stderr(io.StringIO()),
        ):
            manage_shell.run_cmd_and_show_output(
                run_params=manage_shell.RunParams(dry_run=True),
                cmd=["git", "push"],
            )
        render_kwargs = mock_render_line.call_args.kwargs
        self.assertEqual(render_kwargs["symbol"], _manage_terminal.Action.CHANGE.value.symbol)
        self.assertEqual(render_kwargs["colour"], _manage_terminal.OutcomeStatus.SKIPPED.value.colour)

    def test_logs_and_executes_when_not_dry_run(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(returncode=0)
            cmd_succeeded = manage_shell.run_cmd_and_show_output(
                run_params=manage_shell.RunParams(),
                cmd=["git", "status"],
            )
        mock_run.assert_called_once()
        self.assertTrue(cmd_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ git status\n")

    def test_failure_raises_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            manage_shell.run_cmd_and_show_output(
                run_params=manage_shell.RunParams(),
                cmd=["false"],
            )

    def test_failure_returns_false_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_succeeded = manage_shell.run_cmd_and_show_output(
                run_params=manage_shell.RunParams(),
                cmd=["false"],
                raise_error=False,
            )
        self.assertFalse(cmd_succeeded)


class TestRunCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def test_returns_empty_string_in_dry_run(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            captured_output = manage_shell.run_cmd_and_capture_output(
                run_params=manage_shell.RunParams(dry_run=True),
                cmd=["git", "rev-list", "--count", "HEAD"],
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
                run_params=manage_shell.RunParams(),
                cmd=["git", "rev-list", "--count", "HEAD"],
                working_directory=Path("/tmp"),
            )
        self.assertEqual(captured_output, "3")
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


class TestQueryCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def test_raises_on_failure_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            manage_shell.query_cmd_and_capture_output(cmd=["false"])

    def test_returns_empty_string_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            query_output = manage_shell.query_cmd_and_capture_output(
                cmd=["false"],
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
                cmd=["git", "branch", "--show-current"],
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
                cmd=["echo", "a b"],
                working_directory=self.working_directory,
            )
        self.assertEqual(cmd_outcome.cmd, "echo 'a b'")
        self.assertEqual(cmd_outcome.working_directory, self.working_directory)
        self.assertEqual(cmd_outcome.stdout, "a b\n")
        self.assertTrue(cmd_outcome.succeeded)

    def test_does_not_raise_on_failure(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_outcome = manage_shell.query_cmd_and_capture_outcome(cmd=["false"])
        self.assertFalse(cmd_outcome.succeeded)

    def test_missing_program_is_exit_status_127(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            cmd_outcome = manage_shell.query_cmd_and_capture_outcome(
                cmd=["huginn-no-such-program"],
            )
        self.assertEqual(cmd_outcome.exit_code, 127)
        self.assertEqual(cmd_outcome.stderr, "command not found: `huginn-no-such-program`.")


class TestQueryCmdAndDiscardOutput_Behaviour(unittest.TestCase):

    def test_prints_nothing_and_returns_the_exit_code(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            exit_code = manage_shell.query_cmd_and_discard_output(cmd=["false"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_passes_working_directory(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            manage_shell.query_cmd_and_discard_output(
                cmd=["true"],
                working_directory=Path("/tmp"),
            )
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
