## { MODULE

##
## === DEPENDENCIES
##

## stdlib
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import ClassVar

## third-party
from rich import markup as rich_markup

##
## === PALETTE
##


class Colour(StrEnum):
    """Mid-brightness colours, so every message reads on both light and dark terminal themes."""
    PURPLE = "#A660D0"
    GREEN = "#239023"
    YELLOW = "#8C7E00"
    BLUE = "#2A71F6"
    ORANGE = "#B86B00"
    RED = "#FF4500"
    GREY = "#818181"
    CYAN = "#008D8F"


class Symbol(StrEnum):
    OPEN_CIRCLE = "○"
    CLOSED_CIRCLE = "●"
    RIGHT_ARROW = "→"
    HOOKED_ARROW = "↪"
    MIDDLE_DOT = "·"
    QUESTION_MARK = "?"


@dataclass(frozen=True)
class MessageStyle:
    """
    Colour, symbol, label, and style legend description for one kind of message.

    Colour is never the only signal: the symbol says which concept a message is, and where a concept has more than
    one kind, e.g. an outcome that is a success or a failure, the label says which, so the meaning survives in the
    log file, which has no colour. A message with no symbol and no colour prints as plain text.
    """
    num_label_chars: ClassVar[int] = 7
    colour: Colour | None
    symbol: Symbol | None
    description: str
    label: str | None = None

    def __post_init__(
        self,
    ) -> None:
        label_is_too_long = (self.label is not None) and (len(self.label) > self.num_label_chars)
        if label_is_too_long:
            raise ValueError(
                f"{type(self).__name__}: `label` must be at most {self.num_label_chars} characters, so every label lines up; got `{self.label}`.",
            )

    def render(
        self,
        *,
        text: str,
    ) -> str:
        """
        Return the message drawn in this style, as markup: the symbol, then the label and a colon, padded to one width
        so the text lines up, then the text, the whole message in the colour.

        `text` is raw text and always prints exactly as written, even where it looks like markup, so a tool never
        has to think about styling. A message that takes parts from two styles, e.g. a change skipped in dry-run, is
        drawn by a copy of one style with the label and colour of the other.
        """
        msg_parts: list[str] = []
        if self.symbol is not None:
            msg_parts.append(self.symbol)
        if self.label is not None:
            label_with_colon = f"{self.label}:"
            label_padded = label_with_colon.ljust(self.num_label_chars + 1)
            msg_parts.append(label_padded)
        text_markup = rich_markup.escape(text)
        msg_parts.append(text_markup)
        msg_markup = " ".join(msg_parts)
        if self.colour is None:
            return msg_markup
        else:
            return f"[{self.colour}]{msg_markup}[/]"


##
## === TASKS
## a task is a stage of the work, announced in words before it starts.
##

TASK_STYLE = MessageStyle(
    colour=Colour.PURPLE,
    symbol=Symbol.CLOSED_CIRCLE,
    description="a stage of the program is starting",
)

##
## === NOTES
## a note is narration that is neither a task nor an outcome.
##

NOTE_STYLE = MessageStyle(
    colour=Colour.PURPLE,
    symbol=Symbol.OPEN_CIRCLE,
    description="a remark about the current task",
)

##
## === PROMPTS
## a prompt is a question for the user; the answer is typed on the same line.
##

PROMPT_STYLE = MessageStyle(
    colour=Colour.CYAN,
    symbol=Symbol.QUESTION_MARK,
    description="a request for user input",
)

##
## === ACTIONS
## an action is a cmd huginn runs on the system, shown before it runs: a run changes the system, a query only reads it.
##


class Action(Enum):
    """A run is skipped in dry-run; a query always runs, since it changes nothing."""
    RUN = MessageStyle(
        colour=Colour.BLUE,
        symbol=Symbol.RIGHT_ARROW,
        description="a cmd that changes the system; skipped in a dry run",
        label="run",
    )
    QUERY = MessageStyle(
        colour=Colour.GREY,
        symbol=Symbol.RIGHT_ARROW,
        description="a cmd that only reads the system; the tool uses what it finds",
        label="query",
    )


##
## === OUTCOMES
## an outcome is how a task or action ended, reported afterwards, with a status.
##


class OutcomeStatus(Enum):
    SUCCESS = MessageStyle(
        colour=Colour.GREEN,
        symbol=Symbol.HOOKED_ARROW,
        description="a task or action completed successfully",
        label="success",
    )
    WARNING = MessageStyle(
        colour=Colour.YELLOW,
        symbol=Symbol.HOOKED_ARROW,
        description="a task or action completed, but something needs attention",
        label="warning",
    )
    SKIPPED = MessageStyle(
        colour=Colour.ORANGE,
        symbol=Symbol.HOOKED_ARROW,
        description="a task or action was not run; either declined or nothing to do",
        label="skipped",
    )
    FAILURE = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.HOOKED_ARROW,
        description="a task or action failed, but the program continues",
        label="failure",
    )
    ERROR = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.HOOKED_ARROW,
        description="a task or action failed, and the program stops",
        label="error",
    )


##
## === ITEMS
## an item is a name and its value, on its own line under the note or outcome it belongs to.
##

ITEM_STYLE = MessageStyle(
    colour=Colour.GREY,
    symbol=Symbol.MIDDLE_DOT,
    description="a detail giving context to a note or outcome",
)

##
## === RETURNS
## a return is what the tool hands back; it goes to stdout, unstyled, so a pipe gets clean text.
##

RETURN_STYLE = MessageStyle(
    colour=None,
    symbol=None,
    description="what the tool returns via stdout",
)

##
## === MESSAGE GROUPS
##


@dataclass(frozen=True)
class MessageGroup:
    """One concept with every kind of message it covers; the style legend is built from these."""
    title: str
    message_styles: tuple[MessageStyle, ...]


MESSAGE_GROUPS: list[MessageGroup] = [
    MessageGroup(
        title="Task",
        message_styles=(TASK_STYLE, ),
    ),
    MessageGroup(
        title="Note",
        message_styles=(NOTE_STYLE, ),
    ),
    MessageGroup(
        title="Prompt",
        message_styles=(PROMPT_STYLE, ),
    ),
    MessageGroup(
        title="Action",
        message_styles=tuple(_action.value for _action in Action),
    ),
    MessageGroup(
        title="Outcome",
        message_styles=tuple(_outcome_status.value for _outcome_status in OutcomeStatus),
    ),
    MessageGroup(
        title="Item",
        message_styles=(ITEM_STYLE, ),
    ),
    MessageGroup(
        title="Return",
        message_styles=(RETURN_STYLE, ),
    ),
]

## } MODULE
