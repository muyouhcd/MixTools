# -*- coding: utf-8 -*-

import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty

# 定义分类关键词列表，键是分类名，值是相关的关键词
categories = {
    "UpperBody": ["Upper"],
    "LowerBody": ["Lower"],
    "Eyebrow": ["Eyebrow"],
    "Feet": ["Feet"],
    "Mouse": ["Mouth"],  # 包含 Mouse 和 Mouth 两种写法
    "Top": ["Top"],
    "Bottom": ["Bottom"],
    "Hair": ["Hair"],
    "Nose": ["Nose"],
    "Eyes": ["Eyes"],
}

# 新增：定义分类关键词映射
classification_keywords = {
    "性别关键字": ["male", "female"],
    "部位关键词": ["Upper", "lower", "Feet", "mouth", "Top", "bottom", "hair", "nose", "eyes","Eyebrow"],
    "套装关键词": ["sets"]
}

def get_gender(obj_name):
    """获取物体的性别属性"""
    obj_name_lower = obj_name.lower()
    if "female" in obj_name_lower:
        return "female"
    elif "male" in obj_name_lower:
        return "male"
    return None

def parse_object_name(obj_name):
    """解析物体名称，提取性别、部位和套装信息"""
    name_parts = obj_name.split('_')
    result = {
        'gender': None,
        'parts': [],
        'is_set': False,
        'original_name': obj_name
    }
    
    for part in name_parts:
        part_lower = part.lower()
        
        # 检查性别
        if part_lower in ['male', 'female']:
            result['gender'] = part_lower
        
        # 检查部位
        if part_lower in ['upper', 'lower', 'feet', 'mouth', 'top', 'bottom', 'hair', 'nose', 'eyes', 'eyebrow']:
            result['parts'].append(part_lower)
        
        # 检查套装
        if part_lower == 'sets':
            result['is_set'] = True
    
    return result

def create_collection_hierarchy():
    """创建分类集合的层级结构"""
    # 创建主分类集合
    main_collection_name = "Object_Classification"
    main_collection = bpy.data.collections.get(main_collection_name)
    if not main_collection:
        main_collection = bpy.data.collections.new(main_collection_name)
        bpy.context.scene.collection.children.link(main_collection)
    
    # 创建性别子集合
    male_collection = bpy.data.collections.get("Male")
    if not male_collection:
        male_collection = bpy.data.collections.new("Male")
        main_collection.children.link(male_collection)
    
    female_collection = bpy.data.collections.get("Female")
    if not female_collection:
        female_collection = bpy.data.collections.new("Female")
        main_collection.children.link(female_collection)
    
    # 创建部位子集合
    parts = ['upper', 'lower', 'feet', 'mouth', 'top', 'bottom', 'hair', 'nose', 'eyes', 'eyebrow']
    
    for gender_collection in [male_collection, female_collection]:
        for part in parts:
            part_collection = bpy.data.collections.get(f"{gender_collection.name}_{part.capitalize()}")
            if not part_collection:
                part_collection = bpy.data.collections.new(f"{gender_collection.name}_{part.capitalize()}")
                gender_collection.children.link(part_collection)
    
    return main_collection

def classify_and_organize_objects():
    """分类并组织物体到对应集合"""
    # 创建集合层级结构
    main_collection = create_collection_hierarchy()
    
    # 获取所有选中的物体
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        return "没有选中任何物体"
    
    classified_count = 0
    unclassified_count = 0
    
    for obj in selected_objects:
        if obj.type != 'MESH':
            continue
            
        # 解析物体名称
        parsed_info = parse_object_name(obj.name)
        
        # 确定目标集合
        target_collection = None
        
        if parsed_info['gender']:
            # 根据性别确定主集合
            if parsed_info['gender'] == 'male':
                gender_collection = bpy.data.collections.get("Male")
            else:
                gender_collection = bpy.data.collections.get("Female")
            
            if gender_collection and parsed_info['parts']:
                # 使用第一个部位作为分类
                part = parsed_info['parts'][0]
                target_collection = bpy.data.collections.get(f"{gender_collection.name}_{part.capitalize()}")
        
        # 移动物体到目标集合
        if target_collection:
            # 从当前集合中移除
            for collection in obj.users_collection:
                collection.objects.unlink(obj)
            
            # 添加到目标集合
            target_collection.objects.link(obj)
            classified_count += 1
            print(f"物体 '{obj.name}' 已分类到集合 '{target_collection.name}'")
        else:
            unclassified_count += 1
            print(f"物体 '{obj.name}' 无法分类，缺少性别或部位信息")
    
    return f"分类完成：{classified_count} 个物体已分类，{unclassified_count} 个物体无法分类"

class mian_OT_ObjectClassifier(bpy.types.Operator):
    """根据名称关键字分类物体到集合"""
    bl_idname = "object.mian_object_classifier"
    bl_label = "按名称分类物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        result = classify_and_organize_objects()
        self.report({'INFO'}, result)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(mian_OT_ObjectClassifier)

def unregister():
    bpy.utils.unregister_class(mian_OT_ObjectClassifier) 