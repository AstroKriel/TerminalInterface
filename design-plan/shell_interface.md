# shell_interface

Design notes for `heimdall.shell_interface`: the output functions, their themes, and the command runners.

---

## Config

| Detail | Choice | State |
|---|---|---|
| Base type | `Config(dry_run: bool = False)` | decided |
| Tool-specific flags | a tool subclasses `Config` to add its own fields, e.g. `<ToolConfig>(Config)` with `<flag>: bool`; every runner accepts the base type, so a subclass passes through unchanged | decided |
| Who builds it | the entry point builds it once from the parsed global flags (see [`<terminal-interface>/design-plan/cli_builder.md`](cli_builder.md)) and passes it as the first argument to every command function | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in its only `Config`.

---

## Themes

Each kind of output has a fixed colour and marker. The help legend is generated from this table, so the legend cannot drift from the output.

| Theme | Marker | Colour | Used for | State |
|---|---|---|---|---|
| `STEP` | open circle | white | a step starting | decided |
| `SUCCESS` | closed circle | green | the outcome of a step; a result | decided |
| `ACTION` | arrow | blue | a mutating command being run | decided |
| `SKIPPED` | arrow | orange | a mutating command skipped in dry-run | decided |
| `QUERY` | arrow | gray | a read-only command being run | decided |
| `CONTEXT` | dot | gray | a resolved value | decided |
| `ERROR` | closed circle | red | an error, before exiting | decided |

---

## Output Functions

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_msg(msg)` | a plain message | stderr | decided |
| `log_step(msg)` | a step starting | stderr | decided |
| `log_outcome(msg)` | which path a step took | stderr | decided |
| `bind_var(var_name=..., var_value=...)` | a name and the value it resolved to | stderr | decided |
| `log_result(msg)` | a result for the user or a pipe | stdout | decided |
| `kill(msg)` | an error, then exits with status 1 | stderr | decided |

Names and signatures match the existing layer, so tools moving onto this package keep their call sites.

---

## Command Runners

| Function | Kind | In dry-run | Returns | State |
|---|---|---|---|---|
| `run_cmd(config, cmd, cwd=None)` | mutating; raises on failure | printed, skipped | nothing | decided |
| `try_run_cmd(config, cmd, cwd=None)` | mutating; reports failure | printed, skipped | `True` on success | decided |
| `run_cmd_and_capture_output(config, cmd)` | mutating, output captured | printed, skipped | stdout | decided |
| `query_cmd(cmd, error_on_failure=True)` | read-only | runs | stdout | decided |
| `probe_cmd(cmd)` | read-only, silent | runs | exit status | decided |
| `query_cmd_result(cmd, cwd=None)` | read-only | runs | a `CommandResult` | proposed |

`CommandResult` holds `cmd_text` (the command exactly as printed), `stdout`, `stderr`, and `returncode`, and never raises on a non-zero exit. It serves tools that record each finding together with the command that produced it, so the record can show what ran and let the user rerun it. State: proposed.

| Question | State |
|---|---|
| Give `run_cmd_and_capture_output` and `query_cmd` the same `cwd` argument as the other runners | proposed |
| How a command with arguments containing spaces is printed, so that the printed text can be copied and run as is | open |

---

## Timestamps and Persistent Record

Some tools keep a history of what they did to a machine. Two optional features serve them, set once per process by the entry point:

| Feature | Detail | State |
|---|---|---|
| Timestamps | a `YYYY-MM-DD HH:MM:SS` prefix on every line printed to the terminal | proposed |
| Persistent record | every line printed, steps and commands included, is also appended to a file, as plain text without colour markup | proposed |
| Record format | one line per entry: timestamp, tool name, then the line as printed | proposed |
| Record in dry-run | open | open |

Both are off unless a tool turns them on, so tools that do not need them see no change.
