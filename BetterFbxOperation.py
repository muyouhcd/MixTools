import bpy
import os
import sys
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

# 检查BetterFBX插件是否可用
def check_better_fbx_available():
    """检查BetterFBX插件是否可用"""
    try:
        if hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx'):
            return True
        else:
            return False
    except:
        return False

def batch_import_with_better_fbx(file_paths):
    """
    使用BetterFBX插件批量导入FBX文件列表 - 简单逐个导入
    
    参数:
    file_paths: FBX文件路径列表
    
    返回:
    (success, message)
    """
    if not file_paths:
        return False, "没有选择任何文件"
    
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用，请先安装并启用BetterFBX插件"
    
    print(f"\n=== 开始批量导入 {len(file_paths)} 个文件 ===")
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    for i, file_path in enumerate(file_paths):
        if not os.path.exists(file_path):
            error_messages.append(f"文件不存在: {file_path}")
            error_count += 1
            continue
            
        print(f"\n进度: {((i+1)/len(file_paths)*100):.1f}% ({i+1}/{len(file_paths)})")
        print(f"=== 开始导入文件: {os.path.basename(file_path)} ===")
        
        try:
            # 直接调用BetterFBX导入器，使用默认设置
            result = bpy.ops.better_import.fbx(filepath=file_path)
            
            if result == {'FINISHED'}:
                print(f"✓ 成功导入: {os.path.basename(file_path)}")
                success_count += 1
            else:
                print(f"✗ 导入失败: {os.path.basename(file_path)} - Better FBX导入器返回: {result}")
                error_messages.append(f"导入失败: {os.path.basename(file_path)} - Better FBX导入器返回: {result}")
                error_count += 1
                
        except Exception as e:
            print(f"✗ 导入异常: {os.path.basename(file_path)} - 错误: {str(e)}")
            error_messages.append(f"导入异常: {os.path.basename(file_path)} - 错误: {str(e)}")
            error_count += 1
    
    # 输出最终结果
    print(f"\n=== 批量导入完成 ===")
    print(f"成功: {success_count} 个文件")
    print(f"失败: {error_count} 个文件")
    
    if error_messages:
        print("\n错误详情:")
        for msg in error_messages:
            print(f"  - {msg}")
    
    if success_count > 0:
        return True, f"成功导入 {success_count} 个文件，失败 {error_count} 个文件"
    else:
        return False, f"导入失败，错误: {error_messages[0] if error_messages else '未知错误'}"

class BetterFbxBatchImportOperator(Operator):
    """批量导入FBX文件"""
    bl_idname = "better_fbx.batch_import_with_better_fbx"
    bl_label = "批量导入FBX"
    bl_description = "批量导入指定目录中的所有FBX文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        directory = scene.better_fbx_import_directory
        
        if not directory:
            self.report({'ERROR'}, "请先设置3D文件目录")
            return {'CANCELLED'}
        
        # 处理Blender相对路径（//开头）
        if directory.startswith('//'):
            directory = bpy.path.abspath(directory)
        
        if not os.path.exists(directory):
            self.report({'ERROR'}, f"目录不存在: {directory}")
            return {'CANCELLED'}
        
        # 获取文件格式
        file_format = getattr(scene, 'batch_import_file_format', 'FBX')
        if file_format == 'FBX':
            extension = '.fbx'
        elif file_format == 'OBJ':
            extension = '.obj'
        else:
            extension = '.fbx'
        
        # 搜索文件
        file_paths = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    file_paths.append(os.path.join(root, file))
        
        if not file_paths:
            self.report({'WARNING'}, f"在目录 {directory} 中没有找到 {extension} 文件")
            return {'CANCELLED'}
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

class BetterFbxBatchImportFilesOperator(Operator, ImportHelper):
    """选择多个文件批量导入"""
    bl_idname = "better_fbx.batch_import_files_with_better_fbx"
    bl_label = "选择多个文件"
    bl_description = "选择多个FBX文件进行批量导入"
    bl_options = {'REGISTER', 'UNDO'}
    
    filter_glob: StringProperty(
        default="*.fbx;*.obj",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    files: bpy.props.CollectionProperty(
        name="文件路径",
        type=bpy.types.OperatorFileListElement,
    )
    
    def execute(self, context):
        if not self.files:
            self.report({'ERROR'}, "没有选择任何文件")
            return {'CANCELLED'}
        
        # 构建文件路径列表
        file_paths = []
        for file in self.files:
            file_path = os.path.join(os.path.dirname(self.filepath), file.name)
            file_paths.append(file_path)
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

class BetterFbxBatchImportByNameListOperator(Operator):
    """按名称列表批量导入"""
    bl_idname = "better_fbx.batch_import_by_name_list_with_better_fbx"
    bl_label = "按名称列表导入"
    bl_description = "按名称列表批量导入FBX文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        
        # 获取名称列表
        name_list_text = getattr(scene, 'fbx_name_list_text', '')
        if not name_list_text.strip():
            self.report({'ERROR'}, "请输入要查找的文件名称列表")
            return {'CANCELLED'}
        
        # 获取搜索目录
        search_directory = getattr(scene, 'fbx_search_directory', '')
        if not search_directory:
            self.report({'ERROR'}, "请设置搜索目录")
            return {'CANCELLED'}
        
        # 处理Blender相对路径（//开头）
        if search_directory.startswith('//'):
            search_directory = bpy.path.abspath(search_directory)
        
        if not os.path.exists(search_directory):
            self.report({'ERROR'}, f"搜索目录不存在: {search_directory}")
            return {'CANCELLED'}
        
        # 解析名称列表
        names = []
        for name in name_list_text.replace(',', ' ').split():
            name = name.strip()
            if name:
                names.append(name)
        
        if not names:
            self.report({'ERROR'}, "没有找到有效的文件名称")
            return {'CANCELLED'}
        
        # 获取文件格式
        file_format = getattr(scene, 'batch_import_file_format', 'FBX')
        if file_format == 'FBX':
            extension = '.fbx'
        elif file_format == 'OBJ':
            extension = '.obj'
        else:
            extension = '.fbx'
        
        # 搜索匹配的文件
        file_paths = []
        for root, dirs, files in os.walk(search_directory):
            for file in files:
                if file.lower().endswith(extension.lower()):
                    file_name = os.path.splitext(file)[0]
                    for name in names:
                        if name in file_name:
                            file_paths.append(os.path.join(root, file))
                            break
        
        if not file_paths:
            self.report({'WARNING'}, f"在目录 {search_directory} 中没有找到匹配的文件")
            return {'CANCELLED'}
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

# 为了兼容面板中的操作符ID，添加别名操作符
class BetterFbxBatchImportAliasOperator(Operator):
    """批量导入FBX文件 - 别名操作符"""
    bl_idname = "better_fbx.batch_import"
    bl_label = "批量导入"
    bl_description = "批量导入指定目录中的所有FBX文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 调用实际的批量导入操作符
        return bpy.ops.better_fbx.batch_import_with_better_fbx()

class BetterFbxBatchImportFilesAliasOperator(Operator):
    """选择多个文件批量导入 - 别名操作符"""
    bl_idname = "better_fbx.batch_import_files"
    bl_label = "选择多个文件"
    bl_description = "选择多个FBX文件进行批量导入"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 调用实际的文件选择导入操作符
        return bpy.ops.better_fbx.batch_import_files_with_better_fbx()

class BetterFbxBatchImportByNameListAliasOperator(Operator):
    """按名称列表批量导入 - 别名操作符"""
    bl_idname = "better_fbx.batch_import_by_name_list"
    bl_label = "按名称列表导入"
    bl_description = "按名称列表批量导入FBX文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 调用实际的按名称列表导入操作符
        return bpy.ops.better_fbx.batch_import_by_name_list_with_better_fbx()

def register():
    bpy.utils.register_class(BetterFbxBatchImportOperator)
    bpy.utils.register_class(BetterFbxBatchImportFilesOperator)
    bpy.utils.register_class(BetterFbxBatchImportByNameListOperator)
    # 注册别名操作符
    bpy.utils.register_class(BetterFbxBatchImportAliasOperator)
    bpy.utils.register_class(BetterFbxBatchImportFilesAliasOperator)
    bpy.utils.register_class(BetterFbxBatchImportByNameListAliasOperator)

def unregister():
    bpy.utils.unregister_class(BetterFbxBatchImportOperator)
    bpy.utils.unregister_class(BetterFbxBatchImportFilesOperator)
    bpy.utils.unregister_class(BetterFbxBatchImportByNameListOperator)
    # 注销别名操作符
    bpy.utils.unregister_class(BetterFbxBatchImportAliasOperator)
    bpy.utils.unregister_class(BetterFbxBatchImportFilesAliasOperator)
    bpy.utils.unregister_class(BetterFbxBatchImportByNameListAliasOperator)