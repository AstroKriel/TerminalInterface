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
from huginn import _message_styles, params

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
    """Return to the defaults: no time stamps, actions shown, no log file."""
    set_params(
        tool_params=params.ToolParams(),
        output_params=params.OutputParams(),
    )


def get_active_tool_params() -> params.ToolParams:
    """The tool params for the rest of the process; the defaults until `set_params` is called."""
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
    time_stamp: str,
    msg_rendered: str,
    is_result: bool,
) -> None:
    """
    Print to stdout for a result, as is, or to stderr for narration, with the time stamp in front when time stamps are on.

    A result is data for the user or a pipe, so it never gets a time stamp and is never wrapped at the terminal width.
    """
    if is_result:
        _CONSOLE_STDOUT.print(
            msg_rendered,
            soft_wrap=True,
        )
    elif _active_output_params.show_time_stamps:
        time_stamp_markup = escape_markup(f"[{time_stamp}]")
        msg_for_console = f"[{_message_styles.Colour.GREY}]{time_stamp_markup}[/] {msg_rendered}"
        _CONSOLE_STDERR.print(msg_for_console)
    else:
        _CONSOLE_STDERR.print(msg_rendered)


def _append_to_log_file(
    *,
    log_file_path: Path,
    time_stamp: str,
    msg_rendered: str,
) -> None:
    msg_for_log_file = f"[{time_stamp}] {rich_Text.from_markup(msg_rendered).plain}\n"
    log_file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with open(log_file_path, "a") as log_stream:
        log_stream.write(msg_for_log_file)


def route_msg(
    msg_rendered: str,
    *,
    is_result: bool = False,
    is_action: bool = False,
) -> None:
    """
    Send one rendered message to each destination it belongs in: the console, and the log file when one is set.

    A hidden action is left off the console but still logged; the log file is never written in dry-run.
    """
    time_stamp = _get_time_stamp()
    action_is_hidden = is_action and _active_tool_params.hide_actions
    if not action_is_hidden:
        _print_to_console(
            time_stamp=time_stamp,
            msg_rendered=msg_rendered,
            is_result=is_result,
        )
    if _active_tool_params.dry_run or (_active_output_params.log_file_path is None):
        return
    _append_to_log_file(
        log_file_path=_active_output_params.log_file_path,
        time_stamp=time_stamp,
        msg_rendered=msg_rendered,
    )


## } MODULE
