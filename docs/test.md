# 一、目前主要进行的测试内容（Trezor One编译与测试）

 - 以下操作在ubuntu-18.04.3-desktop-amd64和ubuntu 19.10 系统下测试通过
 - 除了clang format检查之外，主要是Emulator和Hardware的脚本测试
## 1.1 Trezor one 编译
__环境安装__
````
apt-get update
````
__安装git、make、wget__
````
sudo apt-get -y install git make wget
````
__安装protoc__
````
sudo apt-get -y install protobuf-compiler
````
__安装python__
````
sudo apt-get -y install python3-dev python3-pip
ln -s /usr/bin/python3 /usr/bin/python  //创建链接
pip3 install pipenv
````
__安装其他依赖库__
````
sudo apt-get install libsdl2-dev libsdl2-image-dev //emulator 依赖
````
__安装交叉编译工具arm-none-eabi-gcc__
- 官网地址
<https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads>
````
wget https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu-rm/9-2019q4/RC2.1/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
tar xjf gcc-arm-none-eabi-9-2019-q4-major-x86\_64-linux.tar.bz2
````
__添加工具链路径，按照自己的路径修改__
````
export PATH=\"\$PATH:/<font color=#FF0000 >your-dir</font>/gcc-arm-none-eabi-9-2019-q4-major/bin/\" \>\>\~/.bashrc
source \~/.bashrc
````
__下载Trezor源码__
````
git clone https://github.com/trezor/trezor-firmware.git
cd trezor-firmware/
pipenv install
cd legacy/
make vendor //下载其他依赖库
````
__编译设备bootloader和firmware__
````
make -C vendor/libopencm3 lib/stm32/f2 //编译stm32驱动库
make
make -C bootloader/ align
make -C vendor/nanopb/generator/proto
pipenv run make -C firmware/protob
pipenv run make -C firmware
````
__编译EMULATOR__
````
cd legacy
make clean
make -C firmware/ clean
export EMULATOR=1
make
make -C emulator
make -C vendor/nanopb/generator/proto
pipenv run make -C firmware/protob
pipenv run make -C firmware
````
__运行模拟器：__
````
firmware/trezor.elf
````
## 1.2 Trezor One Hardware Test
#### 1.2.1 生成使用的bin
生成使用的bin
````
cd legacy
make clean
make -C firmware/ clean
export MEMORY_PROTECT=0 EMULATOR=0 DEBUG_LINK=1
pipenv run ./script/cibuild
````
则可在leagcy目录下得到trezor.bin
#### 1.2.2 升级firmware
````
cd firmware
trezorctl firmware-update -f trezor.bin
````
#### 1.2.3 执行指令开始测试
````
cd ..
pipenv run script/test
````
## 1.3 Trezor One Emulator Test
#### 1.3.1 测试准备工作
- 安装pipenv
````
pip3 install pipenv
````
或使用国内源
````
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple
````
- 安装check
````
sudo apt-get install check
````
- 安装valgrind
````
sudo apt-get install valgrind
````
#### 1.3.2 Legacy (Trezor One) 测试
- 测试case路径：./legacy/script/
- 测试内容：对legacy Emulator的测试
- 以下测试中的多条指令在trezor-firmware根目录下依次执行
````
cd legacy
make clean
make -C firmware/ clean
export EMULATOR=1 DEBUG_LINK=1
pipenv run ./script/cibuild
pipenv run script/test
````
## 1.4 Test Result
- 323 passed, 136 skipped, 1 warning in 81.86s (0:01:21)
- 仿真器/硬件测试使用同样的测试case，仿真器用时1分多钟，硬件用时约25分钟

# 二、Trezor One/T 全部测试内容
## 2.0 测试准备工作
- 安装pipenv ````-> pip3 install pipenv````或使用国内源 ````-> pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple````
- 安装tox ````-> pip3 install tox````
- 安装check ````-> sudo apt-get install check````
- 安装valgrind ````-> sudo apt-get install valgrind````
- 关于emulator，在core目录下完成emulator的编译，在legacy目录下生成trezor.elf文件，检查是否可以顺利启动emulator
- 以下各个测试中的多条指令默认是在trezor-firmware根目录下依次执行

## 2.1 通用测试

#### 2.1.1 Python test
- 测试case路径：./python/tests/
- 测试case数量：58个
- 测试内容：./python/trezorlib中的部分功能
- 指令:
````
	-> cd python
	-> pipenv run tox
````

#### 2.1.2 Storage test
- 测试case路径：./storage/tests/
- 测试case数量：26个
- 测试内容：测试Trezor内部存储
- 指令:
````
    -> cd storage/tests
    -> pipenv run make build
    -> pipenv run make tests_all
````
	
#### 2.1.3 Crypto test
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

## 2.2 Legacy (Trezor One) 测试

#### 2.2.1 Emu test
- 测试case路径：./legacy/script/
- 测试case数量：317个
- 测试内容：对legacy Emulator的测试
- 指令:
````
    -> cd legacy
    -> export EMULATOR=1	
    -> pipenv run script/test
````

#### 2.2.2 Emu btconly test
- 测试case路径：./legacy/script/
- 测试case数量：199个
- 测试内容：对Emulator的测试
- 指令:
````
    -> cd legacy
    -> export EMULATOR=1 TREZOR_PYTEST_SKIP_ALTCOINS=1 BITCOIN_ONLY=1	
    -> pipenv run script/test
````

#### 2.2.3 Emu upgrade test:
- 测试case路径：./tests/upgrade_tests/
- 测试case数量：6个
- 测试内容：测试legacy Emulator固件版本升级
- 指令:
````
    -> tests/download_emulators.sh
    -> TREZOR_UPGRADE_TEST="legacy" pipenv run pytest tests/upgrade_tests
````
	
## 2.3 Core (Trezor T) 测试

#### 2.3.1 Unix unit test
- 测试case路径：./core/tests/
- 测试case数量：90个
- 测试内容：对core的功能测试
- 指令:
````
    -> cd core
    -> pipenv run make build_unix
    -> pipenv run make test
````

#### 2.3.2 Unix device test
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

#### 2.3.3 Unix btconly device test
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

#### 2.3.4 Unix monero test
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

#### 2.3.5 Unix u2f test
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

#### 2.3.6 Unix fido2 test
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

#### 2.3.7 Unix click test
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

#### 2.3.8 Unix upgrade test
- 测试case路径：./tests/upgrade_tests/
- 测试case数量：6个
- 测试内容：测试core Emulator固件版本升级
- 指令:
````
    -> tests/download_emulators.sh
    -> TREZOR_UPGRADE_TEST="core" pipenv run pytest tests/upgrade_tests
````

#### 2.3.9 Unix persistence test
- 测试case路径：./tests/persistence_tests/
- 测试case数量：3个
- 测试内容：测试当前在设备恢复中使用的持久性模式
- 指令:
````
    -> pipenv run pytest tests/persistence_tests
````

#### 2.3.10 Unix mypy test
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
