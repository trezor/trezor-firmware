FROM python:3.7.1-stretch

WORKDIR /trezor-emulator

COPY ./ /trezor-emulator
RUN make vendor

RUN apt-get update
RUN apt-get install libusb-1.0-0

RUN pip3 install scons trezor
RUN make build_unix

ENTRYPOINT ["emulator/run.sh"]
EXPOSE 21324/udp 21325
