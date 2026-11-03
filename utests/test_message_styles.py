## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import dataclasses
import unittest

## local
from huginn import _message_styles

##
## === TEST SUITE
##


class TestLegend_Groups(unittest.TestCase):

    def test_groups_follow_the_concepts(
        self,
    ) -> None:
        self.assertEqual(
            [_message_group.title for _message_group in _message_styles.MESSAGE_GROUPS],
            ["Tasks", "Notes", "Actions", "Outcomes"],
        )

    def test_every_type_status_and_content_is_in_its_group(
        self,
    ) -> None:
        tasks_group, notes_group, actions_group, outcomes_group = _message_styles.MESSAGE_GROUPS
        self.assertEqual(tasks_group.message_styles, (_message_styles.TASK_STYLE, ))
        self.assertEqual(notes_group.message_styles, (_message_styles.NOTE_STYLE, ))
        for action in _message_styles.Action:
            self.assertIn(action.value, actions_group.message_styles)
        for outcome_status in _message_styles.OutcomeStatus:
            self.assertIn(outcome_status.value, outcomes_group.message_styles)
        for outcome_content in _message_styles.OutcomeContent:
            self.assertIn(outcome_content.value, outcomes_group.message_styles)

    def test_every_message_style_has_a_description(
        self,
    ) -> None:
        for message_group in _message_styles.MESSAGE_GROUPS:
            for message_style in message_group.message_styles:
                self.assertNotEqual(message_style.description, "")

    def test_result_has_no_symbol_or_colour(
        self,
    ) -> None:
        result_style = _message_styles.OutcomeContent.RESULT.value
        self.assertIsNone(result_style.symbol)
        self.assertIsNone(result_style.colour)

    def test_only_failure_and_error_share_a_colour(
        self,
    ) -> None:
        outcome_status = _message_styles.OutcomeStatus
        self.assertEqual(outcome_status.FAILURE.value.colour, outcome_status.ERROR.value.colour)
        other_colours = [
            _outcome_status.value.colour
            for _outcome_status in outcome_status
            if _outcome_status is not outcome_status.ERROR
        ]
        self.assertEqual(len(set(other_colours)), len(other_colours))


class TestMessageStyle_Render(unittest.TestCase):

    def test_colours_only_the_symbol(
        self,
    ) -> None:
        line_markup = _message_styles.TASK_STYLE.render(
            text_markup="task",
            colour_whole_line=False,
        )
        self.assertEqual(line_markup, "[#FFFFFF]○[/] task")

    def test_colours_the_whole_line(
        self,
    ) -> None:
        line_markup = _message_styles.OutcomeStatus.SUCCESS.value.render(
            text_markup="done",
            colour_whole_line=True,
        )
        self.assertEqual(line_markup, "[#32CD32]● done[/]")

    def test_renders_plain_without_symbol_or_colour(
        self,
    ) -> None:
        line_markup = _message_styles.OutcomeContent.RESULT.value.render(
            text_markup="plain",
            colour_whole_line=True,
        )
        self.assertEqual(line_markup, "plain")

    def test_copy_with_another_colour_keeps_the_symbol(
        self,
    ) -> None:
        skipped_change_style = dataclasses.replace(
            _message_styles.Action.CHANGE.value,
            colour=_message_styles.OutcomeStatus.SKIPPED.value.colour,
        )
        line_markup = skipped_change_style.render(
            text_markup="git push",
            colour_whole_line=True,
        )
        self.assertEqual(line_markup, "[#E48500]→ git push[/]")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
