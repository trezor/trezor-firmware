# Proposed migration from mini-WARD to MVP

Public mini-WARD stores records on each Trezor, scoped to its passphrase wallet and application.

After unlock, the device reads the active wallet's records in their original application and
   subscope. Once the user enables replication, it checks each eligible destination against its
   trusted root and seals the value. The records stay local and they are marked with a sticky flag.
