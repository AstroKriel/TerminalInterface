## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import dataclasses
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

## local
from huginn import _manage_output, _message_styles

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
    stdout: str
    stderr: str

    @property
    def has_succeeded(
        self,
    ) -> bool:
        return self.exit_code == 0


def _write_cmd(
    *,
    action: _message_styles.Action,
    cmd_parts: list[str],
    is_skipped: bool = False,
) -> None:
    """
    Write a command with the symbol of its action; a command skipped in dry-run takes the colour of the skipped status.

    A skipped command is always shown, since showing it is the point of a dry run; other actions can be hidden.
    """
    cmd = shlex.join(cmd_parts)
    if is_skipped:
        message_style = dataclasses.replace(
            action.value,
            colour=_message_styles.OutcomeStatus.SKIPPED.value.colour,
        )
        msg_text = f"(dry-run) skipped: {cmd}"
    else:
        message_style = action.value
        msg_text = cmd
    msg_rendered = message_style.render(
        text=msg_text,
    )
    _manage_output.route_msg(
        msg_rendered,
        is_action=not is_skipped,
    )


def run_cmd_and_show_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
    """
    if _manage_output.get_active_built_in_params().dry_run:
        _write_cmd(
            action=_message_styles.Action.CHANGE,
            cmd_parts=cmd_parts,
            is_skipped=True,
        )
        return True
    _write_cmd(
        action=_message_styles.Action.CHANGE,
        cmd_parts=cmd_parts,
    )
    result = subprocess.run(
        cmd_parts,
        cwd=working_directory,
    )
    if raise_error and (result.returncode != 0):
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd_parts,
        )
    return result.returncode == 0


def run_cmd_and_capture_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
) -> str:
    """
    Run a mutating command and return its stdout with surrounding whitespace stripped; empty string in dry-run.

    In dry-run the empty string is a placeholder for an unknown value; anything that depends on it should report a
    skipped outcome instead of carrying on with it.
    """
    if _manage_output.get_active_built_in_params().dry_run:
        _write_cmd(
            action=_message_styles.Action.CHANGE,
            cmd_parts=cmd_parts,
            is_skipped=True,
        )
        return ""
    _write_cmd(
        action=_message_styles.Action.CHANGE,
        cmd_parts=cmd_parts,
    )
    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        text=True,
        check=True,
        cwd=working_directory,
    )
    return result.stdout.strip()


def query_cmd_and_capture_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> str:
    """
    Run a read-only command and return its stdout with surrounding whitespace stripped; runs even in dry-run.

    A non-zero exit raises `CalledProcessError`; with `raise_error=False` it returns an empty string instead.
    """
    _write_cmd(
        action=_message_styles.Action.INSPECTION,
        cmd_parts=cmd_parts,
    )
    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        text=True,
        cwd=working_directory,
    )
    if raise_error and (result.returncode != 0):
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd_parts,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result.stdout.strip()


def query_cmd_and_capture_outcome(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
) -> CommandOutcome:
    """
    Run a read-only command and return its stdout, stderr, and exit code unstripped as a `CommandOutcome`; never raises.

    A program that is not installed is reported as exit status 127, the shell code for command not found.
    """
    _write_cmd(
        action=_message_styles.Action.INSPECTION,
        cmd_parts=cmd_parts,
    )
    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            cwd=working_directory,
        )
    except FileNotFoundError:
        return CommandOutcome(
            cmd=shlex.join(cmd_parts),
            working_directory=working_directory,
            exit_code=_CMD_NOT_FOUND_EXIT_CODE,
            stdout="",
            stderr=f"command not found: `{cmd_parts[0]}`.",
        )
    return CommandOutcome(
        cmd=shlex.join(cmd_parts),
        working_directory=working_directory,
        exit_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def query_cmd_and_discard_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
) -> int:
    """Run a read-only command silently and return its exit code, for yes/no checks; the one runner that prints nothing."""
    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        cwd=working_directory,
    )
    return result.returncode


## } MODULE
