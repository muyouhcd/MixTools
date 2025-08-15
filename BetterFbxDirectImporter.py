import bpy
import os
import sys
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

def check_better_fbx_available():
    """检查BetterFBX插件是否可用"""
    try:
        # 检查BetterFBX操作器是否存在
        if hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx'):
            return True
        else:
            return False
    except:
        return False

def import_fbx_with_better_fbx_direct(file_path, import_settings=None):
    """
    直接调用BetterFBX操作器导入FBX文件
    
    参数:
    file_path: FBX文件路径
    import_settings: 导入设置字典
    
    返回:
    (success, message, imported_objects)
    """
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用", []
    
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}", []
    
    try:
        # 记录导入前的对象
        objects_before = set(bpy.context.scene.objects)
        print(f"导入前对象数量: {len(objects_before)}")
        
        # 直接调用BetterFBX导入操作器
        print(f"调用BetterFBX导入器: {file_path}")
        
        # 使用BetterFBX的默认设置进行导入
        result = bpy.ops.better_import.fbx(filepath=file_path)
        print(f"BetterFBX导入器返回结果: {result}")
        
        if result != {'FINISHED'}:
            return False, f"BetterFBX导入失败: {result}", []
        
        # 获取新导入的对象
        objects_after = set(bpy.context.scene.objects)
        imported_objects = list(objects_after - objects_before)
        print(f"导入后对象数量: {len(objects_after)}")
        print(f"新导入的对象数量: {len(imported_objects)}")
        
        if len(imported_objects) == 0:
            return False, "没有检测到新导入的对象", []
        
        # 检查导入的对象是否有顶点组
        for obj in imported_objects:
            if obj.type == 'MESH':
                if len(obj.vertex_groups) > 0:
                    print(f"✓ 网格对象 {obj.name} 有 {len(obj.vertex_groups)} 个顶点组")
                else:
                    print(f"⚠ 网格对象 {obj.name} 没有顶点组")
            
            if obj.type == 'ARMATURE':
                print(f"✓ 骨架对象 {obj.name} 有 {len(obj.data.bones)} 个骨骼")
        
        return True, f"成功导入 {len(imported_objects)} 个对象", imported_objects
        
    except Exception as e:
        return False, f"导入过程出错: {str(e)}", []

def batch_import_fbx_files_with_better_fbx_direct(file_paths):
    """
    使用BetterFBX插件直接批量导入FBX文件
    
    参数:
    file_paths: FBX文件路径列表
    
    返回:
    (success, message)
    """
    if not file_paths:
        return False, "没有选择任何文件"
    
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用，请先安装并启用BetterFBX插件"
    
    print(f"\n=== 使用BetterFBX插件直接批量导入 {len(file_paths)} 个FBX文件 ===")
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    for i, file_path in enumerate(file_paths):
        print(f"\n进度: {(i + 1)}/{len(file_paths)} - 导入: {os.path.basename(file_path)}")
        
        try:
            success, message, imported_objects = import_fbx_with_better_fbx_direct(file_path)
            
            if success:
                print(f"✓ 成功导入: {os.path.basename(file_path)} - {message}")
                success_count += 1
                
                # 重命名骨架（如果需要）
                if imported_objects:
                    file_name = os.path.splitext(os.path.basename(file_path))[0]
                    rename_armature_to_filename(file_name, imported_objects)
            else:
                print(f"✗ 导入失败: {os.path.basename(file_path)} - {message}")
                error_count += 1
                error_messages.append(f"导入 {os.path.basename(file_path)} 失败: {message}")
                
        except Exception as e:
            error_msg = f"导入 {os.path.basename(file_path)} 时出错: {str(e)}"
            print(f"✗ {error_msg}")
            error_messages.append(error_msg)
            error_count += 1
    
    # 生成结果消息
    result_message = f"批量导入完成！成功: {success_count}, 失败: {error_count}"
    if error_messages:
        result_message += f"\n错误详情:\n" + "\n".join(error_messages)
    
    return success_count > 0, result_message

def rename_armature_to_filename(file_name, imported_objects):
    """重命名导入的骨架为文件名"""
    for obj in imported_objects:
        if obj.type == 'ARMATURE':
            obj.name = file_name
            print(f"重命名骨架: {obj.name}")

# 操作器类
class BETTER_FBX_OT_DirectBatchImport(Operator):
    """使用BetterFBX插件直接批量导入FBX文件"""
    bl_idname = "better_fbx.direct_batch_import"
    bl_label = "BetterFBX直接批量导入"
    bl_description = "使用BetterFBX插件直接批量导入FBX文件，确保顶点组和骨骼信息完整"
    bl_options = {'REGISTER', 'UNDO'}
    
    directory: StringProperty(
        name="目录",
        description="选择包含FBX文件的目录",
        subtype='DIR_PATH'
    )
    
    file_extension: StringProperty(
        name="文件扩展名",
        description="要导入的文件扩展名",
        default=".fbx"
    )
    
    recursive: BoolProperty(
        name="递归搜索",
        description="是否递归搜索子目录",
        default=True
    )
    
    def execute(self, context):
        if not check_better_fbx_available():
            self.report({'ERROR'}, "BetterFBX插件不可用，请先安装并启用BetterFBX插件")
            return {'CANCELLED'}
        
        if not self.directory:
            self.report({'ERROR'}, "请先选择包含FBX文件的目录")
            return {'CANCELLED'}
        
        # 获取所有FBX文件
        fbx_files = []
        if self.recursive:
            for root, dirs, files in os.walk(self.directory):
                for file in files:
                    if file.lower().endswith(self.file_extension.lower()):
                        fbx_files.append(os.path.join(root, file))
        else:
            for file in os.listdir(self.directory):
                if file.lower().endswith(self.file_extension.lower()):
                    fbx_files.append(os.path.join(self.directory, file))
        
        if not fbx_files:
            self.report({'WARNING'}, f"在目录 {self.directory} 中没有找到{self.file_extension}文件")
            return {'CANCELLED'}
        
        print(f"找到 {len(fbx_files)} 个{self.file_extension}文件")
        
        # 执行批量导入
        success, message = batch_import_fbx_files_with_better_fbx_direct(fbx_files)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class BETTER_FBX_OT_DirectBatchImportFiles(Operator, ImportHelper):
    """使用BetterFBX插件直接选择多个FBX文件进行批量导入"""
    bl_idname = "better_fbx.direct_batch_import_files"
    bl_label = "BetterFBX直接选择多个文件"
    bl_description = "使用BetterFBX插件直接选择多个FBX文件进行批量导入"
    bl_options = {'REGISTER', 'UNDO'}
    
    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    directory: StringProperty(
        maxlen=1024,
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    
    def execute(self, context):
        if not check_better_fbx_available():
            self.report({'ERROR'}, "BetterFBX插件不可用，请先安装并启用BetterFBX插件")
            return {'CANCELLED'}
        
        # 构建文件路径列表
        file_paths = []
        for file_elem in self.files:
            file_path = os.path.join(self.directory, file_elem.name)
            file_paths.append(file_path)
        
        if not file_paths:
            self.report({'ERROR'}, "没有选择任何文件")
            return {'CANCELLED'}
        
        print(f"选择的文件数量: {len(file_paths)}")
        
        # 执行批量导入
        success, message = batch_import_fbx_files_with_better_fbx_direct(file_paths)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(BETTER_FBX_OT_DirectBatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_DirectBatchImportFiles)

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_DirectBatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_DirectBatchImportFiles)

if __name__ == "__main__":
    register()
