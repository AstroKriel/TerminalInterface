# manage_cli

Design notes for `huginn.manage_cli`: describing a tool and its cmds once, and getting argument parsing, grouped help, and flags from that description. The args themselves are in [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md).

---

## Structure

A tool is described as nested frozen dataclasses, one per concept, so the structure itself enforces what used to need checks: a visible cmd cannot be ungrouped, and a group exists once instead of being stamped onto each cmd. Inside each dataclass, field names drop the owner prefix, since the type already qualifies them (`cmd.name`, not `cmd.cmd_name`). Within `manage_cli`, a cmd is a cmd of the tool: it runs as `<tool> <cmd> [arguments]`.

```text
CommandLineTool
├── name, description
├── flags: list[FlagArgument]
├── cmd_groups: list[CommandGroup]
│   └── CommandGroup(title, cmds: list[Command])
│       └── Command(name, description, fn, arguments: list[PositionalArgument | NamedArgument | FlagArgument])
├── hidden_cmds: list[Command]
├── tool_params_type: type[ToolParams]
└── output_params: OutputParams(show_timestamps, log_path)
```

| Part | Detail | State |
|---|---|---|
| Arguments | `Command.arguments` and `CommandLineTool.flags` hold the arg kinds from `cmd_args`: `PositionalArgument`, `NamedArgument`, and `FlagArgument` (see [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md)) | decided |
| Defaults | the same rule as for args: a field has a default only when it means "nothing extra", e.g. empty `arguments` or `hidden_cmds` | decided |
| `Command` | one cmd: `name`, `description`, `fn`, and `arguments` | decided |
| Definition checks | each argument, cmd, and tool checks itself when made, so a mistake in a command table fails when the tool starts; see [Definition Checks](#definition-checks) | decided |
| `CommandGroup` | cmds listed together in help under one `title`; a `str` enum title prints its value | decided |
| Hidden cmds | `hidden_cmds` on the tool: registered and runnable, left out of help | decided |
| Tool params | `tool_params_type` names `ToolParams` or a subclass; `run_cli` builds it with `from_parsed_arguments` (see [`<terminal-interface>/design-plan/params.md`](params.md)) | decided |
| Output params | `output_params` holds an `OutputParams` (`show_timestamps`, `log_path`); `run_cli` hands it to the output together with the tool params | decided |
| Built-in flags | every tool gets `--dry-run` and `--hide-actions`; both are off unless the user passes them | decided |
| Failed cmd | `run_cli` reports an error outcome naming the shell cmd that failed, then exits with its exit status | decided |
| How a cmd function is called | `fn(tool_params=..., <param_1>=..., <param_2>=...)`, every argument by keyword under its `param_name` (the named argument `base-ref` becomes `base_ref`) | decided |
| Type name | `CommandLineTool`; a variable holding one is named `command_line_tool` | decided |

Calling by keyword means a cmd function declares its parameters keyword-only and names them after the arguments they receive, so a mismatch fails loudly instead of passing a value to the wrong parameter.

```text
run_cli(command_line_tool=command_line_tool)
```

`run_cli` builds the arg parser, registers every cmd and its arguments, parses, builds the tool params, sets the output for the run, dispatches, and exits with the return code of a failed shell cmd when one raises. State: decided.

---

## Definition Checks

The checks on a single argument are in [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md). The checks here involve more than one argument, and use the same message form: the type before the colon, then the field, what it must be and why, and what it got, e.g. ``CommandLineTool: argument parameter names for cmd `go` must differ from the flags of the tool; got `dry_run`, which is also `--dry-run`.`` Checks that argparse already makes clearly are left to it.

| Where | Check | State |
|---|---|---|
| `Command` | parameter names are unique across its arguments, and none is `tool_params` | decided |
| `CommandLineTool` | no cmd argument reuses the parameter name of a tool flag, built-in flags included | decided |
| Left to argparse | two flags with the same form, a tool redefining a built-in flag, and two cmds with the same name: argparse fails with a clear message when it builds the arg parser | decided |

---

## Help Output

| Section | Contents | State |
|---|---|---|
| When shown | on `-h` or `--help`, and when no command is given | decided |
| Header | tool name and description | decided |
| Usage | `<tool_name> [--dry-run] [--hide-actions] [<extra-flags>] <command> [args]`, built from `flags` | decided |
| Cmd groups | one heading per group title, each cmd with its description, in declaration order | decided |
| Flags | the built-in flags and each extra flag with its description; a flag with a short name shows both forms, e.g. `-o, --output` | decided |
| Output legend | one line per message type, generated from the message types | decided |
| Indent | four spaces before every row | decided |
| Separator | spaces only, never tabs, so the layout is the same width on every machine | decided |
| Column width | computed per help screen: the longest label on the screen (command, flag, or legend label) plus two spaces; every section shares it, so descriptions line up across the whole screen | decided |

The column width is never hardcoded, so a long command name widens the column instead of breaking the alignment.

The third generalisation: generating the legend from the message types removes the second copy of the colour values that the existing help kept.
