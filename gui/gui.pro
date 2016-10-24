QT += core gui
greaterThan(QT_MAJOR_VERSION, 4): QT += widgets

TARGET = gui
TEMPLATE = app

SOURCES += ../bip32.c
SOURCES += ../bip39.c
SOURCES += ../sha2.c
SOURCES += ../pbkdf2.c
SOURCES += ../hmac.c
SOURCES += ../rand.c
SOURCES += ../bignum.c
SOURCES += ../ecdsa.c
SOURCES += ../ripemd160.c
SOURCES += ../base58.c
SOURCES += ../secp256k1.c
SOURCES += ../nist256p1.c
SOURCES += ../curves.c
SOURCES += ../curve25519-donna/curve25519-donna.c
SOURCES += ../ed25519-donna/ed25519.c
SOURCES += mainwindow.cpp
SOURCES += main.cpp

HEADERS += mainwindow.h
HEADERS += ../bip32.h
HEADERS += ../bip39.h

FORMS += mainwindow.ui

INCLUDEPATH += ..
INCLUDEPATH += ../curve25519-donna
INCLUDEPATH += ../ed25519-donna

DEFINES += ED25519_CUSTOMRANDOM=1
DEFINES += ED25519_CUSTOMHASH=1
