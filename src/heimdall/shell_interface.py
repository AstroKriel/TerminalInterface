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


def log_message(
    message: str,
) -> None:
    """Print message as narration, with no marker."""
    _terminal_output.emit(message)


def log_task(
    message: str,
) -> None:
    """Announce a task that is starting."""
    _terminal_output.emit_message(
        message_params=_terminal_output.MessageType.TASK.value,
        text_markup=message,
        color_whole_line=False,
    )


def log_outcome(
    message: str,
    *,
    status: OutcomeStatus,
) -> None:
    """Report how a task or action ended; the status sets the colour and is never assumed."""
    _terminal_output.emit_message(
        message_params=status.value,
        text_markup=message,
        color_whole_line=True,
    )


def log_value(
    *,
    name: str,
    value: str,
) -> None:
    """Report a value that an inspection found; the value prints exactly as written."""
    _terminal_output.emit_message(
        message_params=_terminal_output.MessageType.VALUE.value,
        text_markup=escape_markup(f"{name} = {value}"),
        color_whole_line=True,
    )


def log_result(
    message: str,
) -> None:
    """Print a result for the user or a pipe; always on stdout."""
    _terminal_output.emit_message(
        message_params=OutcomeStatus.SUCCESS.value,
        text_markup=message,
        color_whole_line=True,
        is_result=True,
    )


def exit_with_error(
    message: str,
) -> NoReturn:
    """Report a failure that ends the run, then exit the process with status 1."""
    _terminal_output.emit_message(
        message_params=OutcomeStatus.FAILURE.value,
        text_markup=f"error: {message}",
        color_whole_line=False,
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
    message_type: _terminal_output.MessageType,
    cmd: list[str],
    cmd_prefix: str = "",
) -> None:
    _terminal_output.emit_message(
        message_params=message_type.value,
        text_markup=f"{cmd_prefix}{escape_markup(shlex.join(cmd))}",
        color_whole_line=True,
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
            message_type=_terminal_output.MessageType.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return True
    _print_cmd(
        message_type=_terminal_output.MessageType.ACTION,
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
    """
    if run_params.dry_run:
        _print_cmd(
            message_type=_terminal_output.MessageType.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return ""
    _print_cmd(
        message_type=_terminal_output.MessageType.ACTION,
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
        message_type=_terminal_output.MessageType.QUERY,
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
        message_type=_terminal_output.MessageType.QUERY,
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
