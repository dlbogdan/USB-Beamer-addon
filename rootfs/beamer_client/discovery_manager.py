import logging
import asyncio
from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf

SERVICE_TYPE = "_usbip._tcp.local."


class DiscoveryManager:
    """Discovers USB/IP servers on the network using Zeroconf."""

    def __init__(self, add_callback, remove_callback):
        self._add_callback = add_callback
        self._remove_callback = remove_callback
        self.aiozc = None
        self.browser = None

    async def start(self):
        """Starts the Zeroconf browser."""
        self.aiozc = AsyncZeroconf()
        self.browser = AsyncServiceBrowser(
            self.aiozc.zeroconf, [SERVICE_TYPE], handlers=[self.on_service_state_change]
        )
        logging.info("Zeroconf browser started.")

    def on_service_state_change(
        self, zeroconf, service_type, name, state_change
    ):
        """Callback for service state changes."""
        logging.info(f"Service {name} state changed: {state_change.name}")
        asyncio.create_task(self.handle_change(service_type, name, state_change))

    async def handle_change(self, service_type, name, state_change):
        info = await self.aiozc.async_get_service_info(service_type, name)
        if not info:
            if state_change == ServiceStateChange.Removed:
                logging.info(f"Server lost: {name}")
                await self._remove_callback(name)
            return

        if state_change == ServiceStateChange.Added or state_change == ServiceStateChange.Updated:
            logging.info(f"Server discovered/updated: {name} at {info.server}")
            await self._add_callback(info)
        elif state_change == ServiceStateChange.Removed:
            logging.info(f"Server lost: {name}")
            await self._remove_callback(name)

    async def close(self):
        """Shuts down the Zeroconf browser."""
        logging.info("Closing Zeroconf browser.")
        if self.aiozc:
            await self.aiozc.async_close() 