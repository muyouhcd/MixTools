import bpy
import json
from mathutils import Vector
import os
from collections import defaultdict
from mathutils.bvhtree import BVHTree
import bmesh

bl_info = {
    "name": "骨骼数据导出与还原",
    "blender": (3, 6, 0),
    "category": "Object",
    "description": "导出骨骼和空物体的数据到 JSON 文件，并从中还原"
}

name_groups = [
    (["Head", "Neck"], "Face"),
    (["Spine", "UpperArm", "Forearm", "Hand", "Finger"], "UpperBody"),
    (["Pelvis",], "Pelvis"),
    (["Thigh", "Calf",], "LowerBody"),
    (["Foot", "Toe0",], "Feet")
]

class ExportBoneDataOperator(bpy.types.Operator):
    """操作符，用于导出骨骼数据"""
    bl_idname = "object.export_bone_data"
    bl_label = "导出骨骼数据"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'ARMATURE':
            bone_data = get_bone_data_with_scaling(obj.name)
            empty_coords_data = get_empty_object_data(context)

            addon_path = get_addon_path()
            if not addon_path:
                self.report({'ERROR'}, "无法找到插件目录，请确保插件安装在正确位置")
                return {'CANCELLED'}
                
            file_name = f"{obj.name}.json"
            file_path = os.path.join(addon_path, file_name)

            save_data_to_json(bone_data, empty_coords_data, file_path)
            self.report({'INFO'}, f"已成功将骨骼和空物体数据导出到 {file_name}")
            
            # Refresh the JSON list after exporting
            update_json_file_list(context)
        else:
            self.report({'ERROR'}, "请先选择一个骨骼对象")
        return {'FINISHED'}

class RestoreEmptyDataOperator(bpy.types.Operator):
    """读取 JSON 数据并还原空物体位置"""
    bl_idname = "object.restore_empty_data"
    bl_label = "还原空物体位置"

    def execute(self, context):
        index = context.scene.json_file_index
        file_list = context.scene.json_file_list
        
        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的 JSON 文件进行还原")
            return {'CANCELLED'}

        file_name = file_list[index].name
        file_path = os.path.join(get_addon_path(), file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                empty_coords_data = data.get("empty_coords_data", [])

                for empty_name, location in empty_coords_data:
                    empty_obj = bpy.data.objects.get(empty_name)
                    if not empty_obj:
                        empty_obj = bpy.data.objects.new(empty_name, None)
                        context.collection.objects.link(empty_obj)
                    empty_obj.location = Vector(location)

            self.report({'INFO'}, f"空物体位置已成功从 {file_name} 还原")
        
        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")
        
        return {'FINISHED'}

def get_top_parent(obj):
    while obj.parent is not None:
        obj = obj.parent
    return obj if obj else None

def create_parent_dict(name_list):
    top_parents = {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and any(name in obj.name for name in name_list):
            top_parent = get_top_parent(obj)
            if top_parent is None:
                top_parent = obj
            if top_parent not in top_parents:
                top_parents[top_parent] = []
            top_parents[top_parent].append(obj)
    return top_parents

def join_objects(parent_dict, new_name):

    for top_parent, objects in parent_dict.items():
        if len(objects) <= 1:
            continue

        # 确保所有对象都在 OBJECT 模式下
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)

        if bpy.context.selected_objects:
            # 设置第一个选中的对象为活动对象
            bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
            bpy.ops.object.join()

        bpy.context.object.name = new_name

def rename_all_children_based_on_coords(empty_coords):
    objects_bvh = {}

    def create_bvh_tree(obj):
        bm = bmesh.new()
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
        bmesh.ops.transform(bm, verts=bm.verts, matrix=obj.matrix_world)
        bvh = BVHTree.FromBMesh(bm)
        bm.free()
        return bvh

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            objects_bvh[obj] = create_bvh_tree(obj)

    renamed_objects = {}

    for name, coord in empty_coords:
        intersection_count = defaultdict(int)

        for other_obj, bvh in objects_bvh.items():
            ray_origin = Vector(coord)
            ray_direction = Vector((0, 0, -1))

            location, _, _, _ = bvh.ray_cast(ray_origin, ray_direction)
            while location:
                intersection_count[other_obj] += 1
                ray_origin = location + ray_direction * 0.00001
                location, _, _, _ = bvh.ray_cast(ray_origin, ray_direction)

        for other_obj, count in intersection_count.items():
            if count % 2 == 1:
                new_name = name.replace("_example", "")
                if other_obj not in renamed_objects:
                    other_obj.name = new_name
                    renamed_objects[other_obj] = True

def strip_name_suffix(name):
    """去掉名称的数字后缀以便于匹配."""
    return name.rsplit('.', 1)[0]

class RestoreSkeletonFromJsonOperator(bpy.types.Operator):
    """根据 JSON 数据还原骨架并自动绑定到网格"""
    bl_idname = "object.restore_skeleton_from_json"
    bl_label = "从所选配置自动绑定"

    def execute(self, context):
        index = context.scene.json_file_index
        file_list = context.scene.json_file_list

        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的 JSON 文件进行还原")
            return {'CANCELLED'}

        file_name = file_list[index].name
        file_path = os.path.join(get_addon_path(), file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                bone_data = data.get("bone_data", {})
                empty_coords_data = data.get("empty_coords_data", [])

                # 根据空物体的位置重命名场景中的物体
                rename_all_children_based_on_coords(empty_coords_data)

                # 收集顶级父级对象
                top_level_objects = {get_top_parent(obj) for obj in context.scene.objects if obj.type == 'MESH'}

                # 为每个顶级父级对象创建和绑定骨架
                for top_object in top_level_objects:
                    # 创建骨架
                    armature = bpy.data.armatures.new(name=f"{top_object.name}_Armature")
                    armature_obj = bpy.data.objects.new(f"{top_object.name}_Armature_Object", armature)
                    context.collection.objects.link(armature_obj)

                    # 将骨架移到顶级父级对象的下面
                    armature_obj.parent = top_object

                    bpy.context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode='EDIT')

                    created_bones = {}
                    for bone_name, bone_info in bone_data.items():
                        bone = armature.edit_bones.new(name=bone_name)
                        bone.head = Vector(bone_info['head'])
                        bone.tail = Vector(bone_info['tail'])
                        created_bones[bone_name] = bone

                    for bone_name, bone_info in bone_data.items():
                        if bone_info["parent"]:
                            created_bones[bone_name].parent = created_bones.get(bone_info["parent"])

                    bpy.ops.object.mode_set(mode='OBJECT')

                    # 绑定顶级父级对象的所有子对象
                    for child_obj in top_object.children:
                        if child_obj.type == 'MESH':
                            armature_modifier = child_obj.modifiers.new(name="Armature", type='ARMATURE')
                            armature_modifier.object = armature_obj

                            # 清除现有顶点组并设置所有顶点权重为0
                            child_obj.vertex_groups.clear()

                            # 使用去掉后缀的名称创建顶点组
                            group_name = strip_name_suffix(child_obj.name)
                            vertex_group = child_obj.vertex_groups.new(name=group_name)
                            all_verts_indices = list(range(len(child_obj.data.vertices)))

                            # 将所有顶点添加到顶点组并设置权重为1
                            vertex_group.add(all_verts_indices, 1.0, 'ADD')

                # 合并物体
                for names, new_name in name_groups:
                    filtered_objects = create_parent_dict(names)
                    join_objects(filtered_objects, new_name)

            self.report({'INFO'}, f"骨架从 {file_name} 中成功还原并绑定")

        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")

        return {'FINISHED'}

    """根据 JSON 数据还原骨架并自动绑定到网格"""
    bl_idname = "object.restore_skeleton_from_json"
    bl_label = "从JSON还原骨架并自动绑定"

    def execute(self, context):
        index = context.scene.json_file_index
        file_list = context.scene.json_file_list

        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的 JSON 文件进行还原")
            return {'CANCELLED'}

        file_name = file_list[index].name
        file_path = os.path.join(get_addon_path(), file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                bone_data = data.get("bone_data", {})
                empty_coords_data = data.get("empty_coords_data", [])

                # 根据空物体的位置重命名场景中的物体
                rename_all_children_based_on_coords(empty_coords_data)

                # 收集顶级父级对象
                top_level_objects = {get_top_parent(obj) for obj in context.scene.objects if obj.type == 'MESH'}

                # 为每个顶级父级对象创建和绑定骨架
                for top_object in top_level_objects:
                    # 创建骨架
                    armature = bpy.data.armatures.new(name=f"{top_object.name}_Armature")
                    armature_obj = bpy.data.objects.new(f"{top_object.name}_Armature_Object", armature)
                    context.collection.objects.link(armature_obj)

                    # 将骨架移到顶级父级对象的下面
                    armature_obj.parent = top_object

                    bpy.context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode='EDIT')

                    created_bones = {}
                    for bone_name, bone_info in bone_data.items():
                        bone = armature.edit_bones.new(name=bone_name)
                        bone.head = Vector(bone_info['head'])
                        bone.tail = Vector(bone_info['tail'])
                        created_bones[bone_name] = bone

                    for bone_name, bone_info in bone_data.items():
                        if bone_info["parent"]:
                            created_bones[bone_name].parent = created_bones.get(bone_info["parent"])

                    bpy.ops.object.mode_set(mode='OBJECT')

                    # 绑定顶级父级对象的所有子对象
                    for child_obj in top_object.children:
                        if child_obj.type == 'MESH':
                            armature_modifier = child_obj.modifiers.new(name="Armature", type='ARMATURE')
                            armature_modifier.object = armature_obj

                            # 清除现有顶点组并设置所有顶点权重为0
                            child_obj.vertex_groups.clear()

                            # 使用去掉后缀的名称创建顶点组
                            group_name = strip_name_suffix(child_obj.name)
                            vertex_group = child_obj.vertex_groups.new(name=group_name)
                            all_verts_indices = list(range(len(child_obj.data.vertices)))

                            # 将所有顶点添加到顶点组并设置权重为1
                            vertex_group.add(all_verts_indices, 1.0, 'ADD')

                # 合并物体
                for names, new_name in name_groups:
                    filtered_objects = create_parent_dict(names)
                    join_objects(filtered_objects, new_name)

            self.report({'INFO'}, f"骨架从 {file_name} 中成功还原并绑定")

        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")

        return {'FINISHED'}

def get_bone_data_with_scaling(armature_name):
    bone_data = {}
    template_armature = bpy.data.objects.get(armature_name)
    
    if template_armature and template_armature.type == 'ARMATURE':
        bpy.context.view_layer.objects.active = template_armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 获取骨架对象的世界矩阵
        world_matrix = template_armature.matrix_world

        for bone in template_armature.data.edit_bones:
            # 将局部坐标转换为全局坐标
            bone_head_world = world_matrix @ bone.head
            bone_tail_world = world_matrix @ bone.tail

            bone_data[bone.name] = {
                "parent": bone.parent.name if bone.parent else None,
                "head": list(bone_head_world),
                "tail": list(bone_tail_world)
            }
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    return bone_data

def get_empty_object_data(context):
    empty_coords_data = []
    for obj in context.selected_objects:
        if obj.type == 'EMPTY':
            empty_coords_data.append((obj.name, list(obj.location)))
    return empty_coords_data

def save_data_to_json(bone_data, empty_coords_data, file_path):
    data = {
        "bone_data": bone_data,
        "empty_coords_data": empty_coords_data
    }
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

class RestoreBoneDataOperator(bpy.types.Operator):
    """读取 JSON 数据并还原骨骼和空物体位置"""
    bl_idname = "object.restore_bone_data"
    bl_label = "还原骨骼数据"

    def execute(self, context):
        # 使用与保存相同的路径
        index = context.scene.json_file_index
        file_list = context.scene.json_file_list

        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的 JSON 文件进行还原")
            return {'CANCELLED'}

        file_name = file_list[index].name
        file_path = os.path.join(get_addon_path(), file_name)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                bone_data = data.get("bone_data", {})
                empty_coords_data = data.get("empty_coords_data", [])

                print("Loaded bones:", bone_data)
                print("Loaded empties:", empty_coords_data)

                # 清单的顶级对象
                top_level_objects = {get_top_parent(obj) for obj in context.scene.objects if obj.type == 'MESH'}

                for top_object in top_level_objects:
                    # 创建骨架
                    armature = bpy.data.armatures.new(name=f"{top_object.name}_Armature")
                    armature_obj = bpy.data.objects.new(f"{top_object.name}_Armature_Object", armature)
                    context.collection.objects.link(armature_obj)

                    # 设置骨架位置
                    armature_obj.parent = top_object

                    bpy.context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode='EDIT')

                    created_bones = {}
                    for bone_name, bone_info in bone_data.items():
                        bone = armature.edit_bones.new(name=bone_name)
                        bone.head = Vector(bone_info['head'])
                        bone.tail = Vector(bone_info['tail'])
                        created_bones[bone_name] = bone

                    # 设置骨骼父关系
                    for bone_name, bone_info in bone_data.items():
                        if bone_info["parent"]:
                            created_bones[bone_name].parent = created_bones.get(bone_info["parent"])
                    
                    bpy.ops.object.mode_set(mode='OBJECT')

                # 还原空物体位置
                for empty_name, location in empty_coords_data:
                    print(f"Restoring empty object {empty_name} to location {location}")
                    empty_obj = bpy.data.objects.get(empty_name)
                    if empty_obj and empty_obj.type == 'EMPTY':
                        empty_obj.location = Vector(location)

            self.report({'INFO'}, "骨骼数据已成功还原")
        
        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")
        
        return {'FINISHED'}

class BoneDataExporterPanel(bpy.types.Panel):
    """创建一个自定义面板"""
    bl_label = "骨骼数据导出与还原工具"
    bl_idname = "OBJECT_PT_bone_data_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '角色工具'
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("object.export_bone_data", text="导出骨骼数据")
        
        row = layout.row()
        row.template_list("UI_UL_list", "json_files", context.scene, "json_file_list", context.scene, "json_file_index")
        
        row = layout.row()
        row.operator("object.restore_bone_data", text="还原骨骼数据")
        
        row = layout.row()
        row.operator("object.restore_empty_data", text="还原空物体数据")

        row = layout.row()
        row.operator("object.restore_skeleton_from_json", text="根据所选配置自动绑定")

        row = layout.row()
        row.operator("object.refresh_json_list", text="刷新配置列表")

class RefreshJsonListOperator(bpy.types.Operator):
    """操作符，用于刷新JSON文件列表"""
    bl_idname = "object.refresh_json_list"
    bl_label = "刷新JSON列表"
    
    def execute(self, context):
        update_json_file_list(context)
        self.report({'INFO'}, "文件列表已更新")
        return {'FINISHED'}

class CharOperater(bpy.types.Operator):
    bl_idname = "object.miao_char_operater"
    bl_label = "角色一键处理"
    
    def apply_transforms_recursive(self, obj):
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.select_set(False)

        if obj.children:
            for child in obj.children:
                self.apply_transforms_recursive(child)

    def execute(self, context):
        print("开始处理顶点")
        bpy.ops.object.vox_operation()
        print("开始处理碰撞")
        bpy.ops.object.miao_parent_byboundingbox()

        def apply_change_to_scene():
            def set_material_to_objects(objects, material):
                for obj in objects:
                    if len(obj.data.materials):
                        obj.data.materials[0] = material
                    else:
                        obj.data.materials.append(material)

            top_level_parents = [obj for obj in bpy.data.objects if obj.parent is None and 'example' not in obj.name.lower()]

            for parent_obj in top_level_parents:
                parent_obj.scale *= 0.5
                parent_obj.location = (0, 0, 0)

                if parent_obj.children:
                    children_with_materials = [child for child in parent_obj.children if len(child.data.materials) > 0]
                    if children_with_materials:
                        child_with_random_material = random.choice(children_with_materials)
                        random_material = child_with_random_material.data.materials[0]
                        set_material_to_objects(parent_obj.children, random_material)
    
        apply_change_to_scene()

        for parent_obj in bpy.context.scene.objects:
            if parent_obj.parent is None:
                self.apply_transforms_recursive(parent_obj)
        
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

def update_json_file_list(context):
    file_dir = get_addon_path()
    
    files = [f for f in os.listdir(file_dir) if f.endswith('.json')]
    
    context.scene.json_file_list.clear()
    for f in files:
        item = context.scene.json_file_list.add()
        item.name = f

def get_addon_path():
    """
    查找插件目录下的 MiaoTools\RigJson 文件夹路径。
    """
    # 获取当前文件的绝对路径并规范化
    file_path = os.path.normpath(os.path.dirname(__file__))
    
    # 逆向查找直到找到 "addons" 文件夹
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)

    # 确认已经找到 "addons" 文件夹
    if os.path.basename(file_path) == "addons":
        # 添加相对路径到 MiaoTools\RigJson
        target_path = os.path.join(file_path, "MiaoTools", "RigJson")

        # 确保该路径存在
        if os.path.exists(target_path):
            return target_path
    
    return ''  # 如果未找到则返回空字符串

def register():
    bpy.utils.register_class(BoneDataExporterPanel)
    bpy.utils.register_class(ExportBoneDataOperator)
    bpy.utils.register_class(RestoreEmptyDataOperator)
    bpy.utils.register_class(RestoreSkeletonFromJsonOperator)
    bpy.utils.register_class(RefreshJsonListOperator)
    bpy.utils.register_class(CharOperater)
    bpy.utils.register_class(RestoreBoneDataOperator)
    bpy.types.Scene.json_file_list = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.json_file_index = bpy.props.IntProperty()
    update_json_file_list(bpy.context)

def unregister():
    bpy.utils.unregister_class(CharOperater)
    bpy.utils.unregister_class(BoneDataExporterPanel)
    bpy.utils.unregister_class(ExportBoneDataOperator)
    bpy.utils.unregister_class(RestoreEmptyDataOperator)
    bpy.utils.unregister_class(RestoreSkeletonFromJsonOperator)
    bpy.utils.unregister_class(RefreshJsonListOperator)
    bpy.utils.unregister_class(RestoreBoneDataOperator)
    del bpy.types.Scene.json_file_list
    del bpy.types.Scene.json_file_index

if __name__ == "__main__":
    register()