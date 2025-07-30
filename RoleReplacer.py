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
    try:
        print(f"尝试替换: 目标物体 '{target_obj.name}' (类型: {target_obj.type}) -> 源物体 '{source_obj.name}' (类型: {source_obj.type})")
        if target_obj.type != 'MESH' or source_obj.type != 'MESH':
            print(f"替换失败: 物体类型不匹配 - 目标: {target_obj.type}, 源: {source_obj.type}")
            return False
            
        if not target_obj.data or not source_obj.data:
            print(f"替换失败: 物体没有网格数据 - 目标: {bool(target_obj.data)}, 源: {bool(source_obj.data)}")
            return False
            
        # 直接关联源物体的网格数据
        target_obj.data = source_obj.data
        print(f"成功替换: '{target_obj.name}' 的数据已替换为 '{source_obj.name}' 的数据")
        return True
    except Exception as e:
        print(f"替换失败: {str(e)}")
        return False

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
        print(f"源物体 '{obj.name}' 的父级是 '{parent_key}'")
    
    # 按父级分组目标物体
    target_groups = {}
    for obj in target_objects:
        parent_key = obj.parent.name if obj.parent else "no_parent"
        if parent_key not in target_groups:
            target_groups[parent_key] = []
        target_groups[parent_key].append(obj)
        print(f"目标物体 '{obj.name}' 的父级是 '{parent_key}'")
    
    print(f"源物体父级组: {list(source_groups.keys())}")
    print(f"目标物体父级组: {list(target_groups.keys())}")
    
    # 匹配相同父级下的物体
    matches = []
    for parent_key in source_groups:
        if parent_key in target_groups:
            source_group = source_groups[parent_key]
            target_group = target_groups[parent_key]
            print(f"父级 '{parent_key}' 下: 源物体数量 {len(source_group)}, 目标物体数量 {len(target_group)}")
            
            # 对每个目标物体，找到对应的源物体
            for target_obj in target_group:
                # 找到与目标物体类型相同的源物体
                matching_sources = [s for s in source_group if s.type == target_obj.type]
                if matching_sources:
                    # 随机选择一个匹配的源物体
                    source_obj = random.choice(matching_sources)
                    matches.append((source_obj, target_obj))
                    print(f"匹配: 源物体 '{source_obj.name}' -> 目标物体 '{target_obj.name}'")
    
    return matches

class mian_OT_RoleReplacer(bpy.types.Operator):
    """替换角色部件"""
    bl_idname = "object.mian_role_replacer"
    bl_label = "随机替换角色部件"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取场景中设置的集合
        source_collection = context.scene.collectionA
        target_collection = context.scene.collectionB

        # 用于存储分类结果（按分类存储物体）
        classified_objects = {key: [] for key in categories}
        # 用于记录已使用的源物体
        used_objects = set()

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
            
            # 使用分类和性别匹配
            for obj in target_objects:
                if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                    target_gender = get_gender(obj.name)
                    for category, keywords in categories.items():
                        if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                            # 获取符合性别要求的未使用物体列表
                            matching_objects = [
                                source_obj for source_obj, source_gender in classified_objects[category]
                                if (source_gender == target_gender or (source_gender is None and target_gender is None))
                                and source_obj not in used_objects
                            ]
                            
                            if matching_objects:
                                # 随机打乱匹配的物体列表
                                random.shuffle(matching_objects)
                                random_obj = matching_objects[0]
                                self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                replace_object_data(obj, random_obj)
                                used_objects.add(random_obj)
                            else:
                                # 如果没有未使用的物体，则使用所有匹配的物体
                                all_matching_objects = [
                                    source_obj for source_obj, source_gender in classified_objects[category]
                                    if source_gender == target_gender or (source_gender is None and target_gender is None)
                                ]
                                if all_matching_objects:
                                    random.shuffle(all_matching_objects)
                                    random_obj = all_matching_objects[0]
                                    self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                    replace_object_data(obj, random_obj)
                                    used_objects.add(random_obj)
                                else:
                                    self.report({'WARNING'}, f"分类 '{category}' 中没有符合性别要求的可替换物体，跳过物体 '{obj.name}'。")
                            break
        else:
            self.report({'ERROR'}, f"目标集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        return {'FINISHED'}

class mian_OT_RoleReplacerParent(bpy.types.Operator):
    """基于父级关系替换角色部件"""
    bl_idname = "object.mian_role_replacer_parent"
    bl_label = "基于父级关系替换"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取场景中设置的集合
        source_collection = context.scene.collectionA
        target_collection = context.scene.collectionB

        # 用于记录已使用的源物体
        used_objects = set()

        if source_collection and target_collection:
            source_objects = get_all_objects_in_collection(source_collection)
            target_objects = get_all_objects_in_collection(target_collection)
            
            self.report({'INFO'}, f"源集合中有 {len(source_objects)} 个物体，目标集合中有 {len(target_objects)} 个物体。")
            print(f"源集合名称: {source_collection.name}")
            print(f"目标集合名称: {target_collection.name}")
            
            # 使用父级匹配
            parent_matches = find_matching_objects_by_parent(source_objects, target_objects)
            self.report({'INFO'}, f"找到 {len(parent_matches)} 对匹配的物体。")
            
            if not parent_matches:
                self.report({'WARNING'}, "没有找到匹配的物体，请检查物体的父级关系。")
                return {'CANCELLED'}
            
            success_count = 0
            for source_obj, target_obj in parent_matches:
                print(f"\n处理匹配对: '{target_obj.name}' -> '{source_obj.name}'")
                print(f"目标物体类型: {target_obj.type}")
                print(f"源物体类型: {source_obj.type}")
                
                if target_obj.type == 'MESH':
                    target_gender = get_gender(target_obj.name)
                    source_gender = get_gender(source_obj.name)
                    
                    print(f"目标物体性别: {target_gender}")
                    print(f"源物体性别: {source_gender}")
                    
                    # 检查性别是否匹配
                    if target_gender == source_gender or (target_gender is None and source_gender is None):
                        self.report({'INFO'}, f"将物体 '{target_obj.name}' 替换为 '{source_obj.name}' 的数据。")
                        if replace_object_data(target_obj, source_obj):
                            used_objects.add(source_obj)
                            success_count += 1
                    else:
                        self.report({'WARNING'}, f"物体 '{target_obj.name}' 和 '{source_obj.name}' 性别不匹配，跳过替换。")
                else:
                    print(f"跳过非网格物体: {target_obj.name}")
            
            self.report({'INFO'}, f"成功替换了 {success_count} 个物体。")
        else:
            self.report({'ERROR'}, f"源集合或目标集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        return {'FINISHED'}

class mian_OT_RoleReplacerSelected(bpy.types.Operator):
    """替换所选角色部件"""
    bl_idname = "object.mian_role_replacer_selected"
    bl_label = "随机替换所选部件"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取场景中设置的源集合
        source_collection = context.scene.collectionA
        
        if not source_collection:
            self.report({'ERROR'}, f"源集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        # 用于存储分类结果（按分类存储物体）
        classified_objects = {key: [] for key in categories}
        # 用于记录已使用的源物体
        used_objects = set()

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

        # 使用分类和性别匹配
        for obj in selected_objects:
            if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                target_gender = get_gender(obj.name)
                for category, keywords in categories.items():
                    if any(keyword.lower() in obj.name.lower() for keyword in keywords):
                        # 获取符合性别要求的未使用物体列表
                        matching_objects = [
                            source_obj for source_obj, source_gender in classified_objects[category]
                            if (source_gender == target_gender or (source_gender is None and target_gender is None))
                            and source_obj not in used_objects
                        ]
                        
                        if matching_objects:
                            # 随机打乱匹配的物体列表
                            random.shuffle(matching_objects)
                            random_obj = matching_objects[0]
                            self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                            replace_object_data(obj, random_obj)
                            used_objects.add(random_obj)
                        else:
                            # 如果没有未使用的物体，则使用所有匹配的物体
                            all_matching_objects = [
                                source_obj for source_obj, source_gender in classified_objects[category]
                                if source_gender == target_gender or (source_gender is None and target_gender is None)
                            ]
                            if all_matching_objects:
                                random.shuffle(all_matching_objects)
                                random_obj = all_matching_objects[0]
                                self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                replace_object_data(obj, random_obj)
                                used_objects.add(random_obj)
                            else:
                                self.report({'WARNING'}, f"分类 '{category}' 中没有符合性别要求的可替换物体，跳过物体 '{obj.name}'。")
                        break

        return {'FINISHED'}

class mian_OT_RoleReplacerSelectedParent(bpy.types.Operator):
    """基于父级关系替换所选角色部件"""
    bl_idname = "object.mian_role_replacer_selected_parent"
    bl_label = "基于父级关系替换所选"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取场景中设置的源集合
        source_collection = context.scene.collectionA
        
        if not source_collection:
            self.report({'ERROR'}, f"源集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        # 用于记录已使用的源物体
        used_objects = set()

        # 获取源集合中的所有物体
        source_objects = get_all_objects_in_collection(source_collection)
        
        # 获取选中的物体
        selected_objects = context.selected_objects

        self.report({'INFO'}, f"源集合中有 {len(source_objects)} 个物体，选中了 {len(selected_objects)} 个物体。")
        print(f"源集合名称: {source_collection.name}")
        print(f"选中的物体: {[obj.name for obj in selected_objects]}")

        # 使用父级匹配
        parent_matches = find_matching_objects_by_parent(source_objects, selected_objects)
        self.report({'INFO'}, f"找到 {len(parent_matches)} 对匹配的物体。")
        
        if not parent_matches:
            self.report({'WARNING'}, "没有找到匹配的物体，请检查物体的父级关系。")
            return {'CANCELLED'}
        
        success_count = 0
        for source_obj, target_obj in parent_matches:
            print(f"\n处理匹配对: '{target_obj.name}' -> '{source_obj.name}'")
            print(f"目标物体类型: {target_obj.type}")
            print(f"源物体类型: {source_obj.type}")
            
            if target_obj.type == 'MESH':
                target_gender = get_gender(target_obj.name)
                source_gender = get_gender(source_obj.name)
                
                print(f"目标物体性别: {target_gender}")
                print(f"源物体性别: {source_gender}")
                
                # 检查性别是否匹配
                if target_gender == source_gender or (target_gender is None and source_gender is None):
                    self.report({'INFO'}, f"将物体 '{target_obj.name}' 替换为 '{source_obj.name}' 的数据。")
                    if replace_object_data(target_obj, source_obj):
                        used_objects.add(source_obj)
                        success_count += 1
                else:
                    self.report({'WARNING'}, f"物体 '{target_obj.name}' 和 '{source_obj.name}' 性别不匹配，跳过替换。")
            else:
                print(f"跳过非网格物体: {target_obj.name}")
        
        self.report({'INFO'}, f"成功替换了 {success_count} 个物体。")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(mian_OT_RoleReplacer)
    bpy.utils.register_class(mian_OT_RoleReplacerParent)
    bpy.utils.register_class(mian_OT_RoleReplacerSelected)
    bpy.utils.register_class(mian_OT_RoleReplacerSelectedParent)

def unregister():
    bpy.utils.unregister_class(mian_OT_RoleReplacer)
    bpy.utils.unregister_class(mian_OT_RoleReplacerParent)
    bpy.utils.unregister_class(mian_OT_RoleReplacerSelected)
    bpy.utils.unregister_class(mian_OT_RoleReplacerSelectedParent) 