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
class MessageParams:
    """Colour, marker, and legend description for one message type or outcome status."""
    color: Color
    marker: Marker
    description: str


class MessageType(Enum):
    """Every kind of message other than an outcome; declaration order is the order of the help legend."""
    TASK = MessageParams(
        color=Color.WHITE,
        marker=Marker.CIRCLE_OPEN,
        description="start of a task",
    )
    ACTION = MessageParams(
        color=Color.BLUE,
        marker=Marker.ARROW,
        description="action that changes the system",
    )
    SKIPPED = MessageParams(
        color=Color.ORANGE,
        marker=Marker.ARROW,
        description="action skipped in dry-run",
    )
    QUERY = MessageParams(
        color=Color.GRAY,
        marker=Marker.ARROW,
        description="action that only inspects the system",
    )
    VALUE = MessageParams(
        color=Color.GRAY,
        marker=Marker.DOT,
        description="value that an inspection found",
    )


class OutcomeStatus(Enum):
    """How a task or action ended; declaration order is the order of the help legend."""
    SUCCESS = MessageParams(
        color=Color.GREEN,
        marker=Marker.CIRCLE_CLOSED,
        description="success or result of a task",
    )
    WARNING = MessageParams(
        color=Color.YELLOW,
        marker=Marker.CIRCLE_CLOSED,
        description="warning about a task or action",
    )
    SKIPPED = MessageParams(
        color=Color.ORANGE,
        marker=Marker.CIRCLE_CLOSED,
        description="task or action that was skipped",
    )
    FAILURE = MessageParams(
        color=Color.RED,
        marker=Marker.CIRCLE_CLOSED,
        description="failure of a task or action",
    )


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
    """Print one line: results always go to stdout, narration to the stream set in the output params."""
    timestamp = get_timestamp()
    console_line = line_markup
    if _OUTPUT_PARAMS.show_timestamps:
        timestamp_text = escape_markup(f"[{timestamp}]")
        console_line = f"[{Color.GRAY.value}]{timestamp_text}[/] {line_markup}"
    if is_result or _OUTPUT_PARAMS.narration_stream == OutputStream.STDOUT:
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
    message_params: MessageParams,
    text_markup: str,
    color_whole_line: bool,
    is_result: bool = False,
) -> None:
    """Print a marker and text in the colour of a message type or outcome status; either the whole line or only the marker is coloured."""
    if color_whole_line:
        line_markup = f"[{message_params.color.value}]{message_params.marker.value} {text_markup}[/]"
    else:
        line_markup = f"[{message_params.color.value}]{message_params.marker.value}[/] {text_markup}"
    emit(
        line_markup,
        is_result=is_result,
    )


## } MODULE
