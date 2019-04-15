# NEM

MAINTAINER = Tomas Susanka <tomas.susanka@satoshilabs.com>

AUTHOR = Tomas Susanka <tomas.susanka@satoshilabs.com>

REVIEWER = Jan Pochyla <jan.pochyla@satoshilabs.com>

ADVISORS = Grégory Saive, Saleem Rashid

-----

This implementation of NEM for Trezor Core is mostly based on the trezor-mcu C implementation by Saleem Rashid. The protobuf messages are heavily inspired by the [NEM NSI API](https://nemproject.github.io/).

You can read a lot about NEM in the [Technical Reference paper](https://nem.io/wp-content/themes/nem/files/NEM_techRef.pdf).

This app supports number of NEM services (transfers, mosaics, namespaces and multisig), also called _transactions_ as the general term. Each of those services is divided into corresponding folders. In those folders we use `serialize.py` for the transaction serialization and `layout.py` to display data and to require user interactions.

In this app we support the following:

### Mosaics

You can read more on mosaics [here](https://blog.nem.io/mosaics-and-namespaces-2/). Each mosaic has a name and lives under certain namespace, this identification _namespace.mosaic_ is unique in the network.

Trezor Core supports mosaic creation and changing the mosaic's supply.

### Namespaces

You can read more on namespaces at the [same link](https://blog.nem.io/mosaics-and-namespaces-2/). Namespace creation is supported.

### Transfers

There is a number of things the term _transfer_ may refer to:

##### Regular transfers

The traditional transfer of the native NEM coins – XEM.

##### Mosaic transfers

Except XEM you can also transfer mosaics. Mosaics are _attached_ to a regular transfer.

Each such attached mosaic has a `quantity` denoting the amount of such mosaic to be transferred. There is a catch though: the actual amount of the mosaic to be transferred isn't `quantity` but `mosaic.quantity * transfer.amount`. In other words, the quantity is multiplied by the `amount` field in transfer. This is most likely due to backwards compatibility where transfers with amount 0 where discarded.

You can also transfer XEM and mosaics at the same time. In that case you need to attach the nem.xem mosaic. From the user point of view Trezor shows this as a regular XEM transfer.

##### Importance transfer

Importance transfer is a special kind of transaction, which enables (or disables) delegated harvesting.

### Multisig

NEM supports multisig accounts. First you convert an account into a multisig and add cosignatories. After that any cosignatory can initiate a multisig transaction.

Multisig is a wrapper, so you can use any of the services mentioned above wrapped into a multisig transaction requiring n out of m signatures.

A common scenario to test out multisig with NanoWallet might be:

- Create a simple account without Trezor (account A)
- Create another account with Trezor One (account B)
- Convert A to a multisig with B as a cosigner
- Create another account with Trezor T (account C)
- Add C as a cosigner
- Try to send a transaction where B and C cosigns
