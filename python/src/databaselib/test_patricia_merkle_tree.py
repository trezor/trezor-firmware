from patricia_merkle_trie import BranchNode, DigestNode, PatriciaMerkleTrie, ValueNode


def test_find_path():
    tree = PatriciaMerkleTrie()
    assert tree.find_path(()) == ((), ())
    assert tree.find_path((0,)) == ((), (0,))
    assert tree.find_path((0, 1)) == ((), (0, 1))

    node1001 = ValueNode(prefix=(1, 0, 0, 1), value=b"1001")
    node0000 = ValueNode(prefix=(0,), value=b"0000")
    node0001 = ValueNode(prefix=(1,), value=b"0001")
    node000 = BranchNode(prefix=(0, 0, 0), children={0: node0000, 1: node0001})
    node = BranchNode(prefix=(), children={1: node1001, 0: node000})
    tree = PatriciaMerkleTrie(root=node)

    # assert tree.find_path(()) == ((), ()) # TODO: consider fixing find_path
    assert tree.find_path((1, 0, 0, 1)) == ((node, node1001), ())
    assert tree.find_path((0, 0, 0, 0)) == (
        (node, node000, node0000),
        (),
    )
    assert tree.find_path((0, 0, 0, 1)) == (
        (node, node000, node0001),
        (),
    )
    assert tree.find_path((1, 0, 1, 1)) == (
        (node, node1001),
        (1, 0, 1, 1),
    )


def test_search():
    tree = PatriciaMerkleTrie()
    assert tree.search(()) is None

    node1001 = ValueNode(prefix=(1, 0, 0, 1), value=b"1001")
    node0000 = ValueNode(prefix=(0,), value=b"0000")
    node0001 = ValueNode(prefix=(1,), value=b"0001")
    node000 = BranchNode(prefix=(0, 0, 0), children={0: node0000, 1: node0001})
    node = BranchNode(prefix=(), children={1: node1001, 0: node000})
    tree = PatriciaMerkleTrie(root=node)

    assert tree.search((1, 0, 0, 1)) == b"1001"
    assert tree.search((1, 0, 0, 0)) is None


def test_insert():
    tree = PatriciaMerkleTrie()
    assert tree.insert((1, 0, 0, 1), b"1001") is True
    assert tree == PatriciaMerkleTrie(
        root=ValueNode(prefix=(1, 0, 0, 1), value=b"1001")
    )

    assert tree.insert((0, 0, 0, 0), b"0000") is True
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: ValueNode(prefix=(0, 0, 0, 0), value=b"0000"),
            },
        )
    )

    assert tree.insert((0, 0, 0, 1), b"0001") is True
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )


def test_delete():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    assert tree.delete((1, 1, 1, 1)) is False
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    assert tree.delete((0, 0, 0, 1)) is True
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: ValueNode(prefix=(0, 0, 0, 0), value=b"0000"),
            },
        )
    )

    assert tree.delete((0, 0, 0, 0)) is True
    assert tree == PatriciaMerkleTrie(
        root=ValueNode(prefix=(1, 0, 0, 1), value=b"1001")
    )

    assert tree.delete((1, 0, 0, 1)) is True
    assert tree == PatriciaMerkleTrie(root=None)

    assert tree.delete(()) is False


def test_modify():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    tree.modify((1, 0, 0, 1), b"1002")
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1002"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    tree.modify((1, 0, 0, 1), None)
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(
                0,
                0,
                0,
            ),
            children={
                0: ValueNode(
                    prefix=(0,),
                    value=b"0000",
                ),
                1: ValueNode(
                    prefix=(1,),
                    value=b"0001",
                ),
            },
        ),
    )

    tree.modify((1, 0, 0, 1), b"1001")
    assert tree == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )


def test_compute_digest():
    assert (
        PatriciaMerkleTrie().compute_digest().hex()
        == "0000000000000000000000000000000000000000000000000000000000000000"
    )

    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )
    assert (
        tree.compute_digest().hex()
        == "da79df6548466e266932a57f0f7148c33fff390ad660dfa31e3c617a20686691"
    )
    assert (
        tree.compute_digest(tree.root).hex()
        == "da79df6548466e266932a57f0f7148c33fff390ad660dfa31e3c617a20686691"
    )
    assert isinstance(tree.root, BranchNode)
    assert (
        tree.compute_digest(tree.root.children[1]).hex()
        == "779c66134a3d1b58fa5c3cf65bfc50e78d606a471b8351d1e2ab005f89744417"
    )
    assert (
        tree.compute_digest(tree.root.children[0]).hex()
        == "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
    )
    assert isinstance(tree.root.children[0], BranchNode)
    assert (
        tree.compute_digest(tree.root.children[0].children[0]).hex()
        == "48b2f127185a791b84a8c09de2edacdaf291f0b61354e49702184615748ab3f8"
    )
    assert (
        tree.compute_digest(tree.root.children[0].children[1]).hex()
        == "2e387e9c7b24328938f4273b5759dedcd12eb65178cfd3e148ac53efa0fa0cfe"
    )


def test_to_digest_tree():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    assert isinstance(tree.root, BranchNode)
    nodes = (tree.root, tree.root.children[1])
    assert tree.to_digest_tree(nodes) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: DigestNode(
                    digest=bytes.fromhex(
                        "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                    )
                ),
            },
        )
    )


def test_generate_membership_proof():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )
    assert tree.generate_membership_proof((1, 0, 0, 1)) == (
        PatriciaMerkleTrie(
            root=BranchNode(
                prefix=(),
                children={
                    1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                    0: DigestNode(
                        digest=bytes.fromhex(
                            "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                        )
                    ),
                },
            )
        ),
        b"1001",
    )

    assert tree.generate_membership_proof((0, 0, 0, 0)) == (
        PatriciaMerkleTrie(
            root=BranchNode(
                prefix=(),
                children={
                    1: DigestNode(
                        digest=bytes.fromhex(
                            "779c66134a3d1b58fa5c3cf65bfc50e78d606a471b8351d1e2ab005f89744417"
                        )
                    ),
                    0: BranchNode(
                        prefix=(0, 0, 0),
                        children={
                            0: ValueNode(prefix=(0,), value=b"0000"),
                            1: DigestNode(
                                digest=bytes.fromhex(
                                    "2e387e9c7b24328938f4273b5759dedcd12eb65178cfd3e148ac53efa0fa0cfe"
                                )
                            ),
                        },
                    ),
                },
            )
        ),
        b"0000",
    )

    assert tree.generate_membership_proof((1, 1, 1, 1)) == (
        PatriciaMerkleTrie(
            root=BranchNode(
                prefix=(),
                children={
                    1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                    0: DigestNode(
                        digest=bytes.fromhex(
                            "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                        )
                    ),
                },
            )
        ),
        None,
    )


def test_generate_insertion_proof():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    assert tree.generate_insertion_proof((1, 0, 1, 1)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: DigestNode(
                    digest=bytes.fromhex(
                        "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                    )
                ),
            },
        )
    )

    assert tree.generate_insertion_proof((0, 0, 1, 0)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: DigestNode(
                    digest=bytes.fromhex(
                        "779c66134a3d1b58fa5c3cf65bfc50e78d606a471b8351d1e2ab005f89744417"
                    )
                ),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: DigestNode(
                            digest=bytes.fromhex(
                                "2e387e9c7b24328938f4273b5759dedcd12eb65178cfd3e148ac53efa0fa0cfe"
                            )
                        ),
                    },
                ),
            },
        )
    )


def test_generate_deletion_proof():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )

    assert tree.generate_deletion_proof((1, 0, 0, 1)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: DigestNode(
                            digest=bytes.fromhex(
                                "48b2f127185a791b84a8c09de2edacdaf291f0b61354e49702184615748ab3f8"
                            )
                        ),
                        1: DigestNode(
                            digest=bytes.fromhex(
                                "2e387e9c7b24328938f4273b5759dedcd12eb65178cfd3e148ac53efa0fa0cfe"
                            )
                        ),
                    },
                ),
            },
        )
    )

    assert tree.generate_deletion_proof((0, 0, 0, 0)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: DigestNode(
                    digest=bytes.fromhex(
                        "779c66134a3d1b58fa5c3cf65bfc50e78d606a471b8351d1e2ab005f89744417"
                    )
                ),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )


def test_generate_change_proof():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )
    assert tree.generate_change_proof((1, 0, 0, 1)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: DigestNode(
                    digest=bytes.fromhex(
                        "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                    )
                ),
            },
        )
    )

    assert tree.generate_change_proof((0, 0, 0, 0)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: DigestNode(
                    digest=bytes.fromhex(
                        "779c66134a3d1b58fa5c3cf65bfc50e78d606a471b8351d1e2ab005f89744417"
                    )
                ),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: DigestNode(
                            digest=bytes.fromhex(
                                "2e387e9c7b24328938f4273b5759dedcd12eb65178cfd3e148ac53efa0fa0cfe"
                            )
                        ),
                    },
                ),
            },
        )
    )

    assert tree.generate_change_proof((1, 1, 1, 1)) == PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: DigestNode(
                    digest=bytes.fromhex(
                        "f0960dd0dd17c306cfaa0762d3135354ae778057c6b4303458cb2a8a7aead3e2"
                    )
                ),
            },
        )
    )


def test_generate_modification_proof():
    tree = PatriciaMerkleTrie(
        root=BranchNode(
            prefix=(),
            children={
                1: ValueNode(prefix=(1, 0, 0, 1), value=b"1001"),
                0: BranchNode(
                    prefix=(0, 0, 0),
                    children={
                        0: ValueNode(prefix=(0,), value=b"0000"),
                        1: ValueNode(prefix=(1,), value=b"0001"),
                    },
                ),
            },
        )
    )
    assert tree.generate_modification_proof(
        (0, 0, 0, 0), b""
    ) == tree.generate_change_proof((0, 0, 0, 0))
    assert tree.generate_modification_proof(
        (1, 0, 1, 1), b"1011"
    ) == tree.generate_insertion_proof((1, 0, 1, 1))
    assert tree.generate_modification_proof(
        (0, 0, 0, 1), None
    ) == tree.generate_deletion_proof((0, 0, 0, 1))


def test_insertion_deletion_proof():
    tree = PatriciaMerkleTrie()
    items = [
        ((1, 0, 1, 0), b"1010"),
        ((0, 1, 0, 0), b"0100"),
        ((0, 1, 1, 1), b"0111"),
        ((1, 0, 0, 0), b"1000"),
        ((1, 1, 1, 1), b"1111"),
        ((0, 1, 1, 0), b"0110"),
        ((1, 1, 0, 0), b"1100"),
        ((1, 1, 0, 1), b"1101"),
        ((0, 0, 0, 1), b"0001"),
        ((0, 0, 1, 1), b"0011"),
        ((1, 0, 0, 1), b"1001"),
        ((1, 1, 1, 0), b"1110"),
        ((0, 1, 0, 1), b"0101"),
    ]
    for key, value in items:
        proof = tree.generate_insertion_proof(key)
        assert tree.verify_proof(tree.compute_digest(), key, None)
        proof.insert(key, value)
        tree.insert(key, value)
        assert tree.verify_proof(tree.compute_digest(), key, value)
    for key, value in items:
        proof = tree.generate_deletion_proof(key)
        assert tree.verify_proof(tree.compute_digest(), key, value)
        proof.delete(key)
        tree.delete(key)
        assert tree.verify_proof(tree.compute_digest(), key, None)
