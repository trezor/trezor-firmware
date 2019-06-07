QT += core gui
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = gui
TEMPLATE = app

SOURCES += ../address.c
SOURCES += ../bip32.c
SOURCES += ../bip39.c
SOURCES += ../sha2.c
SOURCES += ../pbkdf2.c
SOURCES += ../hmac.c
SOURCES += ../rand.c
SOURCES += ../bignum.c
SOURCES += ../ecdsa.c
SOURCES += ../rfc6979.c
SOURCES += ../hmac_drbg.c
SOURCES += ../ripemd160.c
SOURCES += ../base58.c
SOURCES += ../secp256k1.c
SOURCES += ../nist256p1.c
SOURCES += ../curves.c
SOURCES += ../ed25519-donna/ed25519.c
SOURCES += mainwindow.cpp
SOURCES += main.cpp

HEADERS += mainwindow.h
HEADERS += ../bip32.h
HEADERS += ../bip39.h

FORMS += mainwindow.ui

INCLUDEPATH += ..
INCLUDEPATH += ../ed25519-donna
