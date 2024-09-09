import bpy

class OBJECT_OT_clean_meshes_without_faces(bpy.types.Operator):
    """清理没有面的物体"""
    bl_idname = "object.clean_meshes_without_faces"
    bl_label = "Clean Meshes Without Faces"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 删除场景中没有面的物体（仅包含顶点或边）
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                mesh = obj.data
                if len(mesh.polygons) == 0:  # 检查物体是否没有面
                    obj.select_set(True)

        # 删除选择的没有面的物体
        bpy.ops.object.delete()

        # 强制更新视图层
        bpy.context.view_layer.update()

        self.report({'INFO'}, "无面片物体已经清理")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(OBJECT_OT_clean_meshes_without_faces)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_clean_meshes_without_faces)
