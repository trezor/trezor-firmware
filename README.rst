python-trezor
=============

Client side implementation for Trezor-compatible Bitcoin hardware wallets.

See http://bitcointrezor.com for more information.

How to install (Windows)
------------------------
* Install Python 2.7 (http://python.org)
* Install Cython (Windows binaries on http://cython.org/#download)
* Install Microsoft Visual Studio 2008 Express
* Add "C:\Program Files (x86)\Microsoft Visual Studio 9.0" to system PATH
* Clone repository (using TortoiseGit) to local directory
* Run c:\python27\python.exe setup.py install (or develop)

How to install (Debian-Ubuntu)
------------------------------
* sudo apt-get install python-dev python-setuptools cython
* git clone https://github.com/trezor/python-trezor.git
* cd python-trezor
* python setup.py install (or develop)

Internal note:
--------------
* Clone cython-hidapi from github.com/trezor/cython-hidapi
* Go to cython-hidapi directory
* Run "git submodule init" in Git Bash (TortoiseGit)
* Run "git submodule update" in Git Bash (TortoiseGit)
