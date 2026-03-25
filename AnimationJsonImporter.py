"""
Blender工具：从JSON文件导入Unity AnimationClip数据并创建动作文件
集成到MixTools插件中
"""

import bpy
import json
import math
import os
from mathutils import Euler, Quaternion, Vector

def map_unity_property_json(prop_name):
    """
    将Unity JSON属性名映射到Blender属性名
    处理Unity(左手系Y-up)到Blender(右手系Z-up)的坐标系转换

    Returns:
        (data_path, index, value_scale) 或 None（无法识别时）
    """
    prop_lower = prop_name.lower()
    deg2rad = math.pi / 180.0

    # 位置: Unity(X,Y,Z) -> Blender(X,-Z,Y)
    if 'position' in prop_lower or 'localposition' in prop_lower:
        if 'x' in prop_lower:
            return 'location', 0, 1.0
        elif 'y' in prop_lower:
            return 'location', 2, 1.0
        elif 'z' in prop_lower:
            return 'location', 1, -1.0

    # 欧拉旋转: 角度->弧度 + 轴交换
    if 'rotation' in prop_lower or 'localrotation' in prop_lower:
        if 'w' in prop_lower:
            return 'rotation_quaternion', 3, 1.0
        elif 'x' in prop_lower:
            return 'rotation_euler', 0, deg2rad
        elif 'y' in prop_lower:
            return 'rotation_euler', 2, deg2rad
        elif 'z' in prop_lower:
            return 'rotation_euler', 1, -deg2rad

    # 缩放: Unity(X,Y,Z) -> Blender(X,Z,Y)
    if 'scale' in prop_lower or 'localscale' in prop_lower:
        if 'x' in prop_lower:
            return 'scale', 0, 1.0
        elif 'y' in prop_lower:
            return 'scale', 2, 1.0
        elif 'z' in prop_lower:
            return 'scale', 1, 1.0

    return None


def get_bone_name_from_path_json(unity_path):
    """从Unity路径中提取骨骼名称"""
    if not unity_path:
        return None
    parts = unity_path.strip('/').split('/')
    return parts[-1] if parts else None


def build_data_path_json(base_property, unity_path, target_obj):
    """构建Blender F-Curve的data_path，骨骼动画使用 pose.bones["name"].prop 格式"""
    if not unity_path:
        return base_property

    bone_name = get_bone_name_from_path_json(unity_path)

    if (target_obj and target_obj.type == 'ARMATURE' and
        target_obj.data and bone_name and
        bone_name in target_obj.data.bones):
        return f'pose.bones["{bone_name}"].{base_property}'

    return base_property


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
        action.fcurves.clear()
    else:
        action = bpy.data.actions.new(name=action_name)

    # 获取目标对象
    target_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None

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
    processed_curves = set()

    for (path, prop_name), props in property_groups.items():
        # 映射属性（包含坐标系转换）
        mapping = map_unity_property_json(prop_name)

        if mapping:
            data_path, index, value_scale = mapping
        else:
            # 无法自动识别，尝试直接使用属性名
            value_scale = 1.0
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

        # 构建完整的data_path（处理骨骼动画）
        full_data_path = build_data_path_json(data_path, path, target_obj)

        # 使用完整路径+索引去重，避免不同骨骼的同名属性被跳过
        curve_key = (full_data_path, index)
        if curve_key in processed_curves:
            continue

        # 收集关键帧
        all_keyframes = []
        for prop in props:
            keyframes = prop.get('keyframes', [])
            if keyframes:
                all_keyframes.extend(keyframes)

        if not all_keyframes:
            continue

        all_keyframes.sort(key=lambda kf: kf.get('time', 0))

        # 移除已存在的F-Curve
        existing_fcurve = None
        for fc in action.fcurves:
            if fc.data_path == full_data_path and fc.array_index == index:
                existing_fcurve = fc
                break

        if existing_fcurve:
            action.fcurves.remove(existing_fcurve)

        # 创建F-Curve
        fcurve = action.fcurves.new(data_path=full_data_path, index=index)
        fcurve.keyframe_points.add(len(all_keyframes))

        # 设置关键帧
        for i, kf_data in enumerate(all_keyframes):
            time = kf_data.get('time', 0)
            raw_value = kf_data.get('value', 0)

            # 应用坐标系转换
            value = raw_value * value_scale

            frame = time * frame_rate

            kp = fcurve.keyframe_points[i]
            kp.co = (frame, value)

            # 检查是否为阶跃函数
            is_step_in = kf_data.get('isStepIn', False)
            is_step_out = kf_data.get('isStepOut', False)

            in_tangent = kf_data.get('inTangent')
            out_tangent = kf_data.get('outTangent')

            if in_tangent is not None and abs(in_tangent) >= 999998:
                is_step_in = True
            if out_tangent is not None and abs(out_tangent) >= 999998:
                is_step_out = True

            if is_step_in or is_step_out:
                kp.interpolation = 'CONSTANT'
            else:
                kp.interpolation = 'BEZIER'

                if in_tangent is not None and out_tangent is not None:
                    if abs(in_tangent) < 999998 and abs(out_tangent) < 999998:
                        # 应用value_scale到切线
                        scaled_in = in_tangent * value_scale
                        scaled_out = out_tangent * value_scale

                        # 计算handle距离（相邻帧间距的1/3）
                        if i > 0:
                            prev_frame = all_keyframes[i - 1].get('time', 0) * frame_rate
                            dt_left = (frame - prev_frame) / 3.0
                        else:
                            dt_left = 1.0 / 3.0

                        if i < len(all_keyframes) - 1:
                            next_frame = all_keyframes[i + 1].get('time', 0) * frame_rate
                            dt_right = (next_frame - frame) / 3.0
                        else:
                            dt_right = 1.0 / 3.0

                        if dt_left > 0 and dt_right > 0:
                            kp.handle_left_type = 'FREE'
                            kp.handle_right_type = 'FREE'
                            slope_in_per_frame = scaled_in / frame_rate
                            slope_out_per_frame = scaled_out / frame_rate
                            kp.handle_left = (frame - dt_left, value - slope_in_per_frame * dt_left)
                            kp.handle_right = (frame + dt_right, value + slope_out_per_frame * dt_right)
                        else:
                            kp.handle_left_type = 'AUTO'
                            kp.handle_right_type = 'AUTO'

        fcurve.update()
        imported_count += 1
        processed_curves.add(curve_key)

    # 设置动作范围
    if action.fcurves:
        action.frame_range = (0, length * frame_rate)

    # 将动作分配给选中的对象
    if target_obj:
        if target_obj.animation_data is None:
            target_obj.animation_data_create()
        target_obj.animation_data.action = action
        print(f"动画 '{action_name}' 已分配给对象 '{target_obj.name}'")
    else:
        print(f"动画 '{action_name}' 已创建。请手动将其分配给对象。")

    print(f"成功导入动画: {animation_name}, 时长: {length}s, 帧率: {frame_rate}fps, 导入属性数: {imported_count}")

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

