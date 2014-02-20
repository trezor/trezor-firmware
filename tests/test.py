#!/usr/bin/python
'''

TODO:

* ApplySettings workflow, zistit cez Features ci sa zmeny aplikovali
* WipeDevice workflow, zistit cez Features ci to prebehlo
* LoadDevice workflow, zistit cez Features ci to prebehlo
x ResetDevice workflow

- zrejme v sucinnosti s inymi testami
  * ButtonRequest/ButtonAck workflow (vyvolat napr. pomocou GetEntropy, myslim ze ten GetEntropy vyzaduje PIN, ale ja by som to dal na button)
  * PinMatrixRequest/PinMatrixAck workflow (vyvolat napr. pomocou ChangePin)
  * PassphraseRequest/PassphraseAck workflow (vyvolat napr. pomocou GetAddress)

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

* test bip39, utf, passphrase
x Clear session on ChangePin
'''
