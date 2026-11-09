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


class TestStyleLegend_Groups(unittest.TestCase):

    def test_groups_follow_the_concepts(
        self,
    ) -> None:
        self.assertEqual(
            [_message_group.title for _message_group in _message_styles.MESSAGE_GROUPS],
            ["Task", "Note", "Prompt", "Action", "Outcome", "Item", "Return"],
        )

    def test_every_type_status_and_content_is_in_its_group(
        self,
    ) -> None:
        (
            tasks_group,
            notes_group,
            prompts_group,
            actions_group,
            outcomes_group,
            items_group,
            returns_group,
        ) = _message_styles.MESSAGE_GROUPS
        self.assertEqual(tasks_group.message_styles, (_message_styles.TASK_STYLE, ))
        self.assertEqual(notes_group.message_styles, (_message_styles.NOTE_STYLE, ))
        self.assertEqual(prompts_group.message_styles, (_message_styles.PROMPT_STYLE, ))
        for action in _message_styles.Action:
            self.assertIn(action.value, actions_group.message_styles)
        for outcome_status in _message_styles.OutcomeStatus:
            self.assertIn(outcome_status.value, outcomes_group.message_styles)
        self.assertEqual(items_group.message_styles, (_message_styles.ITEM_STYLE, ))
        self.assertEqual(returns_group.message_styles, (_message_styles.RETURN_STYLE, ))

    def test_every_message_style_has_a_description(
        self,
    ) -> None:
        for message_group in _message_styles.MESSAGE_GROUPS:
            for message_style in message_group.message_styles:
                self.assertNotEqual(message_style.description, "")

    def test_return_has_no_symbol_or_colour(
        self,
    ) -> None:
        return_style = _message_styles.RETURN_STYLE
        self.assertIsNone(return_style.symbol)
        self.assertIsNone(return_style.colour)

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

    def test_colours_the_whole_msg(
        self,
    ) -> None:
        self.assertEqual(_message_styles.TASK_STYLE.render(text="task"), "[#A660D0]● task[/]")
        self.assertEqual(
            _message_styles.OutcomeStatus.SUCCESS.value.render(text="done"),
            "[#239023]↪ success: done[/]",
        )

    def test_renders_plain_without_symbol_or_colour(
        self,
    ) -> None:
        self.assertEqual(_message_styles.RETURN_STYLE.render(text="plain"), "plain")

    def test_copy_with_another_label_and_colour_keeps_the_symbol(
        self,
    ) -> None:
        skipped_style = _message_styles.OutcomeStatus.SKIPPED.value
        skipped_change_style = dataclasses.replace(
            _message_styles.Action.RUN.value,
            colour=skipped_style.colour,
            label=skipped_style.label,
        )
        self.assertEqual(skipped_change_style.render(text="git push"), "[#B86B00]→ skipped: git push[/]")

    def test_labels_pad_to_one_width(
        self,
    ) -> None:
        error_style = _message_styles.OutcomeStatus.ERROR.value
        success_style = _message_styles.OutcomeStatus.SUCCESS.value
        self.assertEqual(error_style.render(text="x").index("x"), success_style.render(text="x").index("x"))

    def test_label_longer_than_the_width_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            _message_styles.MessageStyle(
                colour=None,
                symbol=None,
                description="too long",
                label="much-too-long",
            )


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
