import mock
from common import *

from trezor import ui
from trezor.ui import display
from trezor.ui.components.common import text

if False:
    from typing import List, Tuple


class TestTextSpan(unittest.TestCase):
    def lines(self, span: text.Span) -> List[Tuple[str, int, bool]]:
        result = []
        while True:
            should_continue = span.next_line()
            substr = span.string[span.start : span.start + span.length]
            result.append((substr, span.width, span.word_break))
            if not should_continue:
                break
        return result

    def checkSpanWithoutWidths(
        self, span: text.Span, expected: List[Tuple[str, bool]]
    ) -> None:
        expected_with_calculated_widths = [
            (string, ui.display.text_width(string, span.font), word_break)
            for string, word_break in expected
        ]
        self.assertListEqual(self.lines(span), expected_with_calculated_widths)

    def test_basic(self):
        span = text.Span("hello")
        self.checkSpanWithoutWidths(
            span,
            [("hello", False)],
        )

        span.reset("world", start=0, font=ui.NORMAL)
        self.checkSpanWithoutWidths(
            span,
            [("world", False)],
        )

        span.reset("", start=0, font=ui.NORMAL)
        self.checkSpanWithoutWidths(
            span,
            [("", False)],
        )

    def test_two_lines(self):
        line_width = display.text_width("hello world", ui.NORMAL) - 1
        span = text.Span("hello world", line_width=line_width)
        self.checkSpanWithoutWidths(
            span,
            [
                ("hello", False),
                ("world", False),
            ],
        )

    def test_newlines(self):
        span = text.Span("hello\nworld")
        self.checkSpanWithoutWidths(
            span,
            [
                ("hello", False),
                ("world", False),
            ],
        )

        span = text.Span("\nhello\nworld\n")
        self.checkSpanWithoutWidths(
            span,
            [
                ("", False),
                ("hello", False),
                ("world", False),
                ("", False),
            ],
        )

    def test_break_words(self):
        line_width = display.text_width("hello w", ui.NORMAL) + text.DASH_WIDTH
        span = text.Span("hello world", line_width=line_width, break_words=True)
        self.checkSpanWithoutWidths(
            span,
            [
                ("hello w", True),
                ("orld", False),
            ],
        )

    def test_long_word(self):
        line_width = display.text_width("establishme", ui.NORMAL) + text.DASH_WIDTH
        span = text.Span(
            "Down with the establishment!", line_width=line_width, break_words=False
        )
        self.checkSpanWithoutWidths(
            span,
            [
                ("Down with", False),
                ("the", False),
                ("establishme", True),
                ("nt!", False),
            ],
        )

    def test_has_more_content(self):
        line_width = display.text_width("hello world", ui.NORMAL) - 1
        span = text.Span("hello world", line_width=line_width)
        self.assertTrue(span.has_more_content())
        self.assertTrue(span.next_line())
        self.assertEqual("hello", span.string[span.start : span.start + span.length])

        # has_more_content is True because there's text remaining on the line
        self.assertTrue(span.has_more_content())
        # next_line is False because we should not continue iterating
        self.assertFalse(span.next_line())
        self.assertEqual("world", span.string[span.start : span.start + span.length])

        self.assertFalse(span.has_more_content())
        self.assertFalse(span.next_line())
        self.assertEqual("world", span.string[span.start : span.start + span.length])


    def test_has_more_content_trailing_newline(self):
        span = text.Span("1\n2\n3\n")

        self.assertTrue(span.has_more_content())
        self.assertTrue(span.next_line())
        self.assertEqual("1", span.string[span.start : span.start + span.length])

        self.assertTrue(span.has_more_content())
        self.assertTrue(span.next_line())
        self.assertEqual("2", span.string[span.start : span.start + span.length])

        self.assertTrue(span.has_more_content())
        self.assertTrue(span.next_line())
        self.assertEqual("3", span.string[span.start : span.start + span.length])

        # has_more_content is False because the "remaining" text is empty
        self.assertFalse(span.has_more_content())
        # next_line is False because we should not continue iterating
        self.assertFalse(span.next_line())
        self.assertEqual("", span.string[span.start : span.start + span.length])


if __name__ == "__main__":
    unittest.main()
