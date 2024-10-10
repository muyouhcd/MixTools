import bpy

class ObjectInstancer(bpy.types.Operator):
    bl_idname = "object.object_instance"
    bl_label = "Object Instance"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取所选物体
        selected_objects = context.selected_objects
        if len(selected_objects) < 2:
            self.report({'WARNING'}, "请至少选择两个物体")
            return {'CANCELLED'}
        
        # 使用第一个选中的物体作为替换源
        source_obj = selected_objects[0]
        
        # 记录所选物体的世界空间变换
        world_transforms = [obj.matrix_world.copy() for obj in selected_objects]
        
        # 删除所有选中的物体(除了源物体)
        for obj in selected_objects[1:]:
            bpy.data.objects.remove(obj, do_unlink=True)
        
        # 根据记录的世界空间变换创建源物体的链接副本
        for transform in world_transforms[1:]:
            new_obj = bpy.data.objects.new(source_obj.name, source_obj.data)
            new_obj.matrix_world = transform
            context.collection.objects.link(new_obj)

        self.report({'INFO'}, "替换完成")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ObjectInstancer)

def unregister():
    bpy.utils.unregister_class(ObjectInstancer)
