import bpy

# 定义自定义属性
bpy.types.Scene.rv_start_frame = bpy.props.IntProperty(name="Start Frame", default=1, description="开始帧")
bpy.types.Scene.rv_end_frame = bpy.props.IntProperty(name="End Frame", default=250, description="结束帧")
bpy.types.Scene.rv_initial_visibility = bpy.props.BoolProperty(name="Initial Visibility", default=True, description="初始可见性")

class OBJECT_OT_set_render_visibility(bpy.types.Operator):
    bl_label = "设置渲染可见性"
    bl_idname = "object.set_render_visibility"
    bl_description = "在帧范围内为选中的物体设置渲染可见性"

    def execute(self, context):
        start_frame = context.scene.rv_start_frame
        end_frame = context.scene.rv_end_frame
        initial_visibility = context.scene.rv_initial_visibility

        selected_objects = context.selected_objects

        for obj in selected_objects:
            self.apply_visibility(obj, start_frame, end_frame, initial_visibility)

        self.report({'INFO'}, "渲染可见性已成功设置")
        return {'FINISHED'}
    
    def apply_visibility(self, obj, start_frame, end_frame, initial_visibility):
        # 如果存在旧的关键帧，清除它们
        if obj.animation_data and obj.animation_data.action:
            for fcurve in (fc for fc in obj.animation_data.action.fcurves if "hide_render" in fc.data_path):
                obj.animation_data.action.fcurves.remove(fcurve)

        # 设置新的关键帧
        visibility_states = [not initial_visibility, initial_visibility, not initial_visibility]
        frames = [start_frame, start_frame + 1, end_frame]
        
        for frame, visible in zip(frames, visibility_states):
            obj.hide_render = visible
            obj.keyframe_insert(data_path="hide_render", frame=frame)

        #递归应用到子物体
        for child in obj.children:
            self.apply_visibility(child, start_frame, end_frame, initial_visibility)

def register():
    bpy.utils.register_class(OBJECT_OT_set_render_visibility)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_set_render_visibility)

if __name__ == "__main__":
    register()


