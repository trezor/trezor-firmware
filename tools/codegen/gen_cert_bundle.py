#!/usr/bin/python3
import pem
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization

bundle = '/var/lib/ca-certificates/ca-bundle.pem'

certs = pem.parse_file(bundle)

def process_cert(cert):
    cert = x509.load_pem_x509_certificate(cert.as_bytes(), default_backend())
    i = cert.issuer
    f = cert.fingerprint(hashes.BLAKE2s(32))
    try:
        i = i.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except:
        i = i.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
    print('  # %s' % i)
    print('  %s,' % f)

print('cert_bundle = [')
for c in certs:
    process_cert(c)
print(']')
