"""
Central place for defining all input flows for the device tests.

Each model has potentially its own input flow, and in most cases
we need to distinguish between them. Doing it at one place
offers a better overview of the differences and makes it easier
to maintain. The whole `device_tests` folder can then focus
only on the actual tests and data-assertions, not on the lower-level
input flow details.
"""

from __future__ import annotations

import time
from typing import Callable, Generator, Sequence

import pytest

from trezorlib import messages
from trezorlib.client import Session
from trezorlib.debuglink import DebugLink, DebugSession, LayoutContent, LayoutType
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.debuglink import multipage_content
from trezorlib.exceptions import TrezorFailure

from trezorlib.testing import translations as TR
from trezorlib.testing.common import BRGeneratorType

B = messages.ButtonRequestType

FlowAdapter = Callable[[Session, Callable[[], BRGeneratorType]], BRGeneratorType]


class InputFlowBase:
    def __init__(self, client: Client | DebugSession):
        if isinstance(client, Session):
            client = client.test_ctx
        self.client = client
        self.debug: DebugLink = client.debug
        self.layout_type = client.layout_type

    def get(self) -> Callable[[], BRGeneratorType]:
        self.client.watch_layout(True)

        # There is currently just one input flow for all models
        assert hasattr(self, "input_flow")
        return getattr(self, "input_flow")

    def text_content(self) -> str:
        return self.debug.read_layout().text_content()

    def main_component(self) -> str:
        return self.debug.read_layout().main_component()

    def all_components(self) -> list[str]:
        return self.debug.read_layout().all_components()

    def title(self) -> str:
        return self.debug.read_layout().title()


class InputFlowGetPublicKeyCancel(InputFlowBase):
    def input_flow(self) -> BRGeneratorType:
        br = yield
        assert br.name == "show_pubkey"

        # go to the menu
        self.debug.click(self.debug.screen_buttons.menu())
        self.debug.synchronize_at("VerticalMenu")
        # click the cancel button the 3rd one
        self.debug.button_actions.navigate_to_menu_item(2)
        # confirm cancel
        self.debug.click(self.debug.screen_buttons.ok())
