QT += core gui
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = gui
TEMPLATE = app

SOURCES += ../bip32.c ../bip39.c ../sha2.c ../pbkdf2.c ../hmac.c ../rand.c ../bignum.c ../ecdsa.c ../ripemd160.c ../base58.c ../secp256k1.c mainwindow.cpp main.cpp

HEADERS += mainwindow.h ../bip32.h ../bip39.h

FORMS += mainwindow.ui
