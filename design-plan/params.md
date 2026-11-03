# params

Design notes for `huginn.params`: every params group in one module. What each setting does to the output is in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Groups

Params are split into groups by who sets them, and every group is defined in `params`; no other module defines params.

| Group | Fields | Set by | State |
|---|---|---|---|
| `ToolParams` | `dry_run`, `hide_actions`, plus one field per extra flag in a subclass | the user, by flags, for one run | decided |
| `OutputParams` | `show_timestamps`, `log_path` | the tool author, in `CommandLineTool.output_params` | decided |

A new setting goes in `ToolParams` when the user passes it as a flag, and in `OutputParams` when the tool author fixes it.

---

## Tool Params

| Detail | Choice | State |
|---|---|---|
| Base type | `ToolParams(dry_run: bool = False, hide_actions: bool = False)`, frozen; every flag is off unless the user passes it | decided |
| Tool-specific flags | a tool subclasses `ToolParams` as `<ToolName>Params(ToolParams)` and declares one field per extra flag, e.g. `<flag>: bool`; the subclass must also be frozen; every runner accepts the base type, so a subclass passes through unchanged | decided |
| Building from flags | `from_parsed_args` fills every field from the flag of the same name, so a subclass declares fields and nothing else; a field with no matching flag raises `AttributeError` | decided |
| Who builds it | `run_cli` builds it once from the parsed flags (see [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md)), hands it to the output with `OutputParams`, and passes it to every command function as `tool_params` | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.
