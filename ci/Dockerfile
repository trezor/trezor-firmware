# install the latest Alpine linux from scratch

FROM scratch
ARG ALPINE_VERSION=3.14.2
ARG ALPINE_ARCH=x86_64
ADD alpine-minirootfs-${ALPINE_VERSION}-${ALPINE_ARCH}.tar.gz /

# the following is adapted from https://github.com/NixOS/docker/blob/master/Dockerfile

# Enable HTTPS support in wget and set nsswitch.conf to make resolution work within containers
RUN apk add --no-cache --update openssl \
  && echo hosts: files dns > /etc/nsswitch.conf

# Download Nix and install it into the system.
ARG NIX_VERSION=2.3.15
RUN wget https://nixos.org/releases/nix/nix-${NIX_VERSION}/nix-${NIX_VERSION}-${ALPINE_ARCH}-linux.tar.xz \
  && tar xf nix-${NIX_VERSION}-${ALPINE_ARCH}-linux.tar.xz \
  && addgroup -g 30000 -S nixbld \
  && for i in $(seq 1 30); do adduser -S -D -h /var/empty -g "Nix build user $i" -u $((30000 + i)) -G nixbld nixbld$i ; done \
  && mkdir -m 0755 /etc/nix \
  && echo 'sandbox = false' > /etc/nix/nix.conf \
  && mkdir -m 0755 /nix && USER=root sh nix-${NIX_VERSION}-${ALPINE_ARCH}-linux/install \
  && ln -s /nix/var/nix/profiles/default/etc/profile.d/nix.sh /etc/profile.d/ \
  && rm -r /nix-${NIX_VERSION}-${ALPINE_ARCH}-linux* \
  && rm -rf /var/cache/apk/* \
  && /nix/var/nix/profiles/default/bin/nix-collect-garbage --delete-old \
  && /nix/var/nix/profiles/default/bin/nix-store --optimise \
  && /nix/var/nix/profiles/default/bin/nix-store --verify --check-contents

ENV \
    USER=root \
    PATH=/nix/var/nix/profiles/default/bin:/nix/var/nix/profiles/default/sbin:/bin:/sbin:/usr/bin:/usr/sbin \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt \
    NIX_SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    NIX_PATH=/nix/var/nix/profiles/per-user/root/channels

# Trezor specific stuff starts here

COPY shell.nix shell.nix

# to make multiple python versions and monero test suite available, run docker build
# with the following argument: "--build-arg FULLDEPS_TESTING=1"
ARG FULLDEPS_TESTING=0
ENV FULLDEPS_TESTING=${FULLDEPS_TESTING}

RUN nix-shell --arg fullDeps "$([ ${FULLDEPS_TESTING} = 1 ] && echo true || echo false)" --run "echo deps pre-installed"

CMD [ "nix-shell" ]
