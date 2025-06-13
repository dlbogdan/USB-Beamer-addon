import asyncio
import logging
from zeroconf import ServiceInfo

from discovery_manager import DiscoveryManager
from usb_manager import USBManager

# Constants
PRIVATE_KEY_PATH = "/data/id_rsa"
STARTING_LOCAL_PORT = 13240
SSH_USER = "root"
USBIP_REMOTE_PORT = 3240

class SSHManager:
    """Manages dynamic SSH tunnels to discovered servers."""

    def __init__(self, usb_manager: USBManager):
        self.user = SSH_USER
        self.usb_manager = usb_manager
        self.tunnels = {}  # Maps server name to the tunnel task
        self.servers = {}  # Maps server name to the ServiceInfo object
        self.port_mapping = {}  # Maps server name to its assigned local port
        self.next_local_port = STARTING_LOCAL_PORT
        
        logging.info(f"SSH connections will use hardcoded username: '{self.user}'")
        self.discovery = DiscoveryManager(
            add_callback=self.add_server,
            remove_callback=self.remove_server
        )

    async def add_server(self, info: ServiceInfo):
        """Starts a new SSH tunnel for a discovered server."""
        name = info.name
        if name in self.servers:
            return  # Already managing a tunnel for this server

        local_port = self.next_local_port
        self.next_local_port += 1

        self.servers[name] = info
        self.port_mapping[name] = local_port
        
        task = asyncio.create_task(self._maintain_tunnel(info, local_port))
        self.tunnels[name] = task

    async def remove_server(self, name: str):
        """Stops the SSH tunnel and detaches devices for a lost server."""
        # First, schedule the detachment of all associated USB devices.
        # This is now an async function.
        asyncio.create_task(self.usb_manager.detach_all_for_server(name))

        # Then, proceed with tearing down the connection.
        if name in self.tunnels:
            self.tunnels[name].cancel()
            del self.tunnels[name]
        if name in self.servers:
            del self.servers[name]
        if name in self.port_mapping:
            del self.port_mapping[name]

    def get_active_ports(self) -> dict:
        """Returns a mapping of server names to their local ports."""
        return self.port_mapping.copy()

    async def _maintain_tunnel(self, info: ServiceInfo, local_port: int):
        """Creates and maintains a single SSH tunnel, reconnecting on failure."""
        address = info.server
        ssh_port = info.port
        
        logging.info(f"Starting tunnel for {self.user}@{address}:{ssh_port} ({info.name})")
        
        sync_task = None
        while True:
            process = None
            try:
                cmd = [
                    "ssh",
                    "-p", str(ssh_port),
                    "-i", PRIVATE_KEY_PATH,
                    "-L", f"{local_port}:localhost:{USBIP_REMOTE_PORT}",
                    f"{self.user}@{address}",
                    "-N",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ExitOnForwardFailure=yes",
                    "-o", "ServerAliveInterval=15",
                    "-o", "ServerAliveCountMax=3",
                ]
                process = await asyncio.create_subprocess_exec(*cmd)
                logging.info(f"[{info.name}] SSH tunnel process started on local port {local_port}.")
                
                # Start a periodic task to sync devices for this tunnel.
                sync_task = asyncio.create_task(self._periodic_sync(info.name, local_port))

                # Wait for the SSH process to terminate.
                await process.wait()

            except asyncio.CancelledError:
                logging.info(f"Tunnel for {info.name} is stopping.")
                if process and process.returncode is None:
                    process.terminate()
                break
            except Exception as e:
                logging.error(f"Error with tunnel for {info.name}: {e}")

            finally:
                if sync_task:
                    sync_task.cancel()

            # If the loop continues, it means the connection was lost. Detach devices.
            logging.warning(f"Tunnel for {info.name} disconnected. Detaching devices before reconnecting...")
            await self.usb_manager.detach_all_for_server(info.name)
            await asyncio.sleep(10)

    async def _periodic_sync(self, server_name: str, local_port: int):
        """The background task that periodically calls the USBManager to sync devices."""
        while True:
            try:
                await self.usb_manager.scan_and_sync_devices(server_name, local_port)
                await asyncio.sleep(15)  # Sync interval
            except asyncio.CancelledError:
                logging.info(f"[{server_name}] Device sync loop stopped.")
                break
            except Exception as e:
                logging.error(f"[{server_name}] Error in device sync loop: {e}")
                # Wait longer after an error to avoid spamming logs.
                await asyncio.sleep(30)

    def close(self):
        """Closes all active SSH tunnels and discovery."""
        logging.info("Closing all SSH tunnels and discovery service...")
        self.discovery.close()
        for tunnel in self.tunnels.values():
            tunnel.cancel() 