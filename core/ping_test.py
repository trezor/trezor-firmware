from trezorlib.client import get_default_client, messages

client = get_default_client("webusb:000:1:2:4:4")

client.open()

i = 0
while True:
    client.call_raw(messages.Ping(msg=b"hello"))
    print(f"{i}")
    i += 1


from trezorlib.transport.webusb import WebUsbTransport

transport = WebUsbTransport.find_by_path("webusb:000:1:2:4:4")
transport.handle.open()

while True:
    print(transport.handle.read_chunk())