"""
Blender工具：从JSON文件导入Unity AnimationClip数据并创建动作文件
集成到MixTools插件中
"""

import bpy
import json
import os
from mathutils import Euler, Quaternion, Vector

def import_animation_from_json(json_path):
    """
    从JSON文件导入动画数据并创建Blender动作
    
    Args:
        json_path: JSON文件路径
    """
    # 读取JSON文件
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    animation_name = data.get('name', 'ImportedAnimation')
    length = data.get('length', 0)
    frame_rate = data.get('frameRate', 30)
    wrap_mode = data.get('wrapMode', 'Default')
    properties = data.get('properties', [])
    
    # 设置场景帧率
    bpy.context.scene.render.fps = int(frame_rate)
    
    # 创建或获取动作
    action_name = animation_name
    if action_name in bpy.data.actions:
        action = bpy.data.actions[action_name]
        # 清除现有关键帧
        action.fcurves.clear()
    else:
        action = bpy.data.actions.new(name=action_name)
    
    # 按路径和属性名组织数据
    property_groups = {}
    for prop in properties:
        path = prop.get('path', '')
        prop_name = prop.get('propertyName', '')
        key = (path, prop_name)
        
        if key not in property_groups:
            property_groups[key] = []
        property_groups[key].append(prop)
    
    # 处理每个属性
    imported_count = 0
    # 用于跟踪已处理的(data_path, index)组合，避免重复创建
    processed_curves = set()
    
    for (path, prop_name), props in property_groups.items():
        # 确定数据路径和属性
        data_path = None
        index = -1
        
        # 解析属性名，确定是位置、旋转还是缩放
        prop_lower = prop_name.lower()
        
        if 'position' in prop_lower or 'localposition' in prop_lower:
            if 'x' in prop_lower:
                data_path = 'location'
                index = 0
            elif 'y' in prop_lower:
                data_path = 'location'
                index = 1
            elif 'z' in prop_lower:
                data_path = 'location'
                index = 2
        elif 'rotation' in prop_lower or 'localrotation' in prop_lower:
            if 'x' in prop_lower:
                data_path = 'rotation_euler'
                index = 0
            elif 'y' in prop_lower:
                data_path = 'rotation_euler'
                index = 1
            elif 'z' in prop_lower:
                data_path = 'rotation_euler'
                index = 2
            elif 'w' in prop_lower:
                # 四元数旋转
                data_path = 'rotation_quaternion'
                index = 3
        elif 'scale' in prop_lower or 'localscale' in prop_lower:
            if 'x' in prop_lower:
                data_path = 'scale'
                index = 0
            elif 'y' in prop_lower:
                data_path = 'scale'
                index = 1
            elif 'z' in prop_lower:
                data_path = 'scale'
                index = 2
        
        # 如果无法自动识别，尝试直接使用属性名
        if data_path is None:
            # 尝试直接映射
            if prop_name.endswith('.x') or prop_name.endswith('X'):
                data_path = prop_name[:-2] if '.' in prop_name else prop_name[:-1]
                index = 0
            elif prop_name.endswith('.y') or prop_name.endswith('Y'):
                data_path = prop_name[:-2] if '.' in prop_name else prop_name[:-1]
                index = 1
            elif prop_name.endswith('.z') or prop_name.endswith('Z'):
                data_path = prop_name[:-2] if '.' in prop_name else prop_name[:-1]
                index = 2
            elif prop_name.endswith('.w') or prop_name.endswith('W'):
                data_path = prop_name[:-2] if '.' in prop_name else prop_name[:-1]
                index = 3
            else:
                data_path = prop_name
                index = 0
        
        # 检查是否已经处理过这个(data_path, index)组合
        curve_key = (data_path, index)
        if curve_key in processed_curves:
            # 如果已经处理过，合并关键帧或跳过
            continue
        
        # 为每个属性创建F-Curve（通常每个组只有一个prop）
        all_keyframes = []
        for prop in props:
            keyframes = prop.get('keyframes', [])
            if keyframes:
                all_keyframes.extend(keyframes)
        
        if not all_keyframes:
            continue
        
        # 按时间排序关键帧（如果有多个prop合并的情况）
        all_keyframes.sort(key=lambda kf: kf.get('time', 0))
        
        # 检查是否已存在相同的F-Curve，如果存在则先删除
        existing_fcurve = None
        for fc in action.fcurves:
            if fc.data_path == data_path and fc.array_index == index:
                existing_fcurve = fc
                break
        
        if existing_fcurve:
            # 删除已存在的曲线
            action.fcurves.remove(existing_fcurve)
        
        # 创建F-Curve
        fcurve = action.fcurves.new(data_path=data_path, index=index)
        fcurve.keyframe_points.add(len(all_keyframes))
        
        # 设置关键帧
        for i, kf_data in enumerate(all_keyframes):
            time = kf_data.get('time', 0)
            value = kf_data.get('value', 0)
            
            # 转换时间到帧数
            frame = time * frame_rate
            
            kp = fcurve.keyframe_points[i]
            kp.co = (frame, value)
            
            # 检查是否为阶跃函数（无穷大切线）
            is_step_in = kf_data.get('isStepIn', False)
            is_step_out = kf_data.get('isStepOut', False)
            
            # 获取切线值
            in_tangent = kf_data.get('inTangent')
            out_tangent = kf_data.get('outTangent')
            
            # 处理无穷大值（Unity导出的特殊值）
            if in_tangent is not None:
                # 检查是否为表示无穷大的特殊值（999999或-999999）
                if abs(in_tangent) >= 999998:
                    is_step_in = True
            if out_tangent is not None:
                if abs(out_tangent) >= 999998:
                    is_step_out = True
            
            # 根据是否为阶跃函数设置插值类型
            if is_step_in or is_step_out:
                # 阶跃函数：使用常量插值
                kp.interpolation = 'CONSTANT'
                kp.handle_left_type = 'AUTO'
                kp.handle_right_type = 'AUTO'
            else:
                # 正常曲线：使用自动插值
                kp.handle_left_type = 'AUTO'
                kp.handle_right_type = 'AUTO'
                
                # 如果有有效的切线信息，设置插值
                if in_tangent is not None and out_tangent is not None:
                    # 计算控制点位置
                    prev_frame = frame - 1.0 / frame_rate if i > 0 else frame
                    next_frame = frame + 1.0 / frame_rate if i < len(all_keyframes) - 1 else frame
                    
                    # 确保切线值在合理范围内
                    if abs(in_tangent) < 999998 and abs(out_tangent) < 999998:
                        # 设置切线
                        kp.handle_left = (prev_frame, value - in_tangent / frame_rate)
                        kp.handle_right = (next_frame, value + out_tangent / frame_rate)
        
        # 更新F-Curve
        fcurve.update()
        imported_count += 1
        processed_curves.add(curve_key)
    
    # 设置动作范围
    if action.fcurves:
        action.frame_range = (0, length * frame_rate)
    
    # 将动作分配给选中的对象
    if bpy.context.selected_objects:
        obj = bpy.context.selected_objects[0]
        if obj.animation_data is None:
            obj.animation_data_create()
        obj.animation_data.action = action
        print(f"动画 '{action_name}' 已分配给对象 '{obj.name}'")
    else:
        print(f"动画 '{action_name}' 已创建。请手动将其分配给对象。")
    
    print(f"成功导入动画: {animation_name}")
    print(f"时长: {length} 秒, 帧率: {frame_rate} fps")
    print(f"导入属性数: {imported_count}")
    
    return action


class ImportAnimationJsonOperator(bpy.types.Operator):
    """Blender操作符：导入JSON动画"""
    bl_idname = "animation.import_json"
    bl_label = "导入Unity动画JSON"
    bl_description = "从Unity导出的JSON文件导入动画数据并创建动作文件\n\n默认查找路径：Unity项目/Assets/ExportedAnimations/"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        name="文件路径",
        description="JSON动画文件路径",
        maxlen=1024,
        default=""
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.json",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "未选择文件")
            return {'CANCELLED'}
        
        try:
            action = import_animation_from_json(self.filepath)
            # 保存路径到场景属性，以便下次使用
            context.scene.animation_json_import_path = os.path.dirname(self.filepath)
            self.report({'INFO'}, f"成功导入动画: {action.name}\n文件位置: {self.filepath}")
            return {'FINISHED'}
        except FileNotFoundError:
            self.report({'ERROR'}, f"文件未找到: {self.filepath}\n\n请检查文件路径是否正确")
            return {'CANCELLED'}
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"JSON解析失败: {str(e)}\n\n请确认这是Unity导出的动画JSON文件")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        # 获取默认路径（从场景属性或Unity常见路径）
        default_path = ""
        
        # 尝试从场景属性获取上次使用的路径
        if hasattr(context.scene, 'animation_json_import_path'):
            default_path = context.scene.animation_json_import_path
        
        # 如果场景属性中没有，尝试查找Unity项目的常见路径
        if not default_path or not os.path.exists(default_path):
            # 尝试在常见位置查找
            possible_paths = [
                os.path.join(os.path.expanduser("~"), "Documents", "Unity", "Projects"),
                "D:\\work\\p2_client\\Assets\\ExportedAnimations",
                "C:\\Users\\admin\\Documents\\Unity\\Projects",
            ]
            
            for base_path in possible_paths:
                if os.path.exists(base_path):
                    # 查找ExportedAnimations文件夹
                    for root, dirs, files in os.walk(base_path):
                        if "ExportedAnimations" in dirs:
                            default_path = os.path.join(root, "ExportedAnimations")
                            break
                    if default_path and os.path.exists(default_path):
                        break
        
        # 设置默认文件路径
        if default_path and os.path.exists(default_path):
            self.filepath = os.path.join(default_path, "*.json")
        else:
            # 使用Blender文件路径或用户目录
            self.filepath = bpy.path.abspath("//")
            if not self.filepath:
                self.filepath = os.path.expanduser("~")
        
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def register():
    """注册操作符和属性"""
    bpy.utils.register_class(ImportAnimationJsonOperator)
    
    # 注册场景属性，用于保存上次导入的路径
    bpy.types.Scene.animation_json_import_path = bpy.props.StringProperty(
        name="动画JSON导入路径",
        description="上次导入动画JSON文件的路径",
        default=""
    )


def unregister():
    """注销操作符和属性"""
    bpy.utils.unregister_class(ImportAnimationJsonOperator)
    
    # 注销场景属性
    if hasattr(bpy.types.Scene, 'animation_json_import_path'):
        del bpy.types.Scene.animation_json_import_path


if __name__ == "__main__":
    register()

