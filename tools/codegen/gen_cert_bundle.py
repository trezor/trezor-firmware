#!/usr/bin/python3

from pyblake2 import blake2s
import requests


CERTDATA_TXT = 'https://hg.mozilla.org/releases/mozilla-beta/raw-file/default/security/nss/lib/ckfw/builtins/certdata.txt'


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
    r = requests.get(CERTDATA_TXT)
    assert(r.status_code == 200)

    certs = process_certdata(r.text)

    size = 0
    print('cert_bundle = [')
    for k, v in certs.items():
        print('  # %s' % k)
        print('  %s,' % blake2s(v).digest())
        size += len(v)
    print(']')
    print('# certs: %d | digests size: %d | total size: %d' % (len(certs), len(certs) * 32, size))


if __name__ == '__main__':
    main()
