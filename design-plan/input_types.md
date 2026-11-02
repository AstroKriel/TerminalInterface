# input_types

Design notes for `huginn.input_types`: what kind of thing an input of an argument is. Arguments are described in [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md).

---

## Input Types

| Detail | Choice | State |
|---|---|---|
| Type | `InputType(placeholder_name, convert_fn)`, frozen: `placeholder_name` is the name shown in help, and `convert_fn` turns the typed text into the value the cmd receives | decided |
| Placeholder name | letters, digits, `_`, and `-` only, checked when the input type is made; huginn adds the brackets, so a tool cannot pass its own | decided |
| Basic set | `TEXT`, `NUMBER` (`int`), `DATE` (`datetime.date`, from `YYYY-MM-DD`), `PATH` and `DIR` (both `Path`; `<dir>` tells the user more) | decided |
| Extending | a tool defines its own input types the same way, in an `input_types` module of its own, e.g. `BRANCH = InputType(placeholder_name="branch")`; domain types stay in the tool, so huginn names no tool-specific concept | decided |
| Shown as | always `<placeholder name>`, so every tool prints inputs the same way | decided |
| Required | every positional and named argument states its input type; there is no default, so a tool picks `TEXT` on purpose rather than by leaving it out; a flag takes no input and has no input type | decided |
| Bad input | `convert_fn` raises `argparse.ArgumentTypeError` with a message for the user, so a bad input is a usage error before the cmd runs, e.g. ``date must be YYYY-MM-DD; got `2026-13-01`.`` | decided |

The label and the conversion live together, so they cannot disagree: `NUMBER` always shows `<number>` and always gives an `int`. A shared set of generic types grows only when several tools show the same need.
