# -*- coding: utf-8 -*-

import bpy
import bmesh
import random
import os
import time
from bpy.props import StringProperty, EnumProperty, BoolProperty

# 物体分类关键词定义
GENDER_KEYWORDS = ['male', 'female']
BODY_PART_KEYWORDS = ['upper', 'lower', 'feet', 'mouth', 'top', 'bottom', 'hair', 'nose', 'eyes', 'eyebrow', 'head', 'pieces', 'mouse']
SET_KEYWORDS = ['sets']

def diagnose_object_parsing(obj_name):
    """诊断物体名称解析过程
    
    Args:
        obj_name: 物体名称
        
    Returns:
        dict: 解析结果和诊断信息
    """
    print(f"\n🔍 诊断物体名称解析: {obj_name}")
    
    import re
    
    # 去除Blender自动添加的序号
    base_name = re.sub(r'\.\d{3}$', '', obj_name)
    print(f"  基础名称: {base_name}")
    
    name_parts = base_name.split('_')
    print(f"  分割结果: {name_parts}")
    
    result = {
        'gender': None,
        'parts': [],
        'is_set': False,
        'original_name': obj_name,
        'base_name': base_name
    }
    
    print(f"\n  关键词匹配过程:")
    for i, part in enumerate(name_parts):
        part_lower = part.lower()
        print(f"    [{i}] '{part}' -> '{part_lower}'")
        
        # 检查性别
        if part_lower in GENDER_KEYWORDS:
            result['gender'] = part_lower
            print(f"        ✅ 性别匹配: {part_lower}")
        else:
            print(f"        ❌ 性别不匹配")
        
        # 检查部位
        if part_lower in BODY_PART_KEYWORDS:
            result['parts'].append(part_lower)
            print(f"        ✅ 部位匹配: {part_lower}")
        else:
            print(f"        ❌ 部位不匹配")
        
        # 检查套装
        if part_lower in SET_KEYWORDS:
            result['is_set'] = True
            print(f"        ✅ 套装匹配: {part_lower}")
        else:
            print(f"        ❌ 套装不匹配")
    
    print(f"\n  最终解析结果:")
    print(f"    性别: {result['gender']}")
    print(f"    部位: {result['parts']}")
    print(f"    套装: {result['is_set']}")
    
    return result

def is_exact_part_match(source_parts, target_parts):
    """检查部件是否精确匹配（忽略大小写）
    
    Args:
        source_parts: 源部件列表
        target_parts: 目标部件列表
        
    Returns:
        bool: 是否精确匹配
    """
    # 转换为小写进行比较
    source_set = set(part.lower() for part in source_parts)
    target_set = set(part.lower() for part in target_parts)
    
    # 严格匹配：源部件和目标部件必须完全相同
    return source_set == target_set and len(source_set) > 0

def find_matching_random_target(source_gender, source_parts, target_objects):
    """通用的随机替换函数，根据性别和部件类型查找匹配的目标
    
    Args:
        source_gender: 源物体性别
        source_parts: 源物体部件列表
        target_objects: 目标物体列表
        
    Returns:
        dict or None: 匹配的目标物体，如果没有匹配则返回None
    """
    matching_targets = []
    
    for target_obj in target_objects:
        target_parsed = parse_object_name(target_obj['name'])
        
        # 检查性别和部件是否匹配
        if (target_parsed['gender'] == source_gender and 
            is_exact_part_match(source_parts, target_parsed['parts'])):
            matching_targets.append(target_obj)
    
    if matching_targets:
        target_obj = random.choice(matching_targets)
        print(f"   🎯 精确匹配随机替换: 性别={source_gender}, 部件={source_parts} -> {target_obj['name']}")
        return target_obj
    else:
        print(f"   ⏭️ 跳过：无性别={source_gender}和部件={source_parts}匹配的目标")
        return None

def test_set_grouping():
    """测试套装分组功能"""
    test_objects = [
        "Mod_Female_Sets_Upper_ClothingStoreNPC_001_Red_Lod0.001",
        "Mod_Female_Sets_Lower_ClothingStoreNPC_001_Red_Lod0.003"
    ]
    
    print("🔍 测试套装分组:")
    print("=" * 60)
    
    for obj_name in test_objects:
        parsed = parse_object_name(obj_name)
        print(f"\n物体: {obj_name}")
        print(f"  性别: {parsed['gender']}")
        print(f"  部位: {parsed['parts']}")
        print(f"  套装: {parsed['is_set']}")
        
        # 模拟分组逻辑
        name_parts = obj_name.split('_')
        set_parts = []
        
        for part in name_parts:
            part_lower = part.lower()
            if part_lower not in GENDER_KEYWORDS + BODY_PART_KEYWORDS + SET_KEYWORDS:
                set_parts.append(part)
        
        if set_parts:
            set_id = f"{parsed['gender']}_{'_'.join(set_parts)}"
            base_name = '_'.join(set_parts)
        else:
            set_id = f"{parsed['gender']}_sets"
            base_name = f"{parsed['gender']}_sets"
        
        print(f"  套装ID: {set_id}")
        print(f"  基础名称: {base_name}")
    
    print("=" * 60)

def initialize_random_seed():
    """初始化随机数种子"""
    # 使用当前时间戳作为种子，确保每次运行都有不同的随机性
    # 添加更多随机性因素
    import hashlib
    seed_data = f"{time.time()}_{random.random()}_{id(bpy.context)}"
    seed = int(hashlib.md5(seed_data.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    print(f"随机数种子已初始化: {seed}")

def snapshot_object_state(obj):
    """拍摄物体状态快照
    
    Args:
        obj: 要拍摄的物体对象
        
    Returns:
        dict: 物体状态信息
    """
    if not obj or obj.name not in bpy.data.objects:
        return {'exists': False}
    
    try:
        collections = [c.name for c in obj.users_collection] if hasattr(obj, 'users_collection') else []
        data_name = obj.data.name if getattr(obj, 'data', None) else None
        data_users = getattr(obj.data, 'users', None) if getattr(obj, 'data', None) else None
        
        return {
            'exists': True,
            'name': obj.name,
            'visible_viewport': not obj.hide_viewport,
            'visible_render': not obj.hide_render,
            'in_collections': collections,
            'collection_count': len(collections),
            'data_name': data_name,
            'data_users': data_users,
            'type': obj.type if hasattr(obj, 'type') else None,
            'location': tuple(obj.location) if hasattr(obj, 'location') else None,
            'parent': obj.parent.name if obj.parent else None,
        }
    except Exception as e:
        return {'exists': False, 'error': str(e)}

def diff_states(before, after, obj_name):
    """对比物体状态差异
    
    Args:
        before: 替换前状态
        after: 替换后状态
        obj_name: 物体名称
        
    Returns:
        str: 差异描述
    """
    if not before.get('exists', False) and not after.get('exists', False):
        return f"[{obj_name}] 前后都不存在"
    
    if before.get('exists', False) and not after.get('exists', False):
        return f"[{obj_name}] ❌ 替换后对象不存在（疑似被删除）"
    
    if not before.get('exists', False) and after.get('exists', False):
        return f"[{obj_name}] ✅ 替换后对象重新出现"
    
    msgs = []
    
    # 检查集合链接
    if before.get('collection_count', 0) > 0 and after.get('collection_count', 0) == 0:
        msgs.append("❌ 对象未链接到任何集合（Outliner看不到）")
    
    # 检查可见性
    if not after.get('visible_viewport', True):
        msgs.append("⚠️ 对象视口隐藏")
    
    if not after.get('visible_render', True):
        msgs.append("⚠️ 对象渲染隐藏")
    
    # 检查网格数据
    if before.get('data_name') and not after.get('data_name'):
        msgs.append("❌ 对象网格数据丢失")
    
    if after.get('data_name') and after.get('data_users') == 0:
        msgs.append("⚠️ 对象网格数据users==0（可能被清理）")
    
    # 检查集合变更
    if before.get('in_collections') != after.get('in_collections'):
        msgs.append(f"📁 集合变更: {before.get('in_collections')} -> {after.get('in_collections')}")
    
    # 检查网格变更
    if before.get('data_name') != after.get('data_name'):
        msgs.append(f"🔧 网格变更: {before.get('data_name')} -> {after.get('data_name')}")
    
    return f"[{obj_name}] " + ("；".join(msgs) if msgs else "✅ 状态正常")

def log_replacement_step(step_name, obj_name, details=""):
    """记录替换步骤日志
    
    Args:
        step_name: 步骤名称
        obj_name: 物体名称
        details: 详细信息
    """
    # 检查是否启用诊断
    scene = bpy.context.scene
    if not getattr(scene, 'enable_replacement_diagnostics', False):
        return
    
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] 🔍 {step_name} - {obj_name}: {details}")

def validate_imported_object(obj):
    """验证导入的物体是否有效
    
    Args:
        obj: 要验证的物体
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not obj:
        return False, "物体对象为空"
    
    if obj.name not in bpy.data.objects:
        return False, "物体不在bpy.data.objects中"
    
    if obj.type != 'MESH':
        return False, f"物体类型不是MESH: {obj.type}"
    
    if not obj.data:
        return False, "物体没有网格数据"
    
    if not hasattr(obj.data, 'vertices') or len(obj.data.vertices) == 0:
        return False, "网格数据没有顶点"
    
    if not hasattr(obj.data, 'polygons') or len(obj.data.polygons) == 0:
        return False, "网格数据没有面"
    
    return True, "验证通过"

def log_imported_object_validation(obj_name, obj, prefix=""):
    """记录导入物体的验证信息
    
    Args:
        obj_name: 物体名称
        obj: 物体对象
        prefix: 前缀
    """
    is_valid, error_msg = validate_imported_object(obj)
    if is_valid:
        vertices_count = len(obj.data.vertices) if obj.data else 0
        polygons_count = len(obj.data.polygons) if obj.data else 0
        print(f"{prefix}[{obj_name}] ✅ 验证通过 - 顶点:{vertices_count} 面:{polygons_count}")
    else:
        print(f"{prefix}[{obj_name}] ❌ 验证失败 - {error_msg}")
    
    return is_valid

def validate_replacement_consistency(replacement_plan):
    """验证替换计划的一致性，检查是否有部件类型错误替换
    
    Args:
        replacement_plan: 替换计划列表
        
    Returns:
        dict: 验证结果统计
    """
    print(f"\n🔍 验证替换计划一致性...")
    
    # 统计部件类型
    source_parts_count = {}
    target_parts_count = {}
    part_mapping = {}
    
    for source_obj, target_obj in replacement_plan:
        source_info = parse_object_name(source_obj.name)
        target_info = target_obj['parsed_info']
        
        # 统计源部件
        for part in source_info['parts']:
            source_parts_count[part] = source_parts_count.get(part, 0) + 1
        
        # 统计目标部件
        for part in target_info['parts']:
            target_parts_count[part] = target_parts_count.get(part, 0) + 1
        
        # 记录部件映射
        for source_part in source_info['parts']:
            if source_part not in part_mapping:
                part_mapping[source_part] = []
            part_mapping[source_part].extend(target_info['parts'])
    
    print(f"\n📊 部件类型统计:")
    print(f"  源部件: {source_parts_count}")
    print(f"  目标部件: {target_parts_count}")
    
    print(f"\n🔗 部件映射关系:")
    for source_part, target_parts in part_mapping.items():
        unique_targets = list(set(target_parts))
        print(f"  {source_part} -> {unique_targets}")
        
        # 检查是否有错误的映射
        if source_part not in unique_targets:
            print(f"    ⚠️ 警告: {source_part} 被替换为其他类型部件")
    
    # 检查是否有部件类型冲突
    conflicts = []
    for source_part, target_parts in part_mapping.items():
        if source_part not in target_parts:
            conflicts.append(f"{source_part} -> {list(set(target_parts))}")
    
    if conflicts:
        print(f"\n❌ 发现部件类型冲突:")
        for conflict in conflicts:
            print(f"  {conflict}")
    else:
        print(f"\n✅ 部件类型映射正常")
    
    return {
        'source_parts': source_parts_count,
        'target_parts': target_parts_count,
        'part_mapping': part_mapping,
        'conflicts': conflicts
    }

def validate_replacement_results(replacement_plan):
    """验证替换结果，检查替换后的物体部件类型是否正确
    
    Args:
        replacement_plan: 替换计划列表
        
    Returns:
        dict: 验证结果
    """
    print(f"\n🔍 验证替换结果...")
    
    correct_replacements = 0
    incorrect_replacements = 0
    part_type_errors = []
    
    for source_obj, target_obj in replacement_plan:
        source_info = parse_object_name(source_obj.name)
        target_info = target_obj['parsed_info']
        
        # 检查部件类型是否匹配
        source_parts = set(source_info['parts'])
        target_parts = set(target_info['parts'])
        
        # 检查是否有完全匹配的部件
        exact_matches = source_parts.intersection(target_parts)
        
        if exact_matches:
            correct_replacements += 1
            print(f"  ✅ {source_obj.name} -> {target_obj['name']} (匹配部件: {list(exact_matches)})")
        else:
            incorrect_replacements += 1
            part_type_errors.append({
                'source': source_obj.name,
                'target': target_obj['name'],
                'source_parts': list(source_parts),
                'target_parts': list(target_parts)
            })
            print(f"  ❌ {source_obj.name} -> {target_obj['name']}")
            print(f"      源部件: {list(source_parts)}")
            print(f"      目标部件: {list(target_parts)}")
            print(f"      ⚠️ 部件类型不匹配，可能导致视觉上的'消失'")
    
    print(f"\n📊 替换结果验证:")
    print(f"  正确替换: {correct_replacements}")
    print(f"  错误替换: {incorrect_replacements}")
    
    if part_type_errors:
        print(f"\n❌ 发现部件类型错误:")
        for error in part_type_errors:
            print(f"  {error['source']} ({error['source_parts']}) -> {error['target']} ({error['target_parts']})")
    
    return {
        'correct': correct_replacements,
        'incorrect': incorrect_replacements,
        'errors': part_type_errors
    }

def log_object_state(obj_name, state_snapshot, prefix=""):
    """记录物体状态日志
    
    Args:
        obj_name: 物体名称
        state_snapshot: 状态快照
        prefix: 前缀
    """
    # 检查是否启用诊断
    scene = bpy.context.scene
    if not getattr(scene, 'enable_replacement_diagnostics', False):
        return
    
    if not state_snapshot.get('exists', False):
        print(f"{prefix}[{obj_name}] ❌ 对象不存在")
        return
    
    collections = state_snapshot.get('in_collections', [])
    data_name = state_snapshot.get('data_name', 'None')
    data_users = state_snapshot.get('data_users', 'N/A')
    
    print(f"{prefix}[{obj_name}] 集合:{collections} 网格:{data_name}(users:{data_users}) 可见:{state_snapshot.get('visible_viewport', False)}")

def weighted_random_choice(targets, used_targets=None):
    """带权重的随机选择，避免重复选择
    
    Args:
        targets (list): 目标物体列表或元组列表
        used_targets (set): 已使用的目标物体名称集合
        
    Returns:
        dict or tuple: 选择的目标物体
    """
    if not targets:
        return None
    
    if not used_targets:
        return random.choice(targets)
    
    # 分离已使用和未使用的目标
    unused_targets = []
    used_targets_list = []
    
    for target in targets:
        # 处理元组格式 (id, set_info) 或字典格式
        if isinstance(target, tuple):
            target_id = target[0]
        else:
            target_id = target['name']
            
        if target_id in used_targets:
            used_targets_list.append(target)
        else:
            unused_targets.append(target)
    
    # 优先选择未使用的目标
    if unused_targets:
        return random.choice(unused_targets)
    elif used_targets_list:
        # 如果所有目标都已使用，随机选择一个
        return random.choice(used_targets_list)
    else:
        return random.choice(targets)

def parse_object_name(obj_name):
    """解析物体名称，提取性别、部位和套装信息
    
    Args:
        obj_name (str): 物体名称
        
    Returns:
        dict: 包含解析结果的字典
            - gender: 性别 ('male'/'female' 或 None)
            - parts: 部位列表
            - is_set: 是否为套装
            - original_name: 原始名称
            - base_name: 去除序号的基础名称
    """
    import re
    
    # 去除Blender自动添加的序号（如 .001, .002 等）
    base_name = re.sub(r'\.\d{3}$', '', obj_name)
    
    name_parts = base_name.split('_')
    result = {
        'gender': None,
        'parts': [],
        'is_set': False,
        'original_name': obj_name,
        'base_name': base_name
    }
    
    for part in name_parts:
        part_lower = part.lower()
        
        # 检查性别
        if part_lower in GENDER_KEYWORDS:
            result['gender'] = part_lower
        
        # 检查部位
        if part_lower in BODY_PART_KEYWORDS:
            result['parts'].append(part_lower)
        
        # 检查套装
        if part_lower in SET_KEYWORDS:
            result['is_set'] = True
    
    return result

def create_hidden_import_collection():
    """创建不可见不可渲染的固定集合来存储导入的物体
    
    Returns:
        bpy.types.Collection: 隐藏的导入集合
    """
    collection_name = "Hidden_Imported_Objects"
    hidden_collection = bpy.data.collections.get(collection_name)
    
    if not hidden_collection:
        hidden_collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(hidden_collection)
        
        # 设置为不可见和不可渲染
        hidden_collection.hide_viewport = True
        hidden_collection.hide_render = True
        
        print(f"创建隐藏导入集合: {collection_name}")
    
    return hidden_collection

def create_collection_hierarchy():
    """创建分类集合的层级结构
    
    Returns:
        bpy.types.Collection: 主分类集合
    """
    # 创建主分类集合
    main_collection_name = "Object_Classification"
    main_collection = bpy.data.collections.get(main_collection_name)
    if not main_collection:
        main_collection = bpy.data.collections.new(main_collection_name)
        bpy.context.scene.collection.children.link(main_collection)
    
    # 创建性别子集合
    gender_collections = {}
    for gender in GENDER_KEYWORDS:
        gender_name = gender.capitalize()
        gender_collection = bpy.data.collections.get(gender_name)
        if not gender_collection:
            gender_collection = bpy.data.collections.new(gender_name)
            main_collection.children.link(gender_collection)
        gender_collections[gender] = gender_collection
    
    # 创建部位子集合
    for gender, gender_collection in gender_collections.items():
        for part in BODY_PART_KEYWORDS:
            part_collection_name = f"{gender_collection.name}_{part.capitalize()}"
            part_collection = bpy.data.collections.get(part_collection_name)
            if not part_collection:
                part_collection = bpy.data.collections.new(part_collection_name)
                gender_collection.children.link(part_collection)
    
    return main_collection

def classify_and_organize_objects():
    """分类并组织物体到对应集合
    
    Returns:
        str: 分类结果信息
    """
    # 创建集合层级结构
    create_collection_hierarchy()
    
    # 获取所有选中的物体
    selected_objects = bpy.context.selected_objects
    
    if not selected_objects:
        return "没有选中任何物体"
    
    classified_count = 0
    unclassified_count = 0
    mesh_objects = [obj for obj in selected_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        return "选中的物体中没有网格物体"
    
    for obj in mesh_objects:
        # 解析物体名称
        parsed_info = parse_object_name(obj.name)
        
        # 确定目标集合
        target_collection = None
        
        if parsed_info['gender'] and parsed_info['parts']:
            # 根据性别和部位确定目标集合
            gender_name = parsed_info['gender'].capitalize()
            part_name = parsed_info['parts'][0].capitalize()
            target_collection_name = f"{gender_name}_{part_name}"
            target_collection = bpy.data.collections.get(target_collection_name)
        
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
            missing_info = []
            if not parsed_info['gender']:
                missing_info.append("性别")
            if not parsed_info['parts']:
                missing_info.append("部位")
            print(f"物体 '{obj.name}' 无法分类，缺少: {', '.join(missing_info)}")
    
    return f"分类完成：{classified_count} 个物体已分类，{unclassified_count} 个物体无法分类"

def check_object_exists_in_hidden_collection(obj_name):
    """检查物体是否已存在于隐藏集合中
    
    Args:
        obj_name (str): 物体名称
        
    Returns:
        bpy.types.Object or None: 如果存在返回物体对象，否则返回None
    """
    hidden_collection = bpy.data.collections.get("Hidden_Imported_Objects")
    if not hidden_collection:
        return None
    
    # 检查隐藏集合中是否存在同名物体
    for obj in hidden_collection.objects:
        if obj.name == obj_name:
            return obj
    
    return None

def load_objects_from_blend(file_path):
    """从.blend文件加载物体信息（改进版本 - 检查重复导入）
    
    Args:
        file_path (str): .blend文件路径
        
    Returns:
        list: 包含物体信息的字典列表
    """
    # 处理文件路径
    file_path = bpy.path.abspath(file_path)
    print(f"尝试加载文件: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return []
    
    objects_info = []
    
    try:
        # 新方法：只读取文件信息，不导入到场景
        print(f"正在读取文件信息: {file_path}")
        
        # 使用 bpy.data.libraries.load 只读取信息，不导入
        with bpy.data.libraries.load(file_path, link=False) as (data_from, data_to):
            # 只处理网格物体
            mesh_objects = [name for name in data_from.objects if name in data_from.meshes]
            print(f"找到 {len(mesh_objects)} 个网格物体")
            
            # 为每个网格物体创建信息，检查是否已存在
            for obj_name in mesh_objects:
                try:
                    # 检查物体是否已存在于隐藏集合中
                    existing_obj = check_object_exists_in_hidden_collection(obj_name)
                    
                    # 解析物体名称
                    parsed_info = parse_object_name(obj_name)
                    
                    # 检查是否包含有效信息
                    if parsed_info['gender'] and parsed_info['parts']:
                        # 创建物体信息
                        obj_info = {
                            'name': obj_name,
                            'object': existing_obj,  # 如果已存在则使用现有物体
                            'parsed_info': parsed_info,
                            'location': (0, 0, 0),  # 默认位置
                            'rotation': (0, 0, 0),  # 默认旋转
                            'scale': (1, 1, 1),     # 默认缩放
                            'already_imported': existing_obj is not None  # 标记是否已导入
                        }
                        
                        objects_info.append(obj_info)
                        
                        if existing_obj:
                            print(f"  ✓ 物体 '{obj_name}' 已存在，直接引用")
                        else:
                            print(f"  + 物体 '{obj_name}' 需要导入")
                            
                except Exception as e:
                    print(f"处理物体 {obj_name} 时出错: {e}")
                    continue
        
        print(f"文件读取完成: 总网格物体 {len(mesh_objects)} 个，有效物体 {len(objects_info)} 个")
        
        # 如果没有找到符合命名规范的物体，但有网格物体，则提供备用方案
        if len(mesh_objects) > 0 and len(objects_info) == 0:
            print("警告: 没有找到符合命名规范的物体，尝试加载所有网格物体...")
            
            # 提供备用加载选项：加载所有网格物体（不进行命名过滤）
            for obj_name in mesh_objects:
                try:
                    # 检查物体是否已存在于隐藏集合中
                    existing_obj = check_object_exists_in_hidden_collection(obj_name)
                    
                    # 创建基本的解析信息
                    basic_info = {
                        'gender': 'unknown',
                        'parts': ['unknown'],
                        'is_set': False,
                        'original_name': obj_name,
                        'base_name': obj_name
                    }
                    
                    obj_info = {
                        'name': obj_name,
                        'object': existing_obj,  # 如果已存在则使用现有物体
                        'parsed_info': basic_info,
                        'location': (0, 0, 0),
                        'rotation': (0, 0, 0),
                        'scale': (1, 1, 1),
                        'already_imported': existing_obj is not None
                    }
                    
                    objects_info.append(obj_info)
                    
                    if existing_obj:
                        print(f"  ✓ 物体 '{obj_name}' 已存在，直接引用")
                    else:
                        print(f"  + 物体 '{obj_name}' 需要导入")
                        
                except Exception as e:
                    print(f"备用加载 {obj_name} 时出错: {e}")
                    continue
            
            print(f"备用加载完成: 共加载 {len(objects_info)} 个物体")
        
    except Exception as e:
        print(f"读取.blend文件时出错: {e}")
        return []
    
    return objects_info

def find_matching_objects(source_objects, target_objects):
    """找到匹配的物体
    
    Args:
        source_objects (list): 源物体列表（当前选中的物体）
        target_objects (list): 目标物体列表（从.blend文件加载的物体）
        
    Returns:
        dict: 匹配结果字典
    """
    matches = {}
    
    print(f"\n🔍 开始匹配: 源物体 {len(source_objects)} 个，目标物体 {len(target_objects)} 个")
    
    for source_obj in source_objects:
        # 注意：source_objects 现在只包含网格物体，但为了安全起见保留检查
        if source_obj.type != 'MESH':
            print(f"  ⚠️ 跳过非网格物体: {source_obj.name} (类型: {source_obj.type})")
            continue
            
        source_info = parse_object_name(source_obj.name)
        
        if not source_info['gender'] or not source_info['parts']:
            print(f"  ⚠️ 跳过无效物体: {source_obj.name} (性别: {source_info['gender']}, 部位: {source_info['parts']})")
            continue
        
        print(f"\n  🎯 匹配源物体: {source_obj.name}")
        print(f"      性别: {source_info['gender']}, 部位: {source_info['parts']}")
        
        # 如果是 mouth 部件，进行详细诊断
        if 'mouth' in source_info['parts']:
            print(f"      🔍 检测到 mouth 部件，进行详细诊断...")
            diagnose_object_parsing(source_obj.name)
        
        # 找到匹配的目标物体
        matching_targets = []
        best_match_score = 0
        
        for target_obj in target_objects:
            target_info = target_obj['parsed_info']
            
            # 检查性别是否匹配
            gender_match = source_info['gender'] == target_info['gender']
            
            if not gender_match:
                print(f"      ❌ 性别不匹配: {target_obj['name']} (源: {source_info['gender']}, 目标: {target_info['gender']})")
                continue
            
            # 检查部件是否精确匹配
            is_exact_match = is_exact_part_match(source_info['parts'], target_info['parts'])
            
            if is_exact_match:
                source_parts = set(source_info['parts'])
                target_parts = set(target_info['parts'])
                exact_matches = source_parts.intersection(target_parts)
                
                print(f"      ✅ 精确匹配: {target_obj['name']} (匹配部件: {list(exact_matches)})")
                matching_targets.append(target_obj)
            else:
                source_parts = set(source_info['parts'])
                target_parts = set(target_info['parts'])
                print(f"      ❌ 部位不匹配: {target_obj['name']} (源: {list(source_parts)}, 目标: {list(target_parts)})")
                print(f"         💡 不是精确匹配")
        
        if matching_targets:
            print(f"      📊 找到 {len(matching_targets)} 个精确匹配目标")
        
        if matching_targets:
            matches[source_obj] = matching_targets
            print(f"      ✅ 找到 {len(matching_targets)} 个精确匹配目标，将进行替换")
        else:
            print(f"      ⏭️ 无精确匹配目标，跳过处理（避免错误替换）")
    
    print(f"\n📊 匹配完成: 找到 {len(matches)} 个匹配的源物体")
    
    # 打印详细的匹配对应关系
    print(f"\n🔗 匹配对应关系详情:")
    print("=" * 80)
    for source_obj, target_objects_list in matches.items():
        source_info = parse_object_name(source_obj.name)
        print(f"\n📌 源物体: {source_obj.name}")
        print(f"   ├─ 性别: {source_info['gender']}")
        print(f"   ├─ 部位: {source_info['parts']}")
        print(f"   ├─ 套装: {source_info['is_set']}")
        print(f"   └─ 匹配目标数量: {len(target_objects_list)}")
        
        for i, target_obj in enumerate(target_objects_list, 1):
            target_info = target_obj['parsed_info']
            print(f"      [{i}] 目标: {target_obj['name']}")
            print(f"          ├─ 性别: {target_info['gender']}")
            print(f"          ├─ 部位: {target_info['parts']}")
            print(f"          └─ 套装: {target_info['is_set']}")
    
    print("=" * 80)
    return matches


def validate_object_state(obj):
    """验证对象状态是否有效
    
    Args:
        obj: 要验证的对象
        
    Returns:
        bool: 对象是否有效
    """
    try:
        # 检查对象是否仍然存在
        if not obj or obj.name not in bpy.data.objects:
            return False
        
        # 检查对象类型
        if obj.type != 'MESH':
            return False
            
        # 检查网格数据是否存在
        if not hasattr(obj, 'data') or not obj.data:
            return False
            
        if obj.data.name not in bpy.data.meshes:
            return False
        
        # 尝试访问网格数据，检查是否有效
        try:
            _ = len(obj.data.vertices)
        except Exception:
            return False
            
        return True
        
    except Exception:
        return False

def safe_mesh_operation(operation_func, *args, **kwargs):
    """安全执行网格操作，带错误恢复
    
    Args:
        operation_func: 要执行的操作函数
        *args: 操作函数的参数
        **kwargs: 操作函数的关键字参数
        
    Returns:
        tuple: (成功标志, 结果或错误信息)
    """
    try:
        result = operation_func(*args, **kwargs)
        return True, result
    except Exception as e:
        error_msg = f"网格操作失败: {str(e)}"
        print(f"✗ {error_msg}")
        return False, error_msg

def safe_copy_mesh_data(source_mesh, target_mesh, new_name):
    """安全地复制网格数据
    
    Args:
        source_mesh: 源网格对象
        target_mesh: 目标网格对象
        new_name (str): 新网格的名称
        
    Returns:
        bpy.types.Mesh or None: 复制成功返回新网格，失败返回None
    """
    try:
        # 多重验证源网格和目标网格
        if not source_mesh:
            print(f"✗ 源网格为空")
            return None
            
        if not target_mesh:
            print(f"✗ 目标网格为空")
            return None
        
        # 检查网格是否在数据块中
        if source_mesh.name not in bpy.data.meshes:
            print(f"✗ 源网格不在数据块中: {source_mesh.name}")
            return None
            
        if target_mesh.name not in bpy.data.meshes:
            print(f"✗ 目标网格不在数据块中: {target_mesh.name}")
            return None
        
        # 检查网格是否有效（避免 StructRNA 错误）
        try:
            # 尝试访问网格的基本属性
            _ = len(target_mesh.vertices)
            _ = len(target_mesh.polygons)
        except Exception as mesh_error:
            print(f"✗ 目标网格无效: {mesh_error}")
            return None
        
        # 创建网格副本
        new_mesh = target_mesh.copy()
        if not new_mesh:
            print(f"✗ 网格复制返回空对象")
            return None
            
        new_mesh.name = new_name
        
        # 验证新网格是否创建成功
        if new_mesh.name not in bpy.data.meshes:
            print(f"✗ 新网格未添加到数据块: {new_name}")
            return None
        
        # 验证新网格是否有效
        try:
            _ = len(new_mesh.vertices)
            _ = len(new_mesh.polygons)
        except Exception as new_mesh_error:
            print(f"✗ 新网格无效: {new_mesh_error}")
            # 清理无效的网格
            try:
                bpy.data.meshes.remove(new_mesh)
            except:
                pass
            return None
            
        return new_mesh
        
    except Exception as e:
        print(f"✗ 网格复制异常: {e}")
        return None

def replace_whole_set(source_objects, target_objects, used_targets=None):
    """整套替换函数 - 以整套为单位进行替换
    
    Args:
        source_objects (list): 源套装中的物体列表
        target_objects (list): 目标套装中的物体列表
        used_targets (set): 已使用的目标物体名称集合（这里不使用，因为整套替换）
        
    Returns:
        tuple: (成功数量, 替换详情)
    """
    if not source_objects or not target_objects:
        return 0, []
    
    successful_replacements = []
    
    # 为每个源物体找到对应的目标物体（按部位匹配）
    print(f"\n🔍 批量替换诊断:")
    for source_obj in source_objects:
        source_parsed = parse_object_name(source_obj.name)
        print(f"\n  🎯 处理源物体: {source_obj.name}")
        print(f"      性别: {source_parsed['gender']}, 部位: {source_parsed['parts']}")
        
        matching_targets = []
        
        for target_obj in target_objects:
            target_parsed = target_obj['parsed_info']
            # 检查性别和部位是否匹配（使用精确匹配）
            gender_match = source_parsed['gender'] == target_parsed['gender']
            parts_match = is_exact_part_match(source_parsed['parts'], target_parsed['parts'])
            
            if gender_match and parts_match:
                print(f"      ✅ 精确匹配: {target_obj['name']} (部位: {target_parsed['parts']})")
                matching_targets.append(target_obj)
            else:
                if not gender_match:
                    print(f"      ❌ 性别不匹配: {target_obj['name']} (源: {source_parsed['gender']}, 目标: {target_parsed['gender']})")
                elif not parts_match:
                    print(f"      ❌ 部位不匹配: {target_obj['name']} (源: {source_parsed['parts']}, 目标: {target_parsed['parts']})")
        
        if matching_targets:
            # 对于整套替换，我们选择第一个匹配的目标（因为整套已经确定）
            # 这样可以确保整套的一致性
            target_obj = matching_targets[0]
            
            # 执行替换（这里需要实现具体的替换逻辑）
            # 由于replace_object_with_random函数未定义，我们使用简化的替换逻辑
            try:
                # 保存源物体的变换信息
                original_location = source_obj.location.copy()
                original_rotation = source_obj.rotation_euler.copy()
                original_scale = source_obj.scale.copy()
                
                # 复制网格数据
                new_mesh = target_obj['object'].data.copy()
                new_mesh.name = f"{target_obj['name']}_replaced_{random.randint(1000, 9999)}"
                
                # 替换网格数据
                old_mesh = source_obj.data
                source_obj.data = new_mesh
                
                # 保持源物体的变换
                source_obj.location = original_location
                source_obj.rotation_euler = original_rotation
                source_obj.scale = original_scale
                
                # 更新物体名称（避免名称冲突）
                if target_obj['name'] in bpy.data.objects and bpy.data.objects[target_obj['name']] != source_obj:
                    counter = 1
                    new_name = f"{target_obj['name']}.{counter:03d}"
                    while new_name in bpy.data.objects:
                        counter += 1
                        new_name = f"{target_obj['name']}.{counter:03d}"
                    source_obj.name = new_name
                else:
                    source_obj.name = target_obj['name']
                
                # 清理旧网格
                if old_mesh and old_mesh.users == 0:
                    bpy.data.meshes.remove(old_mesh)
                
                successful_replacements.append((source_obj, target_obj))
                print(f"  ✓ 替换: {source_obj.name}")
            except Exception as e:
                print(f"  ✗ 替换失败: {e}")
                continue
        else:
            print(f"      ⏭️ 跳过 {source_obj.name}：无精确匹配目标（避免错误替换）")
    
    print(f"\n📊 整套替换完成: 成功 {len(successful_replacements)} 个")
    
    # 打印批量替换的详细对应关系
    if successful_replacements:
        print(f"\n🔗 批量替换对应关系详情:")
        print("=" * 80)
        for i, (source_obj, target_obj) in enumerate(successful_replacements, 1):
            source_info = parse_object_name(source_obj.name)
            target_info = target_obj['parsed_info']
            
            print(f"\n[{i}] 成功替换:")
            print(f"   📌 源物体: {source_obj.name}")
            print(f"      ├─ 性别: {source_info['gender']}")
            print(f"      ├─ 部位: {source_info['parts']}")
            print(f"      └─ 套装: {source_info['is_set']}")
            
            print(f"   🎯 目标物体: {target_obj['name']}")
            print(f"      ├─ 性别: {target_info['gender']}")
            print(f"      ├─ 部位: {target_info['parts']}")
            print(f"      └─ 套装: {target_info['is_set']}")
            
            print(f"   ✅ 状态: 替换成功")
        print("=" * 80)
    
    return len(successful_replacements), successful_replacements

def calculate_replacement_plan(source_objects, target_objects, used_targets=None, enable_set_replacement=False):
    """计算替换计划，确定每个源物体要替换成哪个目标物体
    
    Args:
        source_objects (list): 源物体列表
        target_objects (list): 目标物体列表
        used_targets (set): 已使用的目标物体名称集合
        enable_set_replacement (bool): 是否启用套装替换模式
        
    Returns:
        list: 替换计划列表，每个元素包含 (source_obj, target_obj)
    """
    replacement_plan = []
    
    print(f"\n🔍 开始计算替换计划...")
    print(f"  源物体数量: {len(source_objects)}")
    print(f"  目标物体数量: {len(target_objects)}")
    print(f"  套装替换模式: {enable_set_replacement}")
    
    # 分析源物体
    print(f"\n📋 源物体分析:")
    for i, source_obj in enumerate(source_objects, 1):
        source_info = parse_object_name(source_obj.name)
        print(f"  [{i}] {source_obj.name}")
        print(f"      性别: {source_info['gender']}, 部位: {source_info['parts']}, 套装: {source_info['is_set']}")
    
    # 分析目标物体
    print(f"\n🎯 目标物体分析:")
    for i, target in enumerate(target_objects, 1):
        print(f"  [{i}] {target['name']}")
        print(f"      性别: {target['parsed_info']['gender']}, 部位: {target['parsed_info']['parts']}, 套装: {target['parsed_info']['is_set']}")
    
    if enable_set_replacement:
        # 智能套装替换模式
        print(f"\n🔍 智能套装替换模式:")
        print("=" * 60)
        
        # 检查是否为单选模式
        if len(source_objects) == 1:
            source_obj = source_objects[0]
            source_parsed = parse_object_name(source_obj.name)
            
            print(f"🎯 单选模式: {source_obj.name}")
            print(f"   性别: {source_parsed['gender']}, 部位: {source_parsed['parts']}")
            
            # 检查是否为身体部件（上身、下身、头发）
            if any(part in source_parsed['parts'] for part in ['upper', 'lower', 'hair']):
                print(f"   检测到身体部件，智能套装替换...")
                
                # 智能身体部件替换逻辑
                target_obj = smart_body_part_replacement(source_obj, source_parsed, target_objects)
                
                if target_obj:
                    replacement_plan.append((source_obj, target_obj))
                    print(f"   ✅ 智能替换成功: {source_obj.name} -> {target_obj['name']}")
                else:
                    print(f"   ⏭️ 跳过 {source_obj.name}：无匹配目标")
                
                return replacement_plan
        
        # 多选模式：智能套装替换
        print(f"🎯 多选模式，智能套装替换")
        
        # 检查是否启用套装替换
        enable_set_replacement = bpy.context.scene.enable_set_replacement
        print(f"   套装替换模式: {'启用' if enable_set_replacement else '禁用'}")
        
        if enable_set_replacement:
            # 使用新的智能多选替换逻辑（按顶级父级分组）
            replacement_plan = smart_multi_selection_replacement(source_objects, target_objects)
        else:
            # 普通替换模式 - 使用精确匹配
            matches = find_matching_objects(source_objects, target_objects)
            
            print(f"\n🔄 处理匹配结果:")
            for source_obj, target_obj in matches:
                replacement_plan.append((source_obj, target_obj))
                print(f"   ✅ 精确匹配: {source_obj.name} -> {target_obj['name']}")
            
            # 处理未匹配的物体
            matched_sources = {match[0] for match in matches}
            unmatched_objects = [obj for obj in source_objects if obj not in matched_sources]
            
            print(f"\n⚠️ 未匹配的物体数量: {len(unmatched_objects)}")
            for source_obj in unmatched_objects:
                source_parsed = parse_object_name(source_obj.name)
                target_obj = find_matching_random_target(
                    source_parsed['gender'], 
                    source_parsed['parts'], 
                    target_objects
                )
                if target_obj:
                    replacement_plan.append((source_obj, target_obj))
                    print(f"   🎯 随机替换: {source_obj.name} -> {target_obj['name']}")
                else:
                    print(f"   ⏭️ 跳过: {source_obj.name}")
    else:
        # 普通替换模式 - 使用精确匹配
        matches = find_matching_objects(source_objects, target_objects)
        
        print(f"\n🔄 处理匹配结果:")
        for source_obj, target_objects_list in matches.items():
            if target_objects_list:
                # 只选择精确匹配的目标物体
                target_obj = weighted_random_choice(target_objects_list, used_targets)
                if target_obj:
                    replacement_plan.append((source_obj, target_obj))
                    print(f"  ✅ 计划替换: {source_obj.name} -> {target_obj['name']}")
                else:
                    print(f"  ⏭️ 跳过 {source_obj.name}：无可用目标物体")
            else:
                print(f"  ⏭️ 跳过 {source_obj.name}：无精确匹配目标")
        
        # 检查未匹配的源物体
        matched_source_names = {obj.name for obj in matches.keys()}
        for source_obj in source_objects:
            if source_obj.name not in matched_source_names:
                print(f"  ⏭️ 跳过 {source_obj.name}：无任何匹配目标")
    
    print(f"\n📊 替换计划统计:")
    print(f"  计划替换数量: {len(replacement_plan)}")
    print(f"  未匹配源物体: {len(source_objects) - len(replacement_plan)}")
    
    # 打印详细的替换计划对应关系
    if replacement_plan:
        print(f"\n🎯 最终替换计划详情:")
        print("=" * 80)
        for i, (source_obj, target_obj) in enumerate(replacement_plan, 1):
            source_info = parse_object_name(source_obj.name)
            target_info = target_obj['parsed_info']
            
            print(f"\n[{i}] 替换计划:")
            print(f"   📌 源物体: {source_obj.name}")
            print(f"      ├─ 性别: {source_info['gender']}")
            print(f"      ├─ 部位: {source_info['parts']}")
            print(f"      └─ 套装: {source_info['is_set']}")
            
            print(f"   🎯 目标物体: {target_obj['name']}")
            print(f"      ├─ 性别: {target_info['gender']}")
            print(f"      ├─ 部位: {target_info['parts']}")
            print(f"      └─ 套装: {target_info['is_set']}")
            
            # 检查匹配一致性
            gender_match = source_info['gender'] == target_info['gender']
            parts_match = is_exact_part_match(source_info['parts'], target_info['parts'])
            
            if gender_match and parts_match:
                print(f"   ✅ 匹配状态: 完全匹配")
            else:
                print(f"   ❌ 匹配状态: 不匹配")
                if not gender_match:
                    print(f"      └─ 性别不匹配: {source_info['gender']} ≠ {target_info['gender']}")
                if not parts_match:
                    print(f"      └─ 部位不匹配: {source_info['parts']} ≠ {target_info['parts']}")
        
        print("=" * 80)
    
    # 验证替换计划的一致性
    if replacement_plan:
        validate_replacement_consistency(replacement_plan)
    
    return replacement_plan

def import_target_objects(replacement_plan, file_path):
    """批量导入目标物体到隐藏集合
    
    Args:
        replacement_plan (list): 替换计划
        file_path (str): 源文件路径
        
    Returns:
        dict: 导入的物体映射 {target_name: imported_object}
    """
    imported_objects = {}
    unique_targets = set()
    
    # 收集所有需要导入的目标物体名称
    for source_obj, target_obj in replacement_plan:
        unique_targets.add(target_obj['name'])
    
    print(f"准备导入 {len(unique_targets)} 个目标物体")
    
    # 确保隐藏集合存在
    hidden_collection = create_hidden_import_collection()
    
    # 批量导入
    for target_name in unique_targets:
        try:
            # 检查是否已存在
            existing_obj = check_object_exists_in_hidden_collection(target_name)
            if existing_obj:
                imported_objects[target_name] = existing_obj
                print(f"  ✓ 已存在，直接引用: {target_name}")
                continue
            
            # 导入新物体
            bpy.ops.wm.append(
                filepath=file_path,
                directory=file_path + "/Object/",
                filename=target_name
            )
            
            if target_name in bpy.data.objects:
                imported_obj = bpy.data.objects[target_name]
                
                # 验证导入的物体
                is_valid = log_imported_object_validation(target_name, imported_obj, "  ")
                if not is_valid:
                    print(f"  ✗ 导入的物体无效: {target_name}")
                    continue
                
                # 将物体移动到隐藏集合
                # 先从当前集合中移除
                for collection in imported_obj.users_collection:
                    collection.objects.unlink(imported_obj)
                
                # 添加到隐藏集合
                hidden_collection.objects.link(imported_obj)
                
                # 标记为导入的物体
                imported_obj['is_imported_temp'] = True
                imported_obj['is_in_hidden_collection'] = True
                
                imported_objects[target_name] = imported_obj
                print(f"  ✓ 导入到隐藏集合: {target_name}")
            else:
                print(f"  ✗ 导入失败: {target_name}")
        except Exception as e:
            print(f"  ✗ 导入错误: {target_name} - {e}")
    
    print(f"\n📊 导入统计:")
    print(f"  总目标数: {len(unique_targets)}")
    print(f"  成功导入: {len(imported_objects)}")
    print(f"  失败数量: {len(unique_targets) - len(imported_objects)}")
    
    return imported_objects

def execute_replacements(replacement_plan, imported_objects):
    """执行替换操作
    
    Args:
        replacement_plan (list): 替换计划
        imported_objects (dict): 导入的物体映射
        
    Returns:
        int: 成功替换的数量
    """
    successful_replacements = 0
    
    # 检查是否启用诊断
    scene = bpy.context.scene
    enable_diagnostics = getattr(scene, 'enable_replacement_diagnostics', False)
    
    if enable_diagnostics:
        print(f"\n🔍 开始执行 {len(replacement_plan)} 个替换操作")
        print("=" * 60)
    
    for i, (source_obj, target_obj) in enumerate(replacement_plan, 1):
        obj_name = source_obj.name if source_obj else "Unknown"
        target_name = target_obj['name']
        
        if enable_diagnostics:
            print(f"\n[{i}/{len(replacement_plan)}] 处理物体: {obj_name}")
            print("-" * 40)
        
        try:
            # 步骤1: 验证源物体
            log_replacement_step("验证源物体", obj_name, "检查物体有效性")
            if not source_obj or not hasattr(source_obj, 'name') or source_obj.name not in bpy.data.objects:
                log_replacement_step("跳过", obj_name, "源物体无效或不存在")
                continue
            
            source_obj = bpy.data.objects[source_obj.name]
            before_state = snapshot_object_state(source_obj)
            log_object_state(obj_name, before_state, "替换前 ")
            
            # 步骤2: 检查目标物体
            log_replacement_step("检查目标", obj_name, f"目标: {target_name}")
            if target_name not in imported_objects:
                log_replacement_step("错误", obj_name, f"目标物体 '{target_name}' 未导入")
                print(f"  ❌ 可用目标物体: {list(imported_objects.keys())}")
                continue
            
            target_object = imported_objects[target_name]
            log_replacement_step("获取目标", obj_name, f"目标物体: {target_object.name}")
            
            # 步骤2.5: 验证目标物体
            is_target_valid = log_imported_object_validation(target_name, target_object, "  ")
            if not is_target_valid:
                log_replacement_step("错误", obj_name, f"目标物体 '{target_name}' 验证失败")
                continue
            
            # 步骤3: 保存变换信息
            log_replacement_step("保存变换", obj_name, "保存位置、旋转、缩放")
            original_location = source_obj.location.copy()
            original_rotation = source_obj.rotation_euler.copy()
            original_scale = source_obj.scale.copy()
            
            # 步骤4: 直接引用目标网格数据（不创建新网格）
            log_replacement_step("引用网格", obj_name, f"直接引用 {target_object.data.name}")
            old_mesh = source_obj.data
            source_obj.data = target_object.data
            log_replacement_step("网格引用完成", obj_name, f"引用网格: {source_obj.data.name}")
            
            # 步骤5: 恢复变换
            log_replacement_step("恢复变换", obj_name, "恢复位置、旋转、缩放")
            source_obj.location = original_location
            source_obj.rotation_euler = original_rotation
            source_obj.scale = original_scale
            
            # 步骤6: 更新物体名称
            log_replacement_step("更新名称", obj_name, "避免名称冲突")
            old_name = source_obj.name
            if target_name in bpy.data.objects and bpy.data.objects[target_name] != source_obj:
                counter = 1
                new_name = f"{target_name}.{counter:03d}"
                while new_name in bpy.data.objects:
                    counter += 1
                    new_name = f"{target_name}.{counter:03d}"
                source_obj.name = new_name
            else:
                source_obj.name = target_name
            log_replacement_step("名称更新完成", obj_name, f"新名称: {source_obj.name}")
            
            # 步骤7: 清理旧网格
            log_replacement_step("清理旧网格", obj_name, f"检查 {old_mesh.name} 使用情况")
            if old_mesh and old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
                log_replacement_step("旧网格已删除", obj_name, f"删除 {old_mesh.name}")
            else:
                log_replacement_step("保留旧网格", obj_name, f"{old_mesh.name} 仍被 {old_mesh.users} 个对象使用")
            
            # 步骤8: 检查替换后状态
            after_state = snapshot_object_state(source_obj)
            log_object_state(source_obj.name, after_state, "替换后 ")
            
            # 步骤9: 对比状态差异
            if enable_diagnostics:
                diff_result = diff_states(before_state, after_state, obj_name)
                print(f"📊 状态对比: {diff_result}")
            
            # 步骤10: 安全检查 - 如果对象未链接到任何集合，重新链接
            if after_state.get('exists', True) and after_state.get('collection_count', 0) == 0:
                log_replacement_step("安全修复", source_obj.name, "对象未链接到集合，重新链接到场景根集合")
                try:
                    bpy.context.scene.collection.objects.link(source_obj)
                    fixed_state = snapshot_object_state(source_obj)
                    log_object_state(source_obj.name, fixed_state, "修复后 ")
                    if enable_diagnostics:
                        print(f"✅ [{source_obj.name}] 已重新链接到场景根集合")
                except Exception as fix_e:
                    if enable_diagnostics:
                        print(f"❌ [{source_obj.name}] 重新链接失败: {fix_e}")
            
            log_replacement_step("替换完成", source_obj.name, f"成功: {old_name} -> {target_name}")
            successful_replacements += 1
            
        except Exception as e:
            log_replacement_step("替换失败", obj_name, f"错误: {e}")
            # 即使失败也要检查状态
            try:
                error_state = snapshot_object_state(source_obj)
                log_object_state(obj_name, error_state, "错误后 ")
            except:
                if enable_diagnostics:
                    print(f"❌ [{obj_name}] 无法获取错误后状态")
            continue
    
    if enable_diagnostics:
        print(f"\n{'=' * 60}")
        print(f"🎯 替换操作完成: {successful_replacements}/{len(replacement_plan)} 成功")
    else:
        print(f"替换完成: {successful_replacements}/{len(replacement_plan)} 成功")
    
    # 验证替换结果
    if replacement_plan:
        validate_replacement_results(replacement_plan)
    
    # 打印执行结果的详细对应关系
    print(f"\n🔗 执行结果对应关系详情:")
    print("=" * 80)
    print(f"📊 执行统计:")
    print(f"   ├─ 计划替换数量: {len(replacement_plan)}")
    print(f"   ├─ 成功替换数量: {successful_replacements}")
    print(f"   └─ 成功率: {(successful_replacements/len(replacement_plan)*100):.1f}%" if replacement_plan else "0%")
    
    if replacement_plan:
        print(f"\n📋 详细执行结果:")
        for i, (source_obj, target_obj) in enumerate(replacement_plan, 1):
            source_info = parse_object_name(source_obj.name)
            target_info = target_obj['parsed_info']
            
            print(f"\n[{i}] 执行结果:")
            print(f"   📌 源物体: {source_obj.name}")
            print(f"      ├─ 性别: {source_info['gender']}")
            print(f"      ├─ 部位: {source_info['parts']}")
            print(f"      └─ 套装: {source_info['is_set']}")
            
            print(f"   🎯 目标物体: {target_obj['name']}")
            print(f"      ├─ 性别: {target_info['gender']}")
            print(f"      ├─ 部位: {target_info['parts']}")
            print(f"      └─ 套装: {target_info['is_set']}")
            
            print(f"   ✅ 状态: 执行完成")
    
    print("=" * 80)
    
    return successful_replacements

def cleanup_imported_objects(imported_objects):
    """清理导入的临时物体（不清理隐藏集合中的物体）
    
    Args:
        imported_objects (dict): 导入的物体映射
    """
    removed_count = 0
    for target_name, imported_obj in imported_objects.items():
        try:
            # 只清理不在隐藏集合中的临时物体
            if (imported_obj.name in bpy.data.objects and 
                not imported_obj.get('is_in_hidden_collection', False)):
                bpy.data.objects.remove(imported_obj, do_unlink=True)
                removed_count += 1
        except Exception as e:
            pass
    
    if removed_count > 0:
        print(f"清理完成: 删除了 {removed_count} 个临时物体")
    
    # 执行递归清理
    recursive_cleanup_unused_data()

def find_reference_body_part(source_obj, gender):
    """按照优先级顺序查找参考部件：上身 > 下身 > 头发
    
    Args:
        source_obj: 源物体
        gender: 性别
        
    Returns:
        bpy.types.Object or None: 找到的参考部件，如果没找到返回None
    """
    print(f"🔍 查找参考部件: 性别={gender}")
    print(f"   优先级顺序: 上身 > 下身 > 头发")
    
    # 获取顶级父级
    top_parent = source_obj
    while top_parent.parent:
        top_parent = top_parent.parent
    
    print(f"   顶级父级: {top_parent.name}")
    
    # 遍历顶级父级下的所有子物体
    def get_all_children(obj):
        children = []
        for child in obj.children:
            children.append(child)
            children.extend(get_all_children(child))
        return children
    
    all_children = get_all_children(top_parent)
    print(f"   子物体数量: {len(all_children)}")
    
    # 按照优先级顺序查找参考部件
    priority_parts = ['upper', 'lower', 'hair']
    
    for priority_part in priority_parts:
        print(f"   🔍 查找 {priority_part} 部件...")
        
        for child in all_children:
            if child == source_obj:
                continue
                
            if child.type != 'MESH':
                continue
                
            child_parsed = parse_object_name(child.name)
            
            # 检查性别和部位是否匹配
            if (child_parsed['gender'] == gender and 
                priority_part in child_parsed['parts']):
                print(f"   ✅ 找到参考部件: {child.name} (部位: {priority_part})")
                return child
        
        print(f"   ❌ 未找到 {priority_part} 部件")
    
    print(f"   ❌ 未找到任何参考部件")
    return None

def find_matching_target_set(reference_parsed, target_objects):
    """查找匹配的目标套装
    
    Args:
        reference_parsed: 参考部件的解析信息
        target_objects: 目标物体列表
        
    Returns:
        dict or None: 匹配的目标套装物体
    """
    print(f"🔍 查找匹配的目标套装:")
    print(f"   参考部件性别: {reference_parsed['gender']}")
    print(f"   参考部件套装: {reference_parsed['is_set']}")
    
    # 按套装分组目标物体
    target_sets = group_objects_by_sets_smart([{'name': obj['name'], 'parsed_info': obj['parsed_info']} for obj in target_objects])
    
    matching_sets = []
    
    for target_set_id, target_set_info in target_sets.items():
        # 检查性别匹配
        if target_set_info['gender'] != reference_parsed['gender']:
            continue
        
        matching_sets.append((target_set_id, target_set_info))
        print(f"   ✅ 找到匹配套装: {target_set_id}")
    
    if matching_sets:
        # 随机选择一个匹配的套装
        target_set_id, target_set_info = random.choice(matching_sets)
        print(f"   🎯 选择目标套装: {target_set_id}")
        
        # 返回套装中的第一个物体作为代表
        if target_set_info['objects']:
            first_obj = target_set_info['objects'][0]
            if hasattr(first_obj, 'name'):
                obj_name = first_obj.name
            else:
                obj_name = first_obj['name']
            
            # 在target_objects中找到对应的物体
            for target_obj in target_objects:
                if target_obj['name'] == obj_name:
                    return target_obj
    
    print(f"   ❌ 未找到匹配的目标套装")
    return None

def find_matching_part_in_set(source_obj, target_set_obj, target_objects):
    """在目标套装中查找匹配的部件
    
    Args:
        source_obj: 源物体
        target_set_obj: 目标套装代表物体
        target_objects: 目标物体列表
        
    Returns:
        dict or None: 匹配的目标物体
    """
    source_parsed = parse_object_name(source_obj.name)
    target_set_parsed = parse_object_name(target_set_obj['name'])
    
    print(f"🔍 在目标套装中查找匹配部件:")
    print(f"   源部件: {source_obj.name} (部位: {source_parsed['parts']})")
    print(f"   目标套装: {target_set_obj['name']}")
    
    # 获取目标套装的基础名称
    target_base_name = target_set_parsed['base_name']
    
    # 查找目标套装中的所有物体
    target_set_objects = []
    for target_obj in target_objects:
        target_obj_parsed = parse_object_name(target_obj['name'])
        
        # 检查性别匹配
        if target_obj_parsed['gender'] == source_parsed['gender']:
            # 检查基础名称是否匹配
            target_obj_name_parts = target_obj['name'].split('_')
            target_obj_set_parts = []
            
            for part in target_obj_name_parts:
                part_lower = part.lower()
                if part_lower not in BODY_PART_KEYWORDS + SET_KEYWORDS:
                    target_obj_set_parts.append(part)
            
            if target_obj_set_parts:
                target_obj_base_name = '_'.join(target_obj_set_parts)
            else:
                target_obj_base_name = f"{target_obj_parsed['gender']}_sets"
            
            if target_obj_base_name == target_base_name:
                target_set_objects.append(target_obj)
                print(f"      ✅ 性别和套装匹配: {target_obj['name']}")
            else:
                print(f"      ❌ 套装不匹配: {target_obj['name']}")
        else:
            print(f"      ❌ 性别不匹配: {target_obj['name']}")
    
    print(f"   目标套装物体数量: {len(target_set_objects)}")
    
    # 查找精确匹配的部件
    for target_obj in target_set_objects:
        target_obj_parsed = parse_object_name(target_obj['name'])
        
        # 检查部位是否严格匹配
        if is_exact_part_match(source_parsed['parts'], target_obj_parsed['parts']):
            print(f"   ✅ 找到精确匹配: {target_obj['name']}")
            return target_obj
    
    # 如果没有精确匹配，返回None（不进行随机选择）
    print(f"   ❌ 目标套装中无匹配部件")
    return None

def group_objects_by_sets_smart(objects):
    """智能套装分组（包含不完整的套装）
    
    Args:
        objects (list): 物体列表
        
    Returns:
        dict: 套装分组结果
    """
    sets = {}
    
    for obj in objects:
        # 处理物体对象或字典
        if hasattr(obj, 'name'):
            obj_name = obj.name
            parsed_info = parse_object_name(obj_name)
            parent_name = "NoParent"
        else:
            obj_name = obj['name']
            parsed_info = obj['parsed_info']
            parent_name = "NoParent"
        
        # 智能套装识别：基于sets关键词和性别进行分组
        if parsed_info['gender'] and parsed_info['parts']:
            # 检查是否包含sets关键词
            if parsed_info['is_set']:
                # 提取物体名称中除了部位关键词之外的部分作为套装标识符
                name_parts = obj_name.split('_')
                set_parts = []
                
                for part in name_parts:
                    part_lower = part.lower()
                    # 保留性别关键词和部位关键词之外的所有部分
                    if part_lower not in GENDER_KEYWORDS + BODY_PART_KEYWORDS + SET_KEYWORDS:
                        set_parts.append(part)
                
                # 使用性别 + 除了部位关键词以外的所有部分作为套装标识符
                if set_parts:
                    set_id = f"{parsed_info['gender']}_{'_'.join(set_parts)}"
                    base_name = '_'.join(set_parts)
                else:
                    set_id = f"{parsed_info['gender']}_sets"
                    base_name = f"{parsed_info['gender']}_sets"
            else:
                # 非套装物体，每个物体单独分组
                set_id = f"{parsed_info['gender']}_{parsed_info['parts'][0]}_single"
                base_name = f"{parsed_info['gender']}_{parsed_info['parts'][0]}"
            
            if set_id not in sets:
                sets[set_id] = {
                    'gender': parsed_info['gender'],
                    'base_name': base_name,
                    'parent_name': parent_name,
                    'objects': []
                }
            
            sets[set_id]['objects'].append(obj)
    
    return sets

def find_matching_sets_smart(source_sets, target_sets):
    """智能套装匹配（允许不完整的套装）
    
    Args:
        source_sets (dict): 源套装字典
        target_sets (dict): 目标套装字典
        
    Returns:
        dict: 匹配的套装字典
    """
    matches = {}
    
    for source_set_id, source_set in source_sets.items():
        source_gender = source_set['gender']
        source_base_name = source_set['base_name']
        
        # 寻找匹配的目标套装
        matching_target_sets = []
        
        for target_set_id, target_set in target_sets.items():
            target_gender = target_set['gender']
            target_base_name = target_set['base_name']
            
            # 性别必须匹配
            if source_gender != target_gender:
                continue
            
            # 不能是自己
            if source_set_id == target_set_id:
                continue
            
            # 基础名称不同（避免相同套装）
            if source_base_name == target_base_name:
                continue
            
            matching_target_sets.append((target_set_id, target_set))
        
        if matching_target_sets:
            matches[source_set_id] = matching_target_sets
    
    return matches

def group_objects_by_sets(objects):
    """按套装分组物体（基于父级关系）
    
    Args:
        objects (list): 物体列表（可以是物体对象或包含name和parsed_info的字典）
        
    Returns:
        dict: 套装分组结果
    """
    sets = {}
    
    for obj in objects:
        # 处理物体对象或字典
        if hasattr(obj, 'name'):
            obj_name = obj.name
            parsed_info = parse_object_name(obj_name)
            # 获取父级信息
            if hasattr(obj, 'parent') and obj.parent:
                parent_name = obj.parent.name
            else:
                parent_name = "NoParent"
        else:
            # 字典对象
            obj_name = obj['name']
            parsed_info = obj['parsed_info']
            parent_name = "NoParent"  # 字典对象没有父级信息
        
        # 修改套装识别逻辑：基于父级关系和除了部位关键词以外的名称部分
        if parsed_info['gender'] and parsed_info['parts']:
            # 提取物体名称中除了部位关键词之外的部分作为套装标识符
            name_parts = obj_name.split('_')
            set_parts = []
            
            for part in name_parts:
                part_lower = part.lower()
                # 保留性别关键词和部位关键词之外的所有部分
                if part_lower not in BODY_PART_KEYWORDS + SET_KEYWORDS:
                    set_parts.append(part)
            
            # 使用父级名称 + 除了部位关键词以外的所有部分作为套装标识符
            if set_parts:
                set_id = f"{parent_name}_{'_'.join(set_parts)}"
                base_name = '_'.join(set_parts)
            else:
                # 如果没有其他部分，使用父级名称 + 性别 + 第一个部位
                set_id = f"{parent_name}_{parsed_info['gender']}_{parsed_info['parts'][0]}"
                base_name = f"{parsed_info['gender']}_{parsed_info['parts'][0]}"
            
            # 调试信息
            print(f"物体 '{obj_name}' (父级: {parent_name}) -> 套装ID: '{set_id}' (性别: {parsed_info['gender']}, 部位: {parsed_info['parts']})")
            
            if set_id not in sets:
                sets[set_id] = {
                    'gender': parsed_info['gender'],
                    'base_name': base_name,
                    'parent_name': parent_name,
                    'objects': []
                }
            
            sets[set_id]['objects'].append(obj)
    
    return sets

def find_matching_sets(source_sets, target_sets):
    """找到匹配的套装
    
    Args:
        source_sets (dict): 源套装字典
        target_sets (dict): 目标套装字典
        
    Returns:
        dict: 匹配的套装字典
    """
    matches = {}
    
    for source_set_id, source_set in source_sets.items():
        source_gender = source_set['gender']
        source_base_name = source_set['base_name']
        source_parts = set()
        
        # 收集源套装中的所有部位
        for obj in source_set['objects']:
            if hasattr(obj, 'name'):
                parsed = parse_object_name(obj.name)
            else:
                parsed = obj['parsed_info']
            source_parts.update(parsed['parts'])
        
        # 寻找匹配的目标套装
        matching_target_sets = []
        
        for target_set_id, target_set in target_sets.items():
            target_gender = target_set['gender']
            target_base_name = target_set['base_name']
            target_parts = set()
            
            # 收集目标套装中的所有部位
            for obj in target_set['objects']:
                if hasattr(obj, 'name'):
                    parsed = parse_object_name(obj.name)
                else:
                    parsed = obj['parsed_info']
                target_parts.update(parsed['parts'])
            
            # 性别必须匹配
            if source_gender != target_gender:
                continue
            
            # 检查是否有足够的部位匹配（至少50%的源部位在目标套装中存在）
            common_parts = source_parts.intersection(target_parts)
            match_ratio = len(common_parts) / len(source_parts) if source_parts else 0
            
            # 简化的匹配策略：
            # 1. 性别必须匹配
            # 2. 不能是自己
            # 3. 基础名称不同（避免相同套装）
            # 4. 有任意部位匹配即可
            if (source_set_id != target_set_id and
                source_base_name != target_base_name and  # 基础名称必须不同
                len(common_parts) > 0):  # 有任意部位匹配即可
                matching_target_sets.append((target_set_id, target_set))
        
        if matching_target_sets:
            # 按匹配率排序，优先选择匹配率高的目标套装
            matching_target_sets.sort(key=lambda x: len(source_parts.intersection(set().union(*[parse_object_name(obj.name if hasattr(obj, 'name') else obj['name'])['parts'] for obj in x[1]['objects']]))) / len(source_parts), reverse=True)
            matches[source_set_id] = matching_target_sets
        else:
            pass  # 不打印未匹配的套装
    
    return matches

def recursive_cleanup_unused_data():
    """递归清理所有无用的数据块"""
    print("开始递归清理无用数据...")
    
    # 清理策略：多次迭代清理，直到没有更多数据可以清理
    max_iterations = 10
    total_cleaned = 0
    
    for iteration in range(max_iterations):
        iteration_cleaned = 0
        
        # 1. 清理无用的网格数据
        orphaned_meshes = [mesh for mesh in bpy.data.meshes if mesh.users == 0]
        for mesh in orphaned_meshes:
            try:
                if mesh.name in bpy.data.meshes:
                    bpy.data.meshes.remove(mesh)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理网格 '{mesh.name}' 时出错: {e}")
        
        # 2. 清理无用的材质数据
        orphaned_materials = [mat for mat in bpy.data.materials if mat.users == 0]
        for mat in orphaned_materials:
            try:
                if mat.name in bpy.data.materials:
                    bpy.data.materials.remove(mat)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理材质 '{mat.name}' 时出错: {e}")
        
        # 3. 清理无用的纹理数据
        orphaned_textures = [tex for tex in bpy.data.textures if tex.users == 0]
        for tex in orphaned_textures:
            try:
                if tex.name in bpy.data.textures:
                    bpy.data.textures.remove(tex)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理纹理 '{tex.name}' 时出错: {e}")
        
        # 4. 清理无用的图像数据
        orphaned_images = [img for img in bpy.data.images if img.users == 0]
        for img in orphaned_images:
            try:
                if img.name in bpy.data.images:
                    bpy.data.images.remove(img)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理图像 '{img.name}' 时出错: {e}")
        
        # 5. 清理无用的节点组
        orphaned_nodegroups = [ng for ng in bpy.data.node_groups if ng.users == 0]
        for ng in orphaned_nodegroups:
            try:
                if ng.name in bpy.data.node_groups:
                    bpy.data.node_groups.remove(ng)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理节点组 '{ng.name}' 时出错: {e}")
        
        # 6. 清理无用的动作数据
        orphaned_actions = [act for act in bpy.data.actions if act.users == 0]
        for act in orphaned_actions:
            try:
                if act.name in bpy.data.actions:
                    bpy.data.actions.remove(act)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理动作 '{act.name}' 时出错: {e}")
        
        # 7. 清理无用的集合
        orphaned_collections = [col for col in bpy.data.collections if col.users == 0]
        for col in orphaned_collections:
            try:
                if col.name in bpy.data.collections:
                    bpy.data.collections.remove(col)
                    iteration_cleaned += 1
            except Exception as e:
                print(f"清理集合 '{col.name}' 时出错: {e}")
        
        total_cleaned += iteration_cleaned
        
        # 如果这一轮没有清理任何数据，说明已经清理完毕
        if iteration_cleaned == 0:
            break
        
        print(f"第 {iteration + 1} 轮清理: {iteration_cleaned} 个数据块")
    
    print(f"递归清理完成: 总共清理了 {total_cleaned} 个无用数据块")

def final_cleanup_after_replacement():
    """替换完成后的最终清理，只清理导入的临时物体，不清理隐藏集合中的物体"""
    print("开始最终清理...")
    
    # 强制垃圾回收
    import gc
    gc.collect()
    
    # 只清理标记为导入的临时物体，但不清理隐藏集合中的物体
    objects_cleaned = 0
    
    for obj in list(bpy.data.objects):
        if (obj.type == 'MESH' and 
            obj.get('is_imported_temp', False) and
            not obj.get('is_in_hidden_collection', False)):  # 不清理隐藏集合中的物体
            try:
                if obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    objects_cleaned += 1
                    print(f"清理临时物体: {obj.name}")
            except Exception as e:
                print(f"清理临时物体 '{obj.name}' 时出错: {e}")
    
    # 多次递归清理所有数据
    for i in range(3):  # 进行3轮深度清理
        recursive_cleanup_unused_data()
    
    # 最终检查：清理所有孤立的网格
    final_meshes_cleaned = 0
    for mesh in bpy.data.meshes:
        if mesh.users == 0:
            try:
                if mesh.name in bpy.data.meshes:
                    bpy.data.meshes.remove(mesh)
                    final_meshes_cleaned += 1
            except Exception as e:
                print(f"最终清理网格 '{mesh.name}' 时出错: {e}")
    
    print(f"最终清理完成: 清理了 {objects_cleaned} 个物体, {final_meshes_cleaned} 个网格")
    
    # 最后一次垃圾回收
    gc.collect()

def clean_imported_objects():
    """清理之前导入的临时物体，避免累积（不清理隐藏集合中的物体）"""
    # 只清理标记为导入的临时物体，但不清理隐藏集合中的物体
    objects_to_remove = []
    for obj in bpy.data.objects:
        if (obj.type == 'MESH' and 
            obj.get('is_imported_temp', False) and
            not obj.get('is_in_hidden_collection', False)):  # 不清理隐藏集合中的物体
            objects_to_remove.append(obj)
    
    # 安全删除物体
    removed_count = 0
    for obj in objects_to_remove:
        try:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed_count += 1
        except Exception as e:
            pass
    
    if removed_count > 0:
        print(f"已清理 {removed_count} 个临时物体")
    
    # 执行递归清理
    recursive_cleanup_unused_data()

def replace_objects_from_file():
    """从文件替换物体的主函数
    
    Returns:
        str: 替换结果信息
    """
    # 初始化随机数种子
    initialize_random_seed()
    
    # 清理之前导入的物体
    clean_imported_objects()
    
    # 添加全局错误处理
    try:
        scene = bpy.context.scene
        file_path = scene.replacement_blend_file
        enable_set_replacement = scene.enable_set_replacement
        
        if not file_path:
            return "请先选择替换源文件"
    except Exception as e:
        return f"初始化错误: {str(e)}"
    
    # 添加全局错误恢复机制
    try:
        return execute_replacement()
    except Exception as e:
        print(f"替换过程中出现严重错误: {e}")
        # 尝试清理和恢复
        try:
            clean_imported_objects()
            print("已执行紧急清理")
        except:
            pass
        return f"替换失败: {str(e)}"

def execute_replacement():
    # 获取场景设置
    scene = bpy.context.scene
    file_path = scene.replacement_blend_file
    enable_set_replacement = scene.enable_set_replacement
    
    # 处理文件路径
    file_path = bpy.path.abspath(file_path)
    print(f"检查文件路径: {file_path}")
    
    if not os.path.exists(file_path):
        return f"选择的文件不存在: {file_path}"
    
    # 保存当前选中的物体信息
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        return "请先选择要替换的物体"
    
    # 验证选中的物体是否仍然有效
    valid_objects = []
    for obj in selected_objects:
        if obj.name in bpy.data.objects and obj.type == 'MESH':
            valid_objects.append(obj)
        else:
            print(f"跳过无效物体: {obj.name} (类型: {obj.type})")
    
    if not valid_objects:
        return "选中的物体中没有有效的网格物体"
    
    # 保存选中物体的名称，防止文件切换后丢失引用
    selected_object_names = [obj.name for obj in valid_objects]
    print(f"要替换的物体: {selected_object_names}")
    
    # 从文件加载物体
    print("正在从文件加载物体...")
    target_objects = load_objects_from_blend(file_path)
    if not target_objects:
        return "无法从文件中加载有效的物体。请检查文件是否包含网格物体，或确保物体命名符合规范（性别_部位_其他信息）"
    
    print(f"从文件中加载了 {len(target_objects)} 个物体")
    
    # 重新获取选中的物体（防止文件切换后引用丢失）
    current_selected_objects = []
    for obj_name in selected_object_names:
        try:
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                # 再次验证物体是否有效
                if (obj and 
                    hasattr(obj, 'type') and 
                    obj.type == 'MESH' and 
                    obj.name in bpy.data.objects):
                    current_selected_objects.append(obj)
                else:
                    print(f"跳过无效物体: {obj_name}")
            else:
                print(f"物体不存在: {obj_name}")
        except Exception as e:
            print(f"获取物体 '{obj_name}' 时出错: {e}")
            continue
    
    if not current_selected_objects:
        return "选中的物体在当前场景中不存在或无效"
    
    print(f"准备替换 {len(current_selected_objects)} 个网格物体:")
    for obj in current_selected_objects:
        print(f"  - {obj.name} ({obj.type})")
    
    replaced_count = 0
    set_replaced_count = 0
    used_targets = set()  # 跟踪已使用的目标物体
    
    # 计算替换计划
    print("计算替换计划...")
    replacement_plan = calculate_replacement_plan(current_selected_objects, target_objects, used_targets, enable_set_replacement)
    
    if not replacement_plan:
        return "没有找到可替换的物体"
    
    print(f"计划替换 {len(replacement_plan)} 个物体")
    
    # 批量导入目标物体
    print("批量导入目标物体...")
    imported_objects = import_target_objects(replacement_plan, file_path)
    
    if not imported_objects:
        return "导入目标物体失败"
    
    # 执行替换操作
    print("执行替换操作...")
    replaced_count = execute_replacements(replacement_plan, imported_objects)
    
    # 设置选中状态：选中所有已经替换的物体
    try:
        bpy.ops.object.select_all(action='DESELECT')
        
        # 收集所有已经替换的物体
        replaced_objects = []
        for source_obj, target_obj in replacement_plan:
            if source_obj and source_obj.name in bpy.data.objects:
                replaced_objects.append(source_obj)
                print(f"✅ 选中已替换物体: {source_obj.name}")
        
        # 选中所有已替换的物体
        for obj in replaced_objects:
            obj.select_set(True)
        
        # 设置活动物体为第一个已替换的物体
        if replaced_objects:
            bpy.context.view_layer.objects.active = replaced_objects[0]
            print(f"🎯 设置活动物体: {replaced_objects[0].name}")
        
        print(f"📋 最终选中状态: {len(replaced_objects)} 个已替换物体")
        
    except Exception as e:
        print(f"⚠️ 设置选中状态时出错: {e}")
        pass
    
    # 返回结果
    if enable_set_replacement:
        return f"套装替换完成: 成功替换了 {replaced_count} 个物体"
    else:
        return f"替换完成: 成功替换了 {replaced_count} 个物体"

class mian_OT_ObjectClassifier(bpy.types.Operator):
    """根据名称关键字分类物体到集合"""
    bl_idname = "object.mian_object_classifier"
    bl_label = "按名称分类物体"
    bl_description = "根据物体名称中的关键词自动分类到对应集合"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            result = classify_and_organize_objects()
            self.report({'INFO'}, result)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"分类过程中出现错误: {str(e)}")
            return {'CANCELLED'}

class mian_OT_ObjectReplacer(bpy.types.Operator):
    """从.blend文件替换物体"""
    bl_idname = "object.mian_object_replacer"
    bl_label = "从文件替换物体"
    bl_description = "从指定的.blend文件中读取物体并替换当前选中的物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            result = replace_objects_from_file()
            self.report({'INFO'}, result)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"替换过程中出现错误: {str(e)}")
            return {'CANCELLED'}

class mian_OT_ManageHiddenCollection(bpy.types.Operator):
    """管理隐藏导入集合"""
    bl_idname = "object.mian_manage_hidden_collection"
    bl_label = "管理隐藏导入集合"
    bl_description = "管理隐藏的导入物体集合，包括显示、隐藏、清理等操作"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: bpy.props.EnumProperty(
        name="操作",
        description="选择要执行的操作",
        items=[
            ('SHOW', "显示集合", "显示隐藏的导入集合"),
            ('HIDE', "隐藏集合", "隐藏导入集合"),
            ('CLEAR', "清空集合", "清空隐藏集合中的所有物体"),
            ('INFO', "显示信息", "显示隐藏集合的信息"),
        ],
        default='INFO'
    )
    
    def execute(self, context):
        try:
            hidden_collection = bpy.data.collections.get("Hidden_Imported_Objects")
            
            if not hidden_collection:
                self.report({'WARNING'}, "隐藏导入集合不存在")
                return {'CANCELLED'}
            
            if self.action == 'SHOW':
                hidden_collection.hide_viewport = False
                hidden_collection.hide_render = False
                self.report({'INFO'}, "隐藏导入集合已显示")
                
            elif self.action == 'HIDE':
                hidden_collection.hide_viewport = True
                hidden_collection.hide_render = True
                self.report({'INFO'}, "隐藏导入集合已隐藏")
                
            elif self.action == 'CLEAR':
                # 清空集合中的所有物体
                objects_to_remove = list(hidden_collection.objects)
                removed_count = 0
                
                for obj in objects_to_remove:
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                        removed_count += 1
                    except Exception as e:
                        print(f"删除物体 '{obj.name}' 时出错: {e}")
                
                self.report({'INFO'}, f"已清空隐藏集合，删除了 {removed_count} 个物体")
                
            elif self.action == 'INFO':
                object_count = len(hidden_collection.objects)
                self.report({'INFO'}, f"隐藏集合包含 {object_count} 个物体")
                
                # 打印详细信息
                print(f"隐藏导入集合信息:")
                print(f"  集合名称: {hidden_collection.name}")
                print(f"  物体数量: {object_count}")
                print(f"  视口可见: {not hidden_collection.hide_viewport}")
                print(f"  渲染可见: {not hidden_collection.hide_render}")
                
                if object_count > 0:
                    print(f"  物体列表:")
                    for obj in hidden_collection.objects:
                        print(f"    - {obj.name} ({obj.type})")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"管理隐藏集合时出现错误: {str(e)}")
            return {'CANCELLED'}


def smart_body_part_replacement(source_obj, source_parsed, target_objects):
    """智能身体部件替换逻辑
    
    优先级：上身 > 下身 > 头发
    策略：
    1. 如果是头发或下身，优先参考上身是否为套装
    2. 如果上身不是套装，则看下身是否为套装
    3. 如果下身不是套装，则看头发是否为套装
    4. 如果都不是套装，则随机选取同类部件
    5. 如果都是套装，则参考上身进行替换
    6. 如果不是这三种部件类型，则随机替换同类部件
    
    Args:
        source_obj: 源物体
        source_parsed: 源物体解析信息
        target_objects: 目标物体列表
        
    Returns:
        dict or None: 匹配的目标物体
    """
    print(f"🧠 智能身体部件替换:")
    print(f"   源部件: {source_obj.name} (部位: {source_parsed['parts']})")
    
    # 获取所有身体部件
    body_parts = get_all_body_parts(source_obj, source_parsed['gender'])
    
    if not body_parts:
        print(f"   ❌ 未找到任何身体部件，随机替换同类部件")
        return find_matching_random_target(source_parsed['gender'], source_parsed['parts'], target_objects)
    
    print(f"   📋 找到身体部件:")
    for part_type, part_obj in body_parts.items():
        part_parsed = parse_object_name(part_obj.name)
        print(f"      {part_type}: {part_obj.name} (套装: {part_parsed['is_set']})")
    
    # 按优先级检查套装状态
    priority_order = ['upper', 'lower', 'hair']
    set_parts = []
    
    for part_type in priority_order:
        if part_type in body_parts:
            part_obj = body_parts[part_type]
            part_parsed = parse_object_name(part_obj.name)
            if part_parsed['is_set']:
                set_parts.append((part_type, part_obj, part_parsed))
                print(f"   ✅ {part_type} 是套装")
            else:
                print(f"   ❌ {part_type} 不是套装")
    
    # 决定替换策略
    if set_parts:
        # 有套装部件，优先使用上身套装
        if any(part_type == 'upper' for part_type, _, _ in set_parts):
            reference_part_type = 'upper'
        else:
            # 上身不是套装，使用第一个套装
            reference_part_type = set_parts[0][0]
        
        reference_obj = body_parts[reference_part_type]
        reference_parsed = parse_object_name(reference_obj.name)
        
        print(f"   🎯 选择参考套装: {reference_part_type} ({reference_obj.name})")
        
        # 查找匹配的目标套装
        target_set_obj = find_matching_target_set(reference_parsed, target_objects)
        
        if target_set_obj:
            print(f"   ✅ 找到匹配的目标套装")
            
            # 在目标套装中查找匹配的部件
            target_obj = find_matching_part_in_set(source_obj, target_set_obj, target_objects)
            
            if target_obj:
                print(f"   🎯 套装替换成功")
                return target_obj
            else:
                print(f"   ⚠️ 目标套装中无匹配部件，随机替换同类部件")
                return find_matching_random_target(source_parsed['gender'], source_parsed['parts'], target_objects)
        else:
            print(f"   ⚠️ 未找到匹配的目标套装，随机替换同类部件")
            return find_matching_random_target(source_parsed['gender'], source_parsed['parts'], target_objects)
    else:
        print(f"   ⚠️ 所有身体部件都不是套装，随机替换同类部件")
        return find_matching_random_target(source_parsed['gender'], source_parsed['parts'], target_objects)

def get_all_body_parts(source_obj, gender):
    """获取所有身体部件（上身、下身、头发）
    
    Args:
        source_obj: 源物体
        gender: 性别
        
    Returns:
        dict: {part_type: part_obj} 身体部件字典
    """
    # 获取顶级父级
    top_parent = source_obj
    while top_parent.parent:
        top_parent = top_parent.parent
    
    # 遍历顶级父级下的所有子物体
    def get_all_children(obj):
        children = []
        for child in obj.children:
            children.append(child)
            children.extend(get_all_children(child))
        return children
    
    all_children = get_all_children(top_parent)
    
    # 查找身体部件
    body_parts = {}
    body_part_types = ['upper', 'lower', 'hair']
    
    for child in all_children:
        if child.type != 'MESH':
            continue
            
        child_parsed = parse_object_name(child.name)
        
        # 检查性别和部位是否匹配
        if (child_parsed['gender'] == gender and 
            any(part in child_parsed['parts'] for part in body_part_types)):
            
            for part_type in body_part_types:
                if part_type in child_parsed['parts']:
                    body_parts[part_type] = child
                    break
    
    return body_parts

def smart_multi_selection_replacement(source_objects, target_objects):
    """智能多选替换逻辑
    
    策略：自动检测所有顶级父级，按顶级父级分组物体，
    如果勾选套装替换则对每组的物体进行一套内套装的替换
    
    Args:
        source_objects: 源物体列表
        target_objects: 目标物体列表
        
    Returns:
        list: 替换计划 [(source_obj, target_obj), ...]
    """
    print(f"🧠 智能多选替换:")
    print(f"   源物体数量: {len(source_objects)}")
    print(f"   目标物体数量: {len(target_objects)}")
    
    replacement_plan = []
    used_target_objects = set()  # 跟踪已使用的目标物体
    
    # 按顶级父级分组源物体
    source_groups_by_parent = group_objects_by_parent(source_objects)
    
    print(f"\n📦 自动检测顶级父级分组:")
    for parent_name, parent_objects in source_groups_by_parent.items():
        print(f"   父级: {parent_name}")
        print(f"     物体数量: {len(parent_objects)}")
        for obj in parent_objects:
            parsed = parse_object_name(obj.name)
            print(f"       - {obj.name} (性别: {parsed['gender']}, 部位: {parsed['parts']})")
    
    # 为每个父级组独立执行套装替换
    for group_index, (parent_name, parent_objects) in enumerate(source_groups_by_parent.items()):
        print(f"\n🎯 处理父级组 {group_index + 1}/{len(source_groups_by_parent)}: {parent_name}")
        
        # 为当前父级组执行套装替换
        group_replacement_plan = execute_parent_group_set_replacement(
            parent_objects, target_objects, used_target_objects
        )
        
        # 添加到总替换计划
        replacement_plan.extend(group_replacement_plan)
        
        print(f"   📋 父级组替换结果: {len(group_replacement_plan)} 个替换")
        for source_obj, target_obj in group_replacement_plan:
            print(f"      {source_obj.name} -> {target_obj['name']}")
    
    print(f"\n✅ 智能多选替换完成: 共 {len(replacement_plan)} 个替换")
    return replacement_plan

def execute_parent_group_set_replacement(parent_objects, target_objects, used_target_objects):
    """为单个父级组执行套装替换
    
    Args:
        parent_objects: 父级组中的物体列表
        target_objects: 所有目标物体列表
        used_target_objects: 已使用的目标物体集合
        
    Returns:
        list: 替换计划 [(source_obj, target_obj), ...]
    """
    replacement_plan = []
    
    # 按优先级查找参考部件：上身 > 下身 > 头发
    reference_obj = find_reference_body_part_by_priority(parent_objects)
    
    if reference_obj:
        reference_parsed = parse_object_name(reference_obj.name)
        print(f"   ✅ 找到参考部件: {reference_obj.name}")
        print(f"      性别: {reference_parsed['gender']}, 部位: {reference_parsed['parts']}")
        
        # 检查参考部件是否为套装
        if reference_parsed['is_set']:
            print(f"   🎯 参考部件是套装，按套装替换")
            
            # 查找匹配的目标套装（排除已使用的）
            target_set_obj = find_matching_target_set_excluding_used(
                reference_parsed, target_objects, used_target_objects
            )
            
            if target_set_obj:
                print(f"   ✅ 找到匹配的目标套装")
                
                # 获取目标套装中的所有物体
                target_set_objects = get_target_set_objects(target_set_obj, target_objects)
                
                # 为父级组中的每个物体在目标套装中查找匹配的部件
                for source_obj in parent_objects:
                    target_obj = find_matching_part_in_target_set(
                        source_obj, target_set_objects, used_target_objects
                    )
                    
                    if target_obj:
                        replacement_plan.append((source_obj, target_obj))
                        used_target_objects.add(target_obj['name'])
                        print(f"     ✅ 套装替换: {source_obj.name} -> {target_obj['name']}")
                    else:
                        # 目标套装中无匹配部件，查找性别和部件匹配的随机替换
                        target_obj = find_matching_random_target_excluding_used(
                            reference_parsed['gender'], 
                            parse_object_name(source_obj.name)['parts'], 
                            target_objects,
                            used_target_objects
                        )
                        if target_obj:
                            replacement_plan.append((source_obj, target_obj))
                            used_target_objects.add(target_obj['name'])
                            print(f"     🎯 精确匹配随机替换: {source_obj.name} -> {target_obj['name']}")
                        else:
                            print(f"     ⏭️ 跳过 {source_obj.name}：无性别和部件匹配的目标")
            else:
                print(f"   ⚠️ 未找到匹配的目标套装，执行随机替换")
                # 为父级组中的每个物体执行随机替换
                for source_obj in parent_objects:
                    target_obj = find_matching_random_target_excluding_used(
                        reference_parsed['gender'], 
                        parse_object_name(source_obj.name)['parts'], 
                        target_objects,
                        used_target_objects
                    )
                    if target_obj:
                        replacement_plan.append((source_obj, target_obj))
                        used_target_objects.add(target_obj['name'])
                        print(f"     🎯 随机替换: {source_obj.name} -> {target_obj['name']}")
                    else:
                        print(f"     ⏭️ 跳过: {source_obj.name}")
        else:
            print(f"   ⚠️ 参考部件不是套装，执行随机替换")
            # 为父级组中的每个物体执行随机替换
            for source_obj in parent_objects:
                target_obj = find_matching_random_target_excluding_used(
                    reference_parsed['gender'], 
                    parse_object_name(source_obj.name)['parts'], 
                    target_objects,
                    used_target_objects
                )
                if target_obj:
                    replacement_plan.append((source_obj, target_obj))
                    used_target_objects.add(target_obj['name'])
                    print(f"     🎯 随机替换: {source_obj.name} -> {target_obj['name']}")
                else:
                    print(f"     ⏭️ 跳过: {source_obj.name}")
    else:
        print(f"   ❌ 未找到参考部件，执行随机替换")
        # 为父级组中的每个物体执行随机替换
        for source_obj in parent_objects:
            source_parsed = parse_object_name(source_obj.name)
            target_obj = find_matching_random_target_excluding_used(
                source_parsed['gender'], 
                source_parsed['parts'], 
                target_objects,
                used_target_objects
            )
            if target_obj:
                replacement_plan.append((source_obj, target_obj))
                used_target_objects.add(target_obj['name'])
                print(f"     🎯 随机替换: {source_obj.name} -> {target_obj['name']}")
            else:
                print(f"     ⏭️ 跳过: {source_obj.name}")
    
    return replacement_plan

def find_matching_target_set_excluding_used(reference_parsed, target_objects, used_target_objects):
    """查找匹配的目标套装（排除已使用的）
    
    Args:
        reference_parsed: 参考部件解析信息
        target_objects: 目标物体列表
        used_target_objects: 已使用的目标物体集合
        
    Returns:
        dict or None: 匹配的目标套装信息
    """
    # 按套装分组目标物体
    target_sets = group_objects_by_sets_smart([{'name': obj['name'], 'parsed_info': obj['parsed_info']} for obj in target_objects])
    
    # 查找匹配的套装
    matching_sets = []
    for set_id, set_info in target_sets.items():
        # 检查性别是否匹配
        if set_info['gender'] != reference_parsed['gender']:
            continue
        
        # 检查套装中是否有未使用的物体
        has_unused_objects = False
        for obj_info in set_info['objects']:
            if obj_info['name'] not in used_target_objects:
                has_unused_objects = True
                break
        
        if has_unused_objects:
            matching_sets.append((set_id, set_info))
    
    if matching_sets:
        # 随机选择一个匹配的套装
        set_id, set_info = random.choice(matching_sets)
        return {'set_id': set_id, 'set_info': set_info}
    
    return None

def get_target_set_objects(target_set_obj, target_objects):
    """获取目标套装中的所有物体
    
    Args:
        target_set_obj: 目标套装信息
        target_objects: 所有目标物体列表
        
    Returns:
        list: 目标套装中的物体列表
    """
    set_objects = []
    set_info = target_set_obj['set_info']
    
    for obj_info in set_info['objects']:
        # 在目标物体列表中查找对应的物体
        for target_obj in target_objects:
            if target_obj['name'] == obj_info['name']:
                set_objects.append(target_obj)
                break
    
    return set_objects

def find_matching_part_in_target_set(source_obj, target_set_objects, used_target_objects):
    """在目标套装中查找匹配的部件（排除已使用的）
    
    Args:
        source_obj: 源物体
        target_set_objects: 目标套装中的物体列表
        used_target_objects: 已使用的目标物体集合
        
    Returns:
        dict or None: 匹配的目标物体
    """
    source_parsed = parse_object_name(source_obj.name)
    
    # 严格匹配：只返回部件类型完全相同的物体
    for target_obj in target_set_objects:
        if target_obj['name'] in used_target_objects:
            continue
            
        target_parsed = parse_object_name(target_obj['name'])
        
        # 检查性别和部件是否严格匹配
        if (target_parsed['gender'] == source_parsed['gender'] and 
            is_exact_part_match(source_parsed['parts'], target_parsed['parts'])):
            return target_obj
    
    # 如果没有严格匹配，返回None（不进行回退）
    return None

def find_matching_random_target_excluding_used(gender, parts, target_objects, used_target_objects):
    """查找匹配的随机目标（排除已使用的）
    
    Args:
        gender: 性别
        parts: 部件列表
        target_objects: 目标物体列表
        used_target_objects: 已使用的目标物体集合
        
    Returns:
        dict or None: 匹配的目标物体
    """
    matching_targets = []
    
    for target_obj in target_objects:
        if target_obj['name'] in used_target_objects:
            continue
            
        target_parsed = parse_object_name(target_obj['name'])
        
        if (target_parsed['gender'] == gender and 
            is_exact_part_match(parts, target_parsed['parts'])):
            matching_targets.append(target_obj)
    
    if matching_targets:
        return random.choice(matching_targets)
    
    return None

def register():
    bpy.utils.register_class(mian_OT_ObjectClassifier)
    bpy.utils.register_class(mian_OT_ObjectReplacer)
    bpy.utils.register_class(mian_OT_ManageHiddenCollection)

def group_objects_by_parent(objects):
    """按顶级父级分组物体
    
    Args:
        objects: 物体列表
        
    Returns:
        dict: {parent_name: [objects]} 按父级分组的物体字典
    """
    groups = {}
    
    for obj in objects:
        # 获取顶级父级
        top_parent = obj
        while top_parent.parent:
            top_parent = top_parent.parent
        
        parent_name = top_parent.name
        
        if parent_name not in groups:
            groups[parent_name] = []
        
        groups[parent_name].append(obj)
    
    return groups

def find_reference_body_part_by_priority(objects):
    """按优先级查找参考部件：上身 > 下身 > 头发
    
    Args:
        objects: 物体列表
        
    Returns:
        bpy.types.Object or None: 找到的参考部件
    """
    print(f"🔍 按优先级查找参考部件: 上身 > 下身 > 头发")
    
    # 优先级顺序
    priority_parts = ['upper', 'lower', 'hair']
    
    for priority_part in priority_parts:
        for obj in objects:
            if obj.type != 'MESH':
                continue
                
            parsed = parse_object_name(obj.name)
            
            # 检查是否包含当前优先级部位
            if priority_part in parsed['parts']:
                print(f"   ✅ 找到参考部件: {obj.name} (部位: {priority_part})")
                return obj
    
    print(f"   ❌ 未找到任何身体部件")
    return None

def register():
    bpy.utils.register_class(mian_OT_ObjectClassifier)
    bpy.utils.register_class(mian_OT_ObjectReplacer)
    bpy.utils.register_class(mian_OT_ManageHiddenCollection)

def unregister():
    bpy.utils.unregister_class(mian_OT_ObjectClassifier)
    bpy.utils.unregister_class(mian_OT_ObjectReplacer)
    bpy.utils.unregister_class(mian_OT_ManageHiddenCollection)