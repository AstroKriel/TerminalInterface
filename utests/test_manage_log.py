## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import contextlib
import io
import unittest
from collections.abc import Callable

## local
from huginn import _manage_terminal, manage_log

##
## === TEST SUITE
##


class TestLogFunctions_Output(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def _capture(
        self,
        log_call: Callable[[], None],
    ) -> tuple[str, str]:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            log_call()
        return (stdout_buffer.getvalue(), stderr_buffer.getvalue())

    def test_log_note_writes_to_stderr_with_its_symbol(
        self,
    ) -> None:
        stdout_text, stderr_text = self._capture(lambda: manage_log.log_note("this rewrites history"))
        self.assertEqual(stdout_text, "")
        self.assertEqual(stderr_text, "↪ this rewrites history\n")

    def test_log_task_includes_symbol_and_text(
        self,
    ) -> None:
        _, stderr_text = self._capture(lambda: manage_log.log_task("doing something"))
        self.assertEqual(stderr_text, "○ doing something\n")

    def test_log_outcome_prints_every_status(
        self,
    ) -> None:
        for outcome_status in manage_log.OutcomeStatus:
            _, stderr_text = self._capture(
                lambda: manage_log.log_outcome("it ended", status=outcome_status),
            )
            self.assertEqual(stderr_text, "● it ended\n")

    def test_log_outcome_requires_a_status(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            manage_log.log_outcome("it ended")  # pyright: ignore[reportCallIssue]

    def test_log_value_prints_value_literally(
        self,
    ) -> None:
        _, stderr_text = self._capture(
            lambda: manage_log.log_value(
                name="pattern",
                value="[bold]x",
            ),
        )
        self.assertEqual(stderr_text, "· pattern = [bold]x\n")

    def test_log_result_writes_plain_text_to_stdout(
        self,
    ) -> None:
        stdout_text, stderr_text = self._capture(lambda: manage_log.log_result("ahead: 2; behind: 0"))
        self.assertEqual(stderr_text, "")
        self.assertEqual(stdout_text, "ahead: 2; behind: 0\n")

    def test_log_result_is_never_wrapped(
        self,
    ) -> None:
        long_result = " ".join(f"word{_word_index}" for _word_index in range(40))
        stdout_text, _ = self._capture(lambda: manage_log.log_result(long_result))
        self.assertEqual(stdout_text, f"{long_result}\n")

    def test_log_result_has_no_timestamp(
        self,
    ) -> None:
        _manage_terminal.set_output_params(
            output_params=manage_log.OutputParams(show_timestamps=True),
            dry_run=False,
        )
        stdout_text, _ = self._capture(lambda: manage_log.log_result("data"))
        self.assertEqual(stdout_text, "data\n")

    def test_escape_markup_keeps_brackets(
        self,
    ) -> None:
        stdout_text, _ = self._capture(
            lambda: manage_log.log_result(manage_log.escape_markup("[News] title")),
        )
        self.assertEqual(stdout_text, "[News] title\n")

    def test_exit_with_error_exits_with_status_one(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(SystemExit) as exit_context:
            manage_log.exit_with_error("broken")
        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "● error: broken\n")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
