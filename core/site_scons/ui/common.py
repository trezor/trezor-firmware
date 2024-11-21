from __future__ import annotations


def add_font(
    font_name: str,
    font: str | None,
    defines: list[str | tuple[str, str]],
    sources: list[str],
) -> None:
    if font is not None:
        font_filename = font.replace("_upper", "").lower()
        defines += [
            (f"TREZOR_FONT_{font_name}_ENABLE", font),
            (f"TREZOR_FONT_{font_name}_INCLUDE", f'"{font_filename}.h"'),
        ]
        sourcefile = "embed/gfx/fonts/" + font_filename + ".c"
        if sourcefile not in sources:
            sources.append(sourcefile)
