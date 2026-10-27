# manage_shell

Design notes for `heimdall.manage_shell`: the run params and the command runners. The output functions and message types are in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Run Params

| Detail | Choice | State |
|---|---|---|
| Base type | `RunParams(dry_run: bool = False)`, frozen | decided |
| Tool-specific flags | a tool subclasses `RunParams` to add its own fields, e.g. `<Tool>RunParams(RunParams)` with `<flag>: bool`; the subclass must also be frozen; every runner accepts the base type, so a subclass passes through unchanged | decided |
| Who builds it | the entry point builds it once from the parsed flags (see [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md)) and passes it to every command function as `run_params` | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.

---

## Command Runners

Every runner is named `<verb>_command_and_<what happens to the output>`, so the name alone says whether the command changes anything and where its output ends up:

- `run` changes the system and is skipped in dry-run; `query` only reads and always runs.
- `show_output` prints the output live in the terminal; `capture_output` returns it, the term `subprocess.run(capture_output=True)` uses; `capture_outcome` returns stdout, stderr, and the exit code together; `discard_output` throws it away.

| Function | Output | On failure | In dry-run | Returns | State |
|---|---|---|---|---|---|
| `run_command_and_show_output(*, run_params, command, working_directory=None, raise_error=True)` | shown live | raises `CalledProcessError`; returns `False` with `raise_error=False` | printed, skipped, counts as success | `True` iff it succeeded | decided |
| `run_command_and_capture_output(*, run_params, command, working_directory=None)` | captured | raises `CalledProcessError` | printed, skipped | stdout, stripped | decided |
| `query_command_and_capture_output(*, command, working_directory=None, raise_error=True)` | captured | raises `CalledProcessError`; returns `""` with `raise_error=False` | runs | stdout, stripped | decided |
| `query_command_and_capture_outcome(*, command, working_directory=None)` | captured | never raises | runs | a `CommandOutcome`, output unstripped | decided |
| `query_command_and_discard_output(*, command, working_directory=None)` | discarded, nothing printed | never raises | runs | exit status | decided |

Every runner takes keyword arguments only, and every runner accepts `working_directory`. `raise_error` follows the soft error convention: a caller that wants to continue past a failure passes `raise_error=False`. State: decided.

Every runner prints its command with `shlex.join(command)`, which quotes an argument only when it contains spaces or shell characters, so the printed text can be copied and run as is: `["git", "commit", "-m", "a message"]` prints as `git commit -m 'a message'`. `query_command_and_discard_output` is the one exception: it answers yes/no checks, where printing the command would be noise. State: decided.

The two `capture_output` runners strip surrounding whitespace, because their output is a value for code to use; `query_command_and_capture_outcome` keeps it as is, because a `CommandOutcome` is a record of exactly what ran. State: decided.

`CommandOutcome` holds `command` (the command exactly as printed), `working_directory` (`None` if not set), `exit_code`, `stdout`, and `stderr`, with a `succeeded` property. `query_command_and_capture_outcome` prints its command as an inspection, like the other query runners, and never raises: a non-zero exit is part of the outcome, and a program that is not installed is reported as exit status 127, the shell code for command not found, with the reason in `stderr`. It serves tools that record each finding together with the command that produced it, so the record can show what ran and let the user rerun it. The name and fields match an existing result type that is expected to move into this package, so that the move is additive. State: decided.

| Question | State |
|---|---|
| Timeouts for every runner, so that a hung command cannot hang the tool; expected to arrive with the result type that has them | open |
