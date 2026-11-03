## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import datetime
from pathlib import Path

## third-party
from rich import markup as rich_markup
from rich.console import Console as rich_Console
from rich.text import Text as rich_Text

## local
from huginn import params

##
## === ACTIVE PARAMS
##

_active_tool_params = params.ToolParams()
_active_log_file_path: Path | None = None
_CONSOLE_STDERR = rich_Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_STDOUT = rich_Console(
    highlight=False,
    stderr=False,
)


def set_params(
    *,
    tool_params: params.ToolParams,
    log_file_path: Path | None,
) -> None:
    """Set how output behaves for the rest of the process."""
    global _active_tool_params, _active_log_file_path
    _active_tool_params = tool_params
    _active_log_file_path = log_file_path


def reset_params() -> None:
    """Return to the defaults: actions shown, no log file."""
    set_params(
        tool_params=params.ToolParams(),
        log_file_path=None,
    )


def get_active_tool_params() -> params.ToolParams:
    return _active_tool_params


##
## === ROUTING
## a rendered message goes to the terminal and, when a log file is set, to the log file.
##


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
    """The log file could not be written, so the run stops before anything else is done."""


def append_to_log_file(
    msg_rendered: str,
) -> None:
    """Append one time-stamped line to the log file only; nothing is written in dry-run or when no log file is set."""
    msg_plain = rich_Text.from_markup(msg_rendered).plain
    if _active_tool_params.dry_run or (_active_log_file_path is None):
        return
    msg_for_log_file = f"[{_get_time_stamp()}] {msg_plain}\n"
    try:
        _active_log_file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        with open(_active_log_file_path, "a") as log_stream:
            log_stream.write(msg_for_log_file)
    except OSError as os_error:
        raise LogFileError(
            f"cannot write the log file `{_active_log_file_path}`: {os_error.strerror}.",
        ) from os_error


def route_msg(
    msg_rendered: str,
    *,
    is_result: bool = False,
    is_action: bool = False,
) -> None:
    """
    Send one rendered message to each destination it belongs in: the log file when one is set, then the console.

    The log comes first, so a message that cannot be logged is never shown as if its action went ahead. A hidden
    action is left off the console but still logged; the log file is never written in dry-run.
    """
    append_to_log_file(msg_rendered)
    action_is_hidden = is_action and _active_tool_params.hide_actions
    if not action_is_hidden:
        _print_to_console(
            msg_rendered=msg_rendered,
            is_result=is_result,
        )


## } MODULE
