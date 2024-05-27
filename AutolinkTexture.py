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
    )

    def execute(self, context):
        # 获取选中的物体
        selected_objects = context.selected_objects

        for obj in selected_objects:
            # 确保该对象有data属性，比如Mesh类型对象
            if not hasattr(obj.data, 'materials'):
                self.report({'WARNING'}, f"{obj.name} is not a Mesh object or has no data, skipping.")
                continue

            # 获取物体名称
            obj_name = obj.name

            # 根据物体名称构建贴图文件路径
            texture_path = os.path.join(self.texture_dir, f"{obj_name}_texture.png")

            # 检查贴图文件是否存在
            if os.path.exists(texture_path):
                # 创建新的材质
                mat = bpy.data.materials.new(name=f"{obj_name}_Material")

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

            else:
                self.report({'WARNING'}, f"Texture file for {obj_name} not found: {texture_path}")

        return {'FINISHED'}



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
