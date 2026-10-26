# Adopting

Design notes for moving an existing tool onto `heimdall`, and for keeping each tool on a known version.

---

## Moving a Tool Over

A tool moves over on its own branch. The goal is identical behaviour, so every step is checkable.

1. Add `heimdall` as a dependency, pinned to a commit (see [Pinning](#pinning)).
2. Replace the import of the terminal module of the tool with `from heimdall import shell_interface`; output call sites stay unchanged.
3. If the tool has flags beyond `--dry-run`, subclass `RunParams` with them, frozen like the base.
4. Rename mechanically: the `config` parameter of every command function becomes `run_params`, every runner call uses the new runner name (see [Runner names](#runner-names)) and passes `run_params=`, `command=`, and `working_directory=` (was `cwd=`) by keyword, `cli_command` and `command_group` become `make_command` and `make_command_group` with `command_*` keywords, and every command function takes its arguments keyword-only, named after their argparse destinations.
5. Replace the entry point of the tool with a `Tool` and a call to `run_cli`.
6. Delete the copy of the terminal layer that the tool kept.
7. Check: the tests of the tool pass after the mechanical rename, and the help output before and after lists the same commands, flags, and help text in the same order.

Some output changes by design and is not a regression: help columns are aligned with spaces from the longest label, the legend is generated, the flags heading reads "Flags", and printed commands are quoted where an argument contains spaces or square brackets. A tool whose copy of the layer is older than this package also gains the newer features (dry-run styles, read-only runners) as part of the move.

A tool that uses its own plain-text logging moves its narration onto the output functions; anything specific to its subject, such as file actions, stays in the tool and calls the command runners.

### Runner names

| Earlier name | Name here | Change at the call site |
|---|---|---|
| `run_cmd(config, cmd)` | `run_command_and_show_output(run_params=..., command=...)` | none beyond the rename |
| `try_run_cmd(config, cmd)` | `run_command_and_show_output(run_params=..., command=..., raise_error=False)` | add `raise_error=False` |
| `run_cmd_and_capture_output(config, cmd)` | `run_command_and_capture_output(run_params=..., command=...)` | none beyond the rename |
| `query_cmd(cmd, error_on_failure=...)` | `query_command_and_capture_output(command=..., raise_error=...)` | `error_on_failure` becomes `raise_error` |
| `query_cmd_result(cmd)` | `query_command_and_capture_outcome(command=...)` | none beyond the rename |
| `probe_cmd(cmd)` | `query_command_and_discard_output(command=...)` | pass `command` by keyword |

### Output function names

| Earlier name | Name here | Change at the call site |
|---|---|---|
| `log_msg(msg)` | `log_note(message)` | none beyond the rename; the line gains the note symbol |
| `log_step(msg)` | `log_task(message)` | none beyond the rename |
| `log_outcome(msg)` | `log_outcome(message, status=...)` | choose a status for every call: success, warning, skipped, or failure; this is the one change that needs judgement, not a rename |
| `bind_var(var_name=..., var_value=...)` | `log_value(name=..., value=...)` | rename the keywords |
| `log_result(msg)` | `log_result(message)` | none |
| `kill(msg)` | `exit_with_error(message)` | none beyond the rename |

---

## Pinning

| Rule | Detail | State |
|---|---|---|
| Pin by commit | each tool pins `heimdall` to a commit under `[tool.uv.sources]`, so a change here reaches a tool only when its pin moves | decided |
| Local development | a tool can override the pin with a path to a local checkout while developing against an unreleased change | decided |
| Changes here | additive where possible; a change that breaks a signature says so in its commit message | decided |
