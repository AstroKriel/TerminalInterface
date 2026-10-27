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
from heimdall import _manage_terminal

##
## === TEST SUITE
##


class TestLegend_Groups(unittest.TestCase):

    def test_groups_follow_the_concepts(
        self,
    ) -> None:
        self.assertEqual(
            [_message_group.title for _message_group in _manage_terminal.MESSAGE_GROUPS],
            ["Tasks", "Notes", "Actions", "Outcomes"],
        )

    def test_every_type_status_and_content_is_in_its_group(
        self,
    ) -> None:
        tasks_group, notes_group, actions_group, outcomes_group = _manage_terminal.MESSAGE_GROUPS
        self.assertEqual(tasks_group.grouped_message_styles, (_manage_terminal.TASK_STYLE, ))
        self.assertEqual(notes_group.grouped_message_styles, (_manage_terminal.NOTE_STYLE, ))
        for action in _manage_terminal.Action:
            self.assertIn(action.value, actions_group.grouped_message_styles)
        for outcome_status in _manage_terminal.OutcomeStatus:
            self.assertIn(outcome_status.value, outcomes_group.grouped_message_styles)
        for outcome_content in _manage_terminal.OutcomeContent:
            self.assertIn(outcome_content.value, outcomes_group.grouped_message_styles)

    def test_every_message_style_has_a_description(
        self,
    ) -> None:
        for message_group in _manage_terminal.MESSAGE_GROUPS:
            for message_style in message_group.grouped_message_styles:
                self.assertNotEqual(message_style.description, "")

    def test_result_has_no_symbol_or_colour(
        self,
    ) -> None:
        result_style = _manage_terminal.OutcomeContent.RESULT.value
        self.assertIsNone(result_style.symbol)
        self.assertIsNone(result_style.colour)

    def test_only_failure_and_error_share_a_colour(
        self,
    ) -> None:
        outcome_status = _manage_terminal.OutcomeStatus
        self.assertEqual(outcome_status.FAILURE.value.colour, outcome_status.ERROR.value.colour)
        other_colours = [
            _outcome_status.value.colour
            for _outcome_status in outcome_status
            if _outcome_status is not outcome_status.ERROR
        ]
        self.assertEqual(len(set(other_colours)), len(other_colours))


class TestRenderLine_Markup(unittest.TestCase):

    def test_colours_only_the_symbol(
        self,
    ) -> None:
        line_markup = _manage_terminal.render_line(
            symbol=_manage_terminal.Symbol.OPEN_CIRCLE,
            colour=_manage_terminal.Colour.WHITE,
            text_markup="task",
            colour_whole_line=False,
        )
        self.assertEqual(line_markup, "[#FFFFFF]○[/] task")

    def test_colours_the_whole_line(
        self,
    ) -> None:
        line_markup = _manage_terminal.render_line(
            symbol=_manage_terminal.Symbol.CLOSED_CIRCLE,
            colour=_manage_terminal.Colour.GREEN,
            text_markup="done",
            colour_whole_line=True,
        )
        self.assertEqual(line_markup, "[#32CD32]● done[/]")

    def test_renders_plain_without_symbol_or_colour(
        self,
    ) -> None:
        line_markup = _manage_terminal.render_line(
            symbol=None,
            colour=None,
            text_markup="plain",
            colour_whole_line=True,
        )
        self.assertEqual(line_markup, "plain")


class TestWriteLine_Streams(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def test_narration_goes_to_stderr(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            _manage_terminal.write_line("narration")
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("narration", stderr_buffer.getvalue())

    def test_results_always_go_to_stdout(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(io.StringIO()):
            _manage_terminal.write_line(
                "result",
                is_result=True,
            )
        self.assertIn("result", stdout_buffer.getvalue())


class TestWriteLine_Timestamps(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def test_off_by_default(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_terminal.write_line("plain")
        self.assertEqual(stderr_buffer.getvalue(), "plain\n")

    def test_prefix_when_enabled(
        self,
    ) -> None:
        _manage_terminal.set_output_params(
            show_timestamps=True,
            log_path=None,
            dry_run=False,
        )
        stderr_buffer = io.StringIO()
        with mock.patch.object(_manage_terminal, "get_timestamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(stderr_buffer):
                _manage_terminal.write_line("stamped")
        self.assertEqual(stderr_buffer.getvalue(), "[2026-01-02 03:04:05] stamped\n")


class TestWriteLine_Log(unittest.TestCase):

    log_path: Path

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.log_path = Path(temporary_directory.name) / "logs" / "tool.log"

    def _start_logging(
        self,
        *,
        dry_run: bool,
    ) -> None:
        _manage_terminal.set_output_params(
            show_timestamps=False,
            log_path=self.log_path,
            dry_run=dry_run,
        )

    def test_appends_plain_lines(
        self,
    ) -> None:
        self._start_logging(dry_run=False)
        with mock.patch.object(_manage_terminal, "get_timestamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(io.StringIO()):
                _manage_terminal.write_line("[#FFFFFF]○[/] first")
                _manage_terminal.write_line("[bold]second[/bold]")
        self.assertEqual(
            self.log_path.read_text().splitlines(),
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
            _manage_terminal.write_line("nothing happens")
        self.assertFalse(self.log_path.exists())

    def test_off_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            _manage_terminal.write_line("nowhere")
        self.assertFalse(self.log_path.exists())


class TestEscapeMarkup_Text(unittest.TestCase):

    def test_brackets_print_literally(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _manage_terminal.write_line(_manage_terminal.escape_markup("[bold]x[/bold]"))
        self.assertEqual(stderr_buffer.getvalue(), "[bold]x[/bold]\n")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
