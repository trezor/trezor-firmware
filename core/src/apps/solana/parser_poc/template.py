templates = {
    "parameters": [
        {
            "name": "u32",
            "family": "basic"
        },{
            "name": "i32",
            "family": "basic"
        },{
            "name": "u64",
            "family": "basic"
        },{
            "name": "i64",
            "family": "basic"
        },{
            "name": "String",
            "family": "basic"
        },{
            "name": "Pubkey",
            "family": "basic"
        },{
            "name": "StakeAuthorize",
            "family": "enum",
            "fields": [
                {
                    "name": "Staker",
                    "value": 0
                },{
                    "name": "Withdrawer",
                    "value": 1
                }
            ]
        },{
            "name": "Authorized",
            "family": "struct",
            "fields": [
                {
                    "name": "staker",
                    "type": "Pubkey",
                    "optional": False
                }, {
                    "name": "withdrawer",
                    "type": "Pubkey",
                    "optional": False
                }
            ]
        },{
            "name": "Lockup",
            "family": "struct",
            "fields": [
                {
                    "name": "unix_timestamp",
                    "type": "i64",
                    "optional": False
                }, {
                    "name": "epoch",
                    "type": "u64",
                    "optional": False
                }, {
                    "name": "custodian",
                    "type": "Pubkey",
                    "optional": False
                }
            ]
        },{
            "name": "LockupArgs",
            "family": "struct",
            "fields": [
                {
                    "name": "unix_timestamp",
                    "type": "i64",
                    "optional": True
                }, {
                    "name": "epoch",
                    "type": "u64",
                    "optional": True
                }, {
                    "name": "custodian",
                    "type": "Pubkey",
                    "optional": True
                }
            ]
        },{
            "name": "AuthorizeWithSeedArgs",
            "family": "struct",
            "fields": [
                {
                    "name": "new_authorized_pubkey",
                    "type": "Pubkey",
                    "optional": False
                },{
                    "name": "stake_authorize",
                    "type": "StakeAuthorize",
                    "optional": False
                },{
                    "name": "authority_seed",
                    "type": "String",
                    "optional": False
                },{
                    "name": "authority_owner",
                    "type": "Pubkey",
                    "optional": False
                }
            ]
        },{
            "name": "AuthorizeCheckedWithSeedArgs",
            "family": "struct",
            "fields": [
                {
                    "name": "stake_authorize",
                    "type": "StakeAuthorize",
                    "optional": False
                },{
                    "name": "authority_seed",
                    "type": "String",
                    "optional": False
                },{
                    "name": "authority_owner",
                    "type": "Pubkey",
                    "optional": False
                }
            ]
        },{
            "name": "LockupCheckedArgs",
            "family": "struct",
            "fields": [
                {
                    "name": "unix_timestamp",
                    "type": "i64",
                    "optional": True
                },{
                    "name": "epoch",
                    "type": "u64",
                    "optional": True
                }
            ]
        }
    ],
    "programs": [
        {
            "id": "0000000000000000000000000000000000000000000000000000000000000000",
            "name": "System program",
            "instructions": [
                {
                    "id": 0,
                    "name": "CreateAccount",
                    "parameters": [
                        {
                            "name": "lamports",
                            "type": "u64"
                        },{
                            "name": "space",
                            "type": "u64"
                        },{
                            "name": "owner",
                            "type": "Pubkey"
                        }
                    ],
                    "references": [
                        {
                            "name": "Funding account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "New account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 1,
                    "name": "Assign",
                    "parameters": [
                        {
                            "name": "owner",
                            "type": "Pubkey"
                        }
                    ],
                    "references": [
                        {
                            "name": "Assigned account public key",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 2,
                    "name": "Transfer",
                    "parameters": [
                        {
                            "name": "lamports",
                            "type": "u64"
                        }
                    ],
                    "references": [
                        {
                            "name": "Funding account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Recipient account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        }
                    ]
                },{
                    "id": 3,
                    "name": "CreateAccountWithSeed",
                    "parameters": [
                        {
                            "name": "base",
                            "type": "Pubkey"
                        },{
                            "name": "seed",
                            "type": "String"
                        },
                        {
                            "name": "lamports",
                            "type": "u64"
                        },{
                            "name": "space",
                            "type": "u64"
                        },{
                            "name": "owner",
                            "type": "Pubkey"
                        }
                    ],
                    "references": [
                        {
                            "name": "Funding account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Created account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Base account",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 8,
                    "name": "Allocate",
                    "parameters": [
                        {
                            "name": "space",
                            "type": "u64"
                        }
                    ],
                    "references": [
                        {
                            "name": "New account",
                            "access": "w",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 9,
                    "name": "AllocateWithSeed",
                    "parameters": [
                        {
                            "name": "base",
                            "type": "Pubkey"
                        },{
                            "name": "seed",
                            "type": "String"
                        },{
                            "name": "space",
                            "type": "u64"
                        },{
                            "name": "owner",
                            "type": "Pubkey"
                        }
                    ],
                    "references": [
                        {
                            "name": "Allocated account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Base account",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 10,
                    "name": "AssignWithSeed",
                    "parameters": [
                        {
                            "name": "base",
                            "type": "Pubkey"
                        },{
                            "name": "seed",
                            "type": "String"
                        },{
                            "name": "owner",
                            "type": "Pubkey"
                        }
                    ],
                    "references": [
                        {
                            "name": "Assigned account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Base account",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                }
            ]
        }, {
            "id": "06a1d8179137542a983437bdfe2a7ab2557f535c8a78722b68a49dc000000000",
            "name": "Stake program",
            "instructions": [
                {
                    "id": 0,
                    "name": "Initialize",
                    "parameters": [
                        {
                            "name": "authorized",
                            "type": "Authorized"
                        },{
                            "name": "lockup",
                            "type": "Lockup"
                        }
                    ],
                    "references": [
                        {
                            "name": "Uninitialized stake account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Rent sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        }
                    ]
                },{
                    "id": 1,
                    "name": "Authorize",
                    "parameters": [
                        {
                            "name": "pubkey",
                            "type": "Pubkey"
                        },{
                            "name": "stakeauthorize",
                            "type": "StakeAuthorize"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account to be updated",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "The stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Lockup authority",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 2,
                    "name": "DelegateStake",
                    "parameters": [],
                    "references": [
                        {
                            "name": "Initialized stake account to be delegated",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Vote account to which this stake will be delegated",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake history sysvar that carries stake warmup/cooldown history",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Address of config account that carries stake config",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 3,
                    "name": "Split",
                    "parameters": [
                        {
                            "name": "lamports",
                            "type": "u64"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account to be split; must be in the Initialized or Stake state",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Uninitialized stake account that will take the split-off amount",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 4,
                    "name": "Withdraw",
                    "parameters": [
                        {
                            "name": "lamports",
                            "type": "u64"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account from which to withdraw",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Recipient account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake history sysvar that carries stake warmup/cooldown history",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Lockup authority, if before lockup expiration",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 5,
                    "name": "Deactivate",
                    "parameters": [ ],
                    "references": [
                        {
                            "name": "Delegated stake account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 6,
                    "name": "SetLockup",
                    "parameters": [
                        {
                            "name": "lockupargs",
                            "type": "LockupArgs"
                        }
                    ],
                    "references": [
                        {
                            "name": "Initialized stake account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Lockup authority or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 7,
                    "name": "Merge",
                    "parameters": [ ],
                    "references": [
                        {
                            "name": "Destination stake account for the merge",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Source stake account for to merge. This account will be drained",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake history sysvar that carries stake warmup/cooldown history",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Stake authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 8,
                    "name": "AuthorizeWithSeed",
                    "parameters": [
                        {
                            "name": "authorizewithseedargs",
                            "type": "AuthorizeWithSeedArgs"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account to be updated",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Base key of stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Lockup authority, if updating StakeAuthorize::Withdrawer before lockup expiration",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 9,
                    "name": "InitializeChecked",
                    "parameters": [ ],
                    "references": [
                        {
                            "name": "Uninitialized stake account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Rent sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "The stake authority",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "The withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        }
                    ]
                },{
                    "id": 10,
                    "name": "AuthorizeChecked",
                    "parameters": [
                        {
                            "name": "stakeauthorize",
                            "type": "StakeAuthorize"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account to be updated",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "The stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "The new stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Lockup authority, if updating StakeAuthorize::Withdrawer before lockup expiration",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 11,
                    "name": "AuthorizeCheckedWithSeed",
                    "parameters": [
                        {
                            "name": "authorizecheckedwithseedargs",
                            "type": "AuthorizeCheckedWithSeedArgs"
                        }
                    ],
                    "references": [
                        {
                            "name": "Stake account to be updated",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Base key of stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Clock sysvar",
                            "access": "",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "The new stake or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "Lockup authority, if updating StakeAuthorize::Withdrawer before lockup expiration",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                },{
                    "id": 12,
                    "name": "SetLockupChecked",
                    "parameters": [
                        {
                            "name": "lockupcheckedargs",
                            "type": "LockupCheckedArgs"
                        }
                    ],
                    "references": [
                        {
                            "name": "Initialized stake account",
                            "access": "w",
                            "signer": False,
                            "optional": False
                        },{
                            "name": "Lockup authority or withdraw authority",
                            "access": "",
                            "signer": True,
                            "optional": False
                        },{
                            "name": "New lockup authority",
                            "access": "",
                            "signer": True,
                            "optional": True
                        }
                    ]
                }
            ]
        }, {
            "id": "0306466fe5211732ffecadba72c39be7bc8ce5bbc5f7126b2c439b3a40000000",
            "name": "Compute budget program",
            "instructions": [
                {
                    "id": 1,
                    "name": "RequestHeapFrame",
                    "parameters": [
                        {
                            "name": "bytes",
                            "type": "u32"
                        }
                    ],
                    "references": [ ]
                },{
                    "id": 2,
                    "name": "SetComputeUnitLimit",
                    "parameters": [
                        {
                            "name": "units",
                            "type": "u32"
                        }
                    ],
                    "references": [ ]
                },{
                    "id": 3,
                    "name": "SetComputeUnitPrice",
                    "parameters": [
                        {
                            "name": "lamports",
                            "type": "u64"
                        }
                    ],
                    "references": [ ]
                }
            ]
        }, {
            "id": "06ddf6e1d765a193d9cbe146ceeb79ac1cb485ed5f5b37913a8cf5857eff00a9",
            "name": "Token program",
            "instructions": []
        }
    ]
}
