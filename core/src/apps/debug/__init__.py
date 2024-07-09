if not __debug__:
    from trezor.utils import halt

    halt("debug mode inactive")

if __debug__:
    from typing import TYPE_CHECKING

    import trezorui2
    from storage import debug as storage
    from storage.debug import debug_events
    from trezor import log, loop, utils, wire
    from trezor.enums import MessageType
    from trezor.messages import DebugLinkLayout, Success
    from trezor.ui import display
    from trezor.wire import context

    from apps import workflow_handlers

    if TYPE_CHECKING:
        from trezor.messages import (
            DebugLinkDecision,
            DebugLinkEraseSdCard,
            DebugLinkGetState,
            DebugLinkOptigaSetSecMax,
            DebugLinkRecordScreen,
            DebugLinkReseedRandom,
            DebugLinkResetDebugEvents,
            DebugLinkState,
            DebugLinkWatchLayout,
        )
        from trezor.ui import Layout

    swipe_chan = loop.chan()
    result_chan = loop.chan()
    button_chan = loop.chan()
    click_chan = loop.chan()
    swipe_signal = swipe_chan.take
    result_signal = result_chan.take
    button_signal = button_chan.take
    click_signal = click_chan.take

    debuglink_decision_chan = loop.chan()

    layout_change_chan = loop.chan()

    DEBUG_CONTEXT: context.Context | None = None

    LAYOUT_WATCHER_NONE = 0
    LAYOUT_WATCHER_STATE = 1
    LAYOUT_WATCHER_LAYOUT = 2

    REFRESH_INDEX = 0

    def screenshot() -> bool:
        if storage.save_screen:
            # Starting with "refresh00", allowing for 100 emulator restarts
            # without losing the order of the screenshots based on filename.
            display.save(
                storage.save_screen_directory + f"/refresh{REFRESH_INDEX:0>2}-"
            )
            return True
        return False

    def notify_layout_change(layout: Layout, event_id: int | None = None) -> None:
        layout.read_content_into(storage.current_content_tokens)
        if storage.watch_layout_changes or layout_change_chan.takers:
            payload = (event_id, storage.current_content_tokens)
            layout_change_chan.publish(payload)

    async def _dispatch_debuglink_decision(
        event_id: int | None, msg: DebugLinkDecision
    ) -> None:
        from trezor.enums import DebugButton

        if msg.button is not None:
            if msg.button == DebugButton.NO:
                await result_chan.put((event_id, trezorui2.CANCELLED))
            elif msg.button == DebugButton.YES:
                await result_chan.put((event_id, trezorui2.CONFIRMED))
            elif msg.button == DebugButton.INFO:
                await result_chan.put((event_id, trezorui2.INFO))
            else:
                raise RuntimeError(f"Invalid msg.button - {msg.button}")
        elif msg.input is not None:
            await result_chan.put((event_id, msg.input))
        elif msg.swipe is not None:
            await swipe_chan.put((event_id, msg.swipe))
        else:
            # Sanity check. The message will be visible in terminal.
            raise RuntimeError("Invalid DebugLinkDecision message")

    async def debuglink_decision_dispatcher() -> None:
        while True:
            event_id, msg = await debuglink_decision_chan.take()
            await _dispatch_debuglink_decision(event_id, msg)

    async def get_layout_change_content() -> list[str]:
        awaited_event_id = debug_events.awaited_event
        last_result_id = debug_events.last_result

        if awaited_event_id is not None and awaited_event_id == last_result_id:
            # We are awaiting the event that just happened - return current state
            return storage.current_content_tokens

        while True:
            event_id, content = await layout_change_chan.take()
            if awaited_event_id is None or event_id is None:
                # Not waiting for anything or event does not have ID
                break
            elif event_id == awaited_event_id:
                # We found what we were waiting for
                debug_events.awaited_event = None
                break
            elif event_id > awaited_event_id:
                # Sanity check
                pass
                # TODO: find out why this sometimes happens on TR when running tests with
                # "physical" emulator (./emu.py)
                # raise RuntimeError(
                #     f"Waiting for event that already happened - {event_id} > {awaited_event_id}"
                # )

        if awaited_event_id is not None:
            # Updating last result
            debug_events.last_result = awaited_event_id

        return content

    async def return_layout_change() -> None:
        content_tokens = await get_layout_change_content()

        assert isinstance(DEBUG_CONTEXT, context.Context)
        if storage.layout_watcher is LAYOUT_WATCHER_LAYOUT:
            await DEBUG_CONTEXT.write(DebugLinkLayout(tokens=content_tokens))
        else:
            from trezor.messages import DebugLinkState

            await DEBUG_CONTEXT.write(DebugLinkState(tokens=content_tokens))
        storage.layout_watcher = LAYOUT_WATCHER_NONE

    async def dispatch_DebugLinkWatchLayout(msg: DebugLinkWatchLayout) -> Success:
        from trezor import ui

        layout_change_chan.putters.clear()
        if msg.watch:
            await ui.wait_until_layout_is_running()
        storage.watch_layout_changes = bool(msg.watch)
        log.debug(__name__, "Watch layout changes: %s", storage.watch_layout_changes)
        return Success()

    async def dispatch_DebugLinkResetDebugEvents(
        msg: DebugLinkResetDebugEvents,
    ) -> Success:
        # Resetting the debug events makes sure that the previous
        # events/layouts are not mixed with the new ones.
        storage.reset_debug_events()
        return Success()

    async def dispatch_DebugLinkDecision(msg: DebugLinkDecision) -> None:
        from trezor import workflow

        workflow.idle_timer.touch()

        if debuglink_decision_chan.putters:
            log.warning(__name__, "DebugLinkDecision queue is not empty")

        x = msg.x  # local_cache_attribute
        y = msg.y  # local_cache_attribute

        # Incrementing the counter for last events so we know what to await
        debug_events.last_event += 1

        # Touchscreen devices click on specific coordinates, with possible hold
        if (
            x is not None
            and y is not None
            and utils.INTERNAL_MODEL in ("T2T1", "T3T1", "D001")
        ):
            click_chan.publish((debug_events.last_event, x, y, msg.hold_ms))
        # Button devices press specific button
        elif msg.physical_button is not None and utils.INTERNAL_MODEL in ("T2B1",):
            button_chan.publish(
                (debug_events.last_event, msg.physical_button, msg.hold_ms)
            )
        else:
            # Will get picked up by _dispatch_debuglink_decision eventually
            debuglink_decision_chan.publish((debug_events.last_event, msg))

        if msg.wait:
            # We wait for all the previously sent events
            debug_events.awaited_event = debug_events.last_event
            storage.layout_watcher = LAYOUT_WATCHER_LAYOUT
            loop.schedule(return_layout_change())

    async def dispatch_DebugLinkGetState(
        msg: DebugLinkGetState,
    ) -> DebugLinkState | None:
        from trezor.messages import DebugLinkState

        from apps.common import mnemonic, passphrase

        m = DebugLinkState()
        m.mnemonic_secret = mnemonic.get_secret()
        m.mnemonic_type = mnemonic.get_type()
        m.passphrase_protection = passphrase.is_enabled()
        m.reset_entropy = storage.reset_internal_entropy

        if msg.wait_layout:
            if not storage.watch_layout_changes:
                raise wire.ProcessError("Layout is not watched")
            storage.layout_watcher = LAYOUT_WATCHER_STATE
            # We wait for the last previously sent event to finish
            debug_events.awaited_event = debug_events.last_event
            loop.schedule(return_layout_change())
            return None
        else:
            m.tokens = storage.current_content_tokens

        return m

    async def dispatch_DebugLinkRecordScreen(msg: DebugLinkRecordScreen) -> Success:
        if msg.target_directory:
            # In case emulator is restarted but we still want to record screenshots
            # into the same directory as before, we need to increment the refresh index,
            # so that the screenshots are not overwritten.
            global REFRESH_INDEX
            REFRESH_INDEX = msg.refresh_index
            storage.save_screen_directory = msg.target_directory
            storage.save_screen = True
        else:
            storage.save_screen = False
            display.clear_save()  # clear C buffers

        return Success()

    async def dispatch_DebugLinkReseedRandom(msg: DebugLinkReseedRandom) -> Success:
        if msg.value is not None:
            from trezor.crypto import random

            random.reseed(msg.value)
        return Success()

    async def dispatch_DebugLinkEraseSdCard(msg: DebugLinkEraseSdCard) -> Success:
        from trezor import io

        sdcard = io.sdcard  # local_cache_attribute

        try:
            sdcard.power_on()
            if msg.format:
                io.fatfs.mkfs()
            else:
                # trash first 1 MB of data to destroy the FAT filesystem
                assert sdcard.capacity() >= 1024 * 1024
                empty_block = bytes([0xFF] * sdcard.BLOCK_SIZE)
                for i in range(1024 * 1024 // sdcard.BLOCK_SIZE):
                    sdcard.write(i, empty_block)

        except OSError:
            raise wire.ProcessError("SD card operation failed")
        finally:
            sdcard.power_off()
        return Success()

    def boot() -> None:
        register = workflow_handlers.register  # local_cache_attribute

        register(MessageType.DebugLinkDecision, dispatch_DebugLinkDecision)  # type: ignore [Argument of type "(msg: DebugLinkDecision) -> Coroutine[Any, Any, None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkGetState, dispatch_DebugLinkGetState)  # type: ignore [Argument of type "(msg: DebugLinkGetState) -> Coroutine[Any, Any, DebugLinkState | None]" cannot be assigned to parameter "handler" of type "Handler[Msg@register]" in function "register"]
        register(MessageType.DebugLinkReseedRandom, dispatch_DebugLinkReseedRandom)
        register(MessageType.DebugLinkRecordScreen, dispatch_DebugLinkRecordScreen)
        register(MessageType.DebugLinkEraseSdCard, dispatch_DebugLinkEraseSdCard)
        register(MessageType.DebugLinkWatchLayout, dispatch_DebugLinkWatchLayout)
        register(
            MessageType.DebugLinkResetDebugEvents, dispatch_DebugLinkResetDebugEvents
        )
        register(
            MessageType.DebugLinkOptigaSetSecMax, dispatch_DebugLinkOptigaSetSecMax
        )

        loop.schedule(debuglink_decision_dispatcher())
        if storage.layout_watcher is not LAYOUT_WATCHER_NONE:
            loop.schedule(return_layout_change())

    async def dispatch_DebugLinkOptigaSetSecMax(
        msg: DebugLinkOptigaSetSecMax,
    ) -> Success:
        if utils.USE_OPTIGA:
            from trezor.crypto import optiga

            optiga.set_sec_max()
            return Success()
        else:
            raise wire.UnexpectedMessage("Optiga not supported")
