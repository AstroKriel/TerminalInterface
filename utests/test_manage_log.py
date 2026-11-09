## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import contextlib
import io
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest import mock

## local
from huginn import _manage_output, cmd_args, manage_log

##
## === TEST SUITE
##


class TestLogFunctions_Output(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_active_state()
        self.addCleanup(_manage_output.reset_active_state)

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

    def test_log_outcome_prints_its_values_indented_under_it(
        self,
    ) -> None:
        _, stderr_text = self._capture(
            lambda: manage_log.log_outcome(
                "saved",
                status=manage_log.OutcomeStatus.SUCCESS,
                values={
                    "path": "/tmp/out.json",
                    "count": 3,
                },
            ),
        )
        self.assertEqual(stderr_text, "● saved\n    · path = /tmp/out.json\n    · count = 3\n")

    def test_log_note_prints_its_values_literally(
        self,
    ) -> None:
        _, stderr_text = self._capture(
            lambda: manage_log.log_note(
                "parameters",
                values={"pattern": "[bold]x"},
            ),
        )
        self.assertEqual(stderr_text, "↪ parameters\n    · pattern = [bold]x\n")

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

    def test_raw_text_prints_exactly_as_written(
        self,
    ) -> None:
        stdout_text, _ = self._capture(lambda: manage_log.log_result("[News] title"))
        self.assertEqual(stdout_text, "[News] title\n")
        _, stderr_text = self._capture(lambda: manage_log.log_task("checking [red]pins[/]"))
        self.assertEqual(stderr_text, "○ checking [red]pins[/]\n")

    def test_exit_with_error_exits_with_status_one(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(SystemExit) as exit_context:
            manage_log.exit_with_error("broken")
        self.assertEqual(exit_context.exception.code, 1)
        self.assertEqual(stderr_buffer.getvalue(), "● error: broken\n")


class TestAsk_Answers(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_output.reset_active_state()
        self.addCleanup(_manage_output.reset_active_state)

    def _ask(
        self,
        *,
        answers: list[str],
        input_value_type: cmd_args.InputValueType,
    ) -> tuple[Any, str]:
        stderr_buffer = io.StringIO()
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stderr(stderr_buffer):
            answer = manage_log.ask(
                "save it again?",
                input_value_type=input_value_type,
            )
        return (answer, stderr_buffer.getvalue())

    def test_yes_or_no_shows_the_default_and_a_piped_answer(
        self,
    ) -> None:
        _, stderr_text = self._ask(
            answers=["y"],
            input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
        )
        self.assertEqual(stderr_text, "? save it again? [y/N] y\n")

    def test_yes_or_no_is_yes_only_for_an_answer_starting_with_y(
        self,
    ) -> None:
        for answer_text, expected_answer in [
            ("y", True),
            ("Yes", True),
            ("", False),
            ("n", False),
            ("maybe", False),
        ]:
            answer, _ = self._ask(
                answers=[answer_text],
                input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
            )
            self.assertEqual(answer, expected_answer)

    def test_value_is_converted(
        self,
    ) -> None:
        answer, _ = self._ask(
            answers=[" 45 "],
            input_value_type=cmd_args.InputValueTypes.NUMBER,
        )
        self.assertEqual(answer, 45)

    def test_bad_answer_reports_a_failure_and_asks_again(
        self,
    ) -> None:
        answer, stderr_text = self._ask(
            answers=["", "many", "7"],
            input_value_type=cmd_args.InputValueTypes.NUMBER,
        )
        self.assertEqual(answer, 7)
        self.assertIn("● answer must not be empty.\n", stderr_text)
        self.assertIn("● answer must be <number>; got `many`.\n", stderr_text)
        self.assertEqual(stderr_text.count("? save it again? "), 3)

    def test_no_answer_ends_the_run(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with (
                mock.patch("builtins.input", side_effect=EOFError),
                contextlib.redirect_stderr(stderr_buffer),
                self.assertRaises(SystemExit) as exit_context,
        ):
            manage_log.ask(
                "save it again?",
                input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
            )
        self.assertEqual(exit_context.exception.code, 1)
        self.assertIn(
            "● error: no answer to `save it again? [y/N]`: input ended.\n",
            stderr_buffer.getvalue(),
        )

    def test_unset_log_file_path_raises_before_asking(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with (
                mock.patch.object(_manage_output._active_state, "log_file_path_is_set", False),
                mock.patch("builtins.input") as mock_input,
                contextlib.redirect_stderr(stderr_buffer),
                self.assertRaises(_manage_output.LogFileError),
        ):
            manage_log.ask(
                "save it again?",
                input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
            )
        mock_input.assert_not_called()
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_question_and_answer_are_logged_as_one_line(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        log_file_path = Path(temporary_directory.name) / "tool.log"
        manage_log.set_log_file_path(log_file_path=log_file_path)
        self._ask(
            answers=["y"],
            input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
        )
        log_lines = log_file_path.read_text().splitlines()
        self.assertTrue(log_lines[-1].endswith("] ? save it again? [y/N] y"))


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
