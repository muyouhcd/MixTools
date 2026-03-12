"""
MixTools 公共工具模块

提供跨模块复用的通用工具函数，避免代码重复。
"""

import hashlib
import bpy


# ---------------------------------------------------------------------------
# 层级关系工具
# ---------------------------------------------------------------------------

def get_top_parent(obj):
    """获取物体的最顶级父物体。如果物体没有父物体则返回自身。

    Args:
        obj: bpy.types.Object - Blender 物体

    Returns:
        bpy.types.Object - 最顶级的父物体
    """
    top = obj
    while top.parent is not None:
        top = top.parent
    return top


def get_all_children(obj, recursive=True):
    """获取物体的所有子物体。

    Args:
        obj: bpy.types.Object - 父物体
        recursive: bool - 是否递归获取所有后代

    Returns:
        list[bpy.types.Object] - 子物体列表
    """
    children = list(obj.children)
    if recursive:
        for child in list(children):
            children.extend(get_all_children(child, recursive=True))
    return children


# ---------------------------------------------------------------------------
# Mesh 几何工具
# ---------------------------------------------------------------------------

def get_mesh_hash(obj):
    """获取网格物体的几何哈希值，用于比较几何相同性。

    通过顶点坐标、边、面信息生成 MD5 哈希值，
    不比较物体的位置、旋转、缩放信息。

    Args:
        obj: bpy.types.Object - 网格物体

    Returns:
        str | None - MD5 哈希字符串，非网格物体返回 None
    """
    if obj.type != 'MESH':
        return None

    mesh = obj.data
    vertex_data = "".join(f"{v.co.x},{v.co.y},{v.co.z}" for v in mesh.vertices)
    edge_data = "".join(f"{e.vertices[0]},{e.vertices[1]}" for e in mesh.edges)
    polygon_data = "".join(
        "".join(map(str, sorted(p.vertices))) for p in mesh.polygons
    )

    data = vertex_data + edge_data + polygon_data
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def group_objects_by_mesh_hash(mesh_objects):
    """按几何哈希值对网格物体分组，返回包含 2 个及以上相同几何物体的分组。

    Args:
        mesh_objects: iterable[bpy.types.Object] - 网格物体列表

    Returns:
        list[list[bpy.types.Object]] - 分组列表，每组包含几何相同的物体
    """
    groups = {}
    for obj in mesh_objects:
        if obj.type != 'MESH':
            continue
        h = get_mesh_hash(obj)
        if h is None:
            continue
        groups.setdefault(h, []).append(obj)
    return [g for g in groups.values() if len(g) > 1]


# ---------------------------------------------------------------------------
# 选择与过滤工具
# ---------------------------------------------------------------------------

def iter_selected_mesh_objects(context):
    """迭代当前选中的网格物体。

    Args:
        context: bpy.types.Context

    Yields:
        bpy.types.Object - 类型为 MESH 的选中物体
    """
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            yield obj


def select_only(obj):
    """仅选中指定物体，取消其他所有选中。

    Args:
        obj: bpy.types.Object - 要选中的物体
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


# ---------------------------------------------------------------------------
# 模式切换工具
# ---------------------------------------------------------------------------

def safe_mode_set(mode, context=None):
    """安全切换物体模式，如果已在目标模式则不执行操作。

    Args:
        mode: str - 目标模式 ('OBJECT', 'EDIT', 'POSE' 等)
        context: bpy.types.Context | None - 上下文，默认使用 bpy.context

    Returns:
        bool - 是否成功切换
    """
    ctx = context or bpy.context
    if ctx.active_object and ctx.active_object.mode != mode:
        try:
            bpy.ops.object.mode_set(mode=mode)
            return True
        except RuntimeError:
            return False
    return True


# ---------------------------------------------------------------------------
# 集合工具
# ---------------------------------------------------------------------------

def get_object_collection(obj):
    """获取物体所属的第一个集合。

    Args:
        obj: bpy.types.Object

    Returns:
        bpy.types.Collection | None
    """
    for col in bpy.data.collections:
        if obj.name in col.objects:
            return col
    return None


# ---------------------------------------------------------------------------
# 注册辅助工具
# ---------------------------------------------------------------------------

def register_classes(classes):
    """批量注册 Blender 类。

    Args:
        classes: tuple | list - 要注册的类列表
    """
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister_classes(classes):
    """批量注销 Blender 类（逆序）。

    Args:
        classes: tuple | list - 要注销的类列表
    """
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
