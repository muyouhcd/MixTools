import bpy

class SetEmptyDisplaySize(bpy.types.Operator):
    bl_idname = "object.set_empty_display_size"
    bl_label = "设置空物体显示尺寸"
    bl_description = "将所选空物体的显示尺寸设置为指定值"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取所有选中的物体
        selected_objects = [obj for obj in bpy.context.selected_objects]
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择一些物体")
            return {'CANCELLED'}
        
        # 过滤出空物体
        empty_objects = [obj for obj in selected_objects if obj.type == 'EMPTY']
        
        if not empty_objects:
            self.report({'WARNING'}, "所选物体中没有空物体")
            return {'CANCELLED'}
        
        # 获取场景中设置的显示尺寸值
        display_size = context.scene.empty_display_size
        
        # 设置每个空物体的显示尺寸
        for empty_obj in empty_objects:
            empty_obj.empty_display_size = display_size
        
        self.report({'INFO'}, f"已将 {len(empty_objects)} 个空物体的显示尺寸设置为 {display_size}")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(SetEmptyDisplaySize)
    # 注册场景属性
    bpy.types.Scene.empty_display_size = bpy.props.FloatProperty(
        name="空物体显示尺寸",
        description="设置空物体的显示尺寸",
        default=1.0,
        min=0.01,
        max=100.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=2
    )

def unregister():
    bpy.utils.unregister_class(SetEmptyDisplaySize)
    # 注销场景属性
    delattr(bpy.types.Scene, 'empty_display_size')

if __name__ == "__main__":
    register()
