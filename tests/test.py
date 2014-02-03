#!/usr/bin/python
'''

TODO:

* ApplySettings workflow, zistit cez Features ci sa zmeny aplikovali
* WipeDevice workflow, zistit cez Features ci to prebehlo
* LoadDevice workflow, zistit cez Features ci to prebehlo
* ResetDevice workflow

- zrejme v sucinnosti s inymi testami
  * ButtonRequest/ButtonAck workflow (vyvolat napr. pomocou GetEntropy, myslim ze ten GetEntropy vyzaduje PIN, ale ja by som to dal na button)
  * PinMatrixRequest/PinMatrixAck workflow (vyvolat napr. pomocou ChangePin)
  * PassphraseRequest/PassphraseAck workflow (vyvolat napr. pomocou GetAddress)

* rozsirit test_sign.tx o viac transakcii (zlozitejsich)

- chceme v tomto release(?)
  * SignMessage workflow
  * VerifyMessage workflow

* otestovat session handling (tento test bude zrejme failovat na RPi)

* Features reflects all variations of LoadDevice
* Maxfee settings
* Client requires OTP
* Client requires PIN
'''
