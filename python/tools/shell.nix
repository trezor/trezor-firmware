nix-shell -p "python3.withPackages (p: [ p.gevent p.click p.bottle p.typing-extensions p.construct p.requests p.libusb1 ])"
