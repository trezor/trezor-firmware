from typing import Optional, Tuple

from trezor.crypto import random
from trezor.crypto.curve import secp256k1

from .databaselib.database_payload import DatabasePayload
from .databaselib.digest_patricia_merkle_trie import DigestPatriciaMerkleTrie
from .databaselib.time import Time
from .databaselib.update_payload import UpdatePayload


def generate_random_identifier() -> bytes:
    import utime

    random.reseed(utime.ticks_us())
    return random.bytes(32)


class DatabaseContext:
    def __init__(
        self,
        identifier: Optional[bytes],
        revision_number: Optional[int],
        signing_key: bytes,
    ):
        self.identifier = identifier
        self.signing_key = signing_key
        self.revision_number = revision_number

    def sign_digest(self, digest: bytes) -> bytes:
        return secp256k1.sign(self.signing_key, digest)

    def verify_digest(self, signature: bytes, digest: bytes) -> bool:
        return secp256k1.verify(
            secp256k1.publickey(self.signing_key), signature, digest
        )

    def verify_database(
        self, global_time: Time, digest: bytes, signature: bytes
    ) -> None:
        assert self.identifier is not None
        assert self.revision_number is not None

        payload = DatabasePayload(
            self.identifier,
            self.revision_number,
            global_time,
            digest,
        )

        if not self.verify_digest(signature, payload.to_digest()):
            raise ValueError("Invalid signature")

    def sign_database(self, global_time: Time, digest: bytes) -> bytes:
        assert self.identifier is not None
        assert self.revision_number is not None

        payload = DatabasePayload(
            self.identifier, self.revision_number, global_time, digest
        )
        return self.sign_digest(payload.to_digest())

    def verify_update(
        self,
        identifier: bytes,
        time: Time,
        key: str,
        value: Optional[str],
        signature: bytes,
    ) -> None:
        assert self.identifier is not None
        assert self.revision_number is not None

        update = UpdatePayload(identifier, time, key, value)
        if not self.verify_digest(signature, update.to_digest()):
            raise ValueError("Invalid signature")

    def sign_payload(
        self, identifier: bytes, time: Time, key: str, value: Optional[str]
    ) -> bytes:
        assert self.identifier is not None
        assert self.revision_number is not None

        update = UpdatePayload(identifier, time, key, value)
        return self.sign_digest(update.to_digest())

    def verify_membership_inner(
        self,
        database_time: Time,
        database_signature: bytes,
        key: str,
        proof: DigestPatriciaMerkleTrie,
    ) -> Optional[str]:
        assert self.identifier is not None

        root_digest = proof.compute_digest()
        value = proof.search(key)
        self.verify_database(database_time, root_digest, database_signature)
        return value

    def verify_membership(
        self,
        database_time_bytes: bytes,
        database_signature: bytes,
        key: str,
        proof_bytes: bytes,
    ) -> Optional[str]:
        proof = DigestPatriciaMerkleTrie.from_bytes(proof_bytes)
        global_time = Time.from_bytes(database_time_bytes)
        return self.verify_membership_inner(global_time, database_signature, key, proof)
        
    def apply_operation(
        self,
        database_time: Time,
        database_signature: bytes,
        data_type : str,
        key: str,
    ):
        pass
        
        

    def modify_key_inner(
        self,
        database_time: Time,
        database_signature: bytes,
        key: str,
        value: Optional[str],
        proof: DigestPatriciaMerkleTrie,
    ) -> Tuple[bytes, bytes]:
        assert self.identifier is not None
        assert self.revision_number is not None

        self.verify_database(database_time, proof.compute_digest(), database_signature)

        try:
            proof.modify(key, value)
        except Exception:
            raise ValueError("Invalid proof")

        self.revision_number += 1
        database_time.increment(self.identifier)

        database_signature = self.sign_database(database_time, proof.compute_digest())
        update = UpdatePayload(self.identifier, database_time, key, value)
        update_signature = self.sign_digest(update.to_digest())

        return database_signature, update_signature

    def modify_key(
        self,
        database_time_bytes: bytes,
        database_signature: bytes,
        key: str,
        value: Optional[str],
        proof_bytes: bytes,
    ) -> Tuple[bytes, bytes]:
        proof = DigestPatriciaMerkleTrie.from_bytes(proof_bytes)
        database_global_time = Time.from_bytes(database_time_bytes)
        return self.modify_key_inner(
            database_global_time, database_signature, key, value, proof
        )

    def merge_inner(
        self,
        database_time: Time,
        database_signature: bytes,
        key: str,
        value: str,
        proof: DigestPatriciaMerkleTrie,
        update_identifier: bytes,
        update_time: Time,
        update_signature: bytes,
    ) -> bytes:
        assert self.identifier is not None
        assert self.revision_number is not None

        self.verify_database(database_time, proof.compute_digest(), database_signature)
        self.verify_update(update_identifier, update_time, key, value, update_signature)

        if database_time.get_local_time(
            update_identifier
        ) + 1 != update_time.get_local_time(update_identifier):
            raise ValueError("Invalid update global time")

        try:
            proof.modify(key, value)
        except Exception:
            raise ValueError("Invalid proof")
        self.revision_number += 1
        database_time.increment(update_identifier)

        database_signature = self.sign_database(database_time, proof.compute_digest())
        return database_signature

    def merge(
        self,
        database_time_bytes: bytes,
        database_signature: bytes,
        key: str,
        value: str,
        proof_bytes: bytes,
        update_identifier: bytes,
        update_time_bytes: bytes,
        update_signature: bytes,
    ) -> bytes:
        assert self.identifier is not None
        assert self.revision_number is not None

        database_time = Time.from_bytes(database_time_bytes)
        proof = DigestPatriciaMerkleTrie.from_bytes(proof_bytes)
        update_time = Time.from_bytes(update_time_bytes)
        return self.merge_inner(
            database_time,
            database_signature,
            key,
            value,
            proof,
            update_identifier,
            update_time,
            update_signature,
        )

    def wipe(self) -> bytes:
        self.identifier = generate_random_identifier()
        self.revision_number = 0

        root = DigestPatriciaMerkleTrie()
        time = Time.zero()

        database_signature = self.sign_database(time, root.compute_digest())
        return database_signature
