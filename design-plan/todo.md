# To Do

Changes found in review that are too large to make on the spot. Each waits until use of huginn confirms it; friction found by the tools that use huginn is collected in the ProjectNotes thread `settle-the-interface-through-use/` under `<project-notes>/Asgard/sindri/huginn/threads/`.

---

## Open

| Item | Detail | Raised |
|---|---|---|
| A cmd type that holds its parts | cmds are run as parts (`list[str]`) but shown as text, and tools turn parts into text in different ways: a hand-written f-string, `shlex.join` at the caller, or text returned already joined, as in `CommandOutcome.cmd`. A frozen dataclass holding the parts, with a `text` property that is the one place `shlex.join` is called, would serve both: runners and `CommandOutcome` take it, and tools only ever read `.text`. Open: the type name, since `Command` is taken by the entry of a tool in `manage_cli`. This changes every runner signature | review, 2026-11-02 |
| Type checks in the definition checks | the `__post_init__` checks of `InputValueType`, the argument types, `Command`, and `CommandLineTool` check names and combinations, but not the types of their fields, e.g. a `long_arg_name` that is not a `str`, or an `allowed_num_input_values` that is not an `AllowedNumInputValues`. Once `heimdall`, the planned types and validation package, is built, use it to check field types in the same `__post_init__` methods; huginn then depends on `heimdall`, as the planned dependency tree already has it | review, 2026-11-02 |
| Arg names as a validated type | the long and short arg names are checked by `_ArgumentWithNames`, the class that holds them; a dataclass per kind of name would let each name hold its own rules and dash prefix, but would make every argument in a command table longer to write. If `heimdall` offers a cheap validated string type, use it for the arg names instead | review, 2026-11-02 |
| A width setting for blocks | the jormi log manager caps the width of its titled blocks at 100 columns by default (`BlockWidthMode.PRETTY`) and lets a script lift the cap (`PRACTICAL`); ten mimir scripts lift it, e.g. `paper_style.py` and `submit_compute_jobs.py`. Bring the setting in with the blocks, shaped by those callers: they are scripts that never call `run_cli`, so a script must be able to set it directly, and a tool could also set it on `CommandLineTool`. huginn has no blocks yet, and its one-line messages have no cap to lift | review, 2026-11-03 |
| A prompt API | huginn writes messages but cannot ask the user anything; arXivScraper asks with plain `input()`, e.g. a y/N confirmation and a free-text tag in `fetch`. Build it when arXivScraper moves onto huginn, shaped by those prompts: a prompt message kind in the same style as the others, with its own symbol and colour in the help legend, and answers converted the way input values are | arXivScraper survey, 2026-11-02 |
