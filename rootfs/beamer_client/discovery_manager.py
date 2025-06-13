import logging
import asyncio
from zeroconf import ServiceBrowser, Zeroconf

SERVICE_TYPE = "_usbip._tcp.local."

class DiscoveryManager:
    """Discovers USB/IP servers on the network using Zeroconf."""

    def __init__(self, add_callback, remove_callback):
        self._add_callback = add_callback
        self._remove_callback = remove_callback
        self._loop = asyncio.get_running_loop()
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, listener=self)
        logging.info("Zeroconf browser started.")

    def add_service(self, zeroconf, type, name):
        """Callback for when a new service is discovered."""
        info = zeroconf.get_service_info(type, name)
        if info:
            logging.info(f"Server discovered: {name} at {info.server}")
            self._loop.call_soon_threadsafe(asyncio.create_task, self._add_callback(info))

    def update_service(self, zeroconf, type, name):
        """Callback for when a service is updated."""
        # Treat update as add; the manager can handle duplicates.
        self.add_service(zeroconf, type, name)

    def remove_service(self, zeroconf, type, name):
        """Callback for when a service is lost."""
        logging.info(f"Server lost: {name}")
        self._loop.call_soon_threadsafe(asyncio.create_task, self._remove_callback(name))

    def close(self):
        """Shuts down the Zeroconf browser."""
        logging.info("Closing Zeroconf browser.")
        self.zeroconf.close() 