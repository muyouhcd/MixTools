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
                # 缩放曲线的数据路径通常包含 "scale"
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

class TransferBoneAnimation(bpy.types.Operator):
    bl_idname = "animation.transfer_bone_animation"
    bl_label = "转移骨骼动画"
    bl_description = "将源骨架的动画转移到目标骨架，基于骨骼端点位置计算"
    bl_options = {'REGISTER', 'UNDO'}
    
    # 添加采样率属性
    keyframe_sample_rate: bpy.props.IntProperty(
        name="关键帧采样率",
        description="处理关键帧的采样率，较低的值处理更少的关键帧（更快但可能精度更低）",
        default=1,
        min=1,
        max=10
    ) # type: ignore
    
    # 添加批处理大小选项
    batch_size: bpy.props.IntProperty(
        name="批处理帧数",
        description="为大型动画设置批处理帧数，减少内存使用（0表示不分批）",
        default=0,
        min=0,
        max=1000
    ) # type: ignore
    
    # 添加显示详细信息的选项
    show_detailed_info: bpy.props.BoolProperty(
        name="显示详细信息",
        description="在控制台显示详细的处理信息和进度",
        default=True
    )
    
    def execute(self, context):
        # 从场景属性中获取源骨架和目标骨架
        source_armature = context.scene.source_armature
        target_armature = context.scene.target_armature
        
        # 检查是否选择了骨架
        if not source_armature:
            self.report({'ERROR'}, "请选择源骨架")
            return {'CANCELLED'}
            
        if not target_armature:
            self.report({'ERROR'}, "请选择目标骨架")
            return {'CANCELLED'}
        
        # 检查源骨架是否有动画
        if not source_armature.animation_data or not source_armature.animation_data.action:
            self.report({'ERROR'}, "源骨架没有动画数据")
            return {'CANCELLED'}
        
        # 获取动画数据
        action = source_armature.animation_data.action
        
        # 获取帧范围
        frame_range = self.get_action_frame_range(action)
        if not frame_range:
            self.report({'ERROR'}, "未找到有效的关键帧范围")
            return {'CANCELLED'}
        
        start_frame, end_frame = frame_range
        
        # 处理动画转移
        success = self.transfer_animation(context, source_armature, target_armature, action, start_frame, end_frame)
        if not success:
            self.report({'ERROR'}, f"处理骨架 {target_armature.name} 时出错")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"已成功将动画从 {source_armature.name} 转移到 {target_armature.name}")
        return {'FINISHED'}
    
    def get_action_frame_range(self, action):
        """获取动作的帧范围"""
        if not action.fcurves:
            return None
            
        start_frame = float('inf')
        end_frame = float('-inf')
        
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                start_frame = min(start_frame, keyframe.co.x)
                end_frame = max(end_frame, keyframe.co.x)
        
        if start_frame == float('inf') or end_frame == float('-inf'):
            return None
            
        return (int(start_frame), int(end_frame))
    
    def transfer_animation(self, context, source_armature, target_armature, action, start_frame, end_frame):
        """转移动画数据"""
        try:
            # 获取匹配的骨骼对
            matching_bones = self.get_matching_bones(source_armature, target_armature)
            if not matching_bones:
                self.report({'WARNING'}, "未找到匹配的骨骼")
                return False
            
            # 创建新的动作
            new_action = bpy.data.actions.new(name=f"{target_armature.name}_transferred")
            target_armature.animation_data_create()
            target_armature.animation_data.action = new_action
            
            # 设置帧范围
            frame_count = end_frame - start_frame + 1
            processed_frames = 0
            
            # 获取源骨架和目标骨架的缩放因子
            source_scale = source_armature.scale
            target_scale = target_armature.scale
            
            # 计算缩放比例（分别计算每个分量）
            scale_ratio = [
                target_scale[0] / source_scale[0] if source_scale[0] != 0 else 1.0,
                target_scale[1] / source_scale[1] if source_scale[1] != 0 else 1.0,
                target_scale[2] / source_scale[2] if source_scale[2] != 0 else 1.0
            ]
            
            # 处理每一帧
            for frame in range(start_frame, end_frame + 1, self.keyframe_sample_rate):
                context.scene.frame_set(frame)
                
                # 处理每个匹配的骨骼对
                for source_bone, target_bone in matching_bones:
                    # 获取源骨骼的矩阵
                    source_matrix = source_bone.matrix.copy()
                    
                    # 应用缩放比例
                    source_matrix.col[3][0] *= scale_ratio[0]  # X scale
                    source_matrix.col[3][1] *= scale_ratio[1]  # Y scale
                    source_matrix.col[3][2] *= scale_ratio[2]  # Z scale
                    
                    # 设置目标骨骼的矩阵
                    target_bone.matrix = source_matrix
                    
                    # 插入关键帧
                    target_bone.keyframe_insert(data_path="location", frame=frame)
                    target_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                
                processed_frames += 1
                if self.show_detailed_info and processed_frames % 10 == 0:
                    print(f"已处理 {processed_frames}/{frame_count} 帧")
            
            return True
            
        except Exception as e:
            self.report({'ERROR'}, f"处理过程中出错: {str(e)}")
            return False
    
    def get_matching_bones(self, source_armature, target_armature):
        """获取两个骨架中名称匹配的骨骼对"""
        matching_bones = []
        source_bones = {bone.name: bone for bone in source_armature.pose.bones}
        target_bones = {bone.name: bone for bone in target_armature.pose.bones}
        
        for bone_name in source_bones:
            if bone_name in target_bones:
                matching_bones.append((source_bones[bone_name], target_bones[bone_name]))
        
        return matching_bones


def register():
    bpy.utils.register_class(ClearScaleAnimation)
    bpy.utils.register_class(ClearAllAnimation)
    bpy.utils.register_class(ClearLocationAnimation)
    bpy.utils.register_class(ClearRotationAnimation)
    bpy.utils.register_class(TransferBoneAnimation)
    
    # 添加属性用于存储源骨架和目标骨架
    bpy.types.Scene.source_armature = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="源骨架",
        description="选择带动画的源骨架",
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    
    bpy.types.Scene.target_armature = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="目标骨架",
        description="选择要接收动画的目标骨架",
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )
    
    # 添加操作符的属性到场景
    op = TransferBoneAnimation
    for prop_name, prop in op.__annotations__.items():
        # 检查是否是Blender属性类型
        if hasattr(prop, 'bl_rna'):
            setattr(bpy.types.Scene, f"transfer_bone_animation_{prop_name}", prop)

def unregister():
    bpy.utils.unregister_class(ClearScaleAnimation)
    bpy.utils.unregister_class(ClearAllAnimation)
    bpy.utils.unregister_class(ClearLocationAnimation)
    bpy.utils.unregister_class(ClearRotationAnimation)
    bpy.utils.unregister_class(TransferBoneAnimation)
    
    # 删除属性
    del bpy.types.Scene.source_armature
    del bpy.types.Scene.target_armature
    
    # 删除操作符的属性
    op = TransferBoneAnimation
    for prop_name in op.__annotations__:
        if hasattr(bpy.types.Scene, f"transfer_bone_animation_{prop_name}"):
            delattr(bpy.types.Scene, f"transfer_bone_animation_{prop_name}")

