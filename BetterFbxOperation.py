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

def batch_import_with_better_fbx(file_paths, rename_top_level=False):
    """
    使用BetterFBX插件批量导入FBX文件列表 - 简单逐个导入
    
    参数:
    file_paths: FBX文件路径列表
    rename_top_level: 是否重命名顶级父级为文件名
    
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
            # 记录导入前的对象数量
            objects_before = len(bpy.context.scene.objects)
            
            # 直接调用BetterFBX导入器，使用默认设置
            result = bpy.ops.better_import.fbx(filepath=file_path)
            
            if result == {'FINISHED'}:
                print(f"✓ 成功导入: {os.path.basename(file_path)}")
                
                # 等待导入完全完成
                bpy.context.view_layer.update()
                
                # 如果需要重命名顶级父级
                if rename_top_level:
                    print(f"  → 开始重命名处理...")
                    # 获取导入后新增的对象
                    objects_after = len(bpy.context.scene.objects)
                    print(f"  → 导入前对象数量: {objects_before}, 导入后对象数量: {objects_after}")
                    
                    if objects_after > objects_before:
                        # 找到新导入的对象
                        new_objects = bpy.context.scene.objects[objects_before:]
                        print(f"  → 新导入的对象数量: {len(new_objects)}")
                        
                        # 获取文件名（不含扩展名）
                        file_name = os.path.splitext(os.path.basename(file_path))[0]
                        print(f"  → 目标文件名: {file_name}")
                        
                        # 打印所有新对象的名称和父级信息
                        for i, obj in enumerate(new_objects):
                            parent_name = obj.parent.name if obj.parent else "None"
                            print(f"  → 新对象 {i}: '{obj.name}', 父级: {parent_name}")
                        
                        # 查找顶级父级对象（没有父级的对象）
                        top_level_objects = [obj for obj in new_objects if obj.parent is None]
                        print(f"  → 新导入的顶级父级对象数量: {len(top_level_objects)}")
                        
                        # 如果新导入的对象中没有顶级父级，通过分析父级关系找到真正的顶级父级
                        if not top_level_objects:
                            print(f"  → 新导入对象中没有顶级父级，通过分析父级关系找到真正的顶级父级...")
                            
                            # 收集所有新导入对象的父级链
                            all_parents = set()
                            for obj in new_objects:
                                current_obj = obj
                                while current_obj.parent is not None:
                                    all_parents.add(current_obj.parent)
                                    current_obj = current_obj.parent
                            
                            # 打印所有父级对象
                            print(f"  → 所有父级对象:")
                            for i, parent in enumerate(all_parents):
                                print(f"    {i}: '{parent.name}' (类型: {parent.type}, 父级: {parent.parent.name if parent.parent else 'None'})")
                            
                            print(f"  → 找到 {len(all_parents)} 个父级对象")
                            
                            # 从父级对象中找到真正的顶级父级（没有父级的父级）
                            top_parents = [parent for parent in all_parents if parent.parent is None]
                            print(f"  → 找到 {len(top_parents)} 个顶级父级对象")
                            
                            # 打印所有顶级父级对象
                            for i, parent in enumerate(top_parents):
                                print(f"  → 顶级父级 {i}: '{parent.name}' (类型: {parent.type})")
                            
                            # 选择目标对象
                            target_obj = None
                            
                            # 1. 优先选择名称包含Root的顶级父级
                            for parent in top_parents:
                                if 'root' in parent.name.lower():
                                    target_obj = parent
                                    print(f"  → 找到Root顶级父级: '{parent.name}' (类型: {parent.type})")
                                    break
                            
                            # 2. 如果没找到Root，优先选择空物体
                            if target_obj is None:
                                for parent in top_parents:
                                    if parent.type == 'EMPTY':
                                        target_obj = parent
                                        print(f"  → 选择空物体作为顶级父级: '{parent.name}' (类型: {parent.type})")
                                        break
                            
                            # 3. 如果还没找到，选择第一个顶级父级
                            if target_obj is None and top_parents:
                                target_obj = top_parents[0]
                                print(f"  → 选择第一个顶级父级: '{target_obj.name}' (类型: {target_obj.type})")
                            
                            if target_obj is None:
                                print(f"  → 警告: 没有找到合适的顶级父级进行重命名")
                        else:
                            # 新导入的对象中有顶级父级，但需要检查是否还有更高级的父级
                            print(f"  → 新导入对象中有顶级父级，检查是否还有更高级的父级...")
                            
                            # 打印新导入的顶级对象及其类型
                            for i, obj in enumerate(top_level_objects):
                                obj_type = obj.type
                                print(f"  → 新导入顶级对象 {i}: '{obj.name}' (类型: {obj_type})")
                            
                            # 检查新导入的顶级对象是否还有父级
                            all_parents = set()
                            for obj in top_level_objects:
                                current_obj = obj
                                while current_obj.parent is not None:
                                    all_parents.add(current_obj.parent)
                                    current_obj = current_obj.parent
                            
                            # 同时检查所有新导入对象的父级链
                            for obj in new_objects:
                                current_obj = obj
                                while current_obj.parent is not None:
                                    all_parents.add(current_obj.parent)
                                    current_obj = current_obj.parent
                            
                            # 从父级对象中找到真正的顶级父级（没有父级的父级）
                            top_parents = [parent for parent in all_parents if parent.parent is None]
                            
                            target_obj = None
                            
                            if top_parents:
                                print(f"  → 找到 {len(top_parents)} 个更高级的顶级父级对象")
                                
                                # 打印所有更高级的顶级父级对象
                                for i, parent in enumerate(top_parents):
                                    print(f"  → 更高级顶级父级 {i}: '{parent.name}' (类型: {parent.type})")
                                
                                # 1. 优先选择名称包含Root的顶级父级
                                for parent in top_parents:
                                    if 'root' in parent.name.lower():
                                        target_obj = parent
                                        print(f"  → 找到Root顶级父级: '{parent.name}' (类型: {parent.type})")
                                        break
                                
                                # 2. 如果没找到Root，优先选择空物体
                                if target_obj is None:
                                    for parent in top_parents:
                                        if parent.type == 'EMPTY':
                                            target_obj = parent
                                            print(f"  → 选择空物体作为顶级父级: '{parent.name}' (类型: {parent.type})")
                                            break
                                
                                # 3. 如果还没找到，选择第一个更高级的顶级父级
                                if target_obj is None:
                                    target_obj = top_parents[0]
                                    print(f"  → 选择第一个更高级的顶级父级: '{target_obj.name}' (类型: {target_obj.type})")
                            else:
                                # 没有更高级的父级，从新导入的顶级对象中选择
                                print(f"  → 没有更高级的父级，从新导入的顶级对象中选择...")
                                
                                # 1. 首先尝试找到名称包含文件名的顶级对象
                                for obj in top_level_objects:
                                    if file_name in obj.name:
                                        target_obj = obj
                                        print(f"  → 找到包含文件名的顶级对象: '{obj.name}' (类型: {obj.type})")
                                        break
                                
                                # 2. 如果没找到，优先选择空物体
                                if target_obj is None:
                                    for obj in top_level_objects:
                                        if obj.type == 'EMPTY':
                                            target_obj = obj
                                            print(f"  → 选择空物体作为顶级父级: '{obj.name}' (类型: {obj.type})")
                                            break
                                
                                # 3. 如果还没找到，选择第一个顶级对象
                                if target_obj is None and top_level_objects:
                                    target_obj = top_level_objects[0]
                                    print(f"  → 选择第一个新导入的顶级对象: '{target_obj.name}' (类型: {target_obj.type})")
                        
                        if target_obj:
                            old_name = target_obj.name
                            target_obj.name = file_name
                            print(f"  → 重命名对象 '{old_name}' 为: '{file_name}'")
                        else:
                            print(f"  → 警告: 没有找到可重命名的对象")
                    else:
                        print(f"  → 警告: 导入后对象数量没有增加")
                
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
        
        # 获取重命名选项
        rename_top_level = getattr(scene, 'fbx_rename_top_level', False)
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths, rename_top_level)
        
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
        
        # 获取重命名选项
        scene = context.scene
        rename_top_level = getattr(scene, 'fbx_rename_top_level', False)
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths, rename_top_level)
        
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
        
        # 获取重命名选项
        rename_top_level = getattr(scene, 'fbx_rename_top_level', False)
        
        # 执行批量导入
        success, message = batch_import_with_better_fbx(file_paths, rename_top_level)
        
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