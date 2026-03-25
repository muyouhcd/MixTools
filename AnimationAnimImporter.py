"""
Blender工具：直接导入Unity .anim文件（YAML格式）
集成到MixTools插件中
"""

import bpy
import os
import re
import math
from mathutils import Euler, Quaternion, Vector

def parse_num(s):
    """解析数字字符串，支持inf/-inf"""
    s = s.strip()
    if s in ('inf', '+inf', 'Infinity', '+Infinity'):
        return float('inf')
    if s in ('-inf', '-Infinity'):
        return float('-inf')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def parse_vector3(s):
    """解析Unity向量格式 {x: 0, y: 0, z: 0}，返回(x, y, z)"""
    m = re.match(r'\{x:\s*([^,]+),\s*y:\s*([^,]+),\s*z:\s*([^}]+)\}', s.strip())
    if m:
        return parse_num(m.group(1)), parse_num(m.group(2)), parse_num(m.group(3))
    return 0.0, 0.0, 0.0

def parse_vector4(s):
    """解析Unity四元数格式 {x: 0, y: 0, z: 0, w: 1}，返回(x, y, z, w)"""
    m = re.match(r'\{x:\s*([^,]+),\s*y:\s*([^,]+),\s*z:\s*([^,]+),\s*w:\s*([^}]+)\}', s.strip())
    if m:
        return parse_num(m.group(1)), parse_num(m.group(2)), parse_num(m.group(3)), parse_num(m.group(4))
    # 如果没有w分量，尝试解析为vector3并补w=0
    v3 = parse_vector3(s)
    return v3[0], v3[1], v3[2], 0.0

def parse_anim_file(anim_path):
    """
    解析Unity .anim文件（YAML格式）
    使用逐行状态机解析，避免复杂正则的MULTILINE/DOTALL陷阱
    返回解析后的动画数据字典
    """
    with open(anim_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    data = {
        'name': '',
        'length': 0,
        'frameRate': 30,
        'wrapMode': 'Default',
        'curves': []
    }

    # 提取元数据
    for line in lines:
        stripped = line.strip()
        m = re.match(r'm_Name:\s+(.+)', stripped)
        if m:
            data['name'] = m.group(1).strip().strip('"\'')
            continue
        m = re.match(r'm_SampleRate:\s+([\d.eE+-]+)', stripped)
        if m:
            try:
                data['frameRate'] = float(m.group(1))
            except (ValueError, TypeError):
                pass
            continue
        m = re.match(r'm_WrapMode:\s+(\d+)', stripped)
        if m:
            wrap_map = {0: 'Default', 1: 'Once', 2: 'Loop', 4: 'PingPong', 8: 'ClampForever'}
            data['wrapMode'] = wrap_map.get(int(m.group(1)), 'Default')
            continue

    # 逐行解析曲线数据
    # 需要识别的section: m_RotationCurves, m_EulerCurves, m_PositionCurves, m_ScaleCurves, m_EditorCurves
    QUATERNION_SECTIONS = {'m_RotationCurves'}  # 四元数(xyzw)，需要拆为4条曲线
    VECTOR_SECTIONS = {'m_EulerCurves', 'm_PositionCurves', 'm_ScaleCurves'}
    SCALAR_SECTIONS = {'m_EditorCurves', 'm_FloatCurves'}
    ALL_SECTIONS = QUATERNION_SECTIONS | VECTOR_SECTIONS | SCALAR_SECTIONS

    current_section = None  # 当前section名
    in_curve_block = False  # 是否在 - curve: 块中
    in_m_curve = False  # 是否在 m_Curve: 列表中
    in_keyframe = False  # 是否在一个keyframe（- serializedVersion:）中

    # 当前曲线块的数据
    current_keyframes = []  # 当前m_Curve下的关键帧列表
    current_kf = {}  # 当前正在解析的关键帧
    current_path = ''  # 当前curve块的path
    current_m_attribute = ''  # m_EditorCurves中的m_Attribute

    def get_indent(line):
        return len(line) - len(line.lstrip())

    def flush_keyframe():
        nonlocal current_kf, in_keyframe
        if current_kf and 'time' in current_kf:
            current_keyframes.append(current_kf)
        current_kf = {}
        in_keyframe = False

    def flush_curve():
        """将当前曲线块的关键帧数据添加到data['curves']"""
        nonlocal current_keyframes, current_path, in_m_curve, in_curve_block
        nonlocal current_m_attribute

        flush_keyframe()

        if not current_keyframes:
            current_keyframes = []
            current_path = ''
            current_m_attribute = ''
            in_m_curve = False
            in_curve_block = False
            return

        path_val = current_path.strip().strip('"\'')

        if current_section in QUATERNION_SECTIONS:
            # 四元数关键帧：拆分为x, y, z, w四条曲线
            attr_names = ['m_LocalRotationQuat.x', 'm_LocalRotationQuat.y', 'm_LocalRotationQuat.z', 'm_LocalRotationQuat.w']
            comp_kfs = [[], [], [], []]
            for kf in current_keyframes:
                val = kf.get('value', (0, 0, 0, 1))
                in_s = kf.get('inSlope', (0, 0, 0, 0))
                out_s = kf.get('outSlope', (0, 0, 0, 0))
                for i in range(4):
                    v = val[i] if isinstance(val, (list, tuple)) and len(val) > i else (val if not isinstance(val, (list, tuple)) else 0)
                    ins = in_s[i] if isinstance(in_s, (list, tuple)) and len(in_s) > i else (in_s if not isinstance(in_s, (list, tuple)) else 0)
                    outs = out_s[i] if isinstance(out_s, (list, tuple)) and len(out_s) > i else (out_s if not isinstance(out_s, (list, tuple)) else 0)
                    comp_kfs[i].append({
                        'time': kf.get('time', 0),
                        'value': v,
                        'inSlope': ins,
                        'outSlope': outs,
                    })

            for i, attr_name in enumerate(attr_names):
                if comp_kfs[i]:
                    data['curves'].append({
                        'path': path_val,
                        'attribute': attr_name,
                        'keyframes': comp_kfs[i]
                    })

        elif current_section in VECTOR_SECTIONS:
            # 向量关键帧：拆分为x, y, z三条曲线
            if current_section == 'm_EulerCurves':
                attr_names = ['m_LocalRotation.x', 'm_LocalRotation.y', 'm_LocalRotation.z']
            elif current_section == 'm_PositionCurves':
                attr_names = ['m_LocalPosition.x', 'm_LocalPosition.y', 'm_LocalPosition.z']
            else:  # m_ScaleCurves
                attr_names = ['m_LocalScale.x', 'm_LocalScale.y', 'm_LocalScale.z']

            comp_kfs = [[], [], []]
            for kf in current_keyframes:
                val = kf.get('value', (0, 0, 0))
                in_s = kf.get('inSlope', (0, 0, 0))
                out_s = kf.get('outSlope', (0, 0, 0))
                for i in range(3):
                    v = val[i] if isinstance(val, (list, tuple)) else val
                    ins = in_s[i] if isinstance(in_s, (list, tuple)) else in_s
                    outs = out_s[i] if isinstance(out_s, (list, tuple)) else out_s
                    comp_kfs[i].append({
                        'time': kf.get('time', 0),
                        'value': v,
                        'inSlope': ins,
                        'outSlope': outs,
                    })

            for i, attr_name in enumerate(attr_names):
                if comp_kfs[i]:
                    data['curves'].append({
                        'path': path_val,
                        'attribute': attr_name,
                        'keyframes': comp_kfs[i]
                    })
        elif current_section in SCALAR_SECTIONS and current_m_attribute:
            # 标量关键帧（m_EditorCurves格式）
            data['curves'].append({
                'path': path_val,
                'attribute': current_m_attribute,
                'keyframes': current_keyframes
            })

        current_keyframes = []
        current_path = ''
        current_m_attribute = ''
        in_m_curve = False
        in_curve_block = False

    for line in lines:
        stripped = line.strip()
        indent = get_indent(line)

        # 空行跳过
        if not stripped:
            continue

        # 检测section头（顶层缩进，通常2空格）
        if indent == 2 and stripped.endswith(':') and not stripped.startswith('-'):
            section_name = stripped[:-1]  # 去掉冒号
            if section_name in ALL_SECTIONS:
                # 先flush上一个curve（如果有）
                if in_curve_block:
                    flush_curve()
                current_section = section_name
                in_curve_block = False
                in_m_curve = False
                continue
            elif current_section and section_name.startswith('m_'):
                # 遇到其他m_开头的section，结束当前section
                if in_curve_block:
                    flush_curve()
                current_section = None
                continue

        # 检测 "[] " 格式的空section（如 m_FloatCurves: []）
        if indent == 2 and ': []' in stripped:
            section_name = stripped.split(':')[0]
            if section_name in ALL_SECTIONS:
                if in_curve_block:
                    flush_curve()
                current_section = None
                continue

        # 如果不在已知section中，跳过
        if current_section is None:
            continue

        # 检测新曲线块的开始
        # 格式1 (m_EulerCurves等): "  - curve:"
        # 格式2 (m_FloatCurves/m_EditorCurves): "  - serializedVersion: 2"
        is_new_curve_block = False
        if stripped == '- curve:' and indent >= 2:
            is_new_curve_block = True
        elif (stripped.startswith('- serializedVersion:') and indent == 2
              and current_section in SCALAR_SECTIONS):
            is_new_curve_block = True

        if is_new_curve_block:
            if in_curve_block:
                flush_curve()
            in_curve_block = True
            in_m_curve = False
            current_keyframes = []
            current_path = ''
            current_m_attribute = ''
            continue

        if not in_curve_block:
            continue

        # 在curve块内解析

        # 检测 "curve:" (无dash，格式2中的子键)，跳过
        if stripped == 'curve:' or stripped.startswith('serializedVersion:'):
            continue

        # 检测 attribute: 行（m_EditorCurves/m_FloatCurves中使用）
        m = re.match(r'\s+attribute:\s*(.*)', line)
        if m and not in_m_curve:
            current_m_attribute = m.group(1).strip().strip('"\'')
            continue

        # 检测 m_Attribute: 行（旧格式）
        m = re.match(r'\s+m_Attribute:\s*(.*)', line)
        if m and not in_m_curve:
            current_m_attribute = m.group(1).strip().strip('"\'')
            continue

        # 检测 path: 行（curve块末尾）
        m = re.match(r'\s+path:\s*(.*)', line)
        if m and not in_m_curve:
            current_path = m.group(1).strip()
            continue

        # 检测 m_Curve: 开始关键帧列表
        if stripped == 'm_Curve:':
            in_m_curve = True
            continue

        if not in_m_curve:
            continue

        # ===== 在m_Curve列表中解析关键帧 =====

        # 检测新关键帧开始: "- serializedVersion: N"（在m_Curve内部，indent >= 6）
        m = re.match(r'\s+-\s+serializedVersion:\s*\d+', line)
        if m:
            flush_keyframe()
            in_keyframe = True
            continue

        # m_Curve结束标志：m_PreInfinity, m_PostInfinity, m_RotationOrder等
        if stripped.startswith('m_Pre') or stripped.startswith('m_Post') or stripped.startswith('m_Rotation'):
            flush_keyframe()
            in_m_curve = False
            in_keyframe = False
            continue

        if not in_keyframe:
            # 可能遇到path:行或attribute:行（m_Curve结束后）
            m2 = re.match(r'\s+path:\s*(.*)', line)
            if m2:
                current_path = m2.group(1).strip()
                in_m_curve = False
            m3 = re.match(r'\s+attribute:\s*(.*)', line)
            if m3:
                current_m_attribute = m3.group(1).strip().strip('"\'')
                in_m_curve = False
            continue

        # 解析关键帧字段
        m = re.match(r'\s+time:\s+([\d.eE+\-]+)', line)
        if m:
            current_kf['time'] = parse_num(m.group(1))
            continue

        # value可以是四元数、向量或标量
        m = re.match(r'\s+value:\s*(\{.+\})', line)
        if m:
            vec_str = m.group(1)
            if current_section in QUATERNION_SECTIONS:
                current_kf['value'] = parse_vector4(vec_str)
            else:
                current_kf['value'] = parse_vector3(vec_str)
            continue
        m = re.match(r'\s+value:\s+([\d.eE+\-]+)', line)
        if m:
            current_kf['value'] = parse_num(m.group(1))
            continue

        m = re.match(r'\s+inSlope:\s*(\{.+\})', line)
        if m:
            vec_str = m.group(1)
            current_kf['inSlope'] = parse_vector4(vec_str) if current_section in QUATERNION_SECTIONS else parse_vector3(vec_str)
            continue
        m = re.match(r'\s+inSlope:\s+([\d.eE+\-infintyIFNT]+)', line)
        if m:
            current_kf['inSlope'] = parse_num(m.group(1))
            continue

        m = re.match(r'\s+outSlope:\s*(\{.+\})', line)
        if m:
            vec_str = m.group(1)
            current_kf['outSlope'] = parse_vector4(vec_str) if current_section in QUATERNION_SECTIONS else parse_vector3(vec_str)
            continue
        m = re.match(r'\s+outSlope:\s+([\d.eE+\-infintyIFNT]+)', line)
        if m:
            current_kf['outSlope'] = parse_num(m.group(1))
            continue

        # 如果在keyframe中遇到path:/attribute:行，说明m_Curve列表已结束
        m = re.match(r'\s+path:\s*(.*)', line)
        if m:
            flush_keyframe()
            current_path = m.group(1).strip()
            in_m_curve = False
            in_keyframe = False
            continue
        m = re.match(r'\s+attribute:\s*(.*)', line)
        if m:
            flush_keyframe()
            current_m_attribute = m.group(1).strip().strip('"\'')
            in_m_curve = False
            in_keyframe = False
            continue

    # flush最后一个curve
    if in_curve_block:
        flush_curve()

    # 去重：如果已有向量section的曲线，移除m_EditorCurves中重复的标量拆分
    # m_EditorCurves中localEulerAnglesRaw.x/y/z与m_EulerCurves的数据相同
    vector_keys = set()
    for c in data['curves']:
        attr = c['attribute']
        if attr.startswith('m_Local'):
            vector_keys.add((c['path'], attr))
    if vector_keys:
        # 映射EditorCurves属性名到向量属性名
        # 注意：只映射EditorCurves中的别名，不映射Vector Sections自身的属性名
        editor_to_vector = {
            'localEulerAnglesRaw.x': 'm_LocalRotation.x',
            'localEulerAnglesRaw.y': 'm_LocalRotation.y',
            'localEulerAnglesRaw.z': 'm_LocalRotation.z',
        }
        deduped = []
        for c in data['curves']:
            mapped = editor_to_vector.get(c['attribute'])
            if mapped and (c['path'], mapped) in vector_keys:
                continue  # 跳过重复的EditorCurves数据
            deduped.append(c)
        data['curves'] = deduped

    # 如果长度为0，从关键帧中计算
    if data['length'] == 0:
        max_time = 0
        for curve in data['curves']:
            for kf in curve.get('keyframes', []):
                max_time = max(max_time, kf.get('time', 0))
        if max_time > 0:
            data['length'] = max_time

    # 尝试从m_AnimationClipSettings获取StopTime作为length
    if data['length'] == 0:
        for line in lines:
            m = re.match(r'\s+m_StopTime:\s+([\d.eE+\-]+)', line)
            if m:
                try:
                    stop_time = float(m.group(1))
                    if stop_time > 0:
                        data['length'] = stop_time
                except (ValueError, TypeError):
                    pass
                break

    print(f"解析完成: {anim_path}")
    print(f"  名称={data['name']}, 长度={data['length']}s, 帧率={data['frameRate']}, 曲线数={len(data['curves'])}")
    return data

def map_unity_to_blender_property(attribute):
    """
    将Unity属性名映射到Blender属性名
    处理Unity(左手系Y-up)到Blender(右手系Z-up)的坐标系转换

    Returns:
        (data_path, index, value_scale) - value_scale用于乘以关键帧值
        处理轴交换(Y<->Z)、取反、角度转弧度等
    """
    attribute_lower = attribute.lower()
    deg2rad = math.pi / 180.0

    # 位置映射: Unity(X,Y,Z) -> Blender(X,-Z,Y)
    # Unity X -> Blender X, Unity Y -> Blender Z, Unity Z -> Blender -Y
    if 'localposition' in attribute_lower or 'position' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'location', 0, 1.0
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'location', 2, 1.0
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'location', 1, -1.0

    # 四元数旋转映射（来自m_RotationCurves）
    # Unity Quat(X,Y,Z,W) -> Blender Quat(W,X,-Z,Y)
    if 'localrotationquat' in attribute_lower:
        if '.x' in attribute_lower:
            return 'rotation_quaternion', 1, 1.0
        elif '.y' in attribute_lower:
            return 'rotation_quaternion', 3, 1.0
        elif '.z' in attribute_lower:
            return 'rotation_quaternion', 2, -1.0
        elif '.w' in attribute_lower:
            return 'rotation_quaternion', 0, 1.0

    # 欧拉旋转映射（角度->弧度 + 坐标系转换）
    # Unity Euler X -> Blender Euler X, Y -> Z, Z -> -Y
    if 'localrotation' in attribute_lower or 'rotation' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'rotation_euler', 0, deg2rad
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'rotation_euler', 2, deg2rad
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'rotation_euler', 1, -deg2rad
        elif '.w' in attribute_lower or attribute_lower.endswith('w'):
            return 'rotation_quaternion', 3, 1.0

    # 缩放映射: Unity(X,Y,Z) -> Blender(X,Z,Y)（缩放无需取反）
    if 'localscale' in attribute_lower or 'scale' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'scale', 0, 1.0
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'scale', 2, 1.0
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'scale', 1, 1.0

    # 其他属性，尝试直接使用
    prop_name = attribute
    if prop_name.startswith('m_'):
        prop_name = prop_name[2:]

    array_match = re.search(r'\[(\d+)\]', prop_name)
    index = int(array_match.group(1)) if array_match else 0
    prop_name = re.sub(r'\[\d+\]', '', prop_name)

    return prop_name, index, 1.0

def get_bone_name_from_path(unity_path):
    """从Unity路径中提取骨骼名称（路径最后一段）"""
    if not unity_path:
        return None
    parts = unity_path.strip('/').split('/')
    return parts[-1] if parts else None


def build_data_path(base_property, unity_path, target_obj):
    """
    构建Blender F-Curve的data_path
    对于骨骼动画使用 pose.bones["BoneName"].property 格式
    """
    if not unity_path or unity_path.startswith('Curve_') or unity_path.startswith('Path_'):
        return base_property

    bone_name = get_bone_name_from_path(unity_path)

    # 只要有骨骼名称就使用骨骼路径，不再要求骨架中必须存在该骨骼
    # 这样即使导入时没有选中骨架或骨架中没有对应骨骼，F-Curve路径也是正确的
    if bone_name:
        return f'pose.bones["{bone_name}"].{base_property}'

    return base_property


def import_animation_from_anim(anim_path):
    """
    从Unity .anim文件导入动画数据并创建Blender动作

    Args:
        anim_path: .anim文件路径
    """
    # 解析.anim文件
    data = parse_anim_file(anim_path)

    animation_name = data.get('name', os.path.splitext(os.path.basename(anim_path))[0])
    length = data.get('length', 0)
    frame_rate = data.get('frameRate', 30)
    curves = data.get('curves', [])

    print(f"解析结果: 名称={animation_name}, 长度={length}, 帧率={frame_rate}, 曲线数={len(curves)}")

    # 如果长度仍为0，再次尝试从关键帧计算
    if length == 0:
        max_time = 0
        for curve in curves:
            for kf in curve.get('keyframes', []):
                max_time = max(max_time, kf.get('time', 0))
        if max_time > 0:
            length = max_time
            print(f"从关键帧重新计算动画长度: {length} 秒")

    # 设置场景帧率
    bpy.context.scene.render.fps = int(frame_rate)

    # 创建或获取动作
    action_name = animation_name
    if action_name in bpy.data.actions:
        action = bpy.data.actions[action_name]
        action.fcurves.clear()
    else:
        action = bpy.data.actions.new(name=action_name)

    # 获取目标对象（用于判断是否为骨骼动画）
    target_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None

    # 按路径和属性组织数据
    property_groups = {}
    for curve in curves:
        path = curve.get('path', '')
        attribute = curve.get('attribute', '')
        key = (path, attribute)

        if key not in property_groups:
            property_groups[key] = []
        property_groups[key].extend(curve.get('keyframes', []))

    # 处理每个属性
    imported_count = 0
    processed_curves = set()

    print(f"开始处理 {len(property_groups)} 个属性组")

    for (path, attribute), keyframes in property_groups.items():
        if not keyframes:
            continue

        # 映射到Blender属性（包含坐标系转换和角度转弧度）
        data_path, index, value_scale = map_unity_to_blender_property(attribute)

        # 构建完整的data_path（处理骨骼动画）
        full_data_path = build_data_path(data_path, path, target_obj)

        # 使用完整路径+索引作为去重key，避免不同骨骼的同名属性被跳过
        curve_key = (full_data_path, index)

        if curve_key in processed_curves:
            print(f"跳过已处理的曲线: {full_data_path}[{index}]")
            continue

        # 按时间排序关键帧
        keyframes.sort(key=lambda kf: kf.get('time', 0))

        # 检查是否已存在相同的F-Curve
        existing_fcurve = None
        for fc in action.fcurves:
            if fc.data_path == full_data_path and fc.array_index == index:
                existing_fcurve = fc
                break

        if existing_fcurve:
            action.fcurves.remove(existing_fcurve)

        # 创建F-Curve
        fcurve = action.fcurves.new(data_path=full_data_path, index=index)
        fcurve.keyframe_points.add(len(keyframes))

        # 设置关键帧
        for i, kf_data in enumerate(keyframes):
            time = kf_data.get('time', 0)
            raw_value = kf_data.get('value', 0)

            # 应用坐标系转换（轴交换、取反、角度转弧度等）
            value = raw_value * value_scale

            # 转换时间到帧数
            frame = time * frame_rate

            kp = fcurve.keyframe_points[i]
            kp.co = (frame, value)

            # 检查是否为阶跃函数（无穷大切线）
            in_slope = kf_data.get('inSlope', 0)
            out_slope = kf_data.get('outSlope', 0)

            is_step_in = isinstance(in_slope, (int, float)) and math.isinf(in_slope)
            is_step_out = isinstance(out_slope, (int, float)) and math.isinf(out_slope)

            if is_step_in or is_step_out:
                # 阶跃函数：使用常量插值
                kp.interpolation = 'CONSTANT'
            else:
                kp.interpolation = 'BEZIER'

                # 将Unity的slope(dValue/dTime)转换为Blender handle位置
                # 同时应用value_scale到斜率（值取反则斜率也取反，角度转弧度同理）
                scaled_in_slope = (in_slope * value_scale) if isinstance(in_slope, (int, float)) else 0.0
                scaled_out_slope = (out_slope * value_scale) if isinstance(out_slope, (int, float)) else 0.0

                # 计算handle距离：使用相邻帧间距的1/3（Bezier约定）
                if i > 0:
                    prev_frame = keyframes[i - 1].get('time', 0) * frame_rate
                    dt_left = (frame - prev_frame) / 3.0
                else:
                    dt_left = 1.0 / 3.0

                if i < len(keyframes) - 1:
                    next_frame = keyframes[i + 1].get('time', 0) * frame_rate
                    dt_right = (next_frame - frame) / 3.0
                else:
                    dt_right = 1.0 / 3.0

                if dt_left > 0 and dt_right > 0:
                    # 使用FREE手柄类型以便手动设置位置不被覆盖
                    kp.handle_left_type = 'FREE'
                    kp.handle_right_type = 'FREE'
                    # Unity slope是dValue/dTime，转换为dValue/dFrame
                    slope_in_per_frame = scaled_in_slope / frame_rate
                    slope_out_per_frame = scaled_out_slope / frame_rate
                    kp.handle_left = (frame - dt_left, value - slope_in_per_frame * dt_left)
                    kp.handle_right = (frame + dt_right, value + slope_out_per_frame * dt_right)
                else:
                    kp.handle_left_type = 'AUTO'
                    kp.handle_right_type = 'AUTO'

        # 更新F-Curve
        fcurve.update()
        imported_count += 1
        processed_curves.add(curve_key)
        print(f"  成功创建F-Curve: {full_data_path}[{index}], 关键帧数: {len(keyframes)}")

    # 设置动作范围
    if action.fcurves:
        if length <= 0:
            max_frame = 0
            for fc in action.fcurves:
                if fc.keyframe_points:
                    max_frame = max(max_frame, max(kp.co[0] for kp in fc.keyframe_points))
            if max_frame > 0:
                length = max_frame / frame_rate
                print(f"从F-Curve计算动画长度: {length} 秒 ({max_frame} 帧)")

        end_frame = length * frame_rate if length > 0 else 1
        action.frame_range = (0, end_frame)
        print(f"设置动作范围: 0 - {end_frame} 帧 (长度: {length} 秒)")

    # 将动作分配给选中的对象
    if target_obj:
        if target_obj.animation_data is None:
            target_obj.animation_data_create()
        target_obj.animation_data.action = action
        print(f"动画 '{action_name}' 已分配给对象 '{target_obj.name}'")
    else:
        print(f"动画 '{action_name}' 已创建。请手动将其分配给对象。")

    print(f"成功导入动画: {animation_name}, 时长: {length}s, 帧率: {frame_rate}fps, 曲线数: {imported_count}")

    return action


class ImportAnimationAnimOperator(bpy.types.Operator):
    """Blender操作符：导入Unity .anim文件"""
    bl_idname = "animation.import_anim"
    bl_label = "导入Unity动画文件(.anim)"
    bl_description = "直接导入Unity的.anim文件（YAML格式）并创建动作文件\n\n支持所有Unity动画数据，包括关键帧、切线、曲线等"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        name="文件路径",
        description="Unity .anim文件路径",
        maxlen=1024,
        default=""
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.anim",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "未选择文件")
            return {'CANCELLED'}
        
        try:
            action = import_animation_from_anim(self.filepath)
            # 保存路径到场景属性
            context.scene.animation_anim_import_path = os.path.dirname(self.filepath)
            self.report({'INFO'}, f"成功导入动画: {action.name}\n文件位置: {self.filepath}")
            return {'FINISHED'}
        except FileNotFoundError:
            self.report({'ERROR'}, f"文件未找到: {self.filepath}\n\n请检查文件路径是否正确")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # 获取默认路径
        default_path = ""
        
        # 尝试从场景属性获取上次使用的路径
        if hasattr(context.scene, 'animation_anim_import_path'):
            default_path = context.scene.animation_anim_import_path
        
        # 如果场景属性中没有，尝试查找Unity项目的常见路径
        if not default_path or not os.path.exists(default_path):
            possible_paths = [
                os.path.join(os.path.expanduser("~"), "Documents", "Unity", "Projects"),
                "D:\\work\\p2_client\\Assets",
                "C:\\Users\\admin\\Documents\\Unity\\Projects",
            ]
            
            for base_path in possible_paths:
                if os.path.exists(base_path):
                    default_path = base_path
                    break
        
        # 设置默认文件路径
        if default_path and os.path.exists(default_path):
            self.filepath = os.path.join(default_path, "*.anim")
        else:
            self.filepath = bpy.path.abspath("//")
            if not self.filepath:
                self.filepath = os.path.expanduser("~")
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ============================================================
# Unity Humanoid 标准骨骼层级定义
# 用于修正FBX导入时被拆散的骨骼父子关系
# ============================================================
UNITY_HUMANOID_HIERARCHY = {
    # name: parent_name  (None = root)
    'Root': None,
    'Hips': 'Root',
    'Pelvis': 'Hips',
    'Spine': 'Pelvis',
    'Spine1': 'Spine',
    'Spine2': 'Spine1',
    'Neck': 'Spine2',
    'Head': 'Neck',
    # Left arm
    'LeftShoulder': 'Spine2',
    'LeftArm': 'LeftShoulder',
    'LeftForeArm': 'LeftArm',
    'LeftHand': 'LeftForeArm',
    # Right arm
    'RightShoulder': 'Spine2',
    'RightArm': 'RightShoulder',
    'RightForeArm': 'RightArm',
    'RightHand': 'RightForeArm',
    # Left leg
    'LeftUpLeg': 'Hips',
    'LeftLeg': 'LeftUpLeg',
    'LeftFoot': 'LeftLeg',
    'LeftToe': 'LeftFoot',
    'LeftToeBase': 'LeftFoot',
    # Right leg
    'RightUpLeg': 'Hips',
    'RightLeg': 'RightUpLeg',
    'RightFoot': 'RightLeg',
    'RightToe': 'RightFoot',
    'RightToeBase': 'RightFoot',
    # Left fingers (5指，每指最多3节)
    'LeftFinger00': 'LeftHand', 'LeftFinger01': 'LeftFinger00', 'LeftFinger02': 'LeftFinger01',
    'LeftFinger10': 'LeftHand', 'LeftFinger11': 'LeftFinger10', 'LeftFinger12': 'LeftFinger11',
    'LeftFinger20': 'LeftHand', 'LeftFinger21': 'LeftFinger20', 'LeftFinger22': 'LeftFinger21',
    'LeftFinger30': 'LeftHand', 'LeftFinger31': 'LeftFinger30', 'LeftFinger32': 'LeftFinger31',
    'LeftFinger40': 'LeftHand', 'LeftFinger41': 'LeftFinger40', 'LeftFinger42': 'LeftFinger41',
    # LeftFinge (FBX中的拼写变体)
    'LeftFinge30': 'LeftHand', 'LeftFinge31': 'LeftFinge30', 'LeftFinge32': 'LeftFinge31',
    # Right fingers
    'RightFinger00': 'RightHand', 'RightFinger01': 'RightFinger00', 'RightFinger02': 'RightFinger01',
    'RightFinger10': 'RightHand', 'RightFinger11': 'RightFinger10', 'RightFinger12': 'RightFinger11',
    'RightFinger20': 'RightHand', 'RightFinger21': 'RightFinger20', 'RightFinger22': 'RightFinger21',
    'RightFinger30': 'RightHand', 'RightFinger31': 'RightFinger30', 'RightFinger32': 'RightFinger31',
    'RightFinger40': 'RightHand', 'RightFinger41': 'RightFinger40', 'RightFinger42': 'RightFinger41',
    # Head附属
    'HeadBase': 'Head',
    'Root_Position': 'Root',
}

# 需要跳过的骨骼（Nub终端标记、辅助节点等）
SKIP_BONE_PATTERNS = {'Nub', 'Footsteps', 'Base'}  # 包含这些字符串的骨骼跳过


def build_armature_from_fbx(fbx_paths, armature_name="UnityArmature", skip_nub=True):
    """
    从一个或多个Unity Part FBX文件构建正确的Unity Humanoid骨架

    FBX导入时骨骼会被拆分为Armature骨骼+Empty对象，父子关系可能错乱。
    本函数收集所有骨骼节点的位置信息，然后按Unity Humanoid标准层级重建一个完整的Armature。

    Args:
        fbx_paths: FBX文件路径（字符串或字符串列表）
        armature_name: 创建的骨架名称
        skip_nub: 是否跳过Nub终端标记骨骼

    Returns:
        创建的Armature对象
    """
    if isinstance(fbx_paths, str):
        fbx_paths = [fbx_paths]

    # 收集所有FBX的骨骼节点名称和世界坐标
    all_nodes = {}  # name -> world_position

    for fbx_path in fbx_paths:
        # 清空场景用于导入
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # 导入FBX
        bpy.ops.import_scene.fbx(filepath=fbx_path, ignore_leaf_bones=False)

        # 收集Empty和Armature中的骨骼
        for obj in bpy.data.objects:
            if obj.type == 'EMPTY':
                all_nodes[obj.name] = obj.matrix_world.translation.copy()
            elif obj.type == 'ARMATURE':
                # Armature对象本身也是一个节点（通常名为Spine）
                all_nodes[obj.name] = obj.matrix_world.translation.copy()
                # 收集其内部骨骼
                for bone in obj.data.bones:
                    head_world = obj.matrix_world @ bone.head_local
                    all_nodes[bone.name] = head_world.copy()

    # 过滤节点
    if skip_nub:
        filtered_nodes = {}
        for name, pos in all_nodes.items():
            skip = False
            for pattern in SKIP_BONE_PATTERNS:
                if pattern in name and name not in UNITY_HUMANOID_HIERARCHY:
                    skip = True
                    break
            if not skip:
                filtered_nodes[name] = pos
        all_nodes = filtered_nodes

    # 过滤掉Mesh对象名（不是骨骼）
    mesh_names = {obj.name for obj in bpy.data.objects if obj.type == 'MESH'}
    all_nodes = {n: p for n, p in all_nodes.items() if n not in mesh_names}

    print(f"收集到 {len(all_nodes)} 个骨骼节点")

    # 清空场景准备构建骨架
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for arm in list(bpy.data.armatures):
        bpy.data.armatures.remove(arm)

    # 构建children映射（使用标准层级）
    children_map = {}
    for name in all_nodes:
        parent = UNITY_HUMANOID_HIERARCHY.get(name)
        if parent and parent in all_nodes:
            children_map.setdefault(parent, []).append(name)

    # 创建Armature
    arm_data = bpy.data.armatures.new(armature_name)
    arm_obj = bpy.data.objects.new(armature_name, arm_data)
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)

    bpy.ops.object.mode_set(mode='EDIT')

    BONE_LENGTH = 0.05

    def create_bone(name):
        """递归创建骨骼"""
        if name not in all_nodes:
            return
        if name in arm_data.edit_bones:
            return  # 已创建

        pos = all_nodes[name]
        bone = arm_data.edit_bones.new(name)
        bone.head = pos

        # 确定tail位置：优先使用第一个子骨骼位置
        children = children_map.get(name, [])
        tail_set = False
        if children:
            for child_name in children:
                if child_name in all_nodes:
                    child_pos = all_nodes[child_name]
                    if (child_pos - pos).length > 0.001:
                        bone.tail = child_pos
                        tail_set = True
                        break

        if not tail_set:
            # 无有效子骨骼，沿父骨骼方向延伸
            parent_name = UNITY_HUMANOID_HIERARCHY.get(name)
            if parent_name and parent_name in all_nodes:
                direction = pos - all_nodes[parent_name]
                if direction.length > 0.001:
                    bone.tail = pos + direction.normalized() * BONE_LENGTH
                else:
                    bone.tail = pos + Vector((0, 0, BONE_LENGTH))
            else:
                bone.tail = pos + Vector((0, 0, BONE_LENGTH))

        # 设置父骨骼
        parent_name = UNITY_HUMANOID_HIERARCHY.get(name)
        if parent_name and parent_name in arm_data.edit_bones:
            bone.parent = arm_data.edit_bones[parent_name]

        # 递归创建子骨骼
        for child_name in children:
            create_bone(child_name)

    # 从Root开始创建
    if 'Root' in all_nodes:
        create_bone('Root')

    # 创建不在标准层级中但存在于FBX中的额外骨骼（如面部骨骼）
    for name in list(all_nodes.keys()):
        if name not in arm_data.edit_bones and name in UNITY_HUMANOID_HIERARCHY:
            create_bone(name)

    bpy.ops.object.mode_set(mode='OBJECT')

    # 设置显示
    arm_data.display_type = 'STICK'
    arm_obj.show_in_front = True

    bone_count = len(arm_data.bones)
    print(f"成功创建骨架 '{armature_name}'，共 {bone_count} 根骨骼")
    for b in arm_data.bones:
        parent = b.parent.name if b.parent else 'ROOT'
        print(f"  {parent} > {b.name}")

    return arm_obj


class BuildUnityArmatureOperator(bpy.types.Operator):
    """从Unity Part FBX文件构建正确命名的Unity Humanoid骨架"""
    bl_idname = "animation.build_unity_armature"
    bl_label = "从FBX构建Unity骨架"
    bl_description = "导入Unity Part FBX文件并构建正确的Unity Humanoid骨架\n\n解决FBX导入骨骼被拆散为Empty的问题"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        name="文件路径",
        description="Unity Part FBX文件路径",
        maxlen=1024,
        default=""
    )

    filter_glob: bpy.props.StringProperty(
        default="*.fbx",
        options={'HIDDEN'}
    )

    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "未选择文件")
            return {'CANCELLED'}

        try:
            arm_obj = build_armature_from_fbx(self.filepath)
            context.scene.animation_fbx_import_path = os.path.dirname(self.filepath)
            self.report({'INFO'}, f"成功构建骨架: {arm_obj.name}，共 {len(arm_obj.data.bones)} 根骨骼")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"构建骨架失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

    def invoke(self, context, event):
        default_path = ""
        if hasattr(context.scene, 'animation_fbx_import_path'):
            default_path = context.scene.animation_fbx_import_path

        if default_path and os.path.exists(default_path):
            self.filepath = os.path.join(default_path, "*.fbx")
        else:
            self.filepath = bpy.path.abspath("//")
            if not self.filepath:
                self.filepath = os.path.expanduser("~")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def register():
    """注册操作符和属性"""
    bpy.utils.register_class(ImportAnimationAnimOperator)
    bpy.utils.register_class(BuildUnityArmatureOperator)

    # 注册场景属性，用于保存上次导入的路径
    bpy.types.Scene.animation_anim_import_path = bpy.props.StringProperty(
        name="动画.anim导入路径",
        description="上次导入.anim文件的路径",
        default=""
    )
    bpy.types.Scene.animation_fbx_import_path = bpy.props.StringProperty(
        name="FBX骨架导入路径",
        description="上次导入FBX骨架的路径",
        default=""
    )


def unregister():
    """注销操作符和属性"""
    bpy.utils.unregister_class(ImportAnimationAnimOperator)
    bpy.utils.unregister_class(BuildUnityArmatureOperator)

    # 注销场景属性
    if hasattr(bpy.types.Scene, 'animation_anim_import_path'):
        del bpy.types.Scene.animation_anim_import_path
    if hasattr(bpy.types.Scene, 'animation_fbx_import_path'):
        del bpy.types.Scene.animation_fbx_import_path


if __name__ == "__main__":
    register()

