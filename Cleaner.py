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
        self.report({'INFO'}, "UV已清理完成")
        return {'FINISHED'}

# Call the function to validate and fix UVs
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

def remove_broken_images():
    """删除所有丢失的（无法找到源路径）的图片"""
    removed_count = 0
    for img in list(bpy.data.images):  # 遍历所有图片
        try:
            # 尝试访问图片路径，捕获编码错误
            if img.filepath and not img.packed_file:
                abs_path = bpy.path.abspath(img.filepath)
                if not os.path.exists(abs_path):  # 检查文件是否存在
                    bpy.data.images.remove(img)  # 删除丢失的图片
                    removed_count += 1
        except UnicodeDecodeError:
            # 如果路径包含无法解码的字符，直接移除该图片
            print(f"无法解码图片路径，移除图片: {img.name}")
            bpy.data.images.remove(img)
            removed_count += 1
        except Exception as e:
            # 捕获其他可能的异常
            print(f"处理图片 {img.name} 时出错: {str(e)}")
            continue
    return removed_count

class IMAGE_OT_RemoveBrokenImages(bpy.types.Operator):
    """操作类：用于清除引用但丢失的图片"""
    
    bl_idname = "image.remove_broken"
    bl_label = "清除丢失的图片"
    
    def execute(self, context):
        count = remove_broken_images()
        self.report({'INFO'}, f"已移除 {count} 张丢失的图片")
        return {'FINISHED'}


class UNUSED_MATERIAL_SLOTS_OT_Remove(bpy.types.Operator):
    bl_idname = "object.remove_unused_material_slots"
    bl_label = "Remove Unused Material Slots"
    bl_description = "Removes unused material slots from selected objects"

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        selected_objects = context.selected_objects
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                obj.update_from_editmode()
                used_material_indices = set()
                material_index_mapping = {}
                for poly in obj.data.polygons:
                    used_material_indices.add(poly.material_index)
                    material_index_mapping[poly.index] = poly.material_index
                    
                used_material_slots = [obj.material_slots[index].material for index in sorted(used_material_indices)]

                for _ in range(len(obj.material_slots)):

                    bpy.ops.object.material_slot_remove()
                    # bpy.ops.object.material_slot_remove({'object': obj})

                for material in used_material_slots:
                    obj.data.materials.append(material)

                for poly in obj.data.polygons:
                    original_index = material_index_mapping[poly.index]
                    poly.material_index = used_material_slots.index(obj.material_slots[original_index].material)

        return {'FINISHED'}

#清理无子集空物体
class OBJECT_OT_clean_empty(bpy.types.Operator):
    """My Object Empty Deleting Script"""
    bl_idname = "object.clean_empty"
    bl_label = "清除无子集空物体"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取当前场景的所有对象
        scene_objects = context.scene.objects
        # 收集所有没有子对象的空物体
        empties_to_delete = [obj for obj in scene_objects if obj.type == 'EMPTY' and not obj.children]
        # 删除这些空物体
        for empty in empties_to_delete:
            bpy.data.objects.remove(empty)
        
        self.report({'INFO'}, f"Deleted {len(empties_to_delete)} empty objects without children.")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.register_class(UVCleaner)
    bpy.utils.register_class(OBJECT_OT_clean_meshes_without_faces)
    bpy.utils.register_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    bpy.utils.register_class(OBJECT_OT_clean_empty)

def unregister():
    bpy.utils.unregister_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.unregister_class(UVCleaner)
    bpy.utils.unregister_class(OBJECT_OT_clean_meshes_without_faces)
    bpy.utils.unregister_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    bpy.utils.unregister_class(OBJECT_OT_clean_empty)

if __name__ == "__main__":
     register()