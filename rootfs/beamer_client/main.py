import asyncio
import logging
import signal
import argparse

from ssh_manager import SSHManager
from usb_manager import USBManager

# Configure logging at the top level, but it will be overridden in main.
logging.basicConfig(level="INFO", format='%(asctime)s - %(levelname)s - %(message)s')

class BeamerClient:
    """Main client application."""

    def __init__(self):
        # The USB manager is now independent.
        self.usb_manager = USBManager()
        # The SSH manager orchestrates everything, using the usb_manager.
        self.ssh_manager = SSHManager(self.usb_manager)
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Starts the client's main discovery loop and waits for shutdown."""
        logging.info("Starting USB Beamer Client...")
        await self.ssh_manager.start()
        logging.info("Service discovery is active. Client is running.")
        await self.shutdown_event.wait()

    async def stop(self):
        """Stops the client and all its managers."""
        logging.info("Stopping USB Beamer Client...")
        await self.ssh_manager.close()
        self.shutdown_event.set()
        logging.info("Client shutdown initiated.")

async def main():
    client = BeamerClient()

    async def handle_shutdown_signal():
        logging.info("Shutdown signal received.")
        await client.stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(handle_shutdown_signal()))

    try:
        await client.start()
    except asyncio.CancelledError:
        logging.info("Main client task was cancelled.")
    finally:
        logging.info("USB Beamer Client has shut down.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USB Beamer Client")
    parser.add_argument(
        '--log-level',
        default='INFO',
        help='The logging level (DEBUG, INFO, WARNING, ERROR, FATAL)'
    )
    args = parser.parse_args()

    # Validate the log level and default to INFO if it's invalid.
    log_level = args.log_level.upper()
    if log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'FATAL']:
        log_level = 'INFO'

    # Re-configure the root logger with the validated level.
    logging.getLogger().setLevel(log_level)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("USB Beamer Client stopped by user.") 