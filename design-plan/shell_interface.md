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

The model has three concepts: a task (a stage of the work, announced in words before it starts), an action (something done to the system, either changing it or only inspecting it, shown before it happens), and an outcome (how a task or action ended, with a status, optionally carrying a value or a result).

The concepts are layered: each base concept has its own kinds.

```text
task                 a stage of the work, announced in words before it starts
action               something done to the system, shown before it happens
├── change           changes the system; skipped in dry-run
└── inspection       only reads the system; always runs
outcome              how a task or action ended, reported afterwards
├── status           success | warning | skipped | failure
└── content          optional: a value (what an action produced) or a result (for the user, on stdout)
```

The marker says which concept a line is (open circle: task; arrow: action; closed circle or dot: outcome) and the colour says which kind or status. Each base concept has its facets as enums of `MessageStyle` (the name used by the log manager expected to move in) in the private core `_terminal_output`: `TASK_STYLE`; `ActionKind` (`CHANGE`, `INSPECTION`); `OutcomeStatus` (`SUCCESS`, `WARNING`, `SKIPPED`, `FAILURE`); `OutcomeContent` (`VALUE`, `RESULT`). A change skipped in dry-run is not defined separately: `get_skipped_change_style` builds it from the change marker and the skipped colour. `LEGEND_GROUPS` lists everything under the three concepts, and the help legend is generated from it, so the legend cannot drift from the output.

| Concept | Facet | Value | Marker | Colour | State |
|---|---|---|---|---|---|
| task | | | open circle | white | decided |
| action | kind | change | arrow | blue | decided |
| action | kind | inspection | arrow | gray | decided |
| action | kind and status | change skipped in dry-run | arrow | orange, from the skipped status | decided |
| outcome | status | success | closed circle | green | decided |
| outcome | status | warning | closed circle | yellow | decided |
| outcome | status | skipped | closed circle | orange | decided |
| outcome | status | failure, including the error that ends the run | closed circle | red | decided |
| outcome | content | value an action produced | dot | gray | decided |
| outcome | content | result | none | none: plain text on stdout, never timestamped or wrapped, so a pipe gets clean data | decided |

An inspection exists to produce a value; a change exists to alter the system and may produce a value along the way, e.g. the path of a directory it created. In dry-run a change is skipped, so a value it would have produced is unknown: anything that depends on that value reports a skipped outcome instead of carrying on with a placeholder. State: decided.

> **Note:** a richer message layer, with titled blocks and notes, is expected to move into this package later. These message types and statuses are its first layer, not a closed set.

---

## Output Functions

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_message(message)` | a plain message | narration | decided |
| `log_task(message)` | a task starting | narration | decided |
| `log_outcome(message, *, status)` | how a task or action ended; `status` is required, never assumed | narration | decided |
| `log_value(*, name, value)` | a value an action produced, as `name = value` | narration | decided |
| `log_result(message)` | a result for the user or a pipe | stdout | decided |
| `exit_with_error(message)` | a failure that ends the run, then exits with status 1 | narration | decided |
| `escape_markup(text)` | nothing; returns text that prints exactly as written | N/A | decided |

`OutcomeStatus` is available as `shell_interface.OutcomeStatus`.

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
