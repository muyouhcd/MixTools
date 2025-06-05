import bpy
import os
import math
import time  # 添加时间模块以便测量性能
import mathutils

# 导出配置类
class ExportConfig:
    def __init__(self, name, description, fbx_params=None, obj_params=None):
        self.name = name
        self.description = description
        self.fbx_params = fbx_params or {}
        self.obj_params = obj_params or {}

# 预定义导出配置
EXPORT_CONFIGS = {
    'Unity': ExportConfig(
        name="Unity默认(CM)",
        description="标准FBX导出配置，使用米作为单位",
        fbx_params={
            'axis_forward': '-Z',
            'axis_up': 'Y',
            'add_leaf_bones': False,
            'armature_nodetype': 'NULL',
            'bake_space_transform': True,
            'use_custom_props': False,
            'apply_unit_scale': True,
            'rotation': (90, 0, 0),
            'apply_rotation': True,
            'unit': 'cm'  # 单位：'m'=米, 'cm'=厘米, 'mm'=毫米
        }
    ),
    'max': ExportConfig(
        name="3ds Max默认配置(M)",
        description="针对3ds Max优化的FBX导出配置，使用厘米作为单位",
        fbx_params={
            'axis_forward': 'Y',
            'axis_up': 'Z',
            'add_leaf_bones': False,
            'armature_nodetype': 'NULL',
            'bake_anim': True,
            'apply_unit_scale': True,
            'bake_space_transform': True,
            'use_custom_props': False,
            'rotation': (90, 0, 0),
            'apply_rotation': False,
            'unit': 'm'
        }
    )
}

# 导出目录属性
bpy.types.Scene.export_directory = bpy.props.StringProperty(
    name="Export Directory",
    description="Directory where the exported files will be written",
    subtype='DIR_PATH'
)

# 添加清除父级选项
bpy.types.Scene.clear_parent_on_export = bpy.props.BoolProperty(
    name="清除父级关系",
    description="导出时清除顶级父级关系（保持变换）",
    default=False
)

# 批处理大小常量
BATCH_SIZE = 10

# 添加导出配置选择属性
bpy.types.Scene.export_config = bpy.props.EnumProperty(
    name="导出配置",
    description="选择导出配置",
    items=[(key, config.name, config.description) for key, config in EXPORT_CONFIGS.items()],
    default='Unity'
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
    # 记录原始参数
    original_state = {
        'scale': obj.scale.copy(),
        'rotation': obj.rotation_euler.copy(),
        'location': obj.location.copy()
    }

    # 调整比例
    obj.scale *= 100
    obj.rotation_euler = (math.radians(-90), 0, 0)

    # 更新视图
    bpy.context.view_layer.update()
    
    # 应用变换
    if recursion:
        apply_transform_to_descendants(obj)
    return original_state

def get_unit_scale(unit):
    """根据单位返回对应的缩放比例"""
    unit_scales = {
        'm': 1.0,    # 米
        'cm': 0.01,  # 厘米
        'mm': 0.001  # 毫米
    }
    return unit_scales.get(unit, 1.0)

def export_fbx(obj, dest_path, config_name='default'):
    fbx_file_ext = ".fbx"
    fbx_file_path = os.path.join(dest_path, obj.name + fbx_file_ext)

    # 获取配置
    config = EXPORT_CONFIGS[config_name]
    
    # 记录原始变换和父级关系
    original_scale = obj.scale.copy()
    original_rotation = obj.rotation_euler.copy()
    original_parent = obj.parent
    original_matrix = obj.matrix_world.copy()
    
    # 如果需要排除顶级空物体
    if bpy.context.scene.clear_parent_on_export and obj.type == 'EMPTY' and obj.parent is None:
        # 保存所有子物体的世界空间变换
        child_matrices = {}
        for child in obj.children:
            child_matrices[child] = child.matrix_world.copy()
        
        # 选择所有子物体
        bpy.ops.object.select_all(action='DESELECT')
        for child in obj.children:
            child.select_set(True)
        
        # 应用父物体的旋转到所有子物体
        rotation = config.fbx_params.get('rotation', (0, 0, 0))
        rotation_rad = (math.radians(rotation[0]), 
                       math.radians(rotation[1]), 
                       math.radians(rotation[2]))
        
        # 创建一个临时矩阵来存储旋转
        rotation_matrix = mathutils.Euler(rotation_rad).to_matrix().to_4x4()
        
        # 对每个子物体应用旋转
        for child in obj.children:
            # 获取相对于父物体的变换
            local_matrix = obj.matrix_world.inverted() @ child.matrix_world
            # 应用旋转
            rotated_matrix = rotation_matrix @ local_matrix
            # 更新子物体的变换
            child.matrix_world = obj.matrix_world @ rotated_matrix
            
            # 如果需要应用旋转变换
            if config.fbx_params.get('apply_rotation', True):
                bpy.context.view_layer.objects.active = child
                bpy.ops.object.transform_apply(rotation=True, scale=False, location=False)
        
        # 使用子物体名称作为文件名
        if len(obj.children) == 1:
            fbx_file_path = os.path.join(dest_path, obj.children[0].name + fbx_file_ext)
        else:
            fbx_file_path = os.path.join(dest_path, obj.name + "_children" + fbx_file_ext)
            
        # 获取单位缩放比例
        unit = config.fbx_params.get('unit', 'm')
        unit_scale = get_unit_scale(unit)
        
        # 更新导出参数
        export_params = config.fbx_params.copy()
        # 移除自定义参数
        export_params.pop('rotation', None)
        export_params.pop('apply_rotation', None)
        export_params.pop('unit', None)
        
        # 设置单位相关的参数
        export_params.update({
            'apply_unit_scale': True,  # 应用单位缩放
            'bake_space_transform': True,  # 烘焙空间变换
            'use_space_transform': True,  # 使用空间变换
            'global_scale': 1.0,  # 全局缩放设为1，让单位系统处理缩放
            'apply_scale_options': 'FBX_SCALE_ALL'  # 应用所有缩放
        })

        # 使用配置参数导出
        bpy.ops.export_scene.fbx(
            filepath=fbx_file_path,
            use_selection=True,
            **export_params
        )
        
        # 恢复子物体的原始变换
        for child in obj.children:
            child.matrix_world = child_matrices[child]
        
        return fbx_file_path
    
    # 如果不是顶级空物体，使用原有的导出逻辑
    # 获取单位缩放比例
    unit = config.fbx_params.get('unit', 'm')
    unit_scale = get_unit_scale(unit)
    
    # 获取旋转设置
    rotation = config.fbx_params.get('rotation', (0, 0, 0))
    apply_rotation = config.fbx_params.get('apply_rotation', True)
    
    # 应用配置中的旋转设置
    obj.rotation_euler = (math.radians(rotation[0]), 
                         math.radians(rotation[1]), 
                         math.radians(rotation[2]))

    # 如果需要应用旋转变换
    if apply_rotation:
        # 确保对象被选中
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        # 应用旋转变换
        bpy.ops.object.transform_apply(rotation=True, scale=False, location=False)
        # 重新选择对象
        obj.select_set(True)

    # 更新导出参数
    export_params = config.fbx_params.copy()
    # 移除自定义参数
    export_params.pop('rotation', None)
    export_params.pop('apply_rotation', None)
    export_params.pop('unit', None)
    
    # 设置单位相关的参数
    export_params.update({
        'apply_unit_scale': True,  # 应用单位缩放
        'bake_space_transform': True,  # 烘焙空间变换
        'use_space_transform': True,  # 使用空间变换
        'global_scale': 1.0,  # 全局缩放设为1，让单位系统处理缩放
        'apply_scale_options': 'FBX_SCALE_ALL'  # 应用所有缩放
    })

    # 使用配置参数导出
    bpy.ops.export_scene.fbx(
        filepath=fbx_file_path,
        use_selection=True,
        **export_params
    )

    # 恢复原始变换和父级关系
    obj.scale = original_scale
    obj.rotation_euler = original_rotation
    if original_parent is not None:
        obj.parent = original_parent
        obj.matrix_world = original_matrix

    return fbx_file_path

def export_fbx_max(obj, dest_path):
    return export_fbx(obj, dest_path, config_name='max')

def apply_transform_to_descendants(obj):
    # 创建一个副本而不是每次都深度复制数据
    if obj.data and obj.data.users > 1:
        obj.data = obj.data.copy()
    
    # 应用变换
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    
    # 递归处理子对象
    for child in obj.children:
        apply_transform_to_descendants(child)
        
class ExportFbxByParent(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent"
    bl_label = "按照顶级父物体导出FBX"

    def select_children(self, obj):
        for child in obj.children:
            child.select_set(True)
            self.select_children(child)

    def execute(self, context):
        start_time = time.time()  # 记录开始时间
        
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 获取所有顶级父物体
        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]
        
        # 获取选择的导出配置
        config_name = context.scene.export_config
        
        # 禁用不必要的自动更新，提高性能
        bpy.context.view_layer.update()
        
        # 批处理导出
        processed_count = 0
        total_count = len(parents)
        
        for i in range(0, total_count, BATCH_SIZE):
            batch = parents[i:i+BATCH_SIZE]
            self.report({'INFO'}, f"处理批次 {i//BATCH_SIZE + 1}/{math.ceil(total_count/BATCH_SIZE)}")
            
            for obj in batch:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                self.select_children(obj)

                prepare_obj_export(obj, True)
                
                selected_objects = [o.name for o in bpy.context.selected_objects]
                if not selected_objects:
                    continue
                    
                file_path = export_fbx(obj, dest_path, config_name)
                processed_count += 1
                
                # 每导出一个物体，更新进度
                self.report({'INFO'}, f"已导出 {processed_count}/{total_count}: {obj.name}")
                
            # 每批次后强制更新视图并释放内存
            bpy.context.view_layer.update()
            
        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"导出完成! 耗时: {elapsed_time:.2f}秒, 共导出{processed_count}个物体")
        return {'FINISHED'}

class ExportFbxByParentMax(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent_max"
    bl_label = "按照顶级父物体导出3ds Max兼容FBX"

    def select_children(self, obj):
        for child in obj.children:
            child.select_set(True)
            self.select_children(child)

    def execute(self, context):
        start_time = time.time()
        
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 获取所有顶级父物体
        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]
        
        # 禁用不必要的自动更新
        bpy.context.view_layer.update()
        
        # 批处理导出
        processed_count = 0
        total_count = len(parents)
        
        for i in range(0, total_count, BATCH_SIZE):
            batch = parents[i:i+BATCH_SIZE]
            self.report({'INFO'}, f"处理批次 {i//BATCH_SIZE + 1}/{math.ceil(total_count/BATCH_SIZE)}")
            
            for obj in batch:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                self.select_children(obj)

                prepare_obj_export(obj, True)
                
                selected_objects = [o.name for o in bpy.context.selected_objects]
                if not selected_objects:
                    continue
                    
                file_path = export_fbx_max(obj, dest_path)
                processed_count += 1
                
                # 每导出一个物体，更新进度
                self.report({'INFO'}, f"已导出 {processed_count}/{total_count}: {obj.name}")
                
            # 每批次后强制更新视图并释放内存
            bpy.context.view_layer.update()

        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"导出完成! 耗时: {elapsed_time:.2f}秒, 共导出{processed_count}个物体")
        return {'FINISHED'}

class ExportFbxByMesh(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_mesh"
    bl_label = "按Mesh导出FBX"

    def execute(self, context):
        start_time = time.time()
        
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 获取所有顶级父物体
        parents = [obj for obj in bpy.context.scene.objects if obj.parent is None]
        
        # 收集所有需要处理的网格对象
        mesh_objects = []
        for parent in parents:
            for obj in parent.children:
                if obj.type == 'MESH':
                    mesh_objects.append((parent, obj))
        
        # 批处理导出
        processed_count = 0
        total_count = len(mesh_objects)
        
        for i in range(0, total_count, BATCH_SIZE):
            batch = mesh_objects[i:i+BATCH_SIZE]
            self.report({'INFO'}, f"处理批次 {i//BATCH_SIZE + 1}/{math.ceil(total_count/BATCH_SIZE)}")
            
            for parent, obj in batch:
                # 取消选择所有对象
                bpy.ops.object.select_all(action='DESELECT')
                
                # 选择当前的 mesh 对象
                obj.select_set(True)

                # 选择非 mesh 类型的对象 (骨骼等)
                for other_obj in bpy.context.scene.objects:
                    if other_obj.type != 'MESH':
                        other_obj.select_set(True)

                # 设置导出文件路径
                file_path = os.path.join(dest_path, f"{parent.name}_{obj.name}.fbx")

                # 使用优化的参数导出
                bpy.ops.export_scene.fbx(
                    filepath=file_path,
                    use_selection=True,
                    global_scale=0.01,
                    apply_unit_scale=True,
                    axis_forward='-Z',
                    axis_up='Y',
                    use_space_transform=True,
                    bake_space_transform=True,
                    object_types={'MESH', 'ARMATURE', 'EMPTY'},
                    mesh_smooth_type='FACE',
                    use_custom_props=False,  # 不导出自定义属性
                    add_leaf_bones=False     # 不添加叶骨骼
                )
                
                processed_count += 1
                
                # 每导出一个物体，更新进度
                self.report({'INFO'}, f"已导出 {processed_count}/{total_count}: {parent.name}_{obj.name}")
                
            # 每批次后强制更新视图并释放内存
            bpy.context.view_layer.update()

        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"导出完成! 耗时: {elapsed_time:.2f}秒, 共导出{processed_count}个物体")
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

