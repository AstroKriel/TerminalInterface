## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import datetime
import unittest
from pathlib import Path

## local
from huginn import cmd_args

##
## === HELPERS
##


def _parse_with(
    arg: cmd_args.Argument,
    argv: list[str],
) -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser()
    arg.add_to_arg_parser(arg_parser)
    return arg_parser.parse_args(argv)


##
## === TEST SUITE
##


class TestInputValueType_PlaceholderName(unittest.TestCase):

    def test_letters_digits_underscores_and_hyphens_are_accepted(
        self,
    ) -> None:
        input_value_type = cmd_args.InputValueType(
            placeholder_name="base_ref-2",
            convert_fn=str,
        )
        self.assertEqual(input_value_type.placeholder_name, "base_ref-2")

    def test_brackets_spaces_and_empty_names_are_rejected(
        self,
    ) -> None:
        for bad_placeholder_name in ["<dir>", "two words", ""]:
            with self.subTest(bad_placeholder_name=bad_placeholder_name), self.assertRaises(ValueError):
                cmd_args.InputValueType(
                    placeholder_name=bad_placeholder_name,
                    convert_fn=str,
                )


class TestInputValueTypes_Convert(unittest.TestCase):

    def test_text_stays_text(
        self,
    ) -> None:
        self.assertEqual(cmd_args.InputValueTypes.TEXT.convert_fn("abc"), "abc")

    def test_number_becomes_an_int(
        self,
    ) -> None:
        self.assertEqual(cmd_args.InputValueTypes.NUMBER.convert_fn("3"), 3)

    def test_path_and_dir_become_paths(
        self,
    ) -> None:
        self.assertEqual(cmd_args.InputValueTypes.PATH.convert_fn("a/b"), Path("a/b"))
        self.assertEqual(cmd_args.InputValueTypes.DIR.convert_fn("."), Path("."))

    def test_date_becomes_a_date(
        self,
    ) -> None:
        self.assertEqual(cmd_args.InputValueTypes.DATE.convert_fn("2026-11-02"), datetime.date(2026, 11, 2))

    def test_bad_date_raises_an_argument_error(
        self,
    ) -> None:
        with self.assertRaises(argparse.ArgumentTypeError) as error_context:
            cmd_args.InputValueTypes.DATE.convert_fn("2026-13-01")
        self.assertEqual(str(error_context.exception), "date must be YYYY-MM-DD; got `2026-13-01`.")


class TestAllowedNumInputValues_Properties(unittest.TestCase):

    def test_nargs_symbol_of_each_member(
        self,
    ) -> None:
        expected_nargs_symbols: dict[cmd_args.AllowedNumInputValues, str | None] = {
            cmd_args.AllowedNumInputValues.ONE: None,
            cmd_args.AllowedNumInputValues.ZERO_OR_ONE: "?",
            cmd_args.AllowedNumInputValues.ZERO_OR_MORE: "*",
            cmd_args.AllowedNumInputValues.ONE_OR_MORE: "+",
        }
        for allowed_num_input_values, expected_nargs_symbol in expected_nargs_symbols.items():
            with self.subTest(allowed_num_input_values=allowed_num_input_values):
                self.assertEqual(allowed_num_input_values.nargs_symbol, expected_nargs_symbol)

    def test_zero_is_allowed_only_for_the_ranges_from_zero(
        self,
    ) -> None:
        zero_allowed_members = {
            _allowed_num_input_values
            for _allowed_num_input_values in cmd_args.AllowedNumInputValues
            if _allowed_num_input_values.is_zero_allowed
        }
        self.assertEqual(
            zero_allowed_members,
            {
                cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
                cmd_args.AllowedNumInputValues.ZERO_OR_MORE,
            },
        )


class TestAllowedNumInputValues_Parsing(unittest.TestCase):

    def test_one_takes_a_single_input(
        self,
    ) -> None:
        path_arg = cmd_args.PositionalArgument(
            param_name="path",
            description="path to use",
            input_value_type=cmd_args.InputValueTypes.TEXT,
        )
        self.assertEqual(_parse_with(path_arg, ["a"]).path, "a")

    def test_ranges_collect_their_inputs(
        self,
    ) -> None:
        expected_inputs: dict[cmd_args.AllowedNumInputValues, tuple[list[str], list[str] | None]] = {
            cmd_args.AllowedNumInputValues.ZERO_OR_ONE: ([], None),
            cmd_args.AllowedNumInputValues.ZERO_OR_MORE: ([], []),
            cmd_args.AllowedNumInputValues.ONE_OR_MORE: (["a", "b"], ["a", "b"]),
        }
        for allowed_num_input_values, (argv, expected_paths) in expected_inputs.items():
            ranged_arg = cmd_args.PositionalArgument(
                param_name="paths",
                description="paths to use",
                input_value_type=cmd_args.InputValueTypes.TEXT,
                allowed_num_input_values=allowed_num_input_values,
            )
            with self.subTest(allowed_num_input_values=allowed_num_input_values):
                self.assertEqual(_parse_with(ranged_arg, argv).paths, expected_paths)


class TestFlagArgument_Switch(unittest.TestCase):

    def test_flag_is_true_when_passed_and_false_when_not(
        self,
    ) -> None:
        force_flag = cmd_args.FlagArgument(
            long_arg_name="force",
            description="skip the check",
        )
        self.assertTrue(_parse_with(force_flag, ["--force"]).force)
        self.assertFalse(_parse_with(force_flag, []).force)


class TestArgument_Checks(unittest.TestCase):

    def test_positional_name_must_be_a_param_name(
        self,
    ) -> None:
        for bad_name in ["--since", "since-date", "Since", "2nd", ""]:
            with self.subTest(bad_name=bad_name), self.assertRaises(ValueError) as error_context:
                cmd_args.PositionalArgument(
                    param_name=bad_name,
                    description="since date",
                    input_value_type=cmd_args.InputValueTypes.DATE,
                )
            self.assertEqual(
                str(error_context.exception),
                f"PositionalArgument: `param_name` must be lowercase letters, digits, and `_`, starting with a letter; got `{bad_name}`.",
            )

    def test_positional_default_needs_an_input_that_can_be_left_out(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as error_context:
            cmd_args.PositionalArgument(
                param_name="path",
                description="path to use",
                input_value_type=cmd_args.InputValueTypes.PATH,
                default_value=".",
            )
        self.assertEqual(
            str(error_context.exception),
            "PositionalArgument: `default_value` for `path` must be `None` when `allowed_num_input_values` is `ONE`, since an input value is always given; got `.`.",
        )
        optional_path_arg = cmd_args.PositionalArgument(
            param_name="path",
            description="path to use",
            input_value_type=cmd_args.InputValueTypes.PATH,
            allowed_num_input_values=cmd_args.AllowedNumInputValues.ZERO_OR_ONE,
            default_value=".",
        )
        self.assertEqual(_parse_with(optional_path_arg, []).path, Path("."))

    def test_yes_or_no_is_for_prompts_only(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as error_context:
            cmd_args.NamedArgument(
                long_arg_name="overwrite",
                description="replace what is there",
                input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
            )
        self.assertEqual(
            str(error_context.exception),
            "NamedArgument: `input_value_type` must not be `YES_OR_NO`, which is for prompts; a yes or no choice on the command line is a `FlagArgument`.",
        )
        with self.assertRaises(ValueError):
            cmd_args.PositionalArgument(
                param_name="overwrite",
                description="replace what is there",
                input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
            )

    def test_long_arg_name_must_be_bare_lowercase_words(
        self,
    ) -> None:
        for bad_long_arg_name in ["--output", "base_ref", "Output", "-o", ""]:
            with self.subTest(bad_long_arg_name=bad_long_arg_name), self.assertRaises(ValueError):
                cmd_args.NamedArgument(
                    long_arg_name=bad_long_arg_name,
                    description="folder to write to",
                    input_value_type=cmd_args.InputValueTypes.DIR,
                )
            with self.subTest(bad_long_arg_name=bad_long_arg_name), self.assertRaises(ValueError):
                cmd_args.FlagArgument(
                    long_arg_name=bad_long_arg_name,
                    description="skip the check",
                )

    def test_short_arg_name_must_be_one_to_three_letters(
        self,
    ) -> None:
        for good_short_arg_name in ["o", "ou", "out"]:
            output_arg = cmd_args.NamedArgument(
                long_arg_name="output",
                short_arg_name=good_short_arg_name,
                description="folder to write to",
                input_value_type=cmd_args.InputValueTypes.DIR,
            )
            self.assertEqual(output_arg.arg_names, [f"-{good_short_arg_name}", "--output"])
        for bad_short_arg_name in ["-o", "outp", "o1", ""]:
            with self.subTest(
                    bad_short_arg_name=bad_short_arg_name, ), self.assertRaises(ValueError) as error_context:
                cmd_args.FlagArgument(
                    long_arg_name="force",
                    short_arg_name=bad_short_arg_name,
                    description="skip the check",
                )
            self.assertEqual(
                str(error_context.exception),
                f"FlagArgument: `short_arg_name` for `force` must be one to three letters; got `{bad_short_arg_name}`.",
            )

    def test_required_named_arg_has_no_default(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as error_context:
            cmd_args.NamedArgument(
                long_arg_name="output",
                description="folder to write to",
                input_value_type=cmd_args.InputValueTypes.DIR,
                is_required=True,
                default_value=".",
            )
        self.assertEqual(
            str(error_context.exception),
            "NamedArgument: `default_value` for `output` must be `None` when `is_required` is `True`, since a required argument never falls back; got `.`.",
        )


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
