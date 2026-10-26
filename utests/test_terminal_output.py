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
from heimdall import _terminal_output

##
## === TEST SUITE
##


class TestMessageType_Legend(unittest.TestCase):

    def test_every_message_type_has_a_description(
        self,
    ) -> None:
        for message_type in _terminal_output.MessageType:
            self.assertNotEqual(message_type.value.description, "")

    def test_declaration_order_is_the_legend_order(
        self,
    ) -> None:
        self.assertEqual(
            [_message_type.name for _message_type in _terminal_output.MessageType],
            ["STEP", "SUCCESS", "ERROR", "ACTION", "SKIPPED", "QUERY", "CONTEXT"],
        )


class TestEmit_Streams(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def test_narration_goes_to_stderr_by_default(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            _terminal_output.emit("narration")
        self.assertEqual(stdout_buffer.getvalue(), "")
        self.assertIn("narration", stderr_buffer.getvalue())

    def test_narration_can_go_to_stdout(
        self,
    ) -> None:
        _terminal_output.set_output_params(
            tool_name="tool",
            show_timestamps=False,
            record_path=None,
            narration_stream=_terminal_output.OutputStream.STDOUT,
            dry_run=False,
        )
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            _terminal_output.emit("narration")
        self.assertIn("narration", stdout_buffer.getvalue())
        self.assertEqual(stderr_buffer.getvalue(), "")

    def test_results_always_go_to_stdout(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(io.StringIO()):
            _terminal_output.emit(
                "result",
                is_result=True,
            )
        self.assertIn("result", stdout_buffer.getvalue())


class TestEmit_Timestamps(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def test_off_by_default(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _terminal_output.emit("plain")
        self.assertEqual(stderr_buffer.getvalue(), "plain\n")

    def test_prefix_when_enabled(
        self,
    ) -> None:
        _terminal_output.set_output_params(
            tool_name="tool",
            show_timestamps=True,
            record_path=None,
            narration_stream=_terminal_output.OutputStream.STDERR,
            dry_run=False,
        )
        stderr_buffer = io.StringIO()
        with mock.patch.object(_terminal_output, "get_timestamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(stderr_buffer):
                _terminal_output.emit("stamped")
        self.assertEqual(stderr_buffer.getvalue(), "[2026-01-02 03:04:05] stamped\n")


class TestEmit_Record(unittest.TestCase):

    record_path: Path

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.record_path = Path(temporary_directory.name) / "logs" / "record.log"

    def _start_recording(
        self,
        *,
        dry_run: bool,
    ) -> None:
        _terminal_output.set_output_params(
            tool_name="tool",
            show_timestamps=False,
            record_path=self.record_path,
            narration_stream=_terminal_output.OutputStream.STDERR,
            dry_run=dry_run,
        )

    def test_appends_plain_lines(
        self,
    ) -> None:
        self._start_recording(dry_run=False)
        with mock.patch.object(_terminal_output, "get_timestamp", return_value="2026-01-02 03:04:05"):
            with contextlib.redirect_stderr(io.StringIO()):
                _terminal_output.emit_message(
                    message_type=_terminal_output.MessageType.STEP,
                    text_markup="first",
                    color_whole_line=False,
                )
                _terminal_output.emit("[bold]second[/bold]")
        self.assertEqual(
            self.record_path.read_text().splitlines(),
            [
                "[2026-01-02 03:04:05] (tool): ○ first",
                "[2026-01-02 03:04:05] (tool): second",
            ],
        )

    def test_not_written_in_dry_run(
        self,
    ) -> None:
        self._start_recording(dry_run=True)
        with contextlib.redirect_stderr(io.StringIO()):
            _terminal_output.emit("nothing happens")
        self.assertFalse(self.record_path.exists())

    def test_off_by_default(
        self,
    ) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            _terminal_output.emit("nowhere")
        self.assertFalse(self.record_path.exists())


class TestEscapeMarkup_Text(unittest.TestCase):

    def test_brackets_print_literally(
        self,
    ) -> None:
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            _terminal_output.emit(_terminal_output.escape_markup("[bold]x[/bold]"))
        self.assertEqual(stderr_buffer.getvalue(), "[bold]x[/bold]\n")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
