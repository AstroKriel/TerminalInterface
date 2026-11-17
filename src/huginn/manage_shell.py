## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import dataclasses
import inspect
import shlex
import signal
import subprocess
from collections.abc import Callable, Mapping
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
_ACTION_ITEM_INDENT = " " * 4


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
    Write an action with its symbol and label; an action skipped in dry-run takes the colour of the skipped status,
    and its label puts the skipped label before its own, e.g. `skipped run-cmd`, so it still says what was skipped.

    A skipped action is always shown, since showing it is the point of a dry run; other actions can be hidden. Each
    skipped action is counted, so the end of the run can say how many actions were skipped.
    """
    if is_skipped:
        skipped_style = _message_styles.OutcomeStatus.SKIPPED.value
        message_style = dataclasses.replace(
            action.value,
            colour=skipped_style.colour,
            label=f"{skipped_style.label} {action.value.label}",
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
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its output shown live in the terminal; `True` iff it succeeded or was skipped in dry-run.

    The output is never captured, so a command that leaves a child running, as `xclip` does to hold the clipboard,
    cannot hang the run. A failure raises `CalledProcessError`; with `raise_error=False` it returns `False` instead.
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
        cwd=working_directory,
    )
    if raise_error and (result.returncode != 0):
        raise subprocess.CalledProcessError(
            returncode=result.returncode,
            cmd=cmd_parts,
        )
    return result.returncode == 0


def run_cmd_and_discard_output(
    *,
    cmd_parts: list[str],
    working_directory: Path | None = None,
    raise_error: bool = True,
) -> bool:
    """
    Run a mutating command with its stdout and stderr discarded; `True` iff it succeeded or was skipped in dry-run.

    For a command that prints nothing useful and may leave a child running that keeps its output open, e.g. `xclip`,
    whose child holds the clipboard: with the output discarded, the child cannot hold a pipe the tool writes to, so
    `<tool> | tee <log>` still ends. The command is still printed. A failure raises `CalledProcessError`; with
    `raise_error=False` it returns `False` instead.
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
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
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


def _get_fn_call_text(
    *,
    fn: Callable[..., None],
    fn_kwargs: Mapping[str, object],
) -> str:
    """
    Return where `fn` lives and that it is called, e.g. `voice_note.transcribe_audio.join_transcript_lines(...)`;
    `(...)` when it takes arguments, which are not printed, and `()` when it takes none.

    A lambda or a `functools.partial` has no name of its own to point at, so either is rejected.
    """
    fn_is_named_callable = inspect.isfunction(fn) or inspect.ismethod(fn) or inspect.isbuiltin(fn)
    if (not fn_is_named_callable) or (fn.__name__ == "<lambda>"):
        raise ValueError(
            f"run_fn: `fn` must be a named function or method, so the output can say where it lives; got `{fn!r}`.",
        )
    if len(fn_kwargs) == 0:
        call_marker = "()"
    else:
        call_marker = "(...)"
    return f"{fn.__module__}.{fn.__qualname__}{call_marker}"


def _write_action_items(
    *,
    items: Mapping[str, object],
    is_skipped: bool,
) -> None:
    """Write the items of an action under it; hidden along with the action, unless the action was skipped."""
    for item_name, item_value in items.items():
        msg_rendered = _message_styles.ITEM_STYLE.render(text=f"{item_name} = {item_value}")
        _manage_output.route_msg(
            f"{_ACTION_ITEM_INDENT}{msg_rendered}",
            is_action=not is_skipped,
        )


def run_fn(
    *,
    fn: Callable[..., None],
    purpose: str,
    fn_kwargs: Mapping[str, object] | None = None,
    items: Mapping[str, object] | None = None,
) -> None:
    """
    Make a change with the tool's own Python where no command can do it, e.g. writing content the tool produced;
    skipped and counted in dry-run like a mutating command.

    Shown as a `run-fn` action naming the function and its module, so the user knows which code ran and where to
    find it, then `purpose`, then `items`, e.g. the file it writes. `fn` is called with `fn_kwargs`. An exception
    raised by `fn` is passed on unchanged.
    """
    resolved_fn_kwargs: Mapping[str, object]
    if fn_kwargs is None:
        resolved_fn_kwargs = {}
    else:
        resolved_fn_kwargs = fn_kwargs
    fn_call_text = _get_fn_call_text(
        fn=fn,
        fn_kwargs=resolved_fn_kwargs,
    )
    action_items: dict[str, object] = {"purpose": purpose}
    if items is not None:
        action_items.update(items)
    is_skipped = _manage_output.get_active_built_in_params().dry_run
    _write_action(
        action=_message_styles.Action.RUN_FN,
        text=fn_call_text,
        is_skipped=is_skipped,
    )
    _write_action_items(
        items=action_items,
        is_skipped=is_skipped,
    )
    if is_skipped:
        return
    fn(**resolved_fn_kwargs)


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
