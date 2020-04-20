# trezor one签名固件生成及下载方法

环境安装以及固件生成，请参考[trezor编译过程.md](./trezor编译过程.md)

__签名机制__

​	trezor one生成的未签名固件中前1024字节未固件的信息头，定义如下：

typedef *struct* {

 	*uint32_t* magic;

 	*uint32_t* hdrlen;

 	*uint32_t* expiry;

 	*uint32_t* codelen;

 	*uint32_t* version;

 	*uint32_t* fix_version;

 	*uint8_t* __reserved1[8];

 	*uint8_t* hashes[512];

 	 *uint8_t* sig1[64];//签名值1

 	*uint8_t* sig2[64];//签名值2

 	*uint8_t* sig3[64];//签名值3

 	*uint8_t* sigindex1;//签名索引值1

 	*uint8_t* sigindex2;//签名索引值2

 	*uint8_t* sigindex3;//签名索引值3

 	*uint8_t* __reserved2[220];

 	*uint8_t* __sigmask;

 	*uint8_t* __sig[64];

} __attribute__((packed)) image_header;

​	trezor的固件使用了ECC算法签名固件，使用私钥对该文件头sha256哈希值签名。厂商生成5组签名的密钥，固件内固化5组公钥，发布固件时选择其中的三组对固件进行签名。固件会根据文件头中的签名索引值找到对应公钥，然后验证对应的签名，必须3组签名全部验签通过，才认为该固件合法。trezor 使用python实现生成密钥对以及签名固件，该文件位于/legacy/bootloader/firmware_sign.py。进入/legacy/bootloader目录，在当前目录下执行操作。

__生成签名密钥对__

执行如下：

- python3 firmware_sign.py -g

返回如下：

PRIVATE KEY (SECEXP):
79ee6604dfb43d6f8324548b00ec38505f2eda275d4dfb80cf8ffef716b239c7

PRIVATE KEY (PEM):
b'-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIHnuZgTftD1vgyRUiwDsOFBfLtonXU37gM+P/vcWsjnHoAcGBSuBBAAK\noUQDQgAEC6qXNQRc5WXcfhYJClSw/eHgO4ojkQPNEC7fJLgSs25hrvuqyU31K3ny\n/glBF49R6SZ+Wd+v7rLwzxy7We7plw==\n-----END EC PRIVATE KEY-----\n'
PUBLIC KEY:
040baa9735045ce565dc7e16090a54b0fde1e03b8a239103cd102edf24b812b36e61aefbaac94df52b79f2fe0941178f51e9267e59dfafeeb2f0cf1cbb59eee997

生成的私钥有两种格式，将生成的PRIVATE KEY(SECEXP)私钥保存。或者将RIVATE KEY (PEM):中b'<font color=#FF0000 >-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIHnuZgTftD1vgyRUiwDsOFBfLtonXU37gM+P/vcWsjnHoAcGBSuBBAAK\noUQDQgAEC6qXNQRc5WXcfhYJClSw/eHgO4ojkQPNEC7fJLgSs25hrvuqyU31K3ny\n/glBF49R6SZ+Wd+v7rLwzxy7We7plw==\n-----END EC PRIVATE KEY-----\n</font>' 保存，注意要将其中\n换行符替换掉。

同步PUBLIC KEY到固件和firmware_sign.py的pubkeys数组之中。

重复以上操作5次，生成5组新的密钥对。

__签名固件__

使用SECEXP格式的私钥签名

- python3 firmware_sign.py -s -f <font color=#FF0000 >your-firmware.bin</font> 

  按提示输入要签名的序号，回车确认，然后粘贴保存的SECEXP格式私钥，回车确认即可。

  示例如下：

  $ python3 firmware_sign.py -s -f trezor.bin
  Firmware size 519224 bytes
  Firmware fingerprint: 9fc9a5faa9142e7641abc9863771b21aadea0b1610867eae47207a495c241289
  Slot #1 is empty
  Slot #2 is empty
  Slot #3 is empty
  HASHES OK
  <font color=#FF0000 >Enter signature slot (1-3): 1</font> 
  Paste SECEXP (in hex) and press Enter:
  <font color=#FF0000 >(blank private key removes the signature on given index)
  79ee6604dfb43d6f8324548b00ec38505f2eda275d4dfb80cf8ffef716b239c7</font> 
  Firmware fingerprint: 9fc9a5faa9142e7641abc9863771b21aadea0b1610867eae47207a495c241289
  Slot #1 signature: VALID f916ff6350ac68ca05b2d3cde12a95a31d6cd4e7181a417150b3b8fd59e1dc2549959e4ade375ca388bcbbfb245adaf60bd3f541ce84974b98c9b0a66b7de15f
  Slot #2 is empty
  Slot #3 is empty
  HASHES OK

使用pem私钥签名

- python3 firmware_sign.py -s -f <font color=#FF0000 >your-firmware.bin</font> -p 

  示例如下：

  $ python3 firmware_sign.py -s -f trezor.bin -p
  Firmware size 519224 bytes
  Firmware fingerprint: 9fc9a5faa9142e7641abc9863771b21aadea0b1610867eae47207a495c241289
  Slot #1 signature: VALID f916ff6350ac68ca05b2d3cde12a95a31d6cd4e7181a417150b3b8fd59e1dc2549959e4ade375ca388bcbbfb245adaf60bd3f541ce84974b98c9b0a66b7de15f
  Slot #2 is empty
  Slot #3 is empty
  HASHES OK
  Enter signature slot (1-3): 2
  Paste ECDSA private key in PEM format and press Enter:
  (blank private key removes the signature on given index)
  -----BEGIN EC PRIVATE KEY-----
  MHQCAQEEIHnuZgTftD1vgyRUiwDsOFBfLtonXU37gM+P/vcWsjnHoAcGBSuBBAAK
  oUQDQgAEC6qXNQRc5WXcfhYJClSw/eHgO4ojkQPNEC7fJLgSs25hrvuqyU31K3ny
  /glBF49R6SZ+Wd+v7rLwzxy7We7plw==
  -----END EC PRIVATE KEY-----

  Firmware fingerprint: 9fc9a5faa9142e7641abc9863771b21aadea0b1610867eae47207a495c241289
  Slot #1 signature: VALID f916ff6350ac68ca05b2d3cde12a95a31d6cd4e7181a417150b3b8fd59e1dc2549959e4ade375ca388bcbbfb245adaf60bd3f541ce84974b98c9b0a66b7de15f
  Slot #2 signature: DUPLICATE f916ff6350ac68ca05b2d3cde12a95a31d6cd4e7181a417150b3b8fd59e1dc2549959e4ade375ca388bcbbfb245adaf60bd3f541ce84974b98c9b0a66b7de15f
  Slot #3 is empty
  HASHES OK

  使用三组密钥对固件签名完成后即可完成。

__固件下载__

​	使用trezor提供的trezorctl工具下载。windows下的安装过程参考官方教程<https://wiki.trezor.io/Installing_trezorctl_on_Windows>。

安装成功后，在固件目录下打开cmd窗口，确认设备在bootloader状态，执行如下指令下载固件:

- trezorctl firmware-update -f trezor.bin