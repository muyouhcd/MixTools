"""
合成节点库管理工具
功能：
1. 将选中的后处理节点保存为JSON文件（支持群组节点的递归保存）
2. 列出目录中的所有节点JSON文件
3. 从JSON文件加载节点并添加到当前节点面板（追加模式，支持群组节点的递归加载）
"""

import bpy
import json
import os
from typing import Dict, List, Any, Optional, Set

def get_addon_directory():
    """获取插件安装目录（MixTools目录）"""
    file_path = os.path.normpath(os.path.dirname(__file__))
    # 如果文件在MixTools文件夹中，返回MixTools目录
    if os.path.basename(file_path) == "MixTools":
        return file_path
    # 否则查找MixTools目录
    while os.path.dirname(file_path) != file_path:
        if os.path.basename(file_path) == "MixTools":
            return file_path
        file_path = os.path.dirname(file_path)
    return os.path.dirname(os.path.normpath(os.path.dirname(__file__)))

def get_compositor_nodes_json_path():
    """
    获取合成节点JSON文件的存储目录（模仿AutoRig的RigJson结构）
    路径结构：addons/MixTools/NodeJson
    这样可以确保所有工程都能访问相同的节点库
    """
    # 获取当前文件的绝对路径并规范化
    file_path = os.path.normpath(os.path.dirname(__file__))
    
    # 逆向查找直到找到 "addons" 文件夹
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    
    # 确认已经找到 "addons" 文件夹
    if os.path.basename(file_path) == "addons":
        # 添加相对路径到 MixTools\NodeJson（与RigJson并列）
        target_path = os.path.join(file_path, "MixTools", "NodeJson")
        
        # 确保该路径存在（如果不存在则创建）
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path, exist_ok=True)
                print(f"✅ 已创建NodeJson文件夹: {target_path}")
            except Exception as e:
                print(f"警告: 无法创建NodeJson文件夹: {e}")
                return ''
        
        return target_path
    
    # 如果找不到addons目录，回退到使用MixTools目录
    addon_dir = get_addon_directory()
    if addon_dir and os.path.exists(addon_dir):
        node_json_dir = os.path.join(addon_dir, "NodeJson")
        if not os.path.exists(node_json_dir):
            try:
                os.makedirs(node_json_dir, exist_ok=True)
                print(f"✅ 已创建NodeJson文件夹: {node_json_dir}")
            except Exception as e:
                print(f"警告: 无法创建NodeJson文件夹: {e}")
                return ''
        return node_json_dir
    
    # 最后的回退：使用用户主目录
    node_json_dir = os.path.join(os.path.expanduser("~"), "NodeJson")
    if not os.path.exists(node_json_dir):
        try:
            os.makedirs(node_json_dir, exist_ok=True)
            print(f"✅ 已创建NodeJson文件夹: {node_json_dir}")
        except Exception as e:
            print(f"警告: 无法创建NodeJson文件夹: {e}")
            return ''
    return node_json_dir

def ensure_node_json_directories():
    """确保NodeJson文件夹存在（使用与RigJson相同的结构：addons/MixTools/NodeJson）"""
    directories_created = []
    # 使用与get_compositor_nodes_json_path()相同的逻辑
    file_path = os.path.normpath(os.path.dirname(__file__))
    # 逆向查找直到找到 "addons" 文件夹
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    # 确认已经找到 "addons" 文件夹
    if os.path.basename(file_path) == "addons":
        # 添加相对路径到 MixTools\NodeJson
        target_path = os.path.join(file_path, "MixTools", "NodeJson")
        if not os.path.exists(target_path):
            try:
                os.makedirs(target_path, exist_ok=True)
                directories_created.append(target_path)
                print(f"✅ 已创建NodeJson文件夹: {target_path}")
            except Exception as e:
                print(f"⚠️ 无法创建NodeJson文件夹: {e}")
    
    return directories_created

class CompositorNodeLibrary:
    """合成节点库管理类（合并了 CompositorNodeSerializer 的功能）"""
    
    # ============================================================================
    # 辅助方法：序列化/反序列化（从 CompositorNodeSerializer 合并）
    # ============================================================================
    
    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """序列化值，处理特殊类型"""
        if isinstance(value, (int, float, str, bool)):
            return value
        elif isinstance(value, (tuple, list)):
            return [CompositorNodeLibrary._serialize_value(v) for v in value]
        elif hasattr(value, '__iter__') and not isinstance(value, str):
            # 处理mathutils类型等
            try:
                return list(value)
            except:
                return str(value)
        else:
            return str(value)
    
    @staticmethod
    def _deserialize_value(value: Any, default_type: Any) -> Any:
        """反序列化值"""
        if isinstance(value, (int, float, str, bool)):
            return value
        elif isinstance(value, list):
            if isinstance(default_type, (tuple, list)):
                return tuple(value) if len(value) <= 4 else list(value)
            return value
        return value
    
    @staticmethod
    def _export_node_properties(node: bpy.types.Node) -> Dict[str, Any]:
        """导出节点的特有属性"""
        props = {}
        
        # 根据节点类型保存特定属性
        node_type = node.type
        
        # 图像纹理节点的图像路径
        if node_type == 'IMAGE':
            if hasattr(node, 'image') and node.image:
                props['image_path'] = bpy.path.abspath(node.image.filepath) if node.image.filepath else None
                props['image_name'] = node.image.name
        
        # Alpha over节点的混合方式
        if node_type == 'ALPHAOVER':
            if hasattr(node, 'premul'):
                props['premul'] = node.premul
        
        # 模糊节点的设置
        if node_type == 'BLUR':
            if hasattr(node, 'size_x'):
                props['size_x'] = node.size_x
            if hasattr(node, 'size_y'):
                props['size_y'] = node.size_y
            if hasattr(node, 'filter_type'):
                props['filter_type'] = node.filter_type
        
        # 色彩校正节点的设置
        if node_type == 'COLORCORRECT':
            if hasattr(node, 'gain'):
                props['gain'] = node.gain
            if hasattr(node, 'lift'):
                props['lift'] = node.lift
            if hasattr(node, 'gamma'):
                props['gamma'] = node.gamma
        
        # 输出文件节点的设置
        if node_type == 'OUTPUT_FILE':
            if hasattr(node, 'base_path'):
                props['base_path'] = node.base_path
            if hasattr(node, 'format'):
                props['format'] = node.format.file_format if hasattr(node.format, 'file_format') else None
        
        # 群组节点：保存内部节点树的数据
        if node_type == 'GROUP' and hasattr(node, 'node_tree') and node.node_tree:
            props['group_node_tree'] = CompositorNodeLibrary._export_node_tree_internal(node.node_tree)
        
        # 添加更多节点类型的属性保存...
        
        return props
    
    @staticmethod
    def _import_node_properties(node: bpy.types.Node, properties: Dict[str, Any]):
        """导入节点的特有属性"""
        node_type = node.type
        
        # 图像纹理节点的图像路径
        if node_type == 'IMAGE' and 'image_path' in properties:
            image_path = properties['image_path']
            if image_path:
                try:
                    # 尝试加载图像
                    image_name = properties.get('image_name')
                    if image_name and image_name in bpy.data.images:
                        node.image = bpy.data.images[image_name]
                    else:
                        # 尝试从路径加载
                        image = bpy.data.images.load(image_path, check_existing=True)
                        node.image = image
                except Exception as e:
                    print(f"警告: 无法加载图像 '{image_path}': {e}")
        
        # 群组节点：递归加载内部节点树
        if node_type == 'GROUP' and 'group_node_tree' in properties:
            group_data = properties['group_node_tree']
            # 获取或创建节点组（node_tree）
            if hasattr(node, 'node_tree'):
                if node.node_tree is None:
                    # 如果群组节点没有内部节点树，创建一个新的
                    group_node_tree_type = group_data.get('node_tree_type', 'COMPOSITING')
                    group_node_tree_name = group_data.get('node_tree_name', f'Group_{node.name}')
                    
                    # 创建新的节点组
                    new_group_tree = bpy.data.node_groups.new(type=group_node_tree_type, name=group_node_tree_name)
                    node.node_tree = new_group_tree
                    print(f"[DEBUG-Group] 为群组节点 '{node.name}' 创建了新的节点组: {group_node_tree_name}")
                
                # 导入内部节点树
                if node.node_tree:
                    print(f"[DEBUG-Group] 开始导入群组节点 '{node.name}' 的内部节点树...")
                    CompositorNodeLibrary._import_node_tree_internal(group_data, node.node_tree, clear_existing=True)
                    print(f"[DEBUG-Group] ✅ 群组节点 '{node.name}' 的内部节点树导入完成")
                else:
                    print(f"[DEBUG-Group] 警告: 群组节点 '{node.name}' 无法创建或获取节点组")
        
        # 设置其他节点属性
        for key, value in properties.items():
            if key in ['image_path', 'image_name', 'group_node_tree']:  # 已处理
                continue
            if hasattr(node, key):
                try:
                    setattr(node, key, value)
                except Exception as e:
                    print(f"警告: 无法设置属性 '{key}' = {value}: {e}")
    
    @staticmethod
    def _export_node_tree_internal(node_tree: bpy.types.NodeTree) -> Dict[str, Any]:
        """内部方法：导出节点树的所有节点和连接（用于群组节点）"""
        nodes_data = []
        for node in node_tree.nodes:
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': (node.location.x, node.location.y),
                'width': node.width,
                'height': node.height,
                'label': node.label if hasattr(node, 'label') else '',
                'mute': node.mute,
                'hide': node.hide,
                'use_custom_color': node.use_custom_color,
                'color': tuple(node.color) if hasattr(node, 'color') else (0.5, 0.5, 0.5),
            }
            
            inputs_data = []
            for input_socket in node.inputs:
                input_data = {
                    'name': input_socket.name,
                    'identifier': input_socket.identifier,
                }
                if hasattr(input_socket, 'default_value'):
                    try:
                        default_value = input_socket.default_value
                        serialized_value = CompositorNodeLibrary._serialize_value(default_value)
                        input_data['default_value'] = serialized_value
                    except Exception as e:
                        print(f"警告: 无法序列化输入插槽 '{input_socket.identifier}' 的默认值: {e}")
                if hasattr(input_socket, 'enabled'):
                    input_data['enabled'] = input_socket.enabled
                inputs_data.append(input_data)
            node_data['inputs'] = inputs_data
            
            # 保存节点属性（包括递归处理群组节点）
            node_data['properties'] = CompositorNodeLibrary._export_node_properties(node)
            
            nodes_data.append(node_data)
        
        links_data = []
        for link in node_tree.links:
            link_data = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.identifier,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.identifier,
            }
            links_data.append(link_data)
        
        return {
            'nodes': nodes_data,
            'links': links_data,
            'node_tree_name': node_tree.name,
            'node_tree_type': node_tree.type,
        }
    
    @staticmethod
    def _import_node_tree_internal(data: Dict[str, Any], node_tree: bpy.types.NodeTree, clear_existing: bool = True):
        """内部方法：导入节点树到指定的节点树（用于群组节点）"""
        if clear_existing:
            # 清除现有节点
            for node in list(node_tree.nodes):
                node_tree.nodes.remove(node)
            for link in list(node_tree.links):
                node_tree.links.remove(link)
        
        node_map = {}
        nodes_data = data.get('nodes', [])
        
        # 第一步：创建所有节点
        for node_data in nodes_data:
            node_type = node_data.get('type')
            original_name = node_data.get('name', '')
            
            try:
                new_node = node_tree.nodes.new(type=node_type)
                
                # 设置基本属性
                if original_name:
                    new_node.name = original_name
                if 'location' in node_data:
                    new_node.location = node_data['location']
                if 'width' in node_data:
                    new_node.width = node_data['width']
                if 'height' in node_data:
                    new_node.height = node_data['height']
                if 'label' in node_data and hasattr(new_node, 'label'):
                    new_node.label = node_data['label']
                if 'mute' in node_data:
                    new_node.mute = node_data['mute']
                if 'hide' in node_data:
                    new_node.hide = node_data['hide']
                if 'use_custom_color' in node_data:
                    new_node.use_custom_color = node_data['use_custom_color']
                if 'color' in node_data and hasattr(new_node, 'color'):
                    new_node.color = node_data['color']
                
                # 恢复节点属性（包括递归加载群组节点）
                CompositorNodeLibrary._import_node_properties(new_node, node_data.get('properties', {}))
                
                # 恢复输入插槽的值
                inputs_data = node_data.get('inputs', [])
                for input_data in inputs_data:
                    socket_identifier = input_data.get('identifier')
                    socket = None
                    for inp in new_node.inputs:
                        if inp.identifier == socket_identifier:
                            socket = inp
                            break
                    
                    if socket is None:
                        continue
                    
                    if 'default_value' in input_data:
                        try:
                            default_value = input_data['default_value']
                            if hasattr(socket, 'default_value'):
                                socket.default_value = CompositorNodeLibrary._deserialize_value(
                                    default_value, socket.default_value
                                )
                        except Exception as e:
                            print(f"警告: 无法设置输入插槽 '{socket_identifier}' 的值: {e}")
                    if 'enabled' in input_data and hasattr(socket, 'enabled'):
                        socket.enabled = input_data['enabled']
                
                node_map[original_name] = new_node
            except Exception as e:
                print(f"错误: 无法创建节点 '{original_name}' (类型: {node_type}): {e}")
                continue
        
        # 第二步：创建连接
        links_data = data.get('links', [])
        for link_data in links_data:
            from_node_name = link_data.get('from_node')
            from_socket_id = link_data.get('from_socket')
            to_node_name = link_data.get('to_node')
            to_socket_id = link_data.get('to_socket')
            
            if from_node_name not in node_map or to_node_name not in node_map:
                continue
            
            from_node = node_map[from_node_name]
            to_node = node_map[to_node_name]
            
            try:
                # 查找对应的插槽
                from_socket = None
                to_socket = None
                
                for output in from_node.outputs:
                    if output.identifier == from_socket_id:
                        from_socket = output
                        break
                
                for input_sock in to_node.inputs:
                    if input_sock.identifier == to_socket_id:
                        to_socket = input_sock
                        break
                
                if from_socket and to_socket:
                    # 检查连接是否已存在
                    link_exists = False
                    for existing_link in node_tree.links:
                        if (existing_link.from_node == from_node and 
                            existing_link.from_socket == from_socket and
                            existing_link.to_node == to_node and
                            existing_link.to_socket == to_socket):
                            link_exists = True
                            break
                    
                    if not link_exists:
                        node_tree.links.new(from_socket, to_socket)
            except Exception as e:
                print(f"警告: 无法创建连接 {from_node_name}.{from_socket_id} -> {to_node_name}.{to_socket_id}: {e}")
    
    # ============================================================================
    # 节点树获取方法
    # ============================================================================
    
    @staticmethod
    def _get_node_tree_by_type(context: bpy.types.Context, node_type: str) -> Optional[bpy.types.NodeTree]:
        """
        根据节点类型获取节点树
        
        Args:
            context: Blender上下文对象
            node_type: 节点类型（COMPOSITING/SHADER/GEOMETRY）
        
        Returns:
            节点树对象，如果未找到则返回None
        """
        # 优先检查节点编辑器
        if context.space_data and hasattr(context.space_data, 'type'):
            if context.space_data.type == 'NODE_EDITOR':
                if hasattr(context.space_data, 'node_tree') and context.space_data.node_tree:
                    if context.space_data.node_tree.type == node_type:
                        return context.space_data.node_tree
        
        if node_type == 'COMPOSITING':
            # 合成节点
            if context.scene.use_nodes and context.scene.node_tree:
                if context.scene.node_tree.type == 'COMPOSITING':
                    return context.scene.node_tree
        
        elif node_type == 'SHADER':
            # 材质节点
            if context.active_object and context.active_object.active_material:
                material = context.active_object.active_material
                if material.use_nodes and material.node_tree:
                    return material.node_tree
        
        elif node_type == 'GEOMETRY':
            # 几何节点
            if context.active_object:
                for mod in context.active_object.modifiers:
                    if mod.type == 'NODES' and mod.node_group:
                        if mod.node_group.type == 'GEOMETRY':
                            return mod.node_group
        
        return None
    
    @staticmethod
    def export_selected_nodes_by_type(context: Optional[bpy.types.Context] = None,
                                      node_type: str = 'COMPOSITING',
                                      filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        按指定类型导出选中的节点
        
        Args:
            context: Blender上下文对象
            node_type: 节点类型（COMPOSITING/SHADER/GEOMETRY）
            filepath: 保存文件的路径
        
        Returns:
            导出的数据字典
        """
        print(f"[DEBUG-Library] export_selected_nodes_by_type 开始，node_type={node_type}")
        if context is None:
            context = bpy.context
        
        print(f"[DEBUG-Library] 获取节点树...")
        node_tree = CompositorNodeLibrary._get_node_tree_by_type(context, node_type)
        
        if node_tree is None:
            node_type_names = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }
            type_name = node_type_names.get(node_type, node_type)
            print(f"[DEBUG-Library] ❌ 无法找到{type_name}节点树")
            raise ValueError(f"无法找到{type_name}节点树")
        
        print(f"[DEBUG-Library] ✅ 找到节点树: {node_tree.name}, 节点总数: {len(node_tree.nodes)}")
        
        # 获取选中的节点
        selected_nodes = [node for node in node_tree.nodes if node.select]
        print(f"[DEBUG-Library] 选中的节点数量: {len(selected_nodes)}")
        
        if not selected_nodes:
            raise ValueError(f"没有选中的节点")
        
        # 获取所有与选中节点相关的连接
        selected_node_names = {node.name for node in selected_nodes}
        relevant_links = []
        for link in node_tree.links:
            from_node_name = link.from_node.name
            to_node_name = link.to_node.name
            if from_node_name in selected_node_names and to_node_name in selected_node_names:
                relevant_links.append(link)
        
        print(f"[DEBUG-Library] 相关连接数量: {len(relevant_links)}")
        
        # 构建节点数据（复用现有逻辑）
        nodes_data = []
        for node in selected_nodes:
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': (node.location.x, node.location.y),
                'width': node.width,
                'height': node.height,
                'label': node.label if hasattr(node, 'label') else '',
                'mute': node.mute,
                'hide': node.hide,
                'use_custom_color': node.use_custom_color,
                'color': tuple(node.color) if hasattr(node, 'color') else (0.5, 0.5, 0.5),
            }
            
            inputs_data = []
            print(f"[DEBUG-Library] 处理节点 '{node.name}' (类型: {node.type}), 输入插槽数量: {len(node.inputs)}")
            for idx, input_socket in enumerate(node.inputs):
                print(f"[DEBUG-Library]   插槽 [{idx}]: name='{input_socket.name}', identifier='{input_socket.identifier}', type={type(input_socket).__name__}")
                input_data = {
                    'name': input_socket.name,
                    'identifier': input_socket.identifier,
                }
                # 只有存在 default_value 属性的插槽才保存该值
                has_default_value = hasattr(input_socket, 'default_value')
                print(f"[DEBUG-Library]      检查 default_value 属性: {has_default_value}")
                if has_default_value:
                    try:
                        print(f"[DEBUG-Library]      尝试访问 default_value...")
                        default_value = input_socket.default_value
                        print(f"[DEBUG-Library]      default_value 类型: {type(default_value)}, 值: {default_value}")
                        serialized_value = CompositorNodeLibrary._serialize_value(default_value)
                        input_data['default_value'] = serialized_value
                        print(f"[DEBUG-Library]      ✅ 成功序列化 default_value")
                    except AttributeError as e:
                        print(f"[DEBUG-Library]      ❌ AttributeError: {e}")
                        print(f"[DEBUG-Library]      错误详情: {type(e).__name__}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    except Exception as e:
                        print(f"[DEBUG-Library]      ❌ 其他错误: {type(e).__name__}: {str(e)}")
                        print(f"警告: 无法序列化输入插槽 '{input_socket.identifier}' 的默认值: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[DEBUG-Library]      插槽没有 default_value 属性，跳过")
                # enabled 属性可能不存在，需要检查
                has_enabled = hasattr(input_socket, 'enabled')
                if has_enabled:
                    input_data['enabled'] = input_socket.enabled
                    print(f"[DEBUG-Library]      设置 enabled: {input_socket.enabled}")
                inputs_data.append(input_data)
            node_data['inputs'] = inputs_data
            print(f"[DEBUG-Library] 节点 '{node.name}' 处理完成，输入插槽数据: {len(inputs_data)} 个")
            
            node_data['properties'] = CompositorNodeLibrary._export_node_properties(node)
            nodes_data.append(node_data)
        
        links_data = []
        for link in relevant_links:
            link_data = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.identifier,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.identifier,
            }
            links_data.append(link_data)
        
        data = {
            'nodes': nodes_data,
            'links': links_data,
            'export_type': 'selected_nodes',
            'node_tree_type': node_tree.type,
        }
        
        if filepath:
            CompositorNodeLibrary.save_to_json(data, filepath)
        
        return data
    
    @staticmethod
    def export_selected_nodes(context: Optional[bpy.types.Context] = None,
                              scene: Optional[bpy.types.Scene] = None, 
                              filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        导出当前选中的节点为JSON（支持合成、材质、几何节点）
        
        Args:
            context: Blender上下文对象，用于自动检测当前编辑的节点类型
            scene: Blender场景对象（如果明确知道是合成节点）
            filepath: 保存文件的路径，如果为None则使用默认路径
        
        Returns:
            导出的数据字典，如果失败则返回None
        """
        if context is None:
            context = bpy.context
        
        # 自动检测当前编辑的节点树类型
        node_tree = None
        node_tree_source = None
        
        # 优先检查节点编辑器（最准确）
        if context.space_data and hasattr(context.space_data, 'type'):
            if context.space_data.type == 'NODE_EDITOR':
                if hasattr(context.space_data, 'node_tree') and context.space_data.node_tree:
                    node_tree = context.space_data.node_tree
                    node_tree_source = 'active_editor'
        
        # 如果不在节点编辑器中，按优先级检测其他可能的节点树
        # 但优先使用场景的合成节点，因为这是最常用的
        if node_tree is None:
            # 优先检查场景合成节点（因为合成节点最常用）
            if scene is None:
                scene = context.scene
            if scene.use_nodes and scene.node_tree and scene.node_tree.type == 'COMPOSITING':
                node_tree = scene.node_tree
                node_tree_source = 'scene'
        
        # 如果还没找到，尝试从活动对象的几何节点修改器获取
        if node_tree is None and context.active_object:
            for mod in context.active_object.modifiers:
                if mod.type == 'NODES' and mod.node_group:
                    node_tree = mod.node_group
                    node_tree_source = 'geometry_nodes'
                    break
        
        # 最后才检查活动材质（因为材质节点通常需要在材质编辑器中操作）
        if node_tree is None and context.active_object:
            if context.active_object.active_material:
                material = context.active_object.active_material
                if material.use_nodes and material.node_tree:
                    node_tree = material.node_tree
                    node_tree_source = 'active_material'
        
        if node_tree is None:
            raise ValueError("无法找到节点树，请确保：\n"
                           "1. 在合成器/材质编辑器/几何节点编辑器中\n"
                           "2. 或场景已启用合成节点\n"
                           "3. 或活动对象有几何节点修改器")
        
        # 验证节点树类型
        valid_types = {'COMPOSITING', 'SHADER', 'GEOMETRY'}
        if node_tree.type not in valid_types:
            raise ValueError(f"不支持的节点树类型: {node_tree.type}，支持的类型: {valid_types}")
        
        # 获取选中的节点
        selected_nodes = [node for node in node_tree.nodes if node.select]
        
        if not selected_nodes:
            raise ValueError("没有选中的节点")
        
        # 获取所有与选中节点相关的连接（包括节点之间的连接）
        selected_node_names = {node.name for node in selected_nodes}
        relevant_links = []
        for link in node_tree.links:
            from_node_name = link.from_node.name
            to_node_name = link.to_node.name
            # 只有当连接的两端都在选中节点中时才保存
            if from_node_name in selected_node_names and to_node_name in selected_node_names:
                relevant_links.append(link)
        
        # 构建节点数据
        nodes_data = []
        for node in selected_nodes:
            node_data = {
                'name': node.name,
                'type': node.type,
                'location': (node.location.x, node.location.y),
                'width': node.width,
                'height': node.height,
                'label': node.label if hasattr(node, 'label') else '',
                'mute': node.mute,
                'hide': node.hide,
                'use_custom_color': node.use_custom_color,
                'color': tuple(node.color) if hasattr(node, 'color') else (0.5, 0.5, 0.5),
            }
            
            # 保存节点的输入插槽属性值
            inputs_data = []
            print(f"[DEBUG-Library] 处理节点 '{node.name}' (类型: {node.type}), 输入插槽数量: {len(node.inputs)}")
            for idx, input_socket in enumerate(node.inputs):
                print(f"[DEBUG-Library]   插槽 [{idx}]: name='{input_socket.name}', identifier='{input_socket.identifier}', type={type(input_socket).__name__}")
                input_data = {
                    'name': input_socket.name,
                    'identifier': input_socket.identifier,
                }
                # 只有存在 default_value 属性的插槽才保存该值
                has_default_value = hasattr(input_socket, 'default_value')
                print(f"[DEBUG-Library]      检查 default_value 属性: {has_default_value}")
                if has_default_value:
                    try:
                        print(f"[DEBUG-Library]      尝试访问 default_value...")
                        default_value = input_socket.default_value
                        print(f"[DEBUG-Library]      default_value 类型: {type(default_value)}, 值: {default_value}")
                        serialized_value = CompositorNodeLibrary._serialize_value(default_value)
                        input_data['default_value'] = serialized_value
                        print(f"[DEBUG-Library]      ✅ 成功序列化 default_value")
                    except AttributeError as e:
                        print(f"[DEBUG-Library]      ❌ AttributeError: {e}")
                        print(f"[DEBUG-Library]      错误详情: {type(e).__name__}: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    except Exception as e:
                        print(f"[DEBUG-Library]      ❌ 其他错误: {type(e).__name__}: {str(e)}")
                        print(f"警告: 无法序列化输入插槽 '{input_socket.identifier}' 的默认值: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[DEBUG-Library]      插槽没有 default_value 属性，跳过")
                # enabled 属性可能不存在，需要检查
                has_enabled = hasattr(input_socket, 'enabled')
                if has_enabled:
                    input_data['enabled'] = input_socket.enabled
                    print(f"[DEBUG-Library]      设置 enabled: {input_socket.enabled}")
                inputs_data.append(input_data)
            node_data['inputs'] = inputs_data
            print(f"[DEBUG-Library] 节点 '{node.name}' 处理完成，输入插槽数据: {len(inputs_data)} 个")
            
            # 保存节点的特有属性
            node_data['properties'] = CompositorNodeLibrary._export_node_properties(node)
            
            nodes_data.append(node_data)
        
        # 构建连接数据
        links_data = []
        for link in relevant_links:
            link_data = {
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.identifier,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.identifier,
            }
            links_data.append(link_data)
        
        data = {
            'nodes': nodes_data,
            'links': links_data,
            'export_type': 'selected_nodes',  # 标记这是选中的节点，而不是完整节点树
            'node_tree_type': node_tree.type,  # 保存节点树类型
        }
        
        # 如果提供了文件路径，保存文件
        if filepath:
            CompositorNodeLibrary.save_to_json(data, filepath)
        
        return data
    
    @staticmethod
    def save_to_json(data: Dict[str, Any], filepath: str):
        """将节点数据保存为JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"节点配置已保存到: {filepath}")
    
    @staticmethod
    def load_from_json(filepath: str) -> Dict[str, Any]:
        """从JSON文件加载节点数据"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"节点配置已从文件加载: {filepath}")
        return data
    
    @staticmethod
    def import_nodes_append(data: Dict[str, Any], 
                           context: Optional[bpy.types.Context] = None,
                           scene: Optional[bpy.types.Scene] = None,
                           material: Optional[bpy.types.Material] = None,
                           object: Optional[bpy.types.Object] = None,
                           offset: Optional[tuple] = None) -> bpy.types.NodeTree:
        """
        从字典数据导入节点并追加到当前节点树（不清除现有节点，支持所有节点类型）
        
        Args:
            data: 节点配置字典
            context: Blender上下文对象，用于自动检测当前编辑的节点类型
            scene: Blender场景对象（用于合成节点）
            material: 材质对象（用于材质节点）
            object: 物体对象（用于几何节点）
            offset: 节点位置偏移量 (x, y)，如果为None则自动计算避免重叠
        
        Returns:
            节点树对象
        """
        if context is None:
            context = bpy.context
        
        # 获取节点树类型
        node_tree_type = data.get('node_tree_type', 'COMPOSITING')
        
        # 自动检测或使用指定的目标节点树
        node_tree = None
        
        if material is not None:
            # 使用指定的材质
            if node_tree_type != 'SHADER':
                raise ValueError(f"节点树类型不匹配：JSON为{node_tree_type}，目标为SHADER（材质）")
            material.use_nodes = True
            if material.node_tree is None:
                name = data.get('node_tree_name', 'Material')
                node_tree = bpy.data.node_groups.new(type='SHADER', name=name)
                material.node_tree = node_tree
            else:
                node_tree = material.node_tree
                
        elif object is not None:
            # 使用指定的物体（几何节点）
            if node_tree_type != 'GEOMETRY':
                raise ValueError(f"节点树类型不匹配：JSON为{node_tree_type}，目标为GEOMETRY（几何节点）")
            # 查找或创建几何节点修改器
            geo_modifier = None
            for mod in object.modifiers:
                if mod.type == 'NODES':
                    geo_modifier = mod
                    break
            
            if geo_modifier is None:
                # 创建新的几何节点修改器
                geo_modifier = object.modifiers.new(
                    name=data.get('node_tree_name', 'GeometryNodes'),
                    type='NODES'
                )
            
            if geo_modifier.node_group is None:
                name = data.get('node_tree_name', 'GeometryNodes')
                node_tree = bpy.data.node_groups.new(type='GEOMETRY', name=name)
                geo_modifier.node_group = node_tree
            else:
                node_tree = geo_modifier.node_group
                
        elif scene is not None:
            # 使用指定的场景（合成节点）
            if node_tree_type != 'COMPOSITING':
                raise ValueError(f"节点树类型不匹配：JSON为{node_tree_type}，目标为COMPOSITING（合成）")
            scene.use_nodes = True
            if scene.node_tree is None or scene.node_tree.type != 'COMPOSITING':
                name = data.get('node_tree_name', 'Compositor')
                node_tree = bpy.data.node_groups.new(type='COMPOSITING', name=name)
                scene.node_tree = node_tree
            else:
                node_tree = scene.node_tree
        else:
            # 自动检测：尝试从当前上下文获取
            # 检查当前是否在编辑节点
            if context.space_data and hasattr(context.space_data, 'type'):
                if context.space_data.type == 'NODE_EDITOR':
                    if hasattr(context.space_data, 'node_tree') and context.space_data.node_tree:
                        if context.space_data.node_tree.type == node_tree_type:
                            node_tree = context.space_data.node_tree
            
            # 如果没找到，根据类型创建默认目标
            if node_tree is None:
                if node_tree_type == 'SHADER':
                    # 尝试使用活动材质
                    if context.active_object and context.active_object.active_material:
                        material = context.active_object.active_material
                        material.use_nodes = True
                        if material.node_tree is None:
                            name = data.get('node_tree_name', 'Material')
                            node_tree = bpy.data.node_groups.new(type='SHADER', name=name)
                            material.node_tree = node_tree
                        else:
                            node_tree = material.node_tree
                elif node_tree_type == 'GEOMETRY':
                    # 尝试使用活动对象的几何节点
                    if context.active_object:
                        geo_modifier = None
                        for mod in context.active_object.modifiers:
                            if mod.type == 'NODES':
                                geo_modifier = mod
                                break
                        if geo_modifier is None:
                            geo_modifier = context.active_object.modifiers.new(
                                name=data.get('node_tree_name', 'GeometryNodes'),
                                type='NODES'
                            )
                        if geo_modifier.node_group is None:
                            name = data.get('node_tree_name', 'GeometryNodes')
                            node_tree = bpy.data.node_groups.new(type='GEOMETRY', name=name)
                            geo_modifier.node_group = node_tree
                        else:
                            node_tree = geo_modifier.node_group
                else:  # COMPOSITING
                    # 使用场景的合成节点
                    if scene is None:
                        scene = context.scene
                    scene.use_nodes = True
                    if scene.node_tree is None or scene.node_tree.type != 'COMPOSITING':
                        name = data.get('node_tree_name', 'Compositor')
                        node_tree = bpy.data.node_groups.new(type='COMPOSITING', name=name)
                        scene.node_tree = node_tree
                    else:
                        node_tree = scene.node_tree
        
        if node_tree is None:
            node_type_names = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }
            node_type_name = node_type_names.get(node_tree_type, '节点')
            raise ValueError(f"无法找到或创建{node_type_name}节点树，请确保：\n"
                           f"1. 在对应的节点编辑器中\n"
                           f"2. 或指定正确的scene/material/object参数")
        
        # 计算位置偏移（避免与现有节点重叠）
        if offset is None:
            # 找到现有节点的最大X坐标
            max_x = 0
            max_y = 0
            for node in node_tree.nodes:
                max_x = max(max_x, node.location.x + node.width)
                max_y = max(max_y, node.location.y)
            # 偏移量设置为现有节点右侧，留出一些间距
            offset = (max_x + 100, max_y)
        else:
            offset = (offset[0], offset[1])
        
        # 创建节点名映射（处理重名情况）
        node_map = {}  # 映射：原始节点名 -> 节点对象
        nodes_data = data.get('nodes', [])
        print(f"[DEBUG-Load] 开始加载节点，共 {len(nodes_data)} 个节点")
        
        # 第一步：创建所有节点
        # 获取当前节点树中已有节点的类型（作为参考）
        existing_node_types = set()
        for existing_node in node_tree.nodes:
            existing_node_types.add(existing_node.type)
        
        # 节点类型映射表（基于常见问题和版本差异）
        # 注意：这个映射可能需要根据实际测试结果调整
        node_type_fix_map = {
            # 如果遇到这些类型，尝试使用映射后的类型
        }
        
        for idx, node_data in enumerate(nodes_data):
            node_type = node_data.get('type')
            original_name = node_data.get('name', '')
            
            # 如果没有名称，生成一个唯一的名称
            if not original_name or original_name.strip() == '':
                original_name = f"Node_{idx}_{node_type}"
            
            print(f"[DEBUG-Load] 处理节点 [{idx+1}/{len(nodes_data)}]: '{original_name}' (类型: {node_type})")
            
            # 节点类型映射（处理可能的命名差异和版本变化）
            node_type_mapping = {
                'RENDER_LAYERS': 'R_LAYERS',  # 某些版本可能使用不同的名称
                'RENDERLAYERS': 'R_LAYERS',
                'RENDER LAYERS': 'R_LAYERS',
            }
            if node_type in node_type_mapping:
                node_type = node_type_mapping[node_type]
            
            # 尝试创建节点，如果失败则尝试替代类型
            new_node = None
            node_creation_error = None
            
            print(f"[DEBUG-Load] 尝试创建节点 '{original_name}'，类型: '{node_type}'")
            
            try:
                # 首先尝试使用原始类型
                print(f"[DEBUG-Load]   尝试原始类型: {node_type}")
                new_node = node_tree.nodes.new(type=node_type)
                print(f"[DEBUG-Load]   ✅ 成功使用原始类型创建节点")
            except Exception as e:
                node_creation_error = e
                error_msg = str(e)
                
                # 如果是类型未定义的错误，尝试查找替代类型
                if "尚未定义节点类型" in error_msg or "node type not found" in error_msg.lower() or "not defined" in error_msg.lower():
                    # 尝试使用bl_idname格式（某些版本可能需要）
                    alternative_types = []
                    
                    # 根据常见节点类型生成替代名称
                    # 首先尝试通过节点树的类型获取所有可用的节点类型
                    alternative_types = []
                    
                    # 根据节点树类型选择不同的处理方式
                    node_tree_type = node_tree.type if hasattr(node_tree, 'type') else 'COMPOSITING'
                    
                    # 尝试通过bpy.ops获取（某些节点可能需要通过操作符创建）
                    # 但先尝试常见的类型名称变体
                    if node_type == 'GROUP_INPUT':
                        # 组输入节点：在不同节点树中类型名不同
                        if node_tree_type == 'GEOMETRY':
                            alternative_types = [
                                'NodeGroupInput',  # 几何节点使用 NodeGroupInput
                                'GeometryNodeGroupInput',
                                'GROUP_INPUT',
                                'GroupInput'
                            ]
                        elif node_tree_type == 'SHADER':
                            alternative_types = [
                                'NodeGroupInput',  # 材质节点也使用 NodeGroupInput
                                'ShaderNodeGroupInput',
                                'GROUP_INPUT'
                            ]
                        else:
                            alternative_types = [
                                'NodeGroupInput',  # 合成节点也使用 NodeGroupInput
                                'CompositorNodeGroupInput',
                                'GROUP_INPUT'
                            ]
                    elif node_type == 'GROUP_OUTPUT':
                        # 组输出节点：在不同节点树中类型名不同
                        if node_tree_type == 'GEOMETRY':
                            alternative_types = [
                                'NodeGroupOutput',  # 几何节点使用 NodeGroupOutput
                                'GeometryNodeGroupOutput',
                                'GROUP_OUTPUT',
                                'GroupOutput'
                            ]
                        elif node_tree_type == 'SHADER':
                            alternative_types = [
                                'NodeGroupOutput',  # 材质节点也使用 NodeGroupOutput
                                'ShaderNodeGroupOutput',
                                'GROUP_OUTPUT'
                            ]
                        else:
                            alternative_types = [
                                'NodeGroupOutput',  # 合成节点也使用 NodeGroupOutput
                                'CompositorNodeGroupOutput',
                                'GROUP_OUTPUT'
                            ]
                    elif node_type == 'COMPOSITE':
                        alternative_types = [
                            'CompositorNodeComposite', 
                            'COMPOSITE', 
                            'Composite',
                            'COMPOSITOR'
                        ]
                    elif node_type == 'R_LAYERS':
                        alternative_types = [
                            'CompositorNodeRLayers', 
                            'R_LAYERS', 
                            'RenderLayers', 
                            'RENDER_LAYERS',
                            'Render Layers'
                        ]
                    elif node_type == 'GLARE':
                        alternative_types = [
                            'CompositorNodeGlare', 
                            'GLARE', 
                            'Glare'
                        ]
                    elif node_type == 'BLUR':
                        alternative_types = [
                            'CompositorNodeBlur', 
                            'BLUR', 
                            'Blur'
                        ]
                    elif node_type == 'OUTPUT_MATERIAL' or node_type == 'MATERIAL_OUTPUT':
                        # 材质输出节点
                        alternative_types = [
                            'ShaderNodeOutputMaterial',
                            'OUTPUT_MATERIAL',
                            'MATERIAL_OUTPUT',
                            'OutputMaterial',
                            'Material Output'
                        ]
                    elif node_type == 'BSDF_PRINCIPLED' or node_type == 'PRINCIPLED_BSDF':
                        # 原理化BSDF节点
                        alternative_types = [
                            'ShaderNodeBsdfPrincipled',
                            'BSDF_PRINCIPLED',
                            'PRINCIPLED_BSDF',
                            'BsdfPrincipled',
                            'Principled BSDF'
                        ]
                    elif node_type == 'TEX_IMAGE' or node_type == 'IMAGE_TEXTURE':
                        # 图像纹理节点
                        alternative_types = [
                            'ShaderNodeTexImage',
                            'TEX_IMAGE',
                            'IMAGE_TEXTURE',
                            'TexImage',
                            'Image Texture'
                        ]
                    else:
                        # 根据节点树类型选择前缀
                        if node_tree_type == 'SHADER':
                            # 材质节点：使用 ShaderNode 前缀
                            alternative_types = [
                                f'ShaderNode{node_type}',
                                node_type,
                                node_type.capitalize(),
                                node_type.lower(),
                                node_type.replace('_', ' ').title().replace(' ', '')
                            ]
                        elif node_tree_type == 'GEOMETRY':
                            # 几何节点：使用 GeometryNode 前缀
                            # 几何节点的类型名需要转换为驼峰命名
                            # 例如: MESH_TO_POINTS -> MeshToPoints -> GeometryNodeMeshToPoints
                            def to_camel_case(s):
                                parts = s.split('_')
                                return ''.join(word.capitalize() for word in parts)
                            
                            camel_case = to_camel_case(node_type)
                            
                            alternative_types = [
                                node_type,  # 优先尝试原始类型名
                                f'GeometryNode{camel_case}',  # GeometryNodeMeshToPoints
                                f'GeometryNode{node_type.replace("_", "").title()}',  # 备用格式
                                camel_case,  # MeshToPoints
                                node_type.capitalize(),
                                node_type.lower(),
                                node_type.replace('_', ' ').title().replace(' ', ''),
                                node_type.replace('_', '').upper()
                            ]
                            
                            # 移除重复项，保持顺序
                            seen = set()
                            unique_alternatives = []
                            for alt in alternative_types:
                                if alt not in seen:
                                    seen.add(alt)
                                    unique_alternatives.append(alt)
                            alternative_types = unique_alternatives
                        else:
                            # 合成节点：使用 CompositorNode 前缀
                            alternative_types = [
                                f'CompositorNode{node_type}',
                                node_type,
                                node_type.capitalize(),
                                node_type.lower()
                            ]
                    
                    # 如果现有节点中有相同类型的，直接使用那个类型
                    if node_type in existing_node_types:
                        alternative_types.insert(0, node_type)  # 优先使用原始类型
                    
                    # 尝试通过枚举所有已注册的节点类型来查找（仅作为最后手段）
                    if new_node is None:
                        try:
                            # 根据节点树类型查找相关的节点类型
                            node_tree_type = node_tree.type if hasattr(node_tree, 'type') else 'COMPOSITING'
                            search_prefix = {
                                'SHADER': 'ShaderNode',
                                'GEOMETRY': 'GeometryNode',
                                'COMPOSITING': 'CompositorNode'
                            }.get(node_tree_type, 'CompositorNode')
                            
                            print(f"[DEBUG-Load] 为节点类型 '{node_type}' 在 {node_tree_type} 节点树中搜索 (前缀: {search_prefix})")
                            
                            found_node_types = []
                            node_type_upper = node_type.upper()
                            
                            # 特殊处理几何节点的类型名转换
                            if node_tree_type == 'GEOMETRY':
                                # 对于 GROUP_INPUT 和 GROUP_OUTPUT，使用特殊的节点类型名
                                if node_type == 'GROUP_INPUT':
                                    if 'NodeGroupInput' in dir(bpy.types):
                                        found_node_types.append('NodeGroupInput')
                                        print(f"[DEBUG-Load]   ✅ 找到组输入节点: NodeGroupInput")
                                elif node_type == 'GROUP_OUTPUT':
                                    if 'NodeGroupOutput' in dir(bpy.types):
                                        found_node_types.append('NodeGroupOutput')
                                        print(f"[DEBUG-Load]   ✅ 找到组输出节点: NodeGroupOutput")
                                else:
                                    # 其他几何节点的类型名通常需要转换为驼峰命名
                                    # 例如: MESH_TO_POINTS -> MeshToPoints -> GeometryNodeMeshToPoints
                                    def to_camel_case(s):
                                        # 将下划线分隔的字符串转换为驼峰命名
                                        parts = s.split('_')
                                        return ''.join(word.capitalize() for word in parts)
                                    
                                    camel_case = to_camel_case(node_type)
                                    exact_match = f'{search_prefix}{camel_case}'
                                    
                                    # 优先查找精确匹配的类型
                                    if exact_match in dir(bpy.types):
                                        found_node_types.append(exact_match)
                                        print(f"[DEBUG-Load]   ✅ 找到精确匹配: {exact_match}")
                                    
                                    # 也查找其他可能的变体（小写开头等）
                                    camel_case_lower = camel_case[0].lower() + camel_case[1:] if camel_case else ''
                                    if camel_case_lower:
                                        variant = f'{search_prefix}{camel_case_lower}'
                                        if variant in dir(bpy.types) and variant not in found_node_types:
                                            found_node_types.append(variant)
                            
                            # 通用搜索：匹配前缀和节点类型
                            for attr_name in dir(bpy.types):
                                attr_name_upper = attr_name.upper()
                                # 更精确的匹配逻辑
                                if search_prefix in attr_name:
                                    # 移除前缀后进行比较
                                    suffix = attr_name_upper.replace(search_prefix.upper(), '').replace('NODE', '')
                                    # 检查是否匹配节点类型（忽略大小写和分隔符）
                                    if (suffix == node_type_upper or 
                                        suffix.replace('_', '') == node_type_upper.replace('_', '') or
                                        attr_name_upper.endswith(node_type_upper)):
                                        if attr_name not in alternative_types and attr_name not in found_node_types:
                                            found_node_types.append(attr_name)
                                            print(f"[DEBUG-Load]   找到候选类型: {attr_name}")
                            
                            # 将找到的正确类型添加到列表前面（优先使用）
                            if found_node_types:
                                alternative_types = found_node_types[:10] + alternative_types  # 将精确匹配的类型放在前面
                                print(f"[DEBUG-Load] ✅ 将 {len(found_node_types)} 个精确匹配的候选类型放在列表前面")
                            else:
                                alternative_types.extend(found_node_types[:10])  # 如果没有精确匹配，添加到末尾
                            print(f"[DEBUG-Load] 共找到 {len(found_node_types)} 个候选类型")
                        except Exception as search_e:
                            print(f"[DEBUG-Load] 搜索节点类型时出错: {search_e}")
                            import traceback
                            traceback.print_exc()
                            pass
                    
                    # 尝试每个替代类型
                    print(f"[DEBUG-Load] 开始尝试 {len(alternative_types)} 个替代类型...")
                    for idx, alt_type in enumerate(alternative_types):
                        try:
                            print(f"[DEBUG-Load]   尝试 [{idx+1}/{len(alternative_types)}]: {alt_type}")
                            new_node = node_tree.nodes.new(type=alt_type)
                            print(f"✅ 成功: 使用替代类型 '{alt_type}' 创建节点 '{original_name}' (原类型: {node_type})")
                            # 更新节点类型为成功的类型，以便后续使用
                            node_type = alt_type
                            break
                        except Exception as alt_e:
                            # 记录失败但不中断
                            error_msg_short = str(alt_e)[:100]
                            print(f"[DEBUG-Load]     失败: {type(alt_e).__name__}: {error_msg_short}")
                            continue
                
                if new_node is None:
                    raise node_creation_error  # 如果所有尝试都失败，抛出原始错误
            
            # 如果节点创建失败，记录错误并跳过
            if new_node is None:
                print(f"错误: 无法创建节点 '{original_name}' (类型: {node_type}): {node_creation_error}")
                continue
            
            try:
                # 处理重名：如果节点名已存在，添加后缀
                # 注意：检查时要排除自己，且要检查现有节点树中是否已有同名节点
                new_name = original_name
                counter = 1
                # 检查是否已存在同名节点（排除当前正在创建的节点）
                existing_node_names = {n.name for n in node_tree.nodes if n != new_node}
                while new_name in node_map or new_name in existing_node_names:
                    new_name = f"{original_name}.{counter:03d}"
                    counter += 1
                    if counter > 999:  # 防止无限循环
                        new_name = f"{original_name}_{id(new_node)}"
                        break
                
                new_node.name = new_name
                print(f"[DEBUG-Load] 节点 '{original_name}' 重命名为 '{new_name}' (类型: {node_type})")
                
                # 设置基本属性
                if 'location' in node_data:
                    # 应用偏移量
                    loc_x = node_data['location'][0] + offset[0]
                    loc_y = node_data['location'][1] + offset[1]
                    new_node.location = (loc_x, loc_y)
                if 'width' in node_data:
                    new_node.width = node_data['width']
                if 'height' in node_data:
                    new_node.height = node_data['height']
                if 'label' in node_data and hasattr(new_node, 'label'):
                    new_node.label = node_data['label']
                if 'mute' in node_data:
                    new_node.mute = node_data['mute']
                if 'hide' in node_data:
                    new_node.hide = node_data['hide']
                if 'use_custom_color' in node_data:
                    new_node.use_custom_color = node_data['use_custom_color']
                if 'color' in node_data and hasattr(new_node, 'color'):
                    new_node.color = node_data['color']
                
                # 恢复节点属性
                CompositorNodeLibrary._import_node_properties(new_node, node_data.get('properties', {}))
                
                # 恢复输入插槽的值
                inputs_data = node_data.get('inputs', [])
                for input_data in inputs_data:
                    socket_identifier = input_data.get('identifier')
                    # 通过 identifier 查找插槽，而不是直接用 identifier 作为键
                    socket = None
                    for inp in new_node.inputs:
                        if inp.identifier == socket_identifier:
                            socket = inp
                            break
                    
                    if socket is None:
                        print(f"[DEBUG-Load] 警告: 节点 '{new_name}' 没有找到输入插槽 '{socket_identifier}'")
                        continue
                    
                    if 'default_value' in input_data:
                        try:
                            default_value = input_data['default_value']
                            if hasattr(socket, 'default_value'):
                                socket.default_value = CompositorNodeLibrary._deserialize_value(
                                    default_value, socket.default_value
                                )
                        except Exception as e:
                            print(f"警告: 无法设置输入插槽 '{socket_identifier}' 的值: {e}")
                    if 'enabled' in input_data and hasattr(socket, 'enabled'):
                        socket.enabled = input_data['enabled']
                
                # 保存新旧节点名的映射 - 使用 original_name 作为键，这样连接查找时能正确找到
                # 即使节点被重命名了，连接数据中的节点名仍然是 original_name
                if original_name in node_map:
                    print(f"[DEBUG-Load] 警告: 节点名 '{original_name}' 已存在于 node_map 中，将被覆盖")
                node_map[original_name] = new_node
                print(f"[DEBUG-Load] ✅ 节点创建成功: '{original_name}' -> '{new_name}' (类型: {node_type})")
                
            except Exception as e:
                error_msg = str(e)
                print(f"错误: 无法创建节点 '{original_name}' (类型: {node_type}): {error_msg}")
                
                # 如果是类型未定义的错误，尝试查找可能的替代类型
                if "尚未定义节点类型" in error_msg or "node type not found" in error_msg.lower():
                    # 尝试查找类似的节点类型
                    node_label_lower = (original_name.lower() if original_name else '').lower()
                    
                    # 根据节点名称猜测可能的类型
                    type_suggestions = []
                    if '渲染' in original_name or 'render' in node_label_lower or 'layer' in node_label_lower:
                        type_suggestions = ['R_LAYERS', 'RENDER_LAYERS']
                    elif '合成' in original_name or 'composite' in node_label_lower:
                        type_suggestions = ['COMPOSITE', 'COMPOSITOR']
                    elif '辉光' in original_name or 'glare' in node_label_lower:
                        type_suggestions = ['GLARE']
                    elif '模糊' in original_name or 'blur' in node_label_lower:
                        type_suggestions = ['BLUR']
                    
                    # 尝试建议的类型
                    found_alternative = False
                    for suggested_type in type_suggestions:
                        try:
                            test_node = node_tree.nodes.new(type=suggested_type)
                            node_tree.nodes.remove(test_node)
                            print(f"提示: 节点 '{original_name}' 可能需要使用类型 '{suggested_type}' 而不是 '{node_type}'")
                            found_alternative = True
                            break
                        except:
                            pass
                    
                    if not found_alternative:
                        print(f"提示: 节点类型 '{node_type}' 在当前Blender版本中可能不存在或已更改")
                
                continue
        
        # 第二步：创建连接（使用映射后的节点名）
        links_data = data.get('links', [])
        created_links = 0
        print(f"[DEBUG-Load] 开始创建连接，共 {len(links_data)} 条连接")
        print(f"[DEBUG-Load] node_map 中的节点: {list(node_map.keys())}")
        
        for idx, link_data in enumerate(links_data):
            from_node_name = link_data.get('from_node')
            from_socket_id = link_data.get('from_socket')  # 插槽的 identifier
            to_node_name = link_data.get('to_node')
            to_socket_id = link_data.get('to_socket')  # 插槽的 identifier
            
            print(f"[DEBUG-Load] 连接 [{idx+1}/{len(links_data)}]: {from_node_name}.{from_socket_id} -> {to_node_name}.{to_socket_id}")
            
            if from_node_name not in node_map or to_node_name not in node_map:
                missing_nodes = []
                if from_node_name not in node_map:
                    missing_nodes.append(from_node_name)
                if to_node_name not in node_map:
                    missing_nodes.append(to_node_name)
                print(f"警告: 无法创建连接，节点不存在: {missing_nodes}")
                continue
            
            from_node = node_map[from_node_name]
            to_node = node_map[to_node_name]
            
            try:
                # 通过 identifier 查找对应的插槽
                from_socket = None
                to_socket = None
                
                # 查找输出插槽
                for output in from_node.outputs:
                    if output.identifier == from_socket_id:
                        from_socket = output
                        break
                
                # 查找输入插槽
                for input_sock in to_node.inputs:
                    if input_sock.identifier == to_socket_id:
                        to_socket = input_sock
                        break
                
                if from_socket is None:
                    print(f"警告: 输出节点 '{from_node.name}' 没有找到插槽 '{from_socket_id}'")
                    print(f"[DEBUG-Load]   可用输出插槽: {[s.identifier for s in from_node.outputs]}")
                    continue
                    
                if to_socket is None:
                    print(f"警告: 输入节点 '{to_node.name}' 没有找到插槽 '{to_socket_id}'")
                    print(f"[DEBUG-Load]   可用输入插槽: {[s.identifier for s in to_node.inputs]}")
                    continue
                
                # 检查连接是否已存在
                link_exists = False
                for existing_link in node_tree.links:
                    if (existing_link.from_node == from_node and 
                        existing_link.from_socket == from_socket and
                        existing_link.to_node == to_node and
                        existing_link.to_socket == to_socket):
                        link_exists = True
                        break
                
                if not link_exists:
                    node_tree.links.new(from_socket, to_socket)
                    created_links += 1
                    print(f"[DEBUG-Load]   ✅ 成功创建连接: {from_node.name}.{from_socket_id} -> {to_node.name}.{to_socket_id}")
                else:
                    print(f"[DEBUG-Load]   连接已存在，跳过")
                    
            except Exception as e:
                print(f"警告: 无法创建连接 {from_node_name}.{from_socket_id} -> {to_node_name}.{to_socket_id}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[DEBUG-Load] 连接创建完成，成功创建 {created_links} 条连接")
        
        # 选择新创建的节点（这样用户可以看到它们）
        if node_map:
            # 取消选择所有现有节点
            for node in node_tree.nodes:
                node.select = False
            
            # 选择新创建的节点
            for new_node in node_map.values():
                new_node.select = True
            
            # 设置活动节点为第一个新节点
            if node_map:
                first_node = list(node_map.values())[0]
                node_tree.nodes.active = first_node
            
            # 尝试更新节点编辑器视图
            try:
                # 如果当前在节点编辑器中，尝试居中视图
                if context.space_data and context.space_data.type == 'NODE_EDITOR':
                    if context.space_data.node_tree == node_tree:
                        # 计算新节点的中心位置
                        if node_map:
                            nodes = list(node_map.values())
                            center_x = sum(node.location.x for node in nodes) / len(nodes)
                            center_y = sum(node.location.y for node in nodes) / len(nodes)
                            # 设置视图中心（Blender 3.6+）
                            context.space_data.view_center = (center_x, center_y)
            except:
                pass  # 如果无法更新视图，忽略错误
        
        node_tree_type_name = {
            'COMPOSITING': '合成',
            'SHADER': '材质',
            'GEOMETRY': '几何'
        }.get(node_tree_type, '节点')
        print(f"成功追加{node_tree_type_name}节点，共 {len(node_map)} 个节点，{created_links} 条连接")
        return node_tree
    
    @staticmethod
    def list_json_files() -> List[str]:
        """列出目录中所有的JSON文件"""
        json_dir = get_compositor_nodes_json_path()
        if not json_dir:
            return []
        
        if not os.path.exists(json_dir):
            return []
        
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
        json_files.sort()  # 按名称排序
        return json_files

# ============================================================================
# Blender操作符：保存选中的节点
# ============================================================================

class COMPOSITOR_OT_save_selected_nodes(bpy.types.Operator):
    """保存当前选中的节点为JSON文件（自动检测类型）"""
    bl_idname = "compositor.save_selected_nodes"
    bl_label = "保存选中节点（自动）"
    bl_options = {'REGISTER', 'UNDO'}
    
    node_type: bpy.props.StringProperty(
        name="节点类型",
        description="指定节点类型（COMPOSITING/SHADER/GEOMETRY），为空则自动检测",
        default=""
    )
    
    filename_ext = ".json"
    
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    filepath: bpy.props.StringProperty(
        name="文件路径",
        subtype='FILE_PATH',
        default="compositor_nodes.json"
    )
    
    def execute(self, context):
        try:
            # 如果文件路径是相对路径，保存到默认目录
            if not os.path.isabs(self.filepath):
                json_dir = get_compositor_nodes_json_path()
                if json_dir:
                    self.filepath = os.path.join(json_dir, os.path.basename(self.filepath))
            
            # 如果指定了节点类型，使用指定类型；否则自动检测
            if self.node_type:
                data = CompositorNodeLibrary.export_selected_nodes_by_type(
                    context=context, 
                    node_type=self.node_type,
                    filepath=self.filepath
                )
            else:
                data = CompositorNodeLibrary.export_selected_nodes(context=context, filepath=self.filepath)
            
            node_count = len(data.get('nodes', []))
            node_tree_type = data.get('node_tree_type', '未知')
            node_type_names = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }
            type_name = node_type_names.get(node_tree_type, node_tree_type)
            self.report({'INFO'}, f"已保存 {node_count} 个{type_name}节点到: {os.path.basename(self.filepath)}")
            
            # 更新文件列表
            update_compositor_json_file_list(context)
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存失败: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # 如果指定了节点类型，直接使用指定类型查找节点树
        if self.node_type:
            node_tree = CompositorNodeLibrary._get_node_tree_by_type(context, self.node_type)
            if node_tree is None:
                node_type_names = {
                    'COMPOSITING': '合成',
                    'SHADER': '材质',
                    'GEOMETRY': '几何'
                }
                type_name = node_type_names.get(self.node_type, self.node_type)
                self.report({'ERROR'}, f"无法找到{type_name}节点树")
                return {'CANCELLED'}
        else:
            # 自动检测：优先检查节点编辑器
            node_tree = None
            
            # 检查当前是否在节点编辑器中（最准确）
            if context.space_data and hasattr(context.space_data, 'type'):
                if context.space_data.type == 'NODE_EDITOR':
                    if hasattr(context.space_data, 'node_tree') and context.space_data.node_tree:
                        node_tree = context.space_data.node_tree
            
            # 如果不在节点编辑器中，按类型优先级检测
            if node_tree is None:
                # 尝试所有类型，找到第一个有选中节点的
                for node_type in ['COMPOSITING', 'SHADER', 'GEOMETRY']:
                    temp_tree = CompositorNodeLibrary._get_node_tree_by_type(context, node_type)
                    if temp_tree:
                        selected = [n for n in temp_tree.nodes if n.select]
                        if selected:
                            node_tree = temp_tree
                            break
        
        if node_tree is None:
            self.report({'ERROR'}, "无法找到节点树或没有选中的节点。请确保在节点编辑器中选择节点")
            return {'CANCELLED'}
        
        selected_nodes = [n for n in node_tree.nodes if n.select]
        if not selected_nodes:
            node_type_names = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }
            node_type_name = node_type_names.get(node_tree.type, '节点')
            self.report({'ERROR'}, f"请先选中要保存的{node_type_name}节点")
            return {'CANCELLED'}
        
        # 设置默认文件名和目录
        json_dir = get_compositor_nodes_json_path()
        if json_dir:
            # 使用默认目录，文件名包含节点类型
            node_tree_type = node_tree.type
            type_prefix = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }.get(node_tree_type, '节点')
            default_filename = f"{type_prefix}节点_{len(selected_nodes)}nodes.json"
            self.filepath = os.path.join(json_dir, default_filename)
        else:
            self.filepath = "compositor_nodes.json"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ============================================================================
# 三个专门的保存操作符（合成、材质、几何节点）
# ============================================================================

class COMPOSITOR_OT_save_compositor_nodes(bpy.types.Operator):
    """保存选中的合成节点"""
    bl_idname = "compositor.save_compositor_nodes"
    bl_label = "保存合成节点"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'}, maxlen=255)
    filepath: bpy.props.StringProperty(name="文件路径", subtype='FILE_PATH', default="compositor_nodes.json")
    
    def execute(self, context):
        try:
            if not os.path.isabs(self.filepath):
                json_dir = get_compositor_nodes_json_path()
                if json_dir:
                    self.filepath = os.path.join(json_dir, os.path.basename(self.filepath))
            
            data = CompositorNodeLibrary.export_selected_nodes_by_type(
                context=context, 
                node_type='COMPOSITING',
                filepath=self.filepath
            )
            node_count = len(data.get('nodes', []))
            self.report({'INFO'}, f"已保存 {node_count} 个合成节点")
            update_compositor_json_file_list(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存失败: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        node_tree = CompositorNodeLibrary._get_node_tree_by_type(context, 'COMPOSITING')
        if node_tree is None:
            self.report({'ERROR'}, "无法找到合成节点树，请确保场景已启用合成节点")
            return {'CANCELLED'}
        
        selected_nodes = [n for n in node_tree.nodes if n.select]
        if not selected_nodes:
            self.report({'ERROR'}, "请先选中要保存的合成节点")
            return {'CANCELLED'}
        
        json_dir = get_compositor_nodes_json_path()
        if json_dir:
            # 文件名包含节点类型
            default_filename = f"合成节点_{len(selected_nodes)}nodes.json"
            self.filepath = os.path.join(json_dir, default_filename)
        else:
            self.filepath = "compositor_nodes.json"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class COMPOSITOR_OT_save_shader_nodes(bpy.types.Operator):
    """保存选中的材质节点"""
    bl_idname = "compositor.save_shader_nodes"
    bl_label = "保存材质节点"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'}, maxlen=255)
    filepath: bpy.props.StringProperty(name="文件路径", subtype='FILE_PATH', default="shader_nodes.json")
    
    def execute(self, context):
        try:
            print(f"[DEBUG] ========== 开始保存材质节点 ==========")
            print(f"[DEBUG] 文件路径: {self.filepath}")
            if not os.path.isabs(self.filepath):
                json_dir = get_compositor_nodes_json_path()
                if json_dir:
                    self.filepath = os.path.join(json_dir, os.path.basename(self.filepath))
                    print(f"[DEBUG] 解析后的完整路径: {self.filepath}")
            
            print(f"[DEBUG] 调用 export_selected_nodes_by_type...")
            data = CompositorNodeLibrary.export_selected_nodes_by_type(
                context=context, 
                node_type='SHADER',
                filepath=self.filepath
            )
            print(f"[DEBUG] export_selected_nodes_by_type 返回，节点数量: {len(data.get('nodes', []))}")
            node_count = len(data.get('nodes', []))
            self.report({'INFO'}, f"已保存 {node_count} 个材质节点")
            update_compositor_json_file_list(context)
            print(f"[DEBUG] ========== 保存完成 ==========")
            return {'FINISHED'}
        except Exception as e:
            print(f"[DEBUG] ❌❌❌ 保存失败 ❌❌❌")
            print(f"[DEBUG] 错误类型: {type(e).__name__}")
            print(f"[DEBUG] 错误信息: {str(e)}")
            import traceback
            print(f"[DEBUG] 完整堆栈:")
            traceback.print_exc()
            self.report({'ERROR'}, f"保存失败: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        node_tree = CompositorNodeLibrary._get_node_tree_by_type(context, 'SHADER')
        if node_tree is None:
            self.report({'ERROR'}, "无法找到材质节点树，请确保活动对象有材质且启用了节点")
            return {'CANCELLED'}
        
        selected_nodes = [n for n in node_tree.nodes if n.select]
        if not selected_nodes:
            self.report({'ERROR'}, "请先选中要保存的材质节点")
            return {'CANCELLED'}
            
        json_dir = get_compositor_nodes_json_path()
        if json_dir:
            # 文件名包含节点类型
            default_filename = f"材质节点_{len(selected_nodes)}nodes.json"
            self.filepath = os.path.join(json_dir, default_filename)
        else:
            self.filepath = "shader_nodes.json"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class COMPOSITOR_OT_save_geometry_nodes(bpy.types.Operator):
    """保存选中的几何节点"""
    bl_idname = "compositor.save_geometry_nodes"
    bl_label = "保存几何节点"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'}, maxlen=255)
    filepath: bpy.props.StringProperty(name="文件路径", subtype='FILE_PATH', default="geometry_nodes.json")
    
    def execute(self, context):
        try:
            if not os.path.isabs(self.filepath):
                json_dir = get_compositor_nodes_json_path()
                if json_dir:
                    self.filepath = os.path.join(json_dir, os.path.basename(self.filepath))
            
            data = CompositorNodeLibrary.export_selected_nodes_by_type(
                context=context, 
                node_type='GEOMETRY',
                filepath=self.filepath
            )
            node_count = len(data.get('nodes', []))
            self.report({'INFO'}, f"已保存 {node_count} 个几何节点")
            update_compositor_json_file_list(context)
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"保存失败: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        node_tree = CompositorNodeLibrary._get_node_tree_by_type(context, 'GEOMETRY')
        if node_tree is None:
            self.report({'ERROR'}, "无法找到几何节点树，请确保活动对象有几何节点修改器")
            return {'CANCELLED'}
        
        selected_nodes = [n for n in node_tree.nodes if n.select]
        if not selected_nodes:
            self.report({'ERROR'}, "请先选中要保存的几何节点")
            return {'CANCELLED'}
        
        json_dir = get_compositor_nodes_json_path()
        if json_dir:
            # 文件名包含节点类型
            default_filename = f"几何节点_{len(selected_nodes)}nodes.json"
            self.filepath = os.path.join(json_dir, default_filename)
        else:
            self.filepath = "geometry_nodes.json"
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# ============================================================================
# Blender操作符：从JSON文件加载节点（追加模式）
# ============================================================================

class COMPOSITOR_OT_load_nodes_from_json(bpy.types.Operator):
    """从JSON文件加载节点并添加到当前节点树"""
    bl_idname = "compositor.load_nodes_from_json"
    bl_label = "加载节点（追加）"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        name="文件路径",
        subtype='FILE_PATH',
    )
    
    def execute(self, context):
        try:
            # 如果文件路径是相对路径，从默认目录加载
            if not os.path.isabs(self.filepath):
                json_dir = get_compositor_nodes_json_path()
                if json_dir:
                    self.filepath = os.path.join(json_dir, self.filepath)
            
            if not os.path.exists(self.filepath):
                self.report({'ERROR'}, f"文件不存在: {self.filepath}")
                return {'CANCELLED'}
            
            data = CompositorNodeLibrary.load_from_json(self.filepath)
            CompositorNodeLibrary.import_nodes_append(data, context=context)
            
            node_count = len(data.get('nodes', []))
            self.report({'INFO'}, f"已加载 {node_count} 个节点")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


# ============================================================================
# 文件列表管理
# ============================================================================

class CompositorJsonFileItem(bpy.types.PropertyGroup):
    """JSON文件列表项"""
    name: bpy.props.StringProperty(name="文件名")
    node_type: bpy.props.StringProperty(name="节点类型")  # COMPOSITING/SHADER/GEOMETRY


class COMPOSITOR_UL_json_file_list(bpy.types.UIList):
    """自定义UI列表，显示文件名和节点类型"""
    bl_idname = "COMPOSITOR_UL_json_file_list"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        """绘制列表项"""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # 获取节点类型显示名称和图标
            node_type = item.node_type
            type_names = {
                'COMPOSITING': ('合成节点', 'RENDERLAYERS'),
                'SHADER': ('材质节点', 'MATERIAL'),
                'GEOMETRY': ('几何节点', 'MODIFIER'),
                'UNKNOWN': ('未知类型', 'QUESTION')
            }
            type_display, type_icon = type_names.get(node_type, ('未知', 'QUESTION'))
            
            # 显示类型图标和文件名
            row = layout.row(align=True)
            row.label(text="", icon=type_icon)
            row.label(text=type_display, icon='BLANK1')
            row.separator()
            row.label(text=item.name)
            
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)


def update_compositor_json_file_list(context):
    """更新合成节点JSON文件列表，并从JSON文件中读取节点类型"""
    json_dir = get_compositor_nodes_json_path()
    files = CompositorNodeLibrary.list_json_files()
    
    # 清除现有列表
    context.scene.compositor_json_file_list.clear()
    
    # 添加文件到列表，并读取节点类型
    for filename in files:
        item = context.scene.compositor_json_file_list.add()
        item.name = filename
        
        # 尝试从JSON文件中读取节点类型
        try:
            filepath = os.path.join(json_dir, filename)
            if os.path.exists(filepath):
                data = CompositorNodeLibrary.load_from_json(filepath)
                node_tree_type = data.get('node_tree_type', 'UNKNOWN')
                item.node_type = node_tree_type
            else:
                # 根据文件名猜测类型
                filename_lower = filename.lower()
                if '合成' in filename or 'compositor' in filename_lower:
                    item.node_type = 'COMPOSITING'
                elif '材质' in filename or 'shader' in filename_lower:
                    item.node_type = 'SHADER'
                elif '几何' in filename or 'geometry' in filename_lower:
                    item.node_type = 'GEOMETRY'
                else:
                    item.node_type = 'UNKNOWN'
        except:
            # 如果读取失败，根据文件名猜测
            filename_lower = filename.lower()
            if '合成' in filename or 'compositor' in filename_lower:
                item.node_type = 'COMPOSITING'
            elif '材质' in filename or 'shader' in filename_lower:
                item.node_type = 'SHADER'
            elif '几何' in filename or 'geometry' in filename_lower:
                item.node_type = 'GEOMETRY'
            else:
                item.node_type = 'UNKNOWN'

# ============================================================================
# 操作符：从列表中选择文件并加载
# ============================================================================

class COMPOSITOR_OT_delete_json_file(bpy.types.Operator):
    """删除选中的JSON文件"""
    bl_idname = "compositor.delete_json_file"
    bl_label = "删除选中文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def invoke(self, context, event):
        # 确认删除对话框
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        try:
            # 获取当前选择的文件索引
            index = context.scene.compositor_json_file_index
            file_list = context.scene.compositor_json_file_list
            
            if index < 0 or index >= len(file_list):
                self.report({'ERROR'}, "请选择一个有效的JSON文件")
                return {'CANCELLED'}
            
            # 获取文件名和路径
            filename = file_list[index].name
            json_dir = get_compositor_nodes_json_path()
            
            if not json_dir:
                self.report({'ERROR'}, "无法找到节点库目录")
                return {'CANCELLED'}
            
            filepath = os.path.join(json_dir, filename)
            
            if not os.path.exists(filepath):
                self.report({'ERROR'}, f"文件不存在: {filename}")
                return {'CANCELLED'}
            
            # 删除文件
            try:
                os.remove(filepath)
                self.report({'INFO'}, f"已删除文件: {filename}")
                
                # 更新文件列表
                update_compositor_json_file_list(context)
                
                # 如果删除后索引超出范围，调整索引
                if index >= len(context.scene.compositor_json_file_list):
                    context.scene.compositor_json_file_index = max(0, len(context.scene.compositor_json_file_list) - 1)
                
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f"删除文件失败: {str(e)}")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"删除失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

class COMPOSITOR_OT_load_nodes_from_list(bpy.types.Operator):
    """从文件列表中选择并加载节点"""
    bl_idname = "compositor.load_nodes_from_list"
    bl_label = "加载选中节点"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取当前选择的文件索引
        index = context.scene.compositor_json_file_index
        file_list = context.scene.compositor_json_file_list
        
        if index < 0 or index >= len(file_list):
            self.report({'ERROR'}, "请选择一个有效的JSON文件")
            return {'CANCELLED'}
        
        # 获取文件名和路径
        filename = file_list[index].name
        json_dir = get_compositor_nodes_json_path()
        
        if not json_dir:
            self.report({'ERROR'}, "无法找到节点库目录")
            return {'CANCELLED'}
        
        filepath = os.path.join(json_dir, filename)
        
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"文件不存在: {filename}")
            return {'CANCELLED'}
        
        try:
            data = CompositorNodeLibrary.load_from_json(filepath)
            node_tree_type = data.get('node_tree_type', 'COMPOSITING')
            node_tree = CompositorNodeLibrary.import_nodes_append(data, context=context)
            
            node_count = len(data.get('nodes', []))
            node_type_names = {
                'COMPOSITING': '合成',
                'SHADER': '材质',
                'GEOMETRY': '几何'
            }
            type_name = node_type_names.get(node_tree_type, '节点')
            
            # 确保用户在正确的编辑器中查看
            if node_tree:
                # 如果是合成节点，确保场景启用节点
                if node_tree_type == 'COMPOSITING':
                    context.scene.use_nodes = True
                # 如果是材质节点，提示用户切换到材质编辑器
                elif node_tree_type == 'SHADER':
                    self.report({'INFO'}, f"已加载 {node_count} 个材质节点，请切换到材质编辑器查看")
                # 如果是几何节点，提示用户切换到几何节点编辑器
                elif node_tree_type == 'GEOMETRY':
                    self.report({'INFO'}, f"已加载 {node_count} 个几何节点，请切换到几何节点编辑器查看")
            
            self.report({'INFO'}, f"已加载 {node_count} 个{type_name}节点: {filename}")
            
            # 如果不在节点编辑器中，提示用户
            if not (context.space_data and context.space_data.type == 'NODE_EDITOR'):
                editor_names = {
                    'COMPOSITING': '合成节点编辑器',
                    'SHADER': '材质编辑器',
                    'GEOMETRY': '几何节点编辑器'
                }
                editor_name = editor_names.get(node_tree_type, '节点编辑器')
                self.report({'INFO'}, f"提示：请在{editor_name}中查看加载的节点")
            
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"加载失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}

class COMPOSITOR_OT_refresh_file_list(bpy.types.Operator):
    """刷新文件列表"""
    bl_idname = "compositor.refresh_file_list"
    bl_label = "刷新列表"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        update_compositor_json_file_list(context)
        file_count = len(context.scene.compositor_json_file_list)
        self.report({'INFO'}, f"已刷新，找到 {file_count} 个文件")
        return {'FINISHED'}

# ============================================================================
# 注册和注销
# ============================================================================

def register():
    """注册操作符和属性"""
    bpy.utils.register_class(CompositorJsonFileItem)
    bpy.utils.register_class(COMPOSITOR_UL_json_file_list)
    bpy.utils.register_class(COMPOSITOR_OT_save_selected_nodes)
    bpy.utils.register_class(COMPOSITOR_OT_save_compositor_nodes)
    bpy.utils.register_class(COMPOSITOR_OT_save_shader_nodes)
    bpy.utils.register_class(COMPOSITOR_OT_save_geometry_nodes)
    bpy.utils.register_class(COMPOSITOR_OT_load_nodes_from_json)
    bpy.utils.register_class(COMPOSITOR_OT_load_nodes_from_list)
    bpy.utils.register_class(COMPOSITOR_OT_delete_json_file)
    bpy.utils.register_class(COMPOSITOR_OT_refresh_file_list)
    
    # 注册场景属性
    bpy.types.Scene.compositor_json_file_list = bpy.props.CollectionProperty(type=CompositorJsonFileItem)
    bpy.types.Scene.compositor_json_file_index = bpy.props.IntProperty(
        name="选中的JSON文件",
        default=0,
        min=0
    )
    # 确保NodeJson文件夹已创建
    ensure_node_json_directories()

def unregister():
    """注销操作符和属性"""
    bpy.utils.unregister_class(COMPOSITOR_OT_refresh_file_list)
    bpy.utils.unregister_class(COMPOSITOR_OT_load_nodes_from_list)
    bpy.utils.unregister_class(COMPOSITOR_OT_delete_json_file)
    bpy.utils.unregister_class(COMPOSITOR_OT_load_nodes_from_json)
    bpy.utils.unregister_class(COMPOSITOR_OT_save_geometry_nodes)
    bpy.utils.unregister_class(COMPOSITOR_OT_save_shader_nodes)
    bpy.utils.unregister_class(COMPOSITOR_OT_save_compositor_nodes)
    bpy.utils.unregister_class(COMPOSITOR_OT_save_selected_nodes)
    bpy.utils.unregister_class(COMPOSITOR_UL_json_file_list)
    bpy.utils.unregister_class(CompositorJsonFileItem)
    # 删除场景属性
    del bpy.types.Scene.compositor_json_file_list
    del bpy.types.Scene.compositor_json_file_index

