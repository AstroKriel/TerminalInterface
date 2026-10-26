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
class ThemeStyle:
    """Colour, marker, and legend meaning for one kind of output."""
    color: Color
    marker: Marker
    meaning: str


class Theme(Enum):
    """Every kind of output; declaration order is the order of the help legend."""
    STEP = ThemeStyle(
        color=Color.WHITE,
        marker=Marker.CIRCLE_OPEN,
        meaning="action starting",
    )
    SUCCESS = ThemeStyle(
        color=Color.GREEN,
        marker=Marker.CIRCLE_CLOSED,
        meaning="action outcome, or a result on stdout",
    )
    ERROR = ThemeStyle(
        color=Color.RED,
        marker=Marker.CIRCLE_CLOSED,
        meaning="error",
    )
    ACTION = ThemeStyle(
        color=Color.BLUE,
        marker=Marker.ARROW,
        meaning="command being run",
    )
    SKIPPED = ThemeStyle(
        color=Color.ORANGE,
        marker=Marker.ARROW,
        meaning="skipped command (dry-run)",
    )
    QUERY = ThemeStyle(
        color=Color.GRAY,
        marker=Marker.ARROW,
        meaning="read-only lookup command",
    )
    CONTEXT = ThemeStyle(
        color=Color.GRAY,
        marker=Marker.DOT,
        meaning="resolved value / context",
    )


##
## === ACTIVE RUN
##


class OutputStream(str, Enum):
    STDERR = "stderr"
    STDOUT = "stdout"


@dataclass
class _ActiveRun:
    tool_name: str = ""
    show_timestamps: bool = False
    record_path: Path | None = None
    narration_stream: OutputStream = OutputStream.STDERR


_ACTIVE_RUN = _ActiveRun()
_CONSOLE_STDERR = rich_Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_STDOUT = rich_Console(
    highlight=False,
    stderr=False,
)


def start_run(
    *,
    tool_name: str,
    show_timestamps: bool,
    record_path: Path | None,
    narration_stream: OutputStream,
    dry_run: bool,
) -> None:
    """Set how output behaves for the rest of the process; the record is never written in dry-run."""
    _ACTIVE_RUN.tool_name = tool_name
    _ACTIVE_RUN.show_timestamps = show_timestamps
    _ACTIVE_RUN.narration_stream = narration_stream
    if dry_run:
        _ACTIVE_RUN.record_path = None
    else:
        _ACTIVE_RUN.record_path = record_path


def reset_run() -> None:
    """Return to the defaults: no tool name, no timestamps, no record, narration on stderr."""
    start_run(
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
    record_entry = f"[{timestamp}] ({_ACTIVE_RUN.tool_name}): {plain_line}\n"
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
    """Print one line: results always go to stdout, narration to the stream of the active run."""
    timestamp = get_timestamp()
    console_line = line_markup
    if _ACTIVE_RUN.show_timestamps:
        timestamp_text = escape_markup(f"[{timestamp}]")
        console_line = f"[{Color.GRAY.value}]{timestamp_text}[/] {line_markup}"
    if is_result or _ACTIVE_RUN.narration_stream == OutputStream.STDOUT:
        _CONSOLE_STDOUT.print(console_line)
    else:
        _CONSOLE_STDERR.print(console_line)
    if _ACTIVE_RUN.record_path is None:
        return
    _append_record(
        record_path=_ACTIVE_RUN.record_path,
        timestamp=timestamp,
        line_markup=line_markup,
    )


def emit_themed(
    *,
    theme: Theme,
    text_markup: str,
    color_whole_line: bool,
    is_result: bool = False,
) -> None:
    """Print a marker and text in the theme colour; either the whole line or only the marker is coloured."""
    style = theme.value
    if color_whole_line:
        line_markup = f"[{style.color.value}]{style.marker.value} {text_markup}[/]"
    else:
        line_markup = f"[{style.color.value}]{style.marker.value}[/] {text_markup}"
    emit(
        line_markup,
        is_result=is_result,
    )


## } MODULE
