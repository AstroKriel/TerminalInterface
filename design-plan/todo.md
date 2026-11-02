# To Do

Changes found in review that are too large to make on the spot. Each waits until use of huginn confirms it; friction found by the tools that use huginn is collected in the ProjectNotes thread `settle-the-interface-through-use/` under `<project-notes>/Asgard/sindri/huginn/threads/`.

---

## Open

| Item | Detail | Raised |
|---|---|---|
| Shell runners take `dry_run`, not `ToolParams` | the runners in `manage_shell` only ever read `dry_run`; taking `dry_run: bool` directly would mean `manage_shell` knows nothing about tools or their flags | review, 2026-11-02 |
| A cmd type that holds its parts | cmds are run as parts (`list[str]`) but shown as text, and tools turn parts into text in different ways: a hand-written f-string, `shlex.join` at the caller, or text returned already joined, as in `CommandOutcome.cmd`. A frozen dataclass holding the parts, with a `text` property that is the one place `shlex.join` is called, would serve both: runners and `CommandOutcome` take it, and tools only ever read `.text`. Open: the type name, since `Command` is taken by the entry of a tool in `manage_cli`. Do it in the same pass as the item above, since both change every runner signature | review, 2026-11-02 |
| Type checks in the definition checks | the `__post_init__` checks of `InputType`, the argument types, `Command`, and `CommandLineTool` check names and combinations, but not the types of their fields, e.g. a `long_name` that is not a `str`, or an `allowed_input_count` that is not an `AllowedInputCount`. Once `heimdall`, the planned types and validation package, is built, use it to check field types in the same `__post_init__` methods; huginn then depends on `heimdall`, as the planned dependency tree already has it | review, 2026-11-02 |
