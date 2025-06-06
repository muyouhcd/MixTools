import bpy
import mathutils

class BoneConverter:
    @staticmethod
    def convert_empties_to_bones(context):
        # 获取选中的物体
        selected_objects = context.selected_objects
        
        if not selected_objects:
            return {'CANCELLED'}, "请先选择要转换的骨架"
            
        # 检查是否有选中的骨架
        active_armature = None
        for obj in selected_objects:
            if obj.type == 'ARMATURE':
                active_armature = obj
                break
                
        if not active_armature:
            return {'CANCELLED'}, "请先选择一个骨架"
            
        # 获取骨架下的所有空物体
        empty_objects = []
        def collect_empties(obj):
            for child in obj.children:
                if child.type == 'EMPTY':
                    empty_objects.append(child)
                    
        
        collect_empties(active_armature)
        
        print(f"找到 {len(empty_objects)} 个可转换的空物体:")
        for empty in empty_objects:
            print(f"- {empty.name}")
            
        if not empty_objects:
            return {'CANCELLED'}, "骨架下没有空物体"
            
        # 存储空物体的初始状态
        empty_initial_states = {}
        for empty in empty_objects:
            # 保存初始状态
            empty_initial_states[empty.name] = {
                'matrix': empty.matrix_world.copy(),
                'location': empty.location.copy(),
                'rotation_euler': empty.rotation_euler.copy(),
                'scale': empty.scale.copy()
            }
            
            # 重置空物体到初始状态
            empty.location = (0, 0, 0)
            empty.rotation_euler = (0, 0, 0)
            empty.scale = (1, 1, 1)
            
        # 进入编辑模式
        bpy.ops.object.mode_set(mode='EDIT')
        
        # 存储已处理的空物体
        processed_empties = set()
        
        def process_empty(empty_obj, parent_bone=None):
            if empty_obj in processed_empties:
                return
                
            processed_empties.add(empty_obj)
            print(f"正在处理空物体: {empty_obj.name}")
            
            # 创建新骨骼
            bone = active_armature.data.edit_bones.new(empty_obj.name)
            
            # 使用初始状态的矩阵来设置骨骼位置
            initial_matrix = empty_initial_states[empty_obj.name]['matrix']
            bone.head = initial_matrix.translation
            
            # 如果有父级骨骼，设置父子关系
            if parent_bone:
                bone.parent = parent_bone
                print(f"设置 {bone.name} 的父级为 {parent_bone.name}")
                
            # 处理子级空物体
            for child in empty_obj.children:
                if child.type == 'EMPTY':
                    # 使用子级空物体的初始状态矩阵来设置骨骼尾部
                    child_matrix = empty_initial_states[child.name]['matrix']
                    bone.tail = child_matrix.translation
                    print(f"设置 {bone.name} 的尾部位置为子级 {child.name} 的位置")
                    # 递归处理子级空物体
                    process_empty(child, bone)
                    
            # 如果没有子级，设置一个默认的尾部位置
            if not empty_obj.children:
                # 在Z轴方向上延伸一段距离
                bone.tail = bone.head + mathutils.Vector((0, 0, 0.1))
                print(f"设置 {bone.name} 的默认尾部位置")
        
        # 处理所有空物体
        for obj in empty_objects:
            process_empty(obj)
        
        # 退出编辑模式
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # 恢复空物体的原始状态
        for empty in empty_objects:
            initial_state = empty_initial_states[empty.name]
            empty.matrix_world = initial_state['matrix']
        
        # 复制动画数据
        for empty in empty_objects:
            if empty.animation_data and empty.animation_data.action:
                # 获取对应的骨骼
                bone = active_armature.pose.bones.get(empty.name)
                if bone:
                    # 确保骨架有动画数据
                    if not active_armature.animation_data:
                        active_armature.animation_data_create()
                    
                    # 获取或创建动作
                    action = active_armature.animation_data.action
                    if not action:
                        action = bpy.data.actions.new(name=f"{active_armature.name}_Action")
                        active_armature.animation_data.action = action
                    
                    # 获取空物体的动作
                    empty_action = empty.animation_data.action
                    
                    # 复制所有动画数据
                    for fcurve in empty_action.fcurves:
                        # 创建新的F曲线
                        new_fcurve = action.fcurves.new(
                            data_path=f"pose.bones[\"{bone.name}\"].{fcurve.data_path}",
                            index=fcurve.array_index
                        )
                        
                        # 复制关键帧
                        for keyframe in fcurve.keyframe_points:
                            new_keyframe = new_fcurve.keyframe_points.insert(
                                keyframe.co.x,
                                keyframe.co.y
                            )
                            # 复制插值设置
                            new_keyframe.interpolation = keyframe.interpolation
                            new_keyframe.easing = keyframe.easing
                            new_keyframe.handle_left_type = keyframe.handle_left_type
                            new_keyframe.handle_right_type = keyframe.handle_right_type
                            new_keyframe.handle_left = keyframe.handle_left.copy()
                            new_keyframe.handle_right = keyframe.handle_right.copy()
                        
                        # 复制F曲线设置
                        new_fcurve.extrapolation = fcurve.extrapolation
                        
                        # 复制修饰器
                        for modifier in fcurve.modifiers:
                            new_modifier = new_fcurve.modifiers.new(type=modifier.type)
                            # 复制修饰器属性
                            for prop in modifier.bl_rna.properties:
                                if prop.identifier not in ['type']:
                                    try:
                                        setattr(new_modifier, prop.identifier, getattr(modifier, prop.identifier))
                                    except:
                                        print(f"无法复制修饰器属性: {prop.identifier}")
        
        # 选择骨架
        bpy.ops.object.select_all(action='DESELECT')
        active_armature.select_set(True)
        context.view_layer.objects.active = active_armature
        
        return {'FINISHED'}, f"成功将 {len(processed_empties)} 个空物体转换为骨骼，并复制了动画数据"

    @staticmethod
    def copy_bone_parameters(context, source_armature, target_armature):
        if not source_armature or not target_armature:
            return {'CANCELLED'}, "请选择源骨架和目标骨架"
            
        if source_armature.type != 'ARMATURE' or target_armature.type != 'ARMATURE':
            return {'CANCELLED'}, "请确保选择的是骨架对象"
            
        # 存储当前模式
        original_mode = context.active_object.mode if context.active_object else 'OBJECT'
        
        try:
            # 保存原始变换
            source_matrix = source_armature.matrix_world.copy()
            target_matrix = target_armature.matrix_world.copy()
            
            # 重置骨架变换
            source_armature.matrix_world = mathutils.Matrix.Identity(4)
            target_armature.matrix_world = mathutils.Matrix.Identity(4)
            
            # 确保两个骨架都在编辑模式下
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            # 选择源骨架
            source_armature.select_set(True)
            context.view_layer.objects.active = source_armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 获取源骨架的骨骼列表
            source_bones = source_armature.data.edit_bones
            print(f"\n源骨架骨骼列表:")
            source_bone_dict = {}
            for bone in source_bones:
                source_bone_dict[bone.name] = bone
                print(f"- {bone.name}")
            
            # 切换到目标骨架
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            target_armature.select_set(True)
            context.view_layer.objects.active = target_armature
            bpy.ops.object.mode_set(mode='EDIT')
            
            # 获取目标骨架的骨骼列表
            target_bones = target_armature.data.edit_bones
            print(f"\n目标骨架骨骼列表:")
            target_bone_dict = {}
            for bone in target_bones:
                target_bone_dict[bone.name] = bone
                print(f"- {bone.name}")
            
            # 找出匹配的骨骼名称
            matching_bones = set(source_bone_dict.keys()).intersection(set(target_bone_dict.keys()))
            print(f"\n找到的匹配骨骼:")
            for bone_name in matching_bones:
                print(f"- {bone_name}")
            
            if not matching_bones:
                return {'CANCELLED'}, "没有找到匹配的骨骼，请确保两个骨架中有相同名称的骨骼"
            
            # 记录处理的骨骼数量
            processed_bones = 0
            matched_bones = []
            unmatched_bones = []
            
            # 处理每个匹配的骨骼
            for bone_name in matching_bones:
                try:
                    source_bone = source_bone_dict[bone_name]
                    target_bone = target_bone_dict[bone_name]
                    
                    print(f"处理骨骼: {bone_name}")
                    
                    # 保存目标骨骼的原始父级关系
                    original_parent = target_bone.parent
                    
                    # 获取源骨骼的世界空间位置
                    source_head_world = source_matrix @ source_bone.head
                    source_tail_world = source_matrix @ source_bone.tail
                    
                    # 计算源骨骼的方向向量和长度
                    source_direction = (source_tail_world - source_head_world).normalized()
                    source_length = (source_tail_world - source_head_world).length
                    
                    # 转换到目标骨架的局部空间
                    target_head_local = target_matrix.inverted() @ source_head_world
                    
                    # 使用源骨骼的方向和长度来设置尾部位置
                    target_tail_local = target_head_local + (source_direction * source_length)
                    
                    # 只设置目标骨骼的端点位置
                    target_bone.head = target_head_local
                    target_bone.tail = target_tail_local
                    
                    # 确保父级关系保持不变
                    if target_bone.parent != original_parent:
                        target_bone.parent = original_parent
                    
                    processed_bones += 1
                    matched_bones.append(bone_name)
                    
                except Exception as e:
                    print(f"复制骨骼 {bone_name} 时出错: {str(e)}")
                    unmatched_bones.append(bone_name)
            
            # 恢复原始模式
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # 恢复原始变换
            source_armature.matrix_world = source_matrix
            target_armature.matrix_world = target_matrix
            
            # 打印详细的匹配结果
            print("\n匹配结果统计:")
            print(f"成功匹配并复制的骨骼数量: {len(matched_bones)}")
            print(f"未匹配的骨骼数量: {len(unmatched_bones)}")
            if unmatched_bones:
                print("\n未匹配的骨骼列表:")
                for bone_name in unmatched_bones:
                    print(f"- {bone_name}")
            
            if processed_bones == 0:
                return {'CANCELLED'}, "没有找到匹配的骨骼，请确保两个骨架中有相同名称的骨骼"
                
            return {'FINISHED'}, f"成功对齐了 {processed_bones} 个骨骼的端点"
            
        except Exception as e:
            print(f"发生错误: {str(e)}")
            # 确保恢复到原始模式
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
                # 恢复原始变换
                source_armature.matrix_world = source_matrix
                target_armature.matrix_world = target_matrix
            except:
                pass
            return {'CANCELLED'}, f"发生错误: {str(e)}"

class BONE_CONVERTER_OT_Convert(bpy.types.Operator):
    bl_idname = "object.convert_empties_to_bones"
    bl_label = "转换空物体为骨骼"
    bl_description = "将选中骨架下的所有空物体转换为骨骼，并保持动画数据"
    
    def execute(self, context):
        result, message = BoneConverter.convert_empties_to_bones(context)
        if result == {'CANCELLED'}:
            self.report({'ERROR'}, message)
        else:
            self.report({'INFO'}, message)
        return result

class BONE_CONVERTER_OT_CopyParameters(bpy.types.Operator):
    bl_idname = "object.copy_bone_parameters"
    bl_label = "复制骨骼参数"
    bl_description = "将源骨架中的骨骼参数复制到目标骨架中的同名骨骼"
    
    def execute(self, context):
        # 获取面板中选择的骨架
        source_armature = context.scene.source_armature
        target_armature = context.scene.target_armature
        
        if not source_armature or not target_armature:
            self.report({'ERROR'}, "请在面板中选择源骨架和目标骨架")
            return {'CANCELLED'}
            
        if source_armature.type != 'ARMATURE' or target_armature.type != 'ARMATURE':
            self.report({'ERROR'}, "请确保选择的是骨架对象")
            return {'CANCELLED'}
            
        result, message = BoneConverter.copy_bone_parameters(context, source_armature, target_armature)
        self.report({'INFO'}, message)
        return result

def register():
    bpy.utils.register_class(BONE_CONVERTER_OT_Convert)
    bpy.utils.register_class(BONE_CONVERTER_OT_CopyParameters)

def unregister():
    bpy.utils.unregister_class(BONE_CONVERTER_OT_Convert)
    bpy.utils.unregister_class(BONE_CONVERTER_OT_CopyParameters)
