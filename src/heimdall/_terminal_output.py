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


class Symbol(str, Enum):
    OPEN_CIRCLE = "○"
    CLOSED_CIRCLE = "●"
    RIGHT_ARROW = "→"
    HOOKED_ARROW = "↪"
    MIDDLE_DOT = "·"


@dataclass(frozen=True)
class MessageStyle:
    """Colour, icon, and legend description for one kind of line; a line with neither prints as plain text."""
    colour: Colour | None
    icon: Symbol | None
    description: str


##
## === TASKS
## a task is a stage of the work, announced in words before it starts.
##

TASK_STYLE = MessageStyle(
    colour=Colour.WHITE,
    icon=Symbol.OPEN_CIRCLE,
    description="start of a task",
)

##
## === NOTES
## a note is narration that is neither a task nor an outcome.
##

NOTE_STYLE = MessageStyle(
    colour=Colour.WHITE,
    icon=Symbol.HOOKED_ARROW,
    description="note about the work",
)

##
## === ACTIONS
## an action is something done to the system, shown before it happens.
##


class ActionType(Enum):
    """A change is skipped in dry-run; an inspection always runs."""
    CHANGE = MessageStyle(
        colour=Colour.BLUE,
        icon=Symbol.RIGHT_ARROW,
        description="change to the system",
    )
    INSPECTION = MessageStyle(
        colour=Colour.GREY,
        icon=Symbol.RIGHT_ARROW,
        description="inspection of the system",
    )


##
## === OUTCOMES
## an outcome is how a task or action ended, reported afterwards: a status, and optionally some content.
##


class OutcomeStatus(Enum):
    SUCCESS = MessageStyle(
        colour=Colour.GREEN,
        icon=Symbol.CLOSED_CIRCLE,
        description="success",
    )
    WARNING = MessageStyle(
        colour=Colour.YELLOW,
        icon=Symbol.CLOSED_CIRCLE,
        description="warning",
    )
    SKIPPED = MessageStyle(
        colour=Colour.ORANGE,
        icon=Symbol.CLOSED_CIRCLE,
        description="skipped",
    )
    FAILURE = MessageStyle(
        colour=Colour.RED,
        icon=Symbol.CLOSED_CIRCLE,
        description="failure that does not end the run",
    )
    ERROR = MessageStyle(
        colour=Colour.RED,
        icon=Symbol.CLOSED_CIRCLE,
        description="error that ends the run",
    )


class OutcomeContent(Enum):
    """What an outcome carries: a value for the narration, or a result for the user or a pipe."""
    VALUE = MessageStyle(
        colour=Colour.GREY,
        icon=Symbol.MIDDLE_DOT,
        description="value that an action produced",
    )
    RESULT = MessageStyle(
        colour=None,
        icon=None,
        description="result, printed plain on stdout",
    )


##
## === LEGEND
##


@dataclass(frozen=True)
class LegendGroup:
    """One concept in the help legend, with every kind of line it covers."""
    title: str
    grouped_message_styles: tuple[MessageStyle, ...]


LEGEND_GROUPS: list[LegendGroup] = [
    LegendGroup(
        title="Tasks",
        grouped_message_styles=(TASK_STYLE,),
    ),
    LegendGroup(
        title="Notes",
        grouped_message_styles=(NOTE_STYLE,),
    ),
    LegendGroup(
        title="Actions",
        grouped_message_styles=tuple(_action_type.value for _action_type in ActionType),
    ),
    LegendGroup(
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


class OutputStream(str, Enum):
    STDERR = "stderr"
    STDOUT = "stdout"


@dataclass
class _OutputParams:
    tool_name: str = ""
    show_timestamps: bool = False
    record_path: Path | None = None
    narration_stream: OutputStream = OutputStream.STDERR


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
    tool_name: str,
    show_timestamps: bool,
    record_path: Path | None,
    narration_stream: OutputStream,
    dry_run: bool,
) -> None:
    """Set how output behaves for the rest of the process; the record is never written in dry-run."""
    _OUTPUT_PARAMS.tool_name = tool_name
    _OUTPUT_PARAMS.show_timestamps = show_timestamps
    _OUTPUT_PARAMS.narration_stream = narration_stream
    if dry_run:
        _OUTPUT_PARAMS.record_path = None
    else:
        _OUTPUT_PARAMS.record_path = record_path


def reset_output_params() -> None:
    """Return to the defaults: no tool name, no timestamps, no record, narration on stderr."""
    set_output_params(
        tool_name="",
        show_timestamps=False,
        record_path=None,
        narration_stream=OutputStream.STDERR,
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


def _append_record(
    *,
    record_path: Path,
    timestamp: str,
    line_markup: str,
) -> None:
    plain_line = rich_Text.from_markup(line_markup).plain
    record_entry = f"[{timestamp}] ({_OUTPUT_PARAMS.tool_name}): {plain_line}\n"
    record_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with open(record_path, "a") as record_stream:
        record_stream.write(record_entry)


def write_line(
    line_markup: str,
    *,
    is_result: bool = False,
) -> None:
    """Write one finished line: narration goes to the stream set in the output params; a result goes to stdout as is.

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
        if _OUTPUT_PARAMS.narration_stream == OutputStream.STDOUT:
            _CONSOLE_STDOUT.print(console_line)
        else:
            _CONSOLE_STDERR.print(console_line)
    if _OUTPUT_PARAMS.record_path is None:
        return
    _append_record(
        record_path=_OUTPUT_PARAMS.record_path,
        timestamp=timestamp,
        line_markup=line_markup,
    )


def render_line(
    *,
    icon: Symbol | None,
    colour: Colour | None,
    text_markup: str,
    colour_whole_line: bool,
    is_result: bool = False,
) -> None:
    """Render a line with an icon and a colour; either the whole line or only the icon is coloured.

    The icon and colour are passed separately so a line can take them from different facets, e.g. the icon of a
    change in the colour of the skipped status. Without an icon or colour the text renders plain.
    """
    icon_text = ""
    if icon is not None:
        icon_text = f"{icon.value} "
    if colour is None:
        line_markup = f"{icon_text}{text_markup}"
    elif colour_whole_line:
        line_markup = f"[{colour.value}]{icon_text}{text_markup}[/]"
    else:
        line_markup = f"[{colour.value}]{icon_text.strip()}[/] {text_markup}"
    write_line(
        line_markup,
        is_result=is_result,
    )


## } MODULE
