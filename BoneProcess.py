import bpy


class ResetBonePosition(bpy.types.Operator):
    bl_idname = "object.reset_bone_position"
    bl_label = "重置骨骼端点位置（连接）"

    def execute(self, context):
        def align_bone_tail_to_child_head(armature, bone):
            """Align bone's tail to the head of its first child."""
            if bone.children:
                # Align bone's tail to the head of its first child
                bone.tail = bone.children[0].head

        def process_bone_hierarchy(armature, bone):
            """Recursively process the bone hierarchy for alignment."""
            align_bone_tail_to_child_head(armature, bone)
            
            # Recursively handle all children
            for child in bone.children:
                process_bone_hierarchy(armature, child)


        # Ensure we are in edit mode and have an armature selected
        if bpy.context.mode != 'EDIT_ARMATURE':
            bpy.ops.object.mode_set(mode='EDIT')
        
        armature = bpy.context.active_object
        selected_bones = bpy.context.selected_bones
        
        # Process each selected bone
        for bone in selected_bones:
            process_bone_hierarchy(armature, bone)


        return {'FINISHED'}
    

class ConnectBone(bpy.types.Operator):
    bl_idname = "object.connect_bone"
    bl_label = "重置骨骼端点位置（连接）"

    def execute(self, context):
        def connect_bones_recursive(armature, bone_name):
            bones = armature.data.edit_bones
            current_bone = bones.get(bone_name)
            
            if current_bone and current_bone.parent:
                # 检查子骨骼的起点是否与父骨骼的终点重合
                if (current_bone.head - current_bone.parent.tail).length < 1e-5:
                    # 如果重合且未连接时进行连接操作
                    if not current_bone.use_connect:
                        current_bone.use_connect = True

            # 递归处理子骨骼
            for child_bone in current_bone.children:
                connect_bones_recursive(armature, child_bone.name)

        def connect_selected_bones():
            armature = bpy.context.active_object
            
            if armature and armature.type == 'ARMATURE':
                # 存储当前模式
                original_mode = armature.mode

                # 确保在编辑模式中进行操作
                if original_mode != 'EDIT':
                    bpy.ops.object.mode_set(mode='EDIT')

                try:
                    for bone in bpy.context.selected_editable_bones:
                        connect_bones_recursive(armature, bone.name)
                finally:
                    # 切换回原始模式
                    if original_mode != 'EDIT':
                        bpy.ops.object.mode_set(mode=original_mode)
        # 运行该功能
        connect_selected_bones()


        return {'FINISHED'}
    


def register():
    bpy.utils.register_class(ConnectBone)
    bpy.utils.register_class(ResetBonePosition)

def unregister():
    bpy.utils.unregister_class(ConnectBone)
    bpy.utils.unregister_class(ResetBonePosition)
