// https://github.com/input-output-hk/cardano-crypto/blob/master/tests/goldens/cardano/crypto/wallet/BIP39-128
START_TEST(test_bip32_cardano_hdnode_vector_1)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	ck_assert_mem_eq(node.chain_code,  fromhex("739f4b3caca4c9ad4fcd4bdc2ef42c8601af8d6946999ef85ef6ae84f66e72eb"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("6065a956b1b34145c4416fdc3ba3276801850e91a77a31a7be782463288aea53"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("60ba6e25b1a02157fb69c5d1d7b96c4619736e545447069a6a6f0ba90844bc8e"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("64b20fa082b3143d6b5eed42c6ef63f99599d0888afe060620abc1b319935fe1"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_2)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000000);

	ck_assert_mem_eq(node.chain_code,  fromhex("6755cb82e892d6614c007a5efbceb21d95a5244e269d0e206b48b9a495390b03"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("e7d27516538403a53a8b041656a3f570909df641a0ab811fe7d87c9ba02a830c"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("794a2c54ad8b525b781773c87d38cbf4197636bc427a9d551368286fe4c294a4"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("95bb82ffd5707716bc65170ab4e8dafeed90fbe0ce9258713b7751e962d931df"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_3)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000001);

	ck_assert_mem_eq(node.chain_code,  fromhex("47a242713bd18608231147c066b6083bfc1e9066fec9f621844c84fed6228a34"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("9b5a3d9a4c60bcd49bb64b72c082b164314d0f61d842f2575fd1d4fb30a28a0c"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("b093e376f41eb7bf80abcd0073a52455d25b5d21815bc758e5f6f81536aedebb"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("79fc8154554b97e4c56ef2f9dbb4c1421ff19509688931a1e964bda5dec0f19f"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_4)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000000);
	hdnode_private_ckd_cardano(&node, 0x80000001);

	ck_assert_mem_eq(node.chain_code,  fromhex("d6798491b9fa4612370ae5ef3c623a0b6872f3ad8f26970885fa67c83bdc425e"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("52e0c98aa600cfdcd1ff28fcda5227ed87063f4a98547a78b771052cf102b40c"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("6c18d9f8075b1a6a1833540607479bd58b7beb8a83d2bb01ca7ae02452a25803"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("dc907c7c06e6314eedd9e18c9f6c6f9cc4e205fb1c70da608234c319f1f7b0d6"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_5)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000000);
	hdnode_private_ckd_cardano(&node, 0x80000001);
	hdnode_private_ckd_cardano(&node, 0x80000002);
	
	ck_assert_mem_eq(node.chain_code,  fromhex("4169a2a32e3618a903e930bd1a713033a38f92389093408394e29ac37a1752ea"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("11fd6462a3a92b35c22703f6f1c124ddcf36b7c2b09cc2784f320e1cfa12ec04"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("c2785803c61c46aeca192a1bb1b7b20a8c4cc7fa01db57fc5d1d8a5473402352"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("839775a41876e328986aa26168958bba1176e67819b357eea84afceab8b1db78"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_6)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000000);
	hdnode_private_ckd_cardano(&node, 0x80000001);
	hdnode_private_ckd_cardano(&node, 0x80000002);
	hdnode_private_ckd_cardano(&node, 0x80000002);

	ck_assert_mem_eq(node.chain_code,  fromhex("3ae9c99a5925cba2dcf121baf3a0254f3dea23c129f9eb70a8a7e8897c5199ba"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("5b1e5cad02274ba461f4708d8598d3497faf8fe3e894a379573aa6ac3a03e505"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("ba179d2e3c67aabb486c48d16002b51ad32eab434c738a1550962313b07098cd"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("75eb8d197ec8627c85af88e66aa1e49065dd8ac98ed8991db52ece01635dfb76"), 32);
}
END_TEST

START_TEST(test_bip32_cardano_hdnode_vector_7)
{
	HDNode node;

	uint8_t seed[66];
	int seed_len = mnemonic_to_entropy("ring crime symptom enough erupt lady behave ramp apart settle citizen junk", seed + 2);
	ck_assert_int_eq(seed_len, 132);
	hdnode_from_seed_cardano(seed, seed_len / 8, &node);

	hdnode_private_ckd_cardano(&node, 0x80000000);
	hdnode_private_ckd_cardano(&node, 0x80000001);
	hdnode_private_ckd_cardano(&node, 0x80000002);
	hdnode_private_ckd_cardano(&node, 0x80000002);
	hdnode_private_ckd_cardano(&node, 0xBB9ACA00);

	ck_assert_mem_eq(node.chain_code,  fromhex("15c450b86dd7dd83b31951d9ee03eb1a7925161d817bd517c69cf09e3671f1ca"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("624b47150f58dfa44284fbc63c9f99b9b79f808c4955a461f0e2be44eb0be50d"), 32);
	ck_assert_mem_eq(node.private_key_extension, fromhex("097aa006d694b165ef37cf23562e5967c96e49255d2f20faae478dee83aa5b02"), 32);
	hdnode_fill_public_key(&node);
	ck_assert_mem_eq(node.public_key + 1,  fromhex("0588589cd9b51dfc028cf225674069cbe52e0e70deb02dc45b79b26ee3548b00"), 32);
}
END_TEST

// https://github.com/input-output-hk/cardano-crypto/blob/master/tests/goldens/cardano/crypto/wallet/BIP39-128
START_TEST(test_ed25519_cardano_sign_vectors)
{
	ed25519_public_key public_key;
	ed25519_secret_key secret_key;
	ed25519_secret_key secret_key_extension;
	ed25519_signature signature;

	static const char *vectors[] = {
		"6065a956b1b34145c4416fdc3ba3276801850e91a77a31a7be782463288aea53", // private key
		"60ba6e25b1a02157fb69c5d1d7b96c4619736e545447069a6a6f0ba90844bc8e", // private key extension
		"64b20fa082b3143d6b5eed42c6ef63f99599d0888afe060620abc1b319935fe1", // public key
		"45b1a75fe3119e13c6f60ab9ba674b42f946fdc558e07c83dfa0751c2eba69c79331bd8a4a975662b23628a438a0eba76367e44c12ca91b39ec59063f860f10d", // signature

		"e7d27516538403a53a8b041656a3f570909df641a0ab811fe7d87c9ba02a830c", // private key
		"794a2c54ad8b525b781773c87d38cbf4197636bc427a9d551368286fe4c294a4", // private key extension
		"95bb82ffd5707716bc65170ab4e8dafeed90fbe0ce9258713b7751e962d931df", // public key
		"f2c9171782e7df7665126ac545ae53b05964b0160536efdb545e2460dbbec2b19ec6b338b8f1bf4dfee94360ed024b115e37b1d7e6f3f9ae4beb79539428560f", // signature

		"9b5a3d9a4c60bcd49bb64b72c082b164314d0f61d842f2575fd1d4fb30a28a0c", // private key
		"b093e376f41eb7bf80abcd0073a52455d25b5d21815bc758e5f6f81536aedebb", // private key extension
		"79fc8154554b97e4c56ef2f9dbb4c1421ff19509688931a1e964bda5dec0f19f", // public key
		"2ba1439ae648a7e8da7c9ab1ee6da94fd4ebe37abd0978306e8fba2afa8f111a88a993dbf008bedae9167f4f68409e4c9ddaf02cba12418447b1848907ad800f", // signature

		"52e0c98aa600cfdcd1ff28fcda5227ed87063f4a98547a78b771052cf102b40c", // private key
		"6c18d9f8075b1a6a1833540607479bd58b7beb8a83d2bb01ca7ae02452a25803", // private key extension
		"dc907c7c06e6314eedd9e18c9f6c6f9cc4e205fb1c70da608234c319f1f7b0d6", // public key
		"0cd34f84e0d2fcb1800bdb0e869b9041349955ced66aedbe6bda187ebe8d36a62a05b39647e92fcc42aa7a7368174240afba08b8c81f981a22f942d6bd781602", // signature

		"11fd6462a3a92b35c22703f6f1c124ddcf36b7c2b09cc2784f320e1cfa12ec04", // private key
		"c2785803c61c46aeca192a1bb1b7b20a8c4cc7fa01db57fc5d1d8a5473402352", // private key extension
		"839775a41876e328986aa26168958bba1176e67819b357eea84afceab8b1db78", // public key
		"e41f73db2f8d2896a687802b2be76b7cabb73dfbb4891494883a0cbd9bbb9e5f9d3e14d2d0b06c6674333508496db660936737c0efd9511514147dac79fa4905", // signature

		"5b1e5cad02274ba461f4708d8598d3497faf8fe3e894a379573aa6ac3a03e505", // private key
		"ba179d2e3c67aabb486c48d16002b51ad32eab434c738a1550962313b07098cd", // private key extension
		"75eb8d197ec8627c85af88e66aa1e49065dd8ac98ed8991db52ece01635dfb76", // public key
		"631015357cee3051116b4c2ff4d1c5beb13b6e5023635aa1eeb0563cadf0d4fbc10bd5e31b4a4220c67875558c41b5cc0328104ae39cc7ff20ff0c2bda598906", // signature

		"624b47150f58dfa44284fbc63c9f99b9b79f808c4955a461f0e2be44eb0be50d", // private key
		"097aa006d694b165ef37cf23562e5967c96e49255d2f20faae478dee83aa5b02", // private key extension
		"0588589cd9b51dfc028cf225674069cbe52e0e70deb02dc45b79b26ee3548b00", // public key
		"1de1d275428ba9491a433cd473cd076c027f61e7a8b5391df9dea5cb4bc88d8a57b095906a30b13e68259851a8dd3f57b6f0ffa37a5d3ffc171240f2d404f901", // signature

		0, 0,
	};

	const char **test_data;
	test_data = vectors;
	while (*test_data) {
		memcpy(secret_key, fromhex(*test_data), 32);
		MARK_SECRET_DATA(secret_key, sizeof(secret_key));

		memcpy(secret_key_extension, fromhex(*(test_data + 1)), 32);
		MARK_SECRET_DATA(secret_key_extension, sizeof(secret_key_extension));

		ed25519_publickey_ext(secret_key, secret_key_extension, public_key);
		UNMARK_SECRET_DATA(public_key, sizeof(public_key));

		ck_assert_mem_eq(public_key, fromhex(*(test_data + 2)), 32);

		const uint8_t * message = (const uint8_t *) "Hello World";
		ed25519_sign_ext(message, 11, secret_key, secret_key_extension, public_key, signature);
		UNMARK_SECRET_DATA(signature, sizeof(signature));

		ck_assert_mem_eq(signature, fromhex(*(test_data + 3)), 64);

		UNMARK_SECRET_DATA(secret_key, sizeof(secret_key));
		UNMARK_SECRET_DATA(secret_key_extension, sizeof(secret_key_extension));

		test_data += 4;
	}
}
END_TEST
