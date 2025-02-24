import bpy
import os



class ApplyTextureOperator(bpy.types.Operator):
    """Apply Texture to Selected Objects"""
    bl_idname = "object.apply_texture_operator"
    bl_label = "Apply Texture"
    bl_options = {'REGISTER', 'UNDO'}
    
    # texture_dir: bpy.props.StringProperty(
    #     name="Texture Directory",
    #     description="Directory where the texture files are located",
    #     default="",
    #     subtype='DIR_PATH'
    # ) # type: ignore

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
        if obj.type == 'EMPTY':
            return
        
        if not hasattr(obj.data, 'materials'):
            return
        
        obj_name = obj.name.lower()  # 将对象名称转换为小写

        found_texture = False
        while obj_name:
            # 根据物体名称构建贴图文件路径
            texture_path = os.path.join(texture_dir, f"{obj_name}.png").lower()
            
            # 打印调试信息，确认文件路径
            print(f"Checking for texture: {texture_path}")

            # 检查贴图文件是否存在
            if texture_path in processed_textures:
                texture = processed_textures[texture_path]
            else:
                try:
                    texture = bpy.data.images.load(texture_path)
                    processed_textures[texture_path] = texture
                except Exception as e:
                    return

            self.apply_texture(obj, texture)
            found_texture = True
            print(f"Texture applied to {obj.name}")
            break

            # 如果没有找到，则去掉名称的最后一个字符再试
            obj_name = obj_name[:-1]

        if not found_texture:
            print(f"Texture file for {obj.name} not found in {texture_dir}")

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
        texture_node = self.create_texture_node(nodes, texture)

        # 添加BSDF节点
        bsdf_node = self.create_bsdf_node(nodes)

        # 添加输出节点
        output_node = self.create_output_node(nodes)

        # 连接节点
        self.connect_nodes(links, texture_node, bsdf_node, output_node)

    def create_texture_node(self, nodes, texture):
        texture_node = nodes.new(type='ShaderNodeTexImage')
        texture_node.image = texture
        texture_node.interpolation = 'Closest'
        return texture_node

    def create_bsdf_node(self, nodes):
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        return bsdf_node

    def create_output_node(self, nodes):
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        return output_node

    def connect_nodes(self, links, texture_node, bsdf_node, output_node):
        links.new(texture_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

class ApplyTextureToSelectedObjects(bpy.types.Operator):
    """Apply Texture to Selected Objects"""
    bl_idname = "object.apply_texture_to_selected_objects"
    bl_label = "Apply Texture to Selected Objects"
    bl_options = {'REGISTER', 'UNDO'}

    # texture_dir: bpy.props.StringProperty(
    #     name="Texture Directory",
    #     description="Directory where the texture files are located",
    #     default="",
    #     subtype='DIR_PATH'
    # ) # type: ignore

    # ignore_fields_input: bpy.props.StringProperty(
    #     name="Ignore Fields",
    #     description="Comma-separated list of fields to ignore",
    #     default="_Upper, _lower, ,mod_,_clothes"
    # ) # type: ignore


    def execute(self, context):

        texture_dir = bpy.context.scene.texture_dir
        ignore_fields_input = bpy.context.scene.ignore_fields_input

        def apply_texture_to_selected_objects(directory, ignore_fields=None):
            if ignore_fields is None:
                ignore_fields = []
            
            # Ensure the directory path is valid
            if not os.path.isdir(directory):
                print(f"Directory '{directory}' does not exist.")
                return
            
            # Get selected objects
            selected_objects = bpy.context.selected_objects
            
            # Iterate over each selected object
            for obj in selected_objects:
                # Ensure the object is a mesh
                if obj.type != 'MESH':
                    continue
                
                # Check if the object already has a PNG texture
                has_png_texture = False
                if obj.data.materials:
                    mat = obj.data.materials[0]
                    if mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image and node.image.filepath.lower().endswith('.png'):
                                has_png_texture = True
                                break
                
                # Skip objects that already have a PNG texture
                if has_png_texture:
                    print(f"Object '{obj.name}' already has a PNG texture. Skipping.")
                    continue
                
                # Prepare the object name by removing the ignore fields
                object_name = obj.name.lower()
                for field in ignore_fields:
                    object_name = object_name.replace(field.lower(), "")
                
                # Search for a matching PNG file in the directory
                match_found = False
                for root, _, files in os.walk(directory):
                    for file in files:
                        file_name_without_extension = os.path.splitext(file)[0].lower()
                        for field in ignore_fields:
                            file_name_without_extension = file_name_without_extension.replace(field.lower(), "")
                        
                        if file_name_without_extension == object_name and file.lower().endswith('.png'):
                            # Create a new material if the object doesn't have one
                            if not obj.data.materials:
                                mat = bpy.data.materials.new(name=f"{obj.name}_Material")
                                obj.data.materials.append(mat)
                            else:
                                mat = obj.data.materials[0]
                            
                            # Enable 'Use Nodes'
                            mat.use_nodes = True
                            nodes = mat.node_tree.nodes
                            links = mat.node_tree.links
                            
                            # Clear existing nodes
                            for node in nodes:
                                nodes.remove(node)
                            
                            # Create new nodes
                            bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
                            tex_image_node = nodes.new(type='ShaderNodeTexImage')
                            output_node = nodes.new(type='ShaderNodeOutputMaterial')
                            
                            # Load the image
                            image_path = os.path.join(root, file)
                            tex_image_node.image = bpy.data.images.load(image_path)
                            
                            # Set node locations
                            tex_image_node.location = (-300, 300)
                            bsdf_node.location = (0, 300)
                            output_node.location = (200, 300)
                            
                            # Link nodes
                            links.new(tex_image_node.outputs['Color'], bsdf_node.inputs['Base Color'])
                            links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])
                            
                            match_found = True
                            print(f"Applied texture from '{image_path}' to object '{obj.name}'.")
                            break
                    
                    if match_found:
                        break
    
        apply_texture_to_selected_objects(texture_dir, ignore_fields_input)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ApplyTextureOperator)
    bpy.utils.register_class(ApplyTextureToSelectedObjects)

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

    del bpy.types.Scene.texture_dir
    del bpy.types.Scene.ignore_fields_input