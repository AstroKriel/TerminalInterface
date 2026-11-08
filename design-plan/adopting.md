# Adopting

Design notes for moving an existing tool onto `huginn`, and for keeping each tool on a known version.

---

## Moving a Tool Over

A tool moves over on its own branch. The goal is identical behaviour, so every step is checkable.

1. Add `huginn` as a dependency, pinned to a commit (see [Pinning](#pinning)).
2. Replace the import of the terminal module of the tool with `from huginn import manage_log, manage_shell`; output calls go through `manage_log` and runner calls through `manage_shell`.
3. If the tool has flags beyond `--dry-run` and `--hide-actions`, make each one a `FlagArgument` of the cmds that use it; the cmd function receives it by name, e.g. `allow_dirty`.
4. Rename mechanically: the `config` parameter of every cmd function goes, every runner call uses the new runner name (see [Runner names](#runner-names)) and passes `cmd_parts=` (was `cmd`), and `working_directory=` (was `cwd=`) by keyword, and every cmd function takes its arguments keyword-only, named after their argparse destinations.
5. Replace the entry point and command table of the tool with one `CommandLineTool` and a call to `run_cli`: `cli_command` entries become `Command`s, `command_group` calls become `CommandGroup`s, a hidden command becomes a listed command or is deleted, and arguments become `PositionalArgument`s, `NamedArgument`s, or `FlagArgument`s from `huginn.cmd_args`, with the field names in [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md) (a `--name` loses its dashes and becomes `long_arg_name`, an `is_switch=True` argument becomes a `FlagArgument`, `nargs` strings become `AllowedNumInputValues` members, and each `value_type` and `metavar` pair becomes one `input_value_type`, from `cmd_args.InputValueTypes` or the tool's own subclass of it; every argument needs a `description`, and every positional and named argument an `input_value_type`, so arguments that set neither get both).
6. Delete the copy of the terminal layer that the tool kept.
7. Set the log file path in the `main` of the tool, before `run_cli`: `manage_log.set_log_file_path(log_file_path=manage_log.get_home_log_file_path(tool_name="<tool name>"))`. In every test that calls `run_cli`, set the log file path to a temporary folder, or to `None`, so the tests never write to the real log.
8. Check: the tests of the tool pass after the mechanical rename, and the help output before and after lists the same commands, flags, and help text in the same order.

Some output changes by design and is not a regression: help columns are aligned with spaces from the longest label, the style legend is generated, the flags heading reads "Flags", a command that was hidden is now listed, and printed commands are quoted where an argument contains spaces or square brackets. A tool whose copy of the layer is older than this package also gains the newer features (dry-run styles, read-only runners) as part of the move. Every tool also gains a log file at `~/.huginn_logs/<tool name>.log`, from step 7.

A tool that uses its own plain-text logging moves its narration onto the output functions; anything specific to its subject, such as file actions, stays in the tool and calls the command runners.

### Runner names

| Earlier name | Name here | Change at the call site |
|---|---|---|
| `run_cmd(config, cmd)` | `run_cmd_and_show_output(cmd_parts=...)` | drop `config` |
| `try_run_cmd(config, cmd)` | `run_cmd_and_show_output(cmd_parts=..., raise_error=False)` | drop `config`; add `raise_error=False` |
| `run_cmd_and_capture_output(config, cmd)` | `run_cmd_and_capture_output(cmd_parts=...)` | drop `config` |
| `query_cmd(cmd, error_on_failure=...)` | `query_cmd_and_capture_output(cmd_parts=..., raise_error=...)` | `error_on_failure` becomes `raise_error` |
| `query_cmd_result(cmd)` | `query_cmd_and_capture_outcome(cmd_parts=...)` | none beyond the rename |
| `probe_cmd(cmd)` | `query_cmd_and_discard_output(cmd_parts=...)` | pass `cmd_parts` by keyword |

### Output function names

| Earlier name | Name here | Change at the call site |
|---|---|---|
| `log_msg(msg)` | `log_note(text)` | none beyond the rename; the line gains the note symbol |
| `log_step(msg)` | `log_task(text)` | none beyond the rename |
| `log_outcome(msg)` | `log_outcome(text, status=...)` | choose a status for every call: success, warning, skipped, or failure; this is the one change that needs judgement, not a rename |
| `bind_var(var_name=..., var_value=...)` | `log_value(name=..., value=...)` | rename the keywords |
| `log_result(msg)` | `log_result(text)` | none |
| `kill(msg)` | `exit_with_error(text)` | none beyond the rename |

---

## Pinning

| Rule | Detail | State |
|---|---|---|
| Pin by commit | each tool pins `huginn` to a commit under `[tool.uv.sources]`, so a change here reaches a tool only when its pin moves | decided |
| Local development | a tool can override the pin with a path to a local checkout while developing against an unreleased change | decided |
| Changes here | additive where possible; a change that breaks a signature says so in its commit message | decided |
