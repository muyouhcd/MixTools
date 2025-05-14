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

def register():
    bpy.utils.register_class(ApplyTextureOperator)
    bpy.utils.register_class(ApplyTextureToSelectedObjects)
    bpy.utils.register_class(ApplyTextureToMaterialsOperator)
    bpy.utils.register_class(ApplyTextureByParentOperator)

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

    del bpy.types.Scene.texture_dir
    del bpy.types.Scene.ignore_fields_input