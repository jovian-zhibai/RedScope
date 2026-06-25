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
