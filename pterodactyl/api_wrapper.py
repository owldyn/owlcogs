"""Wrapper to make calls easier"""

import asyncio

import pydactyl
from requests import Response

from .dataclasses import Server, Status


class PterodactylAPI:
    def __init__(self, url: str, key: str) -> None:
        """Set up the client.
        Args:
            url (str): The url to the pterodactyl instance.
            key (str): The api key to use.
        """
        self.client = pydactyl.PterodactylClient(url, key)

    def get_servers(self) -> list[Server]:
        """Get all servers (max 1000)"""
        response = self.client.client.servers.list_servers({"per_page": 1000})
        data = response.collect()
        return [Server.from_data(server) for server in data]

    def get_servers_dict(self, key="uuid") -> dict[str, Server]:
        """Get all servers as a dict"""
        return {getattr(server, key or "uuid"): server for server in self.get_servers()}

    def get_server_status(self, server: Server | str) -> Status | None:
        """Get the status of a server."""
        if isinstance(server, Server):
            server = server.uuid
        try:
            response = self.client.client.servers.get_server_utilization(server)
        except Exception:
            return None
        if not isinstance(response, dict):
            raise ValueError("Unexpected response.")
        return Status.from_data(response)

    def restart_server(self, server: Server | str):
        """Restart a server."""
        if isinstance(server, Server):
            server = server.uuid
        response = self.client.client.servers.send_power_action(server, "restart")
        if not isinstance(response, Response):
            return None
        return response.ok

    async def reinstall_server(self, server: Server | str):
        if isinstance(server, Server):
            server = server.uuid
        reinstall_response = self.client.client.servers.settings.reinstall_server(
            server
        )
        if not (
            (isinstance(reinstall_response, Response) and reinstall_response.ok)
            or not isinstance(reinstall_response, Response)
        ):
            raise ValueError("Reinstall failed?")

        await asyncio.sleep(2)
        while (
            response
            if isinstance(response := self.client.client.servers.get_server(server), dict)
            else {}
        ).get("is_installing"):
            await asyncio.sleep(2)
        
        start_response = self.client.client.servers.send_power_action(server, "start")
        if not isinstance(start_response, Response):
            return None
        return start_response.ok
        
