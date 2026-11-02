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
from huginn import input_types

##
## === TEST SUITE
##


class TestInputType_PlaceholderName(unittest.TestCase):

    def test_letters_digits_underscores_and_hyphens_are_accepted(
        self,
    ) -> None:
        input_type = input_types.InputType(placeholder_name="base_ref-2")
        self.assertEqual(input_type.placeholder_name, "base_ref-2")

    def test_brackets_spaces_and_empty_names_are_rejected(
        self,
    ) -> None:
        for bad_placeholder_name in ["<dir>", "two words", ""]:
            with self.subTest(bad_placeholder_name=bad_placeholder_name), self.assertRaises(ValueError):
                input_types.InputType(placeholder_name=bad_placeholder_name)


class TestInputTypes_Convert(unittest.TestCase):

    def test_text_stays_text(
        self,
    ) -> None:
        self.assertEqual(input_types.TEXT.convert_fn("abc"), "abc")

    def test_number_becomes_an_int(
        self,
    ) -> None:
        self.assertEqual(input_types.NUMBER.convert_fn("3"), 3)

    def test_path_and_dir_become_paths(
        self,
    ) -> None:
        self.assertEqual(input_types.PATH.convert_fn("a/b"), Path("a/b"))
        self.assertEqual(input_types.DIR.convert_fn("."), Path("."))

    def test_date_becomes_a_date(
        self,
    ) -> None:
        self.assertEqual(input_types.DATE.convert_fn("2026-11-02"), datetime.date(2026, 11, 2))

    def test_bad_date_raises_an_argument_error(
        self,
    ) -> None:
        with self.assertRaises(argparse.ArgumentTypeError) as error_context:
            input_types.DATE.convert_fn("2026-13-01")
        self.assertEqual(str(error_context.exception), "date must be YYYY-MM-DD; got `2026-13-01`.")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
