import bpy
import os
import random
from pathlib import Path
import json

# 定义关键词列表
GENDER_KEYWORDS = ['male', 'female', 'm', 'f']
BODY_PART_KEYWORDS = ['Upper', 'Lower', 'Hair', 'Nose', 'Eyes', 'Mouse', 'Bottom', 'Top', 'Feet','Eyebrow']

class CharacterPartReplacer:
    """角色部件替换器"""
    
    def __init__(self, source_file_path):
        self.source_file_path = source_file_path
        self.source_objects = {}
        self.current_indices = {}  # 存储每个组合的当前索引
        self.load_source_objects()
    
    def cleanup(self):
        """清理资源，释放内存"""
        try:
            print("开始清理CharacterPartReplacer资源...")
            
            # 清理网格数据
            for (gender, body_part), objects in self.source_objects.items():
                for obj_data in objects:
                    try:
                        if 'mesh_data' in obj_data and obj_data['mesh_data']:
                            mesh = obj_data['mesh_data']
                            if mesh.users == 0:
                                bpy.data.meshes.remove(mesh)
                                print(f"清理网格数据: {mesh.name}")
                    except Exception as e:
                        print(f"清理网格数据时出错: {str(e)}")
                    
                    # 清理材质数据
                    if 'materials' in obj_data:
                        for mat in obj_data['materials']:
                            try:
                                if mat and mat.users == 0:
                                    bpy.data.materials.remove(mat)
                                    print(f"清理材质数据: {mat.name}")
                            except Exception as e:
                                print(f"清理材质数据时出错: {str(e)}")
            
            # 清空数据字典
            self.source_objects.clear()
            self.current_indices.clear()
            
            print("CharacterPartReplacer资源清理完成")
            
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def create_fully_independent_material(self, original_material):
        """创建完全独立的材质副本，简化版本以提高性能"""
        try:
            if not original_material:
                return None
            
            # 简单复制材质，不复制复杂的节点树和纹理
            new_material = original_material.copy()
            
            # 确保材质名称唯一
            if new_material.name in bpy.data.materials:
                counter = 1
                base_name = new_material.name
                while f"{base_name}_{counter:03d}" in bpy.data.materials:
                    counter += 1
                new_material.name = f"{base_name}_{counter:03d}"
            
            # 不复制节点树，避免复杂的数据关系
            # 如果需要节点树，可以后续手动处理
            
            return new_material
            
        except Exception as e:
            print(f"创建独立材质副本时出错: {str(e)}")
            return original_material.copy() if original_material else None
    
    def load_source_objects(self):
        """加载源文件中的对象"""
        if not os.path.exists(self.source_file_path):
            print(f"源文件不存在: {self.source_file_path}")
            return
        
        try:
            print(f"开始加载源文件: {self.source_file_path}")
            
            # 使用链接方式加载源文件
            with bpy.data.libraries.load(self.source_file_path, link=False) as (data_from, data_to):
                # 加载所有网格对象
                data_to.objects = [name for name in data_from.objects if name in data_from.meshes]
            
            print(f"从源文件加载了 {len(data_to.objects)} 个对象")
            
            # 收集源文件中的对象数据
            for obj in data_to.objects:
                if obj and obj.type == 'MESH':
                    try:
                        keywords = self.extract_keywords(obj.name)
                        if keywords:
                            gender, body_part = keywords
                            key = (gender, body_part)
                            if key not in self.source_objects:
                                self.source_objects[key] = []
                            
                            # 复制对象数据 - 确保数据独立性
                            mesh_data = obj.data.copy()
                            
                            # 复制材质数据 - 使用完全独立的方法
                            materials = []
                            for mat in obj.data.materials:
                                if mat:
                                    independent_mat = self.create_fully_independent_material(mat)
                                    if independent_mat:
                                        materials.append(independent_mat)
                            
                            self.source_objects[key].append({
                                'name': obj.name,
                                'mesh_data': mesh_data,
                                'materials': materials,
                                'original_obj': obj
                            })
                            print(f"  添加对象: {obj.name} -> {gender} {body_part}")
                    except Exception as e:
                        print(f"处理对象 {obj.name} 时出错: {str(e)}")
                        continue
            
            print(f"成功处理了 {sum(len(objs) for objs in self.source_objects.values())} 个对象")
            
            # 清理临时对象
            for obj in data_to.objects:
                if obj:
                    try:
                        bpy.data.objects.remove(obj, do_unlink=True)
                    except Exception as e:
                        print(f"清理对象 {obj.name} 时出错: {str(e)}")
                        
        except Exception as e:
            print(f"加载源文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def extract_keywords(self, object_name):
        """从对象名称中提取性别和部位关键词（不区分大小写）"""
        name_lower = object_name.lower()
        
        # 提取性别关键词 - 使用更精确的匹配
        gender = None
        
        # 优先检查完整的性别关键词（避免子字符串匹配问题）
        if 'female' in name_lower:
            gender = 'female'
        elif 'male' in name_lower:
            gender = 'male'
        # 然后检查简写（确保不会与完整词冲突）
        elif 'f' in name_lower and not any(word in name_lower for word in ['female', 'male']):
            gender = 'female'
        elif 'm' in name_lower and not any(word in name_lower for word in ['female', 'male']):
            gender = 'male'
        
        # 提取部位关键词
        body_part = None
        
        # 检查部位关键词（不区分大小写）
        for keyword in BODY_PART_KEYWORDS:
            if keyword.lower() in name_lower:
                body_part = keyword
                print(f"  匹配到部位关键词: {keyword} (在名称: {object_name})")
                break
        
        # 如果没有找到性别关键词，尝试从父对象名称中提取
        if not gender and hasattr(self, 'current_obj') and self.current_obj.parent:
            parent_name_lower = self.current_obj.parent.name.lower()
            if 'female' in parent_name_lower:
                gender = 'female'
            elif 'male' in parent_name_lower:
                gender = 'male'
            elif 'f' in parent_name_lower and not any(word in parent_name_lower for word in ['female', 'male']):
                gender = 'female'
            elif 'm' in parent_name_lower and not any(word in parent_name_lower for word in ['female', 'male']):
                gender = 'male'
        
        return (gender, body_part) if gender and body_part else None
    
    def get_replacement_object(self, gender, body_part, direction=0):
        """获取替换对象
        direction: 0=当前, 1=下一个, -1=上一个
        """
        key = (gender, body_part)
        if key not in self.source_objects or not self.source_objects[key]:
            return None
        
        objects = self.source_objects[key]
        if key not in self.current_indices:
            self.current_indices[key] = 0
        
        current_index = self.current_indices[key]
        
        if direction == 1:  # 下一个
            current_index = (current_index + 1) % len(objects)
        elif direction == -1:  # 上一个
            current_index = (current_index - 1) % len(objects)
        
        self.current_indices[key] = current_index
        return objects[current_index]
    
    def get_replacement_object_random(self, gender, body_part):
        """随机获取替换对象"""
        key = (gender, body_part)
        if key not in self.source_objects or not self.source_objects[key]:
            return None
        
        objects = self.source_objects[key]
        return random.choice(objects)
    
    def get_safe_object_name(self, desired_name):
        """生成安全的对象名称，避免冲突和特殊字符"""
        import re
        
        # 清理名称中的特殊字符
        safe_name = re.sub(r'[^\w\-_.]', '_', desired_name)
        
        # 确保名称不以数字开头
        if safe_name and safe_name[0].isdigit():
            safe_name = 'Obj_' + safe_name
        
        # 如果名称为空，使用默认名称
        if not safe_name:
            safe_name = 'ReplacedObject'
        
        # 检查名称是否已存在，如果存在则添加后缀
        counter = 1
        original_name = safe_name
        while safe_name in bpy.data.objects:
            safe_name = f"{original_name}_{counter:03d}"
            counter += 1
            # 防止无限循环
            if counter > 999:
                safe_name = f"{original_name}_{hash(safe_name) % 1000:03d}"
                break
        
        return safe_name
    

    
    def verify_object_independence(self, obj):
        """验证对象数据的独立性"""
        try:
            # 检查网格数据
            if obj.data.users > 1:
                print(f"警告: 对象 {obj.name} 的网格数据被多个对象共享")
                return False
            
            # 检查材质数据
            for i, mat in enumerate(obj.data.materials):
                if mat and mat.users > 1:
                    print(f"警告: 对象 {obj.name} 的材质 {i} ({mat.name}) 被多个对象共享")
                    return False
            
            # 检查材质内部的纹理和节点数据
            for i, mat in enumerate(obj.data.materials):
                if mat:
                    # 检查材质节点
                    if mat.node_tree:
                        # 检查节点树是否被多个材质共享
                        if mat.node_tree.users > 1:
                            print(f"警告: 对象 {obj.name} 的材质 {i} ({mat.name}) 的节点树被多个材质共享")
                            return False
                        
                        # 检查节点树中的纹理节点
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                if node.image.users > 1:
                                    print(f"警告: 对象 {obj.name} 的材质 {i} ({mat.name}) 的纹理 {node.image.name} 被多个对象共享")
                                    return False
            
            print(f"对象 {obj.name} 的数据独立性验证通过")
            return True
        except Exception as e:
            print(f"验证对象独立性时出错: {str(e)}")
            return False
    
    def replace_object(self, target_obj, direction=0):
        """替换目标对象
        direction: 0=当前, 1=下一个, -1=上一个
        """
        try:
            # 设置当前对象用于父级名称检查
            self.current_obj = target_obj
            
            keywords = self.extract_keywords(target_obj.name)
            if not keywords:
                print(f"无法从对象名称中提取关键词: {target_obj.name}")
                return False
            
            gender, body_part = keywords
            print(f"提取关键词: {target_obj.name} -> 性别: {gender}, 部位: {body_part}")
            print(f"  名称小写: {target_obj.name.lower()}")
            
            replacement_data = self.get_replacement_object(gender, body_part, direction)
            
            if not replacement_data:
                print(f"未找到匹配的替换对象: {gender}, {body_part}")
                return False
            
            # 执行替换操作
            self.perform_replacement(target_obj, replacement_data, replace_name=getattr(bpy.context.scene, 'replace_object_name', True))
            return True
        except Exception as e:
            print(f"替换对象 {target_obj.name} 时出错: {str(e)}")
            return False
    
    def replace_object_random(self, target_obj):
        """随机替换目标对象"""
        try:
            # 设置当前对象用于父级名称检查
            self.current_obj = target_obj
            
            keywords = self.extract_keywords(target_obj.name)
            if not keywords:
                print(f"无法从对象名称中提取关键词: {target_obj.name}")
                return False
            
            gender, body_part = keywords
            print(f"提取关键词: {target_obj.name} -> 性别: {gender}, 部位: {body_part}")
            print(f"  名称小写: {target_obj.name.lower()}")
            
            replacement_data = self.get_replacement_object_random(gender, body_part)
            
            if not replacement_data:
                print(f"未找到匹配的替换对象: {gender}, {body_part}")
                return False
            
            # 执行替换操作
            self.perform_replacement(target_obj, replacement_data, replace_name=getattr(bpy.context.scene, 'replace_object_name', True))
            return True
        except Exception as e:
            print(f"随机替换对象 {target_obj.name} 时出错: {str(e)}")
            return False
    
    def perform_replacement(self, target_obj, replacement_data, replace_name=True):
        """执行实际的替换操作"""
        try:
            print(f"开始替换对象: {target_obj.name}")
            
            # 验证替换数据
            if not replacement_data or 'mesh_data' not in replacement_data:
                print(f"替换数据无效: {replacement_data}")
                return False
            
            # 保存目标对象的原始属性
            original_name = target_obj.name
            original_location = target_obj.location.copy()
            original_rotation = target_obj.rotation_euler.copy()
            original_scale = target_obj.scale.copy()
            original_parent = target_obj.parent
            original_matrix_world = target_obj.matrix_world.copy()
            
            # 创建完全独立的新对象来避免数据冲突
            try:
                # 创建新的网格数据 - 深度复制
                new_mesh = replacement_data['mesh_data'].copy()
                
                # 确保网格数据完全独立
                if new_mesh.users > 1:
                    new_mesh = new_mesh.copy()
                
                # 创建新的材质列表 - 使用完全独立的方法
                new_materials = []
                if 'materials' in replacement_data and replacement_data['materials']:
                    for mat in replacement_data['materials']:
                        if mat:
                            independent_mat = self.create_fully_independent_material(mat)
                            if independent_mat:
                                new_materials.append(independent_mat)
                
                # 清除目标对象的材质
                target_obj.data.materials.clear()
                
                # 保存旧网格数据用于清理
                old_mesh = target_obj.data
                
                # 替换网格数据
                target_obj.data = new_mesh
                
                # 应用新材质
                for mat in new_materials:
                    target_obj.data.materials.append(mat)
                
                # 清理旧网格数据（如果不再被使用）
                if old_mesh.users == 0:
                    bpy.data.meshes.remove(old_mesh)
                
                print(f"网格和材质数据替换成功: {original_name}")
                    
            except Exception as e:
                print(f"替换网格数据时出错: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
            
            # 恢复原始变换
            target_obj.location = original_location
            target_obj.rotation_euler = original_rotation
            target_obj.scale = original_scale
            
            # 恢复父级关系
            if original_parent:
                target_obj.parent = original_parent
            
            # 应用世界矩阵以保持视觉位置
            target_obj.matrix_world = original_matrix_world
            
            # 强制更新对象以确保数据一致性
            try:
                target_obj.update_tag()
                bpy.context.view_layer.update()
                
                # 强制刷新Blender的数据结构
                bpy.context.scene.frame_set(bpy.context.scene.frame_current)
                
            except Exception as e:
                print(f"更新对象时出错: {str(e)}")
            
            # 验证替换后对象的独立性
            if self.verify_object_independence(target_obj):
                print(f"对象数据独立性验证通过: {original_name}")
            else:
                print(f"警告: 对象数据独立性验证失败: {original_name}")
            
            # 还原自动重命名功能
            if replace_name:
                try:
                    # 使用更安全的名称替换方法
                    new_name = self.get_safe_object_name(replacement_data['name'])
                    target_obj.name = new_name
                    print(f"成功替换对象: {original_name} -> {new_name}")
                except Exception as e:
                    print(f"替换名称时出错: {str(e)}")
                    print(f"保持原名称: {original_name}")
            else:
                print(f"成功替换对象: {original_name} (保持原名称)")
            
            # 添加额外的安全检查
            try:
                # 验证对象是否仍然有效
                if target_obj.name in bpy.data.objects:
                    print(f"对象验证通过: {target_obj.name} 仍然存在于场景中")
                else:
                    print(f"警告: 对象 {target_obj.name} 在替换后丢失")
                    return False
            except Exception as e:
                print(f"对象验证时出错: {str(e)}")
                return False
            
            return True
            
        except Exception as e:
            print(f"执行替换操作时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

class CharacterPartReplacerPanel(bpy.types.Panel):
    """角色部件替换面板"""
    bl_label = "角色部件替换"
    bl_idname = "VIEW3D_PT_character_part_replacer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = '角色工具'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 源文件路径设置
        box = layout.box()
        box.prop(scene, "source_file_path", text="源文件路径")
        box.prop(scene, "replace_object_name", text="同时替换对象名称")
        row = box.row()
        row.operator("object.load_source_objects", text="加载源文件", icon='FILE_REFRESH')
        
        # 检查是否已加载源文件
        global _character_replacer_instance
        if _character_replacer_instance:
            row = box.row()
            row.operator("object.replace_all_parts", text="替换所有部件", icon='AUTOMERGE_ON')
            
            # 添加上一个和下一个按钮
            row = box.row()
            row.operator("object.replace_selected_previous", text="上一个", icon='TRIA_LEFT')
            row.operator("object.replace_selected_next", text="下一个", icon='TRIA_RIGHT')
            row.operator("object.replace_selected_parts", text="随机", icon='ARROW_LEFTRIGHT')
            

        else:
            row = box.row()
            row.label(text="请先加载源文件", icon='INFO')
        

        
        # 帮助信息
        box = layout.box()
        box.label(text="使用说明", icon='HELP')
        box.label(text="1. 选择包含替换部件的.blend文件")
        box.label(text="2. 点击'加载源文件'")
        box.label(text="3. 选择要替换的对象")
        box.label(text="4. 使用替换按钮:")
        box.label(text="   - 上一个/下一个: 循环切换")
        box.label(text="   - 随机: 随机选择")
        box.label(text="5. 可选择是否自动替换对象名称")
        box.label(text="支持性别: male/female/m/f")
        box.label(text="支持部位: Upper/Lower/Hair/Nose/Eyes/Mouse/Bottom/Top/Feet")
        box.label(text="注意: 多次加载同一文件会自动清理旧数据")

class LoadSourceObjectsOperator(bpy.types.Operator):
    """加载源文件中的对象"""
    bl_idname = "object.load_source_objects"
    bl_label = "加载源文件对象"
    
    def execute(self, context):
        source_path = context.scene.source_file_path
        if not source_path or not os.path.exists(source_path):
            self.report({'ERROR'}, "请选择有效的源文件路径")
            return {'CANCELLED'}
        
        try:
            global _character_replacer_instance
            
            # 检查是否已经加载了相同的源文件
            if _character_replacer_instance and _character_replacer_instance.source_file_path == source_path:
                self.report({'INFO'}, "源文件已经加载，无需重复加载")
                return {'FINISHED'}
            
            # 清理旧的替换器实例
            if _character_replacer_instance:
                print("检测到重复加载，清理旧实例...")
                _character_replacer_instance.cleanup()
                _character_replacer_instance = None
            
            # 创建新的替换器实例
            replacer = CharacterPartReplacer(source_path)
            
            # 检查是否成功加载了对象
            if not replacer.source_objects:
                self.report({'WARNING'}, "源文件中未找到匹配的对象")
                return {'CANCELLED'}
            
            # 保存到全局变量中
            _character_replacer_instance = replacer
            
            # 生成统计信息
            total_objects = 0
            for (gender, body_part), objects in replacer.source_objects.items():
                count = len(objects)
                total_objects += count
                # 打印详细信息用于调试
                print(f"源文件中的对象组: {gender} {body_part}")
                for obj_data in objects:
                    print(f"  - {obj_data['name']}")
            
            self.report({'INFO'}, f"成功加载源文件，找到 {len(replacer.source_objects)} 个部件类型，共 {total_objects} 个对象")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"加载源文件失败: {str(e)}")
            return {'CANCELLED'}

class ReplaceSelectedPartsOperator(bpy.types.Operator):
    """随机替换选中的部件"""
    bl_idname = "object.replace_selected_parts"
    bl_label = "随机替换选中部件"
    
    def execute(self, context):
        global _character_replacer_instance
        if not _character_replacer_instance:
            self.report({'ERROR'}, "请先加载源文件")
            return {'CANCELLED'}
        
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "请选择要替换的对象")
            return {'CANCELLED'}
        
        replacer = _character_replacer_instance
        success_count = 0
        total_count = len([obj for obj in selected_objects if obj.type == 'MESH'])
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                try:
                    print(f"尝试替换对象: {obj.name}")
                    if replacer.replace_object_random(obj):
                        success_count += 1
                        print(f"成功替换对象: {obj.name}")
                    else:
                        print(f"替换对象失败: {obj.name}")
                except Exception as e:
                    print(f"替换对象 {obj.name} 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
        
        if success_count == total_count:
            self.report({'INFO'}, f"成功随机替换所有 {success_count} 个对象")
        else:
            self.report({'WARNING'}, f"成功随机替换 {success_count}/{total_count} 个对象")
        
        return {'FINISHED'}

class ReplaceAllPartsOperator(bpy.types.Operator):
    """替换场景中所有匹配的部件"""
    bl_idname = "object.replace_all_parts"
    bl_label = "替换所有部件"
    
    def execute(self, context):
        global _character_replacer_instance
        if not _character_replacer_instance:
            self.report({'ERROR'}, "请先加载源文件")
            return {'CANCELLED'}
        
        replacer = _character_replacer_instance
        success_count = 0
        total_count = 0
        
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                keywords = replacer.extract_keywords(obj.name)
                if keywords:
                    total_count += 1
                    try:
                        if replacer.replace_object(obj):
                            success_count += 1
                    except Exception as e:
                        print(f"替换对象 {obj.name} 时出错: {str(e)}")
        
        if total_count == 0:
            self.report({'WARNING'}, "场景中未找到匹配的对象")
        elif success_count == total_count:
            self.report({'INFO'}, f"成功替换所有 {success_count} 个对象")
        else:
            self.report({'WARNING'}, f"成功替换 {success_count}/{total_count} 个对象")
        
        return {'FINISHED'}

class ReplaceSelectedPreviousOperator(bpy.types.Operator):
    """替换选中的部件为上一个"""
    bl_idname = "object.replace_selected_previous"
    bl_label = "替换选中部件(上一个)"
    
    def execute(self, context):
        global _character_replacer_instance
        if not _character_replacer_instance:
            self.report({'ERROR'}, "请先加载源文件")
            return {'CANCELLED'}
        
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "请选择要替换的对象")
            return {'CANCELLED'}
        
        replacer = _character_replacer_instance
        success_count = 0
        total_count = len([obj for obj in selected_objects if obj.type == 'MESH'])
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                try:
                    if replacer.replace_object(obj, direction=-1):  # 上一个
                        success_count += 1
                except Exception as e:
                    print(f"替换对象 {obj.name} 时出错: {str(e)}")
        
        if success_count == total_count:
            self.report({'INFO'}, f"成功替换所有 {success_count} 个对象(上一个)")
        else:
            self.report({'WARNING'}, f"成功替换 {success_count}/{total_count} 个对象(上一个)")
        
        return {'FINISHED'}

class ReplaceSelectedNextOperator(bpy.types.Operator):
    """替换选中的部件为下一个"""
    bl_idname = "object.replace_selected_next"
    bl_label = "替换选中部件(下一个)"
    
    def execute(self, context):
        global _character_replacer_instance
        if not _character_replacer_instance:
            self.report({'ERROR'}, "请先加载源文件")
            return {'CANCELLED'}
        
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "请先选择要替换的对象")
            return {'CANCELLED'}
        
        replacer = _character_replacer_instance
        success_count = 0
        total_count = len([obj for obj in selected_objects if obj.type == 'MESH'])
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                try:
                    if replacer.replace_object(obj, direction=1):  # 下一个
                        success_count += 1
                except Exception as e:
                    print(f"替换对象 {obj.name} 时出错: {str(e)}")
        
        if success_count == total_count:
            self.report({'INFO'}, f"成功替换所有 {success_count} 个对象(下一个)")
        else:
            self.report({'WARNING'}, f"成功替换 {success_count}/{total_count} 个对象(下一个)")
        
        return {'FINISHED'}

# 自定义属性
class CharacterReplacerProperties(bpy.types.PropertyGroup):
    pass

# 全局变量来存储替换器实例
_character_replacer_instance = None

def register():
    bpy.utils.register_class(CharacterPartReplacerPanel)
    bpy.utils.register_class(LoadSourceObjectsOperator)
    bpy.utils.register_class(ReplaceSelectedPartsOperator)
    bpy.utils.register_class(ReplaceSelectedPreviousOperator)
    bpy.utils.register_class(ReplaceSelectedNextOperator)
    bpy.utils.register_class(ReplaceAllPartsOperator)
    bpy.utils.register_class(CharacterReplacerProperties)
    
    # 注册场景属性
    bpy.types.Scene.source_file_path = bpy.props.StringProperty(
        name="源文件路径",
        description="选择包含替换部件的Blender文件",
        default="",
        maxlen=1024,
        subtype='FILE_PATH'
    )
    
    bpy.types.Scene.replace_object_name = bpy.props.BoolProperty(
        name="替换对象名称",
        description="是否在替换时同时替换对象名称",
        default=True
    )

def unregister():
    bpy.utils.unregister_class(CharacterPartReplacerPanel)
    bpy.utils.unregister_class(LoadSourceObjectsOperator)
    bpy.utils.unregister_class(ReplaceSelectedPartsOperator)
    bpy.utils.unregister_class(ReplaceSelectedPreviousOperator)
    bpy.utils.unregister_class(ReplaceSelectedNextOperator)
    bpy.utils.unregister_class(ReplaceAllPartsOperator)
    bpy.utils.unregister_class(CharacterReplacerProperties)
    
    # 删除场景属性
    del bpy.types.Scene.source_file_path
    del bpy.types.Scene.replace_object_name
    
    # 清理全局变量
    global _character_replacer_instance
    if _character_replacer_instance:
        _character_replacer_instance.cleanup()
        _character_replacer_instance = None

# ============================================================================
# 注册和注销
# ============================================================================

# 注意：这些函数已经在上面定义过了，这里不需要重复定义

if __name__ == "__main__":
    register()
