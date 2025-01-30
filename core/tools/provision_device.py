from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from typing import Any
from typing_extensions import Self

import click
import requests
import serial
import shlex

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
        connection.command("optiga-certdev-write", self.device_cert)
        cert_dev = connection.command("optiga-certdev-read")
        if cert_dev != self.device_cert:
            print("Device certificate mismatch")
            print("Expected:", self.device_cert)
            print("Got:     ", cert_dev)
        assert cert_dev == self.device_cert

        connection.command("optiga-certfido-write", self.fido_cert)
        cert_fido = connection.command("optiga-certfido-read")
        assert cert_fido == self.fido_cert

        connection.command("optiga-keyfido-write", self.fido_privkey)
        key_fido = connection.command("optiga-keyfido-read")
        assert key_fido is not None
        assert key_fido in self.fido_cert


@dataclass
class DeviceInfo:
    optiga_id: bytes
    cpu_id: bytes
    device_cert: bytes

    @classmethod
    def read(cls, connection: Connection) -> Self:
        cpu_id = connection.command("get-cpuid")
        optiga_id = connection.command("optiga-id-read")
        cert_bytes = connection.command("optiga-certinf-read")
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
        self.connection.write(b"\r")

    def command(self, cmd: str, *args: Any) -> bytes | None:
        cmd_line = cmd
        for arg in args:
            if isinstance(arg, bytes):
                cmd_line += " " + arg.hex()
            else:
                cmd_line += " " + str(arg)
        self.writeline(cmd_line.encode())

        while True:
            res = self.readline()
            if res.startswith(b"ERROR"):
                error_args = res[len(b"ERROR ") :].decode()
                parts = shlex.split(error_args)
                error_text = parts[0] # error code
                if len(parts) > 1:
                    error_text = parts[1] # error description
                raise ProdtestException(error_text)
            elif res.startswith(b"OK"):
                res_arg = res[len(b"OK ") :]
                if not res_arg:
                    return None
                try:
                    return bytes.fromhex(res_arg.decode())
                except ValueError:
                    return res_arg
            elif not res.startswith(b"#"):
                raise ProdtestException("Unexpected response: " + res.decode())

def provision_request(
    device: DeviceInfo, url: str, model: str, verify: bool = True
) -> ProvisioningResult:
    request = {
        "tester_id": SERVER_TOKEN,
        "run_id": secrets.token_hex(16),
        "optiga_id": device.optiga_id.hex(),
        "cpu_id": device.cpu_id.hex(),
        "cert": device.device_cert.hex(),
        "model": model,
    }
    resp = requests.post(url + '/provision', json=request, verify=verify)
    if resp.status_code == 400:
        print("Server returned error:", resp.text)
    resp.raise_for_status()
    resp_json = resp.json()
    return ProvisioningResult.from_json(resp_json)


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("-d", "--device", default="/dev/ttyACM0", help="Device path")
def identify(device) -> None:
    connection = Connection(device)
    connection.command("ping")
    DeviceInfo.read(connection)


@cli.command()
@click.option("-d", "--device", default="/dev/ttyACM0", help="Device path")
@click.option("--wipe", is_flag=True, help="Wipe the device")
def lock(device, wipe) -> None:
    connection = Connection(device)
    connection.command("ping")
    connection.command("optiga-lock")
    if wipe:
        connection.command("prodtest-wipe")


@cli.command()
@click.option("-u", "--url", default=SERVER_URL, help="Server URL")
@click.option("-d", "--device", default="/dev/ttyACM0", help="Device path")
@click.option("-m", "--model", help="Device path")
@click.option(
    "--no-verify", is_flag=True, help="Disable server certificate verification"
)
@click.option(
    "--lock/--no-lock", default=True, help="Lock the device after provisioning"
)
def provision(url, device, model, no_verify, lock) -> None:
    global SERVER_TOKEN

    SERVER_TOKEN = os.environ.get("SERVER_TOKEN")
    if SERVER_TOKEN is None:
        raise click.ClickException("SERVER_TOKEN environment variable is not set")
    connection = Connection(device)

    # test the connection
    connection.command("ping")

    # grab CPUID, OPTIGAID and device certificate
    device = DeviceInfo.read(connection)
    # call the provisioning server
    result = provision_request(device, url, model, not no_verify)
    # write provisioning result to the device
    result.write(connection)

    if lock:
        connection.command("optiga-lock")
        connection.command("prodtest-wipe")


if __name__ == "__main__":
    cli()
