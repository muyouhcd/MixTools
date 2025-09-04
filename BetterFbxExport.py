import bpy
import os
from pathlib import Path
from bpy.types import Operator

def check_better_fbx_export_available():
    """检查BetterFBX导出器是否可用"""
    try:
        if hasattr(bpy.ops, 'better_export') and hasattr(bpy.ops.better_export, 'fbx'):
            return True
        else:
            return False
    except:
        return False

def get_better_fbx_export_settings():
    """
    获取BetterFBX的当前导出设置
    
    返回:
    导出设置字典或None
    """
    try:
        # 尝试从BetterFBX的导出设置中获取参数
        export_settings = {}
        
        # 检查是否有BetterFBX的导出设置面板
        if hasattr(bpy.context.scene, 'better_fbx_export_settings'):
            settings = bpy.context.scene.better_fbx_export_settings
            for attr in dir(settings):
                if not attr.startswith('_') and not callable(getattr(settings, attr)):
                    export_settings[attr] = getattr(settings, attr)
        
        # 如果没有找到专门的设置面板，尝试从场景属性中获取
        if not export_settings:
            # 常见的FBX导出设置属性
            common_settings = [
                'use_selection', 'use_active_collection', 'global_scale',
                'apply_unit_scale', 'apply_scale_options', 'bake_space_transform',
                'object_types', 'use_mesh_modifiers', 'use_mesh_edges',
                'use_tspace', 'use_custom_props', 'add_leaf_bones',
                'primary_bone_axis', 'secondary_bone_axis', 'use_armature_deform_only',
                'bake_anim', 'bake_anim_use_all_bones', 'bake_anim_use_nla_strips',
                'bake_anim_use_all_actions', 'bake_anim_force_startend_keying',
                'bake_anim_step', 'bake_anim_keep_curves', 'bake_anim_optimize',
                'path_mode', 'embed_textures', 'batch_mode', 'use_metadata'
            ]
            
            for setting in common_settings:
                if hasattr(bpy.context.scene, setting):
                    export_settings[setting] = getattr(bpy.context.scene, setting)
        
        print(f"获取到的导出设置: {export_settings}")
        return export_settings
        
    except Exception as e:
        print(f"获取BetterFBX导出设置时出错: {e}")
        return None

def get_top_level_objects():
    """
    获取场景中的顶级物体（没有父级的物体）
    
    返回:
    顶级物体列表
    """
    top_level_objects = []
    
    for obj in bpy.context.scene.objects:
        # 检查是否为顶级物体（没有父级）
        if obj.parent is None:
            top_level_objects.append(obj)
    
    print(f"找到 {len(top_level_objects)} 个顶级物体")
    for obj in top_level_objects:
        print(f"  - {obj.name} (类型: {obj.type})")
    
    return top_level_objects

def get_object_hierarchy(obj):
    """
    获取指定物体及其所有子物体的层次结构
    
    参数:
    obj: 根物体
    
    返回:
    包含根物体和所有子物体的列表
    """
    hierarchy = [obj]
    
    def collect_children(parent):
        for child in parent.children:
            hierarchy.append(child)
            collect_children(child)
    
    collect_children(obj)
    
    print(f"物体 {obj.name} 的层次结构包含 {len(hierarchy)} 个物体")
    return hierarchy

def select_objects_for_export(objects):
    """
    选择指定的物体用于导出
    
    参数:
    objects: 要选择的物体列表
    """
    # 先取消选择所有物体
    bpy.ops.object.select_all(action='DESELECT')
    
    # 选择指定的物体
    for obj in objects:
        obj.select_set(True)
    
    # 设置活动物体
    if objects:
        bpy.context.view_layer.objects.active = objects[0]
    
    print(f"已选择 {len(objects)} 个物体用于导出")

def export_object_group_as_fbx(root_obj, export_directory, export_settings=None):
    """
    将指定物体组导出为FBX文件
    
    参数:
    root_obj: 根物体
    export_directory: 导出目录
    export_settings: 导出设置
    
    返回:
    (success, message, file_path)
    """
    try:
        # 获取物体层次结构
        hierarchy = get_object_hierarchy(root_obj)
        
        # 选择这些物体
        select_objects_for_export(hierarchy)
        
        # 生成文件名（使用根物体名称）
        safe_name = "".join(c for c in root_obj.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_name:
            safe_name = "unnamed_object"
        
        # 确保文件名唯一
        counter = 1
        base_name = safe_name
        while True:
            if counter == 1:
                filename = f"{base_name}.fbx"
            else:
                filename = f"{base_name}_{counter:03d}.fbx"
            
            file_path = os.path.join(export_directory, filename)
            if not os.path.exists(file_path):
                break
            counter += 1
        
        print(f"导出文件: {filename}")
        print(f"完整路径: {file_path}")
        
        # 使用BetterFBX导出器
        if export_settings and hasattr(bpy.ops, 'better_export') and hasattr(bpy.ops.better_export, 'fbx'):
            # 尝试使用BetterFBX导出器
            try:
                # 这里需要根据实际的BetterFBX导出器API调整参数
                result = bpy.ops.better_export.fbx(
                    filepath=file_path,
                    use_selection=True
                )
                
                if result == {'FINISHED'}:
                    return True, f"成功导出: {filename}", file_path
                else:
                    return False, f"BetterFBX导出失败: {result}", None
                    
            except Exception as better_export_error:
                print(f"BetterFBX导出器出错: {better_export_error}")
                # 回退到标准FBX导出器
                pass
        
        # 回退到标准FBX导出器
        print("使用标准FBX导出器...")
        result = bpy.ops.export_scene.fbx(
            filepath=file_path,
            use_selection=True,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_ALL',
            bake_space_transform=False,
            object_types={'ARMATURE', 'MESH', 'EMPTY'},
            use_mesh_modifiers=True,
            use_mesh_edges=False,
            use_tspace=False,
            use_custom_props=False,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=False,
            bake_anim=False,
            path_mode='COPY',
            embed_textures=False,
            batch_mode='OFF',
            use_metadata=True
        )
        
        if result == {'FINISHED'}:
            return True, f"成功导出: {filename}", file_path
        else:
            return False, f"标准FBX导出失败: {result}", None
            
    except Exception as e:
        error_msg = f"导出物体组 {root_obj.name} 时出错: {str(e)}"
        print(error_msg)
        return False, error_msg, None

def batch_export_by_top_level_objects(export_directory, export_settings=None):
    """
    按顶级物体批量导出FBX文件
    
    参数:
    export_directory: 导出目录
    export_settings: 导出设置
    
    返回:
    (success, message, exported_files)
    """
    print(f"\n=== 开始按顶级物体批量导出 ===")
    print(f"导出目录: {export_directory}")
    
    # 检查导出目录
    if not os.path.exists(export_directory):
        try:
            os.makedirs(export_directory)
            print(f"创建导出目录: {export_directory}")
        except Exception as e:
            return False, f"无法创建导出目录: {str(e)}", []
    
    # 获取顶级物体
    top_level_objects = get_top_level_objects()
    
    if not top_level_objects:
        return False, "场景中没有找到顶级物体", []
    
    # 统计导出结果
    success_count = 0
    error_count = 0
    exported_files = []
    error_messages = []
    
    # 遍历每个顶级物体进行导出
    for i, root_obj in enumerate(top_level_objects):
        print(f"\n进度: {(i + 1)}/{len(top_level_objects)}")
        print(f"处理顶级物体: {root_obj.name}")
        
        # 导出物体组
        success, message, file_path = export_object_group_as_fbx(
            root_obj, export_directory, export_settings
        )
        
        if success:
            print(f"✓ {message}")
            success_count += 1
            exported_files.append(file_path)
        else:
            print(f"✗ {message}")
            error_count += 1
            error_messages.append(f"导出 {root_obj.name} 失败: {message}")
    
    # 生成结果消息
    result_message = f"批量导出完成！成功: {success_count}, 失败: {error_count}"
    if error_messages:
        result_message += f"\n错误详情:\n" + "\n".join(error_messages)
    
    print(f"\n=== 导出结果 ===")
    print(result_message)
    print(f"导出的文件:")
    for file_path in exported_files:
        print(f"  - {os.path.basename(file_path)}")
    
    return success_count > 0, result_message, exported_files

# BetterFBX批量导出操作器
class BETTER_FBX_OT_BatchExportByTopLevel(Operator):
    """按顶级物体批量导出FBX文件"""
    bl_idname = "better_fbx.batch_export_by_top_level"
    bl_label = "按顶级物体批量导出"
    bl_description = "将每个顶级物体及其所有子物体作为一组导出为FBX文件，使用顶级物体名称命名"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 检查BetterFBX导出器是否可用
        if not check_better_fbx_export_available():
            self.report({'WARNING'}, "BetterFBX导出器不可用，将使用标准FBX导出器")
        
        # 获取导出目录
        export_directory = context.scene.better_fbx_export_directory
        if not export_directory:
            self.report({'ERROR'}, "请先设置FBX导出目录")
            return {'CANCELLED'}
        
        # 路径验证
        try:
            # 使用简单的路径验证
            if not os.path.exists(export_directory):
                try:
                    os.makedirs(export_directory)
                    print(f"创建导出目录: {export_directory}")
                except Exception as e:
                    self.report({'ERROR'}, f"无法创建导出目录: {str(e)}")
                    return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"路径验证失败: {str(e)}")
            return {'CANCELLED'}
        
        # 获取BetterFBX导出设置
        export_settings = get_better_fbx_export_settings()
        
        # 执行批量导出
        success, message, exported_files = batch_export_by_top_level_objects(
            export_directory, export_settings
        )
        
        if success:
            self.report({'INFO'}, message)
        else:
            self.report({'ERROR'}, message)
        
        return {'FINISHED'}



def register():
    bpy.utils.register_class(BETTER_FBX_OT_BatchExportByTopLevel)
    
    # 注册场景属性
    bpy.types.Scene.better_fbx_export_directory = bpy.props.StringProperty(
        name="FBX导出目录",
        description="批量导出的FBX文件保存目录",
        subtype='DIR_PATH',
        default=""
    )

def unregister():
    bpy.utils.unregister_class(BETTER_FBX_OT_BatchExportByTopLevel)
    
    # 注销场景属性
    try:
        delattr(bpy.types.Scene, "better_fbx_export_directory")
    except AttributeError:
        pass
