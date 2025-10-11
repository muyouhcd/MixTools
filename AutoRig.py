import bpy
import json
from mathutils import Vector
import os
from collections import defaultdict
from mathutils.bvhtree import BVHTree
import bmesh # type: ignore
import random
import math
import time

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.realpath(__file__))
# 将当前目录添加到系统路径
if current_dir not in os.sys.path:
    os.sys.path.append(current_dir)

# 导入Exporter模块
from .Exporter import check_dir, export_fbx, EXPORT_CONFIGS, BATCH_SIZE, prepare_obj_export

def apply_change_to_scene():

            def set_material_to_objects(objects, material):

                for obj in objects:
                    if len(obj.data.materials):
                        obj.data.materials[0] = material
                    else:
                        obj.data.materials.append(material)

            # 获取所有顶级父对象，排除名称中包含 'example' 的对象
            top_level_parents = [obj for obj in bpy.data.objects if obj.parent is None and 'example' not in obj.name.lower()]

            for parent_obj in top_level_parents:
                # 将父对象的缩放比例减半
                parent_obj.scale *= 0.5
                # 将父对象的位置重置到原点
                parent_obj.location = (0, 0, 0)

                # 检查父对象是否有子对象
                if parent_obj.children:
                    # 获取所有具有材质的子对象
                    children_with_materials = [child for child in parent_obj.children if child.data and len(child.data.materials) > 0]

                    # 如果有具有材质的子对象
                    if children_with_materials:
                        # 随机选择一个具有材质的子对象
                        child_with_random_material = random.choice(children_with_materials)
                        # 获取随机选择的子对象的第一个材质
                        random_material = child_with_random_material.data.materials[0]
                        # 将随机选择的材质应用到所有子对象上
                        set_material_to_objects(parent_obj.children, random_material)

def delete_top_level_parent():
    # 检查是否有对象被选中
    if not bpy.context.selected_objects:
        print("没有选中的对象")
        return
    
    # 获取第一个选中对象
    obj = bpy.context.selected_objects[0]

    # 找出顶级父级
    top_parent = obj
    while top_parent.parent is not None:
        top_parent = top_parent.parent
    
    # 删除顶级父级
    bpy.data.objects.remove(top_parent)

def set_object_as_top_parent(parent_name, keep_transform=True):
    """
    将指定名称的物体设置为当前选择物体的顶级父级，并保持变换。

    参数:
    parent_name (str): 要设置为父级的物体名称。
    keep_transform (bool): 如果为 True，则保持变换不变。
    """
    # 获取指定名称的父级对象
    new_parent = bpy.data.objects.get(parent_name)
    if new_parent is None:
        print(f"未找到名称为 '{parent_name}' 的对象。")
        return

    # 确保在对象模式下操作
    if bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("没有选中的对象。")
        return

    # 遍历选定的对象，将指定对象设置为顶级父级
    for obj in selected_objects:
        # 找到当前对象的顶级父级
        top_parent = obj
        while top_parent.parent is not None:
            top_parent = top_parent.parent

        # 设置新的父级
        bpy.ops.object.select_all(action='DESELECT')
        top_parent.select_set(True)
        new_parent.select_set(True)
        bpy.context.view_layer.objects.active = new_parent

        # 设置父级关系
        bpy.ops.object.parent_set(type='OBJECT', keep_transform=keep_transform)

    print(f"已将 '{parent_name}' 设置为选定对象的顶级父级。")

def add_top_level_parent():
    # 检查是否有对象被选中
    if not bpy.context.selected_objects:
        print("没有选中的对象")
        return

def select_top_level_parent():
    # 获取当前选定的物体
    selected_objects = bpy.context.selected_objects

    # 确保有物体被选中
    if not selected_objects:
        print("没有选中的物体")
        return

    # 遍历选定的物体
    for obj in selected_objects:
        top_parent = obj

        # 找到物体的顶级父级
        while top_parent.parent:
            top_parent = top_parent.parent

        # 取消选中其他物体，并选中顶级父级
        bpy.ops.object.select_all(action='DESELECT')
        top_parent.select_set(True)
        bpy.context.view_layer.objects.active = top_parent

        print(f"{obj.name}的顶级父级是: {top_parent.name}")

def set_armature_as_parent(keep_transform=True):
    """
    将选中物体中的骨架作为其他物体的父级，并保持物体的变换。
    :param keep_transform: 如果为True，则保持变换不变。
    """
    # 确保至少有两个物体被选中
    if len(bpy.context.selected_objects) < 2:
        print("请至少选择一个带有骨架的对象和一个需要绑定的对象。")
        return

    selected_objects = bpy.context.selected_objects
    armature_obj = None

    # 找出骨架对象
    for obj in selected_objects:
        if obj.type == 'ARMATURE':
            armature_obj = obj
            break

    # 如果没有找到骨架对象，则返回
    if armature_obj is None:
        print("没有找到骨架对象，请确保选择的对象中包含一个骨架。")
        return

    # 将其他物体绑定到骨架
    for obj in selected_objects:
        if obj != armature_obj:
            # 设置变换保持选项
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            armature_obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj
            
            bpy.ops.object.parent_set(type='ARMATURE', keep_transform=keep_transform)
            obj.select_set(False)

    print("骨架绑定成功，并保持了变换。" if keep_transform else "骨架绑定成功。")

def select_armature():

    # 确保至少有两个物体被选中
    if len(bpy.context.selected_objects) < 1:
        print("请至少选择一个带有骨架的对象和一个需要绑定的对象。")
        return

    selected_objects = bpy.context.selected_objects
    armature_obj = None

    # 找出骨架对象
    for obj in selected_objects:
        if obj.type == 'ARMATURE':
            armature_obj = obj
            break

    # 取消选中其他物体，并选中骨架
    bpy.ops.object.select_all(action='DESELECT')
    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    # 如果没有找到骨架对象，则返回
    if armature_obj is None:
        print("没有找到骨架对象，请确保选择的对象中包含一个骨架。")
        return
    
    # 进入编辑模式
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.armature.select_all(action='SELECT')
    # 在这里执行所需的编辑模式命令，例如选择所有顶点
    bpy.ops.object.connect_bone()
    # 退出编辑模式，回到对象模式
    bpy.ops.object.mode_set(mode='OBJECT')

def get_largest_mesh_object():
    """
    获取选定对象中最大网格对象。

    返回:
    bpy.types.Object: 最大网格对象。如果没有选定网格对象，则返回 None。
    """
    # 确保进入对象模式
    if bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("没有选中的对象。")
        return None

    max_volume = 0
    largest_mesh_obj = None

    for obj in selected_objects:
        if obj.type == 'MESH':
            dimensions = obj.dimensions
            volume = dimensions.x * dimensions.y * dimensions.z

            if volume > max_volume:
                max_volume = volume
                largest_mesh_obj = obj

    return largest_mesh_obj

def get_largest_mesh_object_name():
    """
    获取选定对象中最大网格对象的名称。

    返回:
    str: 最大网格对象的名称。如果没有选定网格对象，则返回 None。
    """
    largest_mesh_obj = get_largest_mesh_object()
    if largest_mesh_obj:
        print(f"最大网格对象的名称是: {largest_mesh_obj.name}")
        return largest_mesh_obj.name
    else:
        print("未找到可识别的网格对象。")
        return None

def delete_largest_mesh_object():
    """
    删除选定对象中最大网格对象。
    """
    largest_mesh_obj = get_largest_mesh_object()
    if largest_mesh_obj:
        # 在删除对象之前获取其名称
        largest_mesh_obj_name = largest_mesh_obj.name
        bpy.data.objects.remove(largest_mesh_obj, do_unlink=True)
        print(f"已删除最大网格对象: {largest_mesh_obj_name}")
    else:
        print("未找到可删除的网格对象。")

def get_top_parent(obj):
    while obj.parent is not None:
        obj = obj.parent
    return obj if obj else None

def rename_top_level_parents(new_name):
    """
    重命名选定对象的顶级父级。

    参数:
    new_name (str): 要设置的新名称。
    """
    # 确保在对象模式下操作
    if bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("没有选中的对象。")
        return

    renamed_parents = set()  # 用于存储已经重命名的父级，避免重复重命名

    for obj in selected_objects:
        # 找到顶级父级
        top_parent = obj
        while top_parent.parent is not None:
            top_parent = top_parent.parent

        # 检查是否已经重命名过
        if top_parent not in renamed_parents:
            top_parent.name = new_name
            renamed_parents.add(top_parent)
            print(f"已重命名顶级父级: {top_parent.name}")

def select_largest_mesh_object():
    """
    选取选定对象中体积最大的网格对象。
    """
    # 确保在对象模式下操作
    if bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # 获取最大的网格对象
    largest_mesh_obj = get_largest_mesh_object()

    # 取消选中所有对象
    bpy.ops.object.select_all(action='DESELECT')

    if largest_mesh_obj:
        # 选中最大的网格对象
        largest_mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = largest_mesh_obj
        print(f"已选择最大网格对象: {largest_mesh_obj.name}")
    else:
        print("未找到可选择的网格对象。")

def set_material_for_selected_objects(material_name):
    # 获取材质
    material = bpy.data.materials.get(material_name)

    # 如果材质不存在，打印错误消息并退出
    if material is None:
        print(f"Material '{material_name}' not found.")
        return

    # 遍历所有选中的对象
    for obj in bpy.context.selected_objects:
        # 检查对象是否为网格类型
        if obj.type == 'MESH':
            # 如果对象没有材质槽，添加一个
            if len(obj.data.materials) == 0:
                obj.data.materials.append(material)  # 为网格添加材质槽

            # 将网格的第一个材质槽分配为指定的材质
            obj.data.materials[0] = material
            print(f"Material '{material_name}' assigned to object '{obj.name}'")

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
    for _, objects in parent_dict.items():
        # 过滤掉非网格类型的对象
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        
        print(f"合并对象组：{[obj.name for obj in mesh_objects]} 为 {new_name}")

        if len(mesh_objects) < 1:
            print(f"警告: 没有可供合并的网格数据在组 '{new_name}'")
            continue

        bpy.ops.object.select_all(action='DESELECT')
        for obj in mesh_objects:
            obj.select_set(True)

        if bpy.context.selected_objects:
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

def get_embedded_empty_data(armature_object):
    empty_data = []

    for obj in armature_object.children:
        if obj.type == 'EMPTY':
            location_world = obj.matrix_world.translation
            rotation_world = obj.matrix_world.to_euler()
            scale_world = obj.matrix_world.to_scale()
            
            parent_bone = obj.parent_bone if obj.parent_type == 'BONE' else None

            empty_data.append({
                "name": obj.name,
                "location": list(location_world),
                "rotation": list(rotation_world),
                "scale": list(scale_world),
                "parent_bone": parent_bone,  # 记录父级骨骼
            })
    return empty_data

def get_bone_data_with_scaling(armature_name):
    bone_data = {}
    embedded_empties = []  # 空物体列表

    template_armature = bpy.data.objects.get(armature_name)
    if template_armature and template_armature.type == 'ARMATURE':
        bpy.context.view_layer.objects.active = template_armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        world_matrix = template_armature.matrix_world

        for bone in template_armature.data.edit_bones:
            bone_head_world = world_matrix @ bone.head
            bone_tail_world = world_matrix @ bone.tail

            # 获取骨骼的扭转数据和其他属性
            twist = bone.roll  # 假设扭转数据是骨骼的 roll 属性
            custom_properties = {k: v for k, v in bone.items()}  # 自定义属性

            bone_data[bone.name] = {
                "parent": bone.parent.name if bone.parent else None,
                "head": list(bone_head_world),
                "tail": list(bone_tail_world),
                "twist": twist,
                "properties": custom_properties
            }

        embedded_empties = get_embedded_empty_data(template_armature)
        
        bpy.ops.object.mode_set(mode='OBJECT')
    
    return bone_data, embedded_empties

def get_empty_object_data(context):
    empty_coords_data = []
    for obj in context.selected_objects:
        if obj.type == 'EMPTY':
            empty_coords_data.append((obj.name, list(obj.location)))
    return empty_coords_data

def save_data_to_json(bone_data, empty_coords_data, file_path, embedded_empties=None):
    data = {
        "bone_data": bone_data,
        "empty_coords_data": empty_coords_data,
        "embedded_empty_data": embedded_empties or [],
        "name_groups": [["Head"],"Face",["Spine", "Arm", "Forearm", "Hand", "Finger", "Neck"],"UpperBody",["Thigh", "Calf", "Leg", "Pelvis"],"LowerBody",["Foot", "Toe"],"Feet"]
        }
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

def update_json_file_list(context):
    file_dir = get_addon_path()
    files = [f for f in os.listdir(file_dir) if f.endswith('.json')]
    context.scene.json_file_list.clear()
    for f in files:
        item = context.scene.json_file_list.add()
        item.name = f

def get_addon_path():

    # 获取当前文件的绝对路径并规范化
    file_path = os.path.normpath(os.path.dirname(__file__))
    
    # 逆向查找直到找到 "addons" 文件夹
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)

    # 确认已经找到 "addons" 文件夹
    if os.path.basename(file_path) == "addons":
        # 添加相对路径到 MixTools\RigJson
        target_path = os.path.join(file_path, "MixTools", "RigJson")

        # 确保该路径存在
        if os.path.exists(target_path):
            return target_path
    
    return ''  # 如果未找到则返回空字符串

def operate_char():
    bpy.ops.object.restore_skeleton_from_json()

def bind_skeleton():
    #绑定操作
        bpy.ops.object.select_all(action='SELECT')
        #从json数据绑定
        bpy.ops.object.restore_skeleton_from_json()

def set_material():
    #设置材质
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.mian_merge_material()
    bpy.ops.object.select_all(action='SELECT')
    set_material_for_selected_objects("Material")

class BoneDataExporterPanel(bpy.types.Panel):
    """创建一个自定义面板"""
    bl_label = "自动绑定|骨骼处理"
    bl_idname = "OBJECT_PT_bone_data_exporter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '角色工具'
    
    def draw(self, context):

        layout = self.layout
        scene = context.scene

        # 骨骼操作
        col_bone_ops = layout.column()
        col_bone_ops.prop(scene, "show_bone_operators", text="骨骼操作", emboss=False,
                         icon='TRIA_DOWN' if scene.show_bone_operators else 'TRIA_RIGHT')
        if scene.show_bone_operators:
            bone_box = col_bone_ops.box()
            bone_box.label(text="骨骼操作工具:", icon='BONE_DATA')
            row1 = bone_box.row(align=True)
            row1.operator("object.export_bone_data", text="导出骨骼", icon='GROUP_BONE')
            row1.operator("object.restore_bone_data", text="还原骨骼", icon='BONE_DATA')
            row1.operator("object.restore_empty_data", text="还原点位", icon='EMPTY_DATA')
            row2 = bone_box.row(align=True)
            row2.operator('object.reset_bone_position', text="重置端点", icon='BONE_DATA')
            row2.operator('object.connect_bone', text="连接骨骼", icon='CONSTRAINT_BONE')

        # 配置管理
        col_config = layout.column()
        col_config.prop(scene, "config_expand", text="配置管理", emboss=False,
                       icon='TRIA_DOWN' if scene.config_expand else 'TRIA_RIGHT')
        if scene.config_expand:
            config_box = col_config.box()
            config_box.label(text="配置列表:", icon='PREFERENCES')
            config_box.template_list("UI_UL_list", "json_files", context.scene, "json_file_list", context.scene, "json_file_index")
            config_box.operator("object.refresh_json_list", text="刷新配置列表", icon='FILE_REFRESH')
            config_box.operator("object.one_click_operator", text="一键绑定处理角色(64)", icon='COMMUNITY')

        # 角色处理
        col_character_process = layout.column()
        col_character_process.prop(scene, "character_process_expand", text="角色处理", emboss=False,
                                  icon='TRIA_DOWN' if scene.character_process_expand else 'TRIA_RIGHT')
        if scene.character_process_expand:
            # 导出设置
            export_box = col_character_process.box()
            export_box.label(text="导出设置:", icon='EXPORT')
            export_box.prop(context.scene, "export_directory", text="导出目录", icon='FILE_FOLDER')
            export_box.operator("scene.export_fbx_without_parent", text="导出角色(无父级)", icon='EXPORT')
            
            # 角色处理工具
            process_box = col_character_process.box()
            process_box.label(text="角色处理工具:", icon='COMMUNITY')
            row1 = process_box.row(align=True)
            row1.operator("object.mian_parent_byboundingbox", text="接触底心创建父级", icon='ARMATURE_DATA')
            row1.operator("object.scale_adjust", text="缩小1/2", icon='COMMUNITY')
            row2 = process_box.row(align=True)
            row2.operator("object.mian_char_operater", text="导入模型一键预处理", icon='COMMUNITY')
            row2.operator("object.with_combin_rename", text="重命名并合并", icon='COMMUNITY')

        # 角色工具
        col_character_tools = layout.column()
        col_character_tools.prop(scene, "character_tools_expand", text="角色工具", emboss=False,
                                icon='TRIA_DOWN' if scene.character_tools_expand else 'TRIA_RIGHT')
        if scene.character_tools_expand:
            # 角色部件分类工具
            classifier_box = col_character_tools.box()
            classifier_box.label(text="角色部件分类工具:", icon='OUTLINER_COLLECTION')
            classifier_box.operator("object.mian_object_classifier", text="按名称分类物体", icon='OUTLINER_COLLECTION')
            
            # 物体替换工具
            replacer_box = col_character_tools.box()
            replacer_box.label(text="物体替换工具:", icon='FILE_REFRESH')
            replacer_box.prop(context.scene, "replacement_blend_file", text="替换源文件", icon='FILE_BLEND')
            replacer_box.prop(context.scene, "enable_set_replacement", text="套装替换", icon='OUTLINER_COLLECTION')
            replacer_box.operator("object.mian_object_replacer", text="从文件替换物体", icon='FILE_REFRESH')




        # row = layout.row()
        # layout.prop(scene.batchtool, "fbx_path", text="FBX路径")
        # row = layout.row()
        # row.operator("object.operator_by_path", text="批量处理目标文件夹内所有fbx（禁用）")

class OperationPath(bpy.types.PropertyGroup):
    fbx_path: bpy.props.StringProperty(
        name="FBX路径",
        description="输入要处理的FBX文件路径",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    ) # type: ignore

class OperatorByPath(bpy.types.Operator):
    """操作符，用于根据路径操作"""
    bl_idname = "object.operator_by_path"
    bl_label = "根据路径批量操作"

    def execute(self, context):
        return {'FINISH'}

class ScaleAdjust(bpy.types.Operator):
    """操作符，用于缩放调整"""
    bl_idname = "object.scale_adjust"
    bl_label = "缩放调整"

    def execute(self, context):
        bpy.ops.object.select_all(action='SELECT')
        
        bpy.ops.transform.resize(value=(0.5, 0.5, 0.5), orient_type='GLOBAL',
                                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                                orient_matrix_type='GLOBAL',
                                mirror=False,
                                use_proportional_edit=False,
                                proportional_edit_falloff='SMOOTH',
                                proportional_size=1,
                                use_proportional_connected=False, use_proportional_projected=False,
                                snap=False,
                                snap_elements={'INCREMENT'},
                                use_snap_project=False, snap_target='CLOSEST',
                                use_snap_self=True,
                                use_snap_edit=True,
                                use_snap_nonedit=True,
                                use_snap_selectable=False)


        return {'FINISHED'}

class OneClickOperator(bpy.types.Operator):
    """一键处理当前角色"""
    bl_idname = "object.one_click_operator"
    bl_label = "一键处理当前角色(单个)"

    def execute(self, context):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.mian_apply_and_separate()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.reset_normals_flat_shading()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.transform.resize(value=(0.25, 0.25, 0.25), orient_type='GLOBAL',
                                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                                orient_matrix_type='GLOBAL',
                                mirror=False,
                                use_proportional_edit=False,
                                proportional_edit_falloff='SMOOTH',
                                proportional_size=1,
                                use_proportional_connected=False, use_proportional_projected=False,
                                snap=False,
                                snap_elements={'INCREMENT'},
                                use_snap_project=False, snap_target='CLOSEST',
                                use_snap_self=True,
                                use_snap_edit=True,
                                use_snap_nonedit=True,
                                use_snap_selectable=False)
        bpy.ops.object.select_all(action='SELECT')

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        delete_top_level_parent()
        bpy.ops.object.select_all(action='SELECT')
        #清除父级关系
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        #清除空物体
        bpy.ops.object.clean_empty()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        #底部中心创建父级
        bpy.ops.object.mian_create_empty_at_bottom()
        bpy.ops.object.select_all(action='SELECT')
        #选取顶级父级清除位移
        select_top_level_parent()
        bpy.ops.object.location_clear(clear_delta=False)
        bpy.ops.object.select_all(action='SELECT')
        #从json数据绑定
        bpy.ops.object.restore_skeleton_from_json()
        bpy.ops.object.select_all(action='SELECT')
        #删除定位框（尺寸最大物体）
        delete_largest_mesh_object()
        #应用所有变换
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        #删除顶级父级
        delete_top_level_parent()
        #设置骨架为父级
        set_armature_as_parent(keep_transform=True)
        #设置材质
        bpy.ops.object.mian_merge_material()
        bpy.ops.object.select_all(action='SELECT')
        set_material_for_selected_objects("Material")

        bpy.ops.object.select_all(action='SELECT')
        select_armature()

        return {'FINISHED'}
    # def execute(self, context):
    #     #断开所有约束，清空变换
    #     bpy.ops.object.select_all(action='SELECT')
    #     bpy.ops.object.mian_apply_and_separate()
    #     bpy.ops.object.select_all(action='SELECT')
    #     bpy.ops.transform.resize(value=(0.25, 0.25, 0.25), orient_type='GLOBAL',
    #                             orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    #                             orient_matrix_type='GLOBAL',
    #                             mirror=False,
    #                             use_proportional_edit=False,
    #                             proportional_edit_falloff='SMOOTH',
    #                             proportional_size=1,
    #                             use_proportional_connected=False, use_proportional_projected=False,
    #                             snap=False,
    #                             snap_elements={'INCREMENT'},
    #                             use_snap_project=False, snap_target='CLOSEST',
    #                             use_snap_self=True,
    #                             use_snap_edit=True,
    #                             use_snap_nonedit=True,
    #                             use_snap_selectable=False)
    #     bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    #     bpy.ops.object.reset_normals_flat_shading()

    #     #清除父级关系
    #     bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

    #     #清除空物体
    #     bpy.ops.object.clean_empty()
    #     bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    #     bpy.ops.object.select_all(action='SELECT')

    #     bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    #     #底部中心创建父级
    #     bpy.ops.object.mian_create_empty_at_bottom()
    #     #选取顶级父级清除位移
    #     select_top_level_parent()
    #     bpy.ops.object.location_clear(clear_delta=False)
    #     bpy.ops.object.select_all(action='SELECT')

    #     #删除父级
    #     # delete_top_level_parent()

    #     #设置名称为最大物体
    #     name=get_largest_mesh_object_name()

    #     #删除定位框（尺寸最大物体）
    #     delete_largest_mesh_object()

    #     #重命名父级为尺寸最大物体名称
    #     rename_top_level_parents(name)

    #     # 绑定操作
    #     bind_skeleton()

    #     #设置骨架为父级
    #     # set_armature_as_parent(keep_transform=True)
        
    #     #设置指定名称物体为父级
    #     bpy.ops.object.select_all(action='SELECT')
    #     set_object_as_top_parent(name, keep_transform=True)

    #     #设置材质
    #     set_material()

    #     return {'FINISHED'}

class WithCombinRename(bpy.types.Operator):

    bl_idname = "object.with_combin_rename"
    bl_label = "combin重命名"

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
                name_groups = data.get("name_groups", [])
                print(name_groups)

        except Exception as e:
            self.report({'ERROR'}, f"重命名失败 {e}")

        # 重命名对象
        rename_all_children_based_on_coords(empty_coords_data)

        for names, new_name in name_groups:
            filtered_objects = create_parent_dict(names)
            join_objects(filtered_objects, new_name)
        bpy.ops.object.select_all(action='SELECT')
        #删除定位框（尺寸最大物体）
        delete_largest_mesh_object()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

class ExportBoneDataOperator(bpy.types.Operator):
    """操作符，用于导出骨骼数据"""
    bl_idname = "object.export_bone_data"
    bl_label = "导出骨骼数据"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'ARMATURE':
            bone_data, embedded_empties = get_bone_data_with_scaling(obj.name)
            empty_coords_data = get_empty_object_data(context)
            addon_path = get_addon_path()

            if not addon_path:
                self.report({'ERROR'}, "无法找到插件目录，请确保插件安装在正确位置")
                return {'CANCELLED'}
                
            file_name = f"{obj.name}.json"
            file_path = os.path.join(addon_path, file_name)

            save_data_to_json(bone_data, empty_coords_data, file_path, embedded_empties)
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

class RestoreSkeletonFromJsonOperator(bpy.types.Operator):
    """根据 JSON 数据还原骨架并自动绑定"""
    bl_idname = "object.restore_skeleton_from_json"
    bl_label = "从 JSON 还原骨架并自动绑定"

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
                embedded_empty_data = data.get("embedded_empty_data", [])
                name_groups = data.get("name_groups", [])

                # 重命名对象
                rename_all_children_based_on_coords(empty_coords_data)

                # 创建和绑定骨架
                top_level_objects = {get_top_parent(obj) for obj in context.scene.objects if obj.type == 'MESH'}

                for top_object in top_level_objects:
                    armature = bpy.data.armatures.new(name="Root")
                    armature_obj = bpy.data.objects.new("Root", armature)
                    context.collection.objects.link(armature_obj)

                    bpy.context.view_layer.objects.active = armature_obj
                    bpy.ops.object.mode_set(mode='EDIT')

                    created_bones = {}
                    for bone_name, bone_info in bone_data.items():
                        bone = armature.edit_bones.new(name=bone_name)
                        bone.head = Vector(bone_info.get('head', [0, 0, 0]))
                        bone.tail = Vector(bone_info.get('tail', [0, 0, 1]))

                        bone.roll = bone_info.get('twist', 0)  # 使用默认值 0
                        for prop_name, prop_value in bone_info.get('properties', {}).items():
                            bone[prop_name] = prop_value  # 设置自定义属性

                        created_bones[bone_name] = bone

                    for bone_name, bone_info in bone_data.items():
                        if bone_info.get("parent"):
                            created_bones[bone_name].parent = created_bones.get(bone_info["parent"])

                    bpy.ops.object.mode_set(mode='OBJECT')

                    # 绑定子对象
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

                # 合并对象


                for names, new_name in name_groups:
                    filtered_objects = create_parent_dict(names)
                    join_objects(filtered_objects, new_name)

                self.report({'INFO'}, f"骨架从 {file_name} 中成功还原并绑定")

        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")

        return {'FINISHED'}

class RestoreBoneDataOperator(bpy.types.Operator):
    """读取 JSON 数据并还原骨骼和空物体位置"""
    bl_idname = "object.restore_bone_data"
    bl_label = "还原骨骼数据"

    def execute(self, context):
        # 获取插件路径
        addon_path = get_addon_path()
        if not addon_path:
            self.report({'ERROR'}, "无法找到插件目录，请确保插件安装在正确位置")
            return {'CANCELLED'}

        # 获取当前选择的 JSON 文件索引
        index = context.scene.json_file_index
        file_list = context.scene.json_file_list
        
        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的 JSON 文件进行还原")
            return {'CANCELLED'}

        # 获取文件名和路径
        file_name = file_list[index].name
        file_path = os.path.join(addon_path, file_name)

        # 加载 JSON 数据
        try:
            with open(file_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                bone_data = data.get("bone_data", {})

                # 创建一个新的骨架对象
                armature_data = bpy.data.armatures.new('RestoredArmature')
                armature_obj = bpy.data.objects.new('RestoredArmature', armature_data)
                bpy.context.collection.objects.link(armature_obj)
                bpy.context.view_layer.objects.active = armature_obj
                bpy.ops.object.mode_set(mode='EDIT')

                created_bones = {}
                for bone_name, bone_info in bone_data.items():
                    bone = armature_data.edit_bones.new(name=bone_name)
                    bone.head = Vector(bone_info.get('head', [0, 0, 0]))
                    bone.tail = Vector(bone_info.get('tail', [0, 0, 1]))
                    created_bones[bone_name] = bone

                for bone_name, bone_info in bone_data.items():
                    if bone_info.get("parent"):
                        created_bones[bone_name].parent = created_bones.get(bone_info["parent"])

                bpy.ops.object.mode_set(mode='OBJECT')

                self.report({'INFO'}, f"骨架从 {file_name} 中成功还原")

        except Exception as e:
            self.report({'ERROR'}, f"还原失败: {e}")

        return {'FINISHED'}

class RefreshJsonListOperator(bpy.types.Operator):
    """操作符，用于刷新JSON文件列表"""
    bl_idname = "object.refresh_json_list"
    bl_label = "刷新JSON列表"
    
    def execute(self, context):
        update_json_file_list(context)
        self.report({'INFO'}, "文件列表已更新")
        return {'FINISHED'}

class CharOperater(bpy.types.Operator):
    bl_idname = "object.mian_char_operater"
    bl_label = "角色一键处理"
    def apply_transforms_recursive(self, obj):
        if obj.data is not None and obj.data.users > 1:
            # 如果对象是多用户的，先复制对象
            new_obj = obj.copy()
            new_obj.data = obj.data.copy()
            bpy.context.collection.objects.link(new_obj)
            
            # 删除原来的物体
            bpy.data.objects.remove(obj, do_unlink=True)
            
            obj = new_obj
        
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        for child in obj.children:
            self.apply_transforms_recursive(child)
    def execute(self, context):
        print("开始处理顶点")
        bpy.ops.object.vox_operation()
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.mian_apply_and_separate()
        bpy.ops.object.clean_empty()
        bpy.ops.object.reset_normals_flat_shading()
        print("开始处理碰撞")
        bpy.ops.object.mian_parent_byboundingbox()
        apply_change_to_scene()
        for parent_obj in bpy.context.scene.objects:
            if parent_obj.parent is None:
                self.apply_transforms_recursive(parent_obj)
        bpy.ops.object.scale_adjust()
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}

class ResetBonePosition(bpy.types.Operator):
    bl_idname = "object.reset_bone_position"
    bl_label = "重置骨骼端点位置（连接）"

    def execute(self, context):
        def align_bone_tail_to_child_head(armature, bone):
            """Align bone's tail to the head of its first child."""
            if bone.children:
                # Align bone's tail to the head of its first child
                bone.tail = bone.children[0].head

        def process_bone_hierarchy(armature, bone):
            """Recursively process the bone hierarchy for alignment."""
            align_bone_tail_to_child_head(armature, bone)
            
            # Recursively handle all children
            for child in bone.children:
                process_bone_hierarchy(armature, child)


        # Ensure we are in edit mode and have an armature selected
        if bpy.context.mode != 'EDIT_ARMATURE':
            bpy.ops.object.mode_set(mode='EDIT')
        
        armature = bpy.context.active_object
        selected_bones = bpy.context.selected_bones
        
        # Process each selected bone
        for bone in selected_bones:
            process_bone_hierarchy(armature, bone)


        return {'FINISHED'}
    
class ConnectBone(bpy.types.Operator):
    bl_idname = "object.connect_bone"
    bl_label = "重置骨骼端点位置（连接）"

    def execute(self, context):
        def connect_bones_recursive(armature, bone_name):
            bones = armature.data.edit_bones
            current_bone = bones.get(bone_name)
            
            if current_bone and current_bone.parent:
                # 检查子骨骼的起点是否与父骨骼的终点重合
                if (current_bone.head - current_bone.parent.tail).length < 1e-5:
                    # 如果重合且未连接时进行连接操作
                    if not current_bone.use_connect:
                        current_bone.use_connect = True

            # 递归处理子骨骼
            for child_bone in current_bone.children:
                connect_bones_recursive(armature, child_bone.name)

        def connect_selected_bones():
            armature = bpy.context.active_object
            
            if armature and armature.type == 'ARMATURE':
                # 存储当前模式
                original_mode = armature.mode

                # 确保在编辑模式中进行操作
                if original_mode != 'EDIT':
                    bpy.ops.object.mode_set(mode='EDIT')

                try:
                    for bone in bpy.context.selected_editable_bones:
                        connect_bones_recursive(armature, bone.name)
                finally:
                    # 切换回原始模式
                    if original_mode != 'EDIT':
                        bpy.ops.object.mode_set(mode=original_mode)
        # 运行该功能
        connect_selected_bones()


        return {'FINISHED'}
    
class ExportFbxWithoutParent(bpy.types.Operator):
    """导出FBX时不包含父级对象"""
    bl_idname = "scene.export_fbx_without_parent"
    bl_label = "导出FBX(无父级)"

    def execute(self, context):
        # 设置清除父级关系选项
        context.scene.clear_parent_on_export = True
        # 设置导出配置为max
        context.scene.export_config = 'max'
        # 调用面板中的导出操作符
        bpy.ops.scene.export_fbx_by_parent()
        # 恢复清除父级关系选项
        context.scene.clear_parent_on_export = False
        return {'FINISHED'}

def register():
    bpy.utils.register_class(BoneDataExporterPanel)
    bpy.utils.register_class(ExportBoneDataOperator)
    bpy.utils.register_class(RestoreEmptyDataOperator)
    bpy.utils.register_class(RestoreSkeletonFromJsonOperator)
    bpy.utils.register_class(RefreshJsonListOperator)
    bpy.utils.register_class(CharOperater)
    bpy.utils.register_class(RestoreBoneDataOperator)
    bpy.utils.register_class(OneClickOperator)
    bpy.utils.register_class(OperatorByPath)
    bpy.utils.register_class(OperationPath)
    bpy.types.Scene.batchtool = bpy.props.PointerProperty(type=OperationPath)
    bpy.types.Scene.json_file_list = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.json_file_index = bpy.props.IntProperty()
    bpy.types.Scene.show_bone_operators = bpy.props.BoolProperty(default=False)
    bpy.utils.register_class(ScaleAdjust)
    bpy.utils.register_class(WithCombinRename)
    bpy.utils.register_class(ConnectBone)
    bpy.utils.register_class(ResetBonePosition)
    bpy.utils.register_class(ExportFbxWithoutParent)
    
    # 角色工具属性
    bpy.types.Scene.config_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.character_process_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.character_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.replacement_blend_file = bpy.props.StringProperty(
        name="替换源文件",
        description="选择包含替换物体的.blend文件",
        subtype='FILE_PATH',
        default=""
    )
    bpy.types.Scene.enable_set_replacement = bpy.props.BoolProperty(
        name="套装替换",
        description="启用套装替换模式，将同套装的物体一起替换",
        default=False
    )
    

def unregister():
    bpy.utils.unregister_class(CharOperater)
    bpy.utils.unregister_class(BoneDataExporterPanel)
    bpy.utils.unregister_class(ExportBoneDataOperator)
    bpy.utils.unregister_class(RestoreEmptyDataOperator)
    bpy.utils.unregister_class(RestoreSkeletonFromJsonOperator)
    bpy.utils.unregister_class(RefreshJsonListOperator)
    bpy.utils.unregister_class(RestoreBoneDataOperator)
    bpy.utils.unregister_class(OneClickOperator)
    bpy.utils.unregister_class(OperatorByPath)
    bpy.utils.unregister_class(OperationPath)
    bpy.utils.unregister_class(ScaleAdjust)
    bpy.utils.unregister_class(WithCombinRename)
    bpy.utils.unregister_class(ConnectBone)
    bpy.utils.unregister_class(ResetBonePosition)
    bpy.utils.unregister_class(ExportFbxWithoutParent)

    # del bpy.types.Scene.my_tool
    del bpy.types.Scene.json_file_list
    del bpy.types.Scene.json_file_index
    
    # 删除角色工具属性
    del bpy.types.Scene.config_expand
    del bpy.types.Scene.character_process_expand
    del bpy.types.Scene.character_tools_expand
    del bpy.types.Scene.replacement_blend_file
    del bpy.types.Scene.enable_set_replacement
    
    del bpy.types.Scene.show_bone_operators

if __name__ == "__main__":
    register()