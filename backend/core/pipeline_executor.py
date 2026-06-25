"""Pipeline executor: runs multi-step scan pipelines (DAG-based)."""

import asyncio
from collections import defaultdict
from backend.core.plugin_manager import plugin_manager
from backend.core.engine_orchestrator import EngineOrchestrator


class PipelineExecutor:
    def __init__(self):
        self.orchestrator = EngineOrchestrator()

    async def execute(self, pipeline_dag: dict, initial_targets: list[str], proxy_url: str | None = None) -> dict:
        nodes = {n["id"]: n for n in pipeline_dag.get("nodes", [])}
        edges = pipeline_dag.get("edges", [])

        deps = defaultdict(list)
        for edge in edges:
            deps[edge["to"]].append(edge["from"])

        if self._has_cycle(nodes, edges):
            return {"error": "Pipeline DAG contains a cycle"}

        completed: dict[str, list[str]] = {}
        results: dict[str, dict] = {}

        roots = [nid for nid in nodes if nid not in deps]

        async def run_node(node_id: str):
            node = nodes[node_id]
            plugin_name = node.get("plugin")
            plugin = plugin_manager.get_plugin(plugin_name)
            if not plugin:
                results[node_id] = {"error": f"Plugin {plugin_name} not found"}
                return

            targets = initial_targets
            for dep_id in deps.get(node_id, []):
                if dep_id in completed:
                    targets = completed[dep_id]

            node_results = []
            for target in targets:
                params = {**node.get("config", {}), "target": target, "url": target, "domain": target}
                result = await self.orchestrator.run_engine(plugin, params, proxy_url=proxy_url)
                if result.success:
                    from backend.parsers.builtin import parse_output
                    parsed = parse_output(plugin.name, plugin.output_format, result.output_path, plugin.output_path)
                    output_targets = [p.get("host", p.get("url", target)) for p in parsed if p.get("host") or p.get("url")]
                    node_results.extend(output_targets if output_targets else [target])

            completed[node_id] = node_results or targets
            results[node_id] = {"targets_in": len(targets), "targets_out": len(node_results), "plugin": plugin_name}

            children = [e["to"] for e in edges if e["from"] == node_id]
            child_tasks = []
            for child_id in children:
                all_deps_done = all(d in completed for d in deps[child_id])
                if all_deps_done:
                    child_tasks.append(run_node(child_id))
            if child_tasks:
                await asyncio.gather(*child_tasks)

        await asyncio.gather(*[run_node(r) for r in roots])
        return results

    @staticmethod
    def _has_cycle(nodes: dict, edges: list) -> bool:
        adj = defaultdict(list)
        for e in edges:
            adj[e["from"]].append(e["to"])
        visited = set()
        in_stack = set()

        def dfs(node):
            visited.add(node)
            in_stack.add(node)
            for neighbor in adj.get(node, []):
                if neighbor in in_stack:
                    return True
                if neighbor not in visited and dfs(neighbor):
                    return True
            in_stack.discard(node)
            return False

        for nid in nodes:
            if nid not in visited and dfs(nid):
                return True
        return False
