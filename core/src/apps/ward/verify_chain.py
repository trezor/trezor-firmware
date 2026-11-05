from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import WARDVerifyChain, WARDVerifyChainAck


async def verify_chain(msg: "WARDVerifyChain") -> "WARDVerifyChainAck":
    """WARDVerifyChain wire handler (TA): another-Trezor read-only chain verification.
    Verifies the AuthCommit chain from the device's trusted baseline to the WM-attested
    head (contiguity + counter+1 + AuthCommit per link), then adopts the head. Runs
    after WARDIngestAttestation, in place of WARDReconcile.
    """
    from trezor.messages import WARDVerifyChainAck

    from apps.common import ward as core
    from apps.ward import service

    links = []
    for link in msg.links:
        # Absent root fields mean the empty tree -> the 32-byte MAC-preimage sentinel.
        from_root = link.from_root if link.from_root else service.EMPTY_ROOT_HASH
        to_root = link.to_root if link.to_root else service.EMPTY_ROOT_HASH
        links.append(
            (
                link.from_counter,
                from_root,
                link.to_counter,
                to_root,
                link.auth_commit,
                link.sig_commit,
            )
        )

    counter, root, ward_id, root_mac = await core.verify_chain(links)

    return WARDVerifyChainAck(
        counter=counter, new_root=root, ward_id=ward_id, root_mac=root_mac
    )
