class OrchardPool:
    def __init__(self, tx, hasher, tx_req, keychain):
        self.tx = tx
        self.hasher = hasher
        self.orchard_inputs_hash = None
        self.orchard_outputs_hash = None
        self.keychain = keychain

        self.total_in = 0
        self.total_out = 0
        self.change_out = 0
        self.change_count = 0

        self.wallet_path_checker = OrchardWalletPathChecker()

        self.tx_req = tx_req

    async def step1_process_inputs(self):
        log.warning(__name__, "step1_process_inputs")
        #txi = await self.get_orchard_input(0)
        #log.warning(__name__, "txi 0: " + str(txi))

        hasher = HashWriter(blake2b(outlen=32, personal=b"orchard_inputs_"))

        for i in range(self.tx.orchard.inputs_count):
            txi = await self.get_orchard_input(i)
            hasher.write(protobuf.dump_message_buffer(txi))

            log.warning(__name__, "processing txi " + str(txi))
            self.wallet_path_checker.add_input(txi)
            self.total_in += txi.amount

        self.orchard_inputs_hash = hasher.get_digest()

    async def step2_approve_outputs(self):
        log.warning(__name__, "step2_approve_outputs")

        hasher = HashWriter(blake2b(outlen=32, personal=b"orchard_outputs"))

        for i in range(self.tx.orchard.outputs_count):
            txo = await self.get_orchard_output(i)
            hasher.write(protobuf.dump_message_buffer(txo))

            if orchard_output_is_change(txo):
                self.change_out += txo.amount
                self.change_count += 1

            if not self.wallet_path_checker.output_matches(txo):
                yield UiConfirmorchardOutput(txo)

            self.total_out += txo.amount

        self.orchard_outputs_hash = hasher.get_digest()

            #self.tx_info.add_orchard_output(txo)

    # step3: approve orig tx ???

    # step4: serialize_inputs

    async def step5_serialize(self): 
        log.warning(__name__, "step5_serialize")

        # Orchard

        # write_bitcoin_varint(self.serialized_tx, self.actions_amount())  # nActionsOrchard
        # let the orchard serialization to the client

        seed = random.bytes(32)

        # TODO: send the seed to the client

        rand_config = {
            "seed": seed,
            "pos": 0,
        }

        # TODO: init hashers
        hasher_in = HashWriter(blake2b(outlen=32, personal=b"orchard_inputs_"))
        hasher_out = HashWriter(blake2b(outlen=32, personal=b"orchard_outputs"))

        for i in range(self.actions_count()):
            action_info = dict()

            if i < self.tx.orchard.inputs_count:
                txi = await self.get_orchard_input(i)
                hasher_in.write(protobuf.dump_message_buffer(txi))

                sk = self.keychain.derive(txi.address_n).spending_key()
                fvk = zcashlib.get_orchard_fvk(sk)
                action_info["spend_info"] = {
                    "fvk": fvk,
                    "note": txi.zcash.note,
                }

            if i < self.tx.orchard.outputs_count:
                txo = await self.get_orchard_output(i)
                hasher_out.write(protobuf.dump_message_buffer(txo))

                if orchard_output_is_change(txo):
                    sk = self.keychain.derive(txo.address_n).spending_key()
                    address = zcashlib.get_orchard_address(sk, 0)
                else:
                    receivers = zcash.address.decode_unified(txo.address)
                    address = receivers.get(zcash.address.ORCHARD)
                    assert address is not None

                action_info["output_info"] = {
                    "ovk_flag": txo.zcash.ovk_flag,
                    "address": address,
                    "value": txo.amount,
                    "memo": txo.zcash.memo,
                }

                if txo.zcash.ovk_flag:
                    sk = self.keychain.derive(txo.address_n).spending_key()
                    fvk = zcash.get_orchard_fvk(sk)
                    action_info["output_info"]["fvk"] = fvk


            log.warning(__name__, "processing action info: %s", pretty_str(action_info))
            action = zcashlib.shield(action_info, rand_config)  # on this line the magic happens
            log.warning(__name__, "action: %s", pretty_str(action))
            self.hasher.add_action(action)
            log.warning(__name__, "rand_config: pos %s", str(rand_config["pos"]))

        if (hasher_in.get_digest() != self.orchard_inputs_hash or
            hasher_out.get_digest() != self.orchard_outputs_hash):
            raise ProcessError("Transaction data changed during the process.")

        # Orchard flags as defined in protocol §7.1 tx v5 format
        flags = 0x00 \
              | 0x01 if self.tx.orchard.enable_spends else 0x00 \
              | 0x02 if self.tx.orchard.enable_outputs else 0x00

        self.hasher.finalize(
            flags=bytes([flags]),  # one byte
            value_balance=self.balance(),
            anchor=self.tx.orchard.anchor,
        )


    async def step6_sign_inputs(self, sighash, signer):
        # checking inputs integrity is not relevant
        for i in range(self.tx.orchard.inputs_count):
            txi = await self.get_orchard_input(i)

            alpha = 32*b"\x00"
            sk = self.keychain.derive(txi.address_n).spending_key()
            signature = zcashlib.sign(sk, alpha, sighash)
            signer.set_serialized_signature(i, signature)

    # step7: finish

    async def get_orchard_input(self, i):
        self.tx_req.request_type = RequestType.TXorchardINPUT
        self.tx_req.details.request_index = i
        ack = yield TxAckInput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return sanitize_orchard_input(ack.tx.input)

    async def get_orchard_output(self, i):
        self.tx_req.request_type = RequestType.TXorchardOUTPUT
        self.tx_req.details.request_index = i
        ack = yield TxAckOutput, self.tx_req
        helpers._clear_tx_request(self.tx_req)
        return sanitize_orchard_output(ack.tx.output)

    def balance(self):
        return self.total_in - self.total_out

    def actions_count(self):
        if self.tx.orchard.inputs_count + self.tx.orchard.outputs_count > 0:
            return max(
                2,  # minimal amount of actions
                self.tx.orchard.inputs_count,
                self.tx.orchard.outputs_count
            )
        else:
            return 0

    def is_empty(self):
        return self.actions_count() == 0