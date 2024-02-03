from dataclasses import dataclass

from pydactyl import PterodactylClient


@dataclass
class Port:
    id: int
    ip: str
    ip_alias: str
    port: int
    notes: str
    is_default: bool

    @classmethod
    def from_data(cls, data: dict):
        return cls(
            id=data["attributes"]["id"],
            ip=data["attributes"]["ip"],
            ip_alias=data["attributes"]["ip_alias"],
            port=data["attributes"]["port"],
            notes=data["attributes"]["notes"],
            is_default=data["attributes"]["is_default"],
        )


@dataclass
class Limits:
    memory: int
    swap: int
    disk: int
    cpu: int

    @classmethod
    def from_data(cls, data: dict):
        return cls(
            memory=data["memory"],
            swap=data["swap"],
            disk=data["disk"],
            cpu=data["cpu"],
        )


@dataclass
class Server:
    identifier: str
    internal_id: int
    uuid: str
    name: str
    node: str
    is_node_under_maintenance: bool
    is_installing: bool
    is_transferring: bool
    default_port: int
    other_ports: list[Port]
    limits: Limits

    def get_utilization(self, client: PterodactylClient):
        return client.client.servers.get_server_utilization(self.uuid)

    @classmethod
    def from_data(cls, data: dict):
        ports = [
            Port.from_data(port)
            for port in data["attributes"]["relationships"]["allocations"]["data"]
        ]
        default_port = next(port for port in ports if port.is_default)
        return cls(
            identifier=data["attributes"]["identifier"],
            internal_id=data["attributes"]["internal_id"],
            uuid=data["attributes"]["uuid"],
            name=data["attributes"]["name"],
            node=data["attributes"]["node"],
            is_node_under_maintenance=data["attributes"]["is_node_under_maintenance"],
            is_installing=data["attributes"]["is_installing"],
            is_transferring=data["attributes"]["is_transferring"],
            other_ports=ports,
            default_port=default_port.port,
            limits=Limits.from_data(data["attributes"]["limits"]),
        )


a = {
    "current_state": "offline",
    "is_suspended": False,
    "resources": {
        "memory_bytes": 0,
        "cpu_absolute": 0,
        "disk_bytes": 2000683887,
        "network_rx_bytes": 0,
        "network_tx_bytes": 0,
        "uptime": 0,
    },
}


@dataclass
class Status:
    current_state: str
    is_suspended: bool
    memory_bytes: int
    cpu_absolute: int
    disk_bytes: int

    @classmethod
    def from_data(cls, data: dict):
        return cls(
            current_state=data["current_state"],
            is_suspended=data["is_suspended"],
            memory_bytes=data["resources"]["memory_bytes"],
            cpu_absolute=data["resources"]["cpu_absolute"],
            disk_bytes=data["resources"]["disk_bytes"],
        )
