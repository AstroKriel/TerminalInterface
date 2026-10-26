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
from heimdall._terminal_output import escape_markup as escape_markup

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


def _render_message(
    *,
    message_style: _terminal_output.MessageStyle,
    text_markup: str,
    colour_whole_line: bool,
    is_result: bool = False,
) -> None:
    _terminal_output.render_line(
        symbol=message_style.symbol,
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
    """Print a result for the user or a pipe: plain text on stdout, with no symbol, colour, timestamp, or wrapping."""
    _render_message(
        message_style=_terminal_output.OutcomeContent.RESULT.value,
        text_markup=message,
        colour_whole_line=True,
        is_result=True,
    )


def exit_with_error(
    message: str,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Report an error that ends the run, then exit the process with `exit_code`."""
    _render_message(
        message_style=OutcomeStatus.ERROR.value,
        text_markup=f"error: {message}",
        colour_whole_line=True,
    )
    sys.exit(exit_code)


##
## === COMMAND RUNNERS
## every runner prints its command with `shlex.join` before running it, except `query_command_and_discard_output`.
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


def _print_command(
    *,
    action: _terminal_output.Action,
    command: list[str],
    outcome_status: OutcomeStatus | None = None,
    command_prefix: str = "",
) -> None:
    """Print a command with the symbol of its action, in the colour of its outcome status when it already has one."""
    colour = action.value.colour
    if outcome_status is not None:
        colour = outcome_status.value.colour
    _terminal_output.render_line(
        symbol=action.value.symbol,
        colour=colour,
        text_markup=f"{command_prefix}{escape_markup(shlex.join(command))}",
        colour_whole_line=True,
    )


def run_command_and_show_output(
    *,
    run_params: RunParams,
    command: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
    """
    if run_params.dry_run:
        _print_command(
            action=_terminal_output.Action.CHANGE,
            outcome_status=OutcomeStatus.SKIPPED,
            command=command,
            command_prefix="(dryrun) skipped: ",
        )
        return True
    _print_command(
        action=_terminal_output.Action.CHANGE,
        command=command,
    )
    result = subprocess.run(
        command,
        cwd=working_directory,
    )
    if raise_error and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=command,
        )
    return result.returncode == 0


def run_command_and_capture_output(
    *,
    run_params: RunParams,
    command: list[str],
    working_directory: Path | None = None,
) -> str:
    """
    Run a mutating command and return its stdout with surrounding whitespace stripped; empty string in dry-run.

    In dry-run the empty string is a placeholder for an unknown value; anything that depends on it should report a
    skipped outcome instead of carrying on with it.
    """
    if run_params.dry_run:
        _print_command(
            action=_terminal_output.Action.CHANGE,
            outcome_status=OutcomeStatus.SKIPPED,
            command=command,
            command_prefix="(dryrun) skipped: ",
        )
        return ""
    _print_command(
        action=_terminal_output.Action.CHANGE,
        command=command,
    )
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        cwd=working_directory,
    )
    return result.stdout.strip()


def query_command_and_capture_output(
    *,
    command: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> str:
    """
    Run a read-only command and return its stdout with surrounding whitespace stripped; runs even in dry-run.

    A non-zero exit raises `CalledProcessError`; with `raise_error=False` it returns an empty string instead.
    """
    _print_command(
        action=_terminal_output.Action.INSPECTION,
        command=command,
    )
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=working_directory,
    )
    if raise_error and result.returncode != 0:
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def query_command_and_capture_outcome(
    *,
    command: list[str],
    working_directory: Path | None = None,
) -> CommandOutcome:
    """
    Run a read-only command and return its stdout, stderr, and exit code unstripped as a `CommandOutcome`; never raises.

    A program that is not installed is reported as exit status 127, the shell code for command not found.
    """
    _print_command(
        action=_terminal_output.Action.INSPECTION,
        command=command,
    )
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=working_directory,
        )
    except FileNotFoundError:
        return CommandOutcome(
            command=shlex.join(command),
            working_directory=working_directory,
            exit_code=_COMMAND_NOT_FOUND_EXIT_CODE,
            stdout="",
            stderr=f"command not found: `{command[0]}`.",
        )
    return CommandOutcome(
        command=shlex.join(command),
        working_directory=working_directory,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def query_command_and_discard_output(
    *,
    command: list[str],
    working_directory: Path | None = None,
) -> int:
    """Run a read-only command silently and return its exit code, for yes/no checks; the one runner that prints nothing."""
    result = subprocess.run(
        command,
        capture_output=True,
        cwd=working_directory,
    )
    return result.returncode


## } MODULE
