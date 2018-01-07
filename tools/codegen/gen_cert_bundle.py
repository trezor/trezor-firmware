#!/usr/bin/python3

from pyblake2 import blake2s
import requests


CERTDATA      = 'https://hg.mozilla.org/releases/mozilla-beta'
CERTDATA_HASH = CERTDATA + '/?cmd=lookup&key=tip'
CERTDATA_TXT  = CERTDATA + '/raw-file/default/security/nss/lib/ckfw/builtins/certdata.txt'


def fetch_certdata():
    r = requests.get(CERTDATA_HASH)
    assert(r.status_code == 200)
    commithash = r.text.strip().split(' ')[1]

    r = requests.get(CERTDATA_TXT)
    assert(r.status_code == 200)
    certdata = r.text

    return commithash, certdata


def process_certdata(data):
    certs = {}
    lines = [x.strip() for x in data.split('\n')]
    label = None
    value = None
    for line in lines:
        if line == 'END':
            if label is not None and value is not None:
                certs[label] = bytes([int(x, 8) for x in value.split('\\')[1:]])
                label = None
                value = None
        elif line.startswith('CKA_LABEL UTF8 '):
            label = line.split('"')[1]
        elif line == 'CKA_VALUE MULTILINE_OCTAL':
            assert(label is not None)
            value = ''
        elif value is not None:
            assert(label is not None)
            value += line
    return certs


def main():
    commithash, certdata = fetch_certdata()

    print('# fetched from %s (default branch)' % CERTDATA)
    print('# commit %s' % commithash)

    certs = process_certdata(certdata)

    size = sum([len(x) for x in certs.values()])
    print('# certs: %d | digests size: %d | total size: %d' % (len(certs), len(certs) * 32, size))

    print('cert_bundle = [')
    for k, v in certs.items():
        print('  # %s' % k)
        print('  %s,' % blake2s(v).digest())
    print(']')


if __name__ == '__main__':
    main()
