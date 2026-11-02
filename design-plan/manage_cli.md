# manage_cli

Design notes for `huginn.manage_cli`: describing a tool and its cmds once, and getting argument parsing, grouped help, and flags from that description.

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
| `Argument` | the base of every argument: `description`, which has no default, so every argument states it, and `add_to_parser`, which registers it with argparse; never made directly | decided |
| `param_name` | what the cmd function receives an argument as; every concrete kind has one, a field on `PositionalArgument` and derived from the long arg name on the named kinds, so `Command.arguments` lists the three concrete kinds rather than the base | decided |
| `_ArgumentWithInputValue` | private; what an argument the user types a value for adds: `input_value_type` (an `InputValueType`, see [`<terminal-interface>/design-plan/input_value_types.md`](input_value_types.md)), `allowed_num_input_values`, and `default_value`, and turning them into argparse settings | decided |
| `_ArgumentWithNames` | private; what an argument the user types by name adds: `long_arg_name` (shown as `--<long arg name>`) and optional `short_arg_name` (shown as `-<short arg name>`), their checks, `arg_names` (every typed form, e.g. `["-o", "--output"]`), and a `param_name` from the long arg name | decided |
| `PositionalArgument(_ArgumentWithInputValue)` | an input value typed straight after the cmd name, e.g. `arch-news-since 2026-10-01`; adds `param_name`; only its value is typed, so it has a param name and no arg name | decided |
| `NamedArgument(_ArgumentWithNames, _ArgumentWithInputValue)` | an input value given after its arg name, e.g. `--output ./notes`; adds `is_required` | decided |
| `FlagArgument(_ArgumentWithNames)` | a named argument with no input value, e.g. `--dry-run`; received as `True` if passed and `False` if not | decided |
| Ownership | each class owns the fields it adds, their checks, and their part of the argparse wiring, so no module function does the work of a type; the concrete kinds are the combinations of the two private bases, and tools only ever write the concrete kinds | decided |
| Check chain | each `__post_init__` calls `super().__post_init__()` first, so making a `NamedArgument` runs the arg name checks of `_ArgumentWithNames`, then its own; `Argument.__post_init__` ends the chain | decided |
| Input value type | `input_value_type` has no default and no `None`, and exists only on the kinds the user types a value for, so a flag cannot be given one and an input value cannot be left without one | decided |
| Defaults | a field has a default only when the default means "nothing extra": absent (`short_arg_name=None`, `default_value=None`, empty `arguments`), off (`is_required=False`), or the plain case (`allowed_num_input_values=ONE`); a field with no neutral value, such as `description` or `input_value_type`, has no default, so every argument states it; this keeps a command table to what is special about each entry | decided |
| `AllowedNumInputValues` | how many input values an argument allows the user to type: `ONE` (the default), `ZERO_OR_ONE`, `ZERO_OR_MORE`, or `ONE_OR_MORE`; the enum answers questions about itself: `nargs_symbol` gives the argparse symbol (`?`, `*`, `+`, or `None` for `ONE`), and `is_zero_allowed` says whether the user may type nothing, so a default value can apply | decided |
| `Command` | one cmd: `name`, `description`, `fn`, and `arguments` | decided |
| Definition checks | each argument, cmd, and tool checks itself when made, so a mistake in a command table fails when the tool starts; see [Definition Checks](#definition-checks) | decided |
| `CommandGroup` | cmds listed together in help under one `title`; a `str` enum title prints its value | decided |
| Hidden cmds | `hidden_cmds` on the tool: registered and runnable, left out of help | decided |
| Tool params | `tool_params_type` names `ToolParams` or a subclass; `run_cli` builds it with `from_parsed_arguments` (see [`<terminal-interface>/design-plan/params.md`](params.md)) | decided |
| Output params | `output_params` holds an `OutputParams` (`show_timestamps`, `log_path`); `run_cli` hands it to the output together with the tool params | decided |
| Built-in flags | every tool gets `--dry-run` and `--hide-actions`; both are off unless the user passes them | decided |
| Failed cmd | `run_cli` reports an error outcome naming the shell cmd that failed, then exits with its exit status | decided |
| How a cmd function is called | `fn(tool_params=..., <param_1>=..., <param_2>=...)`, every argument by keyword under its `param_name` (the named argument `base-ref` becomes `base_ref`) | decided |
| Arg and param | an arg is what the user types on the command line, e.g. `--output`; a param is what the cmd function receives, e.g. `output`; the shorthand marks these concrete things, while the types that define them keep the full word, e.g. `NamedArgument` | decided |
| Type name | `CommandLineTool`; a variable holding one is named `command_line_tool` | decided |

Calling by keyword means a cmd function declares its parameters keyword-only and names them after the arguments they receive, so a mismatch fails loudly instead of passing a value to the wrong parameter.

```text
run_cli(command_line_tool=command_line_tool)
```

`run_cli` builds the parser, registers every cmd and its arguments, parses, builds the tool params, sets the output for the run, dispatches, and exits with the return code of a failed shell cmd when one raises. State: decided.

---

## Definition Checks

Each check catches a definition that would otherwise pass silently or fail later with an unclear message, and raises a `ValueError` that says what went wrong. The scope before the colon is always just the type, as written in the command table; the sentence then names the field, the argument it belongs to as "for `<name>`", what it must be and why, and what it got, e.g. ``NamedArgument: `default_value` for `output` must be `None` when `is_required` is `True`, since a required argument never falls back; got `.`.`` A check on the identifying name itself leaves out the "for", since that name is the bad value, e.g. ``PositionalArgument: `param_name` must be lowercase letters, digits, and `_`, starting with a letter; got `Since`.`` Rules the types already express, such as a flag having no input value type, need no check. Checks that argparse already makes clearly are left to it.

| Where | Check | State |
|---|---|---|
| `PositionalArgument` | `param_name` is lowercase letters, digits, and `_`, starting with a letter, since it is a Python parameter name | decided |
| `PositionalArgument` | `default_value` only with `ZERO_OR_ONE` or `ZERO_OR_MORE`; otherwise an input value is always given and the default is never used | decided |
| `NamedArgument`, `FlagArgument` | `long_arg_name` is lowercase letters, digits, and `-`, starting with a letter, with no dashes passed in | decided |
| `NamedArgument`, `FlagArgument` | `short_arg_name` is one to three letters | decided |
| `NamedArgument` | not `is_required` together with `default_value`: a required argument never falls back | decided |
| `Command` | parameter names are unique across its arguments, and none is `tool_params` | decided |
| `CommandLineTool` | no cmd argument reuses the parameter name of a tool flag, built-in flags included | decided |
| Left to argparse | two flags with the same form, a tool redefining a built-in flag, and two cmds with the same name: argparse fails with a clear message when it builds the parser | decided |

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
