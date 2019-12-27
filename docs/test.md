
# 0. 测试准备工作
- 安装pipenv ````-> pip3 install pipenv````或使用国内源 ````-> pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple````
- 安装tox ````-> pip3 install tox````
- 安装check ````-> sudo apt-get install check````
- 安装valgrind ````-> sudo apt-get install valgrind````
- 关于emulator，在core目录下完成emulator的编译，在legacy目录下生成trezor.elf文件，检查是否可以顺利启动emulator
- 以下各个测试中的多条指令默认是在trezor-firmware根目录下依次执行

# 1. 通用测试

## 1.1 Python test
- 测试case路径：./python/tests/
- 测试case数量：58个
- 测试内容：./python/trezorlib中的部分功能
- 指令:
````
	-> cd python
	-> pipenv run tox
````

## 1.2 Storage test
- 测试case路径：./storage/tests/
- 测试case数量：26个
- 测试内容：测试Trezor内部存储
- 指令:
````
    -> cd storage/tests
    -> pipenv run make build
    -> pipenv run make tests_all
````
	
## 1.3 Crypto test
- 测试case路径：./crypto/tests/
- 测试case数量：1898个
- 测试内容：测试加密算法
- 指令:
````
    -> cd crypto
    -> make
    -> ./tests/aestst
    -> ./tests/test_check
    -> ./tests/test_openssl 1000
    -> ITERS=10 pipenv run pytest tests
    -> CK_TIMEOUT_MULTIPLIER=20 valgrind -q --error-exitcode=1 ./tests/test_check
````

# 2. Legacy (Trezor One) 测试

## 2.1 Emu test
- 测试case路径：./legacy/script/
- 测试case数量：317个
- 测试内容：对legacy Emulator的测试
- 指令:
````
    -> cd legacy
    -> export EMULATOR=1	
    -> pipenv run script/test
````

## 2.2 Emu btconly test
- 测试case路径：./legacy/script/
- 测试case数量：199个
- 测试内容：对Emulator的测试
- 指令:
````
    -> cd legacy
    -> export EMULATOR=1 TREZOR_PYTEST_SKIP_ALTCOINS=1 BITCOIN_ONLY=1	
    -> pipenv run script/test
````

## 2.3 Emu upgrade test:
- 测试case路径：./tests/upgrade_tests/
- 测试case数量：6个
- 测试内容：测试legacy Emulator固件版本升级
- 指令:
````
    -> tests/download_emulators.sh
    -> TREZOR_UPGRADE_TEST="legacy" pipenv run pytest tests/upgrade_tests
````
	
# 3. Core (Trezor T) 测试

## 3.1 Unix unit test
- 测试case路径：./core/tests/
- 测试case数量：90个
- 测试内容：对core的功能测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test
````

## 3.2 Unix device test
- 测试case路径：./tests/device_tests/
- 测试case数量：388个
- 测试内容：对core device emualtor的测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test_emu
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}
````
- 备注：````${CI_PROJECT_DIR}````是想要存放log的目录，如/all/trezor-firmware就是放在了工程的根目录下

## 3.3 Unix btconly device test
- 测试case路径：./tests/device_tests/
- 测试case数量：201个
- 测试内容：对core device emualtor的测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> export TREZOR_PYTEST_SKIP_ALTCOINS=1
    -> pipenv run make test_emu
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}		
````

## 3.4 Unix monero test
- 测试case路径：./tests/device_tests/
- 测试case数量：389个
- 测试内容：对core device emualtor的测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test_emu_monero
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}	
````

## 3.5 Unix u2f test
- 测试case路径：./tests/fido_tests/u2f-tests-hid/
- 测试case数量：5个
- 测试内容：对U2F的测试
- 指令:
````
    -> make -C tests/fido_tests/u2f-tests-hid
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test_emu_u2f
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}
````

## 3.6 Unix fido2 test
- 测试case路径：./tests/fido_tests/
- 测试case数量：125个
- 测试内容：对fido2的测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test_emu_fido2
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}
````

## 3.7 Unix click test
- 测试case路径：./tests/click_tests/
- 测试case数量：5个
- 测试内容：能够模拟用户与屏幕的交互，需要使用设备或仿真器
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test_emu_click
    -> cp /var/tmp/trezor.log ${CI_PROJECT_DIR}
````

## 3.8 Unix upgrade test
- 测试case路径：./tests/upgrade_tests/
- 测试case数量：6个
- 测试内容：测试core Emulator固件版本升级
- 指令:
````
    -> tests/download_emulators.sh
    -> TREZOR_UPGRADE_TEST="core" pipenv run pytest tests/upgrade_tests
````

## 3.9 Unix persistence test
- 测试case路径：./tests/persistence_tests/
- 测试case数量：3个
- 测试内容：测试当前在设备恢复中使用的持久性模式
- 指令:
````
    -> pipenv run pytest tests/persistence_tests
````

## 3.10 Unix mypy test
- 测试case路径：./tests/click_tests/
- 测试case数量：1个
- 测试内容：对mypy的测试
- 指令:
````
    -> cd core
    -> pipenv run mypy --version
    -> pipenv run make res  # needed for clean mypy
    -> pipenv run make mypy
````
