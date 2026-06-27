"""Proxy router: determines which proxy to use for a given target."""

import ipaddress
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.operational import ProxyNode


class ProxyRoute:
    def __init__(self, proxy_url: str, chain: list[str], username: str = "", password: str = ""):
        self.proxy_url = proxy_url
        self.chain = chain
        # Store credentials separately to avoid leaking in URL/logs
        self.username = username
        self.password = password


class ProxyRouter:
    def __init__(self, db: Session, project_id: int):
        result = db.execute(
            select(ProxyNode).where(ProxyNode.project_id == project_id, ProxyNode.status != "offline")
        )
        self.nodes = {n.id: n for n in result.scalars().all()}

    def get_route(self, target: str) -> ProxyRoute | None:
        for node in self.nodes.values():
            if self._target_in_cidrs(target, node.reachable_cidrs):
                chain = self._build_chain(node)
                username = ""
                password = ""
                if node.username_enc:
                    from backend.utils.crypto import decrypt_value
                    username = decrypt_value(node.username_enc)
                    password = decrypt_value(node.password_enc) if node.password_enc else ""
                # Build proxy URL without credentials; pass them separately
                proxy_url = f"{node.proxy_type}://{node.host}:{node.port}"
                return ProxyRoute(proxy_url=proxy_url, chain=chain, username=username, password=password)
        return None

    def _target_in_cidrs(self, target: str, cidrs: list) -> bool:
        try:
            addr = ipaddress.ip_address(target)
            for cidr in cidrs:
                if addr in ipaddress.ip_network(cidr, strict=False):
                    return True
        except ValueError:
            pass
        return False

    def _build_chain(self, node: ProxyNode) -> list[str]:
        chain = []
        current = node
        while current:
            chain.insert(0, f"{current.name} ({current.proxy_type}://{current.host}:{current.port})")
            if current.upstream_node_id and current.upstream_node_id in self.nodes:
                current = self.nodes[current.upstream_node_id]
            else:
                break
        return chain

    def generate_proxychains_config(self, target: str) -> str:
        route = self.get_route(target)
        if not route:
            return ""

        lines = ["[ProxyList]"]
        node = self._find_node_for_target(target)
        current = node
        while current:
            lines.append(f"{current.proxy_type} {current.host} {current.port}")
            if current.upstream_node_id and current.upstream_node_id in self.nodes:
                current = self.nodes[current.upstream_node_id]
            else:
                break
        return "\n".join(lines)

    def _find_node_for_target(self, target: str) -> ProxyNode | None:
        for node in self.nodes.values():
            if self._target_in_cidrs(target, node.reachable_cidrs):
                return node
        return None
