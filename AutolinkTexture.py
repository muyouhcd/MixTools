import bpy
import os

class ApplyTextureOperator(bpy.types.Operator):
    """Apply Texture to Selected Objects"""
    bl_idname = "object.apply_texture_operator"
    bl_label = "Apply Texture"
    bl_options = {'REGISTER', 'UNDO'}
    
    texture_dir: bpy.props.StringProperty(
        name="Texture Directory",
        description="Directory where the texture files are located",
        default="",
        subtype='DIR_PATH'
    ) # type: ignore

    def execute(self, context):
        # 获取从UI中输入的贴图目录
        texture_dir = bpy.context.scene.texture_dir
        
        # 获取贴图文件所在目录的绝对路径
        abs_texture_dir = os.path.abspath(texture_dir)
        print(f"Texture Directory (absolute): {abs_texture_dir}")

        # 获取选中的物体
        selected_objects = bpy.context.selected_objects

        # 存储已处理过的纹理文件
        processed_textures = {}

        for obj in selected_objects:
            self.process_object_and_children(obj, abs_texture_dir, processed_textures)

        return {'FINISHED'}
    
    def process_object_and_children(self, obj, texture_dir, processed_textures):
        # 如果物体类型是空物体，忽略
        if obj.type == 'EMPTY':
            return
        
        # 确保该对象有data属性，比如Mesh类型对象
        if not hasattr(obj.data, 'materials'):
            self.report({'WARNING'}, f"{obj.name} is not a Mesh object or has no data, skipping.")
            return
        
        obj_name = obj.name.lower()  # 将对象名称转换为小写

        found_texture = False
        while obj_name:
            # 根据物体名称构建贴图文件路径
            texture_path = os.path.join(texture_dir, f"{obj_name}_texture.png").lower()
            abs_texture_path = os.path.abspath(texture_path).lower()
            
            # 打印调试信息，确认文件路径
            print(f"Checking for texture: {abs_texture_path}")

            # 检查贴图文件是否存在
            if os.path.exists(abs_texture_path):
                if abs_texture_path in processed_textures:
                    texture = processed_textures[abs_texture_path]
                else:
                    texture = bpy.data.images.load(abs_texture_path)
                    processed_textures[abs_texture_path] = texture
                
                self.apply_texture(obj, texture)
                found_texture = True
                break # 找到纹理文件，跳出循环

            # 如果没有找到，则去掉名称的最后一个字符再试
            obj_name = obj_name[:-1]

        if not found_texture:
            self.report({'WARNING'}, f"Texture file for {obj.name} not found in {texture_dir}")

        # 递归处理子物体
        for child in obj.children:
            self.process_object_and_children(child, texture_dir, processed_textures)

    def apply_texture(self, obj, texture):
        """辅助函数：应用纹理"""
        # 创建新的材质
        mat = bpy.data.materials.new(name=f"{obj.name}_Material")

        # 将材质分配给物体
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        # 创建材质节点树
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 清除默认的节点
        for node in nodes:
            nodes.remove(node)

        # 添加纹理节点
        texture_node = nodes.new(type='ShaderNodeTexImage')
        texture_node.image = texture
        texture_node.interpolation = 'Closest'

        # 添加BSDF节点
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')

        # 添加输出节点
        output_node = nodes.new(type='ShaderNodeOutputMaterial')

        # 连接节点
        links.new(texture_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

def register():
    bpy.utils.register_class(ApplyTextureOperator)
    bpy.types.Scene.texture_dir = bpy.props.StringProperty(
        name="Texture Directory",
        description="Directory where the texture files are located",
        default="",
        subtype='DIR_PATH'
    )

def unregister():
    bpy.utils.unregister_class(ApplyTextureOperator)
    del bpy.types.Scene.texture_dir