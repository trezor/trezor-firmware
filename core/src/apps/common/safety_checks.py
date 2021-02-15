import storage.cache
import storage.device
from storage.cache import APP_COMMON_SAFETY_CHECKS_TEMPORARY
from storage.device import SAFETY_CHECK_LEVEL_PROMPT, SAFETY_CHECK_LEVEL_STRICT
from trezor.messages import SafetyCheckLevel

if False:
    from typing import Optional
    from trezor.messages.ApplySettings import EnumTypeSafetyCheckLevel


def read_setting() -> EnumTypeSafetyCheckLevel:
    """
    Returns the effective safety check level.
    """
    temporary_safety_check_level: Optional[
        EnumTypeSafetyCheckLevel
    ] = storage.cache.get(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
    if temporary_safety_check_level is not None:
        return temporary_safety_check_level
    else:
        stored = storage.device.safety_check_level()
        if stored == SAFETY_CHECK_LEVEL_STRICT:
            return SafetyCheckLevel.Strict
        elif stored == SAFETY_CHECK_LEVEL_PROMPT:
            return SafetyCheckLevel.PromptAlways
        else:
            raise ValueError("Unknown SafetyCheckLevel")


def apply_setting(level: EnumTypeSafetyCheckLevel) -> None:
    """
    Changes the safety level settings.
    """
    if level == SafetyCheckLevel.Strict:
        storage.cache.delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
        storage.device.set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)
    elif level == SafetyCheckLevel.PromptAlways:
        storage.cache.delete(APP_COMMON_SAFETY_CHECKS_TEMPORARY)
        storage.device.set_safety_check_level(SAFETY_CHECK_LEVEL_PROMPT)
    elif level == SafetyCheckLevel.PromptTemporarily:
        storage.device.set_safety_check_level(SAFETY_CHECK_LEVEL_STRICT)
        storage.cache.set(APP_COMMON_SAFETY_CHECKS_TEMPORARY, level)
    else:
        raise ValueError("Unknown SafetyCheckLevel")


def is_strict() -> bool:
    """
    Shorthand for checking whether the effective level is Strict.
    """
    return read_setting() == SafetyCheckLevel.Strict
