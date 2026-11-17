## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import dataclasses
import shlex
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

## local
from huginn import _manage_output, _message_styles

##
## === COMMAND RUNNERS
## every runner prints its command with `shlex.join` before running it; `run_fn` prints a description instead.
##

_CMD_NOT_FOUND_EXIT_CODE = 127
_STOP_TIMEOUT_SECONDS = 5


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


def _write_action(
    *,
    action: _message_styles.Action,
    text: str,
    is_skipped: bool = False,
) -> None:
    """
    Write an action with its symbol and label; an action skipped in dry-run takes the label and colour of the
    skipped status.

    A skipped action is always shown, since showing it is the point of a dry run; other actions can be hidden. Each
    skipped action is counted, so the end of the run can say how many actions were skipped.
    """
    if is_skipped:
        skipped_style = _message_styles.OutcomeStatus.SKIPPED.value
        message_style = dataclasses.replace(
            action.value,
            colour=skipped_style.colour,
            label=skipped_style.label,
        )
    else:
        message_style = action.value
    msg_rendered = message_style.render(
        text=text,
    )
    _manage_output.route_msg(
        msg_rendered,
        is_action=not is_skipped,
    )
    if is_skipped:
        _manage_output.record_skipped_action()


def _write_cmd(
    *,
    action: _message_styles.Action,
    cmd_parts: list[str],
    is_skipped: bool = False,
) -> None:
    """Write a command as an action, quoted with `shlex.join` so it can be copied back into a shell."""
    _write_action(
        action=action,
        text=shlex.join(cmd_parts),
        is_skipped=is_skipped,
    )


def run_cmd_and_show_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
    input_text: str | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    `input_text` is sent to the command on its stdin, e.g. text for `xclip` to put on the clipboard; without it, the
    command reads the terminal. The output is never captured, so a command that leaves a child running, as `xclip`
    does to hold the clipboard, cannot hang the run. A failure raises `CalledProcessError`; with `raise_error=False`
    it returns `False` instead.
    """
    if _manage_output.get_active_built_in_params().dry_run:
        _write_cmd(
            action=_message_styles.Action.RUN_CMD,
            cmd_parts=cmd_parts,
            is_skipped=True,
        )
        return True
    _write_cmd(
        action=_message_styles.Action.RUN_CMD,
        cmd_parts=cmd_parts,
    )
    result = subprocess.run(
        cmd_parts,
        input=input_text,
        text=True,
        cwd=working_directory,
    )
    if raise_error and (result.returncode != 0):
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd_parts,
        )
    return result.returncode == 0


def run_cmd_in_background(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
) -> subprocess.Popen[bytes] | None:
    """
    Start a mutating command that runs until `stop_cmd_in_background`, e.g. a recorder, and return its process;
    `None` in dry-run, where it is skipped.

    Its output is discarded, since it would print over whatever the tool shows while the command runs.
    """
    if _manage_output.get_active_built_in_params().dry_run:
        _write_cmd(
            action=_message_styles.Action.RUN_CMD,
            cmd_parts=cmd_parts,
            is_skipped=True,
        )
        return None
    _write_cmd(
        action=_message_styles.Action.RUN_CMD,
        cmd_parts=cmd_parts,
    )
    return subprocess.Popen(
        cmd_parts,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=working_directory,
    )


def stop_cmd_in_background(
    process: subprocess.Popen[bytes],
) -> int:
    """
    Stop a command started by `run_cmd_in_background` with SIGINT, as Ctrl-C would, and return its exit code.

    SIGINT lets the command finish cleanly, e.g. a recorder completes its file. A command still running after
    `_STOP_TIMEOUT_SECONDS` raises `TimeoutExpired`. Nothing is printed: a signal is not a command, so the tool
    reports how the command ended as an outcome.
    """
    process_is_running = process.poll() is None
    if process_is_running:
        process.send_signal(signal.SIGINT)
    return process.wait(timeout=_STOP_TIMEOUT_SECONDS)


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
            action=_message_styles.Action.RUN_CMD,
            cmd_parts=cmd_parts,
            is_skipped=True,
        )
        return ""
    _write_cmd(
        action=_message_styles.Action.RUN_CMD,
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


def run_fn(
    *,
    description: str,
    fn: Callable[[], None],
) -> None:
    """
    Make a change with a Python function instead of a command, e.g. writing content the tool produced; shown as a
    `run-fn` action with `description`, so it never reads as a command, and skipped and counted in dry-run like a
    mutating command.

    An exception raised by `fn` is passed on unchanged.
    """
    if _manage_output.get_active_built_in_params().dry_run:
        _write_action(
            action=_message_styles.Action.RUN_FN,
            text=description,
            is_skipped=True,
        )
        return
    _write_action(
        action=_message_styles.Action.RUN_FN,
        text=description,
    )
    fn()


def query_cmd_and_show_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a read-only command with its output shown live in the terminal, e.g. a log or a diff for the user to read;
    runs even in dry-run, since it changes nothing. `True` iff it succeeded.

    A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
    """
    _write_cmd(
        action=_message_styles.Action.QUERY_CMD,
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
        action=_message_styles.Action.QUERY_CMD,
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
        action=_message_styles.Action.QUERY_CMD,
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
    """Run a read-only command and return its exit code, for yes/no checks; the command is shown, and its output is discarded."""
    _write_cmd(
        action=_message_styles.Action.QUERY_CMD,
        cmd_parts=cmd_parts,
    )
    result = subprocess.run(
        cmd_parts,
        capture_output=True,
        cwd=working_directory,
    )
    return result.returncode


## } MODULE
