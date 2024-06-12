
import bpy

def retopologize_and_bake_color(context):
    selected_objects = context.selected_objects
    if len(selected_objects) < 1:
        print("请至少选择一个对象。")
        return
    
    new_material = bpy.data.materials.new(name="SharedMaterial")
    
    new_material.use_nodes = True
    nodes = new_material.node_tree.nodes
    links = new_material.node_tree.links
    
    for node in nodes:
        nodes.remove(node)
        
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    texture_node = nodes.new(type='ShaderNodeTexImage')
    
    links.new(principled_bsdf.outputs['BSDF'], output_node.inputs['Surface'])
    links.new(texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    new_material.node_tree.nodes.active = texture_node

    processed_objects = []
    duplicate_objects = []
    
    for original_obj in selected_objects:
        if not original_obj.data or not original_obj.data.polygons:
            print(f"忽略空物体: {original_obj.name}")
            continue
        
        if not original_obj.data.materials:
            print(f"原始对象没有材质: {original_obj.name}")
            continue
        
        print(f"正在处理对象: {original_obj.name}")

        bpy.ops.object.select_all(action='DESELECT')
        original_obj.select_set(True)
        bpy.ops.object.duplicate()
        duplicate_obj = bpy.context.selected_objects[0]
        
        context.view_layer.objects.active = duplicate_obj
        bpy.ops.object.modifier_add(type='REMESH')
        remesh_modifier = duplicate_obj.modifiers[-1]
        remesh_modifier.name = "TempRemesh"
        remesh_modifier.octree_depth = 1
        remesh_modifier.use_smooth_shade = False
        remesh_modifier.mode = 'SHARP'
        
        try:
            bpy.ops.object.modifier_apply(modifier="TempRemesh")
            print(f"应用REMESH到: {duplicate_obj.name}")
        except Exception as e:
            print(f"应用REMESH修改器失败: {e}")
            bpy.data.objects.remove(duplicate_obj)
            continue

        bpy.ops.object.select_all(action='DESELECT')
        duplicate_obj.select_set(True)
        context.view_layer.objects.active = duplicate_obj
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.uv.smart_project(island_margin=0.01)
            print(f"UV展开完成: {duplicate_obj.name}")
        except Exception as e:
            print(f"UV展开失败: {e}")
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.objects.remove(duplicate_obj)
            continue
        bpy.ops.object.mode_set(mode='OBJECT')
        
        duplicate_obj.data.materials.clear()
        duplicate_obj.data.materials.append(new_material)
        
        processed_objects.append(original_obj)
        duplicate_objects.append(duplicate_obj)
    
    bpy.ops.object.select_all(action='DESELECT')
    for obj in duplicate_objects:
        obj.select_set(True)
    context.view_layer.objects.active = duplicate_objects[0]
    
    bpy.ops.object.join_uvs()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=0.01)
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"所有对象的UV展开完成")
    
    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    
    final_image = bpy.data.images.new(name="FinalBakedTexture", width=1024, height=1024, alpha=False)
    final_image.generated_color = (1.0, 1.0, 1.0, 1.0)
    
    final_texture_node = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
    final_texture_node.interpolation = 'Closest'
    final_texture_node.image = final_image
    new_material.node_tree.links.new(final_texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    for original_obj, duplicate_obj in zip(processed_objects, duplicate_objects):
        bpy.ops.object.select_all(action='DESELECT')
        original_obj.select_set(True)
        duplicate_obj.select_set(True)
        context.view_layer.objects.active = duplicate_obj
        
        new_material.node_tree.nodes.active = final_texture_node
        
        try:
            bpy.ops.object.bake(type='DIFFUSE', use_clear=False, margin=16)
            print(f"烘焙贴图完成: {duplicate_obj.name}")
        except Exception as e:
            print(f"烘焙贴图失败: {e}")
            bpy.data.objects.remove(duplicate_obj)
            continue

    final_image.filepath_raw = f"//Combined_Baked.png"
    final_image.file_format = 'PNG'
    final_image.save()
    print(f"所有对象的贴图保存完成")
    
    for obj in processed_objects:
        bpy.data.objects.remove(obj)

class RetopologizeAndBakeOperator(bpy.types.Operator):
    bl_idname = "object.retopologize_and_bake"
    bl_label = "Retopologize and Bake"
    
    def execute(self, context):
        retopologize_and_bake_color(context)
        return {'FINISHED'}

# class RetopologizeAndBakePanel(bpy.types.Panel):
#     bl_label = "Retopologize and Bake"
#     bl_idname = "OBJECT_PT_retopologize_and_bake"
#     bl_space_type = 'VIEW_3D'
#     bl_region_type = 'UI'
#     bl_category = 'Tool'
    
#     def draw(self, context):
#         layout = self.layout
#         row = layout.row()
#         row.operator("object.retopologize_and_bake")

def register():
    bpy.utils.register_class(RetopologizeAndBakeOperator)
    # bpy.utils.register_class(RetopologizeAndBakePanel)

def unregister():
    bpy.utils.unregister_class(RetopologizeAndBakeOperator)
    # bpy.utils.unregister_class(RetopologizeAndBakePanel)

if __name__ == "__main__":
    register()