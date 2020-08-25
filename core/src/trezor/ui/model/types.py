class ButtonStyleState:
    bg_color = None  # type: int
    fg_color = None  # type: int
    text_style = None  # type: int
    border_color = None  # type: int
    radius = None  # type: int


if False:
    from typing import Optional, Type, Union

    ButtonStyleStateType = Type[ButtonStyleState]
    ButtonContent = Optional[Union[str, bytes]]


class ButtonStyle:
    normal = None  # type: ButtonStyleStateType
    active = None  # type: ButtonStyleStateType
    disabled = None  # type: ButtonStyleStateType


if False:
    ButtonStyleType = Type[ButtonStyle]
