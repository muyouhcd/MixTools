import bpy

def retopologize_and_bake_without_remesh_color(new_context):
    selected_models = new_context.selected_objects
    if len(selected_models) < 1:
        print("请至少选择一个对象。")
        return
    
    shared_material = bpy.data.materials.new(name="SharedMaterial")
    shared_material.use_nodes = True
    mat_nodes = shared_material.node_tree.nodes
    mat_links = shared_material.node_tree.links
    
    for mat_node in mat_nodes:
        mat_nodes.remove(mat_node)
        
    output_node = mat_nodes.new(type='ShaderNodeOutputMaterial')
    principled_bsdf = mat_nodes.new(type='ShaderNodeBsdfPrincipled')
    texture_node = mat_nodes.new(type='ShaderNodeTexImage')
    
    mat_links.new(principled_bsdf.outputs['BSDF'], output_node.inputs['Surface'])
    mat_links.new(texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    shared_material.node_tree.nodes.active = texture_node

    processed_models = []
    duplicate_models = []
    
    for source_model in selected_models:
        if not source_model.data or not source_model.data.polygons:
            print(f"忽略空物体: {source_model.name}")
            continue
        
        if not source_model.data.materials:
            print(f"原始对象没有材质: {source_model.name}")
            continue
        
        print(f"正在处理对象: {source_model.name}")

        bpy.ops.object.select_all(action='DESELECT')
        source_model.select_set(True)
        bpy.ops.object.duplicate()
        copied_model = bpy.context.selected_objects[0]
        
        bpy.ops.object.select_all(action='DESELECT')
        copied_model.select_set(True)
        new_context.view_layer.objects.active = copied_model
        
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.uv.smart_project(island_margin=0.01)
            print(f"UV展开完成: {copied_model.name}")
        except Exception as e:
            print(f"UV展开失败: {e}")
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.data.objects.remove(copied_model)
            continue
        bpy.ops.object.mode_set(mode='OBJECT')
        
        copied_model.data.materials.clear()
        copied_model.data.materials.append(shared_material)
        
        processed_models.append(source_model)
        duplicate_models.append(copied_model)
    
    bpy.ops.object.select_all(action='DESELECT')
    for model in duplicate_models:
        model.select_set(True)
    new_context.view_layer.objects.active = duplicate_models[0]
    
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
    
    baked_image = bpy.data.images.new(name="FinalBakedTexture", width=1024, height=1024, alpha=False)
    baked_image.generated_color = (1.0, 1.0, 1.0, 1.0)
    
    result_texture_node = shared_material.node_tree.nodes.new(type='ShaderNodeTexImage')
    result_texture_node.interpolation = 'Closest'
    result_texture_node.image = baked_image
    shared_material.node_tree.links.new(result_texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    for source_model, copied_model in zip(processed_models, duplicate_models):
        bpy.ops.object.select_all(action='DESELECT')
        source_model.select_set(True)
        copied_model.select_set(True)
        new_context.view_layer.objects.active = copied_model
        
        shared_material.node_tree.nodes.active = result_texture_node
        
        try:
            bpy.ops.object.bake(type='DIFFUSE', use_clear=False, margin=16)
            print(f"烘焙贴图完成: {copied_model.name}")
        except Exception as e:
            print(f"烘焙贴图失败: {e}")
            bpy.data.objects.remove(copied_model)
            continue

    baked_image.filepath_raw = f"//Combined_Baked.png"
    baked_image.file_format = 'PNG'
    baked_image.save()
    print(f"所有对象的贴图保存完成")
    
    for model in processed_models:
        bpy.data.objects.remove(model)

class RetopologizeAndBakeOperator(bpy.types.Operator):
    bl_idname = "object.retopologize_and_bake_without_remesh"
    bl_label = "Retopologize and Bake"
    
    def execute(self, new_context):
        retopologize_and_bake_without_remesh_color(new_context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RetopologizeAndBakeOperator)
def unregister():
    bpy.utils.unregister_class(RetopologizeAndBakeOperator)
