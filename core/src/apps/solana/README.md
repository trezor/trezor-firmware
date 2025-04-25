# Solana

---


## Useful links

[Solana documentation](https://docs.solana.com/)

[Solana terminology](https://docs.solana.com/terminology#instruction)

[Transaction fee calculation](https://docs.solana.com/transaction_fees#prioritization-fee)

[System instructions](https://docs.rs/solana-program/latest/solana_program/system_instruction/enum.SystemInstruction.html)

[Stake instructions](https://docs.rs/solana-sdk/latest/solana_sdk/stake/instruction/enum.StakeInstruction.html)

[Token instructions](https://docs.rs/spl-token/latest/spl_token/instruction/index.html)

[Associated token instructions](https://docs.rs/spl-associated-token-account/latest/spl_associated_token_account/instruction/index.html)

[Memo program](https://spl.solana.com/memo)


## Transactions on Solana

On the Solana blockchain, program execution begins with a transaction being submitted to the cluster. With each transaction consisting of one or many instructions, the runtime will process each of the instructions contained within the transaction, in order, and atomically. If any part of an instruction fails, then the entire transaction will fail.

A transaction consists of three parts:
- one or more instructions
- an array of accounts to read or write from
- one or more signatures

An instruction is the smallest execution logic on Solana. Instructions are basically a call to update the global Solana state. Instructions invoke programs that make calls to the Solana runtime to update the state (for example, calling the token program to transfer tokens from your account to another account).


### Transaction format

A transaction contains a compact-array of signatures, followed by a message. Each item in the signatures array is a digital signature of the given message. The Solana runtime verifies that the number of signatures matches the number in the first 8 bits of the message header. It also verifies that each signature was signed by the private key corresponding to the public key at the same index in the message's account addresses array.

### Signature format

Each digital signature is in the ed25519 binary format and consumes 64 bytes.

### Compact array format

A compact-array is serialized as the array length, followed by each array item. The array length is a special multi-byte encoding called compact-u16.

### Compact-u16 format

This is actually identical to protobuf varint except limited to 16-bit numbers.
A compact-u16 is a multi-byte encoding of 16 bits. The first byte contains the lower 7 bits of the value in its lower 7 bits. If the value is above 0x7f, the high bit is set and the next 7 bits of the value are placed into the lower 7 bits of a second byte. If the value is above 0x3fff, the high bit is set and the remaining 2 bits of the value are placed into the lower 2 bits of a third byte.


### Message format

A message contains a header, followed by a compact-array of account addresses, followed by a recent blockhash, followed by a compact-array of instructions.

```
+----------------------------------------------------------------------------+
|                                Message format                              |
+-------------+------------------------+-----------------+-------------------+
| header (3B) | account addresses (CA) | blockhash (32B) | instructions (CA) |
+-------------+------------------------+-----------------+-------------------+
```

### Message Header Format

The message header contains three unsigned 8-bit values. The first value is the number of required signatures in the containing transaction. The second value is the number of those corresponding account addresses that are read-only. The third value in the message header is the number of read-only account addresses not requiring signatures.

```
+--------------------------------------------------------------------------------------+
|                                     Header format                                    |
+--------------------------+---------------------------------+-------------------------+
| required signatures (1B) | read-only signing accounts (1B) | read-only accounts (1B) |
+--------------------------+---------------------------------+-------------------------+
```

### Account Addresses Format

The addresses that require signatures appear at the beginning of the account address array, with addresses requesting read-write access first, and read-only accounts following. The addresses that do not require signatures follow the addresses that do, again with read-write accounts first and read-only accounts following.

```
+-------------------------------------------------------------------------+
|                             Account addresses                           |
+---------------------------+-------------------- ... --------------------+
| Number of accounts (C-16) | account_1 (32B)    .....    account_n (32B) |
+---------------------------+-------------------- ... --------------------+
```

### Blockhash Format

A blockhash contains a 32-byte SHA-256 hash. It is used to indicate when a client last observed the ledger. Validators will reject transactions when the blockhash is too old.

### Instruction Format

An instruction contains a program id index, followed by a compact-array of account address indexes, followed by a compact-array of opaque 8-bit data. The program id index is used to identify an on-chain program that can interpret the opaque data. The program id index is an unsigned 8-bit index to an account address in the message's array of account addresses. The account address indexes are each an unsigned 8-bit index into that same array.

```
+------------------------------------------------------------------------------+
|                              Instruction format                              |
+-----------------------+------------------------------+-----------------------+
| Program id index (1B) | Account address indexes (CA) | Instruction data (CA) |
+-----------------------+------------------------------+-----------------------+
```


### Program Id
The instruction's program id specifies which program will process this instruction. The program's account's owner specifies which loader should be used to load and execute the program, and the data contains information about how the runtime should execute the program.

### Accounts
The accounts referenced by an instruction represent on-chain state and serve as both the inputs and outputs of a program.

### Instruction data
Each instruction carries a general purpose byte array that is passed to the program along with the accounts. The contents of the instruction data is program specific and typically used to convey what operations the program should perform, and any additional information those operations may need above and beyond what the accounts contain.


## Versioned transactions

Messages transmitted to Solana validators must not exceed the IPv6 MTU size to ensure fast and reliable network transmission of cluster info over UDP. Solana's networking stack uses a conservative MTU size of 1280 bytes which, after accounting for headers, leaves 1232 bytes for packet data like serialized transactions. Since each transaction must list all accounts the current cap is about 35 accounts after accounting for signatures and other transaction metadata. To resolve this problem a new transaction format is introduced to make use of on-chain address lookup tables to efficiently load more accounts in a single transaction.

The new transaction format must be distinguished from the legacy transaction format. Legacy transactions can fit at most 19 signatures (64-bytes each) but the message header encodes required_signers_count as a u8. Since the upper bit of the u8 will never be set for a valid transaction, we can enable it to denote whether a transaction should be decoded with the versioned format or not.

```
+-------------------------------------------------------------------------------+
|                             Versioned message format                          |
+-------------------------------+-----------------------+----------------+------+
| Versioned flag + version (1B) | Legacy message format | # OF LUTS (1B) | LUTs |
+-------------------------------+-----------------------+----------------+------+
```

### LUT format
```
+-----------------------------------------------------------------------------------------------------------+
|                                                Look up table                                              |
+---------------+---------------------------+-----------------+---------------------------+-----------------+
| Account (32B) | # of rw acc. indexes (1B) | rw acc. indexes | # of ro acc. indexes (1B) | ro acc. indexes |
+---------------+---------------------------+-----------------+---------------------------+-----------------+
```

## Solana app basic concept and software architecture

The software architecture designed for signing Solana messages utilizes a system of parser functions to construct objects from various classes. At its core is the `Transaction` class, serving as the higher-level entity responsible for encapsulating all transaction-related information. This includes a list of instructions derived from the `Instruction` class. This structure can seamlessly handle both legacy and versioned transactions.

To generate these instructions, a builder function called `get_instruction` comes into play. It takes as input the program ID, instruction id, instruction accounts, as well as the instruction data. Using this information, it crafts the appropriate `Instruction` object, effectively parsing the instruction data. However, in cases where the instruction or program is unknown, the builder function returns a generic `Instruction` object devoid of parsed data. In such instances, the process of blind signing is employed, allowing for the transaction to proceed without fully understanding the content, offering flexibility and adaptability in transaction processing.

In this Solana message signing software architecture, a template file named `programs.json` plays a crucial role in generating the instruction builder. The template file acts as a structured blueprint containing essential information about various Solana programs, including their respective program IDs, parameter types, and expected account templates.

The process of generating the instruction builder involves the utilization of a [mako](https://www.makotemplates.org/) template engine, which is responsible for dynamically populating and transforming the data from `programs.json` into a Python script. This script, referred to as `instructions.py,` becomes an integral part of the software as it contains the instruction builder function, facilitating the creation of `Instruction` objects based on the content and structure defined in the template file.

The `programs.json` template file acts as a central reference point, allowing developers to easily update and adapt the software's behavior without modifying the core codebase. By editing the `programs.json` file and regenerating the `instructions.py` script, developers can efficiently accommodate new Solana programs, modify existing ones, or make adjustments to account templates and parameter types, all while maintaining a clean separation between configuration and code logic.

This approach enhances the software's flexibility, making it straightforward to stay up-to-date with changes in the Solana ecosystem, and ensures that the instruction builder remains a dynamic and adaptable component of the architecture.


The `programs.json` file serves as a structured configuration file in the Solana message signing software architecture. It contains essential information about various Solana programs, each described in a structured manner. The file has the following structure:

- `programs`: An array that lists the different Solana programs and their details.
  - `id`: A unique identifier (program ID) for a specific Solana program, represented as base58 encoded string.
  - `name`: The name of the program, providing a human-readable label for the program.
  - `instruction_id_length`: Specifies the length of the instruction ID, used for parsing.
  - `instructions`: An array of instructions associated with the Solana program.
    - `id`: A numeric identifier for the instruction derived from the Rust implementation of the corresponding program.
    - `name`: The name of the instruction, providing a human-readable label.
    - `is_multisig`: A boolean indicating whether the instruction is a multisig instruction.
    - `is_deprecated_warning`: Optional, contains a warning message when the instruction is deprecated
    - `parameters`: Describes the parameters required for this instruction.
      - `name`: The parameter name.
      - `type`: The data type of the parameter, such as `u64` for 64-bit unsigned integers.
      - `optional`: Indicates whether the parameter is optional.
      - `args`: An optional dict of arguments for the formatter, see explanation below.
    - `references`: An array of account names that are used by the instruction.
    - `references_required`: The number of references required by the instruction. If more `references` are specified than required, the extra ones are optional, and may or may not be present in the transaction.
    - `ui_properties`: Contains user interface-related information for this instruction.
      - `account`: Reference to one account in the references list identified by its `name`
      - `parameter`: Reference to one parameter in the parameters list identified by its `name`
      - `display_name`: A human-readable label for the parameter or account, suitable for user interfaces.
      - `default_value_to_hide`: Optional. If this value is found in the account / parameter, the UI property will not be shown for confirmation. This is useful when the default value is considered safe. In particular, if the value of the property is a public key, and the special word `"signer"` is used for `default_value_to_hide`, the UI property will be hidden if the public key matches the Trezor's account.

Certain types of parameters, specified in `types` dict of the `programs.json` file, have special formatting capabilities.
In particular, the type `token_amount` is a regular `u64` type, but the formatter function accepts additional parameters:
* a special parameter `#definitions` that will be pre-set to the loadable definitions manager
* a parameter `decimals` that specifies the number of decimals of the token
* a parameter `mint` that specifies the mint address of the token

The corresponding parameter of `token_amount` type must provide the `args` dict, mapping the `decimals` and `mint` arguments to fields of the instruction. E.g.: in a hypothetical Swap instruction, you would have two parameters of `token_amount` type. On the first one, the `args` dict would map `decimals` to the `from_amount_decimals` field and `mint` to the `from_amount_mint` field. On the second one, the mapping would go to the `to_amount_decimals` and `to_amount_mint` fields.


After the message has been parsed, the Solana app utilizes the Trezor UI engine to present all the necessary information to the user for review and confirmation. If all the programs and instructions contained within the message are recognized and known, the software ensures that all the relevant information is displayed to the user. Each piece of data, including parameters, account references, and instruction details, is presented on the Trezor's user interface for user confirmation.

However, if the instruction or the program is unknown to the software, a cautionary message is presented to the user. This warning message indicates that the transaction includes unknown instruction(s). In such cases, while the user can still examine all referenced accounts and instruction data, the specific meaning and implications of these properties are not resolved. Therefore, the user is advised to exercise extra caution when proceeding with the transaction.

Assuming that all the information presented to the user is confirmed and accepted, the final screen provides critical details, including the address derivation path, the signer address, the transaction fee to be paid by the user, and the recent block hash. To complete the signing process, the user must confirm the information on this final screen. Upon confirmation, the Trezor device will sign the message, ensuring that the transaction is securely authorized by the user.

The presence of multisig instructions within the Token program adds an additional layer of complexity to the Solana message signing app. Multisig instructions involve owner accounts that are multisignature accounts, which means they require multiple signatures to authorize a transaction. In the context of Solana, this impacts the determination of the transaction fee since the fee is calculated based on the number of required signatures.

