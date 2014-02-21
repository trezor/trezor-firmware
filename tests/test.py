#!/usr/bin/python
'''

TODO:

* ApplySettings workflow, zistit cez Features ci sa zmeny aplikovali
x WipeDevice workflow, zistit cez Features ci to prebehlo
x LoadDevice workflow, zistit cez Features ci to prebehlo
x ResetDevice workflow

- zrejme v sucinnosti s inymi testami
  x ButtonRequest/ButtonAck workflow
  x PinMatrixRequest/PinMatrixAck workflow
  x PassphraseRequest/PassphraseAck workflow

* rozsirit test_sign.tx o viac transakcii (zlozitejsich)
    x fee over threshold
    x not enough funds
    x viac ako jeden vstup a jeden vystup
    x iny cointype ako 0

- chceme v tomto release(?)
  x SignMessage workflow
  x VerifyMessage workflow

* otestovat session handling (tento test bude zrejme failovat na RPi)
* Failure_NotInitialized
* Features reflects all variations of LoadDevice
* Maxfee settings
* Client requires OTP
* Client requires PIN

x Zero signature test

x test bip39, utf, passphrase
x Clear session on ChangePin
'''
