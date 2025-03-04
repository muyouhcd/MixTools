import bpy
import os
import math

# 导出目录属性
bpy.types.Scene.export_directory = bpy.props.StringProperty(
    name="Export Directory",
    description="Directory where the exported files will be written",
    subtype='DIR_PATH'
)

def check_dir(self, context):
    dest_path = bpy.path.abspath(context.scene.export_directory)
    if not os.path.isabs(dest_path):
        self.report({'ERROR'}, "需要提供绝对路径，脚本将终止。")
        return False, None
    elif not os.path.exists(dest_path):
        self.report({'ERROR'}, "提供的路径不存在，脚本将终止。")
        return False, None
    return True, dest_path
def prepare_obj_export(obj, recursion):
    print(f"正在记录 {obj.name} 的原始参数")
    original_state = {
        'scale': obj.scale.copy(),
        'rotation': obj.rotation_euler.copy(),
        'location': obj.location.copy()
    }

    print(f"正在调整 {obj.name} 的比例")
    obj.scale *= 100
    obj.rotation_euler = (math.radians(-90), 0, 0)  # 转换为弧度

    print(f"正在更新视图")
    bpy.context.view_layer.update()
    bpy.ops.object.make_single_user_operator()
    print(f"正在应用选定物体的变换")
    if recursion:
        apply_transform_to_descendants(obj)
    return original_state

def export_fbx(obj, dest_path):
    fbx_file_ext = ".fbx"
    fbx_file_path = os.path.join(dest_path, obj.name + fbx_file_ext)

    print(f"设置FBX文件的导出路径为：{fbx_file_path}")
    print(f"开始导出至：{fbx_file_path}")


    obj.rotation_euler = (math.radians(90), 0, 0)

    bpy.ops.export_scene.fbx(
        filepath=fbx_file_path,
        use_selection=True,
        global_scale=0.01,
        axis_forward='-Z',  # 调整以匹配Unity的坐标系
        axis_up='Y',  # 调整以匹配Unity的坐标系
        add_leaf_bones=False ,
        armature_nodetype = 'NULL'
    )

    print(f"导出完成：{fbx_file_path}")

def export_fbx_max(obj, dest_path):
    fbx_file_ext = ".fbx"
    fbx_file_path = os.path.join(dest_path, obj.name + fbx_file_ext)

    print(f"设置MAX FBX文件的导出路径为：{fbx_file_path}")
    print(f"开始导出至：{fbx_file_path}")

    obj.rotation_euler = (math.radians(90), 0, 0)

    bpy.ops.export_scene.fbx(
        filepath=fbx_file_path,
        use_selection=True,
        global_scale=0.01,
        axis_forward='-Z',  # 调整以匹配Unity的坐标系
        axis_up='Y',  # 调整以匹配Unity的坐标系
        add_leaf_bones=False ,
        armature_nodetype = 'NULL',
        bake_anim=True,
        apply_unit_scale=True,
        
    )

    print(f"导出完成：{fbx_file_path}")

def apply_transform_to_descendants(obj):
    if obj.data and obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

class ExportFbxByParent(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent"
    bl_label = "按照顶级父物体导出FBX"

    def select_children(self, obj):
        for child in obj.children:
            child.select_set(True)
            self.select_children(child)
            print("selected: " + child.name)

    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]

        # 禁用自动更新
        bpy.context.view_layer.update()

        for obj in parents:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            self.select_children(obj)

            prepare_obj_export(obj, True)
            
            selected_objects = [o.name for o in bpy.context.selected_objects]
            print(f"Selected objects for export: {selected_objects}")
            if not selected_objects:
                print("No objects selected for export.")
                continue
            export_fbx(obj, dest_path)

        # 最后统一更新视图
        bpy.context.view_layer.update()
        print("所有导出操作已结束")
        return {'FINISHED'}

class ExportFbxByParentMax(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent_max"
    bl_label = "按照顶级父物体导出FBX"

    def select_children(self, obj):
        for child in obj.children:
            child.select_set(True)
            self.select_children(child)
            print("selected: " + child.name)


    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]

        # 禁用自动更新
        bpy.context.view_layer.update()

        for obj in parents:
            
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            self.select_children(obj)

            prepare_obj_export(obj, True)

            selected_objects = [o.name for o in bpy.context.selected_objects]
            print(f"Selected objects for export: {selected_objects}")
            if not selected_objects:
                print("No objects selected for export.")
                continue

            export_fbx_max(obj, dest_path)

        # 最后统一更新视图
        bpy.context.view_layer.update()
        print("所有导出操作已结束")
        return {'FINISHED'}

class ExportFbxByMesh(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_mesh"
    bl_label = "按Mesh导出FBX"

    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 获取所有顶级父物体
        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]

        # 禁用自动更新
        bpy.context.view_layer.update()

        for parent in parents:
            for obj in parent.children:
                if obj.type == 'MESH':
                    # 取消选择所有对象
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    # 选择当前的 mesh 对象
                    obj.select_set(True)

                    # 选择其他所有非 mesh 类型的对象
                    for other_obj in bpy.context.scene.objects:
                        if other_obj.type != 'MESH':
                            other_obj.select_set(True)

                    # 设置导出文件路径
                    file_path = os.path.join(dest_path, f"{parent.name}_{obj.name}.fbx")

                    # 使用 Blender 的 FBX 导出操作
                    bpy.ops.export_scene.fbx(
                        filepath=file_path,
                        use_selection=True,
                        global_scale=0.01,
                        apply_unit_scale=True,
                        axis_forward='-Z',
                        axis_up='Y',
                        use_space_transform=True,
                        bake_space_transform=True,
                        object_types={'MESH', 'ARMATURE', 'EMPTY'},  # 包含骨骼和空物体
                        mesh_smooth_type='FACE'
                    )



        # 更新视图层
        bpy.context.view_layer.update()
        print("所有导出操作已结束")
        return {'FINISHED'}

# 导出碰撞盒
class ExportFbxByColMark(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_col_mark"
    bl_label = "按_col标记及其父级链导出FBX"

    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 找出所有包含 "_col" 的对象并追溯父级链，然后分别导出
        for col_obj in bpy.context.scene.objects:
            if '_col' in col_obj.name:
                highest_parent = col_obj
                while highest_parent.parent is not None:
                    highest_parent = highest_parent.parent

                bpy.ops.object.select_all(action='DESELECT')

                # 选择最高级父对象和它的所有子孙对象
                highest_parent.select_set(True)
                for descendant in highest_parent.children:
                    descendant.select_set(True)

                print(f"准备导出：{highest_parent.name}")


                print(f"开始导出：{highest_parent.name}")
                export_fbx(highest_parent, dest_path, col_mark=True, scale_factor=0.01, rotation_euler=(math.radians(90), 0, 0))

                print(f"恢复对象：{highest_parent.name}")


        # 最后统一更新视图
        bpy.context.view_layer.update()
        print("所有导出操作已结束")
        return {'FINISHED'}
# 按集合导出FBX
class ExportFbxByCollection(bpy.types.Operator):
    bl_idname = "object.miao_output_fbx_as_collection"
    bl_label = "按集合导出FBX"

    def execute(self, context):
        # 设置导出FBX文件的路径
        check_result, export_dir = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        for collection in bpy.data.collections:
            collection_dir = os.path.join(export_dir, collection.name)
            os.makedirs(collection_dir, exist_ok=True)

            for obj in collection.objects:
                if obj.type not in {'MESH', 'ARMATURE'}:
                    continue
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                fbx_path = os.path.join(collection_dir, obj.name + ".fbx")
                bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, global_scale=0.01)

        # 最后统一更新视图
        bpy.context.view_layer.update()
        print("All objects in collections have been exported as FBX files to " + export_dir)
        return {'FINISHED'}
    

class ExporteObjOperator(bpy.types.Operator):
  bl_label = "批量导出Obj"
  bl_idname = "object.export_objs"

  def execute(self, context):
    
    output_dir = context.scene.export_directory
    
    selected_objects = context.selected_objects
    
    if not selected_objects:
      self.report({'INFO'}, "No objects selected")
      return {'FINISHED'}

    for obj in selected_objects:
        
      obj_name = obj.name
      export_path = os.path.join(output_dir, obj_name + ".obj")
    
      bpy.ops.object.select_all(action='DESELECT')
      obj.select_set(True)
      bpy.context.view_layer.objects.active = obj
      bpy.ops.export_scene.obj(
        filepath = export_path,
        check_existing=True, 
        axis_forward='-Z', 
        axis_up='Y', 
        use_selection=True, 
        use_animation=False, 
        use_mesh_modifiers=True, 
        use_edges=True, 
        use_smooth_groups=False, 
        use_smooth_groups_bitflags=False, 
        use_normals=True, 
        use_uvs=True, 
        use_materials=True, 
        use_triangles=False, 
        use_nurbs=False, 
        use_vertex_groups=False, 
        use_blen_objects=True, 
        group_by_object=False, 
        group_by_material=False, 
        keep_vertex_order=True, 
        global_scale=1, 
        path_mode='COPY',
      )

      self.report({'INFO'}, f"Exported {obj_name} to {export_path}")
      
    return {'FINISHED'}

def register():
    bpy.utils.register_class(ExportFbxByParent)
    bpy.utils.register_class(ExportFbxByColMark)
    bpy.utils.register_class(ExportFbxByCollection)
    bpy.utils.register_class(ExportFbxByParentMax)
    bpy.utils.register_class(ExportFbxByMesh)
    bpy.utils.register_class(ExporteObjOperator)
def unregister():
    bpy.utils.unregister_class(ExportFbxByParent)
    bpy.utils.unregister_class(ExportFbxByColMark)
    bpy.utils.unregister_class(ExportFbxByCollection)
    bpy.utils.unregister_class(ExportFbxByParentMax)
    bpy.utils.unregister_class(ExportFbxByMesh)
    bpy.utils.unregister_class(ExporteObjOperator)

