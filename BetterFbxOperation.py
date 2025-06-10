import bpy
import os
from pathlib import Path
from bpy.props import StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

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
    
    # 导入设置
    import_settings = {
        'use_auto_bone_orientation': True,  # 自动骨骼方向
        'my_import_normal': 'Import',       # 导入法线
        'use_auto_smooth': True,           # 自动平滑
        'my_angle': 60.0,                  # 平滑角度
        'my_shade_mode': 'Smooth',         # 平滑着色
        'use_import_materials': True,      # 导入材质
        'my_rotation_mode': 'QUATERNION',  # 旋转模式
    }
    
    print("\n=== 导入设置 ===")
    for key, value in import_settings.items():
        print(f"{key}: {value}")
    
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
            
            # 调用Better FBX导入器
            bpy.ops.better_import.fbx(
                filepath=file_path,
                **import_settings
            )
            print(f"成功导入: {os.path.basename(file_path)}")
            success_count += 1
            
            # 获取新导入的对象
            objects_after = set(bpy.context.scene.objects)
            imported_objects = list(objects_after - objects_before)
            
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
            # 尝试调用Better FBX导入器来检查插件是否可用
            bpy.ops.better_import.fbx
        except AttributeError:
            self.report({'ERROR'}, "Better FBX插件未安装或未启用！请先安装并启用Better FBX插件。")
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
            # 尝试调用Better FBX导入器来检查插件是否可用
            bpy.ops.better_import.fbx
        except AttributeError:
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

def register():
    bpy.utils.register_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.register_class(BETTER_FBX_OT_BatchImportFiles)
    
    # 注册场景属性
    bpy.types.Scene.better_fbx_import_directory = bpy.props.StringProperty(
        name="Better FBX导入目录",
        description="Better FBX批量导入的文件目录路径",
        subtype='DIR_PATH',
        default=""
    )

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImport)
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchImportFiles)
    
    # 注销场景属性
    try:
        delattr(bpy.types.Scene, "better_fbx_import_directory")
    except AttributeError:
        pass 