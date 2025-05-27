import bpy
import os

def load_textures_to_dict(texture_dir, ignore_fields=None):
    """加载目录中的所有纹理到字典，支持任意图片格式"""
    texture_mapping = {}
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tif', '.tiff', '.exr', '.hdr')

    try:
        # 使用Blender的路径处理函数
        texture_dir = bpy.path.abspath(texture_dir)
        
        # 如果路径是相对路径，尝试解析
        if not os.path.isabs(texture_dir):
            blend_file_path = bpy.data.filepath
            if blend_file_path:
                blend_dir = os.path.dirname(blend_file_path)
                texture_dir = os.path.join(blend_dir, texture_dir)
        
        texture_dir = os.path.normpath(texture_dir)
        
        if not os.path.exists(texture_dir):
            print(f"ERROR: Texture directory does not exist: {texture_dir}")
            return texture_mapping

        # 首先收集所有文件
        all_files = []
        for dirpath, _, filenames in os.walk(texture_dir):
            for filename in filenames:
                if filename.lower().endswith(supported_formats):
                    all_files.append((dirpath, filename))

        # 批量处理文件
        for dirpath, filename in all_files:
            original_name = os.path.splitext(filename)[0]
            material_name = original_name.lower().strip()
            
            # 如果提供了忽略字段，则从纹理名称中移除
            if ignore_fields:
                for field in ignore_fields:
                    if field.strip():
                        material_name = material_name.replace(field.lower().strip(), "")
            
            texture_path = os.path.abspath(os.path.join(dirpath, filename))
            texture_mapping[material_name] = texture_path

        return texture_mapping
        
    except Exception as e:
        print(f"Error processing texture directory: {str(e)}")
        return texture_mapping

def apply_texture_to_material(mat, image_path):
    """应用纹理到材质"""
    try:
        image_path = os.path.abspath(image_path)  # Ensure the path is absolute
        image = bpy.data.images.load(image_path)

        # Set alpha mode for TGA images
        if image_path.lower().endswith('.tga'):
            image.alpha_mode = 'CHANNEL_PACKED'  # Set alpha mode to Channel Packed

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 清除默认节点
        nodes.clear()

        # 添加必要节点
        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = image
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        output_node = nodes.new(type='ShaderNodeOutputMaterial')

        # 设置节点位置（可选）
        tex_node.location = (-300, 300)
        bsdf_node.location = (0, 300)
        output_node.location = (200, 300)

        # 连接节点
        links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        # 打印连接信息
        print(f"连接: {tex_node.outputs['Color']} -> {bsdf_node.inputs['Base Color']}")
        print(f"连接: {bsdf_node.outputs['BSDF']} -> {output_node.inputs['Surface']}")

    except Exception as e:
        print(f"无法加载纹理 '{image_path}': {e}")

def apply_texture(obj, image_path):
    """应用纹理到对象的每个材质"""
    try:
        image_path = os.path.abspath(image_path)  # Ensure the path is absolute
        image = bpy.data.images.load(image_path)

        # Set alpha mode for TGA images
        if image_path.lower().endswith('.tga'):
            image.alpha_mode = 'CHANNEL_PACKED'  # Set alpha mode to Channel Packed

        for mat_slot in obj.material_slots:
            mat = mat_slot.material
            if not mat:
                continue

            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

            # 清除默认节点
            nodes.clear()

            # 添加必要节点
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.image = image
            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            output_node = nodes.new(type='ShaderNodeOutputMaterial')

            # 设置节点位置（可选）
            tex_node.location = (-300, 300)
            bsdf_node.location = (0, 300)
            output_node.location = (200, 300)

            # 连接节点
            links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

            # 打印连接信息
            print(f"连接: {tex_node.outputs['Color']} -> {bsdf_node.inputs['Base Color']}")
            print(f"连接: {bsdf_node.outputs['BSDF']} -> {output_node.inputs['Surface']}")

    except Exception as e:
        print(f"无法加载纹理 '{image_path}': {e}")

class ApplyTextureOperator(bpy.types.Operator):
    """根据完整名称匹配并应用纹理"""
    bl_idname = "object.apply_texture_operator"
    bl_label = "Apply Texture"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = os.path.abspath(bpy.context.scene.texture_dir)  # Ensure the directory is absolute
        ignore_fields_input = bpy.context.scene.ignore_fields_input.split(',')
        ignore_fields = [field.lower().strip() for field in ignore_fields_input if field.strip()]
        
        # 使用忽略字段加载纹理
        texture_mapping = load_textures_to_dict(texture_dir, ignore_fields)
        selected_objects = bpy.context.selected_objects

        for obj in selected_objects:
            original_name = obj.name.lower()
            processed_name = original_name
            
            # 从对象名称中移除忽略字段
            for field in ignore_fields:
                processed_name = processed_name.replace(field, "")
                
            if processed_name in texture_mapping:
                apply_texture(obj, texture_mapping[processed_name])
                print(f"已为 {obj.name} 应用纹理: {texture_mapping[processed_name]}")
            else:
                print(f"未找到 {obj.name} 的纹理")

        return {'FINISHED'}

class ApplyTextureToSelectedObjects(bpy.types.Operator):
    """忽略部分名称匹配并应用纹理"""
    bl_idname = "object.apply_texture_to_selected_objects"
    bl_label = "Apply Texture to Selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = bpy.context.scene.texture_dir
        ignore_fields_input = bpy.context.scene.ignore_fields_input.split(',')
        ignore_fields = [field.lower().strip() for field in ignore_fields_input if field.strip()]
        
        # 使用忽略字段加载纹理
        texture_mapping = load_textures_to_dict(os.path.abspath(texture_dir), ignore_fields)

        for obj in bpy.context.selected_objects:
            original_name = obj.name.lower()
            processed_name = original_name
            
            # 从对象名称中移除忽略字段
            for field in ignore_fields:
                processed_name = processed_name.replace(field, "")

            if processed_name in texture_mapping:
                apply_texture(obj, texture_mapping[processed_name])
                print(f"已为 {obj.name} 应用纹理: {texture_mapping[processed_name]}")
            else:
                print(f"未找到 {obj.name} 的纹理")

        return {'FINISHED'}

class ApplyTextureToMaterialsOperator(bpy.types.Operator):
    """根据材质名称为所选物体的所有材质应用纹理"""
    bl_idname = "object.apply_texture_to_materials"
    bl_label = "Apply Texture to Materials"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = bpy.context.scene.texture_dir
        if not texture_dir:
            self.report({'ERROR'}, "Texture directory is not set!")
            return {'CANCELLED'}
            
        try:
            texture_dir = bpy.path.abspath(texture_dir)
            if not os.path.isabs(texture_dir):
                blend_file_path = bpy.data.filepath
                if blend_file_path:
                    blend_dir = os.path.dirname(blend_file_path)
                    texture_dir = os.path.join(blend_dir, texture_dir)
            texture_dir = os.path.normpath(texture_dir)
            
        except Exception as e:
            self.report({'ERROR'}, f"Invalid texture directory path: {str(e)}")
            return {'CANCELLED'}
            
        ignore_fields_input = bpy.context.scene.ignore_fields_input.split(',')
        ignore_fields = [field.lower().strip() for field in ignore_fields_input if field.strip()]
        
        # 使用忽略字段加载纹理
        texture_mapping = load_textures_to_dict(texture_dir, ignore_fields)
        
        if not texture_mapping:
            self.report({'WARNING'}, "No texture files found in the specified directory!")
            return {'CANCELLED'}
            
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected!")
            return {'CANCELLED'}

        # 收集所有独立的材质
        materials = set()
        for obj in selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        materials.add(mat_slot.material)

        if not materials:
            self.report({'WARNING'}, "No materials found in selected objects!")
            return {'CANCELLED'}

        # 批量处理材质
        matched_count = 0
        for mat in materials:
            original_name = mat.name.lower().strip()
            processed_name = original_name
            
            # 从材质名称中移除忽略字段
            for field in ignore_fields:
                processed_name = processed_name.replace(field, "")
                
            if processed_name in texture_mapping:
                apply_texture_to_material(mat, texture_mapping[processed_name])
                matched_count += 1

        if matched_count > 0:
            self.report({'INFO'}, f"Successfully applied textures to {matched_count} materials")
        else:
            self.report({'WARNING'}, "No matching textures found for any materials")

        return {'FINISHED'}

class ApplyTextureByParentOperator(bpy.types.Operator):
    """根据顶级父级名称查找并应用纹理"""
    bl_idname = "object.apply_texture_by_parent"
    bl_label = "Apply Texture By Parent"
    bl_options = {'REGISTER', 'UNDO'}
    
    def get_top_parent(self, obj):
        """获取对象的顶级父级"""
        if obj.parent is None:
            return obj
        else:
            return self.get_top_parent(obj.parent)
    
    def execute(self, context):
        texture_dir = bpy.context.scene.texture_dir
        ignore_fields_input = bpy.context.scene.ignore_fields_input.split(',')
        ignore_fields = [field.lower().strip() for field in ignore_fields_input if field.strip()]
        
        # 使用忽略字段加载纹理
        texture_mapping = load_textures_to_dict(os.path.abspath(texture_dir), ignore_fields)
        selected_objects = bpy.context.selected_objects
        
        # 按顶级父级对象分组
        parent_groups = {}
        for obj in selected_objects:
            top_parent = self.get_top_parent(obj)
            if top_parent not in parent_groups:
                parent_groups[top_parent] = []
            parent_groups[top_parent].append(obj)
        
        # 为每个顶级父级查找纹理并应用到其所有子对象
        for parent, objects in parent_groups.items():
            original_name = parent.name.lower()
            processed_name = original_name
            
            # 从父级名称中移除忽略字段
            for field in ignore_fields:
                processed_name = processed_name.replace(field, "")
            
            if processed_name in texture_mapping:
                for obj in objects:
                    apply_texture(obj, texture_mapping[processed_name])
                print(f"已根据父级 '{parent.name}' 为 {len(objects)} 个对象应用纹理: {texture_mapping[processed_name]}")
            else:
                print(f"未找到父级 '{parent.name}' 的纹理")
        
        return {'FINISHED'}

class ApplyTextureByObjectNameOperator(bpy.types.Operator):
    """根据物体名称匹配并应用纹理"""
    bl_idname = "object.apply_texture_by_object_name"
    bl_label = "按物体名称匹配"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = os.path.abspath(bpy.context.scene.texture_dir)
        if not os.path.exists(texture_dir):
            self.report({'ERROR'}, f"贴图目录不存在: {texture_dir}")
            return {'CANCELLED'}

        # 获取所有贴图文件
        texture_files = []
        for root, _, files in os.walk(texture_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tif', '.tiff', '.exr', '.hdr')):
                    texture_files.append((file, os.path.join(root, file)))

        # 遍历选中的物体
        matched_count = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            obj_name = obj.name.lower()
            # 查找包含物体名称的贴图
            for tex_name, tex_path in texture_files:
                tex_name_no_ext = os.path.splitext(tex_name)[0].lower()
                if obj_name in tex_name_no_ext:
                    # 应用贴图到物体的所有材质
                    for mat_slot in obj.material_slots:
                        if mat_slot.material:
                            apply_texture_to_material(mat_slot.material, tex_path)
                            matched_count += 1
                            print(f"已为物体 '{obj.name}' 的材质 '{mat_slot.material.name}' 应用贴图: {tex_path}")
                    break  # 找到一个匹配的贴图后就停止搜索

        if matched_count > 0:
            self.report({'INFO'}, f"成功应用了 {matched_count} 个贴图")
        else:
            self.report({'WARNING'}, "没有找到匹配的贴图")

        return {'FINISHED'}

def split_into_words(text):
    """将文本分割成单词，处理各种分隔符和数字"""
    # 替换常见的分隔符为空格
    separators = ['_', '-', '.', ',', '|', '/', '\\', '(', ')', '[', ']', '{', '}']
    for sep in separators:
        text = text.replace(sep, ' ')
    
    # 在数字和字母之间添加空格
    import re
    text = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', text)  # 数字后跟字母
    text = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', text)  # 字母后跟数字
    
    # 分割单词并过滤空字符串
    words = [word.lower() for word in text.split() if word.strip()]
    return words

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度"""
    # 移除文件扩展名
    str1 = os.path.splitext(str1)[0].lower()
    str2 = os.path.splitext(str2)[0].lower()
    
    # 1. 检查完全匹配
    if str1 == str2:
        return 1.0
    
    # 2. 检查包含关系
    if str1 in str2 or str2 in str1:
        # 如果物体名称完全包含在贴图名称中
        if str1 in str2:
            # 检查是否包含材质相关词
            material_terms = ['defaultmaterial', 'basecolor', 'diffuse', 'normal', 'roughness', 'metallic', 'ao']
            if not any(term in str2 for term in material_terms):
                return 0.9
            return 0.8
        return 0.7
    
    # 3. 检查单词匹配
    words1 = split_into_words(str1)
    words2 = split_into_words(str2)
    
    if not words1 or not words2:
        return 0
    
    # 计算共同单词
    common_words = set(words1) & set(words2)
    if not common_words:
        return 0
    
    # 计算基础相似度
    similarity = len(common_words) / max(len(words1), len(words2))
    
    # 如果共同单词数量超过物体名称单词数量的一半，提高相似度
    if len(common_words) >= len(words1) * 0.5:
        similarity += 0.2
    
    # 如果贴图名称包含材质相关词，降低相似度
    material_terms = ['defaultmaterial', 'basecolor', 'diffuse', 'normal', 'roughness', 'metallic', 'ao']
    if any(term in str2 for term in material_terms):
        similarity *= 0.8
    
    return min(similarity, 1.0)

class ApplyTextureBySimilarityOperator(bpy.types.Operator):
    """根据名称相似度匹配并应用纹理"""
    bl_idname = "object.apply_texture_by_similarity"
    bl_label = "按相似度匹配"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = os.path.abspath(bpy.context.scene.texture_dir)
        if not os.path.exists(texture_dir):
            self.report({'ERROR'}, f"贴图目录不存在: {texture_dir}")
            return {'CANCELLED'}

        # 获取所有贴图文件
        texture_files = []
        for root, _, files in os.walk(texture_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tif', '.tiff', '.exr', '.hdr')):
                    texture_files.append((file, os.path.join(root, file)))

        if not texture_files:
            self.report({'WARNING'}, "贴图目录中没有找到支持的贴图文件")
            return {'CANCELLED'}

        # 遍历选中的物体
        matched_count = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            obj_name = obj.name.lower()
            best_match = None
            best_similarity = 0

            # 计算与每个贴图的相似度
            for tex_name, tex_path in texture_files:
                similarity = calculate_similarity(obj_name, tex_name)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = (tex_name, tex_path)

            # 如果找到匹配度超过阈值的贴图，应用它
            if best_match and best_similarity > 0.3:  # 设置相似度阈值
                tex_name, tex_path = best_match
                # 应用贴图到物体的所有材质
                for mat_slot in obj.material_slots:
                    if mat_slot.material:
                        apply_texture_to_material(mat_slot.material, tex_path)
                        matched_count += 1
                        print(f"已为物体 '{obj.name}' 的材质 '{mat_slot.material.name}' 应用贴图: {tex_path} (相似度: {best_similarity:.2f})")
            else:
                print(f"未找到与物体 '{obj.name}' 匹配的贴图")

        if matched_count > 0:
            self.report({'INFO'}, f"成功应用了 {matched_count} 个贴图")
        else:
            self.report({'WARNING'}, "没有找到匹配的贴图")

        return {'FINISHED'}

def register():
    bpy.utils.register_class(ApplyTextureOperator)
    bpy.utils.register_class(ApplyTextureToSelectedObjects)
    bpy.utils.register_class(ApplyTextureToMaterialsOperator)
    bpy.utils.register_class(ApplyTextureByParentOperator)
    bpy.utils.register_class(ApplyTextureByObjectNameOperator)
    bpy.utils.register_class(ApplyTextureBySimilarityOperator)

    bpy.types.Scene.texture_dir = bpy.props.StringProperty(
        name="Texture Directory",
        description="Directory where the texture files are located",
        default="",
        subtype='DIR_PATH'
    )
    bpy.types.Scene.ignore_fields_input = bpy.props.StringProperty(
        name="Ignore Fields",
        description="Comma-separated list of fields to ignore",
        default="_Upper, _lower, ,mod_,_clothes"
    )

def unregister():
    bpy.utils.unregister_class(ApplyTextureOperator)
    bpy.utils.unregister_class(ApplyTextureToSelectedObjects)
    bpy.utils.unregister_class(ApplyTextureToMaterialsOperator)
    bpy.utils.unregister_class(ApplyTextureByParentOperator)
    bpy.utils.unregister_class(ApplyTextureByObjectNameOperator)
    bpy.utils.unregister_class(ApplyTextureBySimilarityOperator)

    del bpy.types.Scene.texture_dir
    del bpy.types.Scene.ignore_fields_input