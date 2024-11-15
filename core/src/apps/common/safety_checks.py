import storage.device as storage_device
from storage.cache_common import APP_COMMON_SAFETY_CHECKS_TEMPORARY
from storage.device import SAFETY_CHECK_LEVEL_PROMPT, SAFETY_CHECK_LEVEL_STRICT
from trezor.enums import SafetyCheckLevel
from trezor.wire import context


def read_setting() -> SafetyCheckLevel:
    """
    Returns the effective safety check level.
    """
    temporary_safety_check_level = context.cache_get(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
    if temporary_safety_check_level:
        return int.from_bytes(temporary_safety_check_level, "big")  # type: ignore [int-into-enum]
    else:
        stored = storage_device.safety_check_level()
        if stored == SAFETY_CHECK_LEVEL_STRICT:
            return SafetyCheckLevel.Strict
        elif stored == SAFETY_CHECK_LEVEL_PROMPT:
            return SafetyCheckLevel.PromptAlways
        else:
            raise ValueError("Unknown SafetyCheckLevel")


def apply_setting(level: SafetyCheckLevel) -> None:
    """
    Changes the safety level settings.
    """
    if level == SafetyCheckLevel.Strict:
        context.cache_delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
        storage_device.set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)
    elif level == SafetyCheckLevel.PromptAlways:
        context.cache_delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
        storage_device.set_safety_check_level(SAFETY_CHECK_LEVEL_PROMPT)
    elif level == SafetyCheckLevel.PromptTemporarily:
        storage_device.set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)
        context.cache_set(APP_COMMON_SAFETY_CHECKS_TEMPORARY, level.to_bytes(1, "big"))
    else:
        raise ValueError("Unknown SafetyCheckLevel")


def is_strict() -> bool:
    """
    Shorthand for checking whether the effective level is Strict.
    """
    return read_setting() == SafetyCheckLevel.Strict
