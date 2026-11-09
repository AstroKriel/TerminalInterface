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

The symbol says which concept a line is (open circle: task; hooked arrow: note; right arrow: action; closed circle or middle dot: outcome) and the colour says which type or status. The vocabulary follows the jormi log manager: `MessageStyle` (`colour`, `symbol`, `description`), `Colour`, `Symbol`, notes, and an `ERROR` status beside `FAILURE`. Each base concept has its facets as enums of `MessageStyle` in the private `_message_styles`: `TASK_STYLE`; `NOTE_STYLE`; `Action` (`CHANGE`, `INSPECTION`); `OutcomeStatus` (`SUCCESS`, `WARNING`, `SKIPPED`, `FAILURE`, `ERROR`); `OutcomeContent` (`VALUE`, `RESULT`). There are no named combinations: a change skipped in dry-run is drawn by a copy of the change style with the skipped colour, and the style legend lists only the building blocks. `MESSAGE_GROUPS` lists everything by concept, and the style legend in the help is generated from it, so it cannot drift from the output. A style draws a message itself, with `MessageStyle.render`, and the private `_manage_output` sends it to each destination it belongs in with `route_msg`. A style always colours the whole message, symbol and text together. Every colour is mid-brightness, so a message reads on both light and dark terminal themes; there is no white.

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
| outcome | content | value under a note or an outcome, one indent deeper | middle dot | grey | decided |
| prompt | | a question for the user (see [Prompts](#prompts)) | question mark | cyan | decided |
| outcome | content | result | none | none: plain text on stdout, never wrapped, so a pipe gets clean data | decided |

An inspection exists to produce a value; a change exists to alter the system and may produce a value along the way, e.g. the path of a directory it created. In dry-run a change is skipped, so a value it would have produced is unknown: anything that depends on that value reports a skipped outcome instead of carrying on with a placeholder. State: decided.

> **Note:** a richer message layer, with titled blocks and notes, is expected to move into this package later. These message types and statuses are its first layer, not a closed set.

---

## Output Functions

A tool chooses from one function per concept of the message model: task, note, outcome, result, error, and prompt.

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_task(text)` | a task starting, from one step to the heading of a whole run | narration | decided |
| `log_note(text, *, values=None)` | a note about the work, neither a task nor an outcome, then its values, if any | narration | decided |
| `log_outcome(text, *, status, values=None)` | how a task or action ended, then its values, if any; `status` is required, never assumed | narration | decided |
| `log_result(text)` | a result for the user or a pipe | stdout | decided |
| `exit_with_error(text, *, exit_code=1)` | an error outcome, then exits with `exit_code` | narration | decided |
| `report_failure(text, *, raise_error)` | for code that lets its caller choose: raises with `text`, or prints a failure outcome and carries on (see [`<terminal-interface>/design-plan/jormi_log.md`](jormi_log.md#library-code)) | narration | proposed |
| `ask(text, *, input_value_type)` | a question, then returns the answer (see [Prompts](#prompts)) | narration | decided |

`OutcomeStatus` is available as `manage_log.OutcomeStatus`.

`values` is a mapping of names to values, each printed on its own line under the message, one indent deeper, in the value style, e.g.:

```text
● Save wavenumbers
    · path = <output path>
```

A value always belongs to a note or an outcome, so there is no function for a value on its own; the earlier `log_value` is gone, and a caller passes the value to the note or outcome it belongs to. State: decided.

Narration always goes to stderr; whoever runs the tool can merge the two streams, e.g. with `2>&1`. A tool supplies raw text and chooses the kind of message, and huginn handles the styling: `text` always prints exactly as written, so square brackets in a news title or a file name need no care. Every message is escaped in one place, `MessageStyle.render`, before its style adds the symbol and colour; text huginn prints without a style, such as the help screen, is escaped where it is printed.

---

## Prompts

A prompt asks the user something and returns the answer. It is a message type of its own, so it has a style, shows in the style legend, and is logged like any other message. The first caller is a tool that confirms before saving and asks for a free-text tag.

| Detail | Choice | State |
|---|---|---|
| Where | in `manage_log`, beside the output functions, so a tool imports nothing new; a prompt is a message that also reads an answer | decided |
| One function | `ask(text, *, input_value_type) -> Any`; the answer, trimmed of surrounding spaces, is converted by `input_value_type.convert_fn`, as for a cmd arg, e.g. `cmd_args.InputValueTypes.NUMBER`, so prompts and cmd args share one set of input value types | decided |
| Yes or no | the input value type `InputValueTypes.YES_OR_NO`; the question ends in `[y/N]`; an answer starting with `y` or `Y` is `True`, and anything else, an empty answer included, is `False`. Yes is never the default: every current caller defaults to no, and no is the safe answer when the user only presses enter | decided |
| Bad answer | for every other input value type, an empty answer, or one that does not convert, reports a failure outcome naming the problem, e.g. ``answer must be <number>; got `many`.``, with the placeholder as help shows it, and asks again | decided |
| Style | `PROMPT_STYLE` in `_message_styles`, a cyan `?`, in its own "Prompts" group of `MESSAGE_GROUPS`, so the style legend lists it | decided |
| Stream | the question goes to stderr with the other narration, and the answer is typed on the same line, so stdout stays clean for results; an answer piped in is not echoed by a terminal, so huginn prints it after the question, and the output reads the same either way | decided |
| Log | one line per prompt: the question as shown, then the answer as typed, e.g. `? save it again? [y/N] y`; a prompt that asks again logs each attempt | decided |
| No one to answer | the answer is read from stdin, so piped input, e.g. from `yes`, still works; when stdin ends without an answer, e.g. in a job, the prompt ends the run with an error naming the question instead of waiting or guessing | decided |
| Log file path not set | the prompt raises `LogFileError` before it asks, so no answer is typed for a run that then stops | decided |
| Dry-run | a prompt still asks: asking changes nothing, and the answer often decides which actions a dry run shows | decided |
| Hidden actions | a prompt is not an action, so `--hide-actions` never hides it | decided |

A missing required arg is not a prompt: argparse reports it before the cmd runs, so a tool never asks for an arg at runtime.

---

## Built-In Params

`BuiltInParams` holds the values of the built-in flags for one run. It is defined in the private `_manage_output`, beside the one active copy that huginn reads.

| Detail | Choice | State |
|---|---|---|
| Base type | `BuiltInParams(dry_run: bool = False, hide_actions: bool = False)`, frozen; every flag is off unless the user passes it | decided |
| Building from flags | `from_parsed_args` fills every field from the flag of the same name; a field with no matching flag raises `AttributeError` | decided |
| Who builds it | `run_cli` builds it once from the parsed flags (see [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md)) and sets it as the active built-in params | decided |
| Who reads it | huginn only: the output reads `hide_actions` and `dry_run`, and the mutating runners in `manage_shell` read `dry_run`; a cmd function never receives it | decided |
| What goes in it | a setting the user passes as a built-in flag and huginn itself acts on; a flag only a cmd acts on is an argument of that cmd | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.

---

## Output for One Run

The entry point sets the built-in params once per process; the tool or script sets the log file path. The log file keeps a history of what each tool or script did.

| Feature | Detail | State |
|---|---|---|
| Wrapping | in a terminal, narration wraps at the terminal width; elsewhere, e.g. in a job, it is never wrapped, so each message stays one line; a result is never wrapped | decided |
| Hidden actions | with `hide_actions`, action messages are left off the terminal; set by the `--hide-actions` flag, off by default; a cmd skipped in dry-run still shows, since showing it is the point of a dry run | decided |
| Log | every message, hidden actions included, is also appended to the log file at the set path, as plain text without markup | decided |
| Setting the log file path | one call for tools and scripts alike, `manage_log.set_log_file_path(log_file_path=...)`, before the first message: a path logs there, and `None` logs nothing. `run_cli` never sets it. Logging before the path is set raises `LogFileError`, even in dry-run, so a forgotten call shows up on the first run | decided |
| Home log | `manage_log.get_home_log_file_path(tool_name=...)` gives `~/.huginn_logs/<tool name>.log`: one folder outside every repo, so git never sees it. An installed tool, e.g. `git_helpers`, sets it in its `main` before `run_cli` | decided |
| Log in a job | a job script passes its working folder to the script, e.g. a sim folder, and the script logs there, e.g. `<sim folder>/<name>.log`; parallel jobs then never share one file | decided |
| Log format | `[<time stamp>] <line>`, one line per entry; the time stamp is `YYYY-MM-DD HH:MM:SS`, from `datetime.now().isoformat(sep=" ", timespec="seconds")` | decided |
| Invoked cmd | each run starts with one line giving the invoked cmd, the command that started the process, from `sys.argv`, after a `$ `, e.g. `$ git_helpers sync --allow-dirty`, so runs can be told apart in one file; the `$ ` keeps it apart from a plain result line. It is written with the first message, so a dry run or a run that logs nothing leaves the file alone | decided |
| Log cannot be written | the run stops with an error naming the log file and exits with status 1; a run that cannot be recorded is not done quietly | decided |
| No action goes unlogged | a message is logged before it is shown, and an action is shown before it runs, so when the log fails, the action it belongs to never starts and is never shown as started | decided |
| Log in dry-run | nothing is written: the log is a history of what was done to the machine, and a dry-run does nothing | decided |
| Log growth | the file is only ever appended to; no rotation until a log grows large enough to need it | decided |
| Terminal time stamps | none; the log carries the times | decided |
| Tests | tests set the log file path to a temporary folder, or to `None`, so they never write to a real log | decided |
