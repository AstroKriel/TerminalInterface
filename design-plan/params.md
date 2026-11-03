# params

Design notes for `huginn.params`: every params group in one module. What each setting does to the output is in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Groups

Params are split into groups by who sets them, and every group is defined in `params`; no other module defines params.

| Group | Fields | Set by | State |
|---|---|---|---|
| `ToolParams` | `dry_run`, `hide_actions` | the user, by the built-in flags, for one run | decided |
| `OutputParams` | `show_time_stamps`, `log_file_path` | the tool author, in `CommandLineTool.output_params` | decided |

A new setting goes in `ToolParams` when huginn itself acts on a flag the user passes, and in `OutputParams` when the tool author fixes it. A flag only a cmd acts on is an argument of that cmd.

---

## Tool Params

| Detail | Choice | State |
|---|---|---|
| Base type | `ToolParams(dry_run: bool = False, hide_actions: bool = False)`, frozen; every flag is off unless the user passes it | decided |
| Building from flags | `from_parsed_args` fills every field from the flag of the same name; a field with no matching flag raises `AttributeError` | decided |
| Who builds it | `run_cli` builds it once from the parsed flags (see [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md)) and sets it as the active params together with `OutputParams` | decided |
| Who reads it | huginn only: the output reads `hide_actions` and `dry_run`, and the mutating runners in `manage_shell` read `dry_run`; a cmd function never receives it | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.
