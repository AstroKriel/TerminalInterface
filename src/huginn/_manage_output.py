## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import dataclasses
import datetime
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Self

## third-party
from rich import markup as rich_markup
from rich.console import Console as rich_Console
from rich.text import Text as rich_Text

##
## === BUILT-IN PARAMS
##


@dataclass(frozen=True)
class BuiltInParams:
    """The values of the built-in flags for one run, e.g. `--dry-run`; huginn reads them, so a cmd never needs them."""
    dry_run: bool = False
    hide_actions: bool = False

    @classmethod
    def from_parsed_args(
        cls,
        parsed_args: argparse.Namespace,
    ) -> Self:
        """Fill every field from the flag of the same name; a field with no flag raises `AttributeError`."""
        flag_values = {_field.name: getattr(parsed_args, _field.name) for _field in dataclasses.fields(cls)}
        return cls(**flag_values)


##
## === ACTIVE STATE
##


@dataclass
class _ActiveState:
    """
    What huginn tracks for the current run.

    This covers the built-in params the user passed, the log file path set by the tool or script, and whether the
    invoked cmd of this run was written to that log file yet.
    """
    built_in_params: BuiltInParams = dataclasses.field(default_factory=BuiltInParams)
    log_file_path_is_set: bool = False
    log_file_path: Path | None = None
    invoked_cmd_was_written_to_log_file: bool = False


_active_state = _ActiveState()


def set_built_in_params(
    built_in_params: BuiltInParams,
) -> None:
    _active_state.built_in_params = built_in_params


def set_log_file_path(
    *,
    log_file_path: Path | None,
) -> None:
    """Log to `log_file_path` from here on, or to nothing for `None`; a new log file starts with the invoked cmd."""
    _active_state.log_file_path_is_set = True
    _active_state.log_file_path = log_file_path
    _active_state.invoked_cmd_was_written_to_log_file = False


def reset_active_state() -> None:
    """Return to the defaults: actions shown, and no log file."""
    global _active_state
    _active_state = _ActiveState(log_file_path_is_set=True)


def get_active_built_in_params() -> BuiltInParams:
    return _active_state.built_in_params


##
## === ROUTING
## a rendered message goes to the terminal and, unless the log file is `None`, to the log file.
##

_CONSOLE_STDERR = rich_Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_STDOUT = rich_Console(
    highlight=False,
    stderr=False,
)


def _get_time_stamp() -> str:
    return datetime.datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )


def escape_markup(
    text: str,
) -> str:
    """Make text print exactly as written, even where it looks like rich markup."""
    return rich_markup.escape(text)


def _print_to_console(
    *,
    msg_rendered: str,
    is_result: bool,
) -> None:
    """
    Print to stdout for a result, or to stderr for narration.

    A result is data for the user or a pipe, so it is never wrapped at the terminal width. Narration wraps at the
    terminal width in a terminal, and is never wrapped elsewhere, e.g. in a job, so each message stays one line.
    """
    if is_result:
        _CONSOLE_STDOUT.print(
            msg_rendered,
            soft_wrap=True,
        )
    else:
        narration_is_unwrapped = not _CONSOLE_STDERR.is_terminal
        _CONSOLE_STDERR.print(
            msg_rendered,
            soft_wrap=narration_is_unwrapped,
        )


class LogFileError(Exception):
    """No log file path was set, or the log file could not be written, so the run stops before anything else is done."""


def _check_log_file_path_is_set() -> None:
    if not _active_state.log_file_path_is_set:
        raise LogFileError(
            "no log file path set; call `manage_log.set_log_file_path` with a path, or with `None` to log nothing.",
        )


def append_to_log_file(
    msg_rendered: str,
) -> None:
    """
    Append one time-stamped line to the log file only, after the invoked cmd when it is the first line of this run.

    Nothing is written in dry-run or when the log file is `None`. Logging before the log file path is set raises,
    even in dry-run, so a tool or script that forgot to set it finds out on its first message.
    """
    _check_log_file_path_is_set()
    log_file_path = _active_state.log_file_path
    if _active_state.built_in_params.dry_run or (log_file_path is None):
        return
    msg_plain = rich_Text.from_markup(msg_rendered).plain
    log_lines: list[str] = []
    if not _active_state.invoked_cmd_was_written_to_log_file:
        invoked_cmd_parts = [Path(sys.argv[0]).name, *sys.argv[1:]]
        invoked_cmd = shlex.join(invoked_cmd_parts)
        msg_text = f"$ {invoked_cmd}"
        log_lines.append(msg_text)
    log_lines.append(msg_plain)
    time_stamp = _get_time_stamp()
    msg_for_log_file = "".join(f"[{time_stamp}] {_log_line}\n" for _log_line in log_lines)
    try:
        log_file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with open(log_file_path, "a") as log_stream:
            log_stream.write(msg_for_log_file)
    except OSError as os_error:
        raise LogFileError(
            f"cannot write the log file `{log_file_path}`: {os_error.strerror}.",
        ) from os_error
    _active_state.invoked_cmd_was_written_to_log_file = True


def route_msg(
    msg_rendered: str,
    *,
    is_result: bool = False,
    is_action: bool = False,
) -> None:
    """
    Send one rendered message to each destination it belongs in: the log file unless it is `None`, then the console.

    The log comes first, so a message that cannot be logged is never shown as if its action went ahead. A hidden
    action is left off the console but still logged; the log file is never written in dry-run.
    """
    append_to_log_file(msg_rendered)
    action_is_hidden = is_action and _active_state.built_in_params.hide_actions
    if not action_is_hidden:
        _print_to_console(
            msg_rendered=msg_rendered,
            is_result=is_result,
        )


def read_answer(
    question_rendered: str,
) -> str | None:
    """
    Show a question on stderr, read the answer typed on the same line, then log both as one line.

    An answer piped in is not echoed by the terminal, so it is printed after the question, and the output reads the
    same as a typed answer. Returns `None` when input ends without an answer, e.g. in a job with nothing to read.
    """
    _check_log_file_path_is_set()
    try:
        answer = _CONSOLE_STDERR.input(f"{question_rendered} ")
    except EOFError:
        _CONSOLE_STDERR.print()
        return None
    answer_markup = escape_markup(answer)
    answer_was_echoed = sys.stdin.isatty()
    if not answer_was_echoed:
        _CONSOLE_STDERR.print(answer_markup)
    append_to_log_file(f"{question_rendered} {answer_markup}")
    return answer


## } MODULE
