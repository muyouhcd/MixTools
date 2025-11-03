import bpy
import os
import math
import hashlib


class UVCleaner(bpy.types.Operator):
    bl_idname = "object.uv_cleaner"
    bl_label = "UV清理"
    
    def execute(self, context):
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

                for material in used_material_slots:
                    obj.data.materials.append(material)

                for poly in obj.data.polygons:
                    original_index = material_index_mapping[poly.index]
                    poly.material_index = used_material_slots.index(obj.material_slots[original_index].material)

        return {'FINISHED'}


class OBJECT_OT_clean_empty(bpy.types.Operator):
    """清理无子集空物体"""
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

#自动递归清理无子集空物体
class OBJECT_OT_clean_empty_recursive(bpy.types.Operator):
    """自动递归清理无子集空物体"""
    bl_idname = "object.clean_empty_recursive"
    bl_label = "自动递归清理"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        total_deleted = 0
        iteration = 0
        max_iterations = 100  # 防止无限循环
        
        while iteration < max_iterations:
            iteration += 1
            # 获取当前场景的所有对象
            scene_objects = context.scene.objects
            # 收集所有没有子对象的空物体
            empties_to_delete = [obj for obj in scene_objects if obj.type == 'EMPTY' and not obj.children]
            
            if not empties_to_delete:
                # 没有更多空物体可以删除，退出循环
                break
                
            # 删除这些空物体
            for empty in empties_to_delete:
                bpy.data.objects.remove(empty)
            
            total_deleted += len(empties_to_delete)
            
            # 强制更新场景
            bpy.context.view_layer.update()
        
        if iteration >= max_iterations:
            self.report({'WARNING'}, f"达到最大迭代次数({max_iterations})，可能还有空物体未清理")
        
        self.report({'INFO'}, f"递归清理完成，共删除了 {total_deleted} 个空物体，进行了 {iteration} 次迭代")

        return {'FINISHED'}


# 清理空物体（删除所选空物体）
class CleanEmpty(bpy.types.Operator):
    bl_idname = "object.mian_clean_empty"
    bl_label = "清理所选空物体"
    bl_description = "删除所选的空物体（没有几何数据的物体）"

    def execute(self, context):
        # 遍历所选的物体
        for obj in bpy.context.selected_objects:
            # 检查物体是否为空
            if obj.type == 'EMPTY':
                # 从场景中删除空物体
                bpy.data.objects.remove(obj)

        # 更新场景
        bpy.context.view_layer.update()
        return {"FINISHED"}


# 清空空集合
def clean_collection(collection):
    for child in collection.children:  
        clean_collection(child)

    if collection.children:
        return
    
    if not collection.objects:
        bpy.data.collections.remove(collection)


class CleanCollection(bpy.types.Operator):
    bl_idname = "object.mian_clean_collection"
    bl_label = "清空空集合"
    bl_description = "删除场景中所有空的集合（不包含任何物体的集合）"

    def execute(self, context):
        scene = bpy.context.scene
        
        clean_collection(scene.collection)

        return {'FINISHED'}


class RemoveModifiers(bpy.types.Operator):
    """移除所选物体的修改器"""
    bl_idname = "object.remove_modifiers"
    bl_label = "移除选中物体的修改器"
    bl_description = "移除所选物体的所有修改器，包括子物体"

    def execute(self, context):
        # 获取当前的选中物体
        selected_objects = context.selected_objects

        # 遍历每个选中的物体
        for obj in selected_objects:

            # 判断这个物体是否有修改器
            if obj.type == 'MESH' and obj.modifiers:

                #如果有，那么我们就移除所有的修改器
                while(obj.modifiers):
                    obj.modifiers.remove(obj.modifiers[0])

        return {'FINISHED'}


#移除所选物体约束
class RemoveConstraints(bpy.types.Operator):
    """移除所选物体的约束"""
    bl_idname = "object.remove_constraints"
    bl_label = "移除选中物体的约束"
    bl_description = "移除所选物体的所有约束，包括子物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前的选中物体
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个物体")
            return {'CANCELLED'}

        removed_count = 0
        processed_objects = 0

        # 遍历每个选中的物体
        for obj in selected_objects:
            # 检查物体是否有约束
            if obj.constraints:
                constraint_count = len(obj.constraints)
                # 移除所有约束
                while obj.constraints:
                    obj.constraints.remove(obj.constraints[0])
                removed_count += constraint_count
                processed_objects += 1

        if removed_count > 0:
            self.report({'INFO'}, f"成功从 {processed_objects} 个物体中移除了 {removed_count} 个约束")
        else:
            self.report({'INFO'}, "所选物体没有约束需要移除")

        return {'FINISHED'}


# 删除实例化物体重复项
class RemoveInstanceDuplicatesOperator(bpy.types.Operator):
    bl_idname = "object.remove_instance_duplicates"
    bl_label = "删除实例化物体重复项"
    bl_description = "删除所有相关联（实例化）出来的物体，仅保留一个"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取所有网格物体
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        if len(mesh_objects) < 2:
            self.report({'WARNING'}, "场景中至少需要2个网格物体")
            return {'CANCELLED'}

        # 按几何相同性分组
        identical_groups = self.group_identical_objects_by_hash(mesh_objects)
        
        if not identical_groups:
            self.report({'INFO'}, "未发现几何相同的物体")
            return {'FINISHED'}

        # 处理每组几何相同的物体，删除重复项
        processed_count = 0
        deleted_count = 0
        
        for group in identical_groups:
            if len(group) > 1:  # 只处理有多个物体的组
                deleted_in_group = self.remove_duplicates_from_group(context, group)
                if deleted_in_group > 0:
                    processed_count += 1
                    deleted_count += deleted_in_group

        if processed_count > 0:
            self.report({'INFO'}, f"成功处理了 {processed_count} 组几何相同的物体，删除了 {deleted_count} 个重复物体")
        else:
            self.report({'INFO'}, "未发现需要删除的重复物体")
        
        return {'FINISHED'}

    def get_mesh_identifier(self, obj):
        """
        获取网格对象的唯一标识，用于比较几何相同性。
        通过顶点坐标、边、面信息生成哈希值，不比较物体位置、旋转、缩放信息。
        """
        if obj.type != 'MESH':
            return None  # 非网格对象返回 None

        mesh = obj.data

        # 将顶点、边、面数据拼接成字符串，用于哈希生成
        vertex_data = "".join([f"{v.co.x},{v.co.y},{v.co.z}" for v in mesh.vertices])
        edge_data = "".join([f"{e.vertices[0]},{e.vertices[1]}" for e in mesh.edges])
        polygon_data = "".join(["".join(map(str, sorted(p.vertices))) for p in mesh.polygons])

        # 创建哈希值，唯一标识该物体的网格几何
        data = vertex_data + edge_data + polygon_data
        mesh_hash = hashlib.md5(data.encode('utf-8')).hexdigest()

        return mesh_hash

    def group_identical_objects_by_hash(self, mesh_objects):
        """
        使用网格哈希值将几何相同的网格对象分组。
        返回分组列表，每组是一列表，内含相同几何的物体。
        """
        mesh_groups = {}  # 使用字典存储组 {hash: [object, object,...]}

        for obj in mesh_objects:
            if obj.type != 'MESH':  # 跳过非网格对象
                continue

            mesh_hash = self.get_mesh_identifier(obj)
            if not mesh_hash:  # 如果无法生成哈希值，跳过
                continue

            # 根据哈希值分组
            if mesh_hash in mesh_groups:
                mesh_groups[mesh_hash].append(obj)  # 添加到现有组
            else:
                mesh_groups[mesh_hash] = [obj]  # 创建新的组

        # 返回分组后的结果，每组是一个物体列表
        return [group for group in mesh_groups.values() if len(group) > 1]

    def remove_duplicates_from_group(self, context, group_objects):
        """
        从一组几何相同的物体中删除重复项，只保留第一个。
        返回删除的物体数量。
        """
        try:
            if len(group_objects) <= 1:
                return 0

            # 保留第一个物体，删除其余的
            objects_to_delete = group_objects[1:]
            deleted_count = 0

            for obj in objects_to_delete:
                if obj and obj.name in bpy.data.objects:
                    # 删除物体
                    bpy.data.objects.remove(obj, do_unlink=True)
                    deleted_count += 1

            return deleted_count
            
        except Exception as e:
            print(f"错误：无法删除重复物体，物体组：{[obj.name for obj in group_objects if obj]}")
            return 0


class CleanSense(bpy.types.Operator):
    bl_idname = "object.mian_clean_sense"
    bl_label = "清理场景"

    def execute(self, context):
        def remove_unused_data_blocks():
            # 删除未使用的万花筒
            bpy.ops.outliner.orphans_purge()

            # 删除未使用的材质
            for material in bpy.data.materials:
                if not material.users:
                    bpy.data.materials.remove(material)

            # 删除未使用的纹理
            for texture in bpy.data.textures:
                if not texture.users:
                    bpy.data.textures.remove(texture)

            # 删除未使用的节点分组（Node groups）
            for node_group in bpy.data.node_groups:
                if not node_group.users:
                    bpy.data.node_groups.remove(node_group)

            # 删除未使用的颜色距（Color Ramps）
            for color_ramp in bpy.data.node_groups:
                if not color_ramp.users:
                    bpy.data.node_groups.remove(color_ramp)

            # 删除未使用的画笔
            for brush in bpy.data.brushes:
                if not brush.users:
                    bpy.data.brushes.remove(brush)

            # 删除未使用的贴图
            for image in bpy.data.images:
                if not image.users:
                    bpy.data.images.remove(image)

        def recursive_cleanup(num_iterations=5):
            for _ in range(num_iterations):
                data_sizes = [
                    len(bpy.data.materials),
                    len(bpy.data.textures),
                    len(bpy.data.node_groups),
                    len(bpy.data.brushes),
                    len(bpy.data.images),
                ]

                remove_unused_data_blocks()

                new_data_sizes = [
                    len(bpy.data.materials),
                    len(bpy.data.textures),
                    len(bpy.data.node_groups),
                    len(bpy.data.brushes),
                    len(bpy.data.images),
                ]

                if data_sizes == new_data_sizes:
                    break

        recursive_cleanup()

        return {"FINISHED"}


#批量清空动画数据
class ClearAnimationData(bpy.types.Operator):
    bl_idname = "object.clear_animation_data"
    bl_label = "清除动画数据"
    bl_description = "清除所选物体的所有动画数据，包括关键帧和动画曲线"

    def clear_animation_data_for_selected(self):
        selected_objects = bpy.context.selected_objects
        
        for obj in selected_objects:
            if obj.animation_data:
                obj.animation_data_clear()
                print(f"已清除 {obj.name} 的动画数据")
            else:
                print(f"{obj.name} 没有动画数据")

    def execute(self, context):
        self.clear_animation_data_for_selected()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.register_class(UVCleaner)
    bpy.utils.register_class(OBJECT_OT_clean_meshes_without_faces)
    bpy.utils.register_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    bpy.utils.register_class(OBJECT_OT_clean_empty)
    bpy.utils.register_class(OBJECT_OT_clean_empty_recursive)
    bpy.utils.register_class(CleanEmpty)
    bpy.utils.register_class(CleanCollection)
    bpy.utils.register_class(RemoveModifiers)
    bpy.utils.register_class(RemoveConstraints)
    bpy.utils.register_class(RemoveInstanceDuplicatesOperator)
    bpy.utils.register_class(CleanSense)
    bpy.utils.register_class(ClearAnimationData)

def unregister():
    bpy.utils.unregister_class(IMAGE_OT_RemoveBrokenImages)
    bpy.utils.unregister_class(UVCleaner)
    bpy.utils.unregister_class(OBJECT_OT_clean_meshes_without_faces)
    bpy.utils.unregister_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    bpy.utils.unregister_class(OBJECT_OT_clean_empty)
    bpy.utils.unregister_class(OBJECT_OT_clean_empty_recursive)
    bpy.utils.unregister_class(CleanEmpty)
    bpy.utils.unregister_class(CleanCollection)
    bpy.utils.unregister_class(RemoveModifiers)
    bpy.utils.unregister_class(RemoveConstraints)
    bpy.utils.unregister_class(RemoveInstanceDuplicatesOperator)
    bpy.utils.unregister_class(CleanSense)
    bpy.utils.unregister_class(ClearAnimationData)

if __name__ == "__main__":
     register()