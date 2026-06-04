"""
Console formatting utilities for professional output without external dependencies.
Uses only standard Python libraries for clean, readable console output.
"""

import time
from datetime import datetime
from typing import Any, Dict, List


class ConsoleFormatter:
    """Professional console formatting using only standard Python features."""

    # ANSI Color Codes
    class Colors:
        RESET = "\033[0m"
        BOLD = "\033[1m"
        DIM = "\033[2m"

        # Text Colors
        BLACK = "\033[30m"
        RED = "\033[31m"
        GREEN = "\033[32m"
        YELLOW = "\033[33m"
        BLUE = "\033[34m"
        MAGENTA = "\033[35m"
        CYAN = "\033[36m"
        WHITE = "\033[37m"

        # Bright Colors
        BRIGHT_RED = "\033[91m"
        BRIGHT_GREEN = "\033[92m"
        BRIGHT_YELLOW = "\033[93m"
        BRIGHT_BLUE = "\033[94m"
        BRIGHT_MAGENTA = "\033[95m"
        BRIGHT_CYAN = "\033[96m"

        # Background Colors
        BG_RED = "\033[41m"
        BG_GREEN = "\033[42m"
        BG_YELLOW = "\033[43m"
        BG_BLUE = "\033[44m"

    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors
        self.start_time = time.time()

    def _color(self, text: str, color: str) -> str:
        """Apply color if enabled, otherwise return plain text."""
        if self.use_colors:
            return f"{color}{text}{self.Colors.RESET}"
        return text

    def header(self, title: str, subtitle: str = None, width: int = 80) -> None:
        """Print a professional header section."""
        print("\n" + "=" * width)
        centered_title = title.center(width)
        print(self._color(centered_title, self.Colors.BOLD + self.Colors.BRIGHT_BLUE))

        if subtitle:
            centered_subtitle = subtitle.center(width)
            print(self._color(centered_subtitle, self.Colors.DIM))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        centered_time = timestamp.center(width)
        print(self._color(centered_time, self.Colors.DIM))
        print("=" * width + "\n")

    def section(self, title: str, width: int = 80) -> None:
        """Print a section separator."""
        print(f"\n{'-' * width}")
        section_text = f"  {title.upper()}  "
        print(self._color(section_text, self.Colors.BOLD + self.Colors.BRIGHT_CYAN))
        print("-" * width)

    def subsection(self, title: str) -> None:
        """Print a subsection title."""
        print(f"\n┌── {self._color(title, self.Colors.BOLD + self.Colors.YELLOW)}")

    def info(self, message: str, indent: int = 0) -> None:
        """Print an info message."""
        prefix = "│   " if indent > 0 else "• "
        print(f"{' ' * (indent * 2)}{prefix}{message}")

    def success(self, message: str, indent: int = 0) -> None:
        """Print a success message."""
        prefix = "│   " if indent > 0 else "✓ "
        colored_msg = self._color(message, self.Colors.BRIGHT_GREEN)
        print(f"{' ' * (indent * 2)}{prefix}{colored_msg}")

    def warning(self, message: str, indent: int = 0) -> None:
        """Print a warning message."""
        prefix = "│   " if indent > 0 else "⚠ "
        colored_msg = self._color(message, self.Colors.BRIGHT_YELLOW)
        print(f"{' ' * (indent * 2)}{prefix}{colored_msg}")

    def error(self, message: str, indent: int = 0) -> None:
        """Print an error message."""
        prefix = "│   " if indent > 0 else "✗ "
        colored_msg = self._color(message, self.Colors.BRIGHT_RED)
        print(f"{' ' * (indent * 2)}{prefix}{colored_msg}")

    def progress(self, message: str, step: int = None, total: int = None) -> None:
        """Print a progress message."""
        if step is not None and total is not None:
            percentage = (step / total) * 100
            progress_bar = self._create_progress_bar(percentage)
            print(f"│   [{progress_bar}] {percentage:5.1f}% - {message}")
        else:
            print(f"│    {message}")

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a text-based progress bar."""
        filled = int(width * percentage / 100)
        bar = "█" * filled + "░" * (width - filled)
        return bar

    def table(
        self, headers: List[str], rows: List[List[str]], title: str = None
    ) -> None:
        """Print a formatted table."""
        if title:
            self.subsection(title)

        # Calculate column widths
        col_widths = [len(header) for header in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        # Print table
        def print_row(row_data, is_header=False):
            row_str = (
                "│ "
                + " │ ".join(
                    str(cell).ljust(col_widths[i]) for i, cell in enumerate(row_data)
                )
                + " │"
            )
            if is_header:
                print(self._color(row_str, self.Colors.BOLD))
            else:
                print(row_str)

        # Top border
        border = "┌─" + "─┬─".join("─" * width for width in col_widths) + "─┐"
        print(border)

        # Header
        print_row(headers, is_header=True)

        # Header separator
        separator = "├─" + "─┼─".join("─" * width for width in col_widths) + "─┤"
        print(separator)

        # Data rows
        for row in rows:
            print_row(row)

        # Bottom border
        bottom = "└─" + "─┴─".join("─" * width for width in col_widths) + "─┘"
        print(bottom)

    def key_value_pairs(
        self, data: Dict[str, Any], title: str = None, indent: int = 0
    ) -> None:
        """Print key-value pairs in a formatted way."""
        if title:
            self.subsection(title)

        max_key_length = max(len(str(key)) for key in data.keys()) if data else 0

        for key, value in data.items():
            key_str = f"{str(key):>{max_key_length}}"
            colored_key = self._color(key_str, self.Colors.BRIGHT_CYAN)
            print(f"{' ' * (indent * 2)}│   {colored_key}: {value}")

    def elapsed_time(self) -> str:
        """Get elapsed time since formatter initialization."""
        elapsed = time.time() - self.start_time
        if elapsed < 60:
            return f"{elapsed:.2f}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            return f"{minutes}m {seconds:.1f}s"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}h {minutes}m"

    def footer(self, width: int = 80) -> None:
        """Print a footer with completion info."""
        print("\n" + "=" * width)
        completion_msg = f"PROCESSING COMPLETED - Total time: {self.elapsed_time()}"
        centered_msg = completion_msg.center(width)
        print(self._color(centered_msg, self.Colors.BOLD + self.Colors.BRIGHT_GREEN))
        print("=" * width + "\n")


# Convenience functions for quick use
console = ConsoleFormatter()


def header(title: str, subtitle: str = None, width: int = 80):
    console.header(title, subtitle, width)


def section(title: str, width: int = 80):
    console.section(title, width)


def subsection(title: str):
    console.subsection(title)


def info(message: str, indent: int = 0):
    console.info(message, indent)


def success(message: str, indent: int = 0):
    console.success(message, indent)


def warning(message: str, indent: int = 0):
    console.warning(message, indent)


def error(message: str, indent: int = 0):
    console.error(message, indent)


def progress(message: str, step: int = None, total: int = None):
    console.progress(message, step, total)


def table(headers: List[str], rows: List[List[str]], title: str = None):
    console.table(headers, rows, title)


def key_value_pairs(data: Dict[str, Any], title: str = None, indent: int = 0):
    console.key_value_pairs(data, title, indent)


def footer(width: int = 80):
    console.footer(width)
