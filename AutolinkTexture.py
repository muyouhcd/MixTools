import bpy
import os
import difflib

class ApplyTextureOperator(bpy.types.Operator):
    """将纹理应用到选定的对象"""
    bl_idname = "object.apply_texture_operator"
    bl_label = "应用纹理"
    bl_options = {'REGISTER', 'UNDO'}

    # 定义贴图目录属性
    texture_dir: bpy.props.StringProperty(
        name="纹理目录",
        description="存放纹理文件的目录",
        default="",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        # 从场景中获取用户输入的纹理目录，并转换为绝对路径
        texture_dir = bpy.context.scene.texture_dir
        abs_texture_dir = os.path.abspath(bpy.path.abspath(texture_dir))
        print(f"纹理目录（绝对路径）：{abs_texture_dir}")
        
        # 获取当前选定的对象
        selected_objects = bpy.context.selected_objects
        
        # 初始化一个空字典，用于存储已处理的纹理
        processed_textures = {}

        # 收集所有纹理文件名
        texture_files = []
        for root, _, files in os.walk(abs_texture_dir):
            for file in files:
                texture_files.append(os.path.join(root, file))

        # 处理每一个选中的对象
        for obj in selected_objects:
            self.process_object_and_children(obj, texture_files, abs_texture_dir, processed_textures)

        return {'FINISHED'}

    def process_object_and_children(self, obj, texture_files, texture_dir, processed_textures):
        """递归处理对象及其子对象，应用纹理"""
        # 如果对象类型是空物体，则忽略
        if obj.type == 'EMPTY':
            return
        
        # 确保对象具有数据属性，比如Mesh对象
        if not hasattr(obj.data, 'materials'): 
            self.report({'WARNING'}, f"{obj.name} 不是Mesh对象或没有数据，跳过。")
            return

        obj_name = obj.name.lower().replace('_', ' ')  # 将对象名称转换为小写并替换下划线
        print(f"正在处理对象：{obj_name}")

        # 使用difflib去匹配最接近的纹理文件
        closest_matches = difflib.get_close_matches(obj_name, [os.path.basename(f).rsplit('.', 1)[0].replace('_', ' ') for f in texture_files])
        
        if closest_matches:
            # 最接近的匹配
            closest_match = closest_matches[0]
            abs_texture_path = next((f for f in texture_files if os.path.basename(f).rsplit('.', 1)[0].replace('_', ' ') == closest_match), None)
            print(f"最接近的匹配文件：{abs_texture_path}")

            if abs_texture_path in processed_textures:
                texture = processed_textures[abs_texture_path]
            else:
                try:
                    texture = bpy.data.images.load(abs_texture_path)
                    processed_textures[abs_texture_path] = texture
                except Exception as e:
                    print(f"加载纹理时发生错误：{e}")
                    return

            self.apply_texture(obj, texture)
        else:
            self.report({'WARNING'}, f"{obj.name} 在 {texture_dir} 中未找到合适的纹理文件")

        for child in obj.children:
            self.process_object_and_children(child, texture_files, texture_dir, processed_textures)

    def apply_texture(self, obj, texture):
        """将纹理应用到对象上"""
        # 创建新的材质
        mat = bpy.data.materials.new(name=f"{obj.name}_Material")
        
        # 将材质分配给对象
        if obj.data.materials: 
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

        # 使用节点系统为材质添加纹理
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 移除默认的所有节点
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
        name="纹理目录",
        description="存放纹理文件的目录",
        default="",
        subtype='DIR_PATH'
    )

def unregister():
    bpy.utils.unregister_class(ApplyTextureOperator)
    del bpy.types.Scene.texture_dir

if __name__ == "__main__":
    register()