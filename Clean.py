import bpy
import os
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
        # print("开始处理顶点")
        # bpy.ops.object.vox_operation()
        # print("开始处理碰撞")
        # bpy.ops.object.miao_parent_byboundingbox()
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


def remove_broken_images():
    """删除所有丢失的（无法找到源路径）的图片"""
    removed_count = 0
    for img in list(bpy.data.images):  # 遍历所有图片
        if img.filepath and not img.packed_file:
            abs_path = bpy.path.abspath(img.filepath)
            if not os.path.exists(abs_path):  # 检查文件是否存在
                bpy.data.images.remove(img)  # 删除丢失的图片
                removed_count += 1
    return removed_count

class IMAGE_OT_RemoveBrokenImages(bpy.types.Operator):
    """操作类：用于清除引用但丢失的图片"""
    
    bl_idname = "image.remove_broken"
    bl_label = "清除丢失的图片"
    
    def execute(self, context):
        count = remove_broken_images()
        self.report({'INFO'}, f"已移除 {count} 张丢失的图片")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.register_class(UVCleaner)

def unregister():
    bpy.utils.unregister_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.unregister_class(UVCleaner)

if __name__ == "__main__":
     register()