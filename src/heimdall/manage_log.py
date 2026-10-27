## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import sys
from typing import NoReturn

## local
from heimdall import _manage_terminal
from heimdall._manage_terminal import OutcomeStatus as OutcomeStatus
from heimdall._manage_terminal import OutputParams as OutputParams
from heimdall._manage_terminal import escape_markup as escape_markup

##
## === OUTPUT
## message text is rich markup; anything added here (resolved values) is escaped.
##


def _write_message(
    *,
    message_style: _manage_terminal.MessageStyle,
    text_markup: str,
    colour_whole_line: bool,
) -> None:
    line_markup = _manage_terminal.render_line(
        symbol=message_style.symbol,
        colour=message_style.colour,
        text_markup=text_markup,
        colour_whole_line=colour_whole_line,
    )
    _manage_terminal.write_line(line_markup)


def log_note(
    text: str,
) -> None:
    """Note something about the work that is neither a task nor an outcome."""
    _write_message(
        message_style=_manage_terminal.NOTE_STYLE,
        text_markup=text,
        colour_whole_line=False,
    )


def log_task(
    text: str,
) -> None:
    """Announce a task that is starting."""
    _write_message(
        message_style=_manage_terminal.TASK_STYLE,
        text_markup=text,
        colour_whole_line=False,
    )


def log_outcome(
    text: str,
    *,
    status: OutcomeStatus,
) -> None:
    """Report how a task or action ended; the status sets the colour and is never assumed."""
    _write_message(
        message_style=status.value,
        text_markup=text,
        colour_whole_line=True,
    )


def log_value(
    *,
    name: str,
    value: str,
) -> None:
    """Report a value that an action produced, by inspecting or by changing the system; the value prints exactly as written."""
    _write_message(
        message_style=_manage_terminal.OutcomeContent.VALUE.value,
        text_markup=escape_markup(f"{name} = {value}"),
        colour_whole_line=True,
    )


def log_result(
    text: str,
) -> None:
    """Print a result for the user or a pipe: plain text on stdout, with no symbol, colour, timestamp, or wrapping."""
    _manage_terminal.write_line(
        text,
        is_result=True,
    )


def exit_with_error(
    text: str,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Report an error that ends the run, then exit the process with `exit_code`."""
    _write_message(
        message_style=OutcomeStatus.ERROR.value,
        text_markup=f"error: {text}",
        colour_whole_line=True,
    )
    sys.exit(exit_code)


## } MODULE
