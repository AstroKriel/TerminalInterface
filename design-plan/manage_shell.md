# manage_shell

Design notes for `huginn.manage_shell`: the command runners. The mutating runners take `tool_params` from [`<terminal-interface>/design-plan/params.md`](params.md). The output functions and message types are in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Command Runners

Every runner is named `<verb>_cmd_and_<what happens to the output>` (`cmd` is the allowed shorthand for command in names), so the name alone says whether the command changes anything and where its output ends up:

- `run` changes the system and is skipped in dry-run; `query` only reads and always runs.
- `show_output` prints the output live in the terminal; `capture_output` returns it, the term `subprocess.run(capture_output=True)` uses; `capture_outcome` returns stdout, stderr, and the exit code together; `discard_output` throws it away.

| Function | Output | On failure | In dry-run | Returns | State |
|---|---|---|---|---|---|
| `run_cmd_and_show_output(*, tool_params, cmd_parts, working_directory=None, raise_error=True)` | shown live | raises `CalledProcessError`; returns `False` with `raise_error=False` | printed, skipped, counts as success | `True` iff it succeeded | decided |
| `run_cmd_and_capture_output(*, tool_params, cmd_parts, working_directory=None)` | captured | raises `CalledProcessError` | printed, skipped | stdout, stripped | decided |
| `query_cmd_and_capture_output(*, cmd_parts, working_directory=None, raise_error=True)` | captured | raises `CalledProcessError`; returns `""` with `raise_error=False` | runs | stdout, stripped | decided |
| `query_cmd_and_capture_outcome(*, cmd_parts, working_directory=None)` | captured | never raises | runs | a `CommandOutcome`, output unstripped | decided |
| `query_cmd_and_discard_output(*, cmd_parts, working_directory=None)` | discarded, nothing printed | never raises | runs | exit status | decided |

Every runner takes keyword arguments only, and every runner accepts `working_directory`. `raise_error` follows the soft error convention: a caller that wants to continue past a failure passes `raise_error=False`. State: decided.

Every runner prints its command with `shlex.join(cmd)`, which quotes an argument only when it contains spaces or shell characters, so the printed text can be copied and run as is: `["git", "commit", "-m", "a message"]` prints as `git commit -m 'a message'`. `query_cmd_and_discard_output` is the one exception: it answers yes/no checks, where printing the command would be noise. State: decided.

The two `capture_output` runners strip surrounding whitespace, because their output is a value for code to use; `query_cmd_and_capture_outcome` keeps it as is, because a `CommandOutcome` is a record of exactly what ran. State: decided.

`CommandOutcome` holds `cmd` (the command exactly as printed), `working_directory` (`None` if not set), `exit_code`, `stdout`, and `stderr`, with a `has_succeeded` property. `stdout` and `stderr` are always text, empty when the command printed nothing, so callers never check for `None`. `query_cmd_and_capture_outcome` prints its command as an inspection, like the other query runners, and never raises: a non-zero exit is part of the outcome, and a program that is not installed is reported as exit status 127, the shell code for command not found, with the reason in `stderr`. It serves tools that record each finding together with the command that produced it, so the record can show what ran and let the user rerun it. The name and fields match an existing result type that is expected to move into this package, so that the move is additive. State: decided.

| Question | State |
|---|---|
| Timeouts for every runner, so that a hung command cannot hang the tool; expected to arrive with the result type that has them | open |
