## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Self

## local
from heimdall import _manage_terminal

##
## === PARAMS
##


@dataclass(frozen=True)
class RunParams:
    """Options for one run of a tool; a tool subclasses it to add its own flags and overrides `from_parsed_arguments`."""
    dry_run: bool = False

    @classmethod
    def from_parsed_arguments(
        cls,
        parsed_arguments: argparse.Namespace,
    ) -> Self:
        return cls(dry_run=parsed_arguments.dry_run)


##
## === COMMAND RUNNERS
## every runner prints its command with `shlex.join` before running it, except `query_cmd_and_discard_output`.
##

_CMD_NOT_FOUND_EXIT_CODE = 127


@dataclass(frozen=True)
class CommandOutcome:
    """Everything about one finished command; `cmd` is the text exactly as printed."""
    cmd: str
    working_directory: Path | None
    exit_code: int
    stdout: str | None
    stderr: str | None

    @property
    def succeeded(
        self,
    ) -> bool:
        return self.exit_code == 0


def _write_cmd(
    *,
    action: _manage_terminal.Action,
    cmd: list[str],
    is_skipped: bool = False,
) -> None:
    """Write a command with the symbol of its action; a command skipped in dry-run takes the colour of the skipped status."""
    colour = action.value.colour
    cmd_markup = _manage_terminal.escape_markup(shlex.join(cmd))
    if is_skipped:
        colour = _manage_terminal.OutcomeStatus.SKIPPED.value.colour
        cmd_markup = f"(dry-run) skipped: {cmd_markup}"
    line_markup = _manage_terminal.render_line(
        symbol=action.value.symbol,
        colour=colour,
        text_markup=cmd_markup,
        colour_whole_line=True,
    )
    _manage_terminal.write_line(line_markup)


def run_cmd_and_show_output(
    *,
    run_params: RunParams,
    cmd: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
    """
    if run_params.dry_run:
        _write_cmd(
            action=_manage_terminal.Action.CHANGE,
            cmd=cmd,
            is_skipped=True,
        )
        return True
    _write_cmd(
        action=_manage_terminal.Action.CHANGE,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        cwd=working_directory,
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
    working_directory: Path | None = None,
) -> str:
    """
    Run a mutating command and return its stdout with surrounding whitespace stripped; empty string in dry-run.

    In dry-run the empty string is a placeholder for an unknown value; anything that depends on it should report a
    skipped outcome instead of carrying on with it.
    """
    if run_params.dry_run:
        _write_cmd(
            action=_manage_terminal.Action.CHANGE,
            cmd=cmd,
            is_skipped=True,
        )
        return ""
    _write_cmd(
        action=_manage_terminal.Action.CHANGE,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        cwd=working_directory,
    )
    return result.stdout.strip()


def query_cmd_and_capture_output(
    *,
    cmd: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> str:
    """
    Run a read-only command and return its stdout with surrounding whitespace stripped; runs even in dry-run.

    A non-zero exit raises `CalledProcessError`; with `raise_error=False` it returns an empty string instead.
    """
    _write_cmd(
        action=_manage_terminal.Action.INSPECTION,
        cmd=cmd,
    )
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=working_directory,
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
    working_directory: Path | None = None,
) -> CommandOutcome:
    """
    Run a read-only command and return its stdout, stderr, and exit code unstripped as a `CommandOutcome`; never raises.

    A program that is not installed is reported as exit status 127, the shell code for command not found.
    """
    _write_cmd(
        action=_manage_terminal.Action.INSPECTION,
        cmd=cmd,
    )
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_directory,
        )
    except FileNotFoundError:
        return CommandOutcome(
            cmd=shlex.join(cmd),
            working_directory=working_directory,
            exit_code=_CMD_NOT_FOUND_EXIT_CODE,
            stdout="",
            stderr=f"command not found: `{cmd[0]}`.",
        )
    return CommandOutcome(
        cmd=shlex.join(cmd),
        working_directory=working_directory,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def query_cmd_and_discard_output(
    *,
    cmd: list[str],
    working_directory: Path | None = None,
) -> int:
    """Run a read-only command silently and return its exit code, for yes/no checks; the one runner that prints nothing."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=working_directory,
    )
    return result.returncode


## } MODULE
