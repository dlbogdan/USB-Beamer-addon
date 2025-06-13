import asyncio
import logging

from ssh_manager import SSHManager
from usb_manager import USBManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BeamerClient:
    def __init__(self):
        self.ssh_manager = SSHManager()
        self.usb_manager = USBManager()
        self.running = False

    async def start(self):
        logging.info("Starting USB Beamer Client...")
        self.running = True
        # TODO: Add logic to generate keypair and display public key
        # TODO: Start SSH tunnel and server liveness checks
        # TODO: Start USB device attachment logic
        while self.running:
            await asyncio.sleep(1)

    def stop(self):
        logging.info("Stopping USB Beamer Client...")
        self.running = False
        self.ssh_manager.close_tunnel()

if __name__ == "__main__":
    client = BeamerClient()
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        client.stop()
        logging.info("USB Beamer Client stopped by user.") 