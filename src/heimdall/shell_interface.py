## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

## local
from heimdall import _terminal_output
from heimdall._terminal_output import OutcomeStatus as OutcomeStatus

##
## === PARAMS
##


@dataclass(frozen=True)
class RunParams:
    """Options for one run of a tool; tools subclass it to add their own flags."""
    dry_run: bool = False


##
## === OUTPUT
## message text is rich markup; anything added here (commands, resolved values) is escaped.
##


def escape_markup(
    text: str,
) -> str:
    """Make text print exactly as written, e.g. a title or path that contains square brackets."""
    return _terminal_output.escape_markup(text)


def _render_message(
    *,
    message_style: _terminal_output.MessageStyle,
    text_markup: str,
    colour_whole_line: bool,
    is_result: bool = False,
) -> None:
    _terminal_output.render_line(
        icon=message_style.icon,
        colour=message_style.colour,
        text_markup=text_markup,
        colour_whole_line=colour_whole_line,
        is_result=is_result,
    )


def log_note(
    message: str,
) -> None:
    """Note something about the work that is neither a task nor an outcome."""
    _render_message(
        message_style=_terminal_output.NOTE_STYLE,
        text_markup=message,
        colour_whole_line=False,
    )


def log_task(
    message: str,
) -> None:
    """Announce a task that is starting."""
    _render_message(
        message_style=_terminal_output.TASK_STYLE,
        text_markup=message,
        colour_whole_line=False,
    )


def log_outcome(
    message: str,
    *,
    status: OutcomeStatus,
) -> None:
    """Report how a task or action ended; the status sets the colour and is never assumed."""
    _render_message(
        message_style=status.value,
        text_markup=message,
        colour_whole_line=True,
    )


def log_value(
    *,
    name: str,
    value: str,
) -> None:
    """Report a value that an action produced, by inspecting or by changing the system; the value prints exactly as written."""
    _render_message(
        message_style=_terminal_output.OutcomeContent.VALUE.value,
        text_markup=escape_markup(f"{name} = {value}"),
        colour_whole_line=True,
    )


def log_result(
    message: str,
) -> None:
    """Print a result for the user or a pipe: plain text on stdout, with no icon, colour, timestamp, or wrapping."""
    _render_message(
        message_style=_terminal_output.OutcomeContent.RESULT.value,
        text_markup=message,
        colour_whole_line=True,
        is_result=True,
    )


def exit_with_error(
    message: str,
) -> NoReturn:
    """Report an error that ends the run, then exit the process with status 1."""
    _render_message(
        message_style=OutcomeStatus.ERROR.value,
        text_markup=f"error: {message}",
        colour_whole_line=False,
    )
    sys.exit(1)


##
## === COMMAND RUNNERS
## every runner prints its command with `shlex.join` before running it, except `query_cmd_and_discard_output`.
##

_COMMAND_NOT_FOUND_EXIT_CODE = 127


@dataclass(frozen=True)
class CommandOutcome:
    """Everything about one finished command; `command` is the text exactly as printed."""
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


def _print_cmd(
    *,
    action_type: _terminal_output.ActionType,
    cmd: list[str],
    outcome_status: OutcomeStatus | None = None,
    cmd_prefix: str = "",
) -> None:
    """Print a command with the icon of its action type, in the colour of its outcome status when it already has one."""
    colour = action_type.value.colour
    if outcome_status is not None:
        colour = outcome_status.value.colour
    _terminal_output.render_line(
        icon=action_type.value.icon,
        colour=colour,
        text_markup=f"{cmd_prefix}{escape_markup(shlex.join(cmd))}",
        colour_whole_line=True,
    )


def run_cmd_and_show_output(
    *,
    run_params: RunParams,
    cmd: list[str],
    cwd: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
    """
    if run_params.dry_run:
        _print_cmd(
            action_type=_terminal_output.ActionType.CHANGE,
            outcome_status=OutcomeStatus.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return True
    _print_cmd(
        action_type=_terminal_output.ActionType.CHANGE,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        cwd=cwd,
    )
    if raise_error and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
        )
    return result.returncode == 0


def run_cmd_and_capture_output(
    *,
    run_params: RunParams,
    cmd: list[str],
    cwd: Path | None = None,
) -> str:
    """Run a mutating command and return its stdout with surrounding whitespace stripped; empty string in dry-run.

    Output is stripped because it is a value for code to use; `query_cmd_and_capture_outcome` keeps it unstripped as a record.
    In dry-run the change never happens, so its value is unknown: the empty string is a placeholder, and anything that
    depends on it should report a skipped outcome instead of carrying on with it.
    """
    if run_params.dry_run:
        _print_cmd(
            action_type=_terminal_output.ActionType.CHANGE,
            outcome_status=OutcomeStatus.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return ""
    _print_cmd(
        action_type=_terminal_output.ActionType.CHANGE,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd,
    )
    return result.stdout.strip()


def query_cmd_and_capture_output(
    *,
    cmd: list[str],
    cwd: Path | None = None,
    raise_error: bool = True,
) -> str:
    """Run a read-only command and return its stdout with surrounding whitespace stripped; runs even in dry-run.

    A non-zero exit raises `CalledProcessError`; with `raise_error=False` it returns an empty string instead.
    """
    _print_cmd(
        action_type=_terminal_output.ActionType.INSPECTION,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if raise_error and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def query_cmd_and_capture_outcome(
    *,
    cmd: list[str],
    cwd: Path | None = None,
) -> CommandOutcome:
    """Run a read-only command and return its stdout, stderr, and exit code unstripped as a `CommandOutcome`; never raises.

    A program that is not installed is reported as exit status 127, the shell code for command not found.
    """
    _print_cmd(
        action_type=_terminal_output.ActionType.INSPECTION,
        cmd=cmd,
    )
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    except FileNotFoundError:
        return CommandOutcome(
            command=shlex.join(cmd),
            working_directory=cwd,
            exit_code=_COMMAND_NOT_FOUND_EXIT_CODE,
            stdout="",
            stderr=f"command not found: `{cmd[0]}`.",
        )
    return CommandOutcome(
        command=shlex.join(cmd),
        working_directory=cwd,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def query_cmd_and_discard_output(
    *,
    cmd: list[str],
    cwd: Path | None = None,
) -> int:
    """Run a read-only command silently and return its exit code, for yes/no checks; the one runner that prints nothing."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=cwd,
    )
    return result.returncode


## } MODULE
