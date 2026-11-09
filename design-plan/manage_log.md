# manage_log

Design notes for `huginn.manage_log`: the output functions, their message types, and how the output of one run is set up.

---

## Message Types

The model has seven concepts, each a group of the style legend, named in the singular: a task, a note, a prompt, an action, an outcome, an item, and a return. Two of them have kinds of their own. The style legend describes each one in the words of the legend itself, e.g. a note is "a remark about the current task".

```text
task                 a stage of the program is starting
note                 a remark about the current task
prompt               a request for user input, answered on the same line
action               a cmd run on the system, shown before it runs
├── run              a cmd that changes the system; skipped in a dry run
└── query            a cmd that only reads the system; the tool uses what it finds
outcome              how a task or action ended, reported afterwards
└── status           success | warning | skipped | failure | error
item                 a detail giving context to a note or outcome, as name = value under it
return               what the tool returns via stdout
```

A cmd in the style legend is always a shell cmd an action runs; what a cmd of the tool hands back is a return, of the tool.

Colour is never the only signal: every meaning reads from the symbol and the words alone, as it must in the log file, which has no colour; colour is an extra layer in the terminal. The symbol says which concept a line is (closed circle: task; open circle: note; question mark: prompt; right arrow: action; hooked arrow: outcome; middle dot: item; none: return). Where a concept has more than one kind, a label word and a colon after the symbol say which, padded to one width so the text lines up, e.g. `↪ success: backed up the notes file` and `↪ error:   no command given`: `run` or `query` for an action, the same verbs that start the names of the runners that make them (`run_cmd_...`, `query_cmd_...`), and `success`, `warning`, `skipped`, `failure`, or `error` for an outcome status; the colour repeats it. The vocabulary follows the jormi log manager: `MessageStyle` (`colour`, `symbol`, `description`, `label`), `Colour`, `Symbol`, notes, and an `ERROR` status beside `FAILURE`. Each base concept has its facets as enums of `MessageStyle` in the private `_message_styles`: `TASK_STYLE`; `NOTE_STYLE`; `PROMPT_STYLE`; `Action` (`RUN`, `QUERY`); `OutcomeStatus` (`SUCCESS`, `WARNING`, `SKIPPED`, `FAILURE`, `ERROR`); `ITEM_STYLE`; `RETURN_STYLE`. There are no named combinations: a run skipped in dry-run is drawn by a copy of the run style with the label and colour of the skipped status, `→ skipped: <cmd>`, and the style legend lists only the building blocks. Message text does not repeat its label, e.g. `↪ skipped: there is no notes file to back up`, not `↪ skipped: skipped the backup, ...`. `MESSAGE_GROUPS` lists everything by concept, and the style legend in the help is generated from it, so it cannot drift from the output. A style draws a message itself, with `MessageStyle.render`, and the private `_manage_output` sends it to each destination it belongs in with `route_msg`. A style always colours the whole message, symbol and text together. Every colour is mid-brightness, so a message reads on both light and dark terminal themes; there is no white.

| Concept | Facet | Value | Symbol | Label | Colour | State |
|---|---|---|---|---|---|---|
| task | | | closed circle | | purple | decided |
| note | | | open circle | | purple | decided |
| prompt | | a question for the user (see [Prompts](#prompts)) | question mark | | cyan | decided |
| action | type | run: changes the system | right arrow | `run` | blue | decided |
| action | type | query: only reads the system | right arrow | `query` | grey | decided |
| outcome | status | success | hooked arrow | `success` | green | decided |
| outcome | status | warning | hooked arrow | `warning` | yellow | decided |
| outcome | status | skipped | hooked arrow | `skipped` | orange | decided |
| outcome | status | failure that does not end the run | hooked arrow | `failure` | red | decided |
| outcome | status | error that ends the run | hooked arrow | `error` | red | decided |
| item | | a detail giving context to a note or outcome, one indent deeper | middle dot | | grey | decided |
| return | | what the tool returns via stdout | none | | none: plain text on stdout, never wrapped, so a pipe gets clean data | decided |

A query exists to produce a value; a run exists to change the system and may produce a value along the way, e.g. the path of a directory it created. In dry-run a run is skipped, so a value it would have produced is unknown, and an outcome after it may describe a change that was not made. huginn marks the whole dry run at both ends (see [Dry-run marked at both ends](#output-for-one-run)), and a tool that changes the system without a runner, e.g. by writing a file in Python, reads `manage_cli.get_built_in_params().dry_run` and skips the change itself. State: decided.

> **Note:** a richer message layer, with titled blocks and notes, is expected to move into this package later. These message types and statuses are its first layer, not a closed set.

---

## Output Functions

A tool chooses from one function per concept of the message model: task, note, outcome, return, error, and prompt; items go on a note or an outcome.

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_task(text, *, prepend_empty_line=False)` | a task starting, from one step to the heading of a whole run; with `prepend_empty_line=True`, an empty line comes first, so the task starts a new section. The author marks where a section starts, and huginn decides how a section looks; the empty line is for the terminal only, never the log file | narration | decided |
| `log_note(text, *, items=None)` | a remark about the current task, then its items, if any | narration | decided |
| `log_outcome(text, *, status, items=None)` | how a task or action ended, then its items, if any; `status` is required, never assumed | narration | decided |
| `log_return(text)` | what the tool returns, for the user or a pipe | stdout | decided |
| `exit_with_error(text, *, exit_code=1)` | an error outcome, then exits with `exit_code` | narration | decided |
| `report_failure(text, *, raise_error)` | for code that lets its caller choose: raises with `text`, or prints a failure outcome and carries on (see [`<terminal-interface>/design-plan/jormi_log.md`](jormi_log.md#library-code)) | narration | proposed |
| `ask(text, *, input_value_type)` | a question, then returns the answer (see [Prompts](#prompts)) | narration | decided |

`OutcomeStatus` is available as `manage_log.OutcomeStatus`.

`items` is a mapping of names to values, each printed on its own line under the message, one indent deeper, in the item style. A name is plain words, as a reader would say it, e.g. `latest backup`, not `latest_backup`, e.g.:

```text
↪ success: Save wavenumbers
    · path = <output path>
```

An item always belongs to a note or an outcome, so there is no function for an item on its own; the earlier `log_value` is gone, and a caller passes the item to the note or outcome it belongs to. State: decided.

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
| Stream | the question goes to stderr with the other narration, and the answer is typed on the same line, so stdout stays clean for returns; an answer piped in is not echoed by a terminal, so huginn prints it after the question, and the output reads the same either way | decided |
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
| Who reads it | huginn: the output reads `hide_actions` and `dry_run`, and the runs in `manage_shell` read `dry_run`. A cmd function is never passed it, but a tool can read it with `manage_cli.get_built_in_params()`, for a change huginn cannot skip itself, e.g. a file the tool writes in Python | decided |
| What goes in it | a setting the user passes as a built-in flag and huginn itself acts on; a flag only a cmd acts on is an argument of that cmd | decided |

This is the first generalisation: the existing layer carried a tool-specific flag in a type named `Config`, which also said nothing about what it configured.

---

## Output for One Run

The entry point sets the built-in params once per process; the tool or script sets the log file path. The log file keeps a history of what each tool or script did.

| Feature | Detail | State |
|---|---|---|
| Wrapping | in a terminal, narration wraps at the terminal width; elsewhere, e.g. in a job, it is never wrapped, so each message stays one line; a return is never wrapped | decided |
| Hidden actions | with `hide_actions`, action messages are left off the terminal; set by the `--hide-actions` flag, off by default; a cmd skipped in dry-run still shows, since showing it is the point of a dry run | decided |
| Log | every message, hidden actions included, is also appended to the log file at the set path, as plain text without markup | decided |
| Setting the log file path | one call for tools and scripts alike, `manage_log.set_log_file_path(log_file_path=...)`, before the first message: a path logs there, and `None` logs nothing. `run_cli` never sets it. Logging before the path is set raises `LogFileError`, even in dry-run, so a forgotten call shows up on the first run | decided |
| Home log | `manage_log.get_home_log_file_path(tool_name=...)` gives `~/.huginn_logs/<tool name>.log`: one folder outside every repo, so git never sees it. An installed tool, e.g. `git_helpers`, sets it in its `main` before `run_cli` | decided |
| Log in a job | a job script passes its working folder to the script, e.g. a sim folder, and the script logs there, e.g. `<sim folder>/<name>.log`; parallel jobs then never share one file | decided |
| Log format | `[<time stamp>] <line>`, one line per entry; the time stamp is `YYYY-MM-DD HH:MM:SS`, from `datetime.now().isoformat(sep=" ", timespec="seconds")` | decided |
| Invoked cmd | each run starts with one line giving the invoked cmd, the command that started the process, from `sys.argv`, after a `$ `, e.g. `$ git_helpers sync --allow-dirty`, so runs can be told apart in one file; the `$ ` keeps it apart from a plain return line. It is written with the first message, so a dry run or a run that logs nothing leaves the file alone | decided |
| Log cannot be written | the run stops with an error naming the log file and exits with status 1; a run that cannot be recorded is not done quietly | decided |
| No action goes unlogged | a message is logged before it is shown, and an action is shown before it runs, so when the log fails, the action it belongs to never starts and is never shown as started | decided |
| Log in dry-run | nothing is written: the log is a history of what was done to the machine, and a dry-run does nothing | decided |
| Dry-run marked at both ends | a tool should not have to phrase every outcome for a dry run, so huginn says it for every tool instead: `run_cli` starts a dry run with the note `○ dry run: changes are shown, not made` and ends it with `↪ skipped: dry run; nothing was changed` and the item `skipped actions`, the number of actions shown but not run. The outcomes of the cmd stay as the tool wrote them; huginn cannot tell which of them depended on a skipped change | decided |
| Log growth | the file is only ever appended to; no rotation until a log grows large enough to need it | decided |
| Terminal time stamps | none; the log carries the times | decided |
| Tests | tests set the log file path to a temporary folder, or to `None`, so they never write to a real log | decided |
