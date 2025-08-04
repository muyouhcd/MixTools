import bpy
import os
from pathlib import Path
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

def normalize_blender_path(path_string):
    """
    规范化Blender路径格式
    
    参数:
    path_string: Blender路径字符串
    
    返回:
    规范化后的Path对象
    """
    if not path_string:
        return None
    
    print(f"原始路径: {path_string}")
    
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

def find_valid_path(original_path):
    """
    尝试多种方式找到有效的路径
    
    参数:
    original_path: 原始路径字符串
    
    返回:
    有效的Path对象或None
    """
    print(f"尝试解析路径: {original_path}")
    
    # 方法1: 直接使用原始路径
    try:
        path1 = Path(original_path)
        if path1.exists():
            print(f"方法1成功: {path1}")
            return path1
    except Exception as e:
        print(f"方法1失败: {e}")
    
    # 方法2: 规范化路径
    try:
        path2 = normalize_blender_path(original_path)
        if path2 and path2.exists():
            print(f"方法2成功: {path2}")
            return path2
    except Exception as e:
        print(f"方法2失败: {e}")
    
    # 方法3: 尝试解析相对路径
    try:
        path3 = Path(original_path).resolve()
        if path3.exists():
            print(f"方法3成功: {path3}")
            return path3
    except Exception as e:
        print(f"方法3失败: {e}")
    
    # 方法4: 尝试绝对路径
    try:
        path4 = Path(original_path).absolute()
        if path4.exists():
            print(f"方法4成功: {path4}")
            return path4
    except Exception as e:
        print(f"方法4失败: {e}")
    
    # 方法5: 尝试处理常见的路径问题
    try:
        # 移除可能的驱动器前缀问题
        clean_path = original_path
        if clean_path.startswith('//'):
            clean_path = clean_path[2:]
        clean_path = clean_path.replace('\\', '/')
        
        # 尝试不同的驱动器
        drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:']
        
        for drive in drives:
            test_path = Path(f"{drive}/{clean_path}")
            if test_path.exists():
                print(f"方法5成功: {test_path}")
                return test_path
    except Exception as e:
        print(f"方法5失败: {e}")
    
    # 方法6: 专门处理Blender的路径格式
    try:
        # 处理 //..\..\ 格式的路径
        if original_path.startswith('//'):
            # 移除开头的 //
            clean_path = original_path[2:]
            # 处理Windows路径分隔符
            clean_path = clean_path.replace('\\', '/')
            
            # 尝试不同的驱动器
            drives = ['C:', 'D:', 'E:', 'F:', 'G:', 'H:', 'I:', 'J:', 'K:', 'L:', 'M:', 'N:', 'O:', 'P:', 'Q:', 'R:', 'S:', 'T:', 'U:', 'V:', 'W:', 'X:', 'Y:', 'Z:']
            
            for drive in drives:
                test_path = Path(f"{drive}/{clean_path}")
                if test_path.exists():
                    print(f"方法6成功: {test_path}")
                    return test_path
    except Exception as e:
        print(f"方法6失败: {e}")
    
    # 方法7: 尝试从Blender文件路径推断
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
                if test_path.exists():
                    print(f"方法7成功: {test_path}")
                    return test_path
    except Exception as e:
        print(f"方法7失败: {e}")
    
    print("所有路径解析方法都失败了")
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
                print(f"可能的原因:")
                print(f"1. 文件导入失败")
                print(f"2. 文件内容为空")
                print(f"3. 导入设置有问题")
                print(f"4. Better FBX插件可能有问题")
                
                # 尝试使用Blender内置的FBX导入器
                print(f"尝试使用Blender内置FBX导入器...")
                try:
                    result = bpy.ops.import_scene.fbx(filepath=file_path)
                    print(f"内置导入器结果: {result}")
                    
                    # 再次检查新对象
                    objects_after_builtin = set(bpy.context.scene.objects)
                    imported_objects_builtin = list(objects_after_builtin - objects_before)
                    print(f"内置导入器新对象数量: {len(imported_objects_builtin)}")
                    
                    if len(imported_objects_builtin) > 0:
                        print(f"内置导入器成功！")
                        imported_objects = imported_objects_builtin
                        success_count += 1
                        rename_armature_to_filename(file_name, imported_objects)
                        continue
                except Exception as builtin_error:
                    print(f"内置导入器也失败: {builtin_error}")
                
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

def batch_import_fbx(directory_path, file_extension=".fbx"):
    """
    批量导入指定目录下的所有FBX文件
    
    参数:
    directory_path: 要导入的文件所在目录
    file_extension: 要导入的文件扩展名，默认为.fbx
    """
    # 确保目录路径存在
    if not os.path.exists(directory_path):
        print(f"目录不存在: {directory_path}")
        return False, f"目录不存在: {directory_path}"
    
    # 获取目录下所有指定扩展名的文件
    files = [f for f in os.listdir(directory_path) if f.lower().endswith(file_extension.lower())]
    
    if not files:
        message = f"在目录 {directory_path} 中没有找到{file_extension}文件"
        print(message)
        return False, message
    
    # 构建完整文件路径列表
    file_paths = [os.path.join(directory_path, f) for f in files]
    
    # 使用新的文件列表导入函数
    return batch_import_fbx_files(file_paths)

def batch_import_fbx_directories(directory_paths, file_extension=".fbx"):
    """
    批量导入多个目录下的所有FBX文件
    
    参数:
    directory_paths: 要导入的文件所在目录列表
    file_extension: 要导入的文件扩展名，默认为.fbx
    """
    all_file_paths = []
    
    for directory_path in directory_paths:
        # 确保目录路径存在
        if not os.path.exists(directory_path):
            print(f"目录不存在: {directory_path}")
            continue
        
        # 获取目录下所有指定扩展名的文件
        files = [f for f in os.listdir(directory_path) if f.lower().endswith(file_extension.lower())]
        
        # 构建完整文件路径
        for file in files:
            all_file_paths.append(os.path.join(directory_path, file))
    
    if not all_file_paths:
        message = f"在所选目录中没有找到{file_extension}文件"
        print(message)
        return False, message
    
    # 使用新的文件列表导入函数
    return batch_import_fbx_files(all_file_paths)

class BETTER_FBX_OT_BatchImport(Operator):
    """使用Better FBX导入器批量导入FBX文件"""
    bl_idname = "better_fbx.batch_import"
    bl_label = "Better FBX批量导入"
    bl_description = "使用Better FBX导入器批量导入指定目录下的所有FBX文件，并自动重命名骨架"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 检查Better FBX插件是否可用
        try:
            # 检查Better FBX插件是否已注册
            if not hasattr(bpy.ops, 'better_import') or not hasattr(bpy.ops.better_import, 'fbx'):
                self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"检查Better FBX插件时出错: {str(e)}")
            return {'CANCELLED'}
        
        # 使用场景中设置的目录
        directory_path = context.scene.better_fbx_import_directory
        if not directory_path:
            self.report({'ERROR'}, "请先设置FBX文件目录路径")
            return {'CANCELLED'}
        
        # 执行批量导入
        success, message = batch_import_fbx(directory_path)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}


class BETTER_FBX_OT_BatchImportFiles(Operator, ImportHelper):
    """浏览选择多个FBX文件"""
    bl_idname = "better_fbx.batch_import_files"
    bl_label = "选择多个FBX文件"
    bl_description = "浏览选择多个FBX文件进行批量导入"
    bl_options = {'REGISTER', 'UNDO'}
    
    # 设置文件过滤器为FBX文件
    filename_ext = ".fbx"
    filter_glob: StringProperty(
        default="*.fbx",
        options={'HIDDEN'},
        maxlen=255,
    ) # type: ignore
    
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
        # 检查Better FBX插件是否可用
        try:
            # 检查Better FBX插件是否已注册
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
        
        # 执行批量导入
        success, message = batch_import_fbx_files(file_paths)
        
        if success:
            self.report({'INFO'}, message)
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # 打开文件浏览器选择文件
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class BETTER_FBX_OT_BatchImportByNameList(Operator):
    """根据名称列表批量导入FBX文件"""
    bl_idname = "better_fbx.batch_import_by_name_list"
    bl_label = "按名称列表批量导入"
    bl_description = "根据名称列表在指定路径下查找并批量导入FBX文件"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 检查Better FBX插件是否可用
        try:
            # 检查Better FBX插件是否已注册
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
        
        if not name_list_text.strip():
            self.report({'ERROR'}, "请输入名称列表")
            return {'CANCELLED'}
        
        if not search_directory:
            self.report({'ERROR'}, "请选择搜索目录")
            return {'CANCELLED'}
        
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
        
        # 在指定目录下查找匹配的FBX文件
        found_files = []
        
        # 处理路径格式问题
        try:
            # 使用新的路径查找函数
            search_path = find_valid_path(search_directory)
            if search_path is None:
                self.report({'ERROR'}, f"无法找到有效的路径: {search_directory}\n请检查路径是否正确，或者尝试手动输入绝对路径。")
                return {'CANCELLED'}
            
            print(f"最终使用的路径: {search_path}")
        except Exception as e:
            self.report({'ERROR'}, f"路径处理错误: {search_directory}\n错误信息: {str(e)}")
            return {'CANCELLED'}
        
        # 递归搜索目录下的所有FBX文件
        print(f"开始搜索FBX文件...")
        fbx_files_found = list(search_path.rglob("*.fbx"))
        print(f"找到 {len(fbx_files_found)} 个FBX文件")
        
        for fbx_file in fbx_files_found:
            file_name_without_ext = fbx_file.stem  # 文件名（不含扩展名）
            print(f"检查文件: {file_name_without_ext}")
            
            # 检查文件名是否在名称列表中
            for name in name_list:
                if name.lower() in file_name_without_ext.lower():
                    found_files.append(str(fbx_file))
                    print(f"匹配成功: {name} -> {file_name_without_ext}")
                    break  # 找到匹配就跳出内层循环
        
        if not found_files:
            self.report({'WARNING'}, f"在目录 {search_directory} 中未找到匹配的FBX文件")
            return {'CANCELLED'}
        
        # 执行批量导入
        success, message = batch_import_fbx_files(found_files)
        
        if success:
            self.report({'INFO'}, f"成功导入 {len(found_files)} 个文件: {message}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, message)
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportByNameList)
    
    # 注册场景属性
    bpy.types.Scene.better_fbx_import_directory = bpy.props.StringProperty(
        name="Better FBX导入目录",
        description="Better FBX批量导入的文件目录路径",
        subtype='DIR_PATH',
        default=""
    )
    bpy.types.Scene.fbx_name_list_text = bpy.props.StringProperty(
        name="FBX名称列表",
        description="要查找的FBX文件名称列表，每行一个名称。例如：\nmy_model\nmy_character",
        default="",
        maxlen=1024,
    )
    bpy.types.Scene.fbx_search_directory = bpy.props.StringProperty(
        name="搜索目录",
        description="要搜索FBX文件的目录路径",
        subtype='DIR_PATH',
        default="",
    )

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportFiles)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportByNameList)
    
    # 注销场景属性
    try:
        delattr(bpy.types.Scene, "better_fbx_import_directory")
        delattr(bpy.types.Scene, "fbx_name_list_text")
        delattr(bpy.types.Scene, "fbx_search_directory")
    except AttributeError:
        pass 