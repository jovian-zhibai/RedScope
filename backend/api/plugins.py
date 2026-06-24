from fastapi import APIRouter, Depends
from backend.core.plugin_manager import plugin_manager
from backend.core.rbac import require_manager

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
