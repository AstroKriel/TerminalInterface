## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NoReturn

## local
from huginn import (
    _manage_output,
    _message_styles,
    cmd_args,
)
from huginn._message_styles import OutcomeStatus as OutcomeStatus

##
## === LOG FILE
## every tool and script sets its log file path before its first message: a path, or `None` to log nothing.
##


def set_log_file_path(
    *,
    log_file_path: Path | None,
) -> None:
    _manage_output.set_log_file_path(log_file_path=log_file_path)


def get_home_log_file_path(
    *,
    tool_name: str,
) -> Path:
    return Path.home() / ".huginn_logs" / f"{tool_name}.log"


##
## === OUTPUT
## `text` is raw text: it always prints exactly as written, so a tool supplies the text and the kind of message,
## and huginn handles the styling.
##


def _render_and_route_msg(
    *,
    message_style: _message_styles.MessageStyle,
    text: str,
) -> None:
    msg_rendered = message_style.render(text=text)
    _manage_output.route_msg(msg_rendered)


def _render_and_route_items(
    items: Mapping[str, object],
    *,
    num_indent_spaces: int = 4,
) -> None:
    indent = " " * num_indent_spaces
    for item_name, item_value in items.items():
        msg_text = f"{item_name} = {item_value}"
        msg_rendered = _message_styles.ITEM_STYLE.render(text=msg_text)
        msg_indented = f"{indent}{msg_rendered}"
        _manage_output.route_msg(msg_indented)


def log_note(
    text: str,
    *,
    items: Mapping[str, object] | None = None,
) -> None:
    """Note something about the current task, then its items, one per line."""
    _render_and_route_msg(
        message_style=_message_styles.NOTE_STYLE,
        text=text,
    )
    if items is not None:
        _render_and_route_items(items)


def log_task(
    text: str,
    *,
    prepend_empty_line: bool = False,
) -> None:
    """Announce a task that is starting; `prepend_empty_line` puts an empty line before it, to start a new section."""
    msg_rendered = _message_styles.TASK_STYLE.render(text=text)
    _manage_output.route_msg(
        msg_rendered,
        prepend_empty_line=prepend_empty_line,
    )


def log_outcome(
    text: str,
    *,
    status: OutcomeStatus,
    items: Mapping[str, object] | None = None,
) -> None:
    """Report how a task or action ended, then its items, one per line; the status is required, never assumed."""
    _render_and_route_msg(
        message_style=status.value,
        text=text,
    )
    if items is not None:
        _render_and_route_items(items)


def log_return(
    text: str,
) -> None:
    """Hand back what the tool returns: plain text on stdout, with no symbol, colour, or wrapping."""
    msg_rendered = _message_styles.RETURN_STYLE.render(
        text=text,
    )
    _manage_output.route_msg(
        msg_rendered,
        is_return=True,
    )


def exit_with_error(
    text: str,
    *,
    exit_code: int = 1,
) -> NoReturn:
    """Report an error that ends the run, then exit the process with `exit_code`."""
    _render_and_route_msg(
        message_style=OutcomeStatus.ERROR.value,
        text=text,
    )
    sys.exit(exit_code)


##
## === PROMPTS
## a prompt asks the user a question and returns the answer, converted the same way as a cmd arg.
##


def ask(
    text: str,
    *,
    input_value_type: cmd_args.InputValueType,
) -> Any:
    """
    Ask the user a question and return the answer, converted by `input_value_type`.

    With `InputValueTypes.YES_OR_NO`, the question ends in `[y/N]`, and only an answer starting with `y` is yes. With
    any other type, an empty answer, or one that does not convert, reports a failure and asks again.
    """
    answer_is_yes_or_no = input_value_type is cmd_args.InputValueTypes.YES_OR_NO
    if answer_is_yes_or_no:
        question_text = f"{text} [y/N]"
    else:
        question_text = text
    question_rendered = _message_styles.PROMPT_STYLE.render(text=question_text)
    while True:
        answer = _manage_output.read_answer(question_rendered)
        if answer is None:
            exit_with_error(f"no answer to `{question_text}`: input ended.")
        answer_text = answer.strip()
        if answer_is_yes_or_no:
            return input_value_type.convert_fn(answer_text)
        elif answer_text == "":
            log_outcome("answer must not be empty.", status=OutcomeStatus.FAILURE)
        else:
            try:
                return input_value_type.convert_fn(answer_text)
            except (ValueError, argparse.ArgumentTypeError):
                log_outcome(
                    f"answer must be <{input_value_type.placeholder_name}>; got `{answer_text}`.",
                    status=OutcomeStatus.FAILURE,
                )


## } MODULE
