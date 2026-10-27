## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

## third-party
from rich import markup as rich_markup
from rich.console import Console as rich_Console
from rich.text import Text as rich_Text

##
## === PALETTE
##


class Colour(str, Enum):
    WHITE = "#FFFFFF"
    GREEN = "#32CD32"
    YELLOW = "#FFE600"
    BLUE = "#2A71F6"
    ORANGE = "#E48500"
    RED = "#FF4500"
    GREY = "#818181"
    CYAN = "#00CED1"


class Symbol(str, Enum):
    OPEN_CIRCLE = "○"
    CLOSED_CIRCLE = "●"
    RIGHT_ARROW = "→"
    HOOKED_ARROW = "↪"
    MIDDLE_DOT = "·"


@dataclass(frozen=True)
class MessageStyle:
    """Colour, symbol, and legend description for one kind of line; a line with neither prints as plain text."""
    colour: Colour | None
    symbol: Symbol | None
    description: str


##
## === TASKS
## a task is a stage of the work, announced in words before it starts.
##

TASK_STYLE = MessageStyle(
    colour=Colour.WHITE,
    symbol=Symbol.OPEN_CIRCLE,
    description="start of a task",
)

##
## === NOTES
## a note is narration that is neither a task nor an outcome.
##

NOTE_STYLE = MessageStyle(
    colour=Colour.WHITE,
    symbol=Symbol.HOOKED_ARROW,
    description="note about the work",
)

##
## === ACTIONS
## an action is something done to the system, shown before it happens.
##


class Action(Enum):
    """A change is skipped in dry-run; an inspection always runs."""
    CHANGE = MessageStyle(
        colour=Colour.BLUE,
        symbol=Symbol.RIGHT_ARROW,
        description="change to the system",
    )
    INSPECTION = MessageStyle(
        colour=Colour.GREY,
        symbol=Symbol.RIGHT_ARROW,
        description="inspection of the system",
    )


##
## === OUTCOMES
## an outcome is how a task or action ended, reported afterwards: a status, and optionally some content.
##


class OutcomeStatus(Enum):
    SUCCESS = MessageStyle(
        colour=Colour.GREEN,
        symbol=Symbol.CLOSED_CIRCLE,
        description="success",
    )
    WARNING = MessageStyle(
        colour=Colour.YELLOW,
        symbol=Symbol.CLOSED_CIRCLE,
        description="warning",
    )
    SKIPPED = MessageStyle(
        colour=Colour.ORANGE,
        symbol=Symbol.CLOSED_CIRCLE,
        description="skipped",
    )
    FAILURE = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.CLOSED_CIRCLE,
        description="failure that does not end the run",
    )
    ERROR = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.CLOSED_CIRCLE,
        description="error that ends the run",
    )


class OutcomeContent(Enum):
    """What an outcome carries: a value for the narration, or a result for the user or a pipe."""
    VALUE = MessageStyle(
        colour=Colour.GREY,
        symbol=Symbol.MIDDLE_DOT,
        description="value that an action produced",
    )
    RESULT = MessageStyle(
        colour=None,
        symbol=None,
        description="result, printed plain on stdout",
    )


##
## === MESSAGE GROUPS
##


@dataclass(frozen=True)
class MessageGroup:
    """One concept with every kind of line it covers; the help legend is built from these."""
    title: str
    grouped_message_styles: tuple[MessageStyle, ...]


MESSAGE_GROUPS: list[MessageGroup] = [
    MessageGroup(
        title="Tasks",
        grouped_message_styles=(TASK_STYLE, ),
    ),
    MessageGroup(
        title="Notes",
        grouped_message_styles=(NOTE_STYLE, ),
    ),
    MessageGroup(
        title="Actions",
        grouped_message_styles=tuple(_action.value for _action in Action),
    ),
    MessageGroup(
        title="Outcomes",
        grouped_message_styles=(
            *[_outcome_status.value for _outcome_status in OutcomeStatus],
            *[_outcome_content.value for _outcome_content in OutcomeContent],
        ),
    ),
]

##
## === OUTPUT PARAMS
##


@dataclass
class _OutputParams:
    show_timestamps: bool = False
    log_path: Path | None = None


_OUTPUT_PARAMS = _OutputParams()
_CONSOLE_STDERR = rich_Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_STDOUT = rich_Console(
    highlight=False,
    stderr=False,
)


def set_output_params(
    *,
    show_timestamps: bool,
    log_path: Path | None,
    dry_run: bool,
) -> None:
    """Set how output behaves for the rest of the process; the log is never written in dry-run."""
    _OUTPUT_PARAMS.show_timestamps = show_timestamps
    if dry_run:
        _OUTPUT_PARAMS.log_path = None
    else:
        _OUTPUT_PARAMS.log_path = log_path


def reset_output_params() -> None:
    """Return to the defaults: no timestamps, no log."""
    set_output_params(
        show_timestamps=False,
        log_path=None,
        dry_run=False,
    )


##
## === RENDERING
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
) -> None:
    """
    Write one finished line: narration goes to stderr; a result goes to stdout as is.

    A result is data for the user or a pipe, so it never gets a timestamp and is never wrapped at the terminal width.
    """
    timestamp = get_timestamp()
    if is_result:
        _CONSOLE_STDOUT.print(
            line_markup,
            soft_wrap=True,
        )
    else:
        console_line = line_markup
        if _OUTPUT_PARAMS.show_timestamps:
            timestamp_text = escape_markup(f"[{timestamp}]")
            console_line = f"[{Colour.GREY.value}]{timestamp_text}[/] {line_markup}"
        _CONSOLE_STDERR.print(console_line)
    if _OUTPUT_PARAMS.log_path is None:
        return
    _append_log(
        log_path=_OUTPUT_PARAMS.log_path,
        timestamp=timestamp,
        line_markup=line_markup,
    )


def render_line(
    *,
    symbol: Symbol | None,
    colour: Colour | None,
    text_markup: str,
    colour_whole_line: bool,
) -> str:
    """
    Return the markup for a line with a symbol and a colour; either the whole line or only the symbol is coloured.

    The symbol and colour are passed separately so a line can take them from different facets, e.g. the symbol of a
    change in the colour of the skipped status. Without a symbol or colour the text renders plain.
    """
    symbol_text = ""
    if symbol is not None:
        symbol_text = f"{symbol.value} "
    if colour is None:
        return f"{symbol_text}{text_markup}"
    if colour_whole_line:
        return f"[{colour.value}]{symbol_text}{text_markup}[/]"
    return f"[{colour.value}]{symbol_text.strip()}[/] {text_markup}"


## } MODULE
