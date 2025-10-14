from trezor import io

while True:
    print("Hello from extapp.py")
    msg_entry = [0, 0]
    io.poll([], msg_entry, 1000)
