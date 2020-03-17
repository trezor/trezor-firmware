## 0. 概述
- 本文档的内容是使用BixinKEY测试第三方App的方法和结果
- 部分内容来自Trezor官方支持的加密钱包和APP，参见https://wiki.trezor.io/Apps

## 1. Trezor官方App
- 测试平台：网页或根据网页引导安装的客户端
#### 1.1 连接
- 将BixinKEY插入PC，操作系统不限
- 浏览器会自动弹出trezor网址(https://trezor.io/)，根据引导完成连接
- 如连接失败，可以安装网页(https://wallet.trezor.io/#/)下方的Trezor Bridge
- 设置testnet(https://wiki.trezor.io/Bitcoin_testnet)，即修改bitcoin服务器URL设置
#### 1.2 发币
- 根据左侧菜单创建账户/account，即钱包，此时余额为0
- 在上方的菜单中点击接收菜单，查看完整地址并在BixinKEY上再次检查及确认
- 向该地址发送测试比特币，收到测试币之后，账户的余额会增加，可以发币
- 在上方的菜单中点击发送菜单，输入地址金额并选择费率，点击发送按钮
- 在BixinKEY上确认交易信息并签名，收币地址收到测试币，发币成功
#### 1.3 结果
- 可以使用BixinKEY

## 2. Electrum
- 测试平台：客户端
- App下载地址：https://www.electrum.org/#download
#### 2.1 连接
- 我使用的是Linux版本，Installation from Python sources，便于后续修改py文件以修改测试网络
- 先打开仿真器，或插入BixinKEY
- 再打开客户端，建立钱包的流程中有一项是钱包类型，选择硬件钱包，在弹出窗口选择BixinKEY
- 如使用仿真器但没有找到仿真器，可以检查UDP端口占用情况并关闭占用端口21324的进程
- 通过修改服务器设置testnet/regtest
#### 2.2 发币
- 在发送页面，输入地址和金额
- 点击预览，在弹出的交易窗口点击签名
- 输入PIN码，在仿真器或BixinKEY上确认交易输出信息，点击广播
- 查看收币地址，确认已收币，发币成功
#### 2.3 结果
- 可以使用BixinKEY

## 3. Mycelium
- APP下载地址：https://play.google.com/store/apps/details?id=com.mycelium.testnetwallet&hl=zh-CN
- 参考流程：https://wiki.trezor.io/Apps:Mycelium
- 参考流程：https://blog.trezor.io/using-mycelium-to-watch-your-trezor-accounts-a836dce0b954
#### 3.1 连接
- Trezor只支持Mycelium的Android版本
- 如果使用testnet网络，需要安装testnet版本
- 安装Mycelium到Android手机，连接BixinKEY到手机
#### 3.2 发币
- 在账户页面，点击钥匙图标，新建账户
- 弹出页面选择导入Trezor HD Bitcoin账户下面的trezor图标，导入已有账户，如无账户则选择导入下一个未使用的账户
- 选择trezor账户，点击余额页面，可看到该账户的余额，使用测试网络发币至此账户，确保余额大于0
- 选择该页面的汇款按钮，进入发币页面
- 输入发币金额和地址，选择费率，点击汇款按钮
- 在BixinKEY上确认发币信息，检查收币地址的金额变化，确定发币成功
#### 3.3 结果
- 可以使用BixinKEY

## 4. Bitcoin core
- APP下载地址：https://bitcoin.org/en/download
- 使用Linux下的非安装包版本
#### 4.1 连接
- 安装Bitcoin core
- 在bitcoin.conf中配置参数
````
testnet=1
rpcuser=bitcoin
rpcpassword=secure
````
- 在bin目录下，linux输入命令./bitcoind，同步区块，需要较长时间
- 参考：https://github.com/cryptoadvance/specter-desktop
- 安装Specter-Desktop，linux输入命令
````
python3 -m pip install cryptoadvance.specter
python3 -m cryptoadvance.specter server
````
- 在浏览器中打开网址：http://127.0.0.1:25441/，可以进入UI界面，连接BixinKEY创建钱包及收币，如bitcoin testnet区块未同步，数额为0
#### 4.2 发币
- 点击左侧账户，再点击send，填写地址和金额，最后点击trezor按钮，确定用trezor来签名此次交易
- 弹出寻找硬件设备trezor的弹窗，如未找到，可将trezor拔下来再插上
- 确认交易，然后在BixinKEY上确认交易，如设置PIN则会有弹窗要求输入PIN
- 在收币地址收币成功
#### 4.3 结果
- 可以使用BixinKEY

## 5. Wasabi
- APP下载地址：https://wasabiwallet.io/#download
- github地址：https://github.com/zkSNACKs/WalletWasabi
#### 5.1 连接
- 安装成功后，插入BixinKEY，点击左侧Hardware wallet，再点击下方的search hardware wallet，会自动搜索到BixinKEY，并创建钱包
#### 5.2 发币
- 进入菜单tools/settings，修改网络为testnet，重启软件，点击receive菜单项，获取地址并向该地址发送测试币
- 点击send菜单项，输入金额和地址，即可发送测试币
#### 5.3 结果
- 可以使用BixinKEY

## 6. Exodus
- APP下载地址：https://www.exodus.io/download
#### 6.1 连接
- 不支持testnet
- 参考：https://wiki.trezor.io/Apps:Exodus
- 打开APP，插入BixinKEY，点击Connect Trezor，如果BixinKEY已经初始化则自动连接成功，否则需要做提示错误，初始化后才可连接
#### 6.2 发币
- 在弹出窗口选择账户的路径（自动分配还是自定义）
- 点击确定，进入创建账户页面，也要求校验PIN，输入PIN验证OK，进入钱包界面
#### 6.3 结果
- 未判定

## 7. Copay
- APP下载地址：https://github.com/bitpay/copay/releases
- Chrome插件下载（修改文件类型为rar解压缩）：https://www.gugeapps.net/webstore/detail/copay/cnidaodnidkbaplmghlelgikaiejfhja#download
#### 7.1 连接
- https://bitpay.com/blog/copay-adds-trezor-support/
- BixinKEY无法连接
#### 7.2 结果
- 未判定

## 8. GreenBits
- App下载地址：https://play.google.com/store/apps/details?id=com.greenaddress.greenbits_android_wallet
#### 8.1 连接
- 网络设置选择testnet，版本3.3.4
- BixinKEY无法连接
#### 8.2 结果
- 未判定

## 9.GreenAddress
- App下载地址：https://github.com/greenaddress/WalletElectron/releases
- 参考流程：https://blog.greenaddress.it/how-to-initialize-your-trezor-with-greenaddress-services/
- Chrome插件地址：https://chrome.google.com/webstore/detail/greenaddress-testnet/kbdjlmbommjjeojcngejkamofpnjhahl
#### 9.1 连接
- 该APP的testnet版本可选择Chrome插件或linux AppImage
- BixinKEY无法连接
#### 9.2 发币
- 在左侧菜单的receive页可以找到地址，向该地址发送一定数额的测试币
- 收币后，进入左侧菜单的send页，填写金额地址和费率，点击review&send按钮
- 在弹出窗口检查发币信息，点击send transaction按钮
#### 9.3 结果
- 未判定

## 10. Walleth
- 只能用于Ethereum
- APP下载地址：https://f-droid.org/en/packages/org.walleth/
#### 10.1 连接
- 参考：https://wiki.trezor.io/Apps:Walleth
- 打开APP，插入BixinKEY，点击Connect Trezor，如果BixinKEY已经初始化则自动连接成功，否则需要做提示错误，初始化后才可连接
#### 10.2 发币
- 在弹出窗口选择账户的路径（自动分配还是自定义）
- 点击确定，进入创建账户页面，也要求校验PIN，输入PIN验证OK，进入钱包界面
#### 10.3 结果
- 未判定

## 11. sentinel
- APP下载地址：https://apps.evozi.com/apk-downloader/?id=com.samourai.sentinel
- Github地址：https://github.com/Samourai-Wallet/sentinel-android/releases
#### 11.1 连接
- 参考：https://blog.trezor.io/watch-trezor-bitcoin-account-wallet-sentinel-android-guide-304aeccbd9e4
- Watch-Only wallet
- BixinKEY无法连接
#### 11.2 结果
- 此类钱包不能连接硬件钱包

