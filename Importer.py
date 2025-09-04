import bpy
import os
from bpy.props import StringProperty
from bpy.types import Operator

class mian_OT_batch_import_fbx(Operator):
    """批量导入FBX文件"""
    bl_idname = "miao.batch_import_fbx"
    bl_label = "批量导入FBX"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(
        name="目录",
        description="选择包含FBX文件的目录",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        # 获取所有FBX文件
        fbx_files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith('.fbx'):
                    fbx_files.append(os.path.join(root, file))

        # 导入每个FBX文件
        for fbx_file in fbx_files:
            try:
                bpy.ops.import_scene.fbx(filepath=fbx_file)
                print(f"成功导入: {fbx_file}")
            except Exception as e:
                print(f"导入失败 {fbx_file}: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class mian_OT_batch_import_obj(Operator):
    """批量导入OBJ文件"""
    bl_idname = "miao.batch_import_obj"
    bl_label = "批量导入OBJ"
    bl_options = {'REGISTER', 'UNDO'}

    directory: StringProperty(
        name="目录",
        description="选择包含OBJ文件的目录",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        # 获取所有OBJ文件
        obj_files = []
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.lower().endswith('.obj'):
                    obj_files.append(os.path.join(root, file))

        # 导入每个OBJ文件
        for obj_file in obj_files:
            try:
                # 获取文件名（不包含扩展名）作为物体名称
                obj_name = os.path.splitext(os.path.basename(obj_file))[0]
                
                # 导入OBJ文件
                bpy.ops.import_scene.obj(filepath=obj_file)
                
                # 获取最后导入的物体并重命名
                imported_objects = [obj for obj in context.selected_objects]
                for obj in imported_objects:
                    obj.name = obj_name
                
                print(f"成功导入: {obj_file}")
            except Exception as e:
                print(f"导入失败 {obj_file}: {str(e)}")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def register():
    bpy.utils.register_class(mian_OT_batch_import_fbx)
    bpy.utils.register_class(mian_OT_batch_import_obj)

def unregister():
    bpy.utils.unregister_class(mian_OT_batch_import_fbx)
    bpy.utils.unregister_class(mian_OT_batch_import_obj)

if __name__ == "__main__":
    register()
