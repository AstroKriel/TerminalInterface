# manage_log

Design notes for `huginn.manage_log`: the output functions, their message types, and how the output of one run is set up.

---

## Message Types

The model has three concepts: a task (a stage of the work, announced in words before it starts), an action (something done to the system, either changing it or only inspecting it, shown before it happens), and an outcome (how a task or action ended, with a status, optionally carrying a value or a result).

The concepts are layered: each base concept has its own kinds.

```text
task                 a stage of the work, announced in words before it starts
action               something done to the system, shown before it happens
├── change           changes the system; skipped in dry-run
└── inspection       only reads the system; always runs
outcome              how a task or action ended, reported afterwards
├── status           success | warning | skipped | failure
└── content          optional: a value (what an action produced) or a result (for the user, on stdout)
```

The symbol says which concept a line is (open circle: task; hooked arrow: note; right arrow: action; closed circle or middle dot: outcome) and the colour says which type or status. The vocabulary follows the jormi log manager: `MessageStyle` (`colour`, `symbol`, `description`), `Colour`, `Symbol`, notes, and an `ERROR` status beside `FAILURE`. Each base concept has its facets as enums of `MessageStyle` in the private `_message_styles`: `TASK_STYLE`; `NOTE_STYLE`; `Action` (`CHANGE`, `INSPECTION`); `OutcomeStatus` (`SUCCESS`, `WARNING`, `SKIPPED`, `FAILURE`, `ERROR`); `OutcomeContent` (`VALUE`, `RESULT`). There are no named combinations: a change skipped in dry-run is drawn by a copy of the change style with the skipped colour, and the legend lists only the building blocks. `MESSAGE_GROUPS` lists everything by concept, and the help legend is generated from it, so the legend cannot drift from the output. A style draws a message itself, with `MessageStyle.render`, and the private `_manage_output` sends it to each destination it belongs in with `route_msg`. A style always colours the whole message, symbol and text together. Every colour is mid-brightness, so a message reads on both light and dark terminal themes; there is no white.

| Concept | Facet | Value | Symbol | Colour | State |
|---|---|---|---|---|---|
| task | | | open circle | purple | decided |
| note | | | hooked arrow | purple | decided |
| action | type | change | right arrow | blue | decided |
| action | type | inspection | right arrow | grey | decided |
| outcome | status | success | closed circle | green | decided |
| outcome | status | warning | closed circle | yellow | decided |
| outcome | status | skipped | closed circle | orange | decided |
| outcome | status | failure that does not end the run | closed circle | red | decided |
| outcome | status | error that ends the run | closed circle | red | decided |
| outcome | content | value an action produced | middle dot | grey | decided |
| outcome | content | result | none | none: plain text on stdout, never wrapped, so a pipe gets clean data | decided |

An inspection exists to produce a value; a change exists to alter the system and may produce a value along the way, e.g. the path of a directory it created. In dry-run a change is skipped, so a value it would have produced is unknown: anything that depends on that value reports a skipped outcome instead of carrying on with a placeholder. State: decided.

> **Note:** a richer message layer, with titled blocks and notes, is expected to move into this package later. These message types and statuses are its first layer, not a closed set.

---

## Output Functions

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_note(text)` | a note about the work, neither a task nor an outcome | narration | decided |
| `log_task(text)` | a task starting | narration | decided |
| `log_outcome(text, *, status)` | how a task or action ended; `status` is required, never assumed | narration | decided |
| `log_value(*, name, value)` | a value an action produced, as `name = value` | narration | decided |
| `log_result(text)` | a result for the user or a pipe | stdout | decided |
| `exit_with_error(text, *, exit_code=1)` | an error outcome, then exits with `exit_code` | narration | decided |

`OutcomeStatus` is available as `manage_log.OutcomeStatus`.

Narration always goes to stderr; whoever runs the tool can merge the two streams, e.g. with `2>&1`. A tool supplies raw text and chooses the kind of message, and huginn handles the styling: `text` always prints exactly as written, so square brackets in a news title or a file name need no care. Every message is escaped in one place, `MessageStyle.render`, before its style adds the symbol and colour; text huginn prints without a style, such as the help screen, is escaped where it is printed.

---

## Output for One Run

The entry point sets these once per process, from the tool params (see [`<terminal-interface>/design-plan/params.md`](params.md)) and the name of the tool. The log file keeps a history of what each tool did to a machine.

| Feature | Detail | State |
|---|---|---|
| Hidden actions | with `hide_actions`, action messages are left off the terminal; set by the `--hide-actions` flag, off by default; a cmd skipped in dry-run still shows, since showing it is the point of a dry run | decided |
| Log | every message, hidden actions included, is also appended to `~/.huginn_logs/<tool name>.log`, as plain text without markup; always on for a tool run through `run_cli`, with nothing for the tool author to set | decided |
| Log location | one folder in the home folder for every huginn tool, outside every repo, so git never sees it; one file per tool, named after `CommandLineTool.name`, e.g. `git_helpers.log` | decided |
| Log format | `[<time stamp>] <line>`, one line per entry; the time stamp is `YYYY-MM-DD HH:MM:SS`, from `datetime.now().isoformat(sep=" ", timespec="seconds")` | decided |
| Run header | each run starts with one line giving the command as typed, after a `$ `, e.g. `$ git_helpers sync --allow-dirty`, so runs can be told apart in the one file; the `$ ` keeps it apart from a plain result line | decided |
| Log cannot be written | the run stops with an error naming the log file and exits with status 1; a run that cannot be recorded is not done quietly, and there is no way to turn the log off | decided |
| No action goes unlogged | a message is logged before it is shown, and an action is shown before it runs, so when the log fails, the action it belongs to never starts and is never shown as started | decided |
| Log in dry-run | nothing is written: the log is a history of what was done to the machine, and a dry-run does nothing | decided |
| Log growth | the file is only ever appended to; no rotation until a log grows large enough to need it | decided |
| Terminal time stamps | none; the log carries the times | decided |
| Tests | tests point the home folder at a temporary folder, so they never write to the real log | decided |

A script that never calls the entry point writes no log file.
