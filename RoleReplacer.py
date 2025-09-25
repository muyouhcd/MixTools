# -*- coding: utf-8 -*-

import bpy
import bmesh
import random
import os
import time
from bpy.props import StringProperty, EnumProperty, BoolProperty

# 物体分类关键词定义
GENDER_KEYWORDS = ['male', 'female']
BODY_PART_KEYWORDS = ['upper', 'lower', 'feet', 'mouth', 'top', 'bottom', 'hair', 'nose', 'eyes', 'eyebrow']
SET_KEYWORDS = ['sets']

def initialize_random_seed():
    """初始化随机数种子"""
    # 使用当前时间戳作为种子，确保每次运行都有不同的随机性
    # 添加更多随机性因素
    import hashlib
    seed_data = f"{time.time()}_{random.random()}_{id(bpy.context)}"
    seed = int(hashlib.md5(seed_data.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    print(f"随机数种子已初始化: {seed}")

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

def load_objects_from_blend(file_path):
    """从.blend文件加载物体信息（安全导入版本）
    
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
        # 使用 append 操作安全导入文件中的物体
        print(f"正在导入文件: {file_path}")
        
        # 记录导入前的物体数量
        objects_before = len(bpy.data.objects)
        
        # 导入所有物体（保持与原始版本兼容）
        with bpy.data.libraries.load(file_path, link=False) as (data_from, data_to):
            # 导入所有物体，然后在后续处理中过滤
            data_to.objects = [name for name in data_from.objects if name in data_from.objects]
        
        # 只遍历新导入的物体
        objects_after = len(bpy.data.objects)
        new_objects = bpy.data.objects[objects_before:]
        
        mesh_count = 0
        valid_count = 0
        
        for obj in new_objects:
            if obj.type == 'MESH':
                mesh_count += 1
                
                # 直接进行详细解析（保持与原始版本一致）
                parsed_info = parse_object_name(obj.name)
                
                # 检查是否包含有效信息
                if parsed_info['gender'] and parsed_info['parts']:
                    valid_count += 1
                    
                    # 标记为导入的临时物体
                    obj['is_imported_temp'] = True
                    
                    objects_info.append({
                        'name': obj.name,
                        'object': obj,
                        'parsed_info': parsed_info,
                        'location': obj.location.copy(),
                        'rotation': obj.rotation_euler.copy(),
                        'scale': obj.scale.copy()
                    })
                else:
                    # 调试信息：显示被过滤的物体
                    print(f"过滤物体: {obj.name} (性别: {parsed_info['gender']}, 部位: {parsed_info['parts']})")
        
        print(f"文件导入完成: 总网格物体 {mesh_count} 个，有效物体 {valid_count} 个")
        
    except Exception as e:
        print(f"导入.blend文件时出错: {e}")
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
    
    print(f"开始匹配: 源物体 {len(source_objects)} 个，目标物体 {len(target_objects)} 个")
    print("源物体列表:")
    for obj in source_objects:
        print(f"  - {obj.name} ({obj.type})")
    
    for source_obj in source_objects:
        # 注意：source_objects 现在只包含网格物体，但为了安全起见保留检查
        if source_obj.type != 'MESH':
            print(f"跳过非网格物体: {source_obj.name}")
            continue
            
        source_info = parse_object_name(source_obj.name)
        print(f"源物体 '{source_obj.name}' 解析结果: {source_info}")
        
        if not source_info['gender'] or not source_info['parts']:
            print(f"源物体 '{source_obj.name}' 缺少性别或部位信息")
            continue
        
        # 找到匹配的目标物体
        matching_targets = []
        for target_obj in target_objects:
            target_info = target_obj['parsed_info']
            
            # 检查性别和部位是否匹配
            if (source_info['gender'] == target_info['gender'] and 
                any(part in target_info['parts'] for part in source_info['parts'])):
                matching_targets.append(target_obj)
                print(f"找到匹配: {source_obj.name} -> {target_obj['name']} (基础名称: {source_info['base_name']} -> {target_info['base_name']})")
        
        if matching_targets:
            matches[source_obj] = matching_targets
            print(f"物体 '{source_obj.name}' 找到 {len(matching_targets)} 个匹配目标")
        else:
            print(f"物体 '{source_obj.name}' 没有找到匹配目标")
    
    print(f"匹配完成: 找到 {len(matches)} 个匹配的源物体")
    return matches

def test_serial_number_parsing():
    """测试序号解析功能"""
    test_cases = [
        "male_upper_body",
        "male_upper_body.001",
        "female_lower_body.002",
        "male_hair.003",
        "female_eyes.004",
        "male_upper_body_sets.001",
        "female_lower_body_sets.002"
    ]
    
    print("测试序号解析功能:")
    for test_name in test_cases:
        result = parse_object_name(test_name)
        print(f"  '{test_name}' -> 基础名称: '{result['base_name']}', 性别: {result['gender']}, 部位: {result['parts']}")
    
    return True

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
    for source_obj in source_objects:
        source_parsed = parse_object_name(source_obj.name)
        matching_targets = []
        
        for target_obj in target_objects:
            target_parsed = target_obj['parsed_info']
            # 检查性别和部位是否匹配
            if (source_parsed['gender'] == target_parsed['gender'] and 
                source_parsed['parts'] == target_parsed['parts']):
                matching_targets.append(target_obj)
        
        if matching_targets:
            # 对于整套替换，我们选择第一个匹配的目标（因为整套已经确定）
            # 这样可以确保整套的一致性
            target_obj = matching_targets[0]
            
            # 执行替换
            if replace_object_with_random(source_obj, [target_obj], None):  # 不使用used_targets，因为整套替换
                successful_replacements.append((source_obj, target_obj))
        else:
            print(f"✗ 未找到匹配: {source_obj.name} (部位: {source_parsed['parts']})")
    
    return len(successful_replacements), successful_replacements

def replace_object_with_random(source_obj, target_objects, used_targets=None):
    """用随机选择的目标物体替换源物体（简化版本）
    
    Args:
        source_obj: 源物体
        target_objects (list): 可用的目标物体列表
        used_targets (set): 已使用的目标物体名称集合
        
    Returns:
        bool: 替换是否成功
    """
    if not target_objects:
        print(f"没有可用的目标物体来替换 '{source_obj.name}'")
        return False
    
    # 过滤掉重复的目标物体（基于名称）
    unique_targets = []
    seen_names = set()
    for target in target_objects:
        if target['name'] not in seen_names:
            unique_targets.append(target)
            seen_names.add(target['name'])
    
    if not unique_targets:
        print(f"没有唯一的目标物体来替换 '{source_obj.name}'")
        return False
    
    # 使用带权重的随机选择
    target_obj = weighted_random_choice(unique_targets, used_targets)
    if not target_obj:
        print(f"无法选择目标物体")
        return False
    
    print(f"从 {len(unique_targets)} 个唯一目标中加权随机选择: {target_obj['name']}")
    
    try:
        # 基本验证
        if source_obj.name not in bpy.data.objects:
            print(f"✗ 源物体不存在: '{source_obj.name}'")
            return False
            
        target_object = target_obj['object']
        if not target_object or target_object.name not in bpy.data.objects:
            print(f"✗ 目标物体不存在: '{target_obj['name']}'")
            return False
        
        # 保存源物体的变换信息
        original_location = source_obj.location.copy()
        original_rotation = source_obj.rotation_euler.copy()
        original_scale = source_obj.scale.copy()
        
        # 直接复制网格数据（简化方法）
        new_mesh = target_object.data.copy()
        new_mesh.name = f"{target_obj['name']}_replaced_{random.randint(1000, 9999)}"
        
        # 替换网格数据
        old_mesh = source_obj.data
        source_obj.data = new_mesh
        
        # 保持源物体的变换
        source_obj.location = original_location
        source_obj.rotation_euler = original_rotation
        source_obj.scale = original_scale
        
        # 更新物体名称
        source_obj.name = target_obj['name']
        
        # 清理旧网格（如果不再使用）
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        
        print(f"✓ 替换: '{source_obj.name}' -> '{target_obj['name']}'")
        return True
            
    except Exception as e:
        print(f"✗ 替换错误: '{source_obj.name}' - {e}")
        return False

def group_objects_by_sets(objects):
    """按套装分组物体
    
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
        else:
            # 字典对象
            obj_name = obj['name']
            parsed_info = obj['parsed_info']
        
        # 修改套装识别逻辑：基于物体名称的共同前缀识别套装
        if parsed_info['gender'] and parsed_info['parts']:
            # 提取物体名称中除了性别和部位之外的部分作为套装标识符
            name_parts = obj_name.split('_')
            gender_part = None
            set_parts = []
            
            for part in name_parts:
                part_lower = part.lower()
                if part_lower in GENDER_KEYWORDS:
                    gender_part = part_lower
                elif part_lower not in BODY_PART_KEYWORDS + SET_KEYWORDS:
                    set_parts.append(part)
            
            # 如果有套装部分，使用套装部分作为标识符
            if set_parts:
                set_id = f"{gender_part}_{'_'.join(set_parts)}"
                base_name = '_'.join(set_parts)
            else:
                # 如果没有套装部分，检查是否已有相同性别的套装
                # 寻找可能的套装标识符
                potential_set_id = None
                for existing_set_id, existing_set in sets.items():
                    if existing_set['gender'] == parsed_info['gender']:
                        # 检查是否可能是同一套装的不同部位
                        existing_base = existing_set['base_name']
                        if existing_base and existing_base in obj_name:
                            potential_set_id = existing_set_id
                            break
                
                if potential_set_id:
                    set_id = potential_set_id
                    base_name = existing_set['base_name']
                else:
                    # 创建新的套装标识符
                    set_id = f"{gender_part}_{parsed_info['parts'][0]}"
                    base_name = parsed_info['parts'][0]
            
            if set_id not in sets:
                sets[set_id] = {
                    'gender': parsed_info['gender'],
                    'base_name': base_name,
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
            
            # 改进的匹配策略：
            # 1. 性别必须匹配
            # 2. 不能是自己
            # 3. 有部位匹配（至少50%的源部位在目标套装中存在）
            # 4. 基础名称不同（避免相同套装）
            if (source_set_id != target_set_id and
                match_ratio >= 0.5 and  # 至少50%的源部位在目标套装中存在
                source_base_name != target_base_name):  # 基础名称必须不同
                matching_target_sets.append((target_set_id, target_set))
        
        if matching_target_sets:
            # 按匹配率排序，优先选择匹配率高的目标套装
            matching_target_sets.sort(key=lambda x: len(source_parts.intersection(set().union(*[parse_object_name(obj.name if hasattr(obj, 'name') else obj['name'])['parts'] for obj in x[1]['objects']]))) / len(source_parts), reverse=True)
            matches[source_set_id] = matching_target_sets
        else:
            pass  # 不打印未匹配的套装
    
    return matches

def clean_imported_objects():
    """清理之前导入的物体，避免累积"""
    # 获取当前场景中的所有物体
    all_objects = list(bpy.context.scene.objects)
    
    # 清理策略：删除所有不在当前选中列表中的物体
    # 这样可以避免累积之前导入的物体
    selected_objects = bpy.context.selected_objects
    selected_names = {obj.name for obj in selected_objects}
    
    objects_to_remove = []
    for obj in all_objects:
        # 保留选中的物体和必要的场景物体
        if (obj.name not in selected_names and 
            obj.type == 'MESH' and 
            not obj.name.startswith('Camera') and
            not obj.name.startswith('Light') and
            not obj.name.startswith('Cube') and
            not obj.name.startswith('Plane') and
            not obj.name.startswith('Sphere')):
            objects_to_remove.append(obj)
    
    # 安全删除物体
    removed_count = 0
    for obj in objects_to_remove:
        try:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed_count += 1
        except Exception as e:
            print(f"清理物体 '{obj.name}' 时出错: {e}")
    
    if removed_count > 0:
        print(f"已清理 {removed_count} 个累积的物体")
    
    # 清理孤立的网格数据
    orphaned_meshes = [mesh for mesh in bpy.data.meshes if mesh.users == 0]
    for mesh in orphaned_meshes:
        try:
            if mesh.name in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
        except Exception as e:
            print(f"清理网格 '{mesh.name}' 时出错: {e}")

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
        return "无法从文件中加载有效的物体"
    
    print(f"从文件中加载了 {len(target_objects)} 个物体")
    
    # 重新获取选中的物体（防止文件切换后引用丢失）
    current_selected_objects = []
    for obj_name in selected_object_names:
        if obj_name in bpy.data.objects:
            obj = bpy.data.objects[obj_name]
            # 再次验证物体是否有效
            if obj.type == 'MESH' and obj.name in bpy.data.objects:
                current_selected_objects.append(obj)
            else:
                print(f"跳过无效物体: {obj_name}")
    
    if not current_selected_objects:
        return "选中的物体在当前场景中不存在或无效"
    
    print(f"准备替换 {len(current_selected_objects)} 个网格物体:")
    for obj in current_selected_objects:
        print(f"  - {obj.name} ({obj.type})")
    
    replaced_count = 0
    set_replaced_count = 0
    used_targets = set()  # 跟踪已使用的目标物体
    
    if enable_set_replacement:
        # 套装替换模式
        print("执行套装替换模式...")
        
        # 按套装分组源物体（只处理选中的物体）
        source_sets = group_objects_by_sets(current_selected_objects)
        target_sets = group_objects_by_sets([{'name': obj['name'], 'parsed_info': obj['parsed_info']} for obj in target_objects])
        
        print(f"源套装: {len(source_sets)} 个")
        print(f"目标套装: {len(target_sets)} 个")
        
        # 使用新的匹配逻辑
        set_matches = find_matching_sets(source_sets, target_sets)
        
        print(f"找到 {len(set_matches)} 个匹配的源套装")
        
        # 调试信息：显示匹配的套装详情
        for source_set_id, matching_sets in set_matches.items():
            print(f"  源套装 '{source_set_id}' 有 {len(matching_sets)} 个匹配目标")
        
        # 为每个套装创建独立的目标跟踪
        set_used_targets = {}  # 每个套装独立跟踪已使用的目标
        used_target_sets = set()  # 跟踪已使用的目标套装，避免不同源套装选择相同目标套装
        
        for source_set_id, matching_target_sets in set_matches.items():
            if matching_target_sets:
                # 过滤掉已使用的目标套装
                available_target_sets = [(tid, tset) for tid, tset in matching_target_sets if tid not in used_target_sets]
                
                if available_target_sets:
                    # 从未使用的目标套装中随机选择
                    target_set_id, target_set = random.choice(available_target_sets)
                    used_target_sets.add(target_set_id)
                else:
                    # 如果所有目标套装都已使用，重置并重新选择
                    used_target_sets.clear()
                    target_set_id, target_set = random.choice(matching_target_sets)
                    used_target_sets.add(target_set_id)
                
                # 为当前套装初始化已使用目标列表
                if source_set_id not in set_used_targets:
                    set_used_targets[source_set_id] = set()
                
                # 获取目标套装中的物体名称
                target_set_names = []
                for target_obj in target_set['objects']:
                    if hasattr(target_obj, 'name'):
                        target_set_names.append(target_obj.name)
                    else:
                        target_set_names.append(target_obj['name'])
                
                target_objects_for_set = [obj for obj in target_objects if obj['name'] in target_set_names]
                
                if target_objects_for_set:
                    # 只替换选中的物体（确保不替换未选中的物体）
                    selected_objects_in_set = [obj for obj in source_sets[source_set_id]['objects'] if obj in current_selected_objects]
                    
                    # 整套替换：为每个源物体找到对应的目标物体
                    replaceable_count = 0
                    successful_replacements = []
                    
                    for source_obj in selected_objects_in_set:
                        source_parsed = parse_object_name(source_obj.name)
                        matching_targets = []
                        
                        # 在目标套装中按部位匹配
                        for target_obj in target_objects_for_set:
                            target_parsed = target_obj['parsed_info']
                            
                            # 检查性别是否匹配
                            if source_parsed['gender'] == target_parsed['gender']:
                                # 检查部位是否匹配（使用集合比较，更灵活）
                                source_parts_set = set(source_parsed['parts'])
                                target_parts_set = set(target_parsed['parts'])
                                
                                # 如果源部位是目标部位的子集，或者有交集，就认为匹配
                                if (source_parts_set.issubset(target_parts_set) or 
                                    source_parts_set.intersection(target_parts_set) or
                                    source_parts_set == target_parts_set):
                                    matching_targets.append(target_obj)
                        
                        if matching_targets:
                            # 选择第一个匹配的目标（确保整套一致性）
                            target_obj = matching_targets[0]
                            
                            # 执行替换
                            if replace_object_with_random(source_obj, [target_obj], None):
                                successful_replacements.append((source_obj, target_obj))
                                replaceable_count += 1
                        else:
                            pass  # 不打印未匹配的物体
                    
                    # 如果套装替换成功
                    if replaceable_count > 0:
                        set_replaced_count += 1
                        replaced_count += replaceable_count
                        print(f"✓ 套装替换: '{source_set_id}' -> '{target_set_id}' ({replaceable_count}/{len(selected_objects_in_set)})")
                        
                        # 记录整个目标套装为已使用（以整套为单位）
                        for target_obj in target_objects_for_set:
                            used_targets.add(target_obj['name'])
                    else:
                        print(f"✗ 套装 '{source_set_id}' 无匹配物体")
                else:
                    pass  # 不打印无物体的套装
            else:
                pass  # 不打印无匹配的套装
    else:
        # 普通替换模式
        print("执行普通替换模式...")
        
        # 找到匹配的物体
        matches = find_matching_objects(current_selected_objects, target_objects)
        
        print(f"找到 {len(matches)} 个匹配的物体")
        
        for source_obj, target_objects_list in matches.items():
            if replace_object_with_random(source_obj, target_objects_list, used_targets):
                replaced_count += 1
                # 记录已使用的目标物体名称
                for target in target_objects_list:
                    used_targets.add(target['name'])
                print(f"物体 '{source_obj.name}' 已替换")
    
    # 安全清理导入的临时物体
    print("正在清理导入的临时物体...")
    temp_objects_to_remove = []
    
    # 收集需要清理的临时物体
    for target_obj in target_objects:
        if 'object' in target_obj and target_obj['object']:
            obj = target_obj['object']
            # 检查物体是否仍然存在且是导入的临时物体
            if (hasattr(obj, 'name') and 
                obj.name in bpy.data.objects and 
                hasattr(obj, 'is_imported_temp')):
                temp_objects_to_remove.append(obj)
    
    # 安全删除标记的临时物体
    removed_count = 0
    for obj in temp_objects_to_remove:
        try:
            if obj.name in bpy.data.objects:
                # 检查物体是否正在被使用
                if obj.users == 0:
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                    print(f"已清理临时物体: {obj.name}")
                else:
                    print(f"跳过正在使用的物体: {obj.name} (用户数: {obj.users})")
        except Exception as e:
            print(f"清理物体 '{obj.name}' 时出错: {e}")
    
    # 安全清理孤立的网格数据
    print("正在清理孤立的网格数据...")
    orphaned_meshes = []
    for mesh in bpy.data.meshes:
        # 检查网格是否真的没有用户引用
        if mesh.users == 0:
            orphaned_meshes.append(mesh)
    
    removed_mesh_count = 0
    for mesh in orphaned_meshes:
        try:
            # 再次检查网格是否仍然存在且没有用户
            if mesh.name in bpy.data.meshes and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
                removed_mesh_count += 1
                print(f"已清理孤立网格: {mesh.name}")
        except Exception as e:
            print(f"清理孤立网格 '{mesh.name}' 时出错: {e}")
    
    print(f"清理完成: 删除了 {removed_count} 个临时物体, {removed_mesh_count} 个孤立网格")
    
    if enable_set_replacement:
        return f"替换完成：{replaced_count} 个物体已替换，{set_replaced_count} 个套装已处理"
    else:
        return f"替换完成：{replaced_count} 个物体已替换"

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

class mian_OT_TestFilePath(bpy.types.Operator):
    """测试文件路径"""
    bl_idname = "object.mian_test_file_path"
    bl_label = "测试文件路径"
    bl_description = "测试选择的文件路径是否正确"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        file_path = scene.replacement_blend_file
        
        if not file_path:
            self.report({'WARNING'}, "请先选择文件")
            return {'CANCELLED'}
        
        abs_path = bpy.path.abspath(file_path)
        info = f"原始路径: {file_path}\n绝对路径: {abs_path}\n文件存在: {os.path.exists(abs_path)}"
        
        if os.path.exists(abs_path):
            self.report({'INFO'}, f"文件路径正确: {abs_path}")
        else:
            self.report({'ERROR'}, f"文件不存在: {abs_path}")
        
        print(info)
        return {'FINISHED'}

class mian_OT_TestSerialParsing(bpy.types.Operator):
    """测试序号解析功能"""
    bl_idname = "object.mian_test_serial_parsing"
    bl_label = "测试序号解析"
    bl_description = "测试物体名称序号解析功能"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            test_serial_number_parsing()
            self.report({'INFO'}, "序号解析测试完成，请查看控制台输出")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"测试过程中出现错误: {str(e)}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(mian_OT_ObjectClassifier)
    bpy.utils.register_class(mian_OT_ObjectReplacer)
    bpy.utils.register_class(mian_OT_TestFilePath)
    bpy.utils.register_class(mian_OT_TestSerialParsing)

def unregister():
    bpy.utils.unregister_class(mian_OT_ObjectClassifier)
    bpy.utils.unregister_class(mian_OT_ObjectReplacer)
    bpy.utils.unregister_class(mian_OT_TestFilePath)
    bpy.utils.unregister_class(mian_OT_TestSerialParsing)