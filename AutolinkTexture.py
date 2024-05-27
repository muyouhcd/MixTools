import bpy
import os
import re

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
    )

    def execute(self, context):
        # 获取从UI中输入的贴图目录
        texture_dir = bpy.context.scene.texture_dir
        
        # 获取贴图文件所在目录的绝对路径
        abs_texture_dir = os.path.abspath(texture_dir)
        print(f"Texture Directory (absolute): {abs_texture_dir}")

        # 获取选中的物体
        selected_objects = bpy.context.selected_objects
        
        for obj in selected_objects:
            # 确保该对象有data属性，比如Mesh类型对象
            if not hasattr(obj.data, 'materials'):
                self.report({'WARNING'}, f"{obj.name} is not a Mesh object or has no data, skipping.")
                continue

            # 获取物体名称
            obj_name = obj.name

            # 根据物体名称构建贴图文件路径
            texture_path = os.path.join(abs_texture_dir, f"{obj_name}_texture.png")

            # 打印调试信息，确认文件路径
            abs_texture_path = os.path.abspath(texture_path)
            print(f"Checking for texture: {abs_texture_path}")

            found_texture = False

            # 检查贴图文件是否存在
            if os.path.exists(abs_texture_path):
                self.apply_texture(obj, abs_texture_path)
                found_texture = True
            else:
                # 尝试模糊查找
                # 使用正则表达式去除序号后缀
                base_name = re.sub(r'(_\d+|.\d+)$', '', obj_name)
                fuzzy_texture_path = os.path.join(abs_texture_dir, f"{base_name}_texture.png")
                abs_fuzzy_texture_path = os.path.abspath(fuzzy_texture_path)
                print(f"Attempting fuzzy search for texture: {abs_fuzzy_texture_path}")
                
                # 再次检查去除序号后缀的路径
                if os.path.exists(abs_fuzzy_texture_path):
                    self.apply_texture(obj, abs_fuzzy_texture_path)
                    found_texture = True

            # 在找不到纹理的情况下报告
            if not found_texture:
                self.report({'WARNING'}, f"Texture file for {obj_name} not found: {abs_texture_path} or {abs_fuzzy_texture_path}")

        return {'FINISHED'}

    def apply_texture(self, obj, texture_path):
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
        texture_node.image = bpy.data.images.load(texture_path)
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
