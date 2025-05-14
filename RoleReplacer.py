# -*- coding: utf-8 -*-

import bpy
import random
from bpy.props import StringProperty, EnumProperty

# 定义分类关键词列表，键是分类名，值是相关的关键词
categories = {
    "UpperBody": ["UpperBody", "Upper"],
    "LowerBody": ["LowerBody", "Lower"],
    "Eyebrow": ["Eyebrow"],
    "Feet": ["Feet"],
    "Mouse": ["Mouse", "Mouth"],  # 包含 Mouse 和 Mouth 两种写法
    "Head": ["Head"],
    "Hair": ["Hair"],
    "Nose": ["Nose"],
}

class MIAO_OT_RoleReplacer(bpy.types.Operator):
    """替换角色部件"""
    bl_idname = "object.miao_role_replacer"
    bl_label = "替换角色部件"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取场景中设置的集合
        source_collection = context.scene.collectionA
        target_collection = context.scene.collectionB

        # 用于存储分类结果（按分类存储物体）
        classified_objects = {key: [] for key in categories}

        # 遍历源集合中的物体并分类
        if source_collection:
            for obj in source_collection.objects:
                if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                    for category, keywords in categories.items():
                        if any(keyword in obj.name for keyword in keywords):
                            classified_objects[category].append(obj)  # 存储实际物体对象
                            break
        else:
            self.report({'ERROR'}, f"源集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        # 遍历目标集合中的物体
        if target_collection:
            for obj in target_collection.objects:
                if obj.type == 'MESH':  # 仅针对 Mesh 类型物体
                    for category, keywords in categories.items():
                        if any(keyword in obj.name for keyword in keywords):
                            # 检查源集合中是否有对应分类的物体
                            if classified_objects[category]:
                                # 从对应分类中随机选择一个物体的 Mesh 数据
                                random_obj = random.choice(classified_objects[category])
                                self.report({'INFO'}, f"将物体 '{obj.name}' 替换为 '{random_obj.name}' 的数据。")
                                
                                # 替换物体数据
                                obj.data = random_obj.data
                            else:
                                self.report({'WARNING'}, f"分类 '{category}' 中没有可替换的物体，跳过物体 '{obj.name}'。")
                            break
        else:
            self.report({'ERROR'}, f"目标集合不存在，请检查集合设置。")
            return {'CANCELLED'}

        return {'FINISHED'}

def register():
    bpy.utils.register_class(MIAO_OT_RoleReplacer)

def unregister():
    bpy.utils.unregister_class(MIAO_OT_RoleReplacer) 