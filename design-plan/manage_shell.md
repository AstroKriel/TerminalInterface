# manage_shell

Design notes for `huginn.manage_shell`: the command runners. The mutating runners read `dry_run` from the active built-in params (see [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md#built-in-params)). The output functions and message types are in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Command Runners

Every runner is named `<verb>_cmd_and_<what happens to the output>` (`cmd` is the allowed shorthand for command in names), so the name alone says whether the command changes anything and where its output ends up:

- `run` changes the system and is skipped in dry-run; `query` only reads and always runs.
- `show_output` prints the output live in the terminal; `capture_output` returns it, the term `subprocess.run(capture_output=True)` uses; `capture_outcome` returns stdout, stderr, and the exit code together; `discard_output` throws it away.

| Function | Output | On failure | In dry-run | Returns | State |
|---|---|---|---|---|---|
| `run_cmd_and_show_output(*, cmd_parts, working_directory=None, raise_error=True)` | shown live, never captured | raises `CalledProcessError`; returns `False` with `raise_error=False` | printed, skipped, counts as success | `True` iff it succeeded | decided |
| `run_cmd_in_background(*, cmd_parts, working_directory=None)` | discarded, so it cannot print over the tool while it runs | a missing program raises `FileNotFoundError` | printed, skipped | the process, or `None` in dry-run | decided |
| `run_cmd_and_capture_output(*, cmd_parts, working_directory=None)` | captured | raises `CalledProcessError` | printed, skipped | stdout, stripped | decided |
| `query_cmd_and_show_output(*, cmd_parts, working_directory=None, raise_error=True)` | shown live, e.g. a log or a diff for the user to read | raises `CalledProcessError`; returns `False` with `raise_error=False` | runs | `True` iff it succeeded | decided |
| `query_cmd_and_capture_output(*, cmd_parts, working_directory=None, raise_error=True)` | captured | raises `CalledProcessError`; returns `""` with `raise_error=False` | runs | stdout, stripped | decided |
| `query_cmd_and_capture_outcome(*, cmd_parts, working_directory=None)` | captured | never raises | runs | a `CommandOutcome`, output unstripped | decided |
| `query_cmd_and_discard_output(*, cmd_parts, working_directory=None)` | discarded; the command is still shown, like every other runner, so a yes/no check is never hidden | never raises | runs | exit status | decided |

A command that runs until it is stopped, e.g. a recorder, is started with `run_cmd_in_background` and ended with `stop_cmd_in_background(process)`, which sends SIGINT, as Ctrl-C would, so the command can finish cleanly, then waits up to five seconds and returns the exit code. The stop prints nothing: a signal is not a command, so the tool reports how the command ended as an outcome. State: decided.

No runner sends text to a command on stdin. Data a command reads from the tool would flow into it without showing in the printed line, so the step could not be repeated from the output. A tool writes such data to a file instead, and the command names that file, e.g. `xclip -selection clipboard <file>`, so every hand-off between steps is a named file in a printed line. `run_cmd_and_show_output` never captures output, which matters for such commands: `xclip` leaves a child running to hold the clipboard, and a runner that captured output would wait on it forever. State: decided.

`run_fn(*, fn, purpose, fn_kwargs=None, items=None)` makes a change with the tool's own Python, e.g. saving content the tool produced, where no command can do the work honestly. It calls `fn(**fn_kwargs)` and prints where the code lives, then why it ran, then what it touched:

```text
→ run-fn: voice_note.transcribe_audio.join_transcript_lines(...)
    · purpose = join the transcript into one line
    · output = /tmp/voice_note-.../2026-11-17-16-50-31.transcript.txt
```

The action line names the module and function, read from `fn` itself so it cannot drift from the code: a command names the program that ran, so a function names itself, and the user knows where to look. `(...)` marks a call with arguments, which are not printed, since they can be large, e.g. forty papers to save; `()` marks a call with none. `purpose` is required; `items` are optional and name inputs and outputs, ideally as paths, so the result can be checked. `fn` must be a named function or method: a lambda or a `functools.partial` has no name to point at and is rejected. The items are hidden along with the action under `--hide-actions`. In dry-run the line reads `→ skipped run-fn: ...`, and the step is counted like a skipped run. State: decided.

Every runner takes keyword arguments only, and every runner accepts `working_directory`. `raise_error` follows the soft error convention: a caller that wants to continue past a failure passes `raise_error=False`. State: decided.

Every runner prints its command with `shlex.join(cmd)`, which quotes an argument only when it contains spaces or shell characters, so the printed text can be copied and run as is: `["git", "commit", "-m", "a message"]` prints as `git commit -m 'a message'`. There is no exception: `query_cmd_and_discard_output` shows its yes/no checks too, so the terminal and the log show everything that ran. A tool that makes many checks groups them under a task, e.g. `checking the repo`, so they read as one step. State: decided.

The two `capture_output` runners strip surrounding whitespace, because their output is a value for code to use; `query_cmd_and_capture_outcome` keeps it as is, because a `CommandOutcome` is a record of exactly what ran. State: decided.

`CommandOutcome` holds `cmd` (the command exactly as printed), `working_directory` (`None` if not set), `exit_code`, `stdout`, and `stderr`, with a `has_succeeded` property. `stdout` and `stderr` are always text, empty when the command printed nothing, so callers never check for `None`. `query_cmd_and_capture_outcome` prints its command as an inspection, like the other query runners, and never raises: a non-zero exit is part of the outcome, and a program that is not installed is reported as exit status 127, the shell code for command not found, with the reason in `stderr`. It serves tools that record each finding together with the command that produced it, so the record can show what ran and let the user rerun it. The name and fields match an existing result type that is expected to move into this package, so that the move is additive. State: decided.

| Question | State |
|---|---|
| Timeouts for every runner, so that a hung command cannot hang the tool; expected to arrive with the result type that has them | open |
