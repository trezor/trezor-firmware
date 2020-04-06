#!/bin/bash
openssl req -new -key att_priv_key.pem -config openssl.cnf |
openssl x509 -req -CA ca_cert.pem -CAkey ca_priv_key.pem -out att_cert.der --outform DER -set_serial 54878404 -days 10957 -extfile openssl.cnf -extensions v3_req
