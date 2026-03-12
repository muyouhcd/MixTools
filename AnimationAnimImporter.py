"""
Blender工具：直接导入Unity .anim文件（YAML格式）
集成到MixTools插件中
"""

import bpy
import os
import re
from mathutils import Euler, Quaternion, Vector

def parse_yaml_value(value_str):
    """解析YAML值（简化版，处理Unity .anim文件中的常见格式）"""
    value_str = value_str.strip()
    
    # 处理浮点数
    if '.' in value_str or 'e' in value_str.lower() or 'E' in value_str:
        try:
            return float(value_str)
        except:
            pass
    
    # 处理整数
    try:
        return int(value_str)
    except:
        pass
    
    # 处理布尔值
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    
    # 处理字符串（移除引号）
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1]
    if value_str.startswith("'") and value_str.endswith("'"):
        return value_str[1:-1]
    
    # 处理特殊值
    if value_str == 'inf' or value_str == '+inf':
        return float('inf')
    if value_str == '-inf':
        return float('-inf')
    
    return value_str

def parse_anim_file(anim_path):
    """
    解析Unity .anim文件（YAML格式）
    返回解析后的动画数据字典
    """
    with open(anim_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"开始解析.anim文件: {anim_path}")
    print(f"文件大小: {len(content)} 字符")
    
    # 分析文件结构
    print("\n=== 文件结构分析 ===")
    # 查找所有顶级键
    top_level_keys = re.findall(r'^(\w+):', content, re.MULTILINE)
    print(f"顶级键: {set(top_level_keys[:20])}")  # 只显示前20个
    
    # 查找包含curve的行
    curve_lines = [line for line in content.split('\n') if 'curve' in line.lower() or 'Curve' in line]
    print(f"包含'curve'的行数: {len(curve_lines)}")
    if curve_lines:
        print(f"前5行示例: {curve_lines[:5]}")
    
    # 查找包含m_Path的行
    path_lines = [line for line in content.split('\n') if 'm_Path' in line]
    print(f"包含'm_Path'的行数: {len(path_lines)}")
    if path_lines:
        print(f"前3行示例: {path_lines[:3]}")
    
    # 查找包含m_Keys的行
    keys_lines = [line for line in content.split('\n') if 'm_Keys' in line]
    print(f"包含'm_Keys'的行数: {len(keys_lines)}")
    
    print("==================\n")
    
    data = {
        'name': '',
        'length': 0,
        'frameRate': 30,
        'wrapMode': 'Default',
        'curves': []
    }
    
    # 提取动画名称 - 更灵活的匹配
    name_match = re.search(r'm_Name:\s+(.+?)(?:\s*$|\s*#)', content, re.MULTILINE)
    if name_match:
        name_str = name_match.group(1).strip().strip('"\'')
        data['name'] = name_str
    
    # 提取长度和帧率 - 更灵活的匹配，支持不同缩进
    length_match = re.search(r'm_Length:\s+([\d.eE+-]+)', content, re.MULTILINE)
    if length_match:
        try:
            data['length'] = float(length_match.group(1))
        except:
            pass
    
    # 如果长度仍为0，尝试从关键帧中计算最大时间
    if data['length'] == 0:
        # 先解析曲线，然后从关键帧中找最大时间
        pass  # 稍后在解析曲线后处理
    
    frame_rate_match = re.search(r'm_FrameRate:\s+([\d.eE+-]+)', content, re.MULTILINE)
    if frame_rate_match:
        try:
            data['frameRate'] = float(frame_rate_match.group(1))
        except:
            pass
    
    wrap_mode_match = re.search(r'^m_WrapMode:\s+(\d+)', content, re.MULTILINE)
    if wrap_mode_match:
        wrap_mode_map = {0: 'Default', 1: 'Once', 2: 'Loop', 4: 'PingPong', 8: 'ClampForever'}
        wrap_mode = int(wrap_mode_match.group(1))
        data['wrapMode'] = wrap_mode_map.get(wrap_mode, 'Default')
    
    # 解析曲线数据
    # Unity .anim文件中的曲线结构：
    # m_EditorCurves:
    #   - curve:
    #       m_Path: "path/to/object"
    #       m_Attribute: "m_LocalPosition.x"
    #       m_Curve:
    #         m_Keys:
    #           - time: 0
    #             value: 1.0
    #             inSlope: 0
    #             outSlope: 0
    
    # Unity .anim文件可能使用不同的结构
    # 查找m_EulerCurves（Unity 2018+使用的格式）
    # 需要匹配到下一个顶级键之前的所有内容
    euler_curves_match = re.search(r'm_EulerCurves:\s*\n(.*?)(?=\n\s+[A-Z]\w+:|$)', content, re.MULTILINE | re.DOTALL)
    
    # 查找m_EditorCurves（旧格式）
    editor_curves_match = re.search(r'm_EditorCurves:\s*\n(.*?)(?=\n\s+[A-Z]\w+:|$)', content, re.MULTILINE | re.DOTALL)
    
    # 查找m_ClipBindingConstant (Unity 2018+)
    clip_binding_match = re.search(r'm_ClipBindingConstant:\s*\n(.*?)(?=\n\s+[A-Z]\w+:|$)', content, re.MULTILINE | re.DOTALL)
    
    # 尝试多种方式查找曲线
    curves_section = None
    if euler_curves_match:
        curves_section = euler_curves_match.group(1)
        print("使用m_EulerCurves部分")
    elif editor_curves_match:
        curves_section = editor_curves_match.group(1)
        print("使用m_EditorCurves部分")
    else:
        # 查找m_ClipBindingConstant (Unity 2018+)
        clip_binding_match = re.search(r'm_ClipBindingConstant:\s*\n(.*?)(?=\n\s*\w+:|$)', content, re.MULTILINE | re.DOTALL)
        if clip_binding_match:
            curves_section = clip_binding_match.group(1)
            print("使用m_ClipBindingConstant部分")
        else:
            print("警告: 未找到标准曲线部分，尝试在整个文件中查找")
            curves_section = content
    
    print(f"曲线部分长度: {len(curves_section)} 字符")
    
    # 如果曲线部分太短，说明匹配有问题，尝试更宽松的匹配
    if len(curves_section) < 100:
        print("警告: 曲线部分太短，尝试更宽松的匹配...")
        # 尝试匹配到文件末尾或下一个顶级键
        euler_curves_match2 = re.search(r'm_EulerCurves:\s*\n(.*)', content, re.MULTILINE | re.DOTALL)
        if euler_curves_match2:
            curves_section = euler_curves_match2.group(1)
            # 找到下一个顶级键的位置
            next_key_match = re.search(r'\n\s+[A-Z]\w+:', curves_section)
            if next_key_match:
                curves_section = curves_section[:next_key_match.start()]
            print(f"重新匹配后曲线部分长度: {len(curves_section)} 字符")
    
    # 查找m_ClipBindingConstant来获取路径和属性映射
    clip_binding_section = None
    binding_match = re.search(r'm_ClipBindingConstant:\s*\n(.*?)(?=\n\s+[A-Z]\w+:|$)', content, re.MULTILINE | re.DOTALL)
    if binding_match:
        clip_binding_section = binding_match.group(1)
        print(f"\n找到m_ClipBindingConstant部分，长度: {len(clip_binding_section)} 字符")
        # 查找路径和属性信息
        path_matches = re.findall(r'path:\s*(.+?)(?:\s*\n|$)', clip_binding_section, re.MULTILINE)
        attr_matches = re.findall(r'attribute:\s*(.+?)(?:\s*\n|$)', clip_binding_section, re.MULTILINE)
        print(f"找到 {len(path_matches)} 个路径, {len(attr_matches)} 个属性")
        if path_matches:
            print(f"路径示例（前5个）: {path_matches[:5]}")
        if attr_matches:
            print(f"属性示例（前5个）: {attr_matches[:5]}")
    
    # 先查看原始文件中的curve块位置
    print(f"\n=== 查找curve块的位置 ===")
    curve_line_numbers = []
    for i, line in enumerate(content.split('\n'), 1):
        if '- curve:' in line:
            curve_line_numbers.append(i)
    print(f"找到 {len(curve_line_numbers)} 个 '- curve:' 在第 {curve_line_numbers[:10]} 行")
    
    # 查看第一个curve块前后的内容
    if curve_line_numbers:
        first_curve_line = curve_line_numbers[0]
        lines = content.split('\n')
        start_idx = max(0, first_curve_line - 5)
        end_idx = min(len(lines), first_curve_line + 50)
        print(f"\n第一个curve块周围的内容（行 {start_idx+1} 到 {end_idx}）:")
        for i in range(start_idx, end_idx):
            print(f"  {i+1:5d}: {lines[i]}")
    
    # Unity新格式可能使用不同的结构
    # 尝试逐行解析而不是用正则表达式
    print(f"\n=== 尝试逐行解析curve块 ===")
    
    # 查找所有曲线部分（m_EulerCurves, m_ScaleCurves, m_PositionCurves等）
    all_curves_sections = {}
    section_names = ['m_EulerCurves', 'm_ScaleCurves', 'm_PositionCurves', 'm_EditorCurves']
    
    for i, section_name in enumerate(section_names):
        # 查找当前section的开始位置
        section_start = re.search(rf'^\s+{section_name}:\s*$', content, re.MULTILINE)
        if section_start:
            start_pos = section_start.end()
            # 跳过可能的换行符
            while start_pos < len(content) and content[start_pos] in '\n\r':
                start_pos += 1
            
            print(f"  {section_name} 开始位置: {start_pos}, 匹配文本: {repr(content[section_start.start():section_start.end()])}")
            
            # 查找下一个section的位置（或文件末尾）
            next_section_pos = len(content)
            for next_section in section_names[i+1:]:
                next_match = re.search(rf'^\s+{next_section}:\s*$', content[start_pos:], re.MULTILINE)
                if next_match:
                    next_section_pos = start_pos + next_match.start()
                    print(f"  找到下一个section {next_section} 在位置: {next_section_pos}")
                    break
            
            # 如果没找到下一个section，查找其他顶级键
            if next_section_pos == len(content):
                # 查找下一个顶级键（以m_开头，但不是已知的section）
                other_match = re.search(rf'^\s+m_[A-Z]\w+:\s*$', content[start_pos:], re.MULTILINE)
                if other_match:
                    # 检查是否是已知的section
                    match_start = start_pos + other_match.start()
                    match_end = start_pos + other_match.end()
                    match_text = content[match_start:match_end].strip()
                    if match_text not in section_names:
                        next_section_pos = match_start
                        print(f"  找到下一个顶级键 {match_text} 在位置: {next_section_pos}")
            
            section_content = content[start_pos:next_section_pos].strip()
            if section_content:
                all_curves_sections[section_name] = section_content
                print(f"找到 {section_name} 部分，长度: {len(section_content)} 字符")
                print(f"  前200字符: {section_content[:200]}")
            else:
                print(f"警告: {section_name} 部分内容为空")
    
    # 如果没有找到标准部分，使用curves_section
    if not all_curves_sections:
        all_curves_sections['default'] = curves_section
    
    # 解析所有曲线块
    curve_blocks_lines = []
    curve_section_types = []  # 记录每个曲线块属于哪个部分
    
    for section_name, section_content in all_curves_sections.items():
        lines = section_content.split('\n')
        print(f"\n解析 {section_name} section，共 {len(lines)} 行")
        
        # 找到所有curve开始行的位置
        curve_start_indices = []
        for i, line in enumerate(lines):
            if '- curve:' in line:
                curve_start_indices.append(i)
                print(f"  找到curve在第 {i+1} 行: {line[:80]}")
        
        print(f"  共找到 {len(curve_start_indices)} 个curve")
        
        # 为每个curve提取完整内容
        for idx, curve_start in enumerate(curve_start_indices):
            # 确定当前curve的结束位置（下一个curve的开始，或section结束）
            if idx + 1 < len(curve_start_indices):
                curve_end = curve_start_indices[idx + 1]
            else:
                curve_end = len(lines)
            
            # 提取这个curve的所有行
            curve_lines = lines[curve_start:curve_end]
            curve_content = '\n'.join(curve_lines)
            
            print(f"  Curve {idx+1}: 行 {curve_start+1} 到 {curve_end}, 共 {len(curve_lines)} 行, {len(curve_content)} 字符")
            if curve_content.strip():
                curve_blocks_lines.append(curve_content)
                curve_section_types.append(section_name)
                print(f"    前100字符: {curve_content[:100]}")
            else:
                print(f"    警告: Curve {idx+1} 内容为空")
    
    print(f"逐行解析找到 {len(curve_blocks_lines)} 个curve块")
    if curve_blocks_lines:
        first_curve_full = curve_blocks_lines[0]
        print(f"\n第一个完整curve块（长度: {len(first_curve_full)} 字符）:")
        print(first_curve_full[:10000])  # 显示前10000字符
        
        # 查找所有可能的键
        all_keys = re.findall(r'^\s+(\w+):', first_curve_full, re.MULTILINE)
        print(f"\n曲线块中的所有键: {all_keys}")
        
        # 查找数字数组（可能是压缩的关键帧数据）
        array_matches = re.findall(r'(\w+):\s*\[(.*?)\]', first_curve_full, re.MULTILINE | re.DOTALL)
        if array_matches:
            print(f"\n找到 {len(array_matches)} 个数组:")
            for key, array_content in array_matches[:10]:
                array_values = [s.strip() for s in array_content.split(',') if s.strip()]
                print(f"  {key}: {len(array_values)} 个值（前20个）: {array_values[:20]}")
        
        # 查找所有包含数字的行
        number_lines = [line for line in first_curve_full.split('\n') if re.search(r'[-+]?\d+\.?\d*', line)]
        print(f"\n包含数字的行数: {len(number_lines)}")
        if number_lines:
            print(f"前20行包含数字的行:")
            for line in number_lines[:20]:
                print(f"  {line[:150]}")
        # 查找这个curve块中的所有键
        curve_keys = re.findall(r'^\s+(\w+):', first_curve_full, re.MULTILINE)
        print(f"\n曲线块中的键: {set(curve_keys)}")
        
        # 查找所有数字行（可能是压缩的数据）
        number_lines = [line for line in first_curve_full.split('\n') if re.match(r'^\s+-?\d+\.?\d*', line)]
        if number_lines:
            print(f"\n找到 {len(number_lines)} 行数字数据（前20行）:")
            for line in number_lines[:20]:
                print(f"  {line[:100]}")
        
        # 查找可能的关键帧数据格式
        # 查找包含time的行
        time_lines = [line for line in first_curve_full.split('\n') if 'time' in line.lower()]
        if time_lines:
            print(f"\n找到 {len(time_lines)} 行包含'time'（前10行）:")
            for line in time_lines[:10]:
                print(f"  {line[:150]}")
    else:
        print("警告: 无法找到curve块，查看曲线部分开头:")
        print(curves_section[:1000])
    
    # 尝试多种曲线匹配模式
    curve_patterns = [
        # Unity新格式 - 使用path和attribute ID（小写）
        (r'-\s+curve:\s*\n'
         r'(\s+)path:\s*(\d+)\s*\n'
         r'\1attribute:\s*(\d+)\s*\n'
         r'(.*?)(?=\n\s+-|\n\s+[A-Z]\w+:|$)', "新格式-数字路径"),
        
        # Unity新格式变体 - path和attribute可能在不同位置
        (r'-\s+curve:\s*\n'
         r'(\s+)attribute:\s*(\d+)\s*\n'
         r'\1path:\s*(\d+)\s*\n'
         r'(.*?)(?=\n\s+-|\n\s+[A-Z]\w+:|$)', "新格式-属性在前"),
        
        # 可能只有curve:，后面直接是数据（匹配到下一个curve或顶级键）
        (r'-\s+curve:\s*\n'
         r'(.*?)(?=\n\s{2,4}-|\n\s+[A-Z]\w+:|$)', "只有curve"),
        
        # 标准格式 - curve: 后跟 m_Path 和 m_Attribute
        (r'-\s+curve:\s*\n'
         r'(\s+)m_Path:\s+(.+?)\s*\n'
         r'\1m_Attribute:\s+(.+?)\s*\n'
         r'(\1m_Curve:.*?(?=\n\s+-|\n\s+\w+:|$))', "标准格式"),
        
        # 简化格式 - 可能没有curve:前缀
        (r'(\s+)m_Path:\s+(.+?)\s*\n'
         r'\1m_Attribute:\s+(.+?)\s*\n'
         r'(\1m_Curve:.*?(?=\n\s+\w+:|$))', "简化格式"),
        
        # 直接查找m_Curve块
        (r'm_Path:\s+(.+?)\s*\n'
         r'.*?m_Attribute:\s+(.+?)\s*\n'
         r'(.*?m_Curve:.*?m_Keys:.*?(?=\n\s+\w+:|$))', "直接匹配"),
    ]
    
    # 如果逐行解析成功，使用逐行解析的结果
    if curve_blocks_lines:
        print(f"\n使用逐行解析的结果，共 {len(curve_blocks_lines)} 个curve块")
        # 将逐行解析的结果转换为可处理的格式
        curve_blocks_parsed = []
        for idx, curve_content in enumerate(curve_blocks_lines):
            # 创建一个模拟的match对象，包含section类型信息
            class FakeMatch:
                def __init__(self, content, section_type):
                    self.content = content
                    self.section_type = section_type
                    self.groups_result = (content,)
                def group(self, n):
                    return self.groups_result[n-1] if n <= len(self.groups_result) else None
                def groups(self):
                    return self.groups_result
            
            section_type = curve_section_types[idx] if idx < len(curve_section_types) else 'default'
            curve_blocks_parsed.append((FakeMatch(curve_content, section_type), idx))
        
        curve_blocks = [match for match, _ in curve_blocks_parsed]
        used_pattern = "逐行解析"
    else:
        # 使用正则表达式匹配
        curve_blocks = None
        used_pattern = None
        
        for pattern, pattern_name in curve_patterns:
            curve_blocks = list(re.finditer(pattern, curves_section, re.MULTILINE | re.DOTALL))
            if curve_blocks:
                print(f"使用匹配模式: {pattern_name}, 找到 {len(curve_blocks)} 个曲线块")
                used_pattern = pattern_name
                break
    
    if not curve_blocks:
        print("尝试查找所有包含m_Keys的部分...")
        # 最后尝试：查找所有包含m_Keys的块
        keys_blocks = re.finditer(r'(m_Path:.*?m_Keys:.*?)(?=\n\s+\w+:|$)', curves_section, re.MULTILINE | re.DOTALL)
        keys_list = list(keys_blocks)
        if keys_list:
            print(f"找到 {len(keys_list)} 个包含m_Keys的块")
            # 手动解析这些块
            for keys_block in keys_list:
                block_content = keys_block.group(1)
                path_match = re.search(r'm_Path:\s+(.+?)(?:\s*\n|$)', block_content)
                attr_match = re.search(r'm_Attribute:\s+(.+?)(?:\s*\n|$)', block_content)
                if path_match and attr_match:
                    print(f"  找到路径: {path_match.group(1)}, 属性: {attr_match.group(1)}")
        else:
            print("错误: 无法找到任何曲线数据")
            # 输出文件的关键部分用于调试
            print("\n=== 调试信息 ===")
            # 查找包含m_EditorCurves或类似关键字的行
            important_lines = []
            for i, line in enumerate(content.split('\n')):
                if any(keyword in line for keyword in ['m_EditorCurves', 'm_ClipBindingConstant', 'm_Path', 'm_Attribute', 'm_Keys', 'curve']):
                    important_lines.append(f"行{i+1}: {line[:100]}")
                    if len(important_lines) >= 20:
                        break
            print("关键行示例:")
            for line in important_lines:
                print(f"  {line}")
            print("================")
            return data
    
    if not curve_blocks:
        return data
    
    curve_count = 0
    for curve_match in curve_blocks:
        curve_count += 1
        
        # 初始化变量
        section_type = 'default'
        base_attribute = 'm_Unknown'
        path = None
        attribute = None
        curve_content = None
        
        # 根据使用的模式提取数据
        try:
            if used_pattern == "新格式-数字路径":
                indent = curve_match.group(1)
                path_id = curve_match.group(2)  # 这是路径ID，需要从绑定中查找
                attr_id = curve_match.group(3)  # 这是属性ID
                curve_content = curve_match.group(4)
                # 对于新格式，路径和属性是ID，需要从m_ClipBindingConstant中查找
                path = f"Path_{path_id}"
                attribute = f"Attr_{attr_id}"
                print(f"  新格式曲线: 路径ID={path_id}, 属性ID={attr_id}")
            elif used_pattern == "新格式-属性在前":
                indent = curve_match.group(1)
                attr_id = curve_match.group(2)  # 这是属性ID
                path_id = curve_match.group(3)  # 这是路径ID
                curve_content = curve_match.group(4)
                path = f"Path_{path_id}"
                attribute = f"Attr_{attr_id}"
                print(f"  新格式曲线（属性在前）: 路径ID={path_id}, 属性ID={attr_id}")
            elif used_pattern == "只有curve" or used_pattern == "逐行解析":
                # 这个模式只有curve内容，需要从内容中解析path和attribute
                if used_pattern == "逐行解析":
                    curve_content = curve_match.content
                    section_type = getattr(curve_match, 'section_type', 'default')
                else:
                    curve_content = curve_match.group(1)
                    section_type = 'default'
                indent = ""
                
                print(f"  曲线块内容长度: {len(curve_content)} 字符")
                if len(curve_content) > 500:
                    print(f"  曲线块内容（前1000字符）: {curve_content[:1000]}")
                    print(f"  曲线块内容（后500字符）: {curve_content[-500:]}")
                else:
                    print(f"  曲线块完整内容: {curve_content}")
                
                # 从curve内容查找path（路径通常在曲线块末尾，但也可能在开头）
                # 先尝试在末尾查找（更常见的位置）
                path_match = re.search(r'path:\s*(.+?)(?:\s*\n|$)', curve_content, re.MULTILINE)
                if path_match:
                    # 检查是否在末尾（最后几行）
                    path_line_num = curve_content[:path_match.start()].count('\n')
                    total_lines = curve_content.count('\n')
                    # 如果path不在最后5行，可能不是这个curve的path，继续查找
                    if total_lines - path_line_num > 5:
                        path_match = None
                
                # 如果没找到，尝试更宽松的匹配
                if not path_match:
                    path_match = re.search(r'^\s+path:\s*(.+?)(?:\s*\n|$)', curve_content, re.MULTILINE)
                
                # 根据section类型推断属性类型
                if section_type == 'm_EulerCurves':
                    base_attribute = 'm_LocalRotation'
                elif section_type == 'm_ScaleCurves':
                    base_attribute = 'm_LocalScale'
                elif section_type == 'm_PositionCurves':
                    base_attribute = 'm_LocalPosition'
                else:
                    base_attribute = 'm_Unknown'
                
                if path_match:
                    path = path_match.group(1).strip().strip('"\'')
                    # 清理路径中的特殊字符（如下划线占位符）
                    # Unity有时使用下划线作为占位符，我们需要保留实际路径部分
                    print(f"  从curve内容解析路径: {path}")
                else:
                    # 从curve内容中查找path和attribute（可能是数字ID）
                    path_match_id = re.search(r'^\s+path:\s*(\d+)', curve_content, re.MULTILINE)
                    attr_match_id = re.search(r'^\s+attribute:\s*(\d+)', curve_content, re.MULTILINE)
                    
                    if path_match_id and attr_match_id:
                        path_id = path_match_id.group(1)
                        attr_id = attr_match_id.group(1)
                        path = f"Path_{path_id}"
                        attribute = f"Attr_{attr_id}"
                        print(f"  从curve内容解析: 路径ID={path_id}, 属性ID={attr_id}")
                    else:
                        # 如果找不到，尝试查找其他格式
                        path_match2 = re.search(r'm_Path[:\s]+(.+?)(?:\s*\n|$)', curve_content, re.MULTILINE)
                        attr_match2 = re.search(r'm_Attribute[:\s]+(.+?)(?:\s*\n|$)', curve_content, re.MULTILINE)
                        if path_match2 and attr_match2:
                            path = path_match2.group(1).strip().strip('"\'')
                            attribute = attr_match2.group(1).strip().strip('"\'')
                            print(f"  从curve内容解析(旧格式): 路径={path}, 属性={attribute}")
                        else:
                            # 如果仍然找不到路径，检查曲线块的最后几行
                            lines = curve_content.split('\n')
                            for line in reversed(lines[-10:]):  # 检查最后10行
                                if 'path:' in line.lower():
                                    path_match3 = re.search(r'path:\s*(.+?)(?:\s*$)', line, re.IGNORECASE)
                                    if path_match3:
                                        path = path_match3.group(1).strip().strip('"\'')
                                        print(f"  从曲线块末尾解析路径: {path}")
                                        break
                            
                            if path is None:
                                # 使用索引作为临时标识
                                path = f"Curve_{curve_count}"
                                print(f"  警告: 无法解析路径，使用临时标识: {path}")
                                print(f"  曲线块最后20行内容:")
                                for line in lines[-20:]:
                                    print(f"    {line}")
                # 注意：这里不设置attribute，因为向量值需要拆分为x, y, z三个曲线
            elif used_pattern == "标准格式":
                indent = curve_match.group(1)
                path = curve_match.group(2).strip().strip('"\'')
                attribute = curve_match.group(3).strip().strip('"\'')
                curve_content = curve_match.group(4)
            elif used_pattern == "简化格式":
                indent = curve_match.group(1)
                path = curve_match.group(2).strip().strip('"\'')
                attribute = curve_match.group(3).strip().strip('"\'')
                curve_content = curve_match.group(4)
            else:  # 直接匹配
                path = curve_match.group(1).strip().strip('"\'')
                attribute = curve_match.group(2).strip().strip('"\'')
                curve_content = curve_match.group(3)
                indent = ""
        except IndexError as e:
            print(f"  错误: 模式 '{used_pattern}' 的group访问失败: {e}")
            print(f"  curve_match.groups(): {curve_match.groups()}")
            continue
        
        print(f"  曲线 {curve_count}: 路径={path}, 属性={attribute if 'attribute' in locals() else '待解析'}")
        
        # 解析关键帧 - 更灵活的匹配
        keyframes = []
        
        # 新格式可能使用不同的关键帧结构
        # 查找各种可能的关键帧格式
        keys_match = None
        
        # 尝试查找m_Curve（Unity新格式）
        # m_Curve后面跟着关键帧列表，直到遇到path:或其他顶级键
        print(f"    查找m_Curve，曲线内容长度: {len(curve_content)} 字符")
        if 'm_Curve:' in curve_content:
            print(f"    找到m_Curve:关键字")
            keys_match = re.search(r'm_Curve:\s*\n(.*?)(?=\n\s+path:|$)', curve_content, re.MULTILINE | re.DOTALL)
            if not keys_match:
                # 尝试匹配到下一个顶级键（m_开头的键，但不是m_Curve的子项）
                keys_match = re.search(r'm_Curve:\s*\n(.*?)(?=\n\s+m_[A-Z]\w+:|$)', curve_content, re.MULTILINE | re.DOTALL)
            if keys_match:
                print(f"    找到m_Curve块，长度: {len(keys_match.group(1))} 字符")
                print(f"    m_Curve内容前500字符: {keys_match.group(1)[:500]}")
            else:
                print(f"    警告: 找到m_Curve:但无法提取内容")
        else:
            print(f"    未找到m_Curve:关键字")
        
        # 如果没找到m_Curve，尝试查找m_Keys
        if not keys_match:
            if 'm_Keys:' in curve_content:
                print(f"    找到m_Keys:关键字")
                keys_match = re.search(r'm_Keys:\s*\n(.*?)(?=\n\s+path:|$)', curve_content, re.MULTILINE | re.DOTALL)
                if not keys_match:
                    keys_match = re.search(r'm_Keys:\s*\n(.*?)(?=\n\s+m_[A-Z]\w+:|$)', curve_content, re.MULTILINE | re.DOTALL)
                if keys_match:
                    print(f"    找到m_Keys块，长度: {len(keys_match.group(1))} 字符")
        
        # 如果没找到m_Keys，尝试查找其他格式
        if not keys_match:
            # 尝试查找直接的关键帧数组
            keys_match = re.search(r'(?:keys|keyframes|data):\s*\n(.*?)(?=\n\s+\w+:|$)', curve_content, re.MULTILINE | re.DOTALL)
        
        # 如果还是没找到，尝试查找压缩格式的数据
        if not keys_match:
            # Unity新格式可能使用压缩的数组格式
            # 查找可能的时间数组和值数组
            time_array_match = re.search(r'(?:time|times|m_Time):\s*\[(.*?)\]', curve_content, re.MULTILINE | re.DOTALL)
            value_array_match = re.search(r'(?:value|values|m_Value|m_Values):\s*\[(.*?)\]', curve_content, re.MULTILINE | re.DOTALL)
            
            if time_array_match and value_array_match:
                time_strs = [s.strip() for s in time_array_match.group(1).split(',') if s.strip()]
                value_strs = [s.strip() for s in value_array_match.group(1).split(',') if s.strip()]
                print(f"    找到压缩数组: {len(time_strs)} 个时间, {len(value_strs)} 个值")
                
                # 匹配时间和值
                min_len = min(len(time_strs), len(value_strs))
                for i in range(min_len):
                    try:
                        keyframe = {
                            'time': float(time_strs[i]),
                            'value': float(value_strs[i]),
                            'inSlope': 0.0,
                            'outSlope': 0.0,
                            'inWeight': 0.333,
                            'outWeight': 0.333,
                            'weightedMode': 0
                        }
                        keyframes.append(keyframe)
                    except:
                        pass
                
                if keyframes:
                    print(f"    从压缩数组解析出 {len(keyframes)} 个关键帧")
            else:
                # 查找所有包含time和value的行（可能在不同行）
                time_matches = re.finditer(r'time:\s+([\d.eE+-]+)', curve_content, re.MULTILINE)
                for time_match in time_matches:
                    time_str = time_match.group(1)
                    # 在time行附近查找value
                    start_pos = time_match.start()
                    value_match = re.search(r'value:\s+([\d.eE+-]+)', curve_content[start_pos:start_pos+200])
                    if value_match:
                        value_str = value_match.group(1)
                        try:
                            keyframe = {
                                'time': float(time_str),
                                'value': float(value_str),
                                'inSlope': 0.0,
                                'outSlope': 0.0,
                                'inWeight': 0.333,
                                'outWeight': 0.333,
                                'weightedMode': 0
                            }
                            keyframes.append(keyframe)
                        except:
                            pass
                
                if keyframes:
                    print(f"    找到 {len(keyframes)} 个关键帧（直接匹配time/value）")
        
        if keys_match:
            keys_content = keys_match.group(1)
            
            # 首先尝试匹配向量格式的关键帧（value: {x: 0, y: 0, z: 0}）
            # 使用更宽松的匹配，允许不同的空格和格式
            vector_key_matches = re.finditer(
                r'-\s+serializedVersion:\s*\d+\s*\n'
                r'\s+time:\s+([\d.eE+-inf]+)\s*\n'
                r'\s+value:\s*\{x:\s*([\d.eE+-inf]+)\s*,\s*y:\s*([\d.eE+-inf]+)\s*,\s*z:\s*([\d.eE+-inf]+)\s*\}\s*\n'
                r'(\s+inSlope:\s*\{x:\s*([\d.eE+-inf]+)\s*,\s*y:\s*([\d.eE+-inf]+)\s*,\s*z:\s*([\d.eE+-inf]+)\s*\}\s*\n)?'
                r'(\s+outSlope:\s*\{x:\s*([\d.eE+-inf]+)\s*,\s*y:\s*([\d.eE+-inf]+)\s*,\s*z:\s*([\d.eE+-inf]+)\s*\}\s*\n)?',
                keys_content,
                re.MULTILINE
            )
            
            vector_keyframes = list(vector_key_matches)
            
            if vector_keyframes:
                # 向量格式：拆分为x, y, z三个曲线
                print(f"    找到向量格式关键帧，共 {len(vector_keyframes)} 个")
                
                # 根据section类型确定属性名
                if section_type == 'm_EulerCurves':
                    attr_names = ['m_LocalRotation.x', 'm_LocalRotation.y', 'm_LocalRotation.z']
                elif section_type == 'm_ScaleCurves':
                    attr_names = ['m_LocalScale.x', 'm_LocalScale.y', 'm_LocalScale.z']
                elif section_type == 'm_PositionCurves':
                    attr_names = ['m_LocalPosition.x', 'm_LocalPosition.y', 'm_LocalPosition.z']
                else:
                    attr_names = [f'{base_attribute}.x', f'{base_attribute}.y', f'{base_attribute}.z']
                
                # 为每个分量创建关键帧列表
                component_keyframes = [[], [], []]  # x, y, z
                
                for key_match in vector_keyframes:
                    time = float(key_match.group(1))
                    values = [float(key_match.group(2)), float(key_match.group(3)), float(key_match.group(4))]
                    
                    # 解析inSlope和outSlope（如果有）
                    in_slopes = [0.0, 0.0, 0.0]
                    out_slopes = [0.0, 0.0, 0.0]
                    
                    if key_match.group(5):  # 有inSlope
                        # 处理无穷大值
                        for i in range(3):
                            slope_str = (key_match.group(6+i) or '').strip()
                            if slope_str and ('inf' in slope_str.lower() or slope_str.lower() == 'infinity'):
                                in_slopes[i] = float('inf') if '-' not in slope_str else float('-inf')
                            elif slope_str:
                                try:
                                    in_slopes[i] = float(slope_str)
                                except:
                                    in_slopes[i] = 0.0
                    
                    if key_match.group(9):  # 有outSlope
                        # 处理无穷大值
                        for i in range(3):
                            slope_str = (key_match.group(10+i) or '').strip()
                            if slope_str and ('inf' in slope_str.lower() or slope_str.lower() == 'infinity'):
                                out_slopes[i] = float('inf') if '-' not in slope_str else float('-inf')
                            elif slope_str:
                                try:
                                    out_slopes[i] = float(slope_str)
                                except:
                                    out_slopes[i] = 0.0
                    
                    # 为每个分量创建关键帧
                    for i in range(3):
                        component_keyframes[i].append({
                            'time': time,
                            'value': values[i],
                            'inSlope': in_slopes[i],
                            'outSlope': out_slopes[i],
                            'inWeight': 0.333,
                            'outWeight': 0.333,
                            'weightedMode': 0
                        })
                
                # 确保path已设置
                if path is None:
                    path = f"Curve_{curve_count}"
                    print(f"    警告: 路径未设置，使用临时标识: {path}")
                
                # 验证路径一致性：确保所有分量使用相同的路径
                path_normalized = path.strip() if path else None
                if not path_normalized:
                    path_normalized = f"Curve_{curve_count}"
                    print(f"    警告: 路径为空，使用临时标识: {path_normalized}")
                
                # 添加三个分量的曲线，确保使用相同的路径
                for i, attr_name in enumerate(attr_names):
                    if component_keyframes[i]:
                        data['curves'].append({
                            'path': path_normalized,  # 使用标准化的路径
                            'attribute': attr_name,
                            'keyframes': component_keyframes[i]
                        })
                        print(f"    成功添加曲线 路径={path_normalized}, 属性={attr_name}, 共 {len(component_keyframes[i])} 个关键帧")
            else:
                # 标量格式：匹配每个关键帧 - 更宽松的模式
                key_matches = re.finditer(
                    r'-\s+(?:serializedVersion:\s*\d+\s*\n\s+)?time:\s+([\d.eE+-inf]+)\s*\n'
                    r'\s+value:\s+([\d.eE+-inf]+)\s*\n'
                    r'(\s+inSlope:\s+([\d.eE+-inf]+)\s*\n)?'
                    r'(\s+outSlope:\s+([\d.eE+-inf]+)\s*\n)?'
                    r'(\s+inWeight:\s+([\d.eE+-inf]+)\s*\n)?'
                    r'(\s+outWeight:\s+([\d.eE+-inf]+)\s*\n)?'
                    r'(\s+weightedMode:\s+(\d+)\s*\n)?',
                    keys_content,
                    re.MULTILINE
                )
                
                keyframe_count = 0
                for key_match in key_matches:
                    keyframe_count += 1
                    keyframe = {
                        'time': float(key_match.group(1)),
                        'value': float(key_match.group(2)),
                        'inSlope': float(key_match.group(4)) if key_match.group(4) else 0.0,
                        'outSlope': float(key_match.group(6)) if key_match.group(6) else 0.0,
                        'inWeight': float(key_match.group(8)) if key_match.group(8) else 0.333,
                        'outWeight': float(key_match.group(10)) if key_match.group(10) else 0.333,
                        'weightedMode': int(key_match.group(12)) if key_match.group(12) else 0
                    }
                    
                    # 处理无穷大值
                    in_slope_str = str(key_match.group(4) or '')
                    out_slope_str = str(key_match.group(6) or '')
                    
                    if 'inf' in in_slope_str.lower():
                        keyframe['inSlope'] = float('inf') if '-' not in in_slope_str else float('-inf')
                    if 'inf' in out_slope_str.lower():
                        keyframe['outSlope'] = float('inf') if '-' not in out_slope_str else float('-inf')
                    
                    keyframes.append(keyframe)
                
                if keyframes:
                    # 确定属性名
                    if attribute is None:
                        if section_type == 'm_EulerCurves':
                            attribute = 'm_LocalRotation'
                        elif section_type == 'm_ScaleCurves':
                            attribute = 'm_LocalScale'
                        elif section_type == 'm_PositionCurves':
                            attribute = 'm_LocalPosition'
                        else:
                            attribute = base_attribute if base_attribute != 'm_Unknown' else 'm_Unknown'
                    
                    # 确保path已设置并标准化
                    path_normalized = path.strip() if path else None
                    if not path_normalized:
                        path_normalized = f"Curve_{curve_count}"
                        print(f"    警告: 路径未设置，使用临时标识: {path_normalized}")
                    
                    data['curves'].append({
                        'path': path_normalized,  # 使用标准化的路径
                        'attribute': attribute,
                        'keyframes': keyframes
                    })
                    print(f"    找到 {keyframe_count} 个关键帧，成功添加曲线 路径={path_normalized}, 属性={attribute}")
        else:
            print(f"    警告: 未找到m_Curve或m_Keys块")
    
    # 如果长度为0，从所有关键帧中计算最大时间
    if data['length'] == 0:
        max_time = 0
        for curve in data['curves']:
            for kf in curve.get('keyframes', []):
                max_time = max(max_time, kf.get('time', 0))
        if max_time > 0:
            data['length'] = max_time
            print(f"从关键帧计算动画长度: {max_time} 秒")
    
    print(f"解析完成: 共找到 {len(data['curves'])} 条曲线")
    return data

def map_unity_to_blender_property(attribute):
    """
    将Unity属性名映射到Blender属性名
    """
    attribute_lower = attribute.lower()
    
    # Transform属性映射
    if 'localposition' in attribute_lower or 'position' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'location', 0
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'location', 1
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'location', 2
    
    if 'localrotation' in attribute_lower or 'rotation' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'rotation_euler', 0
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'rotation_euler', 1
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'rotation_euler', 2
        elif '.w' in attribute_lower or attribute_lower.endswith('w'):
            return 'rotation_quaternion', 3
    
    if 'localscale' in attribute_lower or 'scale' in attribute_lower:
        if '.x' in attribute_lower or attribute_lower.endswith('x'):
            return 'scale', 0
        elif '.y' in attribute_lower or attribute_lower.endswith('y'):
            return 'scale', 1
        elif '.z' in attribute_lower or attribute_lower.endswith('z'):
            return 'scale', 2
    
    # 其他属性，尝试直接使用
    # 移除m_前缀和数组索引
    prop_name = attribute
    if prop_name.startswith('m_'):
        prop_name = prop_name[2:]
    
    # 提取数组索引
    array_match = re.search(r'\[(\d+)\]', prop_name)
    index = int(array_match.group(1)) if array_match else 0
    prop_name = re.sub(r'\[\d+\]', '', prop_name)
    
    return prop_name, index

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
    
    # 调试信息
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
            print(f"跳过空关键帧: {path}/{attribute}")
            continue
        
        # 映射到Blender属性
        data_path, index = map_unity_to_blender_property(attribute)
        curve_key = (data_path, index)
        
        print(f"处理属性: {attribute} -> {data_path}[{index}], 关键帧数: {len(keyframes)}")
        
        if curve_key in processed_curves:
            print(f"跳过已处理的曲线: {data_path}[{index}]")
            continue
        
        # 按时间排序关键帧
        keyframes.sort(key=lambda kf: kf.get('time', 0))
        
        # 检查是否已存在相同的F-Curve
        existing_fcurve = None
        for fc in action.fcurves:
            if fc.data_path == data_path and fc.array_index == index:
                existing_fcurve = fc
                break
        
        if existing_fcurve:
            action.fcurves.remove(existing_fcurve)
        
        # 创建F-Curve
        fcurve = action.fcurves.new(data_path=data_path, index=index)
        fcurve.keyframe_points.add(len(keyframes))
        
        # 设置关键帧
        for i, kf_data in enumerate(keyframes):
            time = kf_data.get('time', 0)
            value = kf_data.get('value', 0)
            
            # 转换时间到帧数
            frame = time * frame_rate
            
            kp = fcurve.keyframe_points[i]
            kp.co = (frame, value)
            
            # 检查是否为阶跃函数（无穷大切线）
            in_slope = kf_data.get('inSlope', 0)
            out_slope = kf_data.get('outSlope', 0)
            
            is_step_in = float('inf') == abs(in_slope) if isinstance(in_slope, float) else False
            is_step_out = float('inf') == abs(out_slope) if isinstance(out_slope, float) else False
            
            # 根据是否为阶跃函数设置插值类型
            if is_step_in or is_step_out:
                # 阶跃函数：使用常量插值
                kp.interpolation = 'CONSTANT'
                kp.handle_left_type = 'AUTO'
                kp.handle_right_type = 'AUTO'
            else:
                # 正常曲线：使用自动插值
                kp.handle_left_type = 'AUTO'
                kp.handle_right_type = 'AUTO'
                
                # 如果有有效的切线信息，设置插值
                if in_slope is not None and out_slope is not None:
                    # 计算控制点位置
                    prev_frame = frame - 1.0 / frame_rate if i > 0 else frame
                    next_frame = frame + 1.0 / frame_rate if i < len(keyframes) - 1 else frame
                    
                    # 设置切线（Unity的slope是时间导数，需要转换）
                    if not is_step_in and not is_step_out:
                        kp.handle_left = (prev_frame, value - in_slope / frame_rate)
                        kp.handle_right = (next_frame, value + out_slope / frame_rate)
        
        # 更新F-Curve
        fcurve.update()
        imported_count += 1
        processed_curves.add(curve_key)
        print(f"  成功创建F-Curve: {data_path}[{index}], 关键帧数: {len(keyframes)}")
    
    # 设置动作范围
    if action.fcurves:
        # 确保长度大于0
        if length <= 0:
            # 从所有关键帧中找最大时间
            max_frame = 0
            for fcurve in action.fcurves:
                if fcurve.keyframe_points:
                    max_frame = max(max_frame, max([kp.co[0] for kp in fcurve.keyframe_points]))
            if max_frame > 0:
                length = max_frame / frame_rate
                print(f"从F-Curve计算动画长度: {length} 秒 ({max_frame} 帧)")
        
        end_frame = length * frame_rate if length > 0 else 1
        action.frame_range = (0, end_frame)
        print(f"设置动作范围: 0 - {end_frame} 帧 (长度: {length} 秒)")
    
    # 将动作分配给选中的对象
    if bpy.context.selected_objects:
        obj = bpy.context.selected_objects[0]
        if obj.animation_data is None:
            obj.animation_data_create()
        obj.animation_data.action = action
        print(f"动画 '{action_name}' 已分配给对象 '{obj.name}'")
    else:
        print(f"动画 '{action_name}' 已创建。请手动将其分配给对象。")
    
    print(f"成功导入动画: {animation_name}")
    print(f"时长: {length} 秒, 帧率: {frame_rate} fps")
    print(f"导入曲线数: {imported_count}")
    
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


def register():
    """注册操作符和属性"""
    bpy.utils.register_class(ImportAnimationAnimOperator)
    
    # 注册场景属性，用于保存上次导入的路径
    bpy.types.Scene.animation_anim_import_path = bpy.props.StringProperty(
        name="动画.anim导入路径",
        description="上次导入.anim文件的路径",
        default=""
    )


def unregister():
    """注销操作符和属性"""
    bpy.utils.unregister_class(ImportAnimationAnimOperator)
    
    # 注销场景属性
    if hasattr(bpy.types.Scene, 'animation_anim_import_path'):
        del bpy.types.Scene.animation_anim_import_path


if __name__ == "__main__":
    register()

