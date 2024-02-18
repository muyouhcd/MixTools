import bpy
import os
import math
from bpy.props import PointerProperty


#导出函数

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

def prepare_obj_export(self, obj):
    print(f"正在记录 {obj.name} 的原始参数")
    original_scale = obj.scale.copy()
    original_rotation = obj.rotation_euler.copy()
    original_location = obj.location.copy()

    print(f"正在调整 {obj.name} 的比例")

#导出前应用的缩放
    obj.scale *= 100
    radians = math.radians(-90)  # 转换为弧度
    obj.rotation_euler = (radians, 0, 0)

    print(f"正在更新视图")
    bpy.context.view_layer.update()

    print(f"正在应用选定物体的变换")
    self.apply_transform_to_descendants(obj)

    return original_scale, original_rotation, original_location

def export_fbx(self, obj, dest_path, col_mark=False, scale_factor=1, rotation_euler=None):
    if col_mark:
        fbx_file_ext = "_col.fbx"
    else:
        fbx_file_ext = ".fbx"
    
    fbx_file_path = os.path.join(dest_path, obj.name.split('_col')[0] + fbx_file_ext)
    print(f"设置FBX文件的导出路径为：{fbx_file_path}")

    print(f"开始导出至：{fbx_file_path}")
    
    if rotation_euler:
        obj.rotation_euler = rotation_euler
    bpy.ops.export_scene.fbx(
        filepath=fbx_file_path,
        use_selection=True,
        global_scale=scale_factor,
        axis_forward='-Z',  # 调整以匹配Unity的坐标系
        axis_up='Y'  # 调整以匹配Unity的坐标系
    )
    print(f"导出完成：{fbx_file_path}")

def restore_obj_import(self, obj, original_scale, original_rotation, original_location):
    print(f"开始恢复 {obj.name} 的旋转角度、缩放和位置")
    obj.rotation_euler = original_rotation
    obj.scale = original_scale
    obj.location = original_location
    bpy.context.view_layer.update()

    print(f"{obj.name} 的状态已恢复")

#按照顶级父物体导出
class ExportFbxByParent(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent"
    bl_label = "按照顶级父物体导出FBX"

    def apply_transform_to_descendants(self, obj):
        """递归地为指定对象及其所有子对象应用变换，忽略'_col'的对象及其所有子对象。"""
        if '_col' not in obj.name:
            obj.select_set(True)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            for child in obj.children:
                self.apply_transform_to_descendants(child)

    def print_mesh_names(self, obj):
        """打印物体及其所有子对象的mesh名称（如果有）。"""
        if obj.type == 'MESH':
            print(f"Mesh object: {obj.name}")
        for child in obj.children:
            self.print_mesh_names(child)


    def select_children_except_col(self, obj):
        """递归地选择对象的子对象，忽略'_col'的对象及其所有子对象"""
        for child in obj.children:
            if '_col' in child.name:
                continue
            else:
                child.select_set(True)
                self.select_children_except_col(child)

    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        parents = []
        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                parents.append(obj)

        for obj in parents:
            # 如果物体名称包含'_col'，则跳过这个物体
            if '_col' in obj.name:
                continue

            bpy.ops.object.select_all(action='DESELECT')
            self.select_children_except_col(obj)

            print(f"准备导出：{obj.name}")
            self.print_mesh_names(obj)
            original_scale, original_rotation, original_location = prepare_obj_export(self, obj)

            print(f"开始导出：{obj.name}")
            export_fbx(self, obj, dest_path, col_mark=False, scale_factor=0.01, rotation_euler=(math.radians(90), 0, 0))

            print(f"恢复对象：{obj.name}")
            restore_obj_import(self, obj, original_scale, original_rotation, original_location)

        print("所有导出操作已结束")
        return {'FINISHED'}
    
#导出碰撞盒
class ExportFbxByColMark(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_col_mark"
    bl_label = "按_col标记及其父级链导出FBX"

    def apply_transform_to_descendants(self, obj):
        """递归地为指定当前对象及其所有子对象应用变换。"""
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        for child in obj.children:
            self.apply_transform_to_descendants(child)

    def execute(self, context):
        # 检查路径
        check_result, dest_path = check_dir(self, context)
        if not check_result:
            return {'CANCELLED'}

        # 找出所有包含 "_col" 的对象并追溯父级链，然后分别导出
        # 找出所有包含 "_col" 的对象并追溯到最高级的父级，然后分别导出

        for col_obj in bpy.context.scene.objects:
            if '_col' in col_obj.name:
                # Get the highest level parent of the "_col" object
                highest_parent = col_obj
                while highest_parent.parent is not None:
                    highest_parent = highest_parent.parent

                bpy.ops.object.select_all(action='DESELECT')

                # Select the highest level parent and all its descendants
                highest_parent.select_set(True)
                for descendant in highest_parent.children:
                    descendant.select_set(True)  # recursively select all descendants, if any

                print(f"准备导出：{highest_parent.name}")
                original_scale, original_rotation, original_location = prepare_obj_export(self, highest_parent)

                print(f"开始导出：{highest_parent.name}")
                export_fbx(self, highest_parent, dest_path, col_mark=True, scale_factor=0.01, rotation_euler=(math.radians(90), 0, 0))

                print(f"恢复对象：{highest_parent.name}")
                restore_obj_import(self, highest_parent, original_scale, original_rotation, original_location)
        print("所有导出操作已结束")
        return {'FINISHED'}

# 按照集合导出fbx
class ExportFbxByCollection(bpy.types.Operator):
    bl_idname = "object.miao_output_fbx_as_collection"
    bl_label = "按集合导出fbx"

    def execute(self, context):

        # 设置导出fbx文件的路径
        export_dir = bpy.path.abspath(context.scene.export_directory)

        def MoveOutside(mesh_obj):
            mesh_obj.select_set(True)
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
            # 减去和添加相同的角度，只是为了在减去角度后进行一个转换操作
            radians = math.radians(90)
            mesh_obj.rotation_euler.x -= radians
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            mesh_obj.rotation_euler.x += radians

        def has_mesh_descendants(obj):
            if any(child.type == 'MESH' for child in obj.children):
                return True
            for child in obj.children:
                if has_mesh_descendants(child):
                    return True
            return False

        def CleanEmpty(obj):
            empty_objects_to_delete = [child for child in obj.children if child.type == 'EMPTY' and not has_mesh_descendants(child)]
            # 删除这些空物体
            for obj in empty_objects_to_delete:
                bpy.data.objects.remove(obj)

        # 遍历所有集合
        for collection in bpy.data.collections:
            # 创建集合文件夹
            collection_dir = os.path.join(export_dir, collection.name)
            os.makedirs(collection_dir, exist_ok=True)  # 与之前的代码相同，但更简洁

            # 遍历集合内所有物体
            for obj in collection.objects:
                # 判断当前物体是否可以导出为fbx
                if obj.type not in {'MESH', 'ARMATURE'}:
                    continue

                # 选择当前物体
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                MoveOutside(obj)
                CleanEmpty(obj)

                # 导出fbx文件
                fbx_path = os.path.join(collection_dir, obj.name + ".fbx")
                bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, global_scale=0.01) # <-- scale factor
                obj.rotation_euler = (math.radians(0), 0, 0) # <-- rotation

            bpy.context.view_layer.objects.active = None  # 当完成一个对象的处理后，去掉活动物体

        print("All objects in collections have been exported as FBX files to " + export_dir)

        return {'FINISHED'}
    

def register():
    bpy.utils.register_class(ExportFbxByParent)
    bpy.utils.register_class(ExportFbxByColMark)
    bpy.utils.register_class(ExportFbxByCollection)

def unregister():
    bpy.utils.unregister_class(ExportFbxByParent)
    bpy.utils.unregister_class(ExportFbxByColMark)
    bpy.utils.unregister_class(ExportFbxByCollection)
    