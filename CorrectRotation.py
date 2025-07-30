import bpy


# 校正旋转

class CorrectRotation(bpy.types.Operator):
    bl_idname = "object.mian_correct_rotation"
    bl_label = "校正旋转"

    def execute(self, context):

        def get_3d_view_orientation_matrix():
            # 查找当前激活的3D视图区域
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    # 获取3D视图空间数据
                    space_data = area.spaces.active
                    # 获取当前视图的旋转矩阵
                    rotation_matrix = space_data.region_3d.view_rotation.to_matrix()
                    return rotation_matrix
            return None

        def view_axis(axis, align_active=False):
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = bpy.context.copy()
                            override['area'] = area
                            override['region'] = region
                            bpy.ops.view3d.view_axis(
                                override, type=axis, align_active=align_active)
                            return

        # 使用示例：根据当前所选对象查看顶部视图

        view_axis(axis='TOP', align_active=True)
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.scene.tool_settings.use_transform_data_origin = True

        o_m = get_3d_view_orientation_matrix()
        # print(o_m)

        bpy.ops.transform.transform(mode='ALIGN', value=(0, 0, 0, 0), orient_type='GLOBAL', orient_matrix=(o_m), orient_matrix_type='GLOBAL', mirror=False, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1,
                                    use_proportional_connected=False, use_proportional_projected=False, snap=False, snap_elements={'INCREMENT'}, use_snap_project=False, snap_target='CLOSEST', use_snap_self=False, use_snap_edit=False, use_snap_nonedit=False, use_snap_selectable=False)

        bpy.context.scene.tool_settings.use_transform_data_origin = False
        bpy.ops.object.rotation_clear(clear_delta=False)
        view_axis(axis='FRONT', align_active=True)

        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


def register():
    bpy.utils.register_class(CorrectRotation)

def unregister():
    bpy.utils.unregister_class(CorrectRotation)