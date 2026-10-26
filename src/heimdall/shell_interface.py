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


def log_msg(
    msg: str,
) -> None:
    """Print msg as narration, with no marker."""
    _terminal_output.emit(msg)


def log_step(
    msg: str,
) -> None:
    """Narrate a step that is starting."""
    _terminal_output.emit_themed(
        theme=_terminal_output.Theme.STEP,
        text_markup=msg,
        color_whole_line=False,
    )


def log_outcome(
    msg: str,
) -> None:
    """Narrate which way a step went."""
    _terminal_output.emit_themed(
        theme=_terminal_output.Theme.SUCCESS,
        text_markup=msg,
        color_whole_line=True,
    )


def bind_var(
    *,
    var_name: str,
    var_value: str,
) -> None:
    """Narrate a name and the value it resolved to; the value prints exactly as written."""
    _terminal_output.emit_themed(
        theme=_terminal_output.Theme.CONTEXT,
        text_markup=escape_markup(f"{var_name} = {var_value}"),
        color_whole_line=True,
    )


def log_result(
    msg: str,
) -> None:
    """Print a result for the user or a pipe; always on stdout."""
    _terminal_output.emit_themed(
        theme=_terminal_output.Theme.SUCCESS,
        text_markup=msg,
        color_whole_line=True,
        is_result=True,
    )


def kill(
    msg: str,
) -> NoReturn:
    """Print an error and exit the process with status 1."""
    style = _terminal_output.Theme.ERROR.value
    _terminal_output.emit(f"[{style.color.value}]{style.marker.value}[/] error: {msg}")
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
    theme: _terminal_output.Theme,
    cmd: list[str],
    cmd_prefix: str = "",
) -> None:
    _terminal_output.emit_themed(
        theme=theme,
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
            theme=_terminal_output.Theme.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return True
    _print_cmd(
        theme=_terminal_output.Theme.ACTION,
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
            theme=_terminal_output.Theme.SKIPPED,
            cmd=cmd,
            cmd_prefix="(dryrun) skipped: ",
        )
        return ""
    _print_cmd(
        theme=_terminal_output.Theme.ACTION,
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
        theme=_terminal_output.Theme.QUERY,
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
        theme=_terminal_output.Theme.QUERY,
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
