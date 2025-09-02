import bpy
import mathutils
import time
import gc  # Add garbage collection import

# 添加日志函数，用于打印详细信息
def log_info(message):
    print(f"[T-Pose重计算] {message}")

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

def register():
    bpy.utils.register_class(ClearScaleAnimation)
    bpy.utils.register_class(ClearAllAnimation)
    bpy.utils.register_class(ClearLocationAnimation)
    bpy.utils.register_class(ClearRotationAnimation)
    bpy.utils.register_class(AddCycleModifierToAnimation)
    bpy.utils.register_class(AddCycleModifierNoOffset)
    bpy.utils.register_class(RemoveAllModifiersFromAnimation)

def unregister():
    bpy.utils.unregister_class(ClearScaleAnimation)
    bpy.utils.unregister_class(ClearAllAnimation)
    bpy.utils.unregister_class(ClearLocationAnimation)
    bpy.utils.unregister_class(ClearRotationAnimation)
    bpy.utils.unregister_class(AddCycleModifierToAnimation)
    bpy.utils.unregister_class(AddCycleModifierNoOffset)
    bpy.utils.unregister_class(RemoveAllModifiersFromAnimation)

