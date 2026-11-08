## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import sys
from pathlib import Path
from typing import NoReturn

## local
from huginn import _manage_output, _message_styles
from huginn._message_styles import OutcomeStatus as OutcomeStatus

##
## === LOG FILE
## every tool and script sets its log file path before its first message: a path, or `None` to log nothing.
##


def set_log_file_path(
    *,
    log_file_path: Path | None,
) -> None:
    _manage_output.set_log_file_path(log_file_path=log_file_path)


def get_home_log_file_path(
    *,
    tool_name: str,
) -> Path:
    return Path.home() / ".huginn_logs" / f"{tool_name}.log"


##
## === OUTPUT
## `text` is raw text: it always prints exactly as written, so a tool supplies the text and the kind of message,
## and huginn handles the styling.
##


def _render_and_route_msg(
    *,
    message_style: _message_styles.MessageStyle,
    text: str,
) -> None:
    msg_rendered = message_style.render(text=text)
    _manage_output.route_msg(msg_rendered)


def log_note(
    text: str,
) -> None:
    """Note something about the work that is neither a task nor an outcome."""
    _render_and_route_msg(
        message_style=_message_styles.NOTE_STYLE,
        text=text,
    )


def log_task(
    text: str,
) -> None:
    """Announce a task that is starting."""
    _render_and_route_msg(
        message_style=_message_styles.TASK_STYLE,
        text=text,
    )


def log_outcome(
    text: str,
    *,
    status: OutcomeStatus,
) -> None:
    """Report how a task or action ended; the status sets the colour and is never assumed."""
    _render_and_route_msg(
        message_style=status.value,
        text=text,
    )


def log_value(
    *,
    name: str,
    value: str,
) -> None:
    """Report a value that an action produced, by inspecting or by changing the system; the value prints exactly as written."""
    _render_and_route_msg(
        message_style=_message_styles.OutcomeContent.VALUE.value,
        text=f"{name} = {value}",
    )


def log_result(
    text: str,
) -> None:
    """Print a result for the user or a pipe: plain text on stdout, with no symbol, colour, time stamp, or wrapping."""
    msg_rendered = _message_styles.OutcomeContent.RESULT.value.render(
        text=text,
    )
    _manage_output.route_msg(
        msg_rendered,
        is_result=True,
    )


def exit_with_error(
    text: str,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Report an error that ends the run, then exit the process with `exit_code`."""
    _render_and_route_msg(
        message_style=OutcomeStatus.ERROR.value,
        text=f"error: {text}",
    )
    sys.exit(exit_code)


## } MODULE
