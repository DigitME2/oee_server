from socket import socket, AF_INET, SOCK_DGRAM
from time import sleep

""" Listens for a device broadcast and responds, so the device can discover this server. """

PORT = 8090
EXPECTED_TEXT = "DISCOVER_OEE_SERVER_REQUEST"

s = socket(AF_INET, SOCK_DGRAM)
s.bind(('', PORT))

while 1:
    data, addr = s.recvfrom(1024)  # Wait for a packet
    print("Received broadcast:", data.decode("utf-8"))

    if data.decode("utf-8") == EXPECTED_TEXT:
        print("Responding...")
        s.sendto("DISCOVER_OEE_SERVER_RESPONSE".encode("utf-8"), addr)
    sleep(5)
