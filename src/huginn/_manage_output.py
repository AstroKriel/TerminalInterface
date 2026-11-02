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
from huginn import message_styles, params

##
## === ACTIVE PARAMS
##

_active_tool_params = params.ToolParams()
_active_output_params = params.OutputParams()
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
    output_params: params.OutputParams,
) -> None:
    """Set how output behaves for the rest of the process."""
    global _active_tool_params, _active_output_params
    _active_tool_params = tool_params
    _active_output_params = output_params


def reset_params() -> None:
    """Return to the defaults: no timestamps, actions shown, no log."""
    set_params(
        tool_params=params.ToolParams(),
        output_params=params.OutputParams(),
    )


##
## === WRITING
## a finished line goes to the terminal and, when a log is set, to the log file.
##


def get_timestamp() -> str:
    return datetime.datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )


def escape_markup(
    text: str,
) -> str:
    """Make text print exactly as written, even where it looks like rich markup."""
    return rich_markup.escape(text)


def _append_log(
    *,
    log_path: Path,
    timestamp: str,
    line_markup: str,
) -> None:
    plain_line = rich_Text.from_markup(line_markup).plain
    log_entry = f"[{timestamp}] {plain_line}\n"
    log_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with open(log_path, "a") as log_stream:
        log_stream.write(log_entry)


def write_line(
    line_markup: str,
    *,
    is_result: bool = False,
    is_action: bool = False,
) -> None:
    """
    Write one finished line: narration goes to stderr; a result goes to stdout as is.

    A result is data for the user or a pipe, so it never gets a timestamp and is never wrapped at the terminal width.
    A hidden action is left off the terminal but still logged; the log is never written in dry-run.
    """
    timestamp = get_timestamp()
    action_is_hidden = is_action and _active_tool_params.hide_actions
    if is_result:
        _CONSOLE_STDOUT.print(
            line_markup,
            soft_wrap=True,
        )
    elif not action_is_hidden:
        console_line = line_markup
        if _active_output_params.show_timestamps:
            timestamp_text = escape_markup(f"[{timestamp}]")
            console_line = f"[{message_styles.Colour.GREY}]{timestamp_text}[/] {line_markup}"
        _CONSOLE_STDERR.print(console_line)
    if _active_tool_params.dry_run or (_active_output_params.log_path is None):
        return
    _append_log(
        log_path=_active_output_params.log_path,
        timestamp=timestamp,
        line_markup=line_markup,
    )


## } MODULE
