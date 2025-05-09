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

# 骨架骨骼位置匹配
class MatchArmatureBones(bpy.types.Operator):
    bl_idname = "animation.match_armature_bones"
    bl_label = "骨架骨骼位置匹配"
    bl_description = "将主选的骨架中骨骼的位置和旋转复制给副选骨架中同名骨骼，并且已绑定的蒙皮物体会跟随变换"
    bl_options = {'REGISTER', 'UNDO'}
    
    apply_to_mesh: bpy.props.BoolProperty(
        name="应用到蒙皮网格",
        description="将骨骼变换应用到绑定的蒙皮网格上",
        default=True
    ) # type: ignore

    reset_modifiers: bpy.props.BoolProperty(
        name="重置修改器",
        description="重新应用骨架修改器以解决潜在的变形问题",
        default=True
    ) # type: ignore
    
    preserve_volume: bpy.props.BoolProperty(
        name="保持体积",
        description="在变形过程中保持网格体积",
        default=True
    ) # type: ignore
    
    def match_armatures(self, context, source_armature, target_armature):
        """
        将源骨架的骨骼姿势匹配到目标骨架
        
        Args:
            context: Blender上下文
            source_armature: 源骨架（姿势骨架）
            target_armature: 目标骨架（T-pose骨架）
            
        返回：
            int: 匹配的骨骼数量
        """
        # 清除选择
        bpy.ops.object.select_all(action='DESELECT')
        
        # 选择源骨架和目标骨架
        source_armature.select_set(True)
        target_armature.select_set(True)
        context.view_layer.objects.active = source_armature
        
        # 进入对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 保存源骨架中所有骨骼的姿势信息
        source_bones_data = {}
        for bone in source_armature.pose.bones:
            # 保存姿势骨骼的全局变换和局部变换
            source_bones_data[bone.name] = {
                'matrix_basis': bone.matrix_basis.copy(),  # 局部姿势变换
                'matrix': bone.matrix.copy(),  # 骨骼的完整变换
                'location': bone.location.copy(),  # 局部位置
                'rotation_quaternion': bone.rotation_quaternion.copy() if bone.rotation_mode == 'QUATERNION' else None,
                'rotation_euler': bone.rotation_euler.copy() if bone.rotation_mode in ['XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX'] else None,
                'rotation_axis_angle': bone.rotation_axis_angle[:] if bone.rotation_mode == 'AXIS_ANGLE' else None,
                'rotation_mode': bone.rotation_mode,
                'scale': bone.scale.copy(),
                'parent': bone.parent.name if bone.parent else None
            }
        
        # 保存与目标骨架关联的所有蒙皮物体
        skinned_objects = []
        if self.apply_to_mesh:
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for mod in obj.modifiers:
                        if mod.type == 'ARMATURE' and mod.object == target_armature:
                            skinned_objects.append(obj)
                            break
        
        # 如果需要应用到蒙皮网格，先应用蒙皮修改器
        applied_objects = []
        if self.apply_to_mesh and skinned_objects and self.reset_modifiers:
            for mesh_obj in skinned_objects:
                # 保存原始变换
                orig_mesh_matrix = mesh_obj.matrix_world.copy()
                orig_mesh_vertices = [v.co.copy() for v in mesh_obj.data.vertices]
                
                # 选择网格对象
                bpy.ops.object.select_all(action='DESELECT')
                mesh_obj.select_set(True)
                context.view_layer.objects.active = mesh_obj
                
                # 保存修改器状态
                armature_modifiers = []
                for mod in mesh_obj.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == target_armature:
                        armature_modifiers.append({
                            'name': mod.name,
                            'object': mod.object,
                            'vertex_group': mod.vertex_group if hasattr(mod, 'vertex_group') else None,
                            'use_deform_preserve_volume': mod.use_deform_preserve_volume if hasattr(mod, 'use_deform_preserve_volume') else False
                        })
                
                if armature_modifiers:
                    # 应用所有骨架修改器
                    for mod_data in armature_modifiers:
                        try:
                            bpy.ops.object.modifier_apply(modifier=mod_data['name'])
                        except Exception as e:
                            print(f"应用修改器时出错: {e}")
                    
                    applied_objects.append({
                        'object': mesh_obj,
                        'modifiers': armature_modifiers,
                        'original_matrix': orig_mesh_matrix,
                        'original_vertices': orig_mesh_vertices
                    })
        
        # 现在更新目标骨架的骨骼位置和姿势
        bpy.ops.object.select_all(action='DESELECT')
        target_armature.select_set(True)
        context.view_layer.objects.active = target_armature
        
        # 进入姿势模式以调整骨骼姿势
        bpy.ops.object.mode_set(mode='POSE')
        
        # 匹配骨骼姿势
        matched_bones = 0
        
        # 首先，将目标骨架的所有骨骼重置为静止姿势
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.transforms_clear()
        bpy.ops.pose.select_all(action='DESELECT')
        
        # 然后，应用源骨架的姿势到目标骨架
        for bone_name, source_data in source_bones_data.items():
            if bone_name in target_armature.pose.bones:
                pose_bone = target_armature.pose.bones[bone_name]
                
                # 设置旋转模式
                pose_bone.rotation_mode = source_data['rotation_mode']
                
                # 设置位置
                pose_bone.location = source_data['location']
                
                # 设置旋转
                if source_data['rotation_quaternion'] is not None:
                    pose_bone.rotation_quaternion = source_data['rotation_quaternion']
                elif source_data['rotation_euler'] is not None:
                    pose_bone.rotation_euler = source_data['rotation_euler']
                elif source_data['rotation_axis_angle'] is not None:
                    pose_bone.rotation_axis_angle = source_data['rotation_axis_angle']
                
                # 设置缩放
                pose_bone.scale = source_data['scale']
                
                matched_bones += 1
        
        # 更新视图
        bpy.context.view_layer.update()
        
        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 重新添加骨架修改器到应用过的网格对象
        if applied_objects:
            for obj_data in applied_objects:
                mesh_obj = obj_data['object']
                
                # 选择网格对象
                bpy.ops.object.select_all(action='DESELECT')
                mesh_obj.select_set(True)
                context.view_layer.objects.active = mesh_obj
                
                # 为每个之前的骨架修改器添加新的骨架修改器
                for mod_data in obj_data['modifiers']:
                    new_mod = mesh_obj.modifiers.new(name=mod_data['name'], type='ARMATURE')
                    new_mod.object = mod_data['object']
                    if mod_data['vertex_group']:
                        new_mod.vertex_group = mod_data['vertex_group']
                    if hasattr(new_mod, 'use_deform_preserve_volume'):
                        new_mod.use_deform_preserve_volume = self.preserve_volume
        
        return matched_bones
    
    def execute(self, context):
        # 获取UI中的设置
        self.apply_to_mesh = context.scene.match_armature_apply_to_mesh
        self.reset_modifiers = context.scene.match_armature_reset_modifiers
        self.preserve_volume = context.scene.match_armature_preserve_volume
        
        # 获取所有选中的骨架
        selected_armatures = [obj for obj in context.selected_objects if obj.type == 'ARMATURE']
        
        # 确保至少选中了两个骨架
        if len(selected_armatures) < 2:
            self.report({'ERROR'}, "请至少选择两个骨架，主骨架(姿势骨架)为活动对象，T-pose骨架也需要选中")
            return {'CANCELLED'}
        
        # 获取主选骨架（活动对象）和副选骨架
        active_armature = context.active_object
        if active_armature.type != 'ARMATURE':
            self.report({'ERROR'}, "活动对象必须是骨架")
            return {'CANCELLED'}
        
        # 从选中的骨架中过滤掉主选骨架，得到副选骨架
        target_armatures = [arm for arm in selected_armatures if arm != active_armature]
        
        if not target_armatures:
            self.report({'ERROR'}, "请确保选择了至少一个T-pose骨架")
            return {'CANCELLED'}
        
        # 保存原始模式和选择状态
        original_mode = context.mode
        original_active = context.active_object
        original_selected = [obj for obj in context.selected_objects]
        
        # 记录匹配的骨骼数量和骨架数量
        total_matched_bones = 0
        affected_armatures = 0
        
        # 处理每个目标骨架
        for target_armature in target_armatures:
            matched_bones = self.match_armatures(context, active_armature, target_armature)
            if matched_bones > 0:
                affected_armatures += 1
                total_matched_bones += matched_bones
        
        # 恢复原始选择
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selected:
            if obj:
                obj.select_set(True)
        if original_active:
            context.view_layer.objects.active = original_active
        
        # 尝试恢复原始模式
        try:
            if original_mode == 'EDIT_ARMATURE':
                bpy.ops.object.mode_set(mode='EDIT')
            elif original_mode == 'POSE':
                bpy.ops.object.mode_set(mode='POSE')
            elif original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode=original_mode)
        except Exception as e:
            print(f"恢复原始模式时出错: {e}")
        
        # 构建反馈信息
        message = f"已将 {total_matched_bones} 个骨骼姿势从主骨架匹配到 {affected_armatures} 个T-pose骨架"
        if self.apply_to_mesh:
            message += f"，并保持了蒙皮网格的绑定关系"
        
        self.report({'INFO'}, message)
        return {'FINISHED'}

# 重新实现的T-pose骨架应用与动画重新计算
class ApplyTPoseAndRecalculateAnimation(bpy.types.Operator):
    bl_idname = "animation.apply_tpose_recalculate"
    bl_label = "应用T-pose并重计算动画"
    bl_description = "将T-pose骨架的静止位置应用到目标骨架，并重新计算动画数据以保持动画效果"
    bl_options = {'REGISTER', 'UNDO'}
    
    preserve_volume: bpy.props.BoolProperty(
        name="保持体积",
        description="在变形过程中保持网格体积",
        default=True
    ) # type: ignore
    
    # 添加采样率属性，降低处理的关键帧数量
    keyframe_sample_rate: bpy.props.IntProperty(
        name="关键帧采样率",
        description="处理关键帧的采样率，较低的值处理更少的关键帧（更快但可能精度更低）",
        default=1,
        min=1,
        max=10
    ) # type: ignore
    
    max_keyframes: bpy.props.IntProperty(
        name="最大关键帧数",
        description="处理的最大关键帧数，设置为0表示处理所有关键帧",
        default=0,
        min=0
    ) # type: ignore
    
    process_only_selected_bones: bpy.props.BoolProperty(
        name="仅处理选中的骨骼",
        description="仅处理姿势模式下选中的骨骼",
        default=False
    ) # type: ignore
    
    # 添加显示详细信息的选项
    show_detailed_info: bpy.props.BoolProperty(
        name="显示详细信息",
        description="在控制台显示详细的处理信息和进度",
        default=True
    )
    
    # 添加批处理大小选项
    batch_size: bpy.props.IntProperty(
        name="批处理帧数",
        description="为大型动画设置批处理帧数，减少内存使用（0表示不分批）",
        default=0,
        min=0,
        max=1000
    ) # type: ignore
    
    memory_warning_threshold: bpy.props.FloatProperty(
        name="内存警告阈值",
        description="当估计内存使用超过此值（MB）时发出警告",
        default=1000.0,  # 1GB
        min=100.0,
        max=10000.0,
    ) # type: ignore
    
    def execute(self, context):
        # 打印起始信息
        if self.show_detailed_info:
            log_info("========== 开始执行 T-pose 应用与动画重计算 ==========")
        
        # 设置开始时间
        start_time = time.time()
        
        # 获取活动物体（应该是目标骨架）
        target_armature = context.active_object
        
        # 检查是否为骨架
        if not target_armature or target_armature.type != 'ARMATURE':
            error_msg = "请选择一个目标骨架作为活动对象"
            if self.show_detailed_info:
                log_info(f"错误: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        # 获取T-pose骨架
        tpose_armature = context.scene.tpose_reference_armature
        if not tpose_armature:
            error_msg = "请在设置中选择一个T-pose参考骨架"
            if self.show_detailed_info:
                log_info(f"错误: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        # 检查选择的是否为骨架
        if tpose_armature.type != 'ARMATURE':
            error_msg = "选择的参考对象不是骨架"
            if self.show_detailed_info:
                log_info(f"错误: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        # 确保目标骨架和T-pose骨架不是同一个
        if tpose_armature == target_armature:
            error_msg = "T-pose参考骨架和目标骨架不能是同一个"
            if self.show_detailed_info:
                log_info(f"错误: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        
        # 保存当前场景状态
        original_frame = context.scene.frame_current
        original_mode = target_armature.mode
        
        try:
            # 基于骨骼的新方法，更高效、更准确
            success = self.apply_tpose_efficient(context, tpose_armature, target_armature)
            
            # 恢复原始帧
            context.scene.frame_set(original_frame)
            
            # 强制垃圾回收
            gc.collect()
            
            # 计算用时
            elapsed_time = time.time() - start_time
            time_message = f"操作用时: {elapsed_time:.2f}秒"
            
            if self.show_detailed_info:
                log_info(f"操作完成! {time_message}")
                log_info("========== T-pose 应用与动画重计算结束 ==========")
            
            if success:
                self.report({'INFO'}, f"已成功将T-pose应用到目标骨架并重新计算了动画数据。{time_message}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"操作失败，请检查骨架和动画数据。{time_message}")
                return {'CANCELLED'}
                
        except Exception as e:
            error_msg = f"执行过程中出错: {str(e)}"
            if self.show_detailed_info:
                log_info(f"错误: {error_msg}")
                import traceback
                log_info(traceback.format_exc())
                log_info("========== T-pose 应用与动画重计算异常终止 ==========")
            
            # 尝试恢复原始模式
            try:
                if original_mode == 'EDIT':
                    bpy.ops.object.mode_set(mode='EDIT')
                elif original_mode == 'POSE':
                    bpy.ops.object.mode_set(mode='POSE')
                else:
                    bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
                
            # 恢复原始帧
            try:
                context.scene.frame_set(original_frame)
            except:
                pass
                
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}
        finally:
            # 确保在任何情况下都清理内存
            gc.collect()
            
    def apply_tpose_efficient(self, context, tpose_armature, target_armature):
        """
        使用更高效的方法将T-pose应用到目标骨架，同时保持动画效果不变
        """
        if self.show_detailed_info:
            log_info(f"开始处理 - 目标骨架: {target_armature.name}, T-pose骨架: {tpose_armature.name}")
            
        original_mode = target_armature.mode
            
        # 收集对象选择和活动状态以便稍后恢复
        orig_selected_objects = context.selected_objects.copy()
        orig_active_object = context.view_layer.objects.active
        
        # 检查目标骨架是否有动画
        has_animation = (target_armature.animation_data and 
                        target_armature.animation_data.action and 
                        len(target_armature.animation_data.action.fcurves) > 0)
        
        if self.show_detailed_info:
            if has_animation:
                log_info(f"目标骨架有动画数据")
            else:
                log_info(f"目标骨架没有动画数据")
        
        # 进入对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
            
        # 确保目标骨架被选中和活动
        target_armature.select_set(True)
        context.view_layer.objects.active = target_armature
        
        # 1. 获取选中的骨骼（如果需要）
        selected_bones = []
        if self.process_only_selected_bones:
            bpy.ops.object.mode_set(mode='POSE')
            selected_bones = [bone.name for bone in target_armature.pose.bones if bone.bone.select]
            if self.show_detailed_info:
                log_info(f"已选中 {len(selected_bones)} 个骨骼")
        
        # 2. 收集T-pose骨架的静止姿势信息
        tpose_rest_data = {}
        
        # 选择T-pose骨架并进入编辑模式
        bpy.ops.object.select_all(action='DESELECT')
        tpose_armature.select_set(True)
        context.view_layer.objects.active = tpose_armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 收集所有骨骼的静止姿势
        for bone in tpose_armature.data.edit_bones:
            tpose_rest_data[bone.name] = {
                'head': bone.head.copy(),
                'tail': bone.tail.copy(),
                'roll': bone.roll,
                'matrix': bone.matrix.copy()
            }
            
        if self.show_detailed_info:
            log_info(f"从T-pose骨架收集了 {len(tpose_rest_data)} 个骨骼的静止姿势数据")
        
        # 3. 收集目标骨架的动画和静止姿势数据
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        target_armature.select_set(True)
        context.view_layer.objects.active = target_armature
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 收集原始的静止姿势
        target_rest_data = {}
        matched_bones = []
        
        for bone in target_armature.data.edit_bones:
            # 如果指定了只处理选中的骨骼，则跳过未选中的
            if self.process_only_selected_bones and bone.name not in selected_bones:
                continue
                
            # 仅处理在T-pose中存在的骨骼
            if bone.name in tpose_rest_data:
                target_rest_data[bone.name] = {
                    'head': bone.head.copy(),
                    'tail': bone.tail.copy(),
                    'roll': bone.roll,
                    'matrix': bone.matrix.copy()
                }
                matched_bones.append(bone.name)
        
        if self.show_detailed_info:
            log_info(f"找到 {len(matched_bones)} 个匹配的骨骼")
            
        # 如果没有匹配的骨骼，则退出
        if not matched_bones:
            if self.show_detailed_info:
                log_info("没有找到匹配的骨骼，操作取消")
            self.report({'ERROR'}, "没有找到匹配的骨骼")
            return False
            
        # 4. 如果有动画，收集帧范围和关键帧
        if has_animation:
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 获取动作
            action = target_armature.animation_data.action
            
            # 获取帧范围
            frame_range = self.get_action_frame_range(action)
            if not frame_range:
                if self.show_detailed_info:
                    log_info("未找到有效的关键帧范围")
                self.report({'ERROR'}, "未找到有效的关键帧范围")
                return False
                
            start_frame, end_frame = frame_range
            
            if self.show_detailed_info:
                log_info(f"动画帧范围: {start_frame} - {end_frame}")
                
            # 如果设置了最大关键帧数
            if self.max_keyframes > 0:
                total_frames = end_frame - start_frame + 1
                if total_frames > self.max_keyframes:
                    # 重新计算采样率
                    new_sample_rate = max(1, int(total_frames / self.max_keyframes))
                    old_rate = self.keyframe_sample_rate
                    self.keyframe_sample_rate = max(self.keyframe_sample_rate, new_sample_rate)
                    if self.show_detailed_info and old_rate != self.keyframe_sample_rate:
                        log_info(f"由于帧数过多，采样率已从 {old_rate} 调整为 {self.keyframe_sample_rate}")
            
            # 估计内存使用量
            frame_count = (end_frame - start_frame) // self.keyframe_sample_rate + 1
            estimated_memory = estimate_memory_usage(len(matched_bones), frame_count)
            
            if self.show_detailed_info:
                log_info(f"估计内存使用量: {estimated_memory:.2f}MB")
            
            # 如果估计内存使用量超过阈值，警告用户
            if estimated_memory > self.memory_warning_threshold:
                warning_msg = f"警告：此操作可能使用大量内存（约 {estimated_memory:.2f}MB）。"
                warning_msg += "考虑增加关键帧采样率、降低最大帧数或使用批处理模式。"
                log_info(warning_msg)
                self.report({'WARNING'}, warning_msg)
        
        # 5. 应用T-pose的静止姿势到目标骨架
        bpy.ops.object.mode_set(mode='EDIT')
        
        if self.show_detailed_info:
            log_info("开始应用T-pose静止姿势到目标骨架...")
            
        # 记录修改了多少骨骼
        updated_bones = 0
        
        for bone_name in matched_bones:
            if bone_name in target_armature.data.edit_bones and bone_name in tpose_rest_data:
                # 获取目标骨骼和T-pose数据
                edit_bone = target_armature.data.edit_bones[bone_name]
                tpose_data = tpose_rest_data[bone_name]
                
                # 应用T-pose的位置和方向
                edit_bone.head = tpose_data['head']
                edit_bone.tail = tpose_data['tail']
                edit_bone.roll = tpose_data['roll']
                updated_bones += 1
                
        if self.show_detailed_info:
            log_info(f"已更新 {updated_bones} 个骨骼的静止姿势")
            
        # 6. 如果有动画，重新计算帧位置
        if has_animation:
            bpy.ops.object.mode_set(mode='POSE')
            
            if self.show_detailed_info:
                log_info("开始重新计算动画数据...")
                
            # 找到与骨骼相关的所有曲线
            bone_fcurves = {}
            for matched_bone in matched_bones:
                # 初始化该骨骼的fcurve列表
                bone_fcurves[matched_bone] = []
                
            # 收集与匹配骨骼相关的所有fcurves
            for fcurve in action.fcurves:
                for bone_name in matched_bones:
                    if f'pose.bones["{bone_name}"]' in fcurve.data_path:
                        bone_fcurves[bone_name].append(fcurve)
                        break
                        
            # 计算需要处理的总帧数
            frame_count = (end_frame - start_frame) // self.keyframe_sample_rate + 1
            
            # 确定是否需要批处理
            use_batching = self.batch_size > 0 and frame_count > self.batch_size
            
            if use_batching and self.show_detailed_info:
                log_info(f"启用批处理模式，每批处理 {self.batch_size} 帧")
                batch_count = (frame_count + self.batch_size - 1) // self.batch_size  # 向上取整
                log_info(f"总共需要处理 {batch_count} 批")
            
            # 如果使用批处理，计算批次
            if use_batching:
                batch_ranges = []
                current_start = start_frame
                while current_start <= end_frame:
                    current_end = min(current_start + (self.batch_size * self.keyframe_sample_rate - 1), end_frame)
                    batch_ranges.append((current_start, current_end))
                    current_start = current_end + self.keyframe_sample_rate
            else:
                # 不使用批处理，一次处理所有帧
                batch_ranges = [(start_frame, end_frame)]
                
            # 处理每一批次
            batch_index = 0
            for batch_start, batch_end in batch_ranges:
                batch_index += 1
                
                if use_batching and self.show_detailed_info:
                    log_info(f"开始处理第 {batch_index} 批 (帧 {batch_start}-{batch_end})")
                
                # 为当前批次创建变换矩阵字典
                transform_matrices = {bone_name: {} for bone_name in matched_bones}
                
                # 创建进度条
                wm = context.window_manager
                batch_frame_count = (batch_end - batch_start) // self.keyframe_sample_rate + 1
                wm.progress_begin(0, batch_frame_count)
                
                # 记录处理的帧数
                processed_frames = 0
                
                if self.show_detailed_info:
                    log_info(f"开始处理批次中的 {batch_frame_count} 帧数据...")
                
                # 第一阶段：收集变换矩阵
                for frame in range(batch_start, batch_end + 1, self.keyframe_sample_rate):
                    # 更新进度条
                    wm.progress_update(processed_frames)
                    
                    if self.show_detailed_info and processed_frames % 10 == 0:
                        log_info(f"正在计算帧 {frame} 的变换矩阵 (进度: {processed_frames}/{batch_frame_count})")
                    
                    # 设置当前帧
                    context.scene.frame_set(frame)
                    
                    # 对每个骨骼计算变换矩阵
                    for bone_name in matched_bones:
                        # 如果该骨骼没有fcurves，跳过
                        if not bone_fcurves[bone_name]:
                            continue
                            
                        pose_bone = target_armature.pose.bones[bone_name]
                        
                        # 计算从静止到当前姿势的变换矩阵
                        if bone_name in target_rest_data:
                            # 获取原始静止矩阵的逆
                            rest_matrix_inv = target_rest_data[bone_name]['matrix'].inverted()
                            
                            # 获取当前的姿势矩阵(在编辑模式中的矩阵)
                            pose_matrix = pose_bone.matrix.copy()
                            
                            # 计算变换矩阵
                            transform_matrix = rest_matrix_inv @ pose_matrix
                            
                            # 存储变换矩阵
                            transform_matrices[bone_name][frame] = transform_matrix
                    
                    processed_frames += 1
                
                # 结束第一阶段进度条
                wm.progress_end()
                
                if self.show_detailed_info:
                    log_info(f"成功计算了批次中 {processed_frames} 帧的变换矩阵")
                
                # 重置帧计数器
                processed_frames = 0
                
                # 重新开始进度条
                wm.progress_begin(0, batch_frame_count)
                
                if self.show_detailed_info:
                    log_info("开始应用变换矩阵到骨骼...")
                
                # 第二阶段：应用变换矩阵
                for frame in range(batch_start, batch_end + 1, self.keyframe_sample_rate):
                    # 更新进度条
                    wm.progress_update(processed_frames)
                    
                    if self.show_detailed_info and processed_frames % 10 == 0:
                        log_info(f"正在应用帧 {frame} 的变换矩阵 (进度: {processed_frames}/{batch_frame_count})")
                    
                    # 设置当前帧
                    context.scene.frame_set(frame)
                    
                    # 对每个骨骼应用变换矩阵
                    for bone_name in matched_bones:
                        # 如果该骨骼没有此帧的变换矩阵，跳过
                        if bone_name not in transform_matrices or frame not in transform_matrices[bone_name]:
                            continue
                            
                        pose_bone = target_armature.pose.bones[bone_name]
                        
                        # 获取变换矩阵
                        transform_matrix = transform_matrices[bone_name][frame]
                        
                        # 获取新的静止矩阵
                        if bone_name in tpose_rest_data:
                            new_rest_matrix = tpose_rest_data[bone_name]['matrix']
                            
                            # 计算新的姿势矩阵
                            new_pose_matrix = new_rest_matrix @ transform_matrix
                            
                            # 从新的姿势矩阵中提取位置、旋转和缩放
                            loc, rot, scale = new_pose_matrix.decompose()
                            
                            # 保存原始旋转模式
                            original_rotation_mode = pose_bone.rotation_mode
                            
                            # 设置新的变换
                            pose_bone.location = loc
                            
                            # 旋转需要根据旋转模式处理
                            if original_rotation_mode == 'QUATERNION':
                                pose_bone.rotation_quaternion = rot
                            else:
                                # 转换四元数到欧拉角
                                pose_bone.rotation_mode = 'QUATERNION'
                                pose_bone.rotation_quaternion = rot
                                pose_bone.rotation_mode = original_rotation_mode
                            
                            pose_bone.scale = scale
                            
                            # 插入关键帧
                            pose_bone.keyframe_insert(data_path="location", frame=frame)
                            
                            if original_rotation_mode == 'QUATERNION':
                                pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame)
                            else:
                                pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)
                            
                            pose_bone.keyframe_insert(data_path="scale", frame=frame)
                    
                    processed_frames += 1
                
                # 结束第二阶段进度条
                wm.progress_end()
                
                if self.show_detailed_info:
                    log_info(f"成功应用了批次中 {processed_frames} 帧的变换矩阵")
                
                # 清理当前批次的矩阵数据，释放内存
                del transform_matrices
                gc.collect()
                
                if use_batching and batch_index < len(batch_ranges) and self.show_detailed_info:
                    log_info(f"第 {batch_index} 批处理完成，共 {len(batch_ranges)} 批")
                
        # 恢复原始模式
        try:
            if original_mode == 'EDIT':
                bpy.ops.object.mode_set(mode='EDIT')
            elif original_mode == 'POSE':
                bpy.ops.object.mode_set(mode='POSE')
            else:
                bpy.ops.object.mode_set(mode='OBJECT')
        except Exception as e:
            if self.show_detailed_info:
                log_info(f"恢复原始模式时出错: {e}")
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 恢复原始选择
        bpy.ops.object.select_all(action='DESELECT')
        for obj in orig_selected_objects:
            if obj:
                obj.select_set(True)
        if orig_active_object:
            context.view_layer.objects.active = orig_active_object
            
        # 清理引用变量以释放内存
        del selected_bones
        del tpose_rest_data
        del target_rest_data
        del matched_bones
        if has_animation:
            del bone_fcurves
        
        # 强制进行垃圾回收
        gc.collect()
            
        if self.show_detailed_info:
            log_info("T-pose应用完成")
            
        return True
            
    def get_action_frame_range(self, action):
        """获取动作的帧范围"""
        if not action.fcurves:
            return None
            
        min_frame = float('inf')
        max_frame = float('-inf')
        
        for fcurve in action.fcurves:
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0]
                min_frame = min(min_frame, frame)
                max_frame = max(max_frame, frame)
        
        if min_frame == float('inf') or max_frame == float('-inf'):
            return None
            
        return (int(min_frame), int(max_frame))

def register():
    bpy.utils.register_class(ClearScaleAnimation)
    bpy.utils.register_class(ClearAllAnimation)
    bpy.utils.register_class(ClearLocationAnimation)
    bpy.utils.register_class(ClearRotationAnimation)
    bpy.utils.register_class(MatchArmatureBones)
    bpy.utils.register_class(ApplyTPoseAndRecalculateAnimation)
    
    # 添加属性用于存储T-pose参考骨架
    bpy.types.Scene.tpose_reference_armature = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="T-pose参考骨架",
        description="选择一个标准T-pose骨架作为参考",
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

def unregister():
    bpy.utils.unregister_class(ClearScaleAnimation)
    bpy.utils.unregister_class(ClearAllAnimation)
    bpy.utils.unregister_class(ClearLocationAnimation)
    bpy.utils.unregister_class(ClearRotationAnimation)
    bpy.utils.unregister_class(MatchArmatureBones)
    bpy.utils.unregister_class(ApplyTPoseAndRecalculateAnimation)
    
    # 删除属性
    del bpy.types.Scene.tpose_reference_armature


"""
动画骨架工具性能优化说明：

1. 批处理系统（Batch Processing）
   - 为大型动画添加了批处理功能，可以设置每批处理的帧数
   - 每批次处理完成后会释放内存，避免内存占用过大导致Blender卡死
   - 适合处理非常长的动画或包含大量骨骼的复杂骨架

2. 内存使用估计（Memory Usage Estimation）
   - 添加了内存使用量估计功能，可以提前预测操作会使用多少内存
   - 当预测内存使用量超过用户设置的阈值时，会发出警告
   - 帮助用户选择合适的参数，避免因内存不足导致的崩溃

3. 内存管理优化（Memory Management）
   - 使用Python的垃圾回收机制，主动释放不再使用的临时数据
   - 在操作完成后清理所有引用变量，减少内存占用
   - 在异常情况下也能确保清理内存

使用建议：
- 对于小型动画（少于1000帧），可以使用默认设置
- 对于大型动画，建议：
  1. 增加关键帧采样率（如设置为2-5）
  2. 启用批处理，设置批处理帧数为100-200
  3. 仅处理需要修改的骨骼
- 如果操作仍然很慢，可以尝试限制最大关键帧数
""" 