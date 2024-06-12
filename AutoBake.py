import bpy

def retopologize_and_bake_color(context):
    # 获取选中的对象
    selected_objects = context.selected_objects
    if len(selected_objects) < 1:
        print("请至少选择一个对象。")
        return
    
    # 创建一个新的材质，并命名为"SharedMaterial"
    new_material = bpy.data.materials.new(name="SharedMaterial")
    
    # 启用节点
    new_material.use_nodes = True
    nodes = new_material.node_tree.nodes
    links = new_material.node_tree.links
    
    # 删除现有材质中的所有节点
    for node in nodes:
        nodes.remove(node)
        
    # 创建输出节点、Principled BSDF节点和图像纹理节点，并建立链接
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    principled_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    texture_node = nodes.new(type='ShaderNodeTexImage')
    
    links.new(principled_bsdf.outputs['BSDF'], output_node.inputs['Surface'])
    links.new(texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    new_material.node_tree.nodes.active = texture_node

    # 保存处理过的对象列表和重复对象列表
    processed_objects = []
    duplicate_objects = []
    
    # 处理每一个选中的对象
    for original_obj in selected_objects:
        if not original_obj.data or not original_obj.data.polygons:
            print(f"忽略空物体: {original_obj.name}")
            continue
        
        if not original_obj.data.materials:
            print(f"原始对象没有材质: {original_obj.name}")
            continue
        
        print(f"正在处理对象: {original_obj.name}")

        # 取消所有选择，并复制当前对象
        bpy.ops.object.select_all(action='DESELECT')
        original_obj.select_set(True)
        bpy.ops.object.duplicate()
        duplicate_obj = bpy.context.selected_objects[0]
        
        # 将复制的对象设为活跃对象并添加REMESH修改器
        context.view_layer.objects.active = duplicate_obj
        bpy.ops.object.modifier_add(type='REMESH')
        remesh_modifier = duplicate_obj.modifiers[-1]
        remesh_modifier.name = "TempRemesh"
        remesh_modifier.octree_depth = 1
        remesh_modifier.use_smooth_shade = False
        remesh_modifier.mode = 'SHARP'
        
        try:
            # 应用REMESH修改器
            bpy.ops.object.modifier_apply(modifier="TempRemesh")
            print(f"应用REMESH到: {duplicate_obj.name}")
        except Exception as e:
            print(f"应用REMESH修改器失败: {e}")
            bpy.data.objects.remove(duplicate_obj)
            continue

        # 设定UV智能投影展开
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
        
        # 清除和添加新的共享材质
        duplicate_obj.data.materials.clear()
        duplicate_obj.data.materials.append(new_material)
        
        processed_objects.append(original_obj)
        duplicate_objects.append(duplicate_obj)
    
    # 合并所有重拓扑对象的UV
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
    
    # 设置烘焙类型为漫反射并设置烘焙参数
    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
    bpy.context.scene.render.bake.use_pass_direct = False
    bpy.context.scene.render.bake.use_pass_indirect = False
    bpy.context.scene.render.bake.use_pass_color = True
    
    # 创建一个新的图像用于保存最终烘焙结果
    final_image = bpy.data.images.new(name="FinalBakedTexture", width=1024, height=1024, alpha=False)
    final_image.generated_color = (1.0, 1.0, 1.0, 1.0)
    
    # 将最终图像节点添加到材质节点树中，并连接到Principled BSDF节点的基础颜色输入
    final_texture_node = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
    final_texture_node.interpolation = 'Closest'
    final_texture_node.image = final_image
    new_material.node_tree.links.new(final_texture_node.outputs['Color'], principled_bsdf.inputs['Base Color'])
    
    # 对每一对原始对象和重复对象进行烘焙
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

    # 保存最终的烘焙图像
    final_image.filepath_raw = f"//Combined_Baked.png"
    final_image.file_format = 'PNG'
    final_image.save()
    print(f"所有对象的贴图保存完成")
    
    # 删除原始对象
    for obj in processed_objects:
        bpy.data.objects.remove(obj)

# 定义一个自定义的Blender操作符
class RetopologizeAndBakeOperator(bpy.types.Operator):
    bl_idname = "object.retopologize_and_bake"
    bl_label = "Retopologize and Bake"
    
    def execute(self, context):
        retopologize_and_bake_color(context)
        return {'FINISHED'}

# 注册和解除注册功能
def register():
    bpy.utils.register_class(RetopologizeAndBakeOperator)

def unregister():
    bpy.utils.unregister_class(RetopologizeAndBakeOperator)


if __name__ == "__main__":
    register()