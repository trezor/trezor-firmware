import gc
from typing import TYPE_CHECKING

from trezor.crypto.pallas import Point, Scalar, generators as gen, scalar_from_i64

from .keys import FullViewingKey, sk_to_ask
from .note import Note
from .note_encryption import encrypt_note

if TYPE_CHECKING:
    from .note_encryption import TransmittedNoteCiphertext
    from ..random import ActionShieldingRng


# https://zips.z.cash/protocol/nu5.pdf#concretehomomorphiccommit
def commit_value(rcv: Scalar, v: int):
    V = scalar_from_i64(v) * gen.VALUE_COMMITMENT_VALUE_BASE
    R = rcv * gen.VALUE_COMMITMENT_RANDOMNESS_BASE
    return V + R


class Action:
    def __init__(
        self,
        cv: bytes,
        nf: bytes,
        rk: bytes,
        cmx: bytes,
        encrypted_note: TransmittedNoteCiphertext,
    ) -> None:
        self.cv = cv
        self.nf = nf
        self.rk = rk
        self.cmx = cmx
        self.encrypted_note = encrypted_note


class InputInfo:
    def __init__(
        self, note: Note, fvk: FullViewingKey, dummy_ask: Scalar | None = None
    ):
        self.note = note
        self.fvk = fvk
        self.dummy_ask = dummy_ask  # for dummy notes

    @classmethod
    def dummy(cls, rng: ActionShieldingRng) -> Self:
        dummy_sk = rng.dummy_sk()
        fvk = FullViewingKey.from_spending_key(dummy_sk)
        note = Note(
            recipient=fvk.address(0),
            value=0,
            rho=rng.rho(),
            rseed=rng.rseed_old(),
        )
        dummy_ask = sk_to_ask(dummy_sk)
        return cls(note, fvk, dummy_ask)


class OutputInfo:
    def __init__(self, ovk, address, value, memo):
        self.ovk = ovk
        self.address = address
        self.value = value
        self.memo = memo

    @classmethod
    def dummy(cls, rng: ActionShieldingRng) -> Self:
        return cls(None, rng.recipient(), 0, None)


def build_action(
    input: InputInfo,
    output: OutputInfo,
    rng: ActionShieldingRng,
) -> Action:
    gc.collect()

    # nullifier
    nf_old = input.note.nullifier(input.fvk.nk)

    # verification key
    alpha = rng.alpha()
    akP = Point(input.fvk.ak.to_bytes())
    rk = akP + alpha * gen.SPENDING_KEY_BASE

    # note commitment
    note = Note(
        recipient=output.address,
        value=output.value,
        rho=nf_old,
        rseed=rng.rseed_new(),
    )
    cm_new = note.commitment()

    # value commitment
    v_net = input.note.value - output.value
    rcv = rng.rcv()
    cv_net = commit_value(rcv, v_net)

    # note encryption
    gc.collect()
    encrypted_note = encrypt_note(
        note,
        output.memo,
        cv_net,
        cm_new,
        output.ovk,
        rng,
    )

    gc.collect()
    action = Action(
        cv=cv_net.to_bytes(),
        nf=nf_old.to_bytes(),
        rk=rk.to_bytes(),
        cmx=cm_new.extract().to_bytes(),
        encrypted_note=encrypted_note,
    )
    gc.collect()
    return action
