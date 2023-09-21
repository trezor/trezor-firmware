from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Any
from typing_extensions import Self

import click
import requests
import serial

SERVER_TOKEN = ""
SERVER_URL = "http://localhost:8000/provision"


@dataclass
class ProvisioningResult:
    device_cert: bytes
    fido_privkey: bytes
    fido_cert: bytes
    production: bool

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> Self:
        return cls(
            device_cert=bytes.fromhex(json["device_cert"]),
            fido_privkey=bytes.fromhex(json["fido_privkey"]),
            fido_cert=bytes.fromhex(json["fido_cert"]),
            production=json["production"],
        )

    def write(self, connection: Connection) -> None:
        connection.command("CERTDEV WRITE", self.device_cert)
        cert_dev = connection.command("CERTDEV READ")
        if cert_dev != self.device_cert:
            print("Device certificate mismatch")
            print("Expected:", self.device_cert)
            print("Got:     ", cert_dev)
        assert cert_dev == self.device_cert

        connection.command("CERTFIDO WRITE", self.fido_cert)
        cert_fido = connection.command("CERTFIDO READ")
        assert cert_fido == self.fido_cert

        connection.command("KEYFIDO WRITE", self.fido_privkey)
        key_fido = connection.command("KEYFIDO READ")
        assert key_fido is not None
        assert key_fido in self.fido_cert


@dataclass
class DeviceInfo:
    optiga_id: bytes
    cpu_id: bytes
    device_cert: bytes

    @classmethod
    def read(cls, connection: Connection) -> Self:
        cpu_id = connection.command("CPUID READ")
        optiga_id = connection.command("OPTIGAID READ")
        cert_bytes = connection.command("CERTINF READ")
        assert optiga_id is not None
        assert cpu_id is not None
        assert cert_bytes is not None
        return cls(optiga_id, cpu_id, cert_bytes)


class ProdtestException(Exception):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


class Connection:
    def __init__(self, path: str = "/dev/ttyACM0") -> None:
        self.connection = serial.Serial(path, 115200, timeout=5)

    def readline(self) -> bytes:
        line = self.connection.readline().strip()
        line_str = line.decode()
        if len(line_str) > 100:
            line_str = line_str[:100] + "..."

        print("<<<", line_str)
        return line

    def writeline(self, data: bytes) -> None:
        data_str = data.decode()
        if len(data_str) > 100:
            print(">>>", data_str[:100] + "...")
        else:
            print(">>>", data_str)

        for byte in data:
            if byte < 32 or byte > 126:
                print("!!!", byte, "is not printable")
                continue
            self.connection.write(bytes([byte]))
            echo = self.connection.read(1)
            assert echo[0] == byte
        self.connection.write(b"\r")
        assert self.connection.read(2) == b"\r\n"
        # self.connection.write(data + b"\r")
        # echo = self.connection.read(len(data) + 2)
        # print(len(echo), len(data) + 2)
        # assert echo[:-2] == data
        # assert echo[-2:] == b"\r\n"

    def command(self, cmd: str, *args: Any) -> bytes | None:
        cmd_line = cmd
        for arg in args:
            if isinstance(arg, bytes):
                cmd_line += " " + arg.hex()
            else:
                cmd_line += " " + str(arg)
        self.writeline(cmd_line.encode())

        res = self.readline()
        if res.startswith(b"ERROR"):
            error_text = res[len(b"ERROR ") :].decode()
            raise ProdtestException(error_text)
        if not res.startswith(b"OK"):
            raise ProdtestException("Unexpected response: " + res.decode())
        res_arg = res[len(b"OK ") :]
        if not res_arg:
            return None
        try:
            return bytes.fromhex(res_arg.decode())
        except ValueError:
            return res_arg


def provision_request(
    device: DeviceInfo, url: str, verify: bool = True
) -> ProvisioningResult:
    request = {
        "tester_id": SERVER_TOKEN,
        "run_id": secrets.token_hex(16),
        "optiga_id": device.optiga_id.hex(),
        "cpu_id": device.cpu_id.hex(),
        "cert": device.device_cert.hex(),
        "model": "T2B1",
    }
    resp = requests.post(url, json=request, verify=verify)
    if resp.status_code == 400:
        print("Server returned error:", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    return ProvisioningResult.from_json(resp_json)


@click.group()
def cli() -> None:
    pass


@cli.command()
def identify() -> None:
    connection = Connection()
    connection.command("PING")
    DeviceInfo.read(connection)


@cli.command()
@click.option("--wipe", is_flag=True, help="Wipe the device")
def lock(wipe) -> None:
    connection = Connection()
    connection.command("PING")
    connection.command("LOCK")
    if wipe:
        connection.command("WIPE")


@cli.command()
@click.option("-u", "--url", default=SERVER_URL, help="Server URL")
@click.option("-d", "--device", default="/dev/ttyACM0", help="Device path")
@click.option(
    "--no-verify", is_flag=True, help="Disable server certificate verification"
)
@click.option(
    "--lock/--no-lock", default=True, help="Lock the device after provisioning"
)
def provision(url, device, no_verify, lock) -> None:
    global SERVER_TOKEN

    SERVER_TOKEN = os.environ.get("SERVER_TOKEN")
    if SERVER_TOKEN is None:
        raise click.ClickException("SERVER_TOKEN environment variable is not set")
    connection = Connection(device)

    # test the connection
    connection.command("PING")

    # grab CPUID, OPTIGAID and device certificate
    device = DeviceInfo.read(connection)
    # call the provisioning server
    result = provision_request(device, url, not no_verify)
    # write provisioning result to the device
    result.write(connection)

    if lock:
        connection.command("LOCK")
        connection.command("WIPE")


if __name__ == "__main__":
    cli()
