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
from collections.abc import Callable
from pathlib import Path
from unittest import mock

## local
from heimdall import _terminal_output, shell_interface

##
## === TEST SUITE
##


class TestRunParams_Defaults(unittest.TestCase):

    def test_dry_run_is_false(
        self,
    ) -> None:
        self.assertFalse(shell_interface.RunParams().dry_run)

    def test_subclass_passes_through_runners(
        self,
    ) -> None:
        @dataclasses.dataclass(frozen=True)
        class ToolRunParams(shell_interface.RunParams):
            allow_dirty: bool = False

        tool_run_params = ToolRunParams(dry_run=True, allow_dirty=True)
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            shell_interface.run_cmd_and_show_output(run_params=tool_run_params, cmd=["git", "push"])
        mock_run.assert_not_called()


class TestLogFunctions_Output(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def _capture(
        self,
        log_call: Callable[[], None],
    ) -> tuple[str, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            log_call()
        return (stdout_buffer.getvalue(), stderr_buffer.getvalue())

    def test_log_message_writes_to_stderr(
        self,
    ) -> None:
        stdout_text, stderr_text = self._capture(lambda: shell_interface.log_message("hello"))
        self.assertEqual(stdout_text, "")
        self.assertIn("hello", stderr_text)

    def test_log_task_includes_marker_and_message(
        self,
    ) -> None:
        _, stderr_text = self._capture(lambda: shell_interface.log_task("doing something"))
        self.assertEqual(stderr_text, "○ doing something\n")

    def test_log_outcome_prints_every_status(
        self,
    ) -> None:
        for outcome_status in shell_interface.OutcomeStatus:
            _, stderr_text = self._capture(
                lambda: shell_interface.log_outcome("it ended", status=outcome_status),
            )
            self.assertEqual(stderr_text, "● it ended\n")

    def test_log_outcome_requires_a_status(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            shell_interface.log_outcome("it ended")  # pyright: ignore[reportCallIssue]

    def test_log_value_prints_value_literally(
        self,
    ) -> None:
        _, stderr_text = self._capture(
            lambda: shell_interface.log_value(name="pattern", value="[bold]x"),
        )
        self.assertEqual(stderr_text, "· pattern = [bold]x\n")

    def test_log_result_writes_plain_text_to_stdout(
        self,
    ) -> None:
        stdout_text, stderr_text = self._capture(lambda: shell_interface.log_result("ahead: 2; behind: 0"))
        self.assertEqual(stderr_text, "")
        self.assertEqual(stdout_text, "ahead: 2; behind: 0\n")

    def test_log_result_is_never_wrapped(
        self,
    ) -> None:
        long_result = " ".join(f"word{_word_index}" for _word_index in range(40))
        stdout_text, _ = self._capture(lambda: shell_interface.log_result(long_result))
        self.assertEqual(stdout_text, f"{long_result}\n")

    def test_log_result_has_no_timestamp(
        self,
    ) -> None:
        _terminal_output.set_output_params(
            tool_name="tool",
            show_timestamps=True,
            record_path=None,
            narration_stream=_terminal_output.OutputStream.STDERR,
            dry_run=False,
        )
        stdout_text, _ = self._capture(lambda: shell_interface.log_result("data"))
        self.assertEqual(stdout_text, "data\n")

    def test_escape_markup_keeps_brackets(
        self,
    ) -> None:
        stdout_text, _ = self._capture(
            lambda: shell_interface.log_result(shell_interface.escape_markup("[News] title")),
        )
        self.assertEqual(stdout_text, "[News] title\n")

    def test_exit_with_error_exits_with_status_one(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(SystemExit) as exit_context:
            shell_interface.exit_with_error("broken")
        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "● error: broken\n")


class TestPrintedCommands_Quoting(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def _print_query(
        self,
        cmd: list[str],
    ) -> str:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(stdout="", returncode=0)
            shell_interface.query_cmd_and_capture_output(cmd=cmd)
        return stderr_buffer.getvalue()

    def test_argument_with_spaces_is_quoted(
        self,
    ) -> None:
        self.assertEqual(self._print_query(["git", "commit", "-m", "a message"]), "→ git commit -m 'a message'\n")

    def test_brackets_in_arguments_print_literally(
        self,
    ) -> None:
        self.assertEqual(self._print_query(["ls", "[red]"]), "→ ls '[red]'\n")


class TestRunners_KeywordOnly(unittest.TestCase):

    def test_positional_arguments_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            shell_interface.query_cmd_and_capture_output(["true"])  # pyright: ignore[reportCallIssue]
        with self.assertRaises(TypeError):
            shell_interface.query_cmd_and_discard_output(["true"])  # pyright: ignore[reportCallIssue]


class TestRunCmdAndShowOutput_Behaviour(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def test_dry_run_skips_logs_and_counts_as_success(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            command_succeeded = shell_interface.run_cmd_and_show_output(
                run_params=shell_interface.RunParams(dry_run=True),
                cmd=["git", "push"],
            )
        mock_run.assert_not_called()
        self.assertTrue(command_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ (dryrun) skipped: git push\n")

    def test_logs_and_executes_when_not_dry_run(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(stderr_buffer):
            mock_run.return_value = mock.MagicMock(returncode=0)
            command_succeeded = shell_interface.run_cmd_and_show_output(
                run_params=shell_interface.RunParams(),
                cmd=["git", "status"],
            )
        mock_run.assert_called_once()
        self.assertTrue(command_succeeded)
        self.assertEqual(stderr_buffer.getvalue(), "→ git status\n")

    def test_failure_raises_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            shell_interface.run_cmd_and_show_output(run_params=shell_interface.RunParams(), cmd=["false"])

    def test_failure_returns_false_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            command_succeeded = shell_interface.run_cmd_and_show_output(
                run_params=shell_interface.RunParams(),
                cmd=["false"],
                raise_error=False,
            )
        self.assertFalse(command_succeeded)


class TestRunCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def test_returns_empty_string_in_dry_run(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            captured_output = shell_interface.run_cmd_and_capture_output(
                run_params=shell_interface.RunParams(dry_run=True),
                cmd=["git", "rev-list", "--count", "HEAD"],
            )
        mock_run.assert_not_called()
        self.assertEqual(captured_output, "")

    def test_strips_and_passes_cwd(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            mock_run.return_value = mock.MagicMock(stdout="3\n", returncode=0)
            captured_output = shell_interface.run_cmd_and_capture_output(
                run_params=shell_interface.RunParams(),
                cmd=["git", "rev-list", "--count", "HEAD"],
                cwd=Path("/tmp"),
            )
        self.assertEqual(captured_output, "3")
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


class TestQueryCmdAndCaptureOutput_Behaviour(unittest.TestCase):

    def test_raises_on_failure_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            shell_interface.query_cmd_and_capture_output(cmd=["false"])

    def test_returns_empty_string_when_not_raising(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            query_output = shell_interface.query_cmd_and_capture_output(cmd=["false"], raise_error=False)
        self.assertEqual(query_output, "")

    def test_passes_cwd(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run, contextlib.redirect_stderr(io.StringIO()):
            mock_run.return_value = mock.MagicMock(stdout="main\n", returncode=0)
            shell_interface.query_cmd_and_capture_output(cmd=["git", "branch", "--show-current"], cwd=Path("/tmp"))
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


class TestQueryCmdAndCaptureOutcome_Outcome(unittest.TestCase):

    working_directory: Path

    def setUp(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.working_directory = Path(temporary_directory.name)

    def test_records_command_output_and_exit_code(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            command_outcome = shell_interface.query_cmd_and_capture_outcome(cmd=["echo", "a b"], cwd=self.working_directory)
        self.assertEqual(command_outcome.command, "echo 'a b'")
        self.assertEqual(command_outcome.working_directory, self.working_directory)
        self.assertEqual(command_outcome.stdout, "a b\n")
        self.assertTrue(command_outcome.succeeded)

    def test_does_not_raise_on_failure(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            command_outcome = shell_interface.query_cmd_and_capture_outcome(cmd=["false"])
        self.assertFalse(command_outcome.succeeded)

    def test_missing_program_is_exit_status_127(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            command_outcome = shell_interface.query_cmd_and_capture_outcome(cmd=["heimdall-no-such-program"])
        self.assertEqual(command_outcome.exit_code, 127)
        self.assertEqual(command_outcome.stderr, "command not found: `heimdall-no-such-program`.")


class TestQueryCmdAndDiscardOutput_Behaviour(unittest.TestCase):

    def test_prints_nothing_and_returns_the_exit_code(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            exit_code = shell_interface.query_cmd_and_discard_output(cmd=["false"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_passes_cwd(
        self,
    ) -> None:
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.MagicMock(returncode=0)
            shell_interface.query_cmd_and_discard_output(cmd=["true"], cwd=Path("/tmp"))
        self.assertEqual(mock_run.call_args.kwargs["cwd"], Path("/tmp"))


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
