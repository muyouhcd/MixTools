import bpy
import os
import sys
from pathlib import Path
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

def check_better_fbx_available():
    """检查BetterFBX插件是否可用"""
    try:
        if hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx'):
            return True
        else:
            return False
    except:
        return False

def get_file_extension_from_format(file_format):
    """根据文件格式获取文件扩展名"""
    format_extensions = {
        'fbx': '.fbx',
        'obj': '.obj',
        'dae': '.dae',
        '3ds': '.3ds',
        'dxf': '.dxf'
    }
    return format_extensions.get(file_format, '.fbx')

def validate_and_fix_path(directory_path):
    """验证和修复路径"""
    try:
        # 处理相对路径
        if directory_path.startswith('//'):
            # Blender相对路径，转换为绝对路径
            blend_file_path = bpy.data.filepath
            if blend_file_path:
                blend_dir = os.path.dirname(blend_file_path)
                absolute_path = os.path.join(blend_dir, directory_path[2:])
                if os.path.exists(absolute_path):
                    return Path(absolute_path)
        
        # 尝试直接使用路径
        path = Path(directory_path)
        if path.exists() and path.is_dir():
            return path
        
        # 尝试解析为绝对路径
        absolute_path = Path(directory_path).resolve()
        if absolute_path.exists() and absolute_path.is_dir():
            return absolute_path
        
        return None
    except Exception as e:
        print(f"路径验证失败: {e}")
        return None

def rename_armature_to_filename(file_name, imported_objects):
    """重命名导入的骨架为文件名"""
    for obj in imported_objects:
        if obj.type == 'ARMATURE':
            obj.name = file_name
            print(f"重命名骨架: {obj.name}")

def batch_import_fbx_files(file_paths):
    """
    批量导入指定的FBX文件列表 - 清理版本，只使用BetterFBX
    
    参数:
    file_paths: FBX文件路径列表
    
    返回:
    (success, message)
    """
    if not file_paths:
        return False, "没有选择任何文件"
    
    # 检查BetterFBX插件是否可用
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用，请先安装并启用BetterFBX插件"
    
    print("\n=== 使用Better FBX导入器批量导入 ===")
    
    # 统计导入结果
    success_count = 0
    error_count = 0
    error_messages = []
    
    # 遍历并导入每个文件
    for file_path in file_paths:
        if not os.path.exists(file_path):
            error_msg = f"文件不存在: {file_path}"
            print(error_msg)
            error_messages.append(error_msg)
            error_count += 1
            continue
            
        # 获取文件名（不包含扩展名）
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        print(f"\n=== 开始导入文件: {os.path.basename(file_path)} ===")
        
        try:
            # 记录导入前的对象
            objects_before = set(bpy.context.scene.objects)
            print(f"导入前对象数量: {len(objects_before)}")
            
            # 调用Better FBX导入器
            print(f"调用Better FBX导入器: {file_path}")
            result = bpy.ops.better_import.fbx(filepath=file_path)
            print(f"Better FBX导入器返回结果: {result}")
            
            if result != {'FINISHED'}:
                error_msg = f"Better FBX导入失败: {result}"
                print(error_msg)
                error_messages.append(f"导入 {os.path.basename(file_path)} 失败: {error_msg}")
                error_count += 1
                continue
            
            # 获取新导入的对象
            objects_after = set(bpy.context.scene.objects)
            imported_objects = list(objects_after - objects_before)
            print(f"导入后对象数量: {len(objects_after)}")
            print(f"新导入的对象数量: {len(imported_objects)}")
            
            if len(imported_objects) == 0:
                error_msg = f"没有检测到新导入的对象"
                print(f"警告: {error_msg}")
                error_messages.append(f"导入 {os.path.basename(file_path)} 失败: {error_msg}")
                error_count += 1
                continue
            
            print(f"成功导入: {os.path.basename(file_path)}")
            success_count += 1
            
            # 重命名骨架
            rename_armature_to_filename(file_name, imported_objects)
            
        except Exception as e:
            error_msg = f"导入 {os.path.basename(file_path)} 时出错: {str(e)}"
            print(error_msg)
            error_messages.append(error_msg)
            error_count += 1
    
    # 生成结果消息
    result_message = f"导入完成！成功: {success_count}, 失败: {error_count}"
    if error_messages:
        result_message += f"\n错误详情:\n" + "\n".join(error_messages)
    
    return success_count > 0, result_message

def batch_import_fbx(directory_path, file_extension=".fbx", recursive=True):
    """
    批量导入指定目录下的所有FBX文件
    
    参数:
    directory_path: 要导入的文件所在目录
    file_extension: 要导入的文件扩展名，默认为.fbx
    recursive: 是否递归搜索子目录，默认为True
    """
    print(f"=== 批量导入{file_extension}文件 ===")
    print(f"目录路径: {directory_path}")
    print(f"文件扩展名: {file_extension}")
    print(f"递归搜索: {recursive}")
    
    try:
        dir_path = Path(directory_path)
        print(f"Path对象: {dir_path}")
        
        # 确保目录路径存在
        if not dir_path.exists():
            print(f"目录不存在: {dir_path}")
            return False, f"目录不存在: {dir_path}"
        
        if not dir_path.is_dir():
            print(f"路径不是目录: {dir_path}")
            return False, f"路径不是目录: {dir_path}"
        
        # 获取目录下所有指定扩展名的文件
        print(f"开始搜索{file_extension}文件...")
        
        if recursive:
            # 递归搜索（包括子目录）
            print("使用递归搜索...")
            files = list(dir_path.rglob(f"*{file_extension}"))
        else:
            # 只搜索当前目录
            print("只搜索当前目录...")
            files = list(dir_path.glob(f"*{file_extension}"))
        
        print(f"找到{len(files)}个{file_extension}文件")
        
        if not files:
            message = f"在目录 {dir_path} 中没有找到{file_extension}文件"
            print(message)
            if recursive:
                message += "\n（已尝试递归搜索子目录）"
            return False, message
        
        # 显示找到的文件
        print("找到的文件:")
        for f in files[:10]:  # 只显示前10个
            try:
                relative_path = f.relative_to(dir_path)
                print(f"  - {relative_path}")
            except:
                print(f"  - {f.name}")
        if len(files) > 10:
            print(f"  ... 还有 {len(files) - 10} 个文件")
        
        # 构建完整文件路径列表
        file_paths = [str(f) for f in files]
        
        # 使用文件列表导入函数
        return batch_import_fbx_files(file_paths)
        
    except Exception as e:
        error_msg = f"处理目录时出错: {str(e)}"
        print(error_msg)
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False, error_msg

def batch_import_fbx_directories(directory_paths, file_extension=".fbx", recursive=True):
    """
    批量导入多个目录下的所有FBX文件
    
    参数:
    directory_paths: 要导入的文件所在目录列表
    file_extension: 要导入的文件扩展名，默认为.fbx
    recursive: 是否递归搜索子目录，默认为True
    """
    print(f"=== 批量导入多个目录的{file_extension}文件 ===")
    print(f"目录数量: {len(directory_paths)}")
    print(f"文件扩展名: {file_extension}")
    print(f"递归搜索: {recursive}")
    
    all_file_paths = []
    
    for directory_path in directory_paths:
        print(f"\n处理目录: {directory_path}")
        
        try:
            dir_path = Path(directory_path)
            
            # 确保目录路径存在
            if not dir_path.exists():
                print(f"目录不存在: {dir_path}")
                continue
            
            if not dir_path.is_dir():
                print(f"路径不是目录: {dir_path}")
                continue
            
            # 获取目录下所有指定扩展名的文件
            if recursive:
                files = list(dir_path.rglob(f"*{file_extension}"))
                print(f"在目录 {dir_path} 中递归搜索到 {len(files)} 个{file_extension}文件")
            else:
                files = list(dir_path.glob(f"*{file_extension}"))
                print(f"在目录 {dir_path} 中找到 {len(files)} 个{file_extension}文件")
            
            # 构建完整文件路径
            for file in files:
                all_file_paths.append(str(file))
                
        except Exception as e:
            print(f"处理目录 {directory_path} 时出错: {str(e)}")
            continue
    
    if not all_file_paths:
        message = f"在所选目录中没有找到{file_extension}文件"
        print(message)
        if recursive:
            message += "\n（已尝试递归搜索子目录）"
        return False, message
    
    print(f"\n总共找到 {len(all_file_paths)} 个{file_extension}文件")
    
    # 使用文件列表导入函数
    return batch_import_fbx_files(all_file_paths)

# 操作器类
class BETTER_FBX_OT_BatchImport(Operator):
    """使用Better FBX导入器批量导入3D文件"""
    bl_idname = "better_fbx.batch_import"
    bl_label = "批量导入3D文件"
    bl_description = "批量导入指定目录下的所有3D文件，支持多种格式，并自动重命名骨架"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        print(f"从场景获取的文件格式: {file_format}")
        
        # 检查Better FBX插件是否可用（仅对FBX格式）
        if file_format == 'fbx':
            if not check_better_fbx_available():
                self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                return {'CANCELLED'}
        
        # 使用场景中设置的目录
        directory_path = context.scene.better_fbx_import_directory
        if not directory_path:
            self.report({'ERROR'}, "请先设置3D文件目录路径")
            return {'CANCELLED'}
        
        # 路径验证
        print(f"批量导入路径分析:")
        print(f"- 原始路径: {directory_path}")
        print(f"- 选择的格式: {file_format}")
        print(f"- 文件扩展名: {get_file_extension_from_format(file_format)}")
        
        # 尝试解析路径
        try:
            valid_path = validate_and_fix_path(directory_path)
            
            if valid_path is None:
                self.report({'ERROR'}, f"无法找到有效的路径: {directory_path}\n请检查路径是否正确，或者尝试手动输入绝对路径。")
                return {'CANCELLED'}
            
            print(f"使用验证后的路径: {valid_path}")
            directory_path = str(valid_path)
        except Exception as e:
            self.report({'ERROR'}, f"路径验证失败: {str(e)}")
            return {'CANCELLED'}
        
        # 执行批量导入，传入选择的格式
        file_extension = get_file_extension_from_format(file_format)
        success, message = batch_import_fbx(directory_path, file_extension)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

class BETTER_FBX_OT_BatchImportFiles(Operator, ImportHelper):
    """浏览选择多个3D文件"""
    bl_idname = "better_fbx.batch_import_files"
    bl_label = "选择多个3D文件"
    bl_description = "浏览选择多个3D文件进行批量导入，支持多种格式"
    bl_options = {'REGISTER', 'UNDO'}
    
    # 支持多选文件
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
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        print(f"从场景获取的文件格式: {file_format}")
        
        # 检查Better FBX插件是否可用（仅对FBX格式）
        if file_format == 'fbx':
            if not check_better_fbx_available():
                self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                return {'CANCELLED'}
        
        # 构建文件路径列表
        file_paths = []
        for file_elem in self.files:
            file_path = os.path.join(self.directory, file_elem.name)
            file_paths.append(file_path)
        
        if not file_paths:
            self.report({'ERROR'}, "没有选择任何文件")
            return {'CANCELLED'}
        
        print(f"选择的文件格式: {file_format}")
        print(f"选择的文件数量: {len(file_paths)}")
        
        # 执行批量导入
        success, message = batch_import_fbx_files(file_paths)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}

class BETTER_FBX_OT_BatchImportByNameList(Operator):
    """根据名称列表批量导入3D文件"""
    bl_idname = "better_fbx.batch_import_by_name_list"
    bl_label = "按名称列表批量导入"
    bl_description = "根据名称列表批量导入3D文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        print(f"从场景获取的文件格式: {file_format}")
        
        # 检查Better FBX插件是否可用（仅对FBX格式）
        if file_format == 'fbx':
            if not check_better_fbx_available():
                self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                return {'CANCELLED'}
        
        # 获取名称列表和搜索目录
        name_list_text = context.scene.fbx_name_list_text
        search_directory = context.scene.fbx_search_directory
        
        if not name_list_text.strip():
            self.report({'ERROR'}, "请输入要导入的文件名称列表")
            return {'CANCELLED'}
        
        if not search_directory:
            self.report({'ERROR'}, "请设置搜索目录")
            return {'CANCELLED'}
        
        # 解析名称列表
        file_names = [name.strip() for name in name_list_text.split('\n') if name.strip()]
        print(f"要导入的文件名称: {file_names}")
        
        # 获取文件扩展名
        file_extension = get_file_extension_from_format(file_format)
        
        # 构建文件路径列表
        file_paths = []
        search_path = Path(search_directory)
        
        if not search_path.exists() or not search_path.is_dir():
            self.report({'ERROR'}, f"搜索目录不存在或不是目录: {search_directory}")
            return {'CANCELLED'}
        
        # 递归搜索文件
        for file_name in file_names:
            # 添加扩展名（如果没有的话）
            if not file_name.endswith(file_extension):
                file_name += file_extension
            
            # 搜索文件
            found_files = list(search_path.rglob(file_name))
            if found_files:
                file_paths.extend([str(f) for f in found_files])
                print(f"找到文件: {file_name} -> {found_files[0]}")
            else:
                print(f"未找到文件: {file_name}")
        
        if not file_paths:
            self.report({'WARNING'}, "没有找到任何匹配的文件")
            return {'CANCELLED'}
        
        print(f"总共找到 {len(file_paths)} 个文件")
        
        # 执行批量导入
        success, message = batch_import_fbx_files(file_paths)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportByNameList)

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportByNameList)

if __name__ == "__main__":
    register()
