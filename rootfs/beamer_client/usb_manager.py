import asyncio
import logging
import re
import subprocess
import aiohttp
import json

class USBManager:
    """Manages attaching and detaching USB/IP devices through active SSH tunnels."""

    def __init__(self):
        # Maps a server name (e.g., 'beamer-server') to a SET of its attached bus IDs
        self.attached_devices_by_server = {}

    async def _get_desired_busids(self, server_name: str, local_http_port: int) -> set | None:
        """Gets the desired set of bus IDs from the server's configuration API."""
        url = f"http://127.0.0.1:{local_http_port}/api/exported-devices"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return set(data)
                    else:
                        logging.warning(
                            f"[{server_name}] Failed to get desired devices from API. "
                            f"Status: {response.status}"
                        )
                        return None
        except Exception as e:
            logging.error(f"[{server_name}] Error connecting to device configuration API: {e}")
            return None

    async def _get_remote_busids(self, server_name: str, local_port: int) -> set | None:
        """Lists devices from a server and returns a set of bus IDs, or None on error."""
        list_cmd = ["usbip", f"--tcp-port={local_port}", "list", f"--remote=127.0.0.1"]
        proc = await asyncio.create_subprocess_exec(
            *list_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()
        
        # This log is very verbose, so it's now at DEBUG level.
        logging.debug(f"[{server_name}] 'usbip list' stdout:\n---\n{stdout_str}\n---")

        if proc.returncode != 0:
            logging.error(f"[{server_name}] 'usbip list' command failed with code {proc.returncode}.")
            if stderr_str:
                logging.error(f"[{server_name}] 'usbip list' stderr:\n---\n{stderr_str}\n---")
            return None
        
        if stderr_str:
             # Don't log normal 'usbip info' messages as warnings.
             if "error:" in stderr_str.lower() or "failed:" in stderr_str.lower():
                 logging.warning(f"[{server_name}] 'usbip list' stderr contained warnings/errors:\n---\n{stderr_str}\n---")
             else:
                 logging.debug(f"[{server_name}] 'usbip list' stderr:\n---\n{stderr_str}\n---")
        
        # This regex now correctly parses output like: '      1-5.4: description'
        # by finding bus IDs at the start of an indented line.
        bus_ids = set(re.findall(r'^\s*([0-9a-zA-Z.-]+):', stdout_str, re.MULTILINE))
        # This is also for debugging, so moved to DEBUG level.
        logging.debug(f"[{server_name}] Parsed bus IDs: {bus_ids}")
        return bus_ids

    async def _attach_busid(self, local_port: int, busid: str) -> bool:
        """Attaches a single device by its bus ID."""
        logging.info(f"Attaching device {busid} on port {local_port}...")
        attach_cmd = ["usbip", f"--tcp-port={local_port}", "attach", f"--remote=127.0.0.1", f"--busid={busid}"]
        proc = await asyncio.create_subprocess_exec(
            *attach_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode == 0:
            logging.info(f"Successfully attached {busid}.")
            return True
        else:
            stderr_str = stderr.decode().strip()
            logging.error(f"Failed to attach {busid}. Stderr:\n---\n{stderr_str}\n---")
            return False

    async def _detach_busids(self, busids_to_detach: set):
        """Detaches a set of devices by finding their local port and using 'usbip detach'."""
        if not busids_to_detach:
            return
        
        try:
            result = subprocess.run(["usbip", "port"], capture_output=True, text=True, check=True)
            busid_pattern = "|".join(re.escape(busid) for busid in busids_to_detach)
            port_matches = re.findall(r"Port (\d+).*<Port in Use>.*(?:{})\b".format(busid_pattern), result.stdout)

            for port_num in set(port_matches):
                logging.info(f"Detaching device at local port {port_num} (busids: {busids_to_detach})...")
                subprocess.run(["usbip", "detach", f"--port={port_num}"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error while detaching devices: {e.stderr}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during detach: {e}")

    async def scan_and_sync_devices(self, server_name: str, local_port: int, local_http_port: int):
        """The main periodic function to keep client state in sync with the server."""
        logging.debug(f"[{server_name}] Running device sync...")
        
        # Get the "desired state" from the server's API, which is the source of truth.
        desired_busids = await self._get_desired_busids(server_name, local_http_port)
        if desired_busids is None:
            logging.warning(f"[{server_name}] Could not get desired device list from server API. Skipping sync.")
            return

        currently_attached = self.attached_devices_by_server.get(server_name, set())
        logging.debug(f"[{server_name}] Sync state: Desired={desired_busids}, Local={currently_attached}")
        
        # Detach devices that are attached locally but no longer desired by the server.
        to_detach = currently_attached - desired_busids
        if to_detach:
            logging.info(f"[{server_name}] Server configuration changed. Detaching devices: {to_detach}")
            await self._detach_busids(to_detach)
            self.attached_devices_by_server[server_name] -= to_detach

        # Identify devices that are desired but not yet attached.
        to_attach_candidates = desired_busids - currently_attached
        if to_attach_candidates:
            # Check which of the desired devices are actually available for connection right now.
            available_busids = await self._get_remote_busids(server_name, local_port)
            if available_busids is None:
                logging.warning(f"[{server_name}] Could not get available device list. Will retry attach on next sync.")
                return
            
            # Attach devices that are both desired and available.
            to_attach = to_attach_candidates.intersection(available_busids)
            if to_attach:
                logging.info(f"[{server_name}] Attaching newly configured devices: {to_attach}")
                for busid in to_attach:
                    if await self._attach_busid(local_port, busid):
                        self.attached_devices_by_server.setdefault(server_name, set()).add(busid)

    async def detach_all_for_server(self, server_name: str):
        """Forcefully detaches all known devices for a given server."""
        busids = self.attached_devices_by_server.get(server_name, set())
        if not busids:
            return
        logging.info(f"[{server_name}] Detaching all known devices for server: {busids}")
        await self._detach_busids(busids)
        if server_name in self.attached_devices_by_server:
            del self.attached_devices_by_server[server_name] 