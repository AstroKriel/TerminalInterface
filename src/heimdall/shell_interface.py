## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import datetime
import shlex
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NoReturn, final

## third-party
import rich.markup
import rich.text
from rich.console import Console

##
## === CONFIG
##


@dataclass
class Config:
    dry_run: bool = False


@dataclass
class _OutputSettings:
    tool_name: str = ""
    show_timestamps: bool = False
    record_path: Path | None = None


_OUTPUT_SETTINGS = _OutputSettings()


def configure_output(
    *,
    tool_name: str,
    show_timestamps: bool = False,
    record_path: Path | None = None,
    dry_run: bool = False,
) -> None:
    """Set once per process, before any output; the record is never written in dry-run."""
    _OUTPUT_SETTINGS.tool_name = tool_name
    _OUTPUT_SETTINGS.show_timestamps = show_timestamps
    if dry_run:
        _OUTPUT_SETTINGS.record_path = None
    else:
        _OUTPUT_SETTINGS.record_path = record_path


##
## === THEMES
##

_CONSOLE = Console(
    highlight=False,
    stderr=True,
)
_CONSOLE_OUT = Console(
    highlight=False,
    stderr=False,
)


class _Colors(str, Enum):
    WHITE = "#FFFFFF"
    GREEN = "#32CD32"
    BLUE = "#2A71F6"
    ORANGE = "#E48500"
    RED = "#FF4500"
    GRAY = "#818181"


class _Markers(str, Enum):
    CIRCLE_OPEN = "○"
    CIRCLE_CLOSED = "●"
    ARROW = "→"
    DOT = "·"


@dataclass(frozen=True)
class _Theme:
    color: _Colors
    marker: _Markers


@final
class _Themes:
    STEP = _Theme(
        color=_Colors.WHITE,
        marker=_Markers.CIRCLE_OPEN,
    )
    SUCCESS = _Theme(
        color=_Colors.GREEN,
        marker=_Markers.CIRCLE_CLOSED,
    )
    ACTION = _Theme(
        color=_Colors.BLUE,
        marker=_Markers.ARROW,
    )
    SKIPPED = _Theme(
        color=_Colors.ORANGE,
        marker=_Markers.ARROW,
    )
    ERROR = _Theme(
        color=_Colors.RED,
        marker=_Markers.CIRCLE_CLOSED,
    )
    QUERY = _Theme(
        color=_Colors.GRAY,
        marker=_Markers.ARROW,
    )
    CONTEXT = _Theme(
        color=_Colors.GRAY,
        marker=_Markers.DOT,
    )


_LEGEND_MEANINGS: list[tuple[_Theme, str]] = [
    (_Themes.STEP, "action starting"),
    (_Themes.SUCCESS, "action outcome"),
    (_Themes.ERROR, "error"),
    (_Themes.ACTION, "command being run"),
    (_Themes.SKIPPED, "skipped command (dry-run)"),
    (_Themes.QUERY, "read-only lookup command"),
    (_Themes.CONTEXT, "resolved value / context"),
]


@dataclass(frozen=True)
class LegendEntry:
    marker: str
    color_name: str
    color_hex: str
    meaning: str


def get_legend() -> list[LegendEntry]:
    """One entry per kind of output, built from the themes themselves."""
    legend_entries: list[LegendEntry] = []
    for theme, meaning in _LEGEND_MEANINGS:
        legend_entry = LegendEntry(
            marker=theme.marker.value,
            color_name=theme.color.name.lower(),
            color_hex=theme.color.value,
            meaning=meaning,
        )
        legend_entries.append(legend_entry)
    return legend_entries


##
## === OUTPUT
##


def get_timestamp() -> str:
    return datetime.datetime.now().isoformat(
        sep=" ",
        timespec="seconds",
    )


def _emit(
    *,
    line_markup: str,
    to_stdout: bool = False,
) -> None:
    timestamp = get_timestamp()
    console_line = line_markup
    if _OUTPUT_SETTINGS.show_timestamps:
        timestamp_text = rich.markup.escape(f"[{timestamp}]")
        console_line = f"[{_Colors.GRAY.value}]{timestamp_text}[/] {line_markup}"
    if to_stdout:
        _CONSOLE_OUT.print(console_line)
    else:
        _CONSOLE.print(console_line)
    record_path = _OUTPUT_SETTINGS.record_path
    if record_path is None:
        return
    plain_line = rich.text.Text.from_markup(line_markup).plain
    record_entry = f"[{timestamp}] ({_OUTPUT_SETTINGS.tool_name}): {plain_line}\n"
    record_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with open(record_path, "a") as record_stream:
        record_stream.write(record_entry)


def _print_cmd(
    *,
    theme: _Theme,
    cmd: list[str],
    cmd_prefix: str,
) -> None:
    cmd_text = rich.markup.escape(shlex.join(cmd))
    _emit(line_markup=f"[{theme.color.value}]{theme.marker.value}{cmd_prefix}{cmd_text}[/]")


def log_msg(
    msg: str,
) -> None:
    """Print msg to stderr; all diagnostic output goes here to keep stdout clean."""
    _emit(line_markup=msg)


def log_step(
    msg: str,
) -> None:
    """Narrate a major decision point within a command."""
    theme = _Themes.STEP
    _emit(line_markup=f"[{theme.color.value}]{theme.marker.value}[/] {msg}")


def log_outcome(
    msg: str,
) -> None:
    """Record which path was taken after a branch or decision."""
    theme = _Themes.SUCCESS
    _emit(line_markup=f"[{theme.color.value}]{theme.marker.value} {msg}[/]")


def bind_var(
    *,
    var_name: str,
    var_value: str,
) -> None:
    """Log a variable name alongside the value it was resolved to."""
    theme = _Themes.CONTEXT
    binding_text = rich.markup.escape(f"{var_name} = {var_value}")
    _emit(line_markup=f"[{theme.color.value}]{theme.marker.value} {binding_text}[/]")


def log_result(
    msg: str,
) -> None:
    """Print a user-facing result to stdout."""
    theme = _Themes.SUCCESS
    _emit(
        line_markup=f"[{theme.color.value}]{theme.marker.value} {msg}[/]",
        to_stdout=True,
    )


def kill(
    msg: str,
) -> NoReturn:
    """Print an error message to stderr and exit the process immediately."""
    theme = _Themes.ERROR
    _emit(line_markup=f"[{theme.color.value}]{theme.marker.value}[/] error: {msg}")
    sys.exit(1)


##
## === EXECUTION
##


@dataclass(frozen=True)
class CommandOutcome:
    command: str
    working_directory: Path | None
    exit_code: int
    stdout: str | None
    stderr: str | None

    @property
    def succeeded(
        self,
    ) -> bool:
        return self.exit_code == 0


def run_cmd(
    config: Config,
    cmd: list[str],
    cwd: Path | None = None,
) -> None:
    """Run a mutating command; raises on failure; skipped entirely in dry-run mode."""
    if config.dry_run:
        _print_cmd(
            theme=_Themes.SKIPPED,
            cmd=cmd,
            cmd_prefix=" (dryrun) skipped: ",
        )
        return
    _print_cmd(
        theme=_Themes.ACTION,
        cmd=cmd,
        cmd_prefix=" ",
    )
    subprocess.run(
        cmd,
        check=True,
        cwd=cwd,
    )


def try_run_cmd(
    config: Config,
    cmd: list[str],
    cwd: Path | None = None,
) -> bool:
    """Run a mutating command; returns True on success, False on failure. Skipped in dry-run."""
    if config.dry_run:
        _print_cmd(
            theme=_Themes.SKIPPED,
            cmd=cmd,
            cmd_prefix=" (dryrun) skipped: ",
        )
        return True
    _print_cmd(
        theme=_Themes.ACTION,
        cmd=cmd,
        cmd_prefix=" ",
    )
    result = subprocess.run(
        cmd,
        cwd=cwd,
    )
    return result.returncode == 0


def run_cmd_and_capture_output(
    config: Config,
    cmd: list[str],
    cwd: Path | None = None,
) -> str:
    """Run a mutating command and return its stdout; empty string in dry-run."""
    if config.dry_run:
        _print_cmd(
            theme=_Themes.SKIPPED,
            cmd=cmd,
            cmd_prefix=" (dryrun) skipped: ",
        )
        return ""
    _print_cmd(
        theme=_Themes.ACTION,
        cmd=cmd,
        cmd_prefix=" ",
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def query_cmd(
    cmd: list[str],
    error_on_failure: bool = True,
    cwd: Path | None = None,
) -> str:
    """Run a read-only command, log it, and return its stdout; always executes, even in dry-run.

    When error_on_failure=False, a non-zero exit returns an empty string instead of raising.
    """
    _print_cmd(
        theme=_Themes.QUERY,
        cmd=cmd,
        cmd_prefix=" ",
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if error_on_failure and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def query_cmd_result(
    cmd: list[str],
    cwd: Path | None = None,
) -> CommandOutcome:
    """Run a read-only command, log it, and return everything about the run; never raises on a non-zero exit."""
    _print_cmd(
        theme=_Themes.QUERY,
        cmd=cmd,
        cmd_prefix=" ",
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return CommandOutcome(
        command=shlex.join(cmd),
        working_directory=cwd,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def probe_cmd(
    cmd: list[str],
) -> int:
    """Run a command silently and return its exit code; used for boolean existence checks."""
    result = subprocess.run(
        cmd,
        capture_output=True,
    )
    return result.returncode


## } MODULE
