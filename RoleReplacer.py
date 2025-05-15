# -*- coding: utf-8 -*-

import bpy
import random
from bpy.props import StringProperty, EnumProperty, BoolProperty

# 定义分类关键词列表，键是分类名，值是相关的关键词
categories = {
    "UpperBody": ["UpperBody", "Upper"],
    "LowerBody": ["LowerBody", "Lower"],
    "Eyebrow": ["Eyebrow"],
    "Feet": ["Feet"],
    "Mouse": ["Mouse", "Mouth"],  # 包含 Mouse 和 Mouth 两种写法
    "Top": ["Top"],
    "Bottom": ["Bottom"],
    "Hair": ["Hair"],
    "Nose": ["Nose"],
    "Eyes": ["Eyes"],
}

def get_gender(obj_name):
    """获取物体的性别属性"""
    obj_name_lower = obj_name.lower()
    if "female" in obj_name_lower:
        return "female"
    elif "male" in obj_name_lower:
        return "male"
    return None

def replace_object_data(target_obj, source_obj):
    """替换物体数据的通用函数，使用关联数据"""
    # 直接关联源物体的网格数据
    target_obj.data = source_obj.data

def get_all_objects_in_collection(collection):
    """递归获取集合及其所有子集合中的物体"""
    objects = []
    # 添加当前集合中的物体
    objects.extend(collection.objects)
    # 递归处理所有子集合
    for child in collection.children:
        objects.extend(get_all_objects_in_collection(child))
    return objects

def find_matching_objects_by_parent(source_objects, target_objects):
    """根据父级关系匹配物体"""
    # 按父级分组源物体
    source_groups = {}
    for obj in source_objects:
        parent_key = obj.parent.name if obj.parent else "no_parent"
        if parent_key not in source_groups:
            source_groups[parent_key] = []
        source_groups[parent_key].append(obj)
    
    # 按父级分组目标物体
    target_groups = {}
    for obj in target_objects:
        parent_key = obj.parent.name if obj.parent else "no_parent"
        if parent_key not in target_groups:
            target_groups[parent_key] = []
        target_groups[parent_key].append(obj)
    
    # 匹配相同父级下的物体
    matches = []
    for parent_key in source_groups:
        if parent_key in target_groups:
            source_group = source_groups[parent_key]
            target_group = target_groups[parent_key]
            if len(source_group) == len(target_group):
                matches.extend(zip(source_group, target_group))
    
    return matches

class MIAO_OT_RoleReplacer(bpy.types.Operator):
    """替换角色部件"""
    bl_idname = "object.miao_role_replacer"
    bl_label = "替换角色部件"
    bl_options = {'REGISTER', 'UNDO'}

    use_parent_matching: bpy.props.BoolProperty(
        name="使用父级匹配",
        description="是否使用父级关系进行匹配",
        default=False
    )

    def execute(self, context):
        # 获取场景中设置的集合
        source_collection = context.scene.collectionA
        target_collection = context.scene.collectionB

        # 用于存储分类结果（按分类存储物体）
        classified_objects = {key: [] for key in categories}

        # 遍历源集合中的物体并分类（包括子集合）
        if source_collection:
            source_objects = get_all_objects_in_collection(source_collection)
            for obj in source_objects:
                if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                    obj_gender = get_gender(obj.name)
                    for category, keywords in categories.items():
                        if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                            # 存储物体对象和其性别信息
                            classified_objects[category].append((obj, obj_gender))
                            break
        else:
            self.report({'ERROR'}, f"源集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        # 遍历目标集合中的物体（包括子集合）
        if target_collection:
            target_objects = get_all_objects_in_collection(target_collection)
            
            if self.use_parent_matching:
                # 使用父级匹配
                parent_matches = find_matching_objects_by_parent(source_objects, target_objects)
                for source_obj, target_obj in parent_matches:
                    if target_obj.type == 'MESH':
                        target_gender = get_gender(target_obj.name)
                        source_gender = get_gender(source_obj.name)
                        
                        # 检查性别是否匹配
                        if target_gender == source_gender or (target_gender is None and source_gender is None):
                            self.report({'INFO'}, f"将物体 '{target_obj.name}' 替换为 '{source_obj.name}' 的数据。")
                            replace_object_data(target_obj, source_obj)
                        else:
                            self.report({'WARNING'}, f"物体 '{target_obj.name}' 和 '{source_obj.name}' 性别不匹配，跳过替换。")
            else:
                # 使用分类和性别匹配
                for obj in target_objects:
                    if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                        target_gender = get_gender(obj.name)
                        for category, keywords in categories.items():
                            if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                                # 获取符合性别要求的物体列表
                                matching_objects = [
                                    source_obj for source_obj, source_gender in classified_objects[category]
                                    if source_gender == target_gender or (source_gender is None and target_gender is None)
                                ]
                                
                                if matching_objects:
                                    # 随机打乱匹配的物体列表
                                    random.shuffle(matching_objects)
                                    random_obj = matching_objects[0]
                                    self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                    replace_object_data(obj, random_obj)
                                else:
                                    self.report({'WARNING'}, f"分类 '{category}' 中没有符合性别要求的可替换物体，跳过物体 '{obj.name}'。")
                                break
        else:
            self.report({'ERROR'}, f"目标集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        return {'FINISHED'}

class MIAO_OT_RoleReplacerSelected(bpy.types.Operator):
    """替换所选角色部件"""
    bl_idname = "object.miao_role_replacer_selected"
    bl_label = "替换所选角色部件"
    bl_options = {'REGISTER', 'UNDO'}

    use_parent_matching: bpy.props.BoolProperty(
        name="使用父级匹配",
        description="是否使用父级关系进行匹配",
        default=False
    )

    def execute(self, context):
        # 获取场景中设置的源集合
        source_collection = context.scene.collectionA
        
        if not source_collection:
            self.report({'ERROR'}, f"源集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        # 用于存储分类结果（按分类存储物体）
        classified_objects = {key: [] for key in categories}

        # 遍历源集合中的物体并分类（包括子集合）
        source_objects = get_all_objects_in_collection(source_collection)
        for obj in source_objects:
            if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                obj_gender = get_gender(obj.name)
                for category, keywords in categories.items():
                    if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                        # 存储物体对象和其性别信息
                        classified_objects[category].append((obj, obj_gender))
                        break

        # 获取选中的物体
        selected_objects = context.selected_objects

        if self.use_parent_matching:
            # 使用父级匹配
            parent_matches = find_matching_objects_by_parent(source_objects, selected_objects)
            for source_obj, target_obj in parent_matches:
                if target_obj.type == 'MESH':
                    target_gender = get_gender(target_obj.name)
                    source_gender = get_gender(source_obj.name)
                    
                    # 检查性别是否匹配
                    if target_gender == source_gender or (target_gender is None and source_gender is None):
                        self.report({'INFO'}, f"将物体 '{target_obj.name}' 替换为 '{source_obj.name}' 的数据。")
                        replace_object_data(target_obj, source_obj)
                    else:
                        self.report({'WARNING'}, f"物体 '{target_obj.name}' 和 '{source_obj.name}' 性别不匹配，跳过替换。")
        else:
            # 使用分类和性别匹配
            for obj in selected_objects:
                if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                    target_gender = get_gender(obj.name)
                    for category, keywords in categories.items():
                        if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                            # 获取符合性别要求的物体列表
                            matching_objects = [
                                source_obj for source_obj, source_gender in classified_objects[category]
                                if source_gender == target_gender or (source_gender is None and target_gender is None)
                            ]
                            
                            if matching_objects:
                                # 随机打乱匹配的物体列表
                                random.shuffle(matching_objects)
                                random_obj = matching_objects[0]
                                self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                replace_object_data(obj, random_obj)
                            else:
                                self.report({'WARNING'}, f"分类 '{category}' 中没有符合性别要求的可替换物体，跳过物体 '{obj.name}'。")
                            break

        return {'FINISHED'}

def register():
    bpy.utils.register_class(MIAO_OT_RoleReplacer)
    bpy.utils.register_class(MIAO_OT_RoleReplacerSelected)

def unregister():
    bpy.utils.unregister_class(MIAO_OT_RoleReplacer)
    bpy.utils.unregister_class(MIAO_OT_RoleReplacerSelected) 