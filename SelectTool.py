import bpy
import tempfile
import os

#选择尺寸超过指定值的物体
def is_object_size_above_threshold(obj, threshold):
    dimensions = obj.dimensions
    max_size = max(dimensions)
    return max_size > threshold

def is_object_size_below_threshold(obj, threshold):
    dimensions = obj.dimensions
    max_size = max(dimensions)
    return max_size < threshold

def has_texture(obj):
    for mat_slot in obj.material_slots:
        material = mat_slot.material
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    return True
    return False
    
class SelectLargeObjectsOperator(bpy.types.Operator):
    bl_idname = "object.select_large_objects"
    bl_label = "选择过大物体"
    bl_options = {'REGISTER', 'UNDO'}

    threshold_meters: bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters",
        default=8.0,
        min=0.0
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and is_object_size_above_threshold(obj, self.threshold_meters):
                obj.select_set(True)
        return {'FINISHED'}

class SelectSmallObjectsOperator(bpy.types.Operator):
    bl_idname = "object.select_small_objects"
    bl_label = "选择过小物体"
    bl_options = {'REGISTER', 'UNDO'}

    threshold_meters: bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters",
        default=1.0,
        min=0.0
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and is_object_size_below_threshold(obj, self.threshold_meters):
                obj.select_set(True)
        return {'FINISHED'}
        
class SelectObjectsWithoutTextureOperator(bpy.types.Operator):
    bl_idname = "object.select_objects_without_texture"
    bl_label = "选择没有贴图的物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and not has_texture(obj):
                obj.select_set(True)
        return {'FINISHED'}

class SelectObjectsWithoutVertexGroupsOperator(bpy.types.Operator):
    bl_idname = "object.select_objects_without_vertex_groups"
    bl_label = "选择没有顶点组的物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前选中的物体
        selected_objects = [obj for obj in context.selected_objects]
        
        # 取消所有选择
        bpy.ops.object.select_all(action='DESELECT')
        
        # 从当前选中的物体中筛选出没有顶点组的物体
        for obj in selected_objects:
            if obj.type == 'MESH' and len(obj.vertex_groups) == 0:
                obj.select_set(True)
                
        return {'FINISHED'}

def update_large_objects_threshold(self, context):
    bpy.types.Scene.select_large_objects_threshold = context.scene.select_large_objects_threshold

def update_small_objects_threshold(self, context):
    bpy.types.Scene.select_small_objects_threshold = context.scene.select_small_objects_threshold


# 按体积筛选物体
class SelectByVolume(bpy.types.Operator):
    bl_idname = "object.mian_select_by_volume"
    bl_label = "按体积筛选物体"

    filter_mode: bpy.props.EnumProperty(
        name="Filter Mode",
        description="筛选大于或小于给定体积的物体",
        items=[
            ("GREATER_THAN", "大于", "选择体积大于给定阈值的物体"),
            ("LESS_THAN", "小于", "选择体积小于给定阈值的物体")
        ],
        default="GREATER_THAN",
    )

    volume_threshold: bpy.props.FloatProperty(
        name="体积阈值",
        description="根据筛选模式选择大于或小于此值的物体",
        default=0.0,
        min=0.0,
        max=float('inf'),
        soft_min=0,
        soft_max=1000.0,
        step=1,
        precision=2,
    )

    select: bpy.props.BoolProperty(
        name="选择物体",
        description="若选中，满足条件的物体将被选择；若不选中，满足条件的物体将被取消选择",
        default=True,
    )

    def execute(self, context):
        scene = bpy.context.scene

        for obj in scene.objects:
            if obj.type == "MESH":
                volume = obj.dimensions.x * obj.dimensions.y * obj.dimensions.z

                if self.filter_mode == "GREATER_THAN":
                    condition = volume > self.volume_threshold
                else:
                    condition = volume < self.volume_threshold

                if condition:
                    obj.select_set(self.select)
                else:
                    obj.select_set(not self.select)
        return {"FINISHED"}

# 根据名称列表保留物体并删除其他物体
class SelectAndDeleteByNameListOperator(bpy.types.Operator):
    bl_idname = "object.select_and_delete_by_name_list"
    bl_label = "按名称列表筛选物体"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        # 使用场景中的属性而不是operator的属性
        names_list_string = scene.object_names_list
        delete_lights = scene.delete_lights_option
        show_report = scene.show_report_option
        
        # 将字符串拆分为列表，并去除空行和多余空格
        names_list = [name.strip() for name in names_list_string.split("\n") if name.strip()]
        
        # 检查场景中匹配的物体
        scene_objects = {obj.name for obj in bpy.data.objects}  # 将场景中所有物体名称存入集合
        matched_objects = []  # 匹配的物体名称
        unmatched_objects = []  # 未匹配的物体名称
        
        # 遍历名称列表并分类
        for name in names_list:
            if name in scene_objects:
                matched_objects.append(name)
            else:
                unmatched_objects.append(name)
        
        # 首先创建要删除的对象列表
        objects_to_delete = []
                
        # 递归删除物体及其所有子物体
        def collect_object_with_children(obj, to_delete_list):
            # 创建一个静态列表，防止直接修改 children 集合
            children = [child for child in obj.children]
            for child in children:
                collect_object_with_children(child, to_delete_list)  # 递归收集子物体
            # 将当前对象添加到删除列表
            to_delete_list.append(obj)
        
        # 如果选择删除灯光，收集所有灯光
        if delete_lights:
            for obj in bpy.data.objects:
                if obj.type == 'LIGHT':
                    objects_to_delete.append(obj)
        
        # 收集所有要删除的顶级父物体及其子物体
        for obj in bpy.data.objects:
            if obj.parent is None and obj.type != 'LIGHT':  # 检查是否为顶级父物体（非灯光）
                if obj.name not in matched_objects:  # 如果不在匹配的名称列表中
                    collect_object_with_children(obj, objects_to_delete)  # 收集顶级父物体及其所有子物体
        
        # 最后一次性删除所有收集的对象
        for obj in objects_to_delete:
            if obj.name in bpy.data.objects:  # 再次检查对象是否仍存在
                bpy.data.objects.remove(obj, do_unlink=True)
        
        # 显示报告
        if show_report:
            self.report({'INFO'}, f"名称列表中的总物体数量：{len(names_list)}, 匹配的物体数量：{len(matched_objects)}, 未匹配的物体数量：{len(unmatched_objects)}")
            if unmatched_objects:
                print(f"未匹配物体：{', '.join(unmatched_objects)}")
            else:
                print("所有名称都匹配场景中的物体。")
            
        return {'FINISHED'}

# 临时函数：打开文本编辑器来编辑名称列表
def edit_names_list_in_text_editor(scene):
    # 创建一个临时文件来存储当前名称列表
    temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.txt')
    temp_file.write(scene.object_names_list)
    temp_file.close()
    
    # 使用操作系统的默认文本编辑器打开文件
    bpy.ops.wm.path_open(filepath=temp_file.name)
    
    # 存储临时文件路径以便稍后读取
    scene.temp_names_file_path = temp_file.name
    
    return {'FINISHED'}

# 从临时文件读取名称列表
def read_names_from_temp_file(scene):
    if hasattr(scene, 'temp_names_file_path') and os.path.exists(scene.temp_names_file_path):
        with open(scene.temp_names_file_path, 'r') as f:
            scene.object_names_list = f.read()
        # 删除临时文件
        os.unlink(scene.temp_names_file_path)
        scene.temp_names_file_path = ""
    return {'FINISHED'}

# 操作器：编辑名称列表
class EditNamesListOperator(bpy.types.Operator):
    bl_idname = "object.edit_names_list"
    bl_label = "编辑名称列表"
    bl_description = "在外部文本编辑器中编辑名称列表"
    
    def execute(self, context):
        edit_names_list_in_text_editor(context.scene)
        return {'FINISHED'}

# 操作器：从临时文件读取名称列表
class ReadNamesFromTempFileOperator(bpy.types.Operator):
    bl_idname = "object.read_names_from_temp_file"
    bl_label = "加载名称列表"
    bl_description = "从保存的文本文件加载名称列表"
    
    def execute(self, context):
        read_names_from_temp_file(context.scene)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(SelectLargeObjectsOperator)
    bpy.utils.register_class(SelectSmallObjectsOperator)
    bpy.utils.register_class(SelectObjectsWithoutTextureOperator)
    bpy.utils.register_class(SelectObjectsWithoutVertexGroupsOperator)
    bpy.types.Scene.select_large_objects_threshold = bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters for large objects",
        default=8.0,
        min=0.0,
        update=update_large_objects_threshold
    )
    bpy.types.Scene.select_small_objects_threshold = bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters for small objects",
        default=1.0,
        min=0.0,
        update=update_small_objects_threshold
    )
    bpy.utils.register_class(SelectByVolume)
    bpy.utils.register_class(SelectAndDeleteByNameListOperator)
    bpy.utils.register_class(EditNamesListOperator)
    bpy.utils.register_class(ReadNamesFromTempFileOperator)
    
    # 为按名称列表筛选功能添加属性
    bpy.types.Scene.object_names_list = bpy.props.StringProperty(
        name="物体名称列表",
        description="要保留的物体名称列表，每行一个名称",
        default="",
        subtype='FILE_NAME'  # 这个子类型通常有较大的显示区域
    )
    bpy.types.Scene.temp_names_file_path = bpy.props.StringProperty(
        name="临时名称文件路径",
        description="存储编辑中的名称列表的临时文件路径",
        default="",
        subtype='FILE_PATH'
    )
    bpy.types.Scene.delete_lights_option = bpy.props.BoolProperty(
        name="删除所有灯光",
        description="是否同时删除场景中的所有灯光",
        default=False
    )
    bpy.types.Scene.show_report_option = bpy.props.BoolProperty(
        name="显示报告",
        description="在控制台中显示匹配和未匹配的物体报告",
        default=True
    )



def unregister():
    # 注销操作符类
    bpy.utils.unregister_class(SelectSmallObjectsOperator)
    bpy.utils.unregister_class(SelectLargeObjectsOperator)
    bpy.utils.unregister_class(SelectObjectsWithoutTextureOperator)
    bpy.utils.unregister_class(SelectObjectsWithoutVertexGroupsOperator)
    bpy.utils.unregister_class(SelectByVolume)
    bpy.utils.unregister_class(SelectAndDeleteByNameListOperator)
    bpy.utils.unregister_class(EditNamesListOperator)
    bpy.utils.unregister_class(ReadNamesFromTempFileOperator)
    
    # 注销场景属性
    properties_to_remove = [
        "select_large_objects_threshold",
        "select_small_objects_threshold",
        "object_names_list",
        "temp_names_file_path",
        "delete_lights_option",
        "show_report_option"
    ]
    
    # 安全地删除所有属性
    for prop in properties_to_remove:
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass  # 如果属性不存在，就跳过

if __name__ == "__main__":
    register()