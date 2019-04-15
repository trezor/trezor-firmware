import socket

import logger


class UDPInterface:
    def __init__(self, destination_port):
        self.bind_ip = "127.0.0.1"
        self.bind_port = 21423

        self.destination_ip = "127.0.0.1"
        self.destination_port = destination_port

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.bind_ip, self.bind_port))

        self.file_descriptor = self.socket.fileno()

    def write(self, data):
        bytes_sent = self.socket.sendto(
            data, ((self.destination_ip, self.destination_port))
        )
        assert bytes_sent == len(data)
        logger.log_raw(
            "{}:{} < {}:{}".format(
                self.destination_ip, self.destination_port, self.bind_ip, self.bind_port
            ),
            data.hex(),
        )

    def read(self, length):
        data, address = self.socket.recvfrom(length)
        logger.log_raw(
            "{}:{} < {}:{}".format(
                self.bind_ip, self.bind_port, address[0], address[1]
            ),
            data.hex(),
        )
        return data
