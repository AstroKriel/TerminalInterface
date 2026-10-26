# shell_interface

Design notes for `heimdall.shell_interface`: the run params, the output functions, their message types, and the command runners.

---

## Run Params

| Detail | Choice | State |
|---|---|---|
| Base type | `RunParams(dry_run: bool = False)`, frozen | decided |
| Tool-specific flags | a tool subclasses `RunParams` to add its own fields, e.g. `<Tool>RunParams(RunParams)` with `<flag>: bool`; the subclass must also be frozen; every runner accepts the base type, so a subclass passes through unchanged | decided |
| Who builds it | the entry point builds it once from the parsed flags (see [`<terminal-interface>/design-plan/cli_builder.md`](cli_builder.md)) and passes it to every command function as `run_params` | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.

---

## Message Types

Each kind of message has a fixed colour, marker, and legend description: a `MessageParams` held as the value of one `MessageType` member in the private core `_terminal_output`, so a message type cannot exist without a meaning. The names match those of the log manager expected to move in, and avoid the figure `Theme` used for light and dark plots. The help legend is generated from these members, in declaration order, so the legend cannot drift from the output.

| Message type | Marker | Colour | Used for | State |
|---|---|---|---|---|
| `STEP` | open circle | white | a step starting | decided |
| `SUCCESS` | closed circle | green | the outcome of a step; a result | decided |
| `ERROR` | closed circle | red | an error, before exiting | decided |
| `ACTION` | arrow | blue | a mutating command being run | decided |
| `SKIPPED` | arrow | orange | a mutating command skipped in dry-run | decided |
| `QUERY` | arrow | gray | a read-only command being run | decided |
| `CONTEXT` | dot | gray | a resolved value | decided |

> **Note:** a richer message layer, with typed messages, action outcomes, and boxed panels, is expected to move into this package later. These themes are its first layer, not a closed set: new message kinds are added alongside them, and the existing functions keep their output.

---

## Output Functions

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_msg(msg)` | a plain message | narration | decided |
| `log_step(msg)` | a step starting | narration | decided |
| `log_outcome(msg)` | which path a step took | narration | decided |
| `bind_var(var_name=..., var_value=...)` | a name and the value it resolved to | narration | decided |
| `log_result(msg)` | a result for the user or a pipe | stdout | decided |
| `kill(msg)` | an error, then exits with status 1 | narration | decided |
| `escape_markup(text)` | nothing; returns text that prints exactly as written | N/A | decided |

Narration goes to stderr unless the tool sends it to stdout (see the `narration_stream` field in [`<terminal-interface>/design-plan/cli_builder.md`](cli_builder.md)). Message text is rich markup, so a caller can style it; anything a function adds itself (commands, resolved values, timestamps) is escaped. Text from outside the tool, such as a news title or a file name, goes through `escape_markup` first, so square brackets in it print as written.

Names and signatures match the existing layer, so tools moving onto this package keep their output call sites.

---

## Command Runners

Every runner is named `<verb>_cmd_and_<what happens to the output>`, so the name alone says whether the command changes anything and where its output ends up:

- `run` changes the system and is skipped in dry-run; `query` only reads and always runs.
- `show_output` prints the output live in the terminal; `capture_output` returns it, the term `subprocess.run(capture_output=True)` uses; `capture_outcome` returns stdout, stderr, and the exit code together; `discard_output` throws it away.

| Function | Output | On failure | In dry-run | Returns | State |
|---|---|---|---|---|---|
| `run_cmd_and_show_output(*, run_params, cmd, cwd=None, raise_error=True)` | shown live | raises `CalledProcessError`; returns `False` with `raise_error=False` | printed, skipped, counts as success | `True` iff it succeeded | decided |
| `run_cmd_and_capture_output(*, run_params, cmd, cwd=None)` | captured | raises `CalledProcessError` | printed, skipped | stdout, stripped | decided |
| `query_cmd_and_capture_output(*, cmd, cwd=None, raise_error=True)` | captured | raises `CalledProcessError`; returns `""` with `raise_error=False` | runs | stdout, stripped | decided |
| `query_cmd_and_capture_outcome(*, cmd, cwd=None)` | captured | never raises | runs | a `CommandOutcome`, output unstripped | decided |
| `query_cmd_and_discard_output(*, cmd, cwd=None)` | discarded, nothing printed | never raises | runs | exit status | decided |

Every runner takes keyword arguments only, and every runner accepts `cwd`. `raise_error` follows the soft error convention: a caller that wants to continue past a failure passes `raise_error=False`. State: decided.

Every runner prints its command with `shlex.join(cmd)`, which quotes an argument only when it contains spaces or shell characters, so the printed text can be copied and run as is: `["git", "commit", "-m", "a message"]` prints as `git commit -m 'a message'`. `query_cmd_and_discard_output` is the one exception: it answers yes/no checks, where printing the command would be noise. State: decided.

The two `capture_output` runners strip surrounding whitespace, because their output is a value for code to use; `query_cmd_and_capture_outcome` keeps it as is, because a `CommandOutcome` is a record of exactly what ran. State: decided.

`CommandOutcome` holds `command` (the command exactly as printed), `working_directory` (`None` if not set), `exit_code`, `stdout`, and `stderr`, with a `succeeded` property. `query_cmd_and_capture_outcome` prints its command with the `QUERY` theme, like the other query runners, and never raises: a non-zero exit is part of the outcome, and a program that is not installed is reported as exit status 127, the shell code for command not found, with the reason in `stderr`. It serves tools that record each finding together with the command that produced it, so the record can show what ran and let the user rerun it. The name and fields match an existing result type that is expected to move into this package, so that the move is additive. State: decided.

| Question | State |
|---|---|
| Timeouts for every runner, so that a hung command cannot hang the tool; expected to arrive with the result type that has them | open |

---

## Output for One Run

The entry point sets these once per process, from the fields of the `Tool`. Timestamps and the record serve tools that keep a history of what they did to a machine.

| Feature | Detail | State |
|---|---|---|
| Narration stream | stderr by default; a tool can send narration to stdout, e.g. where job logs capture only stdout | decided |
| Timestamps | a `YYYY-MM-DD HH:MM:SS` prefix on every line printed to the terminal, from `datetime.now().isoformat(sep=" ", timespec="seconds")` | decided |
| Persistent record | every line printed, steps and commands included, is also appended to a file, as plain text without colour markup | decided |
| Record format | `[<timestamp>] (<tool_name>): <line>`, one line per entry, always timestamped whether or not the terminal shows timestamps | decided |
| Record in dry-run | nothing is written: the record is a history of what was done to the machine, and a dry-run does nothing | decided |

Timestamps and the record are off unless a tool turns them on, so tools that do not need them see no change. A script that never calls the entry point gets the defaults: narration on stderr, no timestamps, no record.
