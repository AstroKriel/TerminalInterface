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


class Color(str, Enum):
    WHITE = "#FFFFFF"
    GREEN = "#32CD32"
    YELLOW = "#FFE600"
    BLUE = "#2A71F6"
    ORANGE = "#E48500"
    RED = "#FF4500"
    GRAY = "#818181"


class Marker(str, Enum):
    CIRCLE_OPEN = "○"
    CIRCLE_CLOSED = "●"
    ARROW = "→"
    DOT = "·"


@dataclass(frozen=True)
class MessageStyle:
    """Colour, marker, and legend description for one kind of line; a line with neither prints as plain text."""
    color: Color | None
    marker: Marker | None
    description: str


##
## === TASKS
## a task is a stage of the work, announced in words before it starts.
##

TASK_STYLE = MessageStyle(
    color=Color.WHITE,
    marker=Marker.CIRCLE_OPEN,
    description="start of a task",
)

##
## === ACTIONS
## an action is something done to the system, shown before it happens.
##


class ActionKind(Enum):
    """A change is skipped in dry-run; an inspection always runs."""
    CHANGE = MessageStyle(
        color=Color.BLUE,
        marker=Marker.ARROW,
        description="change to the system",
    )
    INSPECTION = MessageStyle(
        color=Color.GRAY,
        marker=Marker.ARROW,
        description="inspection of the system",
    )


##
## === OUTCOMES
## an outcome is how a task or action ended, reported afterwards: a status, and optionally some content.
##


class OutcomeStatus(Enum):
    SUCCESS = MessageStyle(
        color=Color.GREEN,
        marker=Marker.CIRCLE_CLOSED,
        description="success",
    )
    WARNING = MessageStyle(
        color=Color.YELLOW,
        marker=Marker.CIRCLE_CLOSED,
        description="warning",
    )
    SKIPPED = MessageStyle(
        color=Color.ORANGE,
        marker=Marker.CIRCLE_CLOSED,
        description="skipped",
    )
    FAILURE = MessageStyle(
        color=Color.RED,
        marker=Marker.CIRCLE_CLOSED,
        description="failure",
    )


class OutcomeContent(Enum):
    """What an outcome carries: a value for the narration, or a result for the user or a pipe."""
    VALUE = MessageStyle(
        color=Color.GRAY,
        marker=Marker.DOT,
        description="value that an action produced",
    )
    RESULT = MessageStyle(
        color=None,
        marker=None,
        description="result, printed plain on stdout",
    )


def get_skipped_change_style() -> MessageStyle:
    """A change that dry-run skipped: the marker of a change in the colour of the skipped status."""
    return MessageStyle(
        color=OutcomeStatus.SKIPPED.value.color,
        marker=ActionKind.CHANGE.value.marker,
        description="change skipped in dry-run",
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
        title="Actions",
        grouped_message_styles=(*[_action_kind.value for _action_kind in ActionKind], get_skipped_change_style()),
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
## === EMIT
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


def emit(
    line_markup: str,
    *,
    is_result: bool = False,
) -> None:
    """Print one line: narration goes to the stream set in the output params; a result goes to stdout as is.

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
            console_line = f"[{Color.GRAY.value}]{timestamp_text}[/] {line_markup}"
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


def emit_message(
    *,
    message_style: MessageStyle,
    text_markup: str,
    color_whole_line: bool,
    is_result: bool = False,
) -> None:
    """Print a line in the marker and colour of its message style; either the whole line or only the marker is coloured.

    A style without a marker or colour prints the text plain.
    """
    marker_text = ""
    if message_style.marker is not None:
        marker_text = f"{message_style.marker.value} "
    if message_style.color is None:
        line_markup = f"{marker_text}{text_markup}"
    elif color_whole_line:
        line_markup = f"[{message_style.color.value}]{marker_text}{text_markup}[/]"
    else:
        line_markup = f"[{message_style.color.value}]{marker_text.strip()}[/] {text_markup}"
    emit(
        line_markup,
        is_result=is_result,
    )


## } MODULE
