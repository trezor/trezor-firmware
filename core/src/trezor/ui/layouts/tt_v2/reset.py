from typing import TYPE_CHECKING

from trezor import wire

if TYPE_CHECKING:
    from trezor.enums import BackupType
    from typing import Sequence


async def show_share_words(
    ctx: wire.GenericContext,
    share_words: Sequence[str],
    share_index: int | None = None,
    group_index: int | None = None,
) -> None:
    raise NotImplementedError


async def confirm_word(
    ctx: wire.GenericContext,
    share_index: int | None,
    share_words: Sequence[str],
    offset: int,
    count: int,
    group_index: int | None = None,
) -> bool:
    raise NotImplementedError


async def slip39_show_checklist(
    ctx: wire.GenericContext, step: int, backup_type: BackupType
) -> None:
    raise NotImplementedError


async def slip39_prompt_threshold(
    ctx: wire.GenericContext, num_of_shares: int, group_id: int | None = None
) -> int:
    raise NotImplementedError


async def slip39_prompt_number_of_shares(
    ctx: wire.GenericContext, group_id: int | None = None
) -> int:
    raise NotImplementedError


async def slip39_advanced_prompt_number_of_groups(ctx: wire.GenericContext) -> int:
    raise NotImplementedError


async def slip39_advanced_prompt_group_threshold(
    ctx: wire.GenericContext, num_of_groups: int
) -> int:
    raise NotImplementedError
