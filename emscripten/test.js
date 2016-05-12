var crypto = require('./trezor-crypto');
var bitcoin = require('bitcoinjs-lib');

var XPUB =
    'xpub6AHA9hZDN11k2ijHMeS5QqHx2KP9aMBRhTDqANMnwVtdyw2TDYRm' +
    'F8PjpvwUFcL1Et8Hj59S3gTSMcUQ5gAqTz3Wd8EsMTmF3DChhqPQBnU';
var node = bitcoin.HDNode.fromBase58(XPUB).derive(0);

var nodeStruct = {
    depth: node.depth,
    child_num: node.index,
    fingerprint: node.parentFingerprint,
    chain_code: node.chainCode,
    public_key: node.keyPair.getPublicKeyBuffer()
};

var suite;
var worker;

if (typeof Worker !== 'undefined') {
    console.log('enabling web worker benchmark');
    worker = new Worker('./trezor-crypto.js');
    worker.onerror = function (error) {
        console.error('worker:', error);
    };
    suite = [
        // benchBitcoinJS,
        // benchBrowserify,
        benchWorker
    ];
} else {
    suite = [
        benchBitcoinJS,
        benchBrowserify
    ];
}

benchmark(suite, 1000, 1000);

function benchmark(suite, delay, ops) {
    (function cycle(i) {
        setTimeout(function () {
            var benchmark = suite[i];
            runBenchmark(benchmark, ops, function (runtime) {
                printResult(benchmark, ops, runtime);
                cycle(i+1 < suite.length ? i+1 : 0);
            });
        }, delay);
    }(0));
}

function benchBitcoinJS(ops, fn) {
    var i;
    for (i = 0; i < ops; i++) {
        node.derive(i).getAddress();
    }
    fn();
}

function benchBrowserify(ops, fn) {
    var i;
    crypto.serializeNode(nodeStruct);
    for (i = 0; i < ops; i++) {
        crypto.deriveAddress(i, 0);
    }
    fn();
}

function benchWorker(ops, fn) {
    worker.onmessage = function (event) {
        fn();
    };
    worker.postMessage({
        type: 'deriveAddressRange',
        node: nodeStruct,
        from: 0,
        to: ops - 1,
        version: 0
    });
}

function runBenchmark(benchmark, ops, fn) {
    var start = new Date();
    benchmark(ops, function () {
        var end = new Date();
        fn(end - start);
    });
}

function printResult(benchmark, ops, runtime) {
    var opssec = (ops / runtime) * 1000;
    console.log(
        benchmark.name,
        'ops #', ops,
        'runtime', runtime / 1000,
        'sec, ops/sec', opssec
    );
}
