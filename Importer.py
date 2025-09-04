import bpy
import os
from bpy.props import StringProperty
from bpy.types import Operator

def get_unique_name(base_name):
    """
    获取一个唯一的名称，避免与现有对象重名
    
    参数:
    base_name: 基础名称
    返回:
    唯一的名称
    """
    # 检查基础名称是否已存在
    if base_name not in bpy.data.objects:
        return base_name
    
    # 如果存在，添加数字后缀直到找到唯一名称
    counter = 1
    while f"{base_name}.{counter:03d}" in bpy.data.objects:
        counter += 1
    
    return f"{base_name}.{counter:03d}"

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

        # 获取重命名选项
        rename_objects = context.scene.rename_imported_objects_to_filename
        
        # 添加详细的调试信息
        print(f"=== 调试信息 (miao.batch_import_fbx) ===")
        print(f"场景属性存在: {hasattr(context.scene, 'rename_imported_objects_to_filename')}")
        print(f"场景属性值: {getattr(context.scene, 'rename_imported_objects_to_filename', 'NOT_FOUND')}")
        print(f"重命名对象参数: {rename_objects}")
        print(f"=====================================")
        
        # 强制设置重命名选项为True进行测试
        if hasattr(context.scene, 'rename_imported_objects_to_filename'):
            print(f"强制设置重命名选项为True")
            context.scene.rename_imported_objects_to_filename = True
            rename_objects = True

        # 导入每个FBX文件
        for fbx_file in fbx_files:
            try:
                # 记录导入前的对象
                objects_before = set(context.scene.objects)
                
                # 导入FBX文件
                bpy.ops.import_scene.fbx(filepath=fbx_file)
                
                # 获取新导入的对象
                objects_after = set(context.scene.objects)
                imported_objects = list(objects_after - objects_before)
                
                # 根据选项决定是否重命名
                print(f"重命名选项状态: {rename_objects}")
                if rename_objects and imported_objects:
                    print(f"开始重命名顶级物体为文件名: {os.path.splitext(os.path.basename(fbx_file))[0]}")
                    # 获取文件名（不包含扩展名）
                    file_name = os.path.splitext(os.path.basename(fbx_file))[0]
                    
                    # 找到所有顶级物体（没有父级的物体）
                    top_level_objects = [obj for obj in imported_objects if obj.parent is None]
                    
                    # 重命名顶级物体
                    for i, obj in enumerate(top_level_objects):
                        if len(top_level_objects) == 1:
                            # 使用唯一名称检查
                            unique_name = get_unique_name(file_name)
                            obj.name = unique_name
                        else:
                            # 使用唯一名称检查
                            base_name = f"{file_name}_{i+1:02d}"
                            unique_name = get_unique_name(base_name)
                            obj.name = unique_name
                        if obj.data:
                            obj.data.name = obj.name
                
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

        # 获取重命名选项
        rename_objects = context.scene.rename_imported_objects_to_filename

        # 导入每个OBJ文件
        for obj_file in obj_files:
            try:
                # 记录导入前的对象
                objects_before = set(context.scene.objects)
                
                # 导入OBJ文件
                bpy.ops.import_scene.obj(filepath=obj_file)
                
                # 获取新导入的对象
                objects_after = set(context.scene.objects)
                imported_objects = list(objects_after - objects_before)
                
                # 根据选项决定是否重命名
                if rename_objects and imported_objects:
                    # 获取文件名（不包含扩展名）
                    file_name = os.path.splitext(os.path.basename(obj_file))[0]
                    
                    # 找到所有顶级物体（没有父级的物体）
                    top_level_objects = [obj for obj in imported_objects if obj.parent is None]
                    
                    # 重命名顶级物体
                    for i, obj in enumerate(top_level_objects):
                        if len(top_level_objects) == 1:
                            # 使用唯一名称检查
                            unique_name = get_unique_name(file_name)
                            obj.name = unique_name
                        else:
                            # 使用唯一名称检查
                            base_name = f"{file_name}_{i+1:02d}"
                            unique_name = get_unique_name(base_name)
                            obj.name = unique_name
                        if obj.data:
                            obj.data.name = obj.name
                elif imported_objects:
                    # 保持原有行为：重命名所有导入的物体
                    obj_name = os.path.splitext(os.path.basename(obj_file))[0]
                    unique_name = get_unique_name(obj_name)
                    for obj in imported_objects:
                        obj.name = unique_name
                
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
