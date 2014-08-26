.docs-build-environment: Dockerfile
	docker build -t python-trezor-docs-build-environment .
	touch .docs-build-environment

shell: .docs-build-environment
	docker run -i -t -v $(subst $(notdir $(CURDIR)),,$(CURDIR)):/root -w /root python-trezor-docs-build-environment /bin/bash

html:
	sphinx-build -b html . ./_build/

clean:
	rm -rf _build/

