from socket import socket, AF_INET, SOCK_DGRAM
from time import sleep
from config import Config

""" Listens for a device broadcast and responds, so the device can discover this server. """

BROADCAST_PORT = 8090  # This should match the port set in the app
EXPECTED_TEXT = "DISCOVER_OEE_SERVER_REQUEST"
EXPECTED_RESPONSE = "DISCOVER_OEE_SERVER_RESPONSE"

s = socket(AF_INET, SOCK_DGRAM)
s.bind(('', BROADCAST_PORT))

print("Listening for device broadcasts")
while 1:
    data, addr = s.recvfrom(1024)  # Wait for a packet
    print("Received broadcast:", data.decode("utf-8"))

    if data.decode("utf-8") == EXPECTED_TEXT:
        print("Responding...")
        s.sendto((EXPECTED_RESPONSE + ":" + Config.EXTERNAL_PORT).encode("utf-8"), addr)

    sleep(5)
