import bpy
import os
from bpy.props import StringProperty
from bpy.types import Operator

class MIAO_OT_batch_import_fbx(Operator):
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

def register():
    bpy.utils.register_class(MIAO_OT_batch_import_fbx)

def unregister():
    bpy.utils.unregister_class(MIAO_OT_batch_import_fbx)

if __name__ == "__main__":
    register()
