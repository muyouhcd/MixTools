import bpy
import os

def load_textures_to_dict(texture_dir):
    """加载目录中的所有纹理到字典，支持任意图片格式"""
    texture_mapping = {}
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tga', '.tif', '.tiff', '.exr', '.hdr')

    for dirpath, _, filenames in os.walk(texture_dir):
        for filename in filenames:
            if filename.lower().endswith(supported_formats):
                material_name = os.path.splitext(filename)[0].lower()
                texture_path = os.path.join(dirpath, filename)
                texture_mapping[material_name] = texture_path

    return texture_mapping

def apply_texture(obj, image_path):
    """应用纹理到对象"""
    try:
        image = bpy.data.images.load(image_path)

        # 创建或获取材质
        if not obj.data.materials:
            mat = bpy.data.materials.new(name=f"{obj.name}_Material")
            obj.data.materials.append(mat)
        else:
            mat = obj.data.materials[0]

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
        texture_dir = bpy.context.scene.texture_dir
        texture_mapping = load_textures_to_dict(os.path.abspath(texture_dir))
        selected_objects = bpy.context.selected_objects

        for obj in selected_objects:
            obj_name = obj.name.lower()
            if obj_name in texture_mapping:
                apply_texture(obj, texture_mapping[obj_name])
                print(f"已为 {obj.name} 应用纹理: {texture_mapping[obj_name]}")
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
        texture_mapping = load_textures_to_dict(os.path.abspath(texture_dir))

        for obj in bpy.context.selected_objects:
            object_name = obj.name.lower()
            for field in ignore_fields_input:
                object_name = object_name.replace(field.lower(), "")

            if object_name in texture_mapping:
                apply_texture(obj, texture_mapping[object_name])
                print(f"已为 {obj.name} 应用纹理: {texture_mapping[object_name]}")
            else:
                print(f"未找到 {obj.name} 的纹理")

        return {'FINISHED'}

class ApplyTextureByMaterialNameRecursiveOperator(bpy.types.Operator):
    """通过材质名称匹配并递归应用纹理"""
    bl_idname = "object.apply_texture_by_material_name_recursive"
    bl_label = "Apply Texture by Material Name (Recursive)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        texture_dir = bpy.context.scene.texture_dir
        texture_mapping = load_textures_to_dict(os.path.abspath(texture_dir))
        selected_objects = bpy.context.selected_objects

        # 调试输出：打印纹理字典
        print("纹理字典内容:")
        for key, value in texture_mapping.items():
            print(f"{key}: {value}")

        for obj in selected_objects:
            self.apply_texture_recursively(obj, texture_mapping)

        return {'FINISHED'}

    def apply_texture_recursively(self, obj, texture_mapping):
        """递归应用纹理到物体及其所有子物体"""
        if obj.type == 'MESH' and obj.data.materials:
            for mat in obj.data.materials:
                if mat and mat.name:
                    material_name = mat.name.lower()
                    
                    # 严格的全名比较
                    if material_name in texture_mapping:
                        apply_texture(obj, texture_mapping[material_name])
                        print(f"已为 '{obj.name}' ({mat.name}) 应用纹理: {texture_mapping[material_name]}")
                    else:
                        print(f"未找到匹配的纹理: {material_name}")

        for child in obj.children:
            self.apply_texture_recursively(child, texture_mapping)

def register():
    bpy.utils.register_class(ApplyTextureOperator)
    bpy.utils.register_class(ApplyTextureToSelectedObjects)
    bpy.utils.register_class(ApplyTextureByMaterialNameRecursiveOperator)

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
    bpy.utils.unregister_class(ApplyTextureByMaterialNameRecursiveOperator)

    del bpy.types.Scene.texture_dir
    del bpy.types.Scene.ignore_fields_input