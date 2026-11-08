# manage_cli

Design notes for `huginn.manage_cli`: describing a tool and its cmds once, and getting argument parsing, grouped help, and flags from that description. The args themselves are in [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md).

---

## Structure

A tool is described as nested frozen dataclasses, one per concept, so the structure itself enforces what used to need checks: a visible cmd cannot be ungrouped, and a group exists once instead of being stamped onto each cmd. Inside each dataclass, field names drop the owner prefix, since the type already qualifies them (`cmd.name`, not `cmd.cmd_name`). Within `manage_cli`, a cmd is a cmd of the tool: it runs as `<tool> <cmd> [arguments]`.

```text
CommandLineTool
├── name, description
└── cmd_groups: list[CommandGroup]
    └── CommandGroup(title, cmds: list[Command])
        └── Command(name, description, fn, args: list[CommandArgument])
```

| Part | Detail | State |
|---|---|---|
| Arguments | `Command.args` holds the arg kinds from `cmd_args`: `PositionalArgument`, `NamedArgument`, and `FlagArgument` (see [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md)) | decided |
| Defaults | the same rule as for args: a field has a default only when it means "nothing extra", e.g. empty `args` | decided |
| `Command` | one cmd: `name`, `description`, `fn`, and `args` | decided |
| Definition checks | each argument, cmd, and tool checks itself when made, so a mistake in a command table fails when the tool starts; see [Definition Checks](#definition-checks) | decided |
| `CommandGroup` | cmds listed together in help under one `title`; a `str` enum title prints its value | decided |
| Built-in params | `run_cli` builds a `BuiltInParams` from the built-in flags with `from_parsed_args` (see [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md#built-in-params)) | decided |
| Log file | `run_cli` never sets the log file path; the tool sets it before `run_cli`, usually to `manage_log.get_home_log_file_path`. A log file path that was not set, or a log file that cannot be written, ends the run with an error (see [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md)) | decided |
| Built-in flags | every tool gets `--dry-run` and `--hide-actions`, and no other tool flags; both are off unless the user passes them. huginn reads them itself, so a cmd never receives them. A flag a cmd needs, e.g. `--allow-dirty`, is a `FlagArgument` of that cmd | decided |
| Failed cmd | `run_cli` reports an error outcome naming the shell cmd that failed, then exits with its exit status | decided |
| How a cmd function is called | `fn(<param_1>=..., <param_2>=...)`, every argument of the cmd by keyword under its `param_name` (the named argument `base-ref` becomes `base_ref`) | decided |
| Type name | `CommandLineTool`; a variable holding one is named `command_line_tool` | decided |

Calling by keyword means a cmd function declares its parameters keyword-only and names them after the arguments they receive, so a mismatch fails loudly instead of passing a value to the wrong parameter.

```text
run_cli(command_line_tool=command_line_tool)
```

`run_cli` builds the arg parser, registers every cmd and its arguments, parses, builds the built-in params, sets the output for the run, dispatches, and exits with the return code of a failed shell cmd when one raises. State: decided.

---

## Definition Checks

The checks on a single argument are in [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md). The checks here involve more than one argument, and use the same message form: the type before the colon, then the field, what it must be and why, and what it got, e.g. ``CommandLineTool: argument parameter names for cmd `go` must differ from the flags of the tool; got `dry_run`, which is also `--dry-run`.`` Checks that argparse already makes clearly are left to it.

| Where | Check | State |
|---|---|---|
| `Command` | parameter names are unique across its arguments | decided |
| `CommandLineTool` | no cmd argument reuses the parameter name of a built-in flag | decided |
| Left to argparse | two flags with the same form, and two cmds with the same name: argparse fails with a clear message when it builds the arg parser | decided |

---

## Help Output

| Section | Contents | State |
|---|---|---|
| When shown | on `-h` or `--help`, and when no command is given | decided |
| Header | tool name and description | decided |
| Usage | `<tool_name> [--dry-run] [--hide-actions] <command> [args]` | decided |
| Cmd groups | one heading per group title, each cmd with its description, in declaration order | decided |
| Flags | the built-in flags, each with its description | decided |
| Output legend | one line per message type, generated from the message types; the label column holds the group name, plain and on the first row of its group only, then the symbol and colour name in that colour, e.g. `Actions   → blue` | decided |
| Indent | four spaces before every row, set by `row_indentation` on the help screen | decided |
| Separator | spaces only, never tabs, so the layout is the same width on every machine | decided |
| Column width | computed per help screen: the longest label on the screen (command, flag, or legend label, group name included) plus `col_separation` spaces, two by default; every section shares it, so descriptions line up across the whole screen | decided |

The column width is never hardcoded, so a long command name widens the column instead of breaking the alignment.

The third generalisation: generating the legend from the message types removes the second copy of the colour values that the existing help kept.
