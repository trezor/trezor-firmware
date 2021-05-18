"""
The components/common module contains code that is used by both components/tt
and components/t1.
"""


def break_path_to_lines(path_str: str, per_line: int) -> list[str]:
    lines = []
    while len(path_str) > per_line:
        i = path_str[:per_line].rfind("/")
        lines.append(path_str[:i])
        path_str = path_str[i:]
    lines.append(path_str)

    return lines
