from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.core.plugin_manager import plugin_manager
from backend.core.rbac import require_manager
from backend.models.scan_task import Plugin

router = APIRouter()


@router.get("")
async def list_plugins():
    plugins = plugin_manager.list_plugins()
    return {"items": [
        {
            "name": p.name, "display_name": p.display_name, "version": p.version,
            "description": p.description, "category": p.category,
            "docker_image": p.docker_image, "local_binary": p.local_binary,
            "proxy_supported": p.proxy.supported,
            "inputs": [{"name": i.name, "type": i.type, "required": i.required,
                        "default": i.default, "description": i.description, "options": i.options}
                       for i in p.inputs],
        }
        for p in plugins
    ]}


@router.get("/categories")
async def list_categories():
    plugins = plugin_manager.list_plugins()
    categories = {}
    for p in plugins:
        categories.setdefault(p.category, []).append(p.display_name)
    return categories


@router.post("/reload")
async def reload_plugins(_=Depends(require_manager)):
    plugin_manager.load_all()
    count = len(plugin_manager.list_plugins())
    return {"status": "reloaded", "count": count}


@router.put("/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: str, _=Depends(require_manager), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plugin).where((Plugin.id == int(plugin_id) if plugin_id.isdigit() else False) | (Plugin.name == plugin_id)))
    plugin = result.scalar_one_or_none()
    if not plugin:
        raise HTTPException(404, "插件不存在")
    plugin.is_enabled = not plugin.is_enabled
    await db.flush()
    return {"name": plugin.name, "is_enabled": plugin.is_enabled}


@router.post("/custom")
async def add_custom_plugin(req: dict, _=Depends(require_manager)):
    import yaml
    from pathlib import Path

    name = req.get("name", "").strip()
    if not name or not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "工具名称只能包含字母、数字、连字符和下划线")

    plugin_dir = Path("/app/plugins/custom")
    plugin_dir.mkdir(parents=True, exist_ok=True)
    plugin_file = plugin_dir / f"{name}.yaml"

    if plugin_file.exists():
        raise HTTPException(400, f"工具 {name} 已存在")

    run_mode = req.get("run_mode", "docker")
    yaml_plugin = {
        "name": name,
        "display_name": req.get("display_name", name),
        "version": "1.0.0",
        "description": req.get("description", ""),
        "category": req.get("category", "custom"),
        "inputs": [
            {"name": "target", "type": "string", "required": True, "description": "目标"},
            {"name": "extra_args", "type": "string", "required": False},
        ],
        "command": req.get("command", ""),
        "output": {
            "format": req.get("output_format", "json"),
            "path": req.get("output_path", "/output/result.json"),
        },
        "proxy": {
            "supported": req.get("proxy_supported", False),
            "flag": req.get("proxy_flag", ""),
        },
    }

    if run_mode == "docker":
        yaml_plugin["docker"] = {"image": req.get("docker_image", "")}
    else:
        yaml_plugin["local"] = {"binary": req.get("local_binary", ""), "check_command": f"{req.get('local_binary', '').split()[0]} --help"}

    yaml_content = {"plugin": yaml_plugin}

    with open(plugin_file, "w") as f:
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

    plugin_manager.load_all()
    return {"name": name, "file": str(plugin_file)}
