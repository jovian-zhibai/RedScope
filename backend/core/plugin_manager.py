"""Plugin manager: loads, validates, and manages tool plugins."""

import os
from pathlib import Path
from dataclasses import dataclass, field
import yaml
from backend.config import get_settings


@dataclass
class PluginInput:
    name: str
    type: str  # string / boolean / select / integer
    required: bool = False
    default: str | None = None
    description: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class PluginProxy:
    supported: bool = False
    flag: str = ""  # e.g., "-proxy {proxy_url}"


@dataclass
class PluginConfig:
    name: str
    display_name: str
    version: str = ""
    description: str = ""
    category: str = "custom"
    language: str = ""
    # Docker config
    docker_image: str = ""
    docker_build: str = ""
    # Local config
    local_binary: str = ""
    local_check_command: str = ""
    # Execution
    command: str = ""
    inputs: list[PluginInput] = field(default_factory=list)
    # Output
    output_format: str = "text"
    output_path: str = "/output/result.txt"
    parser: str = ""
    provides: list[str] = field(default_factory=list)
    # Proxy
    proxy: PluginProxy = field(default_factory=PluginProxy)


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, PluginConfig] = {}
        settings = get_settings()
        self.plugins_dir = Path(settings.plugins_dir)

    def load_all(self):
        for subdir in ["builtin", "custom"]:
            plugin_dir = self.plugins_dir / subdir
            if not plugin_dir.exists():
                continue
            for yaml_file in sorted(plugin_dir.glob("*.yaml")):
                try:
                    config = self._parse_yaml(yaml_file)
                    self._plugins[config.name] = config
                except Exception as e:
                    print(f"Failed to load plugin {yaml_file}: {e}")

    def _parse_yaml(self, path: Path) -> PluginConfig:
        with open(path) as f:
            raw = yaml.safe_load(f)

        p = raw.get("plugin", raw)

        inputs = []
        for inp in p.get("inputs", []):
            inputs.append(PluginInput(
                name=inp["name"],
                type=inp.get("type", "string"),
                required=inp.get("required", False),
                default=inp.get("default"),
                description=inp.get("description", ""),
                options=inp.get("options", []),
            ))

        docker = p.get("docker", {})
        local = p.get("local", {})
        output = p.get("output", {})
        proxy_raw = p.get("proxy", {})

        return PluginConfig(
            name=p["name"],
            display_name=p.get("display_name", p["name"]),
            version=p.get("version", ""),
            description=p.get("description", ""),
            category=p.get("category", "custom"),
            language=p.get("language", ""),
            docker_image=docker.get("image", ""),
            docker_build=docker.get("build", ""),
            local_binary=local.get("binary", ""),
            local_check_command=local.get("check_command", ""),
            command=p.get("command", ""),
            inputs=inputs,
            output_format=output.get("format", "text"),
            output_path=output.get("path", "/output/result.txt"),
            parser=output.get("parser", ""),
            provides=p.get("provides", []),
            proxy=PluginProxy(
                supported=proxy_raw.get("supported", False),
                flag=proxy_raw.get("flag", ""),
            ),
        )

    def get_plugin(self, name: str) -> PluginConfig | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[PluginConfig]:
        return list(self._plugins.values())

    def list_by_category(self, category: str) -> list[PluginConfig]:
        return [p for p in self._plugins.values() if p.category == category]

    def build_command(self, plugin: PluginConfig, params: dict, proxy_url: str | None = None) -> str:
        cmd = plugin.command
        for key, value in params.items():
            cmd = cmd.replace(f"{{{key}}}", str(value))

        if proxy_url and plugin.proxy.supported:
            proxy_flag = plugin.proxy.flag.replace("{proxy_url}", proxy_url)
            cmd = f"{cmd} {proxy_flag}"

        # Clean up unreplaced optional placeholders
        import re
        cmd = re.sub(r'\{[^}]+\}', '', cmd).strip()
        cmd = re.sub(r'\s+', ' ', cmd)

        return cmd


plugin_manager = PluginManager()
