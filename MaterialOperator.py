import bpy
import random
import math
import re

bpy.types.Scene.emission_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置发光强度",
    default=0.0,
    min=0.0,
    max=10.0
        )

bpy.types.Scene.roughness_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置光滑强度",
    default=1.0,
    min=0.0,
    max=1.0
        )

bpy.types.Scene.metallic_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置金属度强度",
    default=0.0,
    min=0.0,
    max=1.0
        )

bpy.types.Scene.specular_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置高光强度",
    default=0.0,
    min=0.0,
    max=1.0
        )

bpy.types.Scene.specular_tint_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置光泽度",
    default=0.0,
    min=0.0,
    max=1.0
        )

#设置发光强度
class SetEmissionStrength(bpy.types.Operator):
    bl_idname = "object.set_emission_strength"
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

    def process_material(self, material, strength):
        if material and material.use_nodes:
            self.set_emission_strength(material, strength)

    def process_selected_objects(self, strength):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    self.process_material(mat, strength)

    def process_selected_materials(self, strength):
        for material in bpy.context.selected_ids:
            if isinstance(material, bpy.types.Material):
                self.process_material(material, strength)

    def execute(self, context):
        strength = self.strength
        self.process_selected_objects(strength)
        self.process_selected_materials(strength)
        return {'FINISHED'}

class SetMaterialRoughness(bpy.types.Operator):
    bl_idname = "object.set_roughness"
    bl_label = "设置材质粗糙度"
    
    roughness: bpy.props.FloatProperty(
        name="粗糙度",
        description="调整材质的粗糙度",
        default=1.0,
        min=0.0,
        max=1.0
    ) # type: ignore
    
    def set_roughness(self, material, roughness):
        if not material.use_nodes:
            return
        
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Roughness'].default_value = roughness

    def process_material(self, material, roughness):
        if material and material.use_nodes:
            self.set_roughness(material, roughness)

    def process_selected_objects(self, roughness):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    self.process_material(mat, roughness)

    def process_selected_materials(self, roughness):
        for material in bpy.context.selected_ids:
            if isinstance(material, bpy.types.Material):
                self.process_material(material, roughness)

    def execute(self, context):
        roughness = self.roughness
        self.process_selected_objects(roughness)
        self.process_selected_materials(roughness)
        return {'FINISHED'}

class SetMaterialMetallic(bpy.types.Operator):
    bl_idname = "object.set_metallic"
    bl_label = "设置材质金属度"
    
    metallic: bpy.props.FloatProperty(
        name="金属度",
        description="调整材质的金属度",
        default=0.0,
        min=0.0,
        max=1.0
    ) # type: ignore
    
    def set_metallic(self, material, metallic):
        if not material.use_nodes:
            return
        
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Metallic'].default_value = metallic

    def process_material(self, material, metallic):
        if material and material.use_nodes:
            self.set_metallic(material, metallic)

    def process_selected_objects(self, metallic):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    self.process_material(mat, metallic)

    def process_selected_materials(self, metallic):
        for material in bpy.context.selected_ids:
            if isinstance(material, bpy.types.Material):
                self.process_material(material, metallic)

    def execute(self, context):
        metallic = self.metallic
        self.process_selected_objects(metallic)
        self.process_selected_materials(metallic)
        return {'FINISHED'}

class SetMaterialSpecular(bpy.types.Operator):
    bl_idname = "object.set_specular"
    bl_label = "设置材质高光强度"
    
    specular: bpy.props.FloatProperty(
        name="高光强度",
        description="调整材质的高光强度",
        default=0.5,
        min=0.0,
        max=1.0
    ) # type: ignore
    
    def set_specular(self, material, specular):
        if not material.use_nodes:
            return
        
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Specular'].default_value = specular

    def process_material(self, material, specular):
        if material and material.use_nodes:
            self.set_specular(material, specular)

    def process_selected_objects(self, specular):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    self.process_material(mat, specular)

    def process_selected_materials(self, specular):
        for material in bpy.context.selected_ids:
            if isinstance(material, bpy.types.Material):
                self.process_material(material, specular)

    def execute(self, context):
        specular = self.specular
        self.process_selected_objects(specular)
        self.process_selected_materials(specular)
        return {'FINISHED'}

class SetMaterialSpecularTint(bpy.types.Operator):
    bl_idname = "object.set_specular_tint"
    bl_label = "设置材质光泽度"
    
    specular_tint: bpy.props.FloatProperty(
        name="光泽度",
        description="调整材质的光泽度",
        default=0.0,
        min=0.0,
        max=1.0
    ) # type: ignore
    
    def set_specular_tint(self, material, specular_tint):
        if not material.use_nodes:
            return
        
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                # 确保使用正确的输入名称
                if 'Specular Tint' in node.inputs:
                    node.inputs['Specular Tint'].default_value = specular_tint
                elif 'Specular Tint Weight' in node.inputs:  # 某些版本的Blender可能使用这个名称
                    node.inputs['Specular Tint Weight'].default_value = specular_tint

    def process_material(self, material, specular_tint):
        if material and material.use_nodes:
            self.set_specular_tint(material, specular_tint)

    def process_selected_objects(self, specular_tint):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    self.process_material(mat, specular_tint)

    def process_selected_materials(self, specular_tint):
        for material in bpy.context.selected_ids:
            if isinstance(material, bpy.types.Material):
                self.process_material(material, specular_tint)

    def execute(self, context):
        specular_tint = self.specular_tint
        self.process_selected_objects(specular_tint)
        self.process_selected_materials(specular_tint)
        return {'FINISHED'}

# 材质球排序
class MaterialSort(bpy.types.Operator):
    bl_idname = "object.mian_material_sort"
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
    bl_idname = "object.mian_merge_material"
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


def clean_materials():
    # 收集所有材质
    materials = bpy.data.materials

    # 创建一个字典用于存储不带后缀的材质
    base_materials = {}

    # 遍历所有材质
    for mat in materials:
        # 检查材质名是否带有后缀
        if '.' in mat.name[-4:]:
            base_name = mat.name.rsplit('.', 1)[0]
            
            # 如果没有这个基础材质，则添加到字典中
            if base_name not in base_materials:
                # 确保基础材质存在
                if base_name in materials:
                    base_materials[base_name] = materials[base_name]
            # 如果基础材质存在，则替换物体上的材质
            if base_name in base_materials:
                for obj in bpy.data.objects:
                    if obj.type == 'MESH':
                        for slot in obj.material_slots:
                            if slot.material == mat:
                                slot.material = base_materials[base_name]

    # 删除带有后缀的材质
    for mat in materials:
        if '.' in mat.name[-4:]:
            base_name = mat.name.rsplit('.', 1)[0]
            if base_name in base_materials:
                bpy.data.materials.remove(mat)

class MaterialCleaner(bpy.types.Operator):
    bl_idname = "object.material_cleaner"
    bl_label = "Material Cleaner"

    def execute(self, context):
        clean_materials()
        return {'FINISHED'}

# 合并带有.00x后缀的重复材质球
class OBJECT_OT_MergeDuplicateMaterials(bpy.types.Operator):
    bl_idname = "object.merge_duplicate_materials"
    bl_label = "合并后缀同名材质球"
    bl_description = "合并带有.001, .002等后缀的重复材质球以及参数完全相同的材质"
    bl_options = {'REGISTER', 'UNDO'}
    
    def are_materials_identical(self, mat1, mat2):
        """比较两个材质的参数是否完全相同"""
        # 如果两个材质有不同的节点树设置（一个有节点树，一个没有）
        if (mat1.use_nodes != mat2.use_nodes):
            return False
            
        # 如果材质不使用节点，比较基本属性
        if not mat1.use_nodes:
            # 比较基本颜色和其他属性
            if (mat1.diffuse_color != mat2.diffuse_color or
                mat1.metallic != mat2.metallic or
                mat1.roughness != mat2.roughness or
                mat1.blend_method != mat2.blend_method):
                return False
            return True
            
        # 对于使用节点的材质，检查节点结构
        if len(mat1.node_tree.nodes) != len(mat2.node_tree.nodes):
            return False
            
        # 比较主要节点的关键参数
        for node1 in mat1.node_tree.nodes:
            if node1.type == 'BSDF_PRINCIPLED':
                # 查找对应的节点
                principled_found = False
                for node2 in mat2.node_tree.nodes:
                    if node2.type == 'BSDF_PRINCIPLED':
                        principled_found = True
                        # 比较关键输入参数
                        if (node1.inputs['Base Color'].default_value[:] != node2.inputs['Base Color'].default_value[:] or
                            node1.inputs['Metallic'].default_value != node2.inputs['Metallic'].default_value or
                            node1.inputs['Roughness'].default_value != node2.inputs['Roughness'].default_value or
                            node1.inputs['Specular'].default_value != node2.inputs['Specular'].default_value or
                            node1.inputs['Emission Strength'].default_value != node2.inputs['Emission Strength'].default_value):
                            return False
                            
                if not principled_found:
                    return False
                    
            elif node1.type == 'TEX_IMAGE':
                # 查找是否有对应的图像纹理节点
                image_found = False
                for node2 in mat2.node_tree.nodes:
                    if node2.type == 'TEX_IMAGE':
                        # 如果两者都有图像
                        if node1.image and node2.image:
                            if node1.image.name == node2.image.name:
                                image_found = True
                                break
                        # 如果两者都没有图像
                        elif not node1.image and not node2.image:
                            image_found = True
                            break
                                
                # 如果没有找到对应的图像节点
                if not image_found and node1.image:
                    return False
        
        # 检查材质的渲染设置
        if (mat1.blend_method != mat2.blend_method or
            mat1.shadow_method != mat2.shadow_method or
            mat1.alpha_threshold != mat2.alpha_threshold):
            return False
            
        # 通过所有检查，认为材质参数相同
        return True
    
    def execute(self, context):
        # 收集所有材质球
        all_materials = bpy.data.materials
        
        # 用于存储基础材质名称到材质对象的映射
        base_materials = {}
        materials_to_replace = {}
        
        # 正则表达式用于匹配形如 "material.001" 的材质名称
        pattern = re.compile(r'^(.*?)(?:\.(\d{3,}))?$')
        
        # 第一遍：识别并分组材质
        for mat in all_materials:
            match = pattern.match(mat.name)
            if match:
                base_name = match.group(1)
                suffix = match.group(2)
                
                # 如果这是一个基础材质（没有.00X后缀）
                if suffix is None:
                    if base_name not in base_materials:
                        base_materials[base_name] = mat
                # 如果这是一个带后缀的材质
                else:
                    if base_name not in materials_to_replace:
                        materials_to_replace[base_name] = []
                    materials_to_replace[base_name].append(mat)
        
        # 处理没有基础材质但有后缀版本的情况
        for base_name, duplicates in materials_to_replace.items():
            if base_name not in base_materials and duplicates:
                # 使用名称排序，这样.001会排在前面
                duplicates.sort(key=lambda x: x.name)
                # 将第一个重命名为基础名称
                duplicates[0].name = base_name
                base_materials[base_name] = duplicates[0]
                # 移除已处理的第一个材质
                duplicates.pop(0)
        
        # 计数器
        replaced_count = 0
        removed_count = 0
        identical_count = 0
        
        # 第二遍：替换所有引用并删除重复材质
        for base_name, duplicates in materials_to_replace.items():
            if base_name in base_materials:
                base_mat = base_materials[base_name]
                
                # 遍历所有对象
                for obj in bpy.data.objects:
                    if obj.type == 'MESH' and obj.material_slots:
                        # 检查每个材质槽
                        for slot in obj.material_slots:
                            if slot.material in duplicates:
                                slot.material = base_mat
                                replaced_count += 1
                
                # 删除不再使用的重复材质
                for dup_mat in duplicates:
                    # 确保材质不再被使用
                    if dup_mat.users == 0:
                        bpy.data.materials.remove(dup_mat)
                        removed_count += 1
        
        # 第三遍：寻找并合并参数完全相同的材质（不限于同名）
        for i, mat1 in enumerate(all_materials):
            # 如果材质已被删除，跳过
            if mat1.name not in bpy.data.materials:
                continue
                
            for j in range(i + 1, len(all_materials)):
                # 获取第二个材质（如果它还存在）
                if j >= len(all_materials):
                    break
                    
                mat2_name = all_materials[j].name
                if mat2_name not in bpy.data.materials:
                    continue
                    
                mat2 = bpy.data.materials[mat2_name]
                
                # 如果两个材质参数完全相同
                if self.are_materials_identical(mat1, mat2):
                    print(f"发现完全相同的材质: {mat1.name} 和 {mat2.name}")
                    
                    # 遍历所有对象，将引用mat2的材质替换为mat1
                    for obj in bpy.data.objects:
                        if obj.type == 'MESH' and obj.material_slots:
                            # 检查每个材质槽
                            for slot in obj.material_slots:
                                if slot.material == mat2:
                                    slot.material = mat1
                                    identical_count += 1
                    
                    # 如果mat2不再被使用，删除它
                    if mat2.users == 0:
                        bpy.data.materials.remove(mat2)
                        removed_count += 1
        
        self.report({'INFO'}, f"合并完成：替换了 {replaced_count} 个同名材质引用，{identical_count} 个相同参数材质引用，删除了 {removed_count} 个重复材质")
        return {'FINISHED'}

# 清理空材质槽
class OBJECT_OT_RemoveUnusedMaterialSlots(bpy.types.Operator):
    bl_idname = "object.remove_unused_material_slots"
    bl_label = "清理空材质槽"
    bl_description = "移除所有没有分配多边形的材质槽"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        # 如果没有选中物体，则处理所有网格物体
        if not selected_objects:
            selected_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        removed_count = 0
        for obj in selected_objects:
            if obj.type != 'MESH':
                continue
                
            # 获取每个材质槽的使用情况
            used_slots = set()
            for polygon in obj.data.polygons:
                used_slots.add(polygon.material_index)
            
            # 找出未使用的材质槽
            unused_slot_indices = []
            for i in range(len(obj.material_slots)):
                if i not in used_slots:
                    unused_slot_indices.append(i)
            
            # 从高索引到低索引删除，以避免索引偏移问题
            for slot_index in sorted(unused_slot_indices, reverse=True):
                obj.active_material_index = slot_index
                bpy.ops.object.material_slot_remove({'object': obj})
                removed_count += 1
                
        self.report({'INFO'}, f"已删除 {removed_count} 个未使用的材质槽")
        return {'FINISHED'}

# 设置材质渲染模式为Alpha Clip
class mian_OT_SetMaterialAlphaClipMode(bpy.types.Operator):
    bl_idname = "object.set_material_alpha_clip"
    bl_label = "设置Alpha裁剪模式"
    bl_description = "将所选物体的所有材质视图显示设置为Alpha裁剪模式"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    if slot.material:
                        slot.material.blend_method = 'CLIP'
                        slot.material.shadow_method = 'CLIP'
        return {'FINISHED'}

# 设置材质渲染模式为Alpha Blend
class SetMaterialAlphaBlendMode(bpy.types.Operator):
    bl_idname = "object.set_material_alpha_blend"
    bl_label = "设置Alpha混合模式"
    bl_description = "将所选物体的所有材质视图显示设置为Alpha混合模式"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    material = slot.material
                    if material:
                        # 设置材质的混合模式为Alpha混合
                        material.blend_method = 'BLEND'
                        changed_count += 1
        
        self.report({'INFO'}, f"已将 {changed_count} 个材质设置为Alpha混合模式")
        return {'FINISHED'}

# 设置所选物体阴影不可见
class SetShadowInvisible(bpy.types.Operator):
    bl_idname = "object.set_shadow_invisible"
    bl_label = "设置阴影不可见"
    bl_description = "将所选物体在视图和渲染中的阴影设置为不可见"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                # 设置对象的阴影模式为不可见，此设置同时影响视图和渲染
                obj.visible_shadow = False
                changed_count += 1
        
        self.report({'INFO'}, f"已将 {changed_count} 个物体的阴影设置为不可见（视图和渲染中均不显示阴影）")
        return {'FINISHED'}

# 设置所选物体阴影可见
class SetShadowVisible(bpy.types.Operator):
    bl_idname = "object.set_shadow_visible"
    bl_label = "设置阴影可见"
    bl_description = "将所选物体在视图和渲染中的阴影设置为可见"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                # 设置对象的阴影模式为可见，此设置同时影响视图和渲染
                obj.visible_shadow = True
                changed_count += 1
        
        self.report({'INFO'}, f"已将 {changed_count} 个物体的阴影设置为可见（视图和渲染中均显示阴影）")
        return {'FINISHED'}

# 清理物体中未使用的材质和插槽
class CleanUnusedMaterials(bpy.types.Operator):
    bl_idname = "object.clean_unused_materials"
    bl_label = "清理未使用材质"
    bl_description = "清理物体中未使用的材质球及其插槽"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        materials_removed = 0
        slots_removed = 0
        
        for obj in selected_objects:
            if obj.type != 'MESH' or not obj.data.materials:
                continue
                
            # 获取每个多边形使用的材质索引
            used_indices = set()
            for polygon in obj.data.polygons:
                used_indices.add(polygon.material_index)
            
            # 创建一个映射，将旧索引映射到新索引（考虑到删除后的偏移）
            index_mapping = {}
            current_new_index = 0
            
            # 标记要保留的材质
            materials_to_keep = []
            
            # 遍历所有材质槽，确定哪些需要保留
            for i, slot in enumerate(obj.material_slots):
                if i in used_indices:
                    index_mapping[i] = current_new_index
                    materials_to_keep.append(slot.material)
                    current_new_index += 1
                else:
                    slots_removed += 1
            
            # 调整多边形的材质索引
            for polygon in obj.data.polygons:
                if polygon.material_index in index_mapping:
                    polygon.material_index = index_mapping[polygon.material_index]
            
            # 清除所有材质槽
            while len(obj.material_slots) > 0:
                obj.active_material_index = 0
                bpy.ops.object.material_slot_remove({'object': obj})
            
            # 重新添加需要保留的材质
            for mat in materials_to_keep:
                obj.data.materials.append(mat)
            
            materials_removed += len(obj.material_slots) - len(materials_to_keep)
        
        self.report({'INFO'}, f"已清理 {slots_removed} 个未使用的材质槽，移除了 {materials_removed} 个未使用的材质")
        return {'FINISHED'}

# 材质替换操作符
class ReplaceMaterialOperator(bpy.types.Operator):
    bl_idname = "object.replace_material"
    bl_label = "替换材质"
    bl_description = "将选中物体中的指定材质替换为目标材质"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if not context.scene.source_materials or not context.scene.target_material:
            self.report({'ERROR'}, "请选择至少一个源材质和目标材质")
            return {'CANCELLED'}
            
        # 检查目标材质是否在源材质列表中
        if context.scene.target_material in context.scene.source_materials:
            self.report({'WARNING'}, "目标材质不能是源材质之一")
            return {'CANCELLED'}
            
        replaced_count = 0
        affected_objects = 0
        
        # 遍历所有选中的物体
        for obj in context.selected_objects:
            if obj.type not in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT'}:
                continue
                
            material_changed = False
            
            # 遍历物体的所有材质槽
            for slot in obj.material_slots:
                if slot.material in context.scene.source_materials:
                    slot.material = context.scene.target_material
                    replaced_count += 1
                    material_changed = True
            
            if material_changed:
                affected_objects += 1
        
        if replaced_count > 0:
            self.report({'INFO'}, f"已在 {affected_objects} 个物体中替换了 {replaced_count} 个材质槽")
        else:
            self.report({'WARNING'}, "未找到需要替换的材质")
            
        return {'FINISHED'}

# 基于关键字搜索的材质替换操作符
class ReplaceMaterialByKeywordOperator(bpy.types.Operator):
    bl_idname = "object.replace_material_by_keyword"
    bl_label = "按关键字替换材质"
    bl_description = "将包含指定关键字的材质替换为目标材质"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        keyword = context.scene.keyword_search.strip()
        target_material = context.scene.keyword_target_material
        
        if not keyword:
            self.report({'ERROR'}, "请输入要搜索的关键字")
            return {'CANCELLED'}
            
        if not target_material:
            self.report({'ERROR'}, "请选择目标材质")
            return {'CANCELLED'}
        
        replaced_count = 0
        affected_objects = set()
        
        # 获取选中的物体
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "请选择要替换材质的物体")
            return {'CANCELLED'}
        
        # 过滤出MESH类型的物体
        mesh_objects = [obj for obj in selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "选中的物体中没有MESH类型的物体")
            return {'CANCELLED'}
        
        # 遍历选中的MESH物体
        for obj in mesh_objects:
            for slot in obj.material_slots:
                # 检查材质是否包含关键字
                if slot.material and keyword in slot.material.name:
                    slot.material = target_material
                    replaced_count += 1
                    affected_objects.add(obj.name)
        
        # 显示结果
        if replaced_count > 0:
            self.report({'INFO'}, f"已替换 {replaced_count} 个材质，影响 {len(affected_objects)} 个物体")
        else:
            self.report({'WARNING'}, f"没有找到包含关键字 '{keyword}' 的材质")
            
        return {'FINISHED'}


class SplitMeshByMaterialOperator(bpy.types.Operator):
    bl_idname = "object.split_mesh_by_material"
    bl_label = "按材质拆分Mesh"
    bl_description = "将指定材质的mesh从原本的mesh中拆分出来，保持层级结构"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取选中的物体
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'ERROR'}, "请选择要拆分的物体")
            return {'CANCELLED'}
        
        # 获取要拆分的材质
        split_material = context.scene.split_material
        if not split_material:
            self.report({'ERROR'}, "请选择要拆分的材质")
            return {'CANCELLED'}
        
        # 过滤出MESH类型的物体
        mesh_objects = [obj for obj in selected_objects if obj.type == 'MESH']
        
        if not mesh_objects:
            self.report({'WARNING'}, "选中的物体中没有MESH类型的物体")
            return {'CANCELLED'}
        
        total_split_count = 0
        
        for obj in mesh_objects:
            # 检查物体是否包含指定材质
            material_slots = obj.material_slots
            if not material_slots:
                continue
            
            # 找到指定材质的槽位索引
            material_indices = []
            for i, slot in enumerate(material_slots):
                if slot.material == split_material:
                    material_indices.append(i)
            
            if not material_indices:
                continue
            
            # 使用Blender内置的分离功能
            if self.separate_material_faces(obj, material_indices, split_material):
                total_split_count += 1
        
        if total_split_count > 0:
            self.report({'INFO'}, f"已成功拆分 {total_split_count} 个物体")
        else:
            self.report({'WARNING'}, "没有找到包含指定材质的物体")
            
        return {'FINISHED'}
    
    def separate_material_faces(self, obj, material_indices, split_material):
        """使用Blender内置功能分离指定材质的面（类似Alt+P效果）"""
        try:
            # 进入编辑模式
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 取消选择所有面
            bpy.ops.mesh.select_all(action='DESELECT')
            
            # 选择指定材质的面
            bpy.ops.object.mode_set(mode='OBJECT')
            for poly in obj.data.polygons:
                if poly.material_index in material_indices:
                    poly.select = True
            
            # 回到编辑模式
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 分离选中的面
            bpy.ops.mesh.separate(type='SELECTED')
            
            # 回到物体模式
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 重命名新分离的物体
            if len(bpy.context.selected_objects) > 1:
                # 找到新分离的物体（应该是最后一个选中的）
                new_obj = None
                for selected_obj in bpy.context.selected_objects:
                    if selected_obj != obj and selected_obj.type == 'MESH':
                        new_obj = selected_obj
                        break
                
                if new_obj:
                    new_obj.name = f"{obj.name}_{split_material.name}"
                    
                    # 清理新物体的材质槽，只保留指定材质
                    self.clean_material_slots(new_obj, split_material)
                    
                    # 从原物体中移除指定材质
                    self.remove_material_from_object(obj, split_material)
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"分离材质面时出错: {str(e)}")
            # 确保回到物体模式
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            return False
    
    def clean_material_slots(self, obj, material):
        """清理材质槽，只保留指定材质"""
        # 清除所有材质槽
        while len(obj.material_slots) > 0:
            obj.active_material_index = 0
            bpy.ops.object.material_slot_remove({'object': obj})
        
        # 添加指定材质
        obj.data.materials.append(material)
    
    def remove_material_from_mesh(self, mesh, material_indices):
        """从mesh中移除指定材质的几何体"""
        # 获取要移除的多边形
        polygons_to_remove = []
        for poly in mesh.polygons:
            if poly.material_index in material_indices:
                polygons_to_remove.append(poly.index)
        
        if not polygons_to_remove:
            return
        
        # 从高索引到低索引删除，避免索引偏移
        for poly_idx in sorted(polygons_to_remove, reverse=True):
            mesh.polygons.remove(poly_idx)
        
        # 更新mesh
        mesh.update()
    
    def remove_material_from_object(self, obj, material):
        """从物体中移除指定材质"""
        # 找到材质槽索引
        material_slot_index = -1
        for i, slot in enumerate(obj.material_slots):
            if slot.material == material:
                material_slot_index = i
                break
        
        if material_slot_index >= 0:
            obj.active_material_index = material_slot_index
            bpy.ops.object.material_slot_remove({'object': obj})

# 设置贴图Alpha通道打包模式
class SetTextureAlphaPacking(bpy.types.Operator):
    bl_idname = "object.set_texture_alpha_packing"
    bl_label = "设置贴图Alpha通道打包"
    bl_description = "将所选物体的所有贴图设置为Alpha通道打包模式"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    material = slot.material
                    if material and material.use_nodes:
                        for node in material.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                node.image.alpha_mode = 'CHANNEL_PACKED'
                                changed_count += 1
        
        self.report({'INFO'}, f"已将 {changed_count} 个贴图设置为Alpha通道打包模式")
        return {'FINISHED'}

# 设置材质渲染模式为Opaque
class SetMaterialOpaqueMode(bpy.types.Operator):
    bl_idname = "object.set_material_opaque"
    bl_label = "设置Opaque模式"
    bl_description = "将所选物体的所有材质视图显示设置为Opaque模式"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    material = slot.material
                    if material:
                        # 设置材质的混合模式为Opaque
                        material.blend_method = 'OPAQUE'
                        changed_count += 1
        
        self.report({'INFO'}, f"已将 {changed_count} 个材质设置为Opaque模式")
        return {'FINISHED'}

# 一键执行所有材质强度调整
class ApplyAllMaterialStrengths(bpy.types.Operator):
    bl_idname = "object.apply_all_material_strengths"
    bl_label = "一键执行所有材质强度调整"
    bl_description = "一次性应用所有材质强度设置（发光、粗糙度、金属度、高光、光泽度）"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        
        # 获取当前场景中的强度值
        emission_strength = scene.emission_strength
        roughness_strength = scene.roughness_strength
        metallic_strength = scene.metallic_strength
        specular_strength = scene.specular_strength
        specular_tint_strength = scene.specular_tint_strength
        
        try:
            # 直接调用各个操作符的核心方法
            self.apply_emission_strength(context, emission_strength)
            self.apply_roughness_strength(context, roughness_strength)
            self.apply_metallic_strength(context, metallic_strength)
            self.apply_specular_strength(context, specular_strength)
            self.apply_specular_tint_strength(context, specular_tint_strength)
            
            self.report({'INFO'}, f"已应用所有材质强度设置：发光={emission_strength:.2f}, 粗糙度={roughness_strength:.2f}, 金属度={metallic_strength:.2f}, 高光={specular_strength:.2f}, 光泽度={specular_tint_strength:.2f}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"执行材质强度调整时出错: {str(e)}")
            return {'CANCELLED'}
    
    def apply_emission_strength(self, context, strength):
        """应用发光强度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'EMISSION':
                                node.inputs['Strength'].default_value = strength
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Emission Strength'].default_value = strength
    
    def apply_roughness_strength(self, context, roughness):
        """应用粗糙度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Roughness'].default_value = roughness
    
    def apply_metallic_strength(self, context, metallic):
        """应用金属度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Metallic'].default_value = metallic
    
    def apply_specular_strength(self, context, specular):
        """应用高光强度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Specular'].default_value = specular
    
    def apply_specular_tint_strength(self, context, specular_tint):
        """应用光泽度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                # 确保使用正确的输入名称
                                if 'Specular Tint' in node.inputs:
                                    node.inputs['Specular Tint'].default_value = specular_tint
                                elif 'Specular Tint Weight' in node.inputs:
                                    node.inputs['Specular Tint Weight'].default_value = specular_tint

# 一键调整体素模型材质
class ApplyVoxelModelMaterial(bpy.types.Operator):
    bl_idname = "object.apply_voxel_model_material"
    bl_label = "一键调整体素模型材质"
    bl_description = "一键调整体素模型材质：先调整材质强度，再设置Alpha通道打包，最后设置硬边缘采样"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        try:
            # 步骤1：执行一键调整材质强度
            self.report({'INFO'}, "步骤1: 调整材质强度...")
            self.apply_all_material_strengths(context)
            
            # 步骤2：设置Alpha通道打包
            self.report({'INFO'}, "步骤2: 设置Alpha通道打包...")
            self.apply_alpha_packing(context)
            
            # 步骤3：设置硬边缘采样
            self.report({'INFO'}, "步骤3: 设置硬边缘采样...")
            self.apply_hard_edge_sampling(context)
            
            self.report({'INFO'}, "体素模型材质调整完成！")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"调整体素模型材质时出错: {str(e)}")
            return {'CANCELLED'}
    
    def apply_all_material_strengths(self, context):
        """应用所有材质强度设置"""
        # 直接调用现有的ApplyAllMaterialStrengths操作符的核心方法
        scene = context.scene
        
        # 获取当前场景中的强度值
        emission_strength = scene.emission_strength
        roughness_strength = scene.roughness_strength
        metallic_strength = scene.metallic_strength
        specular_strength = scene.specular_strength
        specular_tint_strength = scene.specular_tint_strength
        
        # 直接应用各种材质强度（复制ApplyAllMaterialStrengths的逻辑）
        self._apply_emission_strength(context, emission_strength)
        self._apply_roughness_strength(context, roughness_strength)
        self._apply_metallic_strength(context, metallic_strength)
        self._apply_specular_strength(context, specular_strength)
        self._apply_specular_tint_strength(context, specular_tint_strength)
    
    def _apply_emission_strength(self, context, strength):
        """应用发光强度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'EMISSION':
                                node.inputs['Strength'].default_value = strength
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Emission Strength'].default_value = strength
    
    def _apply_roughness_strength(self, context, roughness):
        """应用粗糙度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Roughness'].default_value = roughness
    
    def _apply_metallic_strength(self, context, metallic):
        """应用金属度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Metallic'].default_value = metallic
    
    def _apply_specular_strength(self, context, specular):
        """应用高光强度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                node.inputs['Specular'].default_value = specular
    
    def _apply_specular_tint_strength(self, context, specular_tint):
        """应用光泽度"""
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'BSDF_PRINCIPLED':
                                # 确保使用正确的输入名称
                                if 'Specular Tint' in node.inputs:
                                    node.inputs['Specular Tint'].default_value = specular_tint
                                elif 'Specular Tint Weight' in node.inputs:
                                    node.inputs['Specular Tint Weight'].default_value = specular_tint
    
    def apply_alpha_packing(self, context):
        """设置Alpha通道打包"""
        selected_objects = context.selected_objects
        changed_count = 0
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    material = slot.material
                    if material and material.use_nodes:
                        for node in material.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                node.image.alpha_mode = 'CHANNEL_PACKED'
                                changed_count += 1
    
    def apply_hard_edge_sampling(self, context):
        """设置硬边缘采样"""
        selected_objects = context.selected_objects
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                mat_slots = obj.material_slots
                
                for ms in mat_slots:
                    mat = ms.material
                    
                    if mat and mat.node_tree:
                        node_tree = mat.node_tree
                        
                        for node in node_tree.nodes:
                            if node.type == 'TEX_IMAGE':
                                node.interpolation = 'Closest'

def register():
    # 注册操作符类
    classes = [
        SetEmissionStrength,
        SetMaterialRoughness,
        SetMaterialMetallic,
        SetMaterialSpecular,
        SetMaterialSpecularTint,
        MaterialSort,
        OBJ_OT_random_meterial,
        MergeMaterial,
        SetTextureInterpolation,
        AlphaNodeConnector,
        AlphaNodeDisconnector,
        AlphaToSkin,
        MaterialCleaner,
        OBJECT_OT_MergeDuplicateMaterials,
        OBJECT_OT_RemoveUnusedMaterialSlots,
        mian_OT_SetMaterialAlphaClipMode,
        SetMaterialAlphaBlendMode,
        SetShadowInvisible,
        SetShadowVisible,
        CleanUnusedMaterials,
        ReplaceMaterialOperator,
        ReplaceMaterialByKeywordOperator,
        SplitMeshByMaterialOperator,
        SetTextureAlphaPacking,
        SetMaterialOpaqueMode,
        ApplyAllMaterialStrengths,
        ApplyVoxelModelMaterial
    ]
    
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"Error registering {cls.__name__}: {str(e)}")

def unregister():
    # 注销操作符类（反向顺序）
    classes = [
        ApplyVoxelModelMaterial,
        ApplyAllMaterialStrengths,
        SetMaterialOpaqueMode,
        SplitMeshByMaterialOperator,
        ReplaceMaterialByKeywordOperator,
        ReplaceMaterialOperator,
        CleanUnusedMaterials,
        SetShadowVisible,
        SetShadowInvisible,
        SetMaterialAlphaBlendMode,
        mian_OT_SetMaterialAlphaClipMode,
        OBJECT_OT_RemoveUnusedMaterialSlots,
        OBJECT_OT_MergeDuplicateMaterials,
        MaterialCleaner,
        AlphaToSkin,
        AlphaNodeDisconnector,
        AlphaNodeConnector,
        SetTextureInterpolation,
        MergeMaterial,
        OBJ_OT_random_meterial,
        MaterialSort,
        SetMaterialRoughness,
        SetMaterialMetallic,
        SetMaterialSpecular,
        SetMaterialSpecularTint,
        SetEmissionStrength
    ]
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"Error unregistering {cls.__name__}: {str(e)}")
