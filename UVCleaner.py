import bpy
import math


class UVCleaner(bpy.types.Operator):
    bl_idname = "object.uv_cleaner"
    bl_label = "UV清理"

    
    def apply_transforms_recursive(self, obj):
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.select_set(False)

        if obj.children:
            for child in obj.children:
                self.apply_transforms_recursive(child)

    def execute(self, context):
        print("开始处理顶点")
        bpy.ops.object.vox_operation()
        print("开始处理碰撞")
        bpy.ops.object.miao_parent_byboundingbox()
        def validate_and_fix_uvs():
            for mesh in bpy.data.meshes:
                for uv_layer in mesh.uv_layers:
                    invalid_uvs = False
                    for uv in uv_layer.data:
                        if math.isnan(uv.uv.x) or math.isnan(uv.uv.y):
                            invalid_uvs = True
                            print(f"NaN UV found in mesh '{mesh.name}' in UV layer '{uv_layer.name}'")
                            uv.uv.x = 0.0
                            uv.uv.y = 0.0
                            print(f"Fixed NaN UV in mesh '{mesh.name}' in UV layer '{uv_layer.name}'")
                    if invalid_uvs:
                        print(f"UV layer '{uv_layer.name}' in mesh '{mesh.name}' had NaN values and has been fixed.")
        validate_and_fix_uvs()
# Call the function to validate and fix UVs


def register():
    bpy.utils.register_class(UVCleaner)

def unregister():
    bpy.utils.unregister_class(UVCleaner)
