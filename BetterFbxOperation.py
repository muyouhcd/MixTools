import bpy
import os
from pathlib import Path
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

# 支持的3D文件格式
SUPPORTED_FORMATS = [
    ('fbx', 'FBX', 'Autodesk FBX格式'),
    ('dae', 'DAE', 'COLLADA DAE格式'),
    ('obj', 'OBJ', 'Wavefront OBJ格式'),
    ('3ds', '3DS', '3D Studio 3DS格式'),
    ('blend', 'BLEND', 'Blender原生格式'),
]

def get_file_extension_from_format(file_format):
    """
    根据选择的格式返回文件扩展名
    
    参数:
    file_format: 格式标识符
    
    返回:
    文件扩展名字符串
    """
    format_mapping = {
        'fbx': '.fbx',
        'dae': '.dae', 
        'obj': '.obj',
        '3ds': '.3ds',
        'blend': '.blend'
    }
    return format_mapping.get(file_format, '.fbx')

def normalize_blender_path(path_string):
    """
    规范化Blender路径字符串
    
    参数:
    path_string: Blender路径字符串
    
    返回:
    规范化后的Path对象
    """
    if not path_string:
        return None
    
    print(f"原始路径: {path_string}")
    
    # 检查是否为Windows绝对路径（包含驱动器号）
    if len(path_string) >= 2 and path_string[1] == ':' and path_string[0].isalpha():
        # 这是Windows绝对路径，直接使用
        clean_path = path_string.replace('\\', '/')
        print(f"处理Windows绝对路径: {path_string} -> {clean_path}")
        return Path(clean_path)
    
    # 处理Blender的相对路径格式 (//..\..\)
    if path_string.startswith('//'):
        # 移除开头的 //
        clean_path = path_string[2:]
        # 处理Windows路径分隔符
        clean_path = clean_path.replace('\\', '/')
        print(f"处理Blender相对路径: {path_string} -> {clean_path}")
        return Path(clean_path)
    else:
        # 处理普通路径
        clean_path = path_string.replace('\\', '/')
        print(f"处理普通路径: {path_string} -> {clean_path}")
        return Path(clean_path)

def validate_and_fix_path(path_string):
    """
    验证并修复路径，特别处理中文字符路径
    
    参数:
    path_string: 原始路径字符串
    
    返回:
    修复后的有效路径或None
    """
    print(f"=== 路径验证和修复 ===")
    print(f"原始路径: {path_string}")
    
    # 尝试多种路径格式
    path_variants = []
    
    # 1. 原始路径
    path_variants.append(path_string)
    
    # 2. 替换反斜杠为正斜杠
    path_variants.append(path_string.replace('\\', '/'))
    
    # 3. 规范化路径分隔符
    path_variants.append(path_string.replace('/', '\\'))
    
    # 4. 尝试不同的编码
    try:
        # 尝试UTF-8编码
        encoded_path = path_string.encode('utf-8').decode('utf-8')
        path_variants.append(encoded_path)
    except:
        pass
    
    # 5. 尝试系统默认编码
    try:
        import locale
        system_encoding = locale.getpreferredencoding()
        encoded_path = path_string.encode(system_encoding).decode(system_encoding)
        path_variants.append(encoded_path)
    except:
        pass
    
    print(f"尝试的路径变体:")
    for i, variant in enumerate(path_variants):
        print(f"  {i+1}. {variant}")
    
    # 测试每个路径变体
    for i, variant in enumerate(path_variants):
        try:
            print(f"\n测试路径变体 {i+1}: {variant}")
            path_obj = Path(variant)
            
            if path_obj.exists():
                print(f"✓ 路径变体 {i+1} 存在: {path_obj}")
                if path_obj.is_dir():
                    print(f"✓ 确认是目录")
                    # 测试目录访问
                    try:
                        test_list = list(path_obj.iterdir())
                        print(f"✓ 目录访问成功，包含 {len(test_list)} 个项目")
                        return path_obj
                    except Exception as access_error:
                        print(f"✗ 目录访问失败: {access_error}")
                        continue
                else:
                    print(f"✗ 不是目录")
                    continue
            else:
                print(f"✗ 路径变体 {i+1} 不存在")
                
        except Exception as e:
            print(f"✗ 路径变体 {i+1} 测试失败: {e}")
            continue
    
    print(f"所有路径变体都失败了")
    return None

def find_valid_path(original_path):
    """
    尝试多种方式找到有效的路径
    
    参数:
    original_path: 原始路径字符串
    
    返回:
    有效的Path对象或None
    """
    print(f"尝试解析路径: {original_path}")
    print(f"路径编码信息:")
    print(f"- 路径长度: {len(original_path)}")
    print(f"- 路径字节表示: {original_path.encode('utf-8', errors='ignore')}")
    print(f"- 是否包含中文字符: {any(ord(c) > 127 for c in original_path)}")
    
    # 方法1: 检查是否为Windows绝对路径，如果是则直接使用
    if len(original_path) >= 2 and original_path[1] == ':' and original_path[0].isalpha():
        try:
            path1 = Path(original_path)
            print(f"方法1: 尝试Windows绝对路径: {path1}")
            if path1.exists():
                print(f"方法1成功（绝对路径）: {path1}")
                return path1
            else:
                print(f"绝对路径不存在: {path1}")
                # 尝试规范化路径
                try:
                    normalized_path = path1.resolve()
                    if normalized_path.exists():
                        print(f"方法1成功（规范化后）: {normalized_path}")
                        return normalized_path
                except Exception as norm_error:
                    print(f"路径规范化失败: {norm_error}")
        except Exception as e:
            print(f"方法1失败: {e}")
    
    # 方法2: 直接使用原始路径
    try:
        path2 = Path(original_path)
        print(f"方法2: 尝试直接路径: {path2}")
        if path2.exists():
            print(f"方法2成功: {path2}")
            return path2
    except Exception as e:
        print(f"方法2失败: {e}")
    
    # 方法3: 规范化路径
    try:
        path3 = normalize_blender_path(original_path)
        print(f"方法3: 尝试规范化路径: {path3}")
        if path3 and path3.exists():
            print(f"方法3成功: {path3}")
            return path3
    except Exception as e:
        print(f"方法3失败: {e}")
    
    # 方法4: 尝试解析相对路径
    try:
        path4 = Path(original_path).resolve()
        print(f"方法4: 尝试解析相对路径: {path4}")
        if path4.exists():
            print(f"方法4成功: {path4}")
            return path4
    except Exception as e:
        print(f"方法4失败: {e}")
    
    # 方法5: 尝试绝对路径
    try:
        path5 = Path(original_path).absolute()
        print(f"方法5: 尝试绝对路径: {path5}")
        if path5.exists():
            print(f"方法5成功: {path5}")
            return path5
    except Exception as e:
        print(f"方法5失败: {e}")
    
    # 方法6: 优化驱动器搜索 - 只搜索常用驱动器
    try:
        # 移除可能的驱动器前缀问题
        clean_path = original_path
        if clean_path.startswith('//'):
            clean_path = clean_path[2:]
        clean_path = clean_path.replace('\\', '/')
        
        # 只搜索常用的驱动器，减少不必要的检查
        common_drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:']
        
        for drive in common_drives:
            test_path = Path(f"{drive}/{clean_path}")
            print(f"方法6: 尝试驱动器 {drive}: {test_path}")
            if test_path.exists():
                print(f"方法6成功: {test_path}")
                return test_path
    except Exception as e:
        print(f"方法6失败: {e}")
    
    # 方法7: 专门处理Blender的路径格式
    try:
        # 处理 //..\..\ 格式的路径
        if original_path.startswith('//'):
            # 移除开头的 //
            clean_path = original_path[2:]
            # 处理Windows路径分隔符
            clean_path = clean_path.replace('\\', '/')
            
            # 只搜索常用驱动器
            common_drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:']
            
            for drive in common_drives:
                test_path = Path(f"{drive}/{clean_path}")
                print(f"方法7: 尝试Blender路径 {drive}: {test_path}")
                if test_path.exists():
                    print(f"方法7成功: {test_path}")
                    return test_path
    except Exception as e:
        print(f"方法7失败: {e}")
    
    # 方法8: 尝试从Blender文件路径推断
    try:
        # 获取当前Blender文件的路径
        blend_file_path = bpy.data.filepath
        if blend_file_path:
            blend_dir = Path(blend_file_path).parent
            print(f"Blender文件目录: {blend_dir}")
            
            # 处理相对路径
            if original_path.startswith('//'):
                clean_path = original_path[2:].replace('\\', '/')
                # 尝试从Blender文件目录开始解析
                test_path = blend_dir / clean_path
                print(f"方法8: 尝试从Blender文件推断: {test_path}")
                if test_path.exists():
                    print(f"方法8成功: {test_path}")
                    return test_path
    except Exception as e:
        print(f"方法8失败: {e}")
    
    print(f"所有路径解析方法都失败了")
    return None

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

def rename_armature_to_filename(file_name, imported_objects):
    """
    将导入的骨架重命名为FBX文件名
    
    参数:
    file_name: FBX文件名（不包含扩展名）
    imported_objects: 当前导入的对象列表
    """
    # 打印调试信息
    print(f"\n=== 开始查找骨架 ===")
    print(f"当前导入的对象数量: {len(imported_objects)}")
    
    # 遍历导入的对象，找到骨架
    armature_found = False
    for obj in imported_objects:
        if obj.type == 'ARMATURE':
            print(f"\n找到骨架对象:")
            print(f"- 原始名称: {obj.name}")
            print(f"- 骨架数据: {obj.data.name if obj.data else 'None'}")
            
            # 获取唯一的名称
            unique_name = get_unique_name(file_name)
            
            # 重命名骨架
            obj.name = unique_name
            # 如果骨架有数据，也重命名骨架数据
            if obj.data:
                obj.data.name = unique_name
            
            print(f"骨架已重命名为: {unique_name}")
            armature_found = True
    
    if not armature_found:
        print(f"\n警告: 未找到任何骨架对象！")
        print("请确认:")
        print("1. FBX文件是否包含骨架")
        print("2. 导入设置是否正确")
        print("3. 骨架是否被正确导入")
    
    return armature_found

def batch_import_fbx_files(file_paths):
    """
    批量导入指定的FBX文件列表
    
    参数:
    file_paths: FBX文件路径列表
    """
    if not file_paths:
        return False, "没有选择任何文件"
    
    # 使用Better FBX导入器的默认设置
    print("\n=== 使用Better FBX导入器 ===")
    print("Better FBX导入器将使用其默认设置")
    
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
            print(f"开始调用Better FBX导入器...")
            print(f"文件路径: {file_path}")
            
            # 尝试导入 - 专门使用Better FBX导入器
            try:
                # 使用Better FBX导入器
                print(f"使用Better FBX导入器...")
                result = bpy.ops.better_import.fbx(filepath=file_path)
                print(f"Better FBX导入器返回结果: {result}")
            except Exception as better_fbx_error:
                print(f"Better FBX导入器失败: {better_fbx_error}")
                error_count += 1
                error_messages.append(f"导入 {os.path.basename(file_path)} 失败: Better FBX导入器错误 - {str(better_fbx_error)}")
                continue
            
            # 获取新导入的对象
            objects_after = set(bpy.context.scene.objects)
            imported_objects = list(objects_after - objects_before)
            print(f"导入后对象数量: {len(objects_after)}")
            print(f"新导入的对象数量: {len(imported_objects)}")
            
            if len(imported_objects) == 0:
                print(f"警告: 没有检测到新导入的对象！")
                error_count += 1
                error_messages.append(f"导入 {os.path.basename(file_path)} 失败: 没有检测到新对象")
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
    print(f"=== 批量导入FBX文件 ===")
    print(f"目录路径: {directory_path}")
    print(f"文件扩展名: {file_extension}")
    print(f"递归搜索: {recursive}")
    
    # 使用pathlib.Path来处理路径
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
            # 显示相对路径，让用户知道文件在哪个子目录
            try:
                relative_path = f.relative_to(dir_path)
                print(f"  - {relative_path}")
            except:
                print(f"  - {f.name}")
        if len(files) > 10:
            print(f"  ... 还有 {len(files) - 10} 个文件")
        
        # 构建完整文件路径列表
        file_paths = [str(f) for f in files]
        
        # 使用新的文件列表导入函数
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
    print(f"=== 批量导入多个目录的FBX文件 ===")
    print(f"目录数量: {len(directory_paths)}")
    print(f"文件扩展名: {file_extension}")
    print(f"递归搜索: {recursive}")
    
    all_file_paths = []
    
    for directory_path in directory_paths:
        print(f"\n处理目录: {directory_path}")
        
        try:
            # 使用pathlib.Path来处理路径
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
    
    # 使用新的文件列表导入函数
    return batch_import_fbx_files(all_file_paths)



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
            try:
                if not hasattr(bpy.ops, 'better_import') or not hasattr(bpy.ops.better_import, 'fbx'):
                    self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"检查Better FBX插件时出错: {str(e)}")
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
            # 首先尝试使用新的路径验证函数
            print(f"使用新的路径验证函数...")
            valid_path = validate_and_fix_path(directory_path)
            
            if valid_path is None:
                print(f"新路径验证函数失败，尝试原有方法...")
                # 使用原有的路径查找函数作为备选
                valid_path = find_valid_path(directory_path)
                
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
    ) # type: ignore
    
    directory: StringProperty(
        maxlen=1024,
        subtype='DIR_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    ) # type: ignore
    
    def execute(self, context):
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        print(f"从场景获取的文件格式: {file_format}")
        
        # 检查Better FBX插件是否可用（仅对FBX格式）
        if file_format == 'fbx':
            try:
                if not hasattr(bpy.ops, 'better_import') or not hasattr(bpy.ops.better_import, 'fbx'):
                    self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"检查Better FBX插件时出错: {str(e)}")
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
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        file_extension = get_file_extension_from_format(file_format)
        
        # 动态设置文件过滤器
        self.filename_ext = file_extension
        self.filter_glob = f"*{file_extension}"
        
        print(f"设置文件过滤器为: {file_extension}")
        
        # 打开文件浏览器选择文件
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class BETTER_FBX_OT_BatchImportByNameList(Operator):
    """根据名称列表批量导入3D文件"""
    bl_idname = "better_fbx.batch_import_by_name_list"
    bl_label = "按名称列表批量导入"
    bl_description = "根据名称列表在指定路径下查找并批量导入3D文件，支持多种格式"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 从场景中获取选择的格式
        file_format = context.scene.batch_import_file_format
        print(f"从场景获取的文件格式: {file_format}")
        
        # 检查Better FBX插件是否可用（仅对FBX格式）
        if file_format == 'fbx':
            try:
                if not hasattr(bpy.ops, 'better_import') or not hasattr(bpy.ops.better_import, 'fbx'):
                    self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, f"检查Better FBX插件时出错: {str(e)}")
                return {'CANCELLED'}
        
        # 获取名称列表和搜索路径
        name_list_text = context.scene.fbx_name_list_text
        search_directory = context.scene.fbx_search_directory
        
        print(f"调试信息:")
        print(f"原始搜索目录: {search_directory}")
        print(f"名称列表文本: {name_list_text}")
        print(f"选择的文件格式: {file_format}")
        print(f"文件扩展名: {get_file_extension_from_format(file_format)}")
        
        if not name_list_text.strip():
            self.report({'ERROR'}, "请输入名称列表")
            return {'CANCELLED'}
        
        if not search_directory:
            self.report({'ERROR'}, "请选择搜索目录")
            return {'CANCELLED'}
        
        # 添加路径格式检查
        print(f"路径格式分析:")
        print(f"- 路径长度: {len(search_directory)}")
        print(f"- 是否以//开头: {search_directory.startswith('//')}")
        print(f"- 是否包含驱动器号: {len(search_directory) >= 2 and search_directory[1] == ':' and search_directory[0].isalpha()}")
        print(f"- 路径类型: {'绝对路径' if len(search_directory) >= 2 and search_directory[1] == ':' and search_directory[0].isalpha() else '相对路径或Blender路径'}")
        
        # 解析名称列表（支持多种分隔符：换行符、空格、逗号）
        name_list = []
        # 首先按换行符分割
        lines = name_list_text.split('\n')
        for line in lines:
            if line.strip():
                # 再按空格分割每行
                names_in_line = line.split()
                for name in names_in_line:
                    if name.strip():
                        name_list.append(name.strip())
        
        print(f"解析后的名称列表: {name_list}")
        
        if not name_list:
            self.report({'ERROR'}, "名称列表为空")
            return {'CANCELLED'}
        
        # 在指定目录下查找匹配的3D文件
        found_files = []
        
        # 处理路径格式问题
        try:
            # 首先尝试使用新的路径验证函数
            print(f"使用新的路径验证函数...")
            search_path = validate_and_fix_path(search_directory)
            
            if search_path is None:
                print(f"新路径验证函数失败，尝试原有方法...")
                # 使用原有的路径查找函数作为备选
                search_path = find_valid_path(search_directory)
                
            if search_path is None:
                self.report({'ERROR'}, f"无法找到有效的路径: {search_directory}\n请检查路径是否正确，或者尝试手动输入绝对路径。")
                return {'CANCELLED'}
            
            print(f"最终使用的路径: {search_path}")
        except Exception as e:
            self.report({'ERROR'}, f"路径处理错误: {search_directory}\n错误信息: {str(e)}")
            return {'CANCELLED'}
        
        # 优化：限制搜索深度和文件数量
        file_extension = get_file_extension_from_format(file_format)
        print(f"开始搜索{file_extension}文件...")
        fbx_files_found = []
        search_count = 0
        max_search_files = 1000  # 限制最大搜索文件数
        
        # 显示搜索进度
        self.report({'INFO'}, f"开始搜索{file_extension}文件...")
        
        # 添加详细的目录检查
        print(f"=== 目录检查信息 ===")
        print(f"搜索路径: {search_path}")
        print(f"路径类型: {type(search_path)}")
        print(f"路径是否存在: {search_path.exists()}")
        print(f"是否为目录: {search_path.is_dir()}")
        
        # 检查目录内容
        try:
            dir_contents = list(search_path.iterdir())
            print(f"目录内容数量: {len(dir_contents)}")
            print(f"前10个目录项:")
            for i, item in enumerate(dir_contents[:10]):
                print(f"  {i+1}. {item.name} ({'目录' if item.is_dir() else '文件'})")
            
            # 检查是否有指定格式的文件
            files_in_dir = list(search_path.glob(f"*{file_extension}"))
            print(f"当前目录中的{file_extension}文件数量: {len(files_in_dir)}")
            if files_in_dir:
                print(f"当前目录中的{file_extension}文件:")
                for f in files_in_dir[:5]:  # 只显示前5个
                    print(f"  - {f.name}")
        except Exception as dir_error:
            print(f"检查目录内容时出错: {dir_error}")
        
        try:
            # 使用更高效的搜索方式
            print(f"开始递归搜索{file_extension}文件...")
            for file_path in search_path.rglob(f"*{file_extension}"):
                search_count += 1
                if search_count > max_search_files:
                    print(f"警告: 搜索文件数量超过限制({max_search_files})，停止搜索")
                    self.report({'WARNING'}, f"搜索文件数量超过限制({max_search_files})，已停止搜索")
                    break
                    
                # 每搜索100个文件更新一次进度
                if search_count % 100 == 0:
                    print(f"已搜索 {search_count} 个文件...")
                    self.report({'INFO'}, f"已搜索 {search_count} 个文件...")
                
                file_name_without_ext = file_path.stem  # 文件名（不含扩展名）
                
                # 检查文件名是否在名称列表中
                for name in name_list:
                    if name.lower() in file_name_without_ext.lower():
                        found_files.append(str(file_path))
                        print(f"匹配成功: {name} -> {file_name_without_ext}")
                        break  # 找到匹配就跳出内层循环
                        
        except Exception as search_error:
            print(f"搜索过程中出错: {search_error}")
            print(f"错误类型: {type(search_error)}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            self.report({'WARNING'}, f"搜索过程中出错: {search_error}")
        
        print(f"搜索完成，找到 {len(found_files)} 个匹配的文件")
        self.report({'INFO'}, f"搜索完成，找到 {len(found_files)} 个匹配的文件")
        
        if not found_files:
            self.report({'WARNING'}, f"在目录 {search_directory} 中未找到匹配的{file_extension}文件")
            return {'CANCELLED'}
        
        # 执行批量导入（添加进度反馈）
        print(f"开始导入 {len(found_files)} 个文件...")
        self.report({'INFO'}, f"开始导入 {len(found_files)} 个文件...")
        
        # 使用改进的批量导入函数
        success, message = self.batch_import_with_progress(found_files)
        
        if success:
            self.report({'INFO'}, f"成功导入 {len(found_files)} 个文件: {message}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
    
    def batch_import_with_progress(self, file_paths):
        """带进度反馈的批量导入"""
        if not file_paths:
            return False, "没有选择任何文件"
        
        # 统计导入结果
        success_count = 0
        error_count = 0
        error_messages = []
        total_files = len(file_paths)
        
        print(f"\n=== 开始批量导入 {total_files} 个文件 ===")
        
        # 遍历并导入每个文件
        for i, file_path in enumerate(file_paths):
            # 更新进度
            progress = (i + 1) / total_files
            print(f"\n进度: {progress:.1%} ({i + 1}/{total_files})")
            
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
                
                # 调用Better FBX导入器
                result = bpy.ops.better_import.fbx(filepath=file_path)
                
                if result == {'FINISHED'}:
                    # 获取新导入的对象
                    objects_after = set(bpy.context.scene.objects)
                    imported_objects = list(objects_after - objects_before)
                    
                    if len(imported_objects) > 0:
                        print(f"成功导入: {os.path.basename(file_path)}")
                        success_count += 1
                        
                        # 重命名骨架
                        rename_armature_to_filename(file_name, imported_objects)
                    else:
                        print(f"导入失败: {os.path.basename(file_path)} - 没有检测到新对象")
                        error_count += 1
                        error_messages.append(f"导入 {os.path.basename(file_path)} 失败: 没有检测到新对象")
                else:
                    print(f"导入失败: {os.path.basename(file_path)} - Better FBX导入器返回: {result}")
                    error_count += 1
                    error_messages.append(f"导入 {os.path.basename(file_path)} 失败: Better FBX导入器返回: {result}")
                
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

# ==================== BetterFBX直接导入功能 ====================

def check_better_fbx_available():
    """检查BetterFBX插件是否可用"""
    try:
        if hasattr(bpy.ops, 'better_import') and hasattr(bpy.ops.better_import, 'fbx'):
            return True
        else:
            return False
    except:
        return False

def import_fbx_with_better_fbx_direct(file_path, import_settings=None):
    """
    直接使用BetterFBX导入FBX文件，不进行回退
    
    参数:
    file_path: FBX文件路径
    import_settings: 导入设置（可选）
    
    返回:
    (success, message, imported_objects)
    """
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用，请先安装并启用BetterFBX插件", []
    
    if not os.path.exists(file_path):
        return False, f"文件不存在: {file_path}", []
    
    try:
        # 记录导入前的对象
        objects_before = set(bpy.context.scene.objects)
        
        # 直接调用BetterFBX导入器
        result = bpy.ops.better_import.fbx(filepath=file_path)
        
        if result != {'FINISHED'}:
            return False, f"BetterFBX导入失败: {result}", []
        
        # 获取新导入的对象
        objects_after = set(bpy.context.scene.objects)
        imported_objects = list(objects_after - objects_before)
        
        if len(imported_objects) == 0:
            return False, "没有检测到新导入的对象", []
        
        # 检查导入的对象是否有顶点组和骨骼
        has_vertex_groups = False
        has_armature = False
        
        for obj in imported_objects:
            if obj.type == 'MESH' and obj.vertex_groups:
                has_vertex_groups = True
            if obj.type == 'ARMATURE':
                has_armature = True
                if obj.data.bones:
                    print(f"检测到骨骼: {obj.name}，包含 {len(obj.data.bones)} 个骨骼")
        
        if has_vertex_groups:
            print(f"✓ 成功导入带顶点组的网格对象")
        if has_armature:
            print(f"✓ 成功导入骨骼对象")
        
        return True, f"成功导入 {len(imported_objects)} 个对象", imported_objects
        
    except Exception as e:
        return False, f"导入过程出错: {str(e)}", []

def batch_import_fbx_files_with_better_fbx_direct(file_paths):
    """
    使用BetterFBX直接批量导入FBX文件列表
    
    参数:
    file_paths: FBX文件路径列表
    
    返回:
    (success, message)
    """
    if not file_paths:
        return False, "没有选择任何文件"
    
    if not check_better_fbx_available():
        return False, "BetterFBX插件不可用，请先安装并启用BetterFBX插件"
    
    print("\n=== 使用BetterFBX直接导入器批量导入 ===")
    
    success_count = 0
    error_count = 0
    error_messages = []
    
    for file_path in file_paths:
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        print(f"\n=== 开始导入文件: {os.path.basename(file_path)} ===")
        
        success, message, imported_objects = import_fbx_with_better_fbx_direct(file_path)
        
        if success:
            print(f"✓ 成功导入: {os.path.basename(file_path)}")
            success_count += 1
            
            # 重命名骨架
            if imported_objects:
                rename_armature_to_filename(file_name, imported_objects)
        else:
            print(f"✗ 导入失败: {os.path.basename(file_path)} - {message}")
            error_count += 1
            error_messages.append(f"导入 {os.path.basename(file_path)} 失败: {message}")
    
    # 生成结果消息
    result_message = f"BetterFBX直接导入完成！成功: {success_count}, 失败: {error_count}"
    if error_messages:
        result_message += f"\n错误详情:\n" + "\n".join(error_messages)
    
    return success_count > 0, result_message

def rename_armature_to_filename(file_name, imported_objects):
    """重命名导入的骨架为文件名"""
    for obj in imported_objects:
        if obj.type == 'ARMATURE':
            obj.name = file_name
            print(f"重命名骨架: {obj.name}")

# BetterFBX直接导入操作器
class BETTER_FBX_OT_DirectBatchImport(Operator):
    """使用BetterFBX直接批量导入FBX文件（推荐）"""
    bl_idname = "better_fbx.direct_batch_import"
    bl_label = "BetterFBX直接批量导入"
    bl_description = "使用BetterFBX直接批量导入，确保顶点组和骨骼信息完整"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        directory_path = context.scene.better_fbx_import_directory
        if not directory_path:
            self.report({'ERROR'}, "请先设置3D文件目录路径")
            return {'CANCELLED'}
        
        # 路径验证
        try:
            valid_path = validate_and_fix_path(directory_path)
            if valid_path is None:
                self.report({'ERROR'}, f"无法找到有效的路径: {directory_path}")
                return {'CANCELLED'}
            directory_path = str(valid_path)
        except Exception as e:
            self.report({'ERROR'}, f"路径验证失败: {str(e)}")
            return {'CANCELLED'}
        
        # 搜索FBX文件
        try:
            dir_path = Path(directory_path)
            files = list(dir_path.rglob("*.fbx"))
            
            if not files:
                self.report({'WARNING'}, f"在目录 {dir_path} 中没有找到FBX文件")
                return {'CANCELLED'}
            
            file_paths = [str(f) for f in files]
            print(f"找到 {len(file_paths)} 个FBX文件")
            
        except Exception as e:
            self.report({'ERROR'}, f"搜索文件失败: {str(e)}")
            return {'CANCELLED'}
        
        # 执行BetterFBX直接导入
        success, message = batch_import_fbx_files_with_better_fbx_direct(file_paths)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}

class BETTER_FBX_OT_DirectBatchImportFiles(Operator, ImportHelper):
    """选择多个FBX文件进行BetterFBX直接导入"""
    bl_idname = "better_fbx.direct_batch_import_files"
    bl_label = "选择多个FBX文件（BetterFBX）"
    bl_description = "选择多个FBX文件进行BetterFBX直接导入，确保顶点组和骨骼信息完整"
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
        # 构建文件路径列表
        file_paths = []
        for file_elem in self.files:
            file_path = os.path.join(self.directory, file_elem.name)
            file_paths.append(file_path)
        
        if not file_paths:
            self.report({'ERROR'}, "没有选择任何文件")
            return {'CANCELLED'}
        
        print(f"选择的FBX文件数量: {len(file_paths)}")
        
        # 执行BetterFBX直接导入
        success, message = batch_import_fbx_files_with_better_fbx_direct(file_paths)
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportByNameList)
    
    # 注册BetterFBX直接导入操作器
    bpy.utils.register_class(BETTER_FBX_OT_DirectBatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_DirectBatchImportFiles)
    
    # 注册场景属性
    bpy.types.Scene.better_fbx_import_directory = bpy.props.StringProperty(
        name="3D文件导入目录",
        description="批量导入的3D文件目录路径",
        subtype='DIR_PATH',
        default=""
    )
    
    # 添加格式选择属性
    bpy.types.Scene.batch_import_file_format = bpy.props.EnumProperty(
        name="批量导入文件格式",
        description="选择要批量导入的3D文件格式",
        items=SUPPORTED_FORMATS,
        default='fbx'
    )
    
    bpy.types.Scene.fbx_name_list_text = bpy.props.StringProperty(
        name="3D文件名称列表",
        description="要查找的3D文件名称列表，每行一个名称。例如：\nmy_model\nmy_character",
        default="",
        maxlen=1024,
    )
    bpy.types.Scene.fbx_search_directory = bpy.props.StringProperty(
        name="搜索目录",
        description="要搜索3D文件的目录路径",
        subtype='DIR_PATH',
        default="",
    )

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportByNameList)
    
    # 注销BetterFBX直接导入操作器
    bpy.utils.unregister_class(BETTER_FBX_OT_DirectBatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_DirectBatchImportFiles)
    
    # 注销场景属性
    try:
        delattr(bpy.types.Scene, "better_fbx_import_directory")
        delattr(bpy.types.Scene, "batch_import_file_format")
        delattr(bpy.types.Scene, "fbx_name_list_text")
        delattr(bpy.types.Scene, "fbx_search_directory")
    except AttributeError:
        pass 