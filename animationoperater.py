import bpy
import mathutils
import time
import gc  # Add garbage collection import
import random

# 添加日志函数，用于打印详细信息
def log_info(message):
    print(f"[T-Pose重计算] {message}")

# 时间格式化函数
def format_time(seconds):
    """将秒数转换为更易读的时间格式"""
    if seconds < 1:
        return f"{seconds*1000:.0f}毫秒"
    elif seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.1f}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs:.1f}秒"

# 添加内存估计函数
def estimate_memory_usage(bone_count, frame_count):
    """估计操作将使用的内存量（粗略估计，单位为MB）"""
    # 每个骨骼每帧约需要的内存：变换矩阵 + 位置、旋转、缩放等数据
    # 这是一个粗略估计，实际使用可能会有所不同
    bytes_per_bone_frame = 16 * 4 + 3 * 4 + 4 * 4 + 3 * 4  # 矩阵 + 位置 + 四元数 + 缩放
    total_bytes = bone_count * frame_count * bytes_per_bone_frame
    return total_bytes / (1024 * 1024)  # 转换为MB

# 清除所选物体动画中的缩放部分
class ClearScaleAnimation(bpy.types.Operator):
    bl_idname = "animation.clear_scale_animation"
    bl_label = "清除缩放动画"
    bl_description = "从所选物体的动画中清除所有缩放关键帧"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_objects = 0
        
        for obj in selected_objects:
            # 检查对象是否有动画数据
            if obj.animation_data is None or obj.animation_data.action is None:
                continue
                
            action = obj.animation_data.action
            fcurves = action.fcurves
            
            # 标记要删除的曲线
            curves_to_remove = []
            
            # 查找与缩放相关的曲线
            for i, fc in enumerate(fcurves):
                # 检查通道路径是否与缩放相关
                if "scale" in fc.data_path:
                    curves_to_remove.append(i)
            
            # 倒序删除曲线，以避免索引偏移问题
            for index in sorted(curves_to_remove, reverse=True):
                fcurves.remove(fcurves[index])
                
            if curves_to_remove:
                affected_objects += 1
        
        self.report({'INFO'}, f"已从 {affected_objects} 个物体中清除缩放动画")
        return {'FINISHED'}

# 清除所选物体的所有动画
class ClearAllAnimation(bpy.types.Operator):
    bl_idname = "animation.clear_all_animation"
    bl_label = "清除所有动画"
    bl_description = "从所选物体中清除所有动画数据"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_objects = 0
        
        for obj in selected_objects:
            if obj.animation_data:
                obj.animation_data_clear()
                affected_objects += 1
                
        self.report({'INFO'}, f"已从 {affected_objects} 个物体中清除所有动画数据")
        return {'FINISHED'}

# 清除所选物体的位移动画
class ClearLocationAnimation(bpy.types.Operator):
    bl_idname = "animation.clear_location_animation"
    bl_label = "清除位移动画"
    bl_description = "从所选物体的动画中清除所有位移关键帧"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_objects = 0
        
        for obj in selected_objects:
            # 检查对象是否有动画数据
            if obj.animation_data is None or obj.animation_data.action is None:
                continue
                
            action = obj.animation_data.action
            fcurves = action.fcurves
            
            # 标记要删除的曲线
            curves_to_remove = []
            
            # 查找与位移相关的曲线
            for i, fc in enumerate(fcurves):
                # 检查通道路径是否与位移相关
                if "location" in fc.data_path:
                    curves_to_remove.append(i)
            
            # 倒序删除曲线，以避免索引偏移问题
            for index in sorted(curves_to_remove, reverse=True):
                fcurves.remove(fcurves[index])
                
            if curves_to_remove:
                affected_objects += 1
        
        self.report({'INFO'}, f"已从 {affected_objects} 个物体中清除位移动画")
        return {'FINISHED'}

# 清除所选物体的旋转动画
class ClearRotationAnimation(bpy.types.Operator):
    bl_idname = "animation.clear_rotation_animation"
    bl_label = "清除旋转动画"
    bl_description = "从所选物体的动画中清除所有旋转关键帧"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_objects = 0
        
        for obj in selected_objects:
            # 检查对象是否有动画数据
            if obj.animation_data is None or obj.animation_data.action is None:
                continue
                
            action = obj.animation_data.action
            fcurves = action.fcurves
            
            # 标记要删除的曲线
            curves_to_remove = []
            
            # 查找与旋转相关的曲线
            for i, fc in enumerate(fcurves):
                # 检查通道路径是否与旋转相关
                if "rotation" in fc.data_path:
                    curves_to_remove.append(i)
            
            # 倒序删除曲线，以避免索引偏移问题
            for index in sorted(curves_to_remove, reverse=True):
                fcurves.remove(fcurves[index])
                
            if curves_to_remove:
                affected_objects += 1
        
        self.report({'INFO'}, f"已从 {affected_objects} 个物体中清除旋转动画")
        return {'FINISHED'}

# 为所选动画曲线添加循环修改器
class AddCycleModifierToAnimation(bpy.types.Operator):
    bl_idname = "animation.paste_modifiers"
    bl_label = "添加循环修改器(带偏移)"
    bl_description = "为当前在图形编辑器中选择的动画曲线添加带偏移重复的循环修改器"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取所有选中的动画曲线（通过选中的关键帧）
        selected_curves = set()  # 使用集合避免重复
        
        # 遍历所有物体和动画数据
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                for fc in action.fcurves:
                    # 检查曲线是否有选中的关键帧
                    for kf in fc.keyframe_points:
                        if kf.select_control_point:
                            selected_curves.add((obj, fc))
                            break  # 找到选中关键帧就跳出内层循环
        
        if not selected_curves:
            self.report({'WARNING'}, "请在图形编辑器中选择要添加循环修改器的动画关键帧")
            return {'CANCELLED'}
        
        curves_affected = 0
        affected_objects = set()
        
        # 对每个包含选中关键帧的动画曲线添加循环修改器
        for obj, fc in selected_curves:
            try:
                # 添加循环修改器
                cycle_modifier = fc.modifiers.new(type='CYCLES')
                
                # 设置循环修改器参数（带偏移重复）
                cycle_modifier.mode_before = 'REPEAT_OFFSET'  # 前面带偏移重复
                cycle_modifier.mode_after = 'REPEAT_OFFSET'   # 后面带偏移重复
                cycle_modifier.direction = 'FORWARD'   # 向前方向
                
                curves_affected += 1
                affected_objects.add(obj.name)
                
            except Exception as e:
                print(f"对曲线 {fc.data_path} 添加循环修改器时出错: {e}")
                continue
        
        if curves_affected > 0:
            self.report({'INFO'}, f"已为 {len(affected_objects)} 个物体的 {curves_affected} 条动画曲线添加带偏移循环修改器")
        else:
            self.report({'WARNING'}, "添加循环修改器失败")
            
        return {'FINISHED'}

# 为所选动画曲线添加不带偏移的循环修改器
class AddCycleModifierNoOffset(bpy.types.Operator):
    bl_idname = "animation.add_cycle_modifier_no_offset"
    bl_label = "添加循环修改器(无偏移)"
    bl_description = "为当前在图形编辑器中选择的动画曲线添加不带偏移重复的循环修改器"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取所有选中的动画曲线（通过选中的关键帧）
        selected_curves = set()  # 使用集合避免重复
        
        # 遍历所有物体和动画数据
        for obj in bpy.data.objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                for fc in action.fcurves:
                    # 检查曲线是否有选中的关键帧
                    for kf in fc.keyframe_points:
                        if kf.select_control_point:
                            selected_curves.add((obj, fc))
                            break  # 找到选中关键帧就跳出内层循环
        
        if not selected_curves:
            self.report({'WARNING'}, "请在图形编辑器中选择要添加循环修改器的动画关键帧")
            return {'CANCELLED'}
        
        curves_affected = 0
        affected_objects = set()
        
        # 对每个包含选中关键帧的动画曲线添加循环修改器
        for obj, fc in selected_curves:
            try:
                # 添加循环修改器
                cycle_modifier = fc.modifiers.new(type='CYCLES')
                
                # 设置循环修改器参数（不带偏移重复）
                cycle_modifier.mode_before = 'REPEAT'  # 前面简单重复
                cycle_modifier.mode_after = 'REPEAT'   # 后面简单重复
                cycle_modifier.direction = 'FORWARD'   # 向前方向
                
                curves_affected += 1
                affected_objects.add(obj.name)
                
            except Exception as e:
                print(f"对曲线 {fc.data_path} 添加循环修改器时出错: {e}")
                continue
        
        if curves_affected > 0:
            self.report({'INFO'}, f"已为 {len(affected_objects)} 个物体的 {curves_affected} 条动画曲线添加无偏移循环修改器")
        else:
            self.report({'WARNING'}, "添加循环修改器失败")
            
        return {'FINISHED'}

# 移除所有动画曲线的修改器
class RemoveAllModifiersFromAnimation(bpy.types.Operator):
    bl_idname = "animation.remove_all_modifiers"
    bl_label = "移除所有修改器"
    bl_description = "移除所选物体的所有动画曲线的修改器"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要移除修改器的物体")
            return {'CANCELLED'}
        
        curves_affected = 0
        affected_objects = set()
        total_modifiers_removed = 0
        
        # 遍历所选物体
        for obj in selected_objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                
                # 遍历该物体的所有动画曲线
                for fc in action.fcurves:
                    try:
                        # 计算当前曲线的修改器数量
                        modifiers_count = len(fc.modifiers)
                        
                        # 移除所有修改器
                        while fc.modifiers:
                            fc.modifiers.remove(fc.modifiers[0])
                        
                        if modifiers_count > 0:
                            curves_affected += 1
                            total_modifiers_removed += modifiers_count
                    
                    except Exception as e:
                        print(f"对物体 {obj.name} 的曲线 {fc.data_path} 移除修改器时出错: {e}")
                        continue
                
                if curves_affected > 0:
                    affected_objects.add(obj.name)
        
        if curves_affected > 0:
            self.report({'INFO'}, f"已从 {len(affected_objects)} 个物体的 {curves_affected} 条动画曲线移除 {total_modifiers_removed} 个修改器")
        else:
            self.report({'WARNING'}, "所选物体没有找到需要移除的修改器")
            
        return {'FINISHED'}

# 为选中物体添加跟随曲线约束
class AddFollowPathConstraint(bpy.types.Operator):
    bl_idname = "animation.add_follow_path_constraint"
    bl_label = "添加跟随曲线约束"
    bl_description = "为选中的物体添加跟随曲线约束，每个物体对应一条新生成的曲线"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个物体")
            return {'CANCELLED'}
        
        processed_count = 0
        
        for obj in selected_objects:
            try:
                # 为每个物体创建一条新的曲线
                curve_data = bpy.data.curves.new(name=f"{obj.name}_path", type='CURVE')
                curve_data.dimensions = '3D'
                curve_data.resolution_u = 2
                
                # 创建样条线
                spline = curve_data.splines.new('NURBS')
                spline.points.add(3)  # 添加4个点（默认有1个，再添加3个）
                
                # 设置控制点位置，创建一个简单的直线路径
                # 基于物体当前位置创建路径
                obj_location = obj.location
                
                # 创建一条简单的直线路径，总长度约5米
                spline.points[0].co = (obj_location.x - 2.5, obj_location.y, obj_location.z, 1)
                spline.points[1].co = (obj_location.x - 1.25, obj_location.y, obj_location.z, 1)
                spline.points[2].co = (obj_location.x + 1.25, obj_location.y, obj_location.z, 1)
                spline.points[3].co = (obj_location.x + 2.5, obj_location.y, obj_location.z, 1)
                
                # 根据用户设置决定是否创建闭合曲线
                spline.use_cyclic_u = context.scene.curve_closed_option
                
                # 创建曲线物体
                curve_obj = bpy.data.objects.new(f"{obj.name}_path", curve_data)
                context.collection.objects.link(curve_obj)
                
                # 为物体添加跟随路径约束
                constraint = obj.constraints.new(type='FOLLOW_PATH')
                constraint.target = curve_obj
                constraint.use_curve_follow = True  # 启用跟随曲线选项
                constraint.forward_axis = 'FORWARD_X'  # 设置前进轴向
                constraint.up_axis = 'UP_Z'  # 设置上方向轴向
                
                processed_count += 1
                
            except Exception as e:
                print(f"为物体 {obj.name} 添加跟随曲线约束时出错: {e}")
                continue
        
        if processed_count > 0:
            self.report({'INFO'}, f"成功为 {processed_count} 个物体添加了跟随曲线约束")
        else:
            self.report({'WARNING'}, "没有成功为任何物体添加约束")
        
        return {'FINISHED'}

# 设置骨架为静止位置（批量）
class SetToRestPosition(bpy.types.Operator):
    bl_idname = "armature.set_to_rest_position"
    bl_label = "设置为静止位置"
    bl_description = "将所选物体中的骨架设置为静止位置（批量）"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_armatures = 0
        errors = []
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要处理的骨架对象")
            return {'CANCELLED'}
        
        # 保存当前的活动对象和模式
        original_active = context.active_object
        original_mode = context.mode if hasattr(context, 'mode') else 'OBJECT'
        
        try:
            for obj in selected_objects:
                if obj.type == 'ARMATURE':
                    try:
                        # 确保对象可见且可编辑
                        if obj.hide_viewport:
                            obj.hide_viewport = False
                        
                        # 设置为活动对象
                        context.view_layer.objects.active = obj
                        
                        # 设置骨架为静止位置模式
                        obj.data.pose_position = 'REST'
                        
                        affected_armatures += 1
                        print(f"✅ 骨架 '{obj.name}' 已设置为静止位置")
                        
                    except Exception as e:
                        error_msg = f"处理骨架 '{obj.name}' 时出错: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        continue
                else:
                    print(f"⚠️ 跳过非骨架对象: {obj.name} (类型: {obj.type})")
            
            # 恢复原始活动对象
            if original_active:
                context.view_layer.objects.active = original_active
            
            # 报告结果
            if affected_armatures > 0:
                success_msg = f"已将 {affected_armatures} 个骨架设置为静止位置"
                if errors:
                    success_msg += f" (有 {len(errors)} 个错误)"
                self.report({'INFO'}, success_msg)
                
                # 打印错误信息到控制台
                for error in errors:
                    print(f"❌ {error}")
            else:
                self.report({'WARNING'}, "所选物体中没有骨架对象")
                
        except Exception as e:
            error_msg = f"批量设置静止位置时发生错误: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"❌ {error_msg}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

# 设置骨架为姿态位置（批量）
class SetToPosePosition(bpy.types.Operator):
    bl_idname = "armature.set_to_pose_position"
    bl_label = "设置为姿态位置"
    bl_description = "将所选物体中的骨架设置为姿态位置（批量）"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        affected_armatures = 0
        errors = []
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要处理的骨架对象")
            return {'CANCELLED'}
        
        # 保存当前的活动对象和模式
        original_active = context.active_object
        original_mode = context.mode if hasattr(context, 'mode') else 'OBJECT'
        
        try:
            for obj in selected_objects:
                if obj.type == 'ARMATURE':
                    try:
                        # 确保对象可见且可编辑
                        if obj.hide_viewport:
                            obj.hide_viewport = False
                        
                        # 设置为活动对象
                        context.view_layer.objects.active = obj
                        
                        # 设置骨架为姿态位置模式
                        obj.data.pose_position = 'POSE'
                        
                        affected_armatures += 1
                        print(f"✅ 骨架 '{obj.name}' 已设置为姿态位置")
                        
                    except Exception as e:
                        error_msg = f"处理骨架 '{obj.name}' 时出错: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {error_msg}")
                        continue
                else:
                    print(f"⚠️ 跳过非骨架对象: {obj.name} (类型: {obj.type})")
            
            # 恢复原始活动对象
            if original_active:
                context.view_layer.objects.active = original_active
            
            # 报告结果
            if affected_armatures > 0:
                success_msg = f"已将 {affected_armatures} 个骨架设置为姿态位置"
                if errors:
                    success_msg += f" (有 {len(errors)} 个错误)"
                self.report({'INFO'}, success_msg)
                
                # 打印错误信息到控制台
                for error in errors:
                    print(f"❌ {error}")
            else:
                self.report({'WARNING'}, "所选物体中没有骨架对象")
                
        except Exception as e:
            error_msg = f"批量设置姿态位置时发生错误: {str(e)}"
            self.report({'ERROR'}, error_msg)
            print(f"❌ {error_msg}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

# 动画随机偏移操作符（优化版本）
class RandomOffsetAnimation(bpy.types.Operator):
    bl_idname = "animation.random_offset_animation"
    bl_label = "随机偏移动画"
    bl_description = "对所选物体的动画进行高效整体随机偏移，骨架以整体为单位进行偏移。偏移范围根据实际可用空间动态计算"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要处理的物体")
            return {'CANCELLED'}
        
        affected_objects = 0
        total_objects = len(selected_objects)
        
        # 获取场景的帧范围
        scene = context.scene
        frame_start = scene.frame_start
        frame_end = scene.frame_end
        frame_range = frame_end - frame_start
        
        # 简化算法：只要动画与显示范围有完整重叠就可以随机移动
        print(f"🔍 场景帧范围: {frame_start} - {frame_end}")
        # 为每个物体单独计算安全偏移范围
        object_safe_offsets = {}
        
        for obj in selected_objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                obj_min_frame = float('inf')
                obj_max_frame = float('-inf')
                
                # 找到该物体的动画范围
                for fc in action.fcurves:
                    if fc.keyframe_points:
                        for kf in fc.keyframe_points:
                            obj_min_frame = min(obj_min_frame, kf.co[0])
                            obj_max_frame = max(obj_max_frame, kf.co[0])
                
                if obj_min_frame != float('inf') and obj_max_frame != float('-inf'):
                    print(f"🔍 物体 '{obj.name}': 动画范围 {obj_min_frame:.1f}-{obj_max_frame:.1f}, 显示范围 {frame_start}-{frame_end}")
                    
                    # 检查是否有重叠（更宽松的条件）
                    # 1. 帧范围包裹动画
                    frame_contains_animation = (frame_start <= obj_min_frame and obj_max_frame <= frame_end)
                    # 2. 动画包裹帧范围
                    animation_contains_frame = (obj_min_frame <= frame_start and frame_end <= obj_max_frame)
                    # 3. 部分重叠（动画与帧范围有交集）
                    has_partial_overlap = not (obj_max_frame < frame_start or obj_min_frame > frame_end)
                    
                    has_complete_overlap = frame_contains_animation or animation_contains_frame
                    has_any_overlap = has_complete_overlap or has_partial_overlap
                    
                    if has_complete_overlap:
                        # 有完整重叠，根据谁长谁包裹的逻辑计算偏移范围
                        print(f"🔍 物体 '{obj.name}': 进入完整重叠分支")
                        scene_length = frame_end - frame_start
                        animation_length = obj_max_frame - obj_min_frame
                        
                        print(f"📊 物体 '{obj.name}': 完整重叠")
                        print(f"📊 动画范围: {obj_min_frame:.1f} - {obj_max_frame:.1f} (长度: {animation_length:.1f})")
                        print(f"📊 场景范围: {frame_start} - {frame_end} (长度: {scene_length:.1f})")
                        
                        if scene_length >= animation_length:
                            # 场景范围更长，场景包裹动画
                            forward_space = frame_end - obj_max_frame  # 向前空间（负向移动）
                            backward_space = obj_min_frame - frame_start  # 向后空间（正向移动）
                            
                            print(f"📊 场景包裹动画，向前空间: {forward_space:.1f}，向后空间: {backward_space:.1f}")
                            
                            if forward_space == 0 and backward_space == 0:
                                # 动画完全填满场景范围，无需偏移
                                safe_offset = 0
                                can_positive = False
                                can_negative = False
                                print(f"📊 动画完全填满场景范围，无需偏移")
                            else:
                                # 动画可以在场景范围内偏移
                                safe_offset = min(forward_space, backward_space)
                                can_positive = backward_space > 0  # 向后偏移（正向移动）
                                can_negative = forward_space > 0   # 向前偏移（负向移动）
                                if can_positive and can_negative:
                                    print(f"📊 动画可在场景范围内偏移: ±{safe_offset:.1f}")
                                elif can_positive:
                                    print(f"📊 动画可在场景范围内偏移: +{safe_offset:.1f} (向后)")
                                elif can_negative:
                                    print(f"📊 动画可在场景范围内偏移: -{safe_offset:.1f} (向前)")
                                else:
                                    print(f"📊 动画可在场景范围内偏移: 0")
                        else:
                            # 动画范围更长，动画包裹场景
                            forward_space = obj_max_frame - frame_end  # 向前超出（负向移动）
                            backward_space = frame_start - obj_min_frame  # 向后超出（正向移动）
                            
                            print(f"📊 动画包裹场景，向前超出: {forward_space:.1f}，向后超出: {backward_space:.1f}")
                            
                            # 动画可以在超出场景的范围内偏移
                            # 使用较大的超出空间作为偏移范围，而不是取最小值
                            if forward_space > 0 and backward_space > 0:
                                # 双向都有超出，使用较小的作为安全偏移
                                safe_offset = min(forward_space, backward_space)
                                can_positive = True   # 向后偏移（正向移动）
                                can_negative = True   # 向前偏移（负向移动）
                            elif forward_space > 0:
                                # 只有向前超出
                                safe_offset = forward_space
                                can_positive = False  # 不能向后偏移
                                can_negative = True   # 可以向前偏移（负向移动）
                            elif backward_space > 0:
                                # 只有向后超出
                                safe_offset = backward_space
                                can_positive = True   # 可以向后偏移（正向移动）
                                can_negative = False  # 不能向前偏移
                            else:
                                # 没有超出（这种情况不应该发生）
                                safe_offset = 0
                                can_positive = False
                                can_negative = False
                            
                            if can_positive and can_negative:
                                print(f"📊 动画可在超出场景范围内偏移: ±{safe_offset:.1f}")
                            elif can_positive:
                                print(f"📊 动画可在超出场景范围内偏移: +{safe_offset:.1f} (向后)")
                            elif can_negative:
                                print(f"📊 动画可在超出场景范围内偏移: -{safe_offset:.1f} (向前)")
                            else:
                                print(f"📊 动画可在超出场景范围内偏移: 0")
                        
                        # 存储偏移信息
                        offset_info = {
                            'offset': safe_offset,
                            'can_positive': can_positive,
                            'can_negative': can_negative,
                            'max_positive': safe_offset if can_positive else 0,
                            'max_negative': safe_offset if can_negative else 0
                        }
                        object_safe_offsets[obj] = offset_info
                    elif has_partial_overlap:
                        # 有部分重叠，先计算需要移动多少帧才能完全重叠
                        print(f"🔍 物体 '{obj.name}': 进入部分重叠分支")
                        # 计算动画需要移动的距离
                        if obj_min_frame < frame_start:
                            # 动画开始太早，需要向后移动（正向移动）
                            move_offset = frame_start - obj_min_frame
                            # 计算移动后剩余的空间
                            remaining_space = frame_end - (obj_max_frame + move_offset)
                            safe_offset = max(0, remaining_space)
                            can_positive = remaining_space > 0  # 向后偏移（正向移动）
                            can_negative = False  # 已经移动到最左边界
                        else:
                            # 动画结束太晚，需要向前移动（负向移动）
                            move_offset = frame_end - obj_max_frame  # 这会是负值
                            # 计算移动后剩余的空间
                            remaining_space = (obj_min_frame + move_offset) - frame_start
                            safe_offset = max(0, remaining_space)
                            can_positive = False  # 已经移动到最右边界
                            can_negative = remaining_space > 0  # 向前偏移（负向移动）
                        
                        print(f"📊 物体 '{obj.name}': 有部分重叠，需要先移动 {move_offset:.1f} 帧到完全重叠位置")
                        print(f"📊 移动后剩余空间: {remaining_space:.1f}，实际可偏移范围: ±{safe_offset:.1f}")
                        
                        # 存储偏移信息，包含预移动偏移
                        offset_info = {
                            'offset': safe_offset,
                            'can_positive': can_positive,
                            'can_negative': can_negative,
                            'max_positive': safe_offset if can_positive else 0,
                            'max_negative': safe_offset if can_negative else 0,
                            'pre_move_offset': move_offset  # 预移动偏移
                        }
                        object_safe_offsets[obj] = offset_info
                    else:
                        print(f"🔍 物体 '{obj.name}': 进入无重叠分支")
                        print(f"⚠️ 物体 '{obj.name}': 动画范围 {obj_min_frame:.1f}-{obj_max_frame:.1f} 与显示范围 {frame_start}-{frame_end} 无重叠，跳过")
                        object_safe_offsets[obj] = 0
        
        # 开始处理
        start_time = time.time()
        
        for i, obj in enumerate(selected_objects):
            # 检查对象是否有动画数据
            if obj.animation_data is None:
                print(f"⚠️ 物体 '{obj.name}': 没有animation_data，跳过")
                continue
                
            if obj.animation_data.action is None:
                print(f"⚠️ 物体 '{obj.name}': 没有action，跳过")
                continue
            
            action = obj.animation_data.action
            fcurves = action.fcurves
            
            if not fcurves:
                print(f"⚠️ 物体 '{obj.name}': 没有动画曲线，跳过")
                continue
                
            print(f"🔍 物体 '{obj.name}': 找到 {len(fcurves)} 条动画曲线")
            
            # 生成随机偏移值
            pre_move_offset = 0  # 预移动偏移
            if obj in object_safe_offsets:
                # 使用该物体的安全偏移范围和方向信息
                offset_info = object_safe_offsets[obj]
                if offset_info == 0:
                    print(f"⚠️ 跳过物体 '{obj.name}': 动画与场景帧范围无重叠")
                    continue
                elif offset_info['offset'] <= 0:
                    print(f"ℹ️ 物体 '{obj.name}': 偏移空间为 {offset_info['offset']:.1f}，无需偏移")
                    # 当偏移空间为0时，不进行偏移
                    safe_offset = 0
                    can_positive = False
                    can_negative = False
                else:
                    safe_offset = offset_info['offset']
                    can_positive = offset_info['can_positive']
                    can_negative = offset_info['can_negative']
                
                # 检查是否需要预移动
                if 'pre_move_offset' in offset_info:
                    pre_move_offset = offset_info['pre_move_offset']
                    print(f"🔧 物体 '{obj.name}': 需要预移动 {pre_move_offset:.1f} 帧")
                
                # 根据可偏移方向生成随机偏移
                if safe_offset <= 0 or (not can_positive and not can_negative):
                    # 没有可用空间或无法偏移，跳过
                    print(f"ℹ️ 物体 '{obj.name}': 无需偏移，跳过处理")
                    continue
                elif can_positive and can_negative:
                    # 可以双向偏移
                    random_offset = random.randint(-safe_offset, safe_offset)
                    print(f"🎯 物体 '{obj.name}': 可以双向偏移，生成偏移: {random_offset} (范围: ±{safe_offset})")
                elif can_positive:
                    # 只能向后偏移（正向移动）
                    random_offset = random.randint(0, safe_offset)
                    print(f"🎯 物体 '{obj.name}': 只能向后偏移，生成偏移: {random_offset} (范围: 0-{safe_offset})")
                elif can_negative:
                    # 只能向前偏移（负向移动）
                    random_offset = random.randint(-safe_offset, 0)
                    print(f"🎯 物体 '{obj.name}': 只能向前偏移，生成偏移: {random_offset} (范围: -{safe_offset}-0)")
                else:
                    # 无法偏移，跳过
                    print(f"ℹ️ 物体 '{obj.name}': 无法偏移，跳过处理")
                    continue
            else:
                # 这种情况应该很少见，使用默认的小范围偏移
                default_offset = 10
                random_offset = random.randint(-default_offset, default_offset)
                print(f"ℹ️ 物体 '{obj.name}': 使用默认偏移范围 ±{default_offset}，实际偏移: {random_offset}")
            
            print(f"🎲 物体 '{obj.name}': 生成随机偏移 {random_offset} 帧")
            
            if random_offset == 0:
                print(f"ℹ️ 物体 '{obj.name}': 随机偏移为0，仍会处理（用于更新动画数据）")
                # 不再跳过零偏移，因为可能仍需要更新动画数据
            
            # 计算总偏移量（预移动 + 随机偏移）
            total_offset = pre_move_offset + random_offset
            print(f"🔧 开始处理物体 '{obj.name}': 预移动 {pre_move_offset:.1f} 帧 + 随机偏移 {random_offset} 帧 = 总偏移 {total_offset:.1f} 帧")
            
            # 检查偏移方向是否正确
            if can_positive and not can_negative and total_offset < 0:
                print(f"⚠️ 警告: 应该只能正向偏移，但总偏移为负值 {total_offset:.1f}")
            elif can_negative and not can_positive and total_offset > 0:
                print(f"⚠️ 警告: 应该只能负向偏移，但总偏移为正值 {total_offset:.1f}")
            # 对整个动画进行整体偏移（最高效的方法）
            try:
                # 保存原始状态
                original_mode = bpy.context.mode
                original_active = bpy.context.view_layer.objects.active
                
                # 确保对象处于对象模式
                if bpy.context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                # 设置为活动对象
                bpy.context.view_layer.objects.active = obj
                
                # 确保动画数据没有被锁定
                if obj.animation_data:
                    # 在Blender 3.6中，直接设置action即可
                    obj.animation_data.action = action
                
                # 对整个动作进行整体偏移（高效方法）
                keyframes_modified = 0
                if action:
                    # 更新动作的帧范围
                    action.frame_range = (action.frame_start + total_offset, action.frame_end + total_offset)
                    
                    # 对所有动画曲线进行整体偏移
                    for fc in fcurves:
                        try:
                            # 确保曲线没有被锁定
                            fc.lock = False
                            fc.mute = False
                            
                            # 直接修改每个关键帧的x坐标（时间轴）
                            for kf in fc.keyframe_points:
                                kf.co[0] += total_offset
                            keyframes_modified += len(fc.keyframe_points)
                        except Exception as e:
                            print(f"⚠️ 处理曲线 {fc.data_path} 时出错: {e}")
                            continue
                
                # 强制更新动画数据
                # 在Blender 3.6中，Action对象没有update方法，需要手动更新
                # 通过重新计算关键帧来触发更新
                for fc in fcurves:
                    fc.update()
                
                # 恢复原始状态
                if original_active:
                    bpy.context.view_layer.objects.active = original_active
                if original_mode != 'OBJECT':
                    try:
                        bpy.ops.object.mode_set(mode=original_mode)
                    except:
                        pass  # 如果无法恢复模式，忽略错误
                
                print(f"✅ 物体 '{obj.name}': 已修改 {keyframes_modified} 个关键帧")
                
                # 确保当前物体的动画轨道没有被锁定
                for fc in fcurves:
                    try:
                        fc.lock = False
                        fc.mute = False
                    except:
                        pass
                
                affected_objects += 1
                
                # 定期进行垃圾回收，避免内存积累
                if (i + 1) % 50 == 0:
                    gc.collect()
                
                # 显示进度（每10个物体或最后一个物体显示一次）
                if (i + 1) % 10 == 0 or (i + 1) == total_objects:
                    elapsed_time = time.time() - start_time
                    if pre_move_offset != 0:
                        offset_info = f"预移动 {pre_move_offset:.1f} 帧 + 随机偏移 {random_offset} 帧"
                    else:
                        offset_info = f"偏移 {random_offset} 帧"
                    
                    if obj in object_safe_offsets and object_safe_offsets[obj] != 0:
                        offset_data = object_safe_offsets[obj]
                        if offset_data['can_positive'] and offset_data['can_negative']:
                            offset_info += f" (实际范围: ±{offset_data['offset']:.1f})"
                        elif offset_data['can_positive']:
                            offset_info += f" (实际范围: +{offset_data['offset']:.1f})"
                        elif offset_data['can_negative']:
                            offset_info += f" (实际范围: -{offset_data['offset']:.1f})"
                    print(f"✅ 进度: {i + 1}/{total_objects} - 物体 '{obj.name}' 已{offset_info} (耗时: {format_time(elapsed_time)})")
                    
            except Exception as e:
                print(f"⚠️ 处理物体 '{obj.name}' 时出错: {e}")
                continue
        
        # 完成处理
        total_time = time.time() - start_time
        
        # 确保所有处理过的物体动画轨道没有被锁定
        print("🔓 检查并解锁动画轨道...")
        unlocked_curves = 0
        for obj in selected_objects:
            if obj.animation_data and obj.animation_data.action:
                action = obj.animation_data.action
                for fc in action.fcurves:
                    try:
                        if fc.lock:
                            fc.lock = False
                            unlocked_curves += 1
                        if fc.mute:
                            fc.mute = False
                            unlocked_curves += 1
                    except Exception as e:
                        print(f"⚠️ 解锁曲线 {fc.data_path} 时出错: {e}")
                        pass
        
        if unlocked_curves > 0:
            print(f"🔓 已解锁 {unlocked_curves} 个动画轨道")
        else:
            print("🔓 所有动画轨道都已解锁")
        
        if affected_objects > 0:
            avg_time = total_time / affected_objects
            self.report({'INFO'}, f"已对 {affected_objects} 个物体的动画进行随机偏移 (总耗时: {format_time(total_time)}, 平均: {format_time(avg_time)}/物体)")
        else:
            # 提供更详细的错误信息
            no_animation_count = 0
            no_overlap_count = 0
            for obj in selected_objects:
                if obj.animation_data is None or obj.animation_data.action is None:
                    no_animation_count += 1
                elif obj in object_safe_offsets and object_safe_offsets[obj] == 0:
                    no_overlap_count += 1
            
            error_msg = f"所选物体中没有找到可偏移的动画数据"
            if no_animation_count > 0:
                error_msg += f" ({no_animation_count} 个物体没有动画数据"
            if no_overlap_count > 0:
                if no_animation_count > 0:
                    error_msg += f", {no_overlap_count} 个物体动画与场景帧范围无重叠"
                else:
                    error_msg += f" ({no_overlap_count} 个物体动画与场景帧范围无重叠"
            if no_animation_count > 0 or no_overlap_count > 0:
                error_msg += ")"
            
            self.report({'WARNING'}, error_msg)
        
        return {'FINISHED'}

# 移除动画起始和结束的重复帧
class RemoveDuplicateFrames(bpy.types.Operator):
    bl_idname = "animation.remove_duplicate_frames"
    bl_label = "移除重复帧"
    bl_description = "移除所选物体动画中起始和结束的重复帧，保留离动作帧最近的一个"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    def execute(self, context):
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要处理的物体")
            return {'CANCELLED'}
        
        affected_objects = 0
        total_frames_removed = 0
        total_objects = len(selected_objects)
        start_time = time.time()
        
        print(f"🚀 开始处理 {total_objects} 个物体的重复帧移除...")
        print(f"📊 检测模式: {context.scene.duplicate_frames_detection_mode}")
        print(f"📊 检测阈值: {context.scene.duplicate_frames_threshold}")
        print(f"⏰ 开始时间: {time.strftime('%H:%M:%S')}")
        print("=" * 60)
        
        for obj_idx, obj in enumerate(selected_objects, 1):
            # 检查对象是否有动画数据
            if obj.animation_data is None or obj.animation_data.action is None:
                print(f"⏭️  [{obj_idx}/{total_objects}] 跳过物体 '{obj.name}': 没有动画数据")
                continue
                
            action = obj.animation_data.action
            fcurves = action.fcurves
            
            if not fcurves:
                print(f"⏭️  [{obj_idx}/{total_objects}] 跳过物体 '{obj.name}': 没有动画曲线")
                continue
            
            print(f"🔍 [{obj_idx}/{total_objects}] 处理物体 '{obj.name}': 找到 {len(fcurves)} 条动画曲线")
            
            # 高效分析所有曲线的重复帧
            curves_processed = 0
            frames_removed_this_obj = 0
            
            # 预过滤：只处理可能有重复帧的曲线
            valid_curves = []
            threshold = context.scene.duplicate_frames_threshold
            for fc in fcurves:
                keyframes = fc.keyframe_points
                if len(keyframes) >= 3:  # 至少需要3个关键帧
                    # 快速预检查：如果第一个和最后一个关键帧值相同，可能有重复帧
                    first_val = keyframes[0].co[1]
                    last_val = keyframes[-1].co[1]
                    if abs(first_val - last_val) <= threshold:
                        valid_curves.append(fc)
                    else:
                        # 即使首尾不同，也可能有部分重复，也加入处理
                        valid_curves.append(fc)
            
            print(f"  🔍 预过滤后需要处理的曲线: {len(valid_curves)}/{len(fcurves)}")
            
            # 批量处理有效曲线
            for curve_idx, fc in enumerate(valid_curves, 1):
                try:
                    # 获取所有关键帧
                    keyframes = fc.keyframe_points
                    
                    # 按时间排序关键帧
                    sorted_keyframes = sorted(keyframes, key=lambda kf: kf.co[0])
                    
                    # 快速跳过：如果关键帧太少，直接跳过
                    if len(sorted_keyframes) < 3:
                        continue
                    
                    # 从场景属性获取设置
                    detection_mode = context.scene.duplicate_frames_detection_mode
                    threshold = context.scene.duplicate_frames_threshold
                    
                    # 根据模式选择检测方法
                    if detection_mode == 'FAST':
                        start_frames_to_remove = self._detect_start_duplicates(sorted_keyframes, threshold)
                        end_frames_to_remove = self._detect_end_duplicates(sorted_keyframes, threshold)
                    elif detection_mode == 'PRECISE':
                        start_frames_to_remove = self._detect_start_duplicates_fallback(sorted_keyframes, threshold)
                        end_frames_to_remove = self._detect_end_duplicates_fallback(sorted_keyframes, threshold)
                    else:  # SMART mode
                        # 智能选择：根据关键帧数量选择最佳方法
                        if len(sorted_keyframes) > 100:
                            start_frames_to_remove = self._detect_start_duplicates(sorted_keyframes, threshold)
                            end_frames_to_remove = self._detect_end_duplicates(sorted_keyframes, threshold)
                        else:
                            start_frames_to_remove = self._detect_start_duplicates_fallback(sorted_keyframes, threshold)
                            end_frames_to_remove = self._detect_end_duplicates_fallback(sorted_keyframes, threshold)
                    
                    # 移除重复帧
                    frames_removed = self._remove_duplicate_keyframes(fc, start_frames_to_remove, end_frames_to_remove)
                    
                    if frames_removed > 0:
                        curves_processed += 1
                        frames_removed_this_obj += frames_removed
                        print(f"  ✅ [{curve_idx}/{len(valid_curves)}] 曲线 '{fc.data_path}': 移除了 {frames_removed} 个重复帧")
                    else:
                        print(f"  ℹ️  [{curve_idx}/{len(valid_curves)}] 曲线 '{fc.data_path}': 无重复帧")
                    
                except Exception as e:
                    print(f"  ⚠️ [{curve_idx}/{len(valid_curves)}] 处理曲线 '{fc.data_path}' 时出错: {e}")
                    continue
            
            if curves_processed > 0:
                affected_objects += 1
                total_frames_removed += frames_removed_this_obj
                print(f"✅ [{obj_idx}/{total_objects}] 物体 '{obj.name}': 处理了 {curves_processed} 条曲线，移除了 {frames_removed_this_obj} 个重复帧")
            else:
                print(f"ℹ️  [{obj_idx}/{total_objects}] 物体 '{obj.name}': 没有找到需要移除的重复帧")
            
            # 显示当前进度百分比和时间统计
            progress_percent = (obj_idx / total_objects) * 100
            elapsed_time = time.time() - start_time
            avg_time_per_obj = elapsed_time / obj_idx if obj_idx > 0 else 0
            estimated_remaining = avg_time_per_obj * (total_objects - obj_idx)
            
            print(f"📊 进度: {progress_percent:.1f}% ({obj_idx}/{total_objects})")
            print(f"⏱️ 已用时间: {format_time(elapsed_time)} | 预计剩余: {format_time(estimated_remaining)}")
            print("-" * 40)
        
        # 最终结果汇总
        total_time = time.time() - start_time
        print("=" * 60)
        print("🎉 处理完成！")
        print(f"📊 总处理物体: {total_objects}")
        print(f"✅ 成功处理: {affected_objects}")
        print(f"🗑️ 总移除帧数: {total_frames_removed}")
        print(f"📈 成功率: {(affected_objects/total_objects)*100:.1f}%")
        print(f"⏱️ 总耗时: {format_time(total_time)}")
        print(f"⚡ 平均速度: {total_objects/total_time:.1f}物体/秒")
        print("=" * 60)
        
        if affected_objects > 0:
            self.report({'INFO'}, f"已从 {affected_objects} 个物体中移除 {total_frames_removed} 个重复帧")
        else:
            self.report({'WARNING'}, "所选物体中没有找到需要移除的重复帧")
        
        return {'FINISHED'}
    
    def _detect_start_duplicates(self, sorted_keyframes, threshold):
        """高效检测起始重复帧 - 使用向量化操作"""
        if len(sorted_keyframes) < 3:
            return []
        
        # 提取所有关键帧的值到numpy数组进行批量比较
        try:
            import numpy as np
            values = np.array([kf.co[1] for kf in sorted_keyframes])
            reference_value = values[0]
            
            # 向量化比较：一次性比较所有值与参考值
            differences = np.abs(values - reference_value)
            duplicate_mask = differences <= threshold
            
            # 找到第一个非重复帧的位置
            first_different_idx = np.argmax(~duplicate_mask)
            if first_different_idx == 0 and not duplicate_mask[0]:
                # 如果第一个就是不同的，说明没有重复帧
                return []
            
            # 返回从第二个到第一个不同帧之前的所有帧
            return [sorted_keyframes[i] for i in range(1, first_different_idx) if duplicate_mask[i]]
            
        except ImportError:
            # 如果numpy不可用，回退到原始方法
            return self._detect_start_duplicates_fallback(sorted_keyframes, threshold)
    
    def _detect_end_duplicates(self, sorted_keyframes, threshold):
        """高效检测结束重复帧 - 使用向量化操作"""
        if len(sorted_keyframes) < 3:
            return []
        
        try:
            import numpy as np
            values = np.array([kf.co[1] for kf in sorted_keyframes])
            reference_value = values[-1]
            
            # 向量化比较：一次性比较所有值与参考值
            differences = np.abs(values - reference_value)
            duplicate_mask = differences <= threshold
            
            # 从后往前找到第一个非重复帧的位置
            last_different_idx = len(values) - 1 - np.argmax(~duplicate_mask[::-1])
            if last_different_idx == len(values) - 1 and not duplicate_mask[-1]:
                # 如果最后一个就是不同的，说明没有重复帧
                return []
            
            # 返回从倒数第二个到最后一个不同帧之后的所有帧
            return [sorted_keyframes[i] for i in range(last_different_idx + 1, len(values) - 1) if duplicate_mask[i]]
            
        except ImportError:
            # 如果numpy不可用，回退到原始方法
            return self._detect_end_duplicates_fallback(sorted_keyframes, threshold)
    
    def _detect_start_duplicates_fallback(self, sorted_keyframes, threshold):
        """回退方法：原始逐帧检测"""
        frames_to_remove = []
        reference_value = sorted_keyframes[0].co[1]
        
        for i in range(1, len(sorted_keyframes)):
            current_value = sorted_keyframes[i].co[1]
            if abs(current_value - reference_value) <= threshold:
                frames_to_remove.append(sorted_keyframes[i])
            else:
                break
        
        return frames_to_remove
    
    def _detect_end_duplicates_fallback(self, sorted_keyframes, threshold):
        """回退方法：原始逐帧检测"""
        frames_to_remove = []
        reference_value = sorted_keyframes[-1].co[1]
        
        for i in range(len(sorted_keyframes) - 2, -1, -1):
            current_value = sorted_keyframes[i].co[1]
            if abs(current_value - reference_value) <= threshold:
                frames_to_remove.append(sorted_keyframes[i])
            else:
                break
        
        return frames_to_remove
    
    def _remove_duplicate_keyframes(self, fcurve, start_frames, end_frames):
        """移除重复的关键帧"""
        frames_to_remove = start_frames + end_frames
        
        if not frames_to_remove:
            return 0
        
        # 按时间排序要移除的帧
        frames_to_remove.sort(key=lambda kf: kf.co[0])
        
        # 倒序移除关键帧，避免索引偏移问题
        removed_count = 0
        for kf in reversed(frames_to_remove):
            try:
                fcurve.keyframe_points.remove(kf)
                removed_count += 1
            except ValueError:
                # 关键帧可能已经被移除
                continue
        
        return removed_count

def register():
    bpy.utils.register_class(ClearScaleAnimation)
    bpy.utils.register_class(ClearAllAnimation)
    bpy.utils.register_class(ClearLocationAnimation)
    bpy.utils.register_class(ClearRotationAnimation)
    bpy.utils.register_class(AddCycleModifierToAnimation)
    bpy.utils.register_class(AddCycleModifierNoOffset)
    bpy.utils.register_class(RemoveAllModifiersFromAnimation)
    bpy.utils.register_class(AddFollowPathConstraint)
    bpy.utils.register_class(SetToRestPosition)
    bpy.utils.register_class(SetToPosePosition)
    bpy.utils.register_class(RandomOffsetAnimation)
    bpy.utils.register_class(RemoveDuplicateFrames)

def unregister():
    bpy.utils.unregister_class(ClearScaleAnimation)
    bpy.utils.unregister_class(ClearAllAnimation)
    bpy.utils.unregister_class(ClearLocationAnimation)
    bpy.utils.unregister_class(ClearRotationAnimation)
    bpy.utils.unregister_class(AddCycleModifierToAnimation)
    bpy.utils.unregister_class(AddCycleModifierNoOffset)
    bpy.utils.unregister_class(RemoveAllModifiersFromAnimation)
    bpy.utils.unregister_class(AddFollowPathConstraint)
    bpy.utils.unregister_class(SetToRestPosition)
    bpy.utils.unregister_class(SetToPosePosition)
    bpy.utils.unregister_class(RandomOffsetAnimation)
    bpy.utils.unregister_class(RemoveDuplicateFrames)

