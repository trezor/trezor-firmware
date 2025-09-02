#!/usr/bin/env python3
"""
Convert ACVP ML-DSA test vectors to C arrays for embedded testing.
Generates keyGen, sigGen, and sigVer test vectors.
"""

import json
import os


def hex_to_c_array(hex_string, array_name, elements_per_line=12):
    """Convert hex string to C array format."""
    if hex_string.startswith("0x"):
        hex_string = hex_string[2:]

    # Remove any whitespace
    hex_string = hex_string.replace(" ", "").replace("\n", "")

    # Convert to bytes
    byte_values = []
    for i in range(0, len(hex_string), 2):
        byte_values.append(f"0x{hex_string[i:i+2]}")

    # Format as C array
    result = f"static const uint8_t {array_name}[] = {{\n"
    for i in range(0, len(byte_values), elements_per_line):
        line_bytes = byte_values[i : i + elements_per_line]
        result += "    " + ", ".join(line_bytes)
        if i + elements_per_line < len(byte_values):
            result += ","
        result += "\n"
    result += "};\n"

    return result, len(byte_values)


def process_keygen_tests():
    """Process keyGen test vectors."""
    keygen_file = "/home/mpastyrik/Development/trezor-firmware/core/vendor/mldsa-native/test/.acvp-data/v1.1.0.40/files/ML-DSA-keyGen-FIPS204/internalProjection.json"

    with open(keygen_file, "r") as f:
        data = json.load(f)

    # Find ML-DSA-44 test group
    test_group = None
    for group in data["testGroups"]:
        if group["parameterSet"] == "ML-DSA-44":
            test_group = group
            break

    if test_group is None:
        print("ML-DSA-44 keyGen test group not found")
        return None

    return test_group["tests"]


def process_siggen_tests():
    """Process sigGen test vectors."""
    siggen_file = "/home/mpastyrik/Development/trezor-firmware/core/vendor/mldsa-native/test/.acvp-data/v1.1.0.40/files/ML-DSA-sigGen-FIPS204/internalProjection.json"

    with open(siggen_file, "r") as f:
        data = json.load(f)

    # Find ML-DSA-44 test group
    test_group = None
    for group in data["testGroups"]:
        if group["parameterSet"] == "ML-DSA-44":
            test_group = group
            break

    if test_group is None:
        print("ML-DSA-44 sigGen test group not found")
        return None

    return test_group["tests"]


def process_sigver_tests():
    """Process sigVer test vectors."""
    sigver_file = "/home/mpastyrik/Development/trezor-firmware/core/vendor/mldsa-native/test/.acvp-data/v1.1.0.40/files/ML-DSA-sigVer-FIPS204/internalProjection.json"

    with open(sigver_file, "r") as f:
        data = json.load(f)

    # Find ML-DSA-44 test group
    test_group = None
    for group in data["testGroups"]:
        if group["parameterSet"] == "ML-DSA-44":
            test_group = group
            break

    if test_group is None:
        print("ML-DSA-44 sigVer test group not found")
        return None

    return test_group["tests"]


def main():
    # Process all test types
    keygen_tests = process_keygen_tests()
    siggen_tests = process_siggen_tests()
    sigver_tests = process_sigver_tests()

    if not keygen_tests:
        print("No keyGen tests found")
        return

    if not siggen_tests:
        print("No sigGen tests found")
        return

    if not sigver_tests:
        print("No sigVer tests found")
        return

    num_keygen = len(keygen_tests)
    num_siggen = len(siggen_tests)
    num_sigver = len(sigver_tests)

    # # Limit test counts for reasonable file size
    # keygen_tests = keygen_tests[:num_keygen]
    # siggen_tests = siggen_tests[:num_siggen]
    # sigver_tests = sigver_tests[:num_sigver]

    print(
        f"Using {num_keygen} keyGen, {num_siggen} sigGen, {num_sigver} sigVer test cases"
    )

    # Generate C header
    with open("core/embed/projects/prodtest/cmd/test_data.h", "w") as f:
        f.write("// Auto-generated ACVP ML-DSA-44 test vectors\n")
        f.write("// DO NOT EDIT MANUALLY\n\n")
        f.write("#ifndef TEST_DATA_H\n")
        f.write("#define TEST_DATA_H\n\n")
        f.write("#include <stdint.h>\n")
        f.write("#include <stdbool.h>\n\n")

        # Constants
        f.write(f"#define NUM_KEYGEN_TESTS {num_keygen}\n")
        f.write(f"#define NUM_SIGGEN_TESTS {num_siggen}\n")
        f.write(f"#define NUM_SIGVER_TESTS {num_sigver}\n")
        f.write("#ifndef CRYPTO_PUBLICKEYBYTES\n")
        f.write("#define CRYPTO_PUBLICKEYBYTES 1952\n")
        f.write("#endif\n")
        f.write("#ifndef CRYPTO_SECRETKEYBYTES\n")
        f.write("#define CRYPTO_SECRETKEYBYTES 4032\n")
        f.write("#endif\n")
        f.write("#ifndef CRYPTO_SEEDBYTES\n")
        f.write("#define CRYPTO_SEEDBYTES 32\n")
        f.write("#endif\n")
        f.write("#ifndef CRYPTO_BYTES\n")
        f.write("#define CRYPTO_BYTES 3309  // ML-DSA-44 signature size\n")
        f.write("#endif\n\n")

        # KeyGen test vectors
        f.write("// ===== KEYGEN TEST VECTORS =====\n\n")
        seed_arrays = []
        pk_arrays = []
        sk_arrays = []

        for i, test in enumerate(keygen_tests):
            # Test seeds
            seed_array, seed_len = hex_to_c_array(test["seed"], f"keygen_seed_{i}")
            f.write(seed_array)
            f.write(f"// KeyGen seed {i} length: {seed_len} bytes\n\n")
            seed_arrays.append(f"keygen_seed_{i}")

            # Expected public keys
            pk_array, pk_len = hex_to_c_array(test["pk"], f"keygen_pk_{i}")
            f.write(pk_array)
            f.write(f"// KeyGen public key {i} length: {pk_len} bytes\n\n")
            pk_arrays.append(f"keygen_pk_{i}")

            # Expected secret keys
            sk_array, sk_len = hex_to_c_array(test["sk"], f"keygen_sk_{i}")
            f.write(sk_array)
            f.write(f"// KeyGen secret key {i} length: {sk_len} bytes\n\n")
            sk_arrays.append(f"keygen_sk_{i}")

        # KeyGen 2D arrays
        f.write("// KeyGen test seeds array\n")
        f.write("static const uint8_t* const keygen_seeds[NUM_KEYGEN_TESTS] = {\n")
        for i, seed_name in enumerate(seed_arrays):
            f.write(f"    {seed_name}")
            if i < len(seed_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// KeyGen expected public keys array\n")
        f.write(
            "static const uint8_t* const keygen_expected_pks[NUM_KEYGEN_TESTS] = {\n"
        )
        for i, pk_name in enumerate(pk_arrays):
            f.write(f"    {pk_name}")
            if i < len(pk_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// KeyGen expected secret keys array\n")
        f.write(
            "static const uint8_t* const keygen_expected_sks[NUM_KEYGEN_TESTS] = {\n"
        )
        for i, sk_name in enumerate(sk_arrays):
            f.write(f"    {sk_name}")
            if i < len(sk_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        # SigGen test vectors
        f.write("// ===== SIGGEN TEST VECTORS =====\n\n")
        siggen_msg_arrays = []
        siggen_pk_arrays = []
        siggen_sk_arrays = []
        siggen_ctx_arrays = []
        siggen_sig_arrays = []

        for i, test in enumerate(siggen_tests):
            # Messages
            msg_array, msg_len = hex_to_c_array(test["message"], f"siggen_msg_{i}")
            f.write(msg_array)
            f.write(f"// SigGen message {i} length: {msg_len} bytes\n\n")
            siggen_msg_arrays.append((f"siggen_msg_{i}", msg_len))

            # Public keys
            pk_array, pk_len = hex_to_c_array(test["pk"], f"siggen_pk_{i}")
            f.write(pk_array)
            f.write(f"// SigGen public key {i} length: {pk_len} bytes\n\n")
            siggen_pk_arrays.append(f"siggen_pk_{i}")

            # Secret keys
            sk_array, sk_len = hex_to_c_array(test["sk"], f"siggen_sk_{i}")
            f.write(sk_array)
            f.write(f"// SigGen secret key {i} length: {sk_len} bytes\n\n")
            siggen_sk_arrays.append(f"siggen_sk_{i}")

            # Context
            ctx_array, ctx_len = hex_to_c_array(test["context"], f"siggen_ctx_{i}")
            f.write(ctx_array)
            f.write(f"// SigGen context {i} length: {ctx_len} bytes\n\n")
            siggen_ctx_arrays.append((f"siggen_ctx_{i}", ctx_len))

            # Expected signatures
            sig_array, sig_len = hex_to_c_array(test["signature"], f"siggen_sig_{i}")
            f.write(sig_array)
            f.write(f"// SigGen signature {i} length: {sig_len} bytes\n\n")
            siggen_sig_arrays.append(f"siggen_sig_{i}")

        # SigGen arrays with lengths
        f.write("// SigGen message lengths\n")
        f.write("static const size_t siggen_msg_lens[NUM_SIGGEN_TESTS] = {\n")
        for i, (_, msg_len) in enumerate(siggen_msg_arrays):
            f.write(f"    {msg_len}")
            if i < len(siggen_msg_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen context lengths\n")
        f.write("static const size_t siggen_ctx_lens[NUM_SIGGEN_TESTS] = {\n")
        for i, (_, ctx_len) in enumerate(siggen_ctx_arrays):
            f.write(f"    {ctx_len}")
            if i < len(siggen_ctx_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen messages array\n")
        f.write("static const uint8_t* const siggen_messages[NUM_SIGGEN_TESTS] = {\n")
        for i, (msg_name, _) in enumerate(siggen_msg_arrays):
            f.write(f"    {msg_name}")
            if i < len(siggen_msg_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen public keys array\n")
        f.write("static const uint8_t* const siggen_pks[NUM_SIGGEN_TESTS] = {\n")
        for i, pk_name in enumerate(siggen_pk_arrays):
            f.write(f"    {pk_name}")
            if i < len(siggen_pk_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen secret keys array\n")
        f.write("static const uint8_t* const siggen_sks[NUM_SIGGEN_TESTS] = {\n")
        for i, sk_name in enumerate(siggen_sk_arrays):
            f.write(f"    {sk_name}")
            if i < len(siggen_sk_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen contexts array\n")
        f.write("static const uint8_t* const siggen_contexts[NUM_SIGGEN_TESTS] = {\n")
        for i, (ctx_name, _) in enumerate(siggen_ctx_arrays):
            f.write(f"    {ctx_name}")
            if i < len(siggen_ctx_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigGen expected signatures array\n")
        f.write(
            "static const uint8_t* const siggen_expected_sigs[NUM_SIGGEN_TESTS] = {\n"
        )
        for i, sig_name in enumerate(siggen_sig_arrays):
            f.write(f"    {sig_name}")
            if i < len(siggen_sig_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        # SigVer test vectors
        f.write("// ===== SIGVER TEST VECTORS =====\n\n")
        sigver_msg_arrays = []
        sigver_pk_arrays = []
        sigver_ctx_arrays = []
        sigver_sig_arrays = []
        sigver_expected = []

        for i, test in enumerate(sigver_tests):
            # Messages
            msg_array, msg_len = hex_to_c_array(test["message"], f"sigver_msg_{i}")
            f.write(msg_array)
            f.write(f"// SigVer message {i} length: {msg_len} bytes\n\n")
            sigver_msg_arrays.append((f"sigver_msg_{i}", msg_len))

            # Public keys
            pk_array, pk_len = hex_to_c_array(test["pk"], f"sigver_pk_{i}")
            f.write(pk_array)
            f.write(f"// SigVer public key {i} length: {pk_len} bytes\n\n")
            sigver_pk_arrays.append(f"sigver_pk_{i}")

            # Context
            ctx_array, ctx_len = hex_to_c_array(test["context"], f"sigver_ctx_{i}")
            f.write(ctx_array)
            f.write(f"// SigVer context {i} length: {ctx_len} bytes\n\n")
            sigver_ctx_arrays.append((f"sigver_ctx_{i}", ctx_len))

            # Signatures
            sig_array, sig_len = hex_to_c_array(test["signature"], f"sigver_sig_{i}")
            f.write(sig_array)
            f.write(f"// SigVer signature {i} length: {sig_len} bytes\n\n")
            sigver_sig_arrays.append(f"sigver_sig_{i}")

            # Expected result
            sigver_expected.append(test["testPassed"])

        # SigVer arrays
        f.write("// SigVer expected results\n")
        f.write("static const bool sigver_expected_results[NUM_SIGVER_TESTS] = {\n")
        for i, expected in enumerate(sigver_expected):
            f.write(f"    {'true' if expected else 'false'}")
            if i < len(sigver_expected) - 1:
                f.write(",")
            f.write(f"  // Test {i}: {'PASS' if expected else 'FAIL'}\n")
        f.write("};\n\n")

        f.write("// SigVer message lengths\n")
        f.write("static const size_t sigver_msg_lens[NUM_SIGVER_TESTS] = {\n")
        for i, (_, msg_len) in enumerate(sigver_msg_arrays):
            f.write(f"    {msg_len}")
            if i < len(sigver_msg_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigVer context lengths\n")
        f.write("static const size_t sigver_ctx_lens[NUM_SIGVER_TESTS] = {\n")
        for i, (_, ctx_len) in enumerate(sigver_ctx_arrays):
            f.write(f"    {ctx_len}")
            if i < len(sigver_ctx_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigVer messages array\n")
        f.write("static const uint8_t* const sigver_messages[NUM_SIGVER_TESTS] = {\n")
        for i, (msg_name, _) in enumerate(sigver_msg_arrays):
            f.write(f"    {msg_name}")
            if i < len(sigver_msg_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigVer public keys array\n")
        f.write("static const uint8_t* const sigver_pks[NUM_SIGVER_TESTS] = {\n")
        for i, pk_name in enumerate(sigver_pk_arrays):
            f.write(f"    {pk_name}")
            if i < len(sigver_pk_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigVer contexts array\n")
        f.write("static const uint8_t* const sigver_contexts[NUM_SIGVER_TESTS] = {\n")
        for i, (ctx_name, _) in enumerate(sigver_ctx_arrays):
            f.write(f"    {ctx_name}")
            if i < len(sigver_ctx_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("// SigVer signatures array\n")
        f.write("static const uint8_t* const sigver_signatures[NUM_SIGVER_TESTS] = {\n")
        for i, sig_name in enumerate(sigver_sig_arrays):
            f.write(f"    {sig_name}")
            if i < len(sigver_sig_arrays) - 1:
                f.write(",")
            f.write("\n")
        f.write("};\n\n")

        f.write("#endif // TEST_DATA_H\n")

    print(
        f"Generated test_data.h with {num_keygen} keyGen, {num_siggen} sigGen, {num_sigver} sigVer test cases"
    )


if __name__ == "__main__":
    main()
