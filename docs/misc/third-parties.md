# List of third parties

That need to be notified when a protocol breaking change occurs.

### Using trezorlib:
_This usually requires some code changes in the affected software._

- Electrum https://github.com/spesmilo/electrum
- HWI https://github.com/bitcoin-core/HWI
- Trezor Agent https://github.com/romanz/trezor-agent
- Shadowlands https://github.com/kayagoban/shadowlands

### Using HWI
_Updating HWI to the latest version should be enough._

- BTCPay https://github.com/btcpayserver/btcpayserver
- Wasabi https://github.com/zkSNACKs/WalletWasabi

### Using no Trezor libraries
- Monero https://github.com/monero-project/monero
- Mycelium Android https://github.com/mycelium-com/wallet-android
- Mycelium iOS https://github.com/mycelium-com/wallet-ios
- Blockstream Green Android https://github.com/Blockstream/green_android
- Blockstream Green iOS https://github.com/Blockstream/green_ios

### Using Connect:

_See https://github.com/trezor/connect/network/dependents for a full list
of projects depending on Connect._

#### Connect dependencies introduction

Javascript projects that have Connect as a dependency are using the [Connect NPM
package](https://www.npmjs.com/package/trezor-connect) on version specified in their
yarn.lock (or similar). This NPM package is not a complete Connect library, it is a
simple layer that deals with opening an iframe and loading the newest Connect from
connect.trezor.io.

Such project must have the newest MAJOR version of this NPM package (v8 at the moment).
But then the main logic library (dealing with devices etc.) is fetched from
connect.trezor.io and is therefore under our control and can be updated easily.

So in a nutshell:
- If there is a new MAJOR version of Connect we indeed want to notify these parties below.
- In other cases we do not, we just need to deploy updated Connect before releasing
firmwares.

#### Notable third-parties

- Trezor Password Manager https://github.com/trezor/trezor-password-manager
- Exodus (closed source)
- MagnumWallet (closed source)
- CoinMate (closed source)
- MyEtherWallet https://github.com/MyEtherWallet/MyEtherWallet
- MyCrypto https://github.com/MyCryptoHQ/MyCrypto
- MetaMask https://github.com/MetaMask/metamask-extension
- SimpleStaking https://github.com/simplestaking/wallet
- AdaLite https://github.com/vacuumlabs/adalite
- Stellarterm https://github.com/stellarterm/stellarterm
- frame https://github.com/floating/frame
- lisk-desktop https://github.com/LiskHQ/lisk-desktop
- Liskish Wallet https://github.com/hirishh/liskish-wallet/
- web3-react https://github.com/NoahZinsmeister/web3-react
- KyberSwap https://github.com/KyberNetwork/KyberSwap
- Balance Manager https://github.com/balance-io/balance-manager
- www.coinpayments.net
- www.bancor.network
- dubiex.com
- www.coinmap.org
- mydashwallet.org
- app.totle.com
- manager.balance.io
- faa.st
- beta.shapeshift.com
