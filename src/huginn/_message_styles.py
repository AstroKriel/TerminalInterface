## { MODULE

##
## === DEPENDENCIES
##

## stdlib
from dataclasses import dataclass
from enum import Enum, StrEnum

##
## === PALETTE
##


class Colour(StrEnum):
    WHITE = "#FFFFFF"
    GREEN = "#32CD32"
    YELLOW = "#FFE600"
    BLUE = "#2A71F6"
    ORANGE = "#E48500"
    RED = "#FF4500"
    GREY = "#818181"
    CYAN = "#00CED1"


class Symbol(StrEnum):
    OPEN_CIRCLE = "○"
    CLOSED_CIRCLE = "●"
    RIGHT_ARROW = "→"
    HOOKED_ARROW = "↪"
    MIDDLE_DOT = "·"


@dataclass(frozen=True)
class MessageStyle:
    """Colour, symbol, and legend description for one kind of line; a line with neither prints as plain text."""
    colour: Colour | None
    symbol: Symbol | None
    description: str

    def render(
        self,
        *,
        text_markup: str,
        colour_whole_line: bool,
    ) -> str:
        """
        Return the markup for a line in this style; either the whole line or only the symbol is coloured.

        A line that takes its symbol and colour from different styles, e.g. a change skipped in dry-run, is drawn by
        a copy of one style with the colour of the other. Without a symbol or colour the text renders plain.
        """
        symbol_text = ""
        if self.symbol is not None:
            symbol_text = f"{self.symbol} "
        if self.colour is None:
            return f"{symbol_text}{text_markup}"
        if colour_whole_line:
            return f"[{self.colour}]{symbol_text}{text_markup}[/]"
        return f"[{self.colour}]{symbol_text.strip()}[/] {text_markup}"


##
## === TASKS
## a task is a stage of the work, announced in words before it starts.
##

TASK_STYLE = MessageStyle(
    colour=Colour.WHITE,
    symbol=Symbol.OPEN_CIRCLE,
    description="start of a task",
)

##
## === NOTES
## a note is narration that is neither a task nor an outcome.
##

NOTE_STYLE = MessageStyle(
    colour=Colour.WHITE,
    symbol=Symbol.HOOKED_ARROW,
    description="note about the work",
)

##
## === ACTIONS
## an action is something done to the system, shown before it happens.
##


class Action(Enum):
    """A change is skipped in dry-run; an inspection always runs."""
    CHANGE = MessageStyle(
        colour=Colour.BLUE,
        symbol=Symbol.RIGHT_ARROW,
        description="change to the system",
    )
    INSPECTION = MessageStyle(
        colour=Colour.GREY,
        symbol=Symbol.RIGHT_ARROW,
        description="inspection of the system",
    )


##
## === OUTCOMES
## an outcome is how a task or action ended, reported afterwards: a status, and optionally some content.
##


class OutcomeStatus(Enum):
    SUCCESS = MessageStyle(
        colour=Colour.GREEN,
        symbol=Symbol.CLOSED_CIRCLE,
        description="success",
    )
    WARNING = MessageStyle(
        colour=Colour.YELLOW,
        symbol=Symbol.CLOSED_CIRCLE,
        description="warning",
    )
    SKIPPED = MessageStyle(
        colour=Colour.ORANGE,
        symbol=Symbol.CLOSED_CIRCLE,
        description="skipped",
    )
    FAILURE = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.CLOSED_CIRCLE,
        description="failure that does not end the run",
    )
    ERROR = MessageStyle(
        colour=Colour.RED,
        symbol=Symbol.CLOSED_CIRCLE,
        description="error that ends the run",
    )


class OutcomeContent(Enum):
    """What an outcome carries: a value for the narration, or a result for the user or a pipe."""
    VALUE = MessageStyle(
        colour=Colour.GREY,
        symbol=Symbol.MIDDLE_DOT,
        description="value that an action produced",
    )
    RESULT = MessageStyle(
        colour=None,
        symbol=None,
        description="result, printed plain on stdout",
    )


##
## === MESSAGE GROUPS
##


@dataclass(frozen=True)
class MessageGroup:
    """One concept with every kind of line it covers; the help legend is built from these."""
    title: str
    message_styles: tuple[MessageStyle, ...]


MESSAGE_GROUPS: list[MessageGroup] = [
    MessageGroup(
        title="Tasks",
        message_styles=(TASK_STYLE, ),
    ),
    MessageGroup(
        title="Notes",
        message_styles=(NOTE_STYLE, ),
    ),
    MessageGroup(
        title="Actions",
        message_styles=tuple(_action.value for _action in Action),
    ),
    MessageGroup(
        title="Outcomes",
        message_styles=(
            *[_outcome_status.value for _outcome_status in OutcomeStatus],
            *[_outcome_content.value for _outcome_content in OutcomeContent],
        ),
    ),
]

## } MODULE
