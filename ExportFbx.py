import bpy
import os
import math

# 导出目录属性
bpy.types.Scene.export_directory = bpy.props.StringProperty(
    name="Export Directory",
    description="Directory where the exported files will be written",
    subtype='DIR_PATH'
)

changerotation = 90
changescale = 100

# 检查导出目录是否有效
def check_dir(self, context):
    dest_path = bpy.path.abspath(context.scene.export_directory)
    if not os.path.isabs(dest_path):
        self.report({'ERROR'}, "需要提供绝对路径，脚本将终止。")
        return False, None
    elif not os.path.exists(dest_path):
        self.report({'ERROR'}, "提供的路径不存在，脚本将终止。")
        return False, None
    return True, dest_path

# 准备导出前的对象变换
# 准备导出前的对象变换
def prepare_obj_export(obj):
    print(f"正在记录 {obj.name} 的原始参数")
    original_state = {
        'scale': obj.scale.copy(),
        'rotation': obj.rotation_euler.copy(),
        'location': obj.location.copy()
    }

    print(f"正在调整 {obj.name} 的比例")
    obj.scale *= changescale
    obj.rotation_euler = (math.radians(-changerotation), 0, 0)  # 转换为弧度
    # 应用变换到所有子对象
    apply_transform_to_descendants(obj)

    return original_state

# 恢复对象变换
def restore_obj_import(obj, original_state):
    print(f"开始恢复 {obj.name} 的旋转角度、缩放和位置")
    obj.scale = original_state['scale']
    obj.rotation_euler = original_state['rotation']
    obj.location = original_state['location']
    # 不立即更新视图
    print(f"{obj.name} 的状态已恢复")

# 导出FBX文件
def export_fbx(obj, dest_path, col_mark=False, scale_factor=1, rotation_euler=None):
    fbx_file_ext = "_col.fbx" if col_mark else ".fbx"
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

# 递归地为指定对象及其所有子对象应用变换，忽略'_col'的对象及其所有子对象
def apply_transform_to_descendants(obj):
    if '_col' not in obj.name:
        make_single_user(obj)  # 将对象变为单用户对象
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        # for child in obj.children:
        #     apply_transform_to_descendants(child)  # 递归处理子对象

def make_single_user(obj):
    """将对象变为单用户对象"""
    if obj.data and obj.data.users > 1:
        obj.data = obj.data.copy()

# 按照顶级父物体导出
class ExportFbxByParent(bpy.types.Operator):
    bl_idname = "scene.export_fbx_by_parent"
    bl_label = "按照顶级父物体导出FBX"

    def select_children_except_col(self, obj):
        """递归地选择对象的子对象，忽略'_col'的对象及其所有子对象"""
        for child in obj.children:
            if '_col' not in child.name:
                child.select_set(True)
                self.select_children_except_col(child)

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
            self.select_children_except_col(obj)

            print(f"准备导出：{obj.name}")
            original_state = prepare_obj_export(obj)

            print(f"开始导出：{obj.name}")
            export_fbx(obj, dest_path, scale_factor=0.01, rotation_euler=(math.radians(90), 0, 0))

            print(f"恢复对象：{obj.name}")
            restore_obj_import(obj, original_state)

        # 最后统一更新视图
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
                original_state = prepare_obj_export(highest_parent)

                print(f"开始导出：{highest_parent.name}")
                export_fbx(highest_parent, dest_path, col_mark=True, scale_factor=0.01, rotation_euler=(math.radians(90), 0, 0))

                print(f"恢复对象：{highest_parent.name}")
                restore_obj_import(highest_parent, original_state)

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

                original_state = prepare_obj_export(obj)

                fbx_path = os.path.join(collection_dir, obj.name + ".fbx")
                bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True, global_scale=0.01)

                restore_obj_import(obj, original_state)

        # 最后统一更新视图
        bpy.context.view_layer.update()
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

if __name__ == "__main__":
    register()
