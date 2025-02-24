import bpy
import random
import math

bpy.types.Scene.emission_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置发光强度",
    default=0.2,
    min=0.0,
    max=10.0
        )
#设置发光强度
class SetEmissionStrength(bpy.types.Operator):
    bl_idname = "material.set_emission_strength"
    bl_label = "设置发光强度"

    strength : bpy.props.FloatProperty(
        name="强度",
        description="设置发光强度",
        default=0.0,
        min=0.0
    ) # type: ignore

    def set_emission_strength(self, material, strength):
        if not material.use_nodes:
            return

        for node in material.node_tree.nodes:
            if node.type == 'EMISSION':
                node.inputs['Strength'].default_value = strength
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Emission Strength'].default_value = strength

    def process_selected_objects(self, strength):
        for obj in bpy.context.selected_objects:
            # 只处理具有网格数据的对象（即类型为 'MESH' 的对象）
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat.node_tree is not None:
                        self.set_emission_strength(mat, strength)

    def execute(self, context):
        strength = self.strength  # 直接使用类的属性替代 context.scene.emission_strength
        self.process_selected_objects(strength)
        return {'FINISHED'}
# 材质球排序
class MaterialSort(bpy.types.Operator):
    bl_idname = "object.miao_material_sort"
    bl_label = "材质球排序"

    def execute(self, context):
        def sort_materials(obj):
            if obj is not None and obj.type == 'MESH' and len(obj.data.materials) > 1:
                materials = [slot.material for slot in obj.material_slots]
                sorted_materials = sorted(materials, key=lambda x: x.name)

                # 记录顶点组的材质分配关系
                polygon_material_indices = [
                    polygon.material_index for polygon in obj.data.polygons]

                # 创建一个映射，将旧的材质索引映射到新的排序后的材质索引
                index_mapping = {i: sorted_materials.index(
                    material) for i, material in enumerate(materials)}

                # 更新顶点组的材质分配关系
                for polygon in obj.data.polygons:
                    polygon.material_index = index_mapping[polygon_material_indices[polygon.index]]

                # 将排序后的材质球分配回物体的材质插槽
                for i, material in enumerate(sorted_materials):
                    obj.material_slots[i].material = material

        # 获取当前所选物体
        selected_objects = bpy.context.selected_objects
        # 遍历所选物体并排序它们的材质球
        for obj in selected_objects:
            sort_materials(obj)
        return {"FINISHED"}
# 随机材质球颜色
class OBJ_OT_random_meterial(bpy.types.Operator):
    bl_idname = "scene.random_meterial"
    bl_label = "随机材质球颜色"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        def random_color(colors_set):
            while True:
                color = (random.random(), random.random(), random.random(), 1)
                if color not in colors_set:
                    colors_set.add(color)
                    return color

        def create_diffuse_material(name, color):
            material = bpy.data.materials.new(name=name)
            material.use_nodes = True
            node_tree = material.node_tree

            # 获取 Principled BSDF 节点
            principled_bsdf_node = node_tree.nodes.get("Principled BSDF")

            # 更改颜色
            principled_bsdf_node.inputs["Base Color"].default_value = color
            return material

        def main():
            selected_objects = bpy.context.selected_objects
            used_colors = set()

            for obj in selected_objects:
                if obj.type == 'MESH':
                    material_slots = obj.material_slots
                    for index, material_slot in enumerate(material_slots):
                        unique_color = random_color(used_colors)

                        # 创建新的漫反射材质
                        new_material = create_diffuse_material(
                            obj.name + '_diffuse_' + str(index), unique_color)

                        # 替换现有材质
                        material_slot.material = new_material

        main()

        return {'FINISHED'}
# 合并材质
class MergeMaterial(bpy.types.Operator):
    bl_idname = "object.miao_merge_material"
    bl_label = "合并材质"

    def execute(self, context):
        # 单击按钮时要执行的代码
        mesh_objs = [
            obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        for obj in mesh_objs:
            print(obj.name)
            # Delete all materials in the mesh
            for i in range(len(obj.material_slots)):
                with bpy.context.temp_override(object=obj):
                    bpy.ops.object.material_slot_remove()
            mat = bpy.data.materials.new(obj.name)
            obj.data.materials.append(mat)
        return {'FINISHED'}
#设置所选物体材质为临近采样（硬边缘）
class SetTextureInterpolation(bpy.types.Operator):
    bl_label = "设置所选物体材质为硬边缘采样"
    bl_idname = "object.set_texture_interpolation"
    
    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        
        for obj in selected_objects:
            mat_slots = obj.material_slots
            
            for ms in mat_slots:
                mat = ms.material
                
                if mat and mat.node_tree:
                    node_tree = mat.node_tree
                    
                    for node in node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            node.interpolation = 'Closest'
                            
        return {'FINISHED'}

class AlphaNodeConnector(bpy.types.Operator):
    bl_idname = "object.alpha_node_connector"
    bl_label = "Alpha Node Connector"

    def execute(self, context):
        def link_texture_alpha_to_bsdf_alpha():
            # 获取当前选择的物体
            selected_objects = bpy.context.selected_objects
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    # 获取物体的材质槽
                    for slot in obj.material_slots:
                        material = slot.material
                        if material is not None and material.use_nodes:
                            # 获取材质节点树
                            nodes = material.node_tree.nodes
                            links = material.node_tree.links

                            # 查找 Principled BSDF 和 Image Texture 节点
                            principled_bsdf = None
                            image_texture = None

                            for node in nodes:
                                if node.type == 'BSDF_PRINCIPLED':
                                    principled_bsdf = node
                                elif node.type == 'TEX_IMAGE':
                                    image_texture = node

                            # 如果找到两个节点，连接它们的 alpha
                            if principled_bsdf and image_texture:
                                # 检查是否已有连接
                                already_connected = any(
                                    link.to_node == principled_bsdf and
                                    link.to_socket.name == 'Alpha' and
                                    link.from_node == image_texture and
                                    link.from_socket.name == 'Alpha'
                                    for link in links
                                )
                                
                                if not already_connected:
                                    # 连接图像纹理的 Alpha 到 Principled BSDF 的 Alpha
                                    links.new(image_texture.outputs['Alpha'], principled_bsdf.inputs['Alpha'])
                                    print(f"Connected {image_texture.name}'s Alpha to {principled_bsdf.name}'s Alpha in material {material.name}")


        link_texture_alpha_to_bsdf_alpha()
        return {'FINISHED'}

class AlphaNodeDisconnector(bpy.types.Operator):
    bl_idname = "object.alpha_node_disconnector"
    bl_label = "Alpha Node Disconnector"

    def execute(self, context):
        def disconnect_texture_alpha_to_bsdf_alpha():
            # 获取当前选择的物体
            selected_objects = bpy.context.selected_objects
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    # 获取物体的材质槽
                    for slot in obj.material_slots:
                        material = slot.material
                        if material is not None and material.use_nodes:
                            # 获取材质节点树
                            nodes = material.node_tree.nodes
                            links = material.node_tree.links

                            # 查找 Principled BSDF 和 Image Texture 节点
                            principled_bsdf = None
                            image_texture = None

                            for node in nodes:
                                if node.type == 'BSDF_PRINCIPLED':
                                    principled_bsdf = node
                                elif node.type == 'TEX_IMAGE':
                                    image_texture = node

                            # 如果找到两个节点，检查并断开连接
                            if principled_bsdf and image_texture:
                                # 查找并删除所有连接
                                for link in links:
                                    if (link.from_node == image_texture and 
                                        link.from_socket.name == 'Alpha' and 
                                        link.to_node == principled_bsdf and 
                                        link.to_socket.name == 'Alpha'):
                                        links.remove(link)
                                        print(f"Disconnected {image_texture.name}'s Alpha from {principled_bsdf.name}'s Alpha in material {material.name}")

        disconnect_texture_alpha_to_bsdf_alpha()
        return {'FINISHED'}

class AlphaToSkin(bpy.types.Operator):
    bl_idname = "object.alpha_to_skin"
    bl_label = "Alpha To Skin"

    def execute(self, context):
        def link_texture_alpha_to_bsdf_alpha_with_color(target_color=(1.0, 1.0, 1.0, 1.0)):
            # 获取当前选择的物体
            selected_objects = bpy.context.selected_objects
            
            for obj in selected_objects:
                if obj.type == 'MESH':
                    # 获取物体的材质槽
                    for slot in obj.material_slots:
                        material = slot.material
                        if material is not None and material.use_nodes:
                            # 获取材质节点树
                            nodes = material.node_tree.nodes
                            links = material.node_tree.links

                            # 查找 Principled BSDF 和 Image Texture 节点
                            principled_bsdf = None
                            image_texture = None

                            for node in nodes:
                                if node.type == 'BSDF_PRINCIPLED':
                                    principled_bsdf = node
                                elif node.type == 'TEX_IMAGE':
                                    image_texture = node

                            # 如果找到两个节点，连接它们的 alpha
                            if principled_bsdf and image_texture:
                                # 创建 Mix Shader 和 Transparent BSDF 节点
                                mix_shader = nodes.new(type='ShaderNodeMixShader')
                                transparent_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')

                                transparent_bsdf.inputs['Base Color'].default_value = target_color

                                # 连接 Image Texture 的 Alpha 到 Mix Shader 的 Fac
                                links.new(image_texture.outputs['Alpha'], mix_shader.inputs['Fac'])

                                # 连接 Transparent BSDF 到 Mix Shader
                                links.new(transparent_bsdf.outputs['BSDF'], mix_shader.inputs[1])

                                # 连接 Principled BSDF 到 Mix Shader
                                links.new(principled_bsdf.outputs['BSDF'], mix_shader.inputs[2])

                                # 查找 Material Output 节点
                                material_output = None
                                for node in nodes:
                                    if node.type == 'OUTPUT_MATERIAL':
                                        material_output = node
                                        break

                                if material_output:
                                    # 连接 Mix Shader 到 Material Output
                                    links.new(mix_shader.outputs['Shader'], material_output.inputs['Surface'])

                                print(f"Connected {image_texture.name}'s Alpha to Mix Shader in material {material.name}")
        
        link_texture_alpha_to_bsdf_alpha_with_color((0.957, 0.761, 0.620, 1.0))
        return {'FINISHED'}





def register():     
    bpy.utils.register_class(SetEmissionStrength)
    bpy.utils.register_class(MaterialSort)
    bpy.utils.register_class(OBJ_OT_random_meterial)
    bpy.utils.register_class(MergeMaterial)
    bpy.utils.register_class(SetTextureInterpolation)
    bpy.utils.register_class(AlphaNodeConnector)
    bpy.utils.register_class(AlphaToSkin)
    bpy.utils.register_class(AlphaNodeDisconnector)

def unregister():
    bpy.utils.unregister_class(SetEmissionStrength)
    bpy.utils.unregister_class(MaterialSort)
    bpy.utils.unregister_class(OBJ_OT_random_meterial)
    bpy.utils.unregister_class(MergeMaterial)
    bpy.utils.unregister_class(SetTextureInterpolation)
    bpy.utils.unregister_class(AlphaNodeConnector)
    bpy.utils.unregister_class(AlphaToSkin)
    bpy.utils.unregister_class(AlphaNodeDisconnector)

