import bpy
import random
import bmesh
import mathutils
import collections
import os
import math
import time
import hashlib
from bpy.types import Menu
from mathutils import Matrix
from mathutils import Vector
from collections import defaultdict
import re
from mathutils.bvhtree import BVHTree
from bpy.props import PointerProperty
from bpy.types import Operator, Panel, Collection
from bpy.props import EnumProperty
from bpy_extras.object_utils import world_to_camera_view
from mathutils import kdtree
from mathutils import Quaternion

#转换实例化对象
class ObjectInstancer(bpy.types.Operator):
    bl_idname = "object.object_instance"
    bl_label = "Object Instance"
    bl_description = "将所选物体转换为实例化对象：使用第一个物体作为源，其余物体替换为其实例，保持原有位置和变换"
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

        def duplicate_with_children(obj, parent=None):
            # 复制给定物体
            new_obj = bpy.data.objects.new(obj.name, obj.data)

            # 确保将新的对象与场景关联
            context.collection.objects.link(new_obj)

            # 保留变换
            new_obj.matrix_world = obj.matrix_world.copy()
            if obj.type == 'EMPTY':
                new_obj.empty_display_size = obj.empty_display_size

            # 设置父级关系
            if parent:
                new_obj.parent = parent
                new_obj.matrix_parent_inverse = parent.matrix_world.inverted()

            # 递归复制子物体
            for child in obj.children:
                duplicate_with_children(child, new_obj)

            return new_obj

        # 根据记录的世界空间变换创建源物体及其子物体的链接副本
        for transform in world_transforms[1:]:
            new_instance = duplicate_with_children(source_obj)
            if new_instance is not None:
                # 应用变换
                new_instance.matrix_world = transform

        self.report({'INFO'}, "替换完成")
        return {'FINISHED'}   

# 几何相同性检测和实例化
class GeometryMatcherOperator(bpy.types.Operator):
    bl_idname = "object.geometry_matcher"
    bl_label = "几何相同性检测并实例化"
    bl_description = "检测几何相同的物体并转换为实例化对象"
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

        # 处理每组几何相同的物体
        processed_count = 0
        for group in identical_groups:
            if len(group) > 1:  # 只处理有多个物体的组
                if self.process_object_group(context, group):
                    processed_count += 1

        self.report({'INFO'}, f"成功处理了 {processed_count} 组几何相同的物体")
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

    def process_object_group(self, context, group_objects):
        """
        对一组几何相同的物体执行实例化操作。
        """
        try:
            # 清除所有选择，并选择组中的所有物体
            bpy.ops.object.select_all(action='DESELECT')
            for obj in group_objects:
                if obj and obj.name in bpy.data.objects:  # 确保对象有效
                    obj.select_set(True)

            # 设置组中的第一个物体为活动对象
            if group_objects[0] and group_objects[0].name in bpy.data.objects:
                bpy.context.view_layer.objects.active = group_objects[0]

            # 执行实例化操作
            bpy.ops.object.object_instance()
            
            return True
            
        except Exception as e:
            print(f"错误：无法对物体组执行操作，物体组：{[obj.name for obj in group_objects if obj]}")
            return False

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

class OBJECT_OT_reset_z_axis(Operator):
    bl_idname = "object.reset_z_axis"
    bl_label = "重置选择对象的Z轴位置"
    bl_description = "将所选物体的Z轴位置重置为0，保持X和Y轴位置不变"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 遍历所有选中的对象
        for obj in context.selected_objects:
            # 将对象的 Z 轴位置设置为 0
            obj.location.z = 0.0
        
        return {'FINISHED'}

#批量独立化
class OBJECT_OT_make_single_user(bpy.types.Operator):
    bl_idname = "object.make_single_user_operator"
    bl_label = "批量独立化"
    bl_description = "将所选物体的数据块独立化，使每个物体拥有独立的数据副本"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前的选择物体列表
        selected_objects = context.selected_objects

        # 遍历所选物体并执行make_single_user命令
        for obj in selected_objects:
            context.view_layer.objects.active = obj  # 将当前物体设置为活动对象
            bpy.ops.object.make_single_user(
                object=True,    # 单独化对象
                obdata=True,   # 不单独化数据
                material=False, # 不单独化材质
                animation=False, # 不单独化动画
                obdata_animation=False # 不单独化数据动画
            )

        # 更新场景以反映更改
        context.view_layer.update()

        return {'FINISHED'}

#生成凸包
class OBJECT_OT_convex_hull_creator(bpy.types.Operator):
    bl_idname = "object.convex_hull_creator"
    bl_label = "生成凸包"
    bl_description = "为所选物体生成凸包网格，创建包围所有顶点的凸多面体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected = context.selected_objects

        # 使用集合来收集父物体名称以自动移除重复项
        parent_names = set()

        duplicates = []

        for obj in selected:
            top_parent = obj
            while top_parent.parent is not None:
                top_parent = top_parent.parent

            # 将父物体名称添加到集合中
            parent_names.add(top_parent.name)

            dup_obj = obj.copy()
            dup_obj.data = obj.data.copy()
            dup_obj.modifiers.clear()
            context.collection.objects.link(dup_obj)
            duplicates.append(dup_obj)

        bpy.ops.object.select_all(action='DESELECT')

        for dup_obj in duplicates:
            dup_obj.select_set(True)

        bpy.context.view_layer.objects.active = duplicates[0]
        bpy.ops.object.join()

        obj_in_edit = context.object
        context.view_layer.objects.active = obj_in_edit
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.convex_hull()
        bpy.ops.object.mode_set(mode='OBJECT')

        if len(obj_in_edit.data.materials) > 0:
            for _ in range(len(obj_in_edit.data.materials)):
                obj_in_edit.data.materials.pop(index=0)

        # 用已排除重复的父物体名字来命名新物体
        final_name = '_'.join(parent_names) + "_col"
        obj_in_edit.name = final_name
        obj_in_edit.data.name = final_name + "_mesh"

        return {'FINISHED'}

class VoxelConverter(bpy.types.Operator):
    """生成obj2vox指令"""
    bl_idname = "object.voxel_converter"
    bl_label = "生成体素化指令"

    # 添加一个IntProperty属性，用于从UI获取用户输入的值
    resolution_factor: bpy.props.IntProperty(
        name = "分辨率因子",
        description = "定义体素化时使用的分辨率乘数",
        default = 32,
        min = 1
    )#type: ignore

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            dimensions = obj.dimensions
            max_dim = max(dimensions.x, dimensions.y, dimensions.z)
            # 使用用户输入的值（或默认值）来计算result
            result = round(max_dim * context.scene.resolution_factor)
            print(f"obj2voxel {obj.name}.obj {obj.name}.vox -r {result} -p xZy ")
        return {'FINISHED'}

#移除所选物体修改器
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

#曲线精简到两个端点
class SimplifyCurveToEndpoints(bpy.types.Operator):
    """将所选曲线精简到仅剩两个端点"""
    bl_idname = "object.simplify_curve_to_endpoints"
    bl_label = "曲线精简到端点"
    bl_description = "将所选曲线精简到仅剩两个端点"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前的选中物体
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个曲线物体")
            return {'CANCELLED'}

        processed_count = 0
        curve_objects = []

        # 筛选出曲线物体
        for obj in selected_objects:
            if obj.type == 'CURVE':
                curve_objects.append(obj)

        if not curve_objects:
            self.report({'WARNING'}, "所选物体中没有曲线物体")
            return {'CANCELLED'}

        # 处理每个曲线物体
        for obj in curve_objects:
            try:
                # 进入编辑模式
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有控制点
                bpy.ops.curve.select_all(action='SELECT')
                
                # 使用精简操作，将曲线精简到最少点数
                # 这里我们使用一个循环来逐步精简，直到只剩下两个点
                bpy.ops.curve.decimate(ratio=0.1)
                
                # 如果还有超过2个点，继续精简
                while True:
                    # 获取当前选中的点数
                    bpy.ops.curve.select_all(action='SELECT')
                    selected_count = len([p for p in obj.data.splines[0].points if p.select])
                    
                    if selected_count <= 2:
                        break
                    
                    # 进一步精简
                    bpy.ops.curve.decimate(ratio=0.5)
                
                # 返回对象模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                processed_count += 1
                
            except Exception as e:
                print(f"处理曲线 {obj.name} 时出错: {e}")
                # 确保返回对象模式
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
                continue

        if processed_count > 0:
            self.report({'INFO'}, f"成功精简了 {processed_count} 个曲线物体")
        else:
            self.report({'WARNING'}, "没有成功处理任何曲线物体")

        return {'FINISHED'}

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

# 置乱位置
class RandomPlacement(bpy.types.Operator):
    bl_idname = "object.mian_random_placement"
    bl_label = "随机放置"
    bl_description = "在指定范围内随机分布所选物体的位置"

    def execute(self, context):

        bpy.types.Scene.random_placement_extent = bpy.props.FloatVectorProperty(
            name="范围大小(x,y,z)",
            description="设置随机放置的范围大小",
            default=(10, 10, 0),
            size=3
        )
        # 获取自定义属性的值
        extent = bpy.context.scene.random_placement_extent

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        # Scatter the objects randomly in the defined area
        for obj in objects:
            obj.location = (random.uniform(-extent[0], extent[0]),
                            random.uniform(-extent[1], extent[1]),
                            random.uniform(-extent[2], extent[2]))

        return {'FINISHED'}

# 置乱缩放属性注册已移至 register() 函数中
class RandomScale(bpy.types.Operator):
    bl_idname = "object.mian_random_scale"
    bl_label = "随机缩放"
    bl_description = "在指定范围内随机缩放所选物体，可分别设置X、Y、Z轴的缩放范围"

    def execute(self, context):
        # 获取自定义属性的值
        scale_extent_x = bpy.context.scene.random_scale_extent_x
        scale_extent_y = bpy.context.scene.random_scale_extent_y
        scale_extent_z = bpy.context.scene.random_scale_extent_z

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        # Scale the objects randomly within the defined range for each axis
        for obj in objects:
            scale_factor_x = random.uniform(
                scale_extent_x[0], scale_extent_x[1])
            scale_factor_y = random.uniform(
                scale_extent_y[0], scale_extent_y[1])
            scale_factor_z = random.uniform(
                scale_extent_z[0], scale_extent_z[1])
            obj.scale = (scale_factor_x, scale_factor_y, scale_factor_z)

        return {'FINISHED'}

# 随机旋转属性注册已移至 register() 函数中

class RandomRotation(bpy.types.Operator):
    bl_idname = "object.mian_random_rotation"
    bl_label = "随机旋转"
    bl_description = "对所选物体进行指定轴向的随机旋转"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import math
        import mathutils
        import random
        
        # 获取自定义属性的值
        rotation_extent_x = bpy.context.scene.random_rotation_extent_x
        rotation_extent_y = bpy.context.scene.random_rotation_extent_y
        rotation_extent_z = bpy.context.scene.random_rotation_extent_z

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        if not objects:
            self.report({'WARNING'}, "请先选择要旋转的物体")
            return {'CANCELLED'}

        # 对每个物体进行随机旋转
        for obj in objects:
            # 获取当前旋转值
            current_rotation = obj.rotation_euler.copy()
            
            # 计算随机旋转角度（弧度）
            random_rotation_x = math.radians(random.uniform(-rotation_extent_x, rotation_extent_x))
            random_rotation_y = math.radians(random.uniform(-rotation_extent_y, rotation_extent_y))
            random_rotation_z = math.radians(random.uniform(-rotation_extent_z, rotation_extent_z))
            
            # 应用随机旋转
            new_rotation = (
                current_rotation[0] + random_rotation_x,
                current_rotation[1] + random_rotation_y,
                current_rotation[2] + random_rotation_z
            )
            
            obj.rotation_euler = new_rotation

        self.report({'INFO'}, f"已对 {len(objects)} 个物体应用随机旋转")
        return {'FINISHED'}


# 名称顺序y轴列队
bpy.types.Scene.use_bounding_box = bpy.props.BoolProperty(
    name="使用包围盒",
    description="按照包围盒尺寸排列",
    default=False
)
bpy.types.Scene.queue_up_distance = bpy.props.FloatProperty(
    name="距离",
    description="列队移动的距离",
    default=1
)
bpy.types.Scene.queue_up_axis = bpy.props.EnumProperty(
    name="轴向",
    items=[("X", "X轴", "在X轴上排队"),
           ("Y", "Y轴", "在Y轴上排队"),
           ("Z", "Z轴", "在Z轴上排队")],
    default="X"
)
class QueueUp(bpy.types.Operator):
    bl_idname = "object.mian_queue_up"
    bl_label = "列队"
    bl_description = "将所选物体按指定轴向和间距进行排列，形成整齐的队列"

    def execute(self, context):
        distance = bpy.context.scene.queue_up_distance
        axis = bpy.context.scene.queue_up_axis
        use_bounding_box = bpy.context.scene.use_bounding_box

        objects = sorted(list(bpy.context.selected_objects), key=lambda obj: obj.name)
        
        if len(objects) == 0:
            self.report({'WARNING'}, "没有选中的物体")
            return {"CANCELLED"}

        current_position = Vector((0, 0, 0))

        for obj in objects:
            if use_bounding_box:
                # 获取物体包围盒的边界角点坐标
                bounding_box_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                min_corner = Vector((min([v.x for v in bounding_box_corners]),
                                     min([v.y for v in bounding_box_corners]),
                                     min([v.z for v in bounding_box_corners])))
                max_corner = Vector((max([v.x for v in bounding_box_corners]),
                                     max([v.y for v in bounding_box_corners]),
                                     max([v.z for v in bounding_box_corners])))
                size = max_corner - min_corner

                if axis == "X":
                    displacement = Vector((size[0] / 2.0, 0, 0))
                    obj.location = current_position + displacement
                    current_position += Vector((size[0] + distance, 0, 0))
                elif axis == "Y":
                    displacement = Vector((0, size[1] / 2.0, 0))
                    obj.location = current_position + displacement
                    current_position += Vector((0, size[1] + distance, 0))
                elif axis == "Z":
                    displacement = Vector((0, 0, size[2] / 2.0))
                    obj.location = current_position + displacement
                    current_position += Vector((0, 0, size[2] + distance))
            else:
                if axis == "X":
                    obj.location = current_position
                    current_position[0] += distance
                elif axis == "Y":
                    obj.location = current_position
                    current_position[1] += distance
                elif axis == "Z":
                    obj.location = current_position
                    current_position[2] += distance

        return {"FINISHED"}# 创建父级空物体
    
# 获取物体的顶级父物体
def get_top_parent(obj):
    while obj.parent:
        obj = obj.parent
    return obj

# 计算所有选中物体的包围盒
def calculate_bounding_box(objects):
    bbox_corners = [obj.matrix_world @ Vector(corner) for obj in objects for corner in obj.bound_box]
    min_corner = Vector((min(corner[i] for corner in bbox_corners) for i in range(3)))
    max_corner = Vector((max(corner[i] for corner in bbox_corners) for i in range(3)))
    return min_corner, max_corner

# 计算物体底部中心位置
def calculate_bottom_center(min_corner, max_corner):
    return Vector((
        (max_corner.x + min_corner.x) / 2,
        (max_corner.y + min_corner.y) / 2,
        min_corner.z  # 取最底部
    ))

# 向目标集合中添加空物体
def link_empty(obj_collection, empty_name, location):
    empty = bpy.data.objects.new(empty_name, None)
    obj_collection.objects.link(empty)
    empty.location = location
    return empty

class CreateEmptyAtObjectBottom(bpy.types.Operator):
    bl_idname = "object.mian_create_empty_at_bottom"
    bl_label = "在选中物体底部创建父级空物体"
    bl_description = "在所选物体的底部位置创建空物体作为父级，用于组织物体层级"

    def execute(self, context):
        multiple_object_binding = context.scene.multiple_object_binding
        selected_objects = bpy.context.selected_objects

        # 提前计算好包围盒和底部中心
        if multiple_object_binding:
            # 获取所有选中物体的顶级父物体
            top_parents = [get_top_parent(obj) for obj in selected_objects]
            # 计算所有顶级父物体的包围盒
            min_corner, max_corner = calculate_bounding_box(top_parents)
            # 计算所有物体的底部中心
            location = calculate_bottom_center(min_corner, max_corner)

            # 创建一个空物体，放置在所有物体的底部中心
            multiple_empty = link_empty(context.collection, 'multiple_objects_empty', location)

            # 对每个物体进行父级设置
            for top_parent in top_parents:
                self.set_parent_to_empty(top_parent, multiple_empty)

        else:
            for obj in selected_objects:
                top_parent = get_top_parent(obj)
                obj_collection = top_parent.users_collection[0]
                empty_name = top_parent.name + '_empty'

                # 计算包围盒和底部中心
                min_corner, max_corner = calculate_bounding_box([top_parent])
                location = calculate_bottom_center(min_corner, max_corner)

                # 创建空物体
                empty = link_empty(obj_collection, empty_name, location)
                self.set_parent_to_empty(top_parent, empty)

        return {'FINISHED'}

    def set_parent_to_empty(self, obj, empty):
        # 保存原来的矩阵世界
        initial_matrix_world = obj.matrix_world.copy()

        # 清除选择，避免每次都反复选择物体
        bpy.ops.object.select_all(action='DESELECT')

        # 选择空物体和目标物体
        empty.select_set(True)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = empty

        # 设置父级关系
        bpy.ops.object.parent_set(type="OBJECT", keep_transform=True)

        # 恢复物体的世界矩阵
        obj.matrix_world = initial_matrix_world


# 按距离划分编组并绑定最高的物体为父级
class CollectionByDistance(bpy.types.Operator):
    bl_idname = "object.mian_collection_bydistance"
    bl_label = "按距离划分编组并绑定最高的物体为父级"

    def execute(self, context):

        # 获取选定的物体并将其存储在变量中
        selected_objects = bpy.context.selected_objects

        # 将物体分组
        collections = []
        for obj in selected_objects:
            assigned = False
            for collection in collections:
                if all((obj.matrix_world.translation - member.matrix_world.translation).length < 40 for member in collection.objects):
                    collection.objects.link(obj)
                    assigned = True
                    break
            if not assigned:
                new_collection = bpy.data.collections.new("Collection")
                bpy.context.scene.collection.children.link(new_collection)
                new_collection.objects.link(obj)
                collections.append(new_collection)

        # 为每个集合选择父级
        for collection in collections:
            parent = max(collection.objects, key=lambda x: x.location.z)
            for obj in collection.objects:
                if obj != parent:
                    obj.parent = parent
                    obj.matrix_local = parent.matrix_world.inverted() @ obj.matrix_world

        # 输出父级信息
        for obj in selected_objects:
            if obj.parent is not None:
                print(obj.name, "is a child of", obj.parent.name)

#检测碰撞并且合并：
class CollectionByAttached(bpy.types.Operator):
    bl_idname = "object.collection_by_attached"
    bl_label = "接触合并"
    bl_description = "检测接触的物体并将它们合并到同一个集合中"

    def execute(self, context):
        def create_bounding_box_vectors(obj):
            bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            return bbox_corners

        def check_bounding_box_collision(obj1, obj2):
            if obj1 == obj2:
                return False

            bbox1 = create_bounding_box_vectors(obj1)
            bbox2 = create_bounding_box_vectors(obj2)

            obj1_min_x, obj1_max_x = min(bbox1, key=lambda coord: coord.x)[0], max(bbox1, key=lambda coord: coord.x)[0]
            obj1_min_y, obj1_max_y = min(bbox1, key=lambda coord: coord.y)[1], max(bbox1, key=lambda coord: coord.y)[1]
            obj1_min_z, obj1_max_z = min(bbox1, key=lambda coord: coord.z)[2], max(bbox1, key=lambda coord: coord.z)[2]

            obj2_min_x, obj2_max_x = min(bbox2, key=lambda coord: coord.x)[0], max(bbox2, key=lambda coord: coord.x)[0]
            obj2_min_y, obj2_max_y = min(bbox2, key=lambda coord: coord.y)[1], max(bbox2, key=lambda coord: coord.y)[1]
            obj2_min_z, obj2_max_z = min(bbox2, key=lambda coord: coord.z)[2], max(bbox2, key=lambda coord: coord.z)[2]

            return (
                obj1_min_x <= obj2_max_x and obj1_max_x >= obj2_min_x
                and obj1_min_y <= obj2_max_y and obj1_max_y >= obj2_min_y
                and obj1_min_z <= obj2_max_z and obj1_max_z >= obj2_min_z
            )

        def merge_objects(objects):
            bpy.ops.object.select_all(action='DESELECT')

            for obj in objects:
                obj.select_set(True)
            
            bpy.context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()

        def group_colliding_objects(selected_objects):
            object_groups = []

            def find_existing_group(obj, groups):
                for group in groups:
                    if obj in group:
                        return group
                return None

            def merge_groups(obj1, obj2, groups):
                group1 = find_existing_group(obj1, groups)
                group2 = find_existing_group(obj2, groups)

                if group1 and group2:
                    if group1 != group2:
                        group1.update(group2)
                        groups.remove(group2)
                elif group1:
                    group1.add(obj2)
                elif group2:
                    group2.add(obj1)
                else:
                    new_group = {obj1, obj2}
                    groups.append(new_group)

            for obj1 in selected_objects:
                for obj2 in selected_objects:
                    if obj1 == obj2:
                        continue
                    if check_bounding_box_collision(obj1, obj2):
                        merge_groups(obj1, obj2, object_groups)

            return object_groups

        selected_objects = bpy.context.selected_objects
        colliding_object_groups = group_colliding_objects(selected_objects)

        for group in colliding_object_groups:
            merge_objects(list(group))

        if colliding_object_groups:
            self.report({'INFO'}, "Objects have been merged.")
            return {'FINISHED'}
        else:
            self.report({'INFO'}, "No colliding objects found.")
            return {'CANCELLED'}

# 碰撞检测（Boundbox）并打组
class CollectionByBoundingbox(bpy.types.Operator):
    bl_idname = "object.mian_collection_byboundingbox"
    bl_label = "检测碰撞归为一个集合（无法撤回请及时保存）"
    bl_description = "检测包围盒碰撞的物体并将它们归入同一个集合中"

    def execute(self, context):

        def create_bounding_box_vectors(obj):
            bbox_corners = [obj.matrix_world @
                            Vector(corner) for corner in obj.bound_box]
            return bbox_corners

        def check_bounding_box_collision(obj1, obj2):
            if obj1 == obj2:
                return False

            bbox1 = create_bounding_box_vectors(obj1)
            bbox2 = create_bounding_box_vectors(obj2)

            obj1_min_x, obj1_max_x = min(bbox1, key=lambda coord: coord.x)[
                0], max(bbox1, key=lambda coord: coord.x)[0]
            obj1_min_y, obj1_max_y = min(bbox1, key=lambda coord: coord.y)[
                1], max(bbox1, key=lambda coord: coord.y)[1]
            obj1_min_z, obj1_max_z = min(bbox1, key=lambda coord: coord.z)[
                2], max(bbox1, key=lambda coord: coord.z)[2]

            obj2_min_x, obj2_max_x = min(bbox2, key=lambda coord: coord.x)[
                0], max(bbox2, key=lambda coord: coord.x)[0]
            obj2_min_y, obj2_max_y = min(bbox2, key=lambda coord: coord.y)[
                1], max(bbox2, key=lambda coord: coord.y)[1]
            obj2_min_z, obj2_max_z = min(bbox2, key=lambda coord: coord.z)[
                2], max(bbox2, key=lambda coord: coord.z)[2]

            return (
                obj1_min_x <= obj2_max_x and obj1_max_x >= obj2_min_x
                and obj1_min_y <= obj2_max_y and obj1_max_y >= obj2_min_y
                and obj1_min_z <= obj2_max_z and obj1_max_z >= obj2_min_z
            )

        def create_collection(coll_name, objects):
            coll = bpy.data.collections.get(coll_name)
            if not coll:
                coll = bpy.data.collections.new(coll_name)
                bpy.context.scene.collection.children.link(coll)
            for obj in objects:
                current_collections = obj.users_collection
                coll.objects.link(obj)
                for current_coll in current_collections:
                    current_coll.objects.unlink(obj)

        def group_colliding_objects(selected_objects):
            object_groups = []

            def find_existing_group(obj, groups):
                for group in groups:
                    if obj in group:
                        return group
                return None

            def merge_groups(obj1, obj2, groups):
                group1 = find_existing_group(obj1, groups)
                group2 = find_existing_group(obj2, groups)

                if group1 and group2:
                    if group1 != group2:
                        group1.update(group2)
                        groups.remove(group2)
                elif group1:
                    group1.add(obj2)
                elif group2:
                    group2.add(obj1)
                else:
                    new_group = {obj1, obj2}
                    groups.append(new_group)

            for obj1 in selected_objects:
                for obj2 in selected_objects:
                    if obj1 == obj2:
                        continue
                    if check_bounding_box_collision(obj1, obj2):
                        merge_groups(obj1, obj2, object_groups)

            return object_groups

        selected_objects = bpy.context.selected_objects
        colliding_object_groups = group_colliding_objects(selected_objects)

        for i, group in enumerate(colliding_object_groups, 1):
            collection_name = f"Collision_Group_{i}"
            create_collection(collection_name, group)

        if colliding_object_groups:
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

#vox导入处理
class VoxOperation(bpy.types.Operator):
    bl_idname = "object.vox_operation"
    bl_label = "vox角色处理"
    bl_description = "导入VOX文件并进行一键处理，包括材质设置和优化"

    def execute(self, context):

        # bpy.ops.object.mian_apply_and_sparate()
        bpy.ops.object.reset_normals_flat_shading()
        # bpy.ops.object.merge_vertices_operator()

        return {'FINISHED'}

# 碰撞检测（Boundbox）并创建父级
class ParentByBoundingbox(bpy.types.Operator):
    bl_idname = "object.mian_parent_byboundingbox"
    bl_label = "检测碰撞归为一个子集"
    bl_description = "检测包围盒碰撞的物体并创建父级关系，将碰撞的物体设为子物体"

    def execute(self, context):
        def create_bounding_box_vectors(obj):
            bbox_corners = [obj.matrix_world @
                            Vector(corner) for corner in obj.bound_box]
            return bbox_corners

        def check_bounding_box_collision(obj1, obj2):
            if obj1 == obj2:
                return False

            bbox1 = create_bounding_box_vectors(obj1)
            bbox2 = create_bounding_box_vectors(obj2)

            obj1_min_x, obj1_max_x = min(bbox1, key=lambda coord: coord.x)[
                0], max(bbox1, key=lambda coord: coord.x)[0]
            obj1_min_y, obj1_max_y = min(bbox1, key=lambda coord: coord.y)[
                1], max(bbox1, key=lambda coord: coord.y)[1]
            obj1_min_z, obj1_max_z = min(bbox1, key=lambda coord: coord.z)[
                2], max(bbox1, key=lambda coord: coord.z)[2]

            obj2_min_x, obj2_max_x = min(bbox2, key=lambda coord: coord.x)[
                0], max(bbox2, key=lambda coord: coord.x)[0]
            obj2_min_y, obj2_max_y = min(bbox2, key=lambda coord: coord.y)[
                1], max(bbox2, key=lambda coord: coord.y)[1]
            obj2_min_z, obj2_max_z = min(bbox2, key=lambda coord: coord.z)[
                2], max(bbox2, key=lambda coord: coord.z)[2]

            return (
                obj1_min_x <= obj2_max_x and obj1_max_x >= obj2_min_x
                and obj1_min_y <= obj2_max_y and obj1_max_y >= obj2_min_y
                and obj1_min_z <= obj2_max_z and obj1_max_z >= obj2_min_z
            )

        def calculate_group_center(group):
            if not group:
                return Vector((0, 0, 0))

            # 初始化最小和最大向量
            min_coord = Vector((float('inf'), float('inf'), float('inf')))
            max_coord = Vector((-float('inf'), -float('inf'), -float('inf')))

            # 对每个物体的边界框的每个角进行迭代，更新最小和最大坐标
            for obj in group:
                bbox_corners = create_bounding_box_vectors(obj)
                for corner in bbox_corners:
                    min_coord.x = min(min_coord.x, corner.x)
                    min_coord.y = min(min_coord.y, corner.y)
                    min_coord.z = min(min_coord.z, corner.z)

                    max_coord.x = max(max_coord.x, corner.x)
                    max_coord.y = max(max_coord.y, corner.y)
                    max_coord.z = max(max_coord.z, corner.z)

            # 计算并返回最小和最大坐标的平均值
            center = (min_coord + max_coord) * 0.5
            return center
        
        # 获取所有mesh对象
        all_mesh_objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
        bounding_boxes = {obj: create_bounding_box_vectors(obj) for obj in all_mesh_objects}

        def find_colliding_objects(obj, objects):
            """找到与指定对象碰撞的所有对象"""
            colliding_objects = []
            for other in objects:
                if obj != other and check_bounding_box_collision(obj, other):
                    colliding_objects.append(other)
            return colliding_objects

        def group_colliding(obj, grouped_objects, remaining_objects):
            """递归地寻找碰撞对象，并将它们放入同一组"""
            colliding = find_colliding_objects(obj, remaining_objects)
            for coll_obj in colliding:
                if coll_obj not in grouped_objects:
                    grouped_objects.add(coll_obj)
                    remaining_objects.remove(coll_obj)
                    # 继续传递 bounding_boxes 参数
                    group_colliding(coll_obj, grouped_objects, remaining_objects)
        
        # 根据新的起点对象递归寻找碰撞组
        colliding_groups = []
        while all_mesh_objects:
            starting_object = all_mesh_objects.pop()
            current_group = {starting_object}
            group_colliding(starting_object, current_group, all_mesh_objects)
            colliding_groups.append(current_group)
            
        # 创建父对象
        for group in colliding_groups:
            # 取消选择所有物体
            bpy.ops.object.select_all(action='DESELECT')
            
            # 选择当前组中的所有物体
            for obj in group:
                obj.select_set(True)
            
            # 需要设置活跃对象以确保操作运行无误
            if group:  # 如果组非空
                context.view_layer.objects.active = next(iter(group))
            
            # 调用自定义操作，这里假设 `mian_create_empty_at_bottom` 正常工作
            bpy.ops.object.mian_create_empty_at_bottom()

        return {'FINISHED' if colliding_groups else 'CANCELLED'}

#角色一键处理（绑骨骼）
bpy.types.Scene.assign_contact_weights = bpy.props.BoolProperty(
        name="是否赋予权重",
        default=False,
        )
bpy.types.Scene.threshold_distance = bpy.props.FloatProperty(
    name="接触判定阈值",
    description="Set the threshold distance for contact weight calculation",
    default=0.1,
    min=0.0,
    step=0.1,
    precision=2
)

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


class BoundboxGen(bpy.types.Operator):
    bl_idname = "object.mian_boundbox_gen"
    bl_label = "生成包围盒"
    bl_description = "为所选物体生成包围盒，创建立方体网格包围所选物体"

    def execute(self, context):
        def get_local_bounding_box(obj):
            return [mathutils.Vector(corner) for corner in obj.bound_box]

        def get_world_coordinates(corner, obj):
            """将局部坐标转换为世界坐标。"""
            return obj.matrix_world @ corner

        def create_box_from_local_bounding_box(obj):
            # 获取局部坐标系的边界框
            local_bounding_box = get_local_bounding_box(obj)

            # 计算最小和最大的局部XYZ坐标
            min_xyz = mathutils.Vector(
                (min(v.x for v in local_bounding_box),
                min(v.y for v in local_bounding_box),
                min(v.z for v in local_bounding_box))
            )
            max_xyz = mathutils.Vector(
                (max(v.x for v in local_bounding_box),
                max(v.y for v in local_bounding_box),
                max(v.z for v in local_bounding_box))
            )

            # 计算局部中心点和尺寸
            local_center = (min_xyz + max_xyz) / 2
            local_size = max_xyz - min_xyz

            # 考虑物体缩放
            scaled_size = local_size * obj.scale

            # 计算世界坐标系下的中心
            world_center = get_world_coordinates(local_center, obj)

            # 创建新的网格和物体
            mesh = bpy.data.meshes.new(name=(obj.name + "_box"))
            bm = bmesh.new()

            # 创建一个1m³的单位立方体
            bmesh.ops.create_cube(bm, size=1.0, calc_uvs=False)

            # 将bmesh转换为mesh并清理
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

            # 创建物体
            box = bpy.data.objects.new(name=(obj.name + "_box"), object_data=mesh)

            # 设置世界坐标的位置和旋转
            box.location = world_center
            box.rotation_euler = obj.rotation_euler

            # 按照缩放调整，以1m³单位为基础的尺寸
            box.scale = scaled_size

            # 将包围盒添加到场景中
            bpy.context.collection.objects.link(box)

            return box

            
        if bpy.context.selected_objects:
            for obj in bpy.context.selected_objects:
                create_box_from_local_bounding_box(obj)
        else:
            print("没有选择物体")

        return {'FINISHED'}
    
# 选择合并，不破坏集合关系
class CombinObject(bpy.types.Operator):
    bl_idname = "object.mian_safecombin"
    bl_label = "安全合并（不破坏集合）"

    def execute(self, context):

        # 定义一个函数用于合并物体
        def merge_objects(objs, target_collection, new_name):
            # 取消所有选中物体
            bpy.ops.object.select_all(action='DESELECT')

            # 选择 objs 中的物体并设置活动物体
            for obj in objs:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = objs[0]

            # 合并物体
            bpy.ops.object.join()

            # 获取合并后的物体
            merged_object = bpy.context.active_object

            # 对合并后的物体重命名，并移到目标集合
            merged_object.name = new_name
            merged_object.users_collection[0].objects.unlink(merged_object)
            target_collection.objects.link(merged_object)

            return merged_object

        # 获取选中的物体
        selected_objects = bpy.context.selected_objects

        # 按自身所在的集合分组物体
        grouped_objects = collections.defaultdict(list)
        for obj in selected_objects:
            grouped_objects[obj.users_collection[0]].append(obj)

        # 遍历按集合分组的物体
        merged_objects = []
        for collection, objects in grouped_objects.items():

            # 合并物体，并保持在原本的集合中
            new_obj_name = f"Merged_{collection.name}_object"
            merged_object = merge_objects(objects, collection, new_obj_name)
            merged_objects.append(merged_object)

        # 取消原来的选中，选择合并后的物体
        for obj in selected_objects:
            obj.select_set(False)
        for obj in merged_objects:
            obj.select_set(True)

# 移除选中物体的顶点组
class RemoveVertexGroup(bpy.types.Operator):
    bl_idname = "object.mian_remove_vertex_group"
    bl_label = "移除选中物体的顶点组"

    def execute(self, context):

        # 获取当前选择的物体
        selected_objects = bpy.context.selected_objects
        # 批量移除所选物体的顶点组
        for obj in selected_objects:
            # 确保所选物体类型为 MESH
            if obj.type == 'MESH':
                # 直接从 obj.vertex_groups 中删除顶点组
                while obj.vertex_groups:
                    obj.vertex_groups.remove(obj.vertex_groups[0])

        # 减少成功消息的打印频率
        if not hasattr(self, '_vertex_group_removed_printed'):
            print("顶点组已成功移除！")
            self._vertex_group_removed_printed = True
        return {'FINISHED'}

# 移除选中物体中空的顶点组
class RemoveEmptyVertexGroups(bpy.types.Operator):
    bl_idname = "object.mian_remove_empty_vertex_groups"
    bl_label = "移除选中物体中空的顶点组"
    bl_description = "移除选中物体中权重为0或没有顶点的空顶点组"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        total_removed = 0
        affected_objects = 0
        
        if not selected_objects:
            self.report({'WARNING'}, "请先选择要处理的物体")
            return {'CANCELLED'}
        
        for obj in selected_objects:
            if obj.type == 'MESH' and obj.vertex_groups:
                removed_count = 0
                
                # 从后往前遍历顶点组，避免删除时索引变化的问题
                for i in range(len(obj.vertex_groups) - 1, -1, -1):
                    vg = obj.vertex_groups[i]
                    is_empty = True
                    
                    # 检查顶点组是否为空
                    if obj.data.vertices:
                        for vertex in obj.data.vertices:
                            # 检查顶点是否属于这个顶点组且有权重
                            for group in vertex.groups:
                                if group.group == vg.index and group.weight > 0:
                                    is_empty = False
                                    break
                            if not is_empty:
                                break
                    
                    # 如果顶点组为空，则删除
                    if is_empty:
                        obj.vertex_groups.remove(vg)
                        removed_count += 1
                
                if removed_count > 0:
                    total_removed += removed_count
                    affected_objects += 1
                    print(f"✅ 物体 '{obj.name}' 移除了 {removed_count} 个空顶点组")
        
        if affected_objects > 0:
            self.report({'INFO'}, f"已从 {affected_objects} 个物体中移除 {total_removed} 个空顶点组")
        else:
            self.report({'INFO'}, "没有找到空的顶点组")
        
        return {'FINISHED'}

# 对齐原点
class AlignOrign(bpy.types.Operator):
    bl_idname = "object.mian_align_orign"
    bl_label = "对齐原点（需要勾选仅影响原点）"

    def execute(self, context):

        def align_origin(axis='X', objects=None):

            axis_map = {'X': 0, 'Y': 1, 'Z': 2}
            axis_index = axis_map[axis]

            if objects is None:
                objects = bpy.context.selected_objects

            min_origin_coord = None

            # 搜索所选物体中原点坐标值最小的对象
            for obj in objects:
                if obj.type == 'MESH':
                    origin_coordinate = obj.matrix_world.translation
                    if min_origin_coord is None or origin_coordinate[axis_index] < min_origin_coord:
                        min_origin_coord = origin_coordinate[axis_index]

            for obj in objects:
                if obj.type == 'MESH':
                    difference = min_origin_coord - \
                        obj.matrix_world.translation[axis_index]

                    previous_affect_pivot_point = bpy.context.tool_settings.use_transform_pivot_point_align
                    bpy.context.tool_settings.use_transform_pivot_point_align = True

                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.context.view_layer.objects.active = obj
                    obj.select_set(True)

                    bpy.ops.object.mode_set(mode='OBJECT')
                    bpy.ops.transform.translate(value=(
                        difference if axis == 'X' else 0, difference if axis == 'Y' else 0, difference if axis == 'Z' else 0))

                    bpy.context.tool_settings.use_transform_pivot_point_align = previous_affect_pivot_point

        # 调用函数 - 对齐所选物体的X轴原点
        align_origin('X')

#一键提升精度
class MoveOutsideOperator(bpy.types.Operator):
    bl_idname = "object.move_outside_operator"
    bl_label = "校正旋转"
    
    def execute(self, context):
        obj=context.active_object
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        radians=math.radians(90)
        obj.rotation_euler.x-=radians
        obj.rotation_euler.y-=radians
        obj.rotation_euler.y-=radians 
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.rotation_euler.x+=radians
        bpy.ops.object.select_all(action='DESELECT')
        return {"FINISHED"}

class FixSizeOperator(bpy.types.Operator):
    bl_idname = "object.fix_size_operator"
    bl_label = "提升精度"
    
    def execute(self, context):
        outermost_obj = context.active_object
        if outermost_obj is not None:
            outermost_obj.scale *= 0.0001 
            for child_obj in outermost_obj.children:
                child_obj.scale *= 10000
                child_obj.location *= 10000
        return {"FINISHED"}

# 批量标记资产功能已移至 AssetMarker.py

#批量更改子级名称为顶级父级，忽略隐藏物体
class RenameByParent(bpy.types.Operator):
    bl_idname = "object.mian_rename_by_parent"
    bl_label = "更改所选物体为其顶级名称"
    bl_description = "将所选子物体的名称更改为其顶级父物体的名称"

    def execute(self, context):

        def rename_selected_objects_with_sequential_suffixes():
            def get_sequential_suffix(name_base, current_number):
                return f"{name_base}.{current_number:03d}"

            # 获取所有已选择的物体
            all_objects = bpy.data.objects
            selected_objects = bpy.context.selected_objects

            # 遍历所有已选择的物体
            for obj in selected_objects:
                # 检查物体是否有父级，并获得物体的顶级父级
                if obj.parent is None:
                    continue
                top_parent = obj.parent
                while top_parent.parent is not None:
                    top_parent = top_parent.parent

                # 检查物体是否在视口中隐藏，如果是，则跳过
                if obj.hide_viewport:
                    continue

                # 移除顶级父级物体名称的数字后缀
                top_parent_name_no_suffix = top_parent.name.split('.')[0]
                top_parent.name = top_parent_name_no_suffix

                # 获取顶级父级物体的直接子物体
                direct_children = [
                    child for child in selected_objects if child.parent == top_parent]

                # 为顶级父级物体的直接子物体分配连贯的数字后缀
                for index, child in enumerate(direct_children, start=1):
                    new_name = get_sequential_suffix(
                        top_parent_name_no_suffix, index)
                    child.name = new_name

        # 在 Blender 中执行该函数
        rename_selected_objects_with_sequential_suffixes()
        return {"FINISHED"}

# 添加center和distance函数定义
def distance(vecA, vecB):
    return (vecA - vecB).length

def center(collection):
    centers = []
    for obj in collection.objects:
        if obj.type == 'MESH':
            world_vertex_coordinates = [obj.matrix_world @ v.co for v in obj.data.vertices]
            center = sum(world_vertex_coordinates, Vector()) / len(world_vertex_coordinates) if world_vertex_coordinates else Vector()
            centers.append(center)
    return sum(centers, Vector()) / len(centers) if centers else Vector()

#按照集合位置划分绑定父级
def set_nearest_parent_for_collection(self, context):
    collectionA = context.scene.collectionA
    collectionB = context.scene.collectionB
    collections_in_B = [coll for coll in collectionB.children]
    top_level_objs_in_A = [obj for obj in collectionA.objects if obj.parent is None]

    for collB in collections_in_B:
        collB_center = center(collB)
        closest_top_objA = min(top_level_objs_in_A, key=lambda objA: distance(collB_center, objA.location))
        for objB in collB.objects:
            closest_top_objA.select_set(True) 
            context.view_layer.objects.active = closest_top_objA
            objB.select_set(True)
            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
            closest_top_objA.select_set(False) 
            objB.select_set(False)
            collB.name = closest_top_objA.name

# ----       
class OBJECT_OT_SetParentButton(bpy.types.Operator):
    bl_idname = "object.mian_set_parent_collections"
    bl_label = "Set Parent Collections"
    bl_description = "根据目标集合中最接近的物体设置集合的父级关系"

    def execute(self, context):
        set_nearest_parent_for_collection(self, context)
        return {'FINISHED'}
    
#按照集合对齐顶级父级
class OBJECT_OT_AlignOperator(bpy.types.Operator):
    bl_idname = "object.align_operator"
    bl_label = "集合父级批量对齐"
    bl_description = "将目标集合中的顶级父物体与参考集合中最近的物体对齐"
    
    def execute(self, context):
        def get_all_top_level_objects(collection):
            top_objects = [obj for obj in collection.objects if obj.parent is None]
            return top_objects

        def strip_suffix(name):
            return name.split(".")[0]
        collection_a = context.scene.collectionA
        collection_b = context.scene.collectionB

        # To get all top-level objects in collection A and B
        top_objects_a = get_all_top_level_objects(collection_a)
        top_objects_b = get_all_top_level_objects(collection_b)

        # Move each top-level object in Collection B to match position of top-level object in Collection A with same name
        for parent_a in top_objects_a:
            for obj_b in top_objects_b:
                obj_name = strip_suffix(obj_b.name)
                if strip_suffix(parent_a.name) == obj_name:

                    # Store child object's world matrix
                    old_world_matrices = {child: child.matrix_world.copy() for child in obj_b.children}

                    # Set object's location to match with parent_a
                    obj_b.matrix_world = parent_a.matrix_world

                    # Restore the world matrix of the child objects
                    for child in obj_b.children:
                        child.matrix_world = old_world_matrices[child]

        self.report({'INFO'}, "对集合进行了位置对齐")
        return {'FINISHED'}

#根据uv进行选择面
def get_selected_uv_set(ob):
    uv_set = set()   # 创建一个空集合来存储UV数据

    bm = bmesh.new()
    bm.from_mesh(ob.data)

    if bm.loops.layers.uv:  # Check if the object has UV data
        uv_layer = bm.loops.layers.uv.active  # 获取物体的UV层 
        for face in bm.faces:
            for loop in face.loops:    # 获取每个面的环
                uv_set.add(loop[uv_layer].uv.to_tuple())

    return uv_set

# 检查两个UV集合是否相等
def uv_sets_equal(set_a, set_b):
    return set_a == set_b
  
# 相比单独的脚本，插件的不同之处在于需要定义一个操作并注册这个操作
class UVObjectMatcherOperator(bpy.types.Operator):
    bl_idname = "object.match_uv"
    bl_label = "选取同uv物体"
    bl_description = "选择与当前活动物体具有相同UV坐标的物体"

    def execute(self, context):
        selected_object = context.active_object
        if selected_object is None or selected_object.type != 'MESH':
            return {"CANCELLED"}

        selected_object_uv_set = get_selected_uv_set(selected_object)
  
        for obj in context.view_layer.objects:
            if obj.type == 'MESH' and obj != selected_object:  # 忽略非网格物体及活动物体
                obj_uv_set = get_selected_uv_set(obj)

                if uv_sets_equal(selected_object_uv_set, obj_uv_set):
                    obj.select_set(True)
                else:
                    obj.select_set(False)

        return {"FINISHED"}

# 重置所选矢量
class ResetNormals(bpy.types.Operator):
    bl_idname = "object.mian_reset_normals"
    bl_label = "重置所选矢量"

    def execute(self, context):
        # 获取当前激活的物体
        active_object = bpy.context.active_object
        # 如果当前没有激活物体，从对象列表中选中第一个物体并将其设为活跃物体
        if active_object is None:
            first_object = bpy.context.selectable_objects[0] if bpy.context.selectable_objects else None

            if first_object is not None:
                first_object.select_set(True)
                bpy.context.view_layer.objects.active = first_object
                active_object = first_object

        # 检查当前激活的物体是否为 Mesh 类型
        if active_object is not None and active_object.type == 'MESH':

            # 使当前物体处于编辑模式
            bpy.ops.object.editmode_toggle()
            # 确保所有顶点被选中
            bpy.ops.mesh.select_all(action='SELECT')
            # 重置法线矢量
            bpy.ops.mesh.normals_tools(mode='RESET')
            # 返回物体模式
            bpy.ops.object.editmode_toggle()

        else:
            print("当前没有活跃 Mesh 类型物体，请确保您有可选择的 Mesh 物体。")

        return {"FINISHED"}

class ResetNormalsAndFlatShadingOperator(bpy.types.Operator):
    bl_idname = "object.reset_normals_flat_shading"
    bl_label = "Reset Normals and Flat Shading"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = bpy.context.selected_objects

        for obj in selected_objects:
            # 如果当前物体的类型不是 'MESH'，那么就跳过后续处理
            if obj.type != 'MESH':
                continue
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles(threshold=0.0001)
            bpy.ops.object.mode_set(mode='OBJECT')
            print(f"合并顶点成功：{obj}")

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.normals_tools(mode='RESET')
            bpy.ops.object.mode_set(mode='OBJECT')
            print(f"重置矢量成功：{obj}")

            obj_data = obj.data
            if obj_data.materials:
                for mat in obj_data.materials:
                    for poly in obj_data.polygons:
                        poly.use_smooth = False

        return {'FINISHED'}

# 合并顶级层级
class MergeTopLevel(bpy.types.Operator):
  bl_idname = "object.mian_merge_top_level"
  bl_label = "合并顶级层级"
  bl_description = "将所选物体的顶级层级进行合并，简化物体结构"

  def execute(self, context):

    selected_objs = context.selected_objects

    def merge_objects(objects, parent):
        bpy.ops.object.select_all(action='DESELECT')

        for obj in objects:
            # Creates a unique copy of object data
            bpy.data.objects[obj.name].data = obj.data.copy()
            obj.select_set(True)
            context.view_layer.objects.active = obj

        # Apply transforms before merging
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Merge selected objects using built-in command
        bpy.ops.object.join()

        merged_obj = context.object
        merged_obj.name = f"{parent.name}_merged"
        merged_obj.parent = parent

        bpy.ops.object.select_all(action='DESELECT')
        merged_obj.select_set(True)

    for obj in selected_objs:
        parent = obj.parent 
        matrix_world = obj.matrix_world.copy()

        while parent and parent.parent:
            obj.parent = parent.parent
            parent = parent.parent

        if parent:
            obj.parent = parent

        obj.matrix_world = matrix_world

    top_parents = set()
    for obj in selected_objs:
        if obj.parent:
            top_parents.add(obj.parent)

    for parent in top_parents:
        children = [child for child in parent.children 
                if child in selected_objs and child.type=='MESH']

        if len(children) > 1:
            merge_objects(children, parent)

    return {'FINISHED'}

class ApplyAndSeparate(bpy.types.Operator):
    bl_idname = "object.mian_apply_and_separate"
    bl_label = "独立化、应用所有变换"
    bl_description = "将所选物体独立化并应用所有变换，确保物体数据独立"

    def execute(self, context):
        # 获取当前所选物体和具有负缩放的物体列表
        selected_objects = context.selected_objects
        # 减少操作开始消息的打印频率
        if not hasattr(self, '_operation_started_printed'):
            print(f"开始执行操作，选中了 {len(selected_objects)} 个物体。")
            self._operation_started_printed = True
        
        negatively_scaled_objects = set()

        # 在每个对象中检测负缩放
        for obj in selected_objects:
            self.detect_negative_scale(obj, negatively_scaled_objects)
        
        # 独立化、应用变换
        for obj in selected_objects:
            self.separate_and_apply(obj)
        
        # 翻转面朝向
        for obj_name in negatively_scaled_objects:
            if obj_name in bpy.data.objects:
                self.reverse_normals(bpy.data.objects[obj_name])

        print("操作完成。")
        return {'FINISHED'}

    def detect_negative_scale(self, obj, negatively_scaled_objects):
        # 忽略空物体
        if obj.type == 'EMPTY':
            return

        # 检查是否存在负值缩放
        if any(s < 0 for s in obj.scale):
            print(f"检测到负缩放: {obj.name}")
            negatively_scaled_objects.add(obj.name)

        # 递归检查子对象
        for child in obj.children:
            self.detect_negative_scale(child, negatively_scaled_objects)

    def separate_and_apply(self, obj):
        context = bpy.context
        context.view_layer.objects.active = obj
        obj.select_set(True)

        # 确保我们在对象模式
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 独立对象
        bpy.ops.object.make_single_user(
            object=True, obdata=True, material=False, animation=False, obdata_animation=False)

        # 应用所有变换
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    
    def reverse_normals(self, obj):
        # 确保只影响目标对象
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # 进入对象的编辑模式
        if bpy.context.object.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        # 选择所有的面并翻转法线
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.flip_normals()

        # 返回对象模式
        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"已翻转法线: {obj.name}")

# 清理空物体
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
        ####

# 递归清理场景
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

# 批量关联目录内所有blender文件场景
class SCENE_OT_link_scenes_from_blend_files(bpy.types.Operator):
    bl_idname = "scene.link_scenes_batch"
    bl_label = "从选定目录中的.blend文件批量关联场景"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        bpy.types.Scene.export_directory = bpy.props.StringProperty(
            name="Export Directory",
            description="Directory where the exported files will be written"
        )

        directory = context.scene.export_directory

        # 检查路径是否有效，同时兼容使用相对路径
        if directory.startswith('//'):
            directory = bpy.path.abspath(directory)

        if not os.path.exists(directory):
            self.report({'ERROR'}, f"目录 '{directory}' 不存在。")
            return {'CANCELLED'}

        for filename in os.listdir(directory):
            if filename.endswith(".blend"):
                blend_filepath = os.path.join(directory, filename)
                with bpy.data.libraries.load(blend_filepath, link=True) as (data_from, data_to):
                    data_to.scenes = data_from.scenes

                for scene in data_to.scenes:
                    if scene is not None:
                        bpy.context.window.scene = scene
                        bpy.context.view_layer.update()
                        message = f"已关联场景 '{scene.name}' 来自 '{blend_filepath}'."
                        print(message)
                        self.report({'INFO'}, message)
                    else:
                        message = f"'{blend_filepath}' 中没有场景可以关联."
                        print(message)
                        self.report({'INFO'}, message)

        return {'FINISHED'}

# 排序场景列表
class SCENE_OT_sort_scenes(bpy.types.Operator):
    bl_idname = "scene.sort_scenes"
    bl_label = "按名称排序场景"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene_list = list(bpy.data.scenes)

        def natural_sort_key(s):
            return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', s)]

        # 使用自然排序对场景列表进行排序
        sorted_names = sorted(
            [scene.name for scene in scene_list], key=natural_sort_key)

        for scene, new_name in zip(scene_list, sorted_names):
            scene.name = new_name

        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'OUTLINER':
                    area.tag_redraw()

        return {'FINISHED'}

# 场景批量添加至时间轴
class SCENE_OT_add_sorted_scenes_to_sequencer(bpy.types.Operator):
    bl_idname = "scene.add_sorted_scenes_to_sequencer"
    bl_label = "将已排序的场景添加到序列编辑器"
    bl_options = {'REGISTER', 'UNDO'}

    def atoi(self, text):
        return int(text) if text.isdigit() else text

    def natural_keys(self, text):
        return [self.atoi(c) for c in re.split(r'(\d+)', text)]

    def execute(self, context):
        bpy.context.window.workspace = bpy.data.workspaces['Video Editing']
        bpy.ops.sequencer.select_all(action='DESELECT')
        bpy.ops.sequencer.delete()

        scene = bpy.context.scene
        sequencer = scene.sequence_editor

        if sequencer is None:
            sequencer = scene.sequence_editor_create()

        start_frame = 1
        for scene_to_add in sorted(bpy.data.scenes, key=lambda s: self.natural_keys(s.name)):
            if scene_to_add == scene:
                continue

            scene_strip = sequencer.sequences.new_scene(
                name=scene_to_add.name, scene=scene_to_add, channel=1, frame_start=start_frame)
            start_frame += scene_strip.frame_final_duration

        return {'FINISHED'}

# 下落至表面
class OBJECT_OT_move_to_surface(bpy.types.Operator):
    bl_idname = "object.move_to_surface"
    bl_label = "下落至表面"
    bl_description = "将所选物体沿指定方向移动，直到与场景中的其他物体表面接触"
    bl_options = {'REGISTER', 'UNDO'}

    def create_tree_from_object(self, obj):
        bm = bmesh.new()
        bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
        bm.transform(obj.matrix_world)
        bvh = BVHTree.FromBMesh(bm)
        bm.free()
        return bvh

    def get_bbox_bottom_center(self, obj):
        local_bbox = obj.bound_box
        dimensions = obj.dimensions
        bbox_bottom_center = sum((Vector(v) for v in local_bbox), Vector()) / 8
        bbox_bottom_center.z = min(v[2] for v in local_bbox)
        return bbox_bottom_center

    def get_contact_point(self, target_tree, sel_obj):
        bbox_bottom_center = self.get_bbox_bottom_center(sel_obj)
        world_bbox_bottom_center = sel_obj.matrix_world @ bbox_bottom_center
        direction = Vector((0, 0, -1))

        co, normal, _, _ = target_tree.ray_cast(
            world_bbox_bottom_center + direction * 0.001, direction, 1000)

        if co is not None:
            displacement = co.z - world_bbox_bottom_center.z
            return displacement

        return 0

    def move_to_surface(self, target_tree, scene, sel_obj):
        displacement = self.get_contact_point(target_tree, sel_obj)
        if displacement != 0:
            sel_obj.location.z += displacement

    def execute(self, context):
        selected_objects = context.selected_objects
        scene = context.scene

        if len(selected_objects) < 2:
            self.report({"ERROR"}, "选择至少两个物体，一个作为参考物体，其余为要移动的物体。")
            return {"CANCELLED"}

        target_obj = context.active_object
        moving_objects = [o for o in selected_objects if o is not target_obj]

        target_tree = self.create_tree_from_object(target_obj)

        for obj in moving_objects:
            self.move_to_surface(target_tree, scene, obj)

        return {"FINISHED"}

# 批量创建顶点组运算符
class BatchCreateVertexGroup(bpy.types.Operator):
    bl_idname = "object.batch_create_vertex_group"
    bl_label = "批量创建顶点组"
    bl_description = "为所选物体创建指定名称的顶点组，并将所有顶点写入"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取顶点组名称
        vertex_group_name = context.scene.vertex_group_name
        
        if not vertex_group_name.strip():
            self.report({'WARNING'}, "请输入顶点组名称")
            return {'CANCELLED'}
        
        # 获取当前选择的物体
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个物体")
            return {'CANCELLED'}
        
        # 统计处理的物体数量
        processed_count = 0
        
        for obj in selected_objects:
            # 确保物体类型为MESH
            if obj.type == 'MESH':
                # 检查是否已存在同名顶点组
                existing_group = None
                for vg in obj.vertex_groups:
                    if vg.name == vertex_group_name:
                        existing_group = vg
                        break
                
                # 如果不存在，创建新的顶点组
                if existing_group is None:
                    existing_group = obj.vertex_groups.new(name=vertex_group_name)
                
                # 获取网格数据
                mesh = obj.data
                
                # 确保网格有顶点
                if len(mesh.vertices) > 0:
                    # 创建顶点索引列表（所有顶点）
                    vertex_indices = list(range(len(mesh.vertices)))
                    
                    # 为所有顶点分配权重1.0
                    existing_group.add(vertex_indices, 1.0, 'REPLACE')
                    
                    processed_count += 1
        
        if processed_count > 0:
            self.report({'INFO'}, f"成功为 {processed_count} 个物体创建顶点组 '{vertex_group_name}'")
        else:
            self.report({'WARNING'}, "没有找到可处理的网格物体")
        
        return {'FINISHED'}

# 对齐物体原点操作符
class AlignObjectOriginOperator(bpy.types.Operator):
    bl_idname = "object.align_object_origin"
    bl_label = "对齐物体原点"
    bl_description = "将次选物体的原点对齐到主选物体上，同时保证mesh位置不变"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """通过顶点组合并拆分方法对齐原点"""
        
        # 获取选中的物体
        selected_objects = context.selected_objects
        
        if len(selected_objects) < 2:
            self.report({'WARNING'}, "请至少选择两个物体：一个作为主选物体，其余作为次选物体")
            return {'CANCELLED'}
        
        main_object = context.active_object
        secondary_objects = [obj for obj in selected_objects if obj != main_object]
        
        if not main_object:
            self.report({'WARNING'}, "请选择一个主选物体")
            return {'CANCELLED'}
        
        if not secondary_objects:
            self.report({'WARNING'}, "请选择至少一个次选物体")
            return {'CANCELLED'}
        
        # 记录副选物体名称和mesh名称
        secondary_names = [obj.name for obj in secondary_objects]
        secondary_mesh_names = [obj.data.name for obj in secondary_objects]
        
        # 记录副选物体的集合位置和父级关系
        secondary_collections = []
        secondary_parents = []
        secondary_world_matrices = []
        
        # 记录主选物体的材质信息
        main_materials = []
        main_material_slot_count = len(main_object.material_slots)
        for slot in main_object.material_slots:
            if slot.material:
                main_materials.append(slot.material.name)
            else:
                main_materials.append(None)
        
        # 记录副选物体的材质信息
        secondary_materials = []
        secondary_material_slot_counts = []
        for obj in secondary_objects:
            obj_materials = []
            for slot in obj.material_slots:
                if slot.material:
                    obj_materials.append(slot.material.name)
                else:
                    obj_materials.append(None)
            secondary_materials.append(obj_materials)
            secondary_material_slot_counts.append(len(obj.material_slots))
        
        # 记录副选物体的UV层名称
        secondary_uv_layer_names = []
        for obj in secondary_objects:
            uv_layer_names = []
            if obj.data.uv_layers:
                for uv_layer in obj.data.uv_layers:
                    uv_layer_names.append(uv_layer.name)
            secondary_uv_layer_names.append(uv_layer_names)
        
        for obj in secondary_objects:
            # 记录集合位置
            obj_collections = [col for col in bpy.data.collections if obj in col.objects.values()]
            secondary_collections.append(obj_collections)
            
            # 记录父级关系
            secondary_parents.append(obj.parent)
            
            # 记录世界空间变换矩阵
            secondary_world_matrices.append(obj.matrix_world.copy())
        
        # 记录原始活动物体
        original_active_object = context.active_object
        
        try:
            # 逐个处理每个副选物体
            for i, secondary_obj in enumerate(secondary_objects):
                # 为当前副选物体的所有顶点创建一个临时顶点组，全部加入，名称为Merge
                bpy.context.view_layer.objects.active = secondary_obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 创建顶点组
                vertex_group = secondary_obj.vertex_groups.new(name="Merge")
                bpy.ops.object.vertex_group_assign()
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # 将当前副选物体合并至主选物体
                bpy.ops.object.select_all(action='DESELECT')
                secondary_obj.select_set(True)
                main_object.select_set(True)
                bpy.context.view_layer.objects.active = main_object
                
                bpy.ops.object.join()
                merged_object = bpy.context.active_object
                
                # 主选物体进入编辑模式先取消所有选择，之后选取Merge顶点组的顶点
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                
                # 找到Merge顶点组并选择
                merge_vertex_group = None
                for vg in merged_object.vertex_groups:
                    if vg.name == "Merge":
                        merge_vertex_group = vg
                        break
                
                if merge_vertex_group:
                    merged_object.vertex_groups.active_index = merge_vertex_group.index
                    bpy.ops.object.vertex_group_select()
                else:
                    continue
                
                # 拆分选取部分
                bpy.ops.mesh.separate(type='SELECTED')
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # 重命名拆分出的物体
                all_objects = bpy.context.selected_objects
                split_objects = [obj for obj in all_objects if obj != main_object]
                
                if split_objects:
                    split_obj = split_objects[0]  # 取第一个拆分出的物体
                    original_name = secondary_names[i]
                    original_mesh_name = secondary_mesh_names[i]
                    original_collections = secondary_collections[i]
                    original_parent = secondary_parents[i]
                    original_world_matrix = secondary_world_matrices[i]
                    original_materials = secondary_materials[i]
                    original_material_slot_count = secondary_material_slot_counts[i]
                    original_uv_layer_names = secondary_uv_layer_names[i]
                    
                    # 恢复物体名称
                    split_obj.name = original_name
                    # 恢复mesh名称
                    split_obj.data.name = original_mesh_name
                    
                    # 恢复材质信息
                    # 移除多余的材质插槽，只保留原始数量
                    while len(split_obj.data.materials) > original_material_slot_count:
                        split_obj.data.materials.pop()
                    
                    # 如果插槽数量不足，添加空插槽
                    while len(split_obj.data.materials) < original_material_slot_count:
                        split_obj.data.materials.append(None)
                    
                    # 重新添加原始材质到对应插槽
                    for j, material_name in enumerate(original_materials):
                        if j < original_material_slot_count:
                            if material_name and material_name in bpy.data.materials:
                                split_obj.data.materials[j] = bpy.data.materials[material_name]
                            else:
                                split_obj.data.materials[j] = None
                    
                    # 删除多余的UV层，只保留原始的UV层
                    if original_uv_layer_names and split_obj.data.uv_layers:
                        # 获取当前所有UV层名称
                        current_uv_layers = [uv_layer.name for uv_layer in split_obj.data.uv_layers]
                        
                        # 删除不在原始UV层列表中的UV层
                        for uv_layer_name in current_uv_layers:
                            if uv_layer_name not in original_uv_layer_names:
                                # 找到要删除的UV层
                                for j, uv_layer in enumerate(split_obj.data.uv_layers):
                                    if uv_layer.name == uv_layer_name:
                                        split_obj.data.uv_layers.remove(uv_layer)
                                        break
                    
                    # 恢复集合位置
                    # 先从主选物体的集合中移除拆分出的物体
                    main_object_collections = [col for col in bpy.data.collections if main_object in col.objects.values()]
                    for col in main_object_collections:
                        if split_obj in col.objects.values():
                            col.objects.unlink(split_obj)
                    
                    # 然后添加到原始集合中
                    for col in original_collections:
                        if split_obj not in col.objects.values():
                            col.objects.link(split_obj)
                    
                    # 恢复父级关系并保持世界空间变换不变
                    if original_parent:
                        # 先解除当前父级关系（如果有的话）
                        if split_obj.parent:
                            # 记录当前世界空间变换
                            current_world_matrix = split_obj.matrix_world.copy()
                            # 解除父级关系
                            split_obj.parent = None
                            # 保持世界空间变换不变
                            split_obj.matrix_world = current_world_matrix
                        
                        # 设置新的父级关系
                        split_obj.parent = original_parent
                        # 保持世界空间变换不变
                        split_obj.matrix_world = original_world_matrix
                    else:
                        # 如果没有父级，先解除当前父级关系（如果有的话）
                        if split_obj.parent:
                            # 记录当前世界空间变换
                            current_world_matrix = split_obj.matrix_world.copy()
                            # 解除父级关系
                            split_obj.parent = None
                            # 保持世界空间变换不变
                            split_obj.matrix_world = current_world_matrix
                        else:
                            # 直接设置世界空间变换
                            split_obj.matrix_world = original_world_matrix
                    
                    # 删除临时Merge顶点组
                    # 删除主选物体中的Merge顶点组
                    merge_vertex_group = None
                    for vg in merged_object.vertex_groups:
                        if vg.name == "Merge":
                            merge_vertex_group = vg
                            break
                    
                    if merge_vertex_group:
                        merged_object.vertex_groups.remove(merge_vertex_group)
                    
                    # 删除拆分出物体中的Merge顶点组
                    merge_vertex_group = None
                    for vg in split_obj.vertex_groups:
                        if vg.name == "Merge":
                            merge_vertex_group = vg
                            break
                    
                    if merge_vertex_group:
                        split_obj.vertex_groups.remove(merge_vertex_group)
            
                # 恢复主选物体的材质槽数量
                while len(merged_object.data.materials) > main_material_slot_count:
                    merged_object.data.materials.pop()
                
                while len(merged_object.data.materials) < main_material_slot_count:
                    merged_object.data.materials.append(None)
                
                # 恢复主选物体的材质
                for j, material_name in enumerate(main_materials):
                    if j < main_material_slot_count:
                        if material_name and material_name in bpy.data.materials:
                            merged_object.data.materials[j] = bpy.data.materials[material_name]
                        else:
                            merged_object.data.materials[j] = None
                
                # 恢复原始活动物体
                bpy.context.view_layer.objects.active = original_active_object
                
                self.report({'INFO'}, f"已将 {len(secondary_objects)} 个次选物体的原点对齐到主选物体")
                return {'FINISHED'}
            
        except Exception as e:
            # 恢复原始活动物体
            bpy.context.view_layer.objects.active = original_active_object
            self.report({'ERROR'}, f"对齐过程中发生错误: {str(e)}")
            return {'CANCELLED'}

classes = [
    OBJECT_OT_reset_z_axis,
    ParentByBoundingbox,
    OBJECT_OT_make_single_user,
    OBJECT_OT_convex_hull_creator,
    VoxelConverter,
    CollectionByAttached,
    RemoveModifiers,
    RemoveConstraints,
    SimplifyCurveToEndpoints,
    VoxOperation,
    ResetNormalsAndFlatShadingOperator,
    OBJECT_OT_AlignOperator,
    MoveOutsideOperator,
    FixSizeOperator,
    OBJECT_OT_SetParentButton,
    ClearAnimationData,
    OBJECT_OT_move_to_surface,
    SCENE_OT_add_sorted_scenes_to_sequencer,
    SCENE_OT_sort_scenes,
    SCENE_OT_link_scenes_from_blend_files,
    CleanSense,
    CleanEmpty,
    MergeTopLevel,
    ApplyAndSeparate,
    ResetNormals,
    CollectionByDistance,
    CleanCollection,
    BoundboxGen,
    CombinObject,
    RemoveVertexGroup,
    RemoveEmptyVertexGroups,
    QueueUp,
    RandomPlacement,
    CollectionByBoundingbox,
    AlignOrign,
    CreateEmptyAtObjectBottom,
    RenameByParent,
    RandomScale,
    RandomRotation,
    UVObjectMatcherOperator,
    ObjectInstancer,
    GeometryMatcherOperator,
    RemoveInstanceDuplicatesOperator,
    BatchCreateVertexGroup,
    AlignObjectOriginOperator,
]

def register():
    bpy.types.Scene.rename_axis = EnumProperty(
        name="轴向",
        items=[
            ("X", "X轴", "按X轴顺序重命名"),
            ("Y", "Y轴", "按Y轴顺序重命名"),
            ("Z", "Z轴", "按Z轴顺序重命名")
        ],
        default="Y"
    )
    bpy.types.Scene.rename_order = bpy.props.EnumProperty(
        name="排序类型",
        items=[
            ("ASC", "正序", "按正序重新命名"),
            ("DESC", "倒序", "按倒序重新命名")
        ],
        default="ASC"
    )
    bpy.types.Scene.random_placement_extent = bpy.props.FloatVectorProperty(
        name="范围大小",
        description="设置随机放置的范围大小",
        default=(10, 10, 10),
        size=3
    )
    
    # 随机缩放属性
    bpy.types.Scene.random_scale_extent_x = bpy.props.FloatVectorProperty(
        name="X轴缩放范围(min, max)",
        description="设置X轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    bpy.types.Scene.random_scale_extent_y = bpy.props.FloatVectorProperty(
        name="Y轴缩放范围(min, max)",
        description="设置Y轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    bpy.types.Scene.random_scale_extent_z = bpy.props.FloatVectorProperty(
        name="Z轴缩放范围(min, max)",
        description="设置Z轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    
    # 随机旋转属性
    bpy.types.Scene.random_rotation_extent_x = bpy.props.FloatProperty(
        name="X轴旋转范围(度)",
        description="设置X轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )
    bpy.types.Scene.random_rotation_extent_y = bpy.props.FloatProperty(
        name="Y轴旋转范围(度)",
        description="设置Y轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )
    bpy.types.Scene.random_rotation_extent_z = bpy.props.FloatProperty(
        name="Z轴旋转范围(度)",
        description="设置Z轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )

    bpy.types.Scene.multiple_object_binding = bpy.props.BoolProperty(
        name="Multiple Object Binding",
        description="为多个物体创建单个空物体父级",
        default=True)
    bpy.types.Scene.link_scenes_batch_directory = bpy.props.StringProperty(
        name="目录",
        description="包含 .blend 文件的目录",
        subtype='DIR_PATH',
        maxlen=1024
    )
    bpy.types.Scene.tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.GTAtranslate_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.BindOperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.meterialoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.assestoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.renameoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.rsm_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.inout_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.renderadj_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.collectionA = PointerProperty(name="Collection A", type=bpy.types.Collection)
    bpy.types.Scene.collectionB = PointerProperty(name="Collection B", type=bpy.types.Collection)
    bpy.types.Scene.export_directory = bpy.props.StringProperty(
        name="导出路径",
        description="设置导出FBX文件的路径",
        default="",
        maxlen=1024,
        subtype='DIR_PATH')
    bpy.types.Scene.autorender_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.collectionA = PointerProperty(type=Collection)
    bpy.types.Scene.collectionB = PointerProperty(type=Collection)
    bpy.types.Scene.resolution_factor = bpy.props.IntProperty(
        name="分辨率因子",
        description="定义体素化时使用的分辨率乘数",
        default=32,
        min=1
    )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass  # 类已经注册，忽略该异常

def is_class_registered(cls):
    return hasattr(cls, "bl_rna")

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass  # 类未注册，忽略该异常
    del bpy.types.Scene.collectionB
    del bpy.types.Scene.collectionA
    del bpy.types.Scene.random_placement_extent
    del bpy.types.Scene.random_scale_extent_x
    del bpy.types.Scene.random_scale_extent_y
    del bpy.types.Scene.random_scale_extent_z
    del bpy.types.Scene.random_rotation_extent_x
    del bpy.types.Scene.random_rotation_extent_y
    del bpy.types.Scene.random_rotation_extent_z
    del bpy.types.Scene.rename_order
    del bpy.types.Scene.export_directory
    del bpy.types.Scene.multiple_object_binding
    del bpy.types.Scene.link_scenes_batch_directory
    del bpy.types.Scene.rename_axis
    del bpy.types.Scene.resolution_factor
    bpy.types.Scene.tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.GTAtranslate_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.BindOperation_expand = bpy.props.BoolProperty(
        default=False)
    bpy.types.Scene.meterialoperation_expand = bpy.props.BoolProperty(
        default=False)
    bpy.types.Scene.assestoperation_expand = bpy.props.BoolProperty(
        default=False)
    bpy.types.Scene.renameoperation_expand = bpy.props.BoolProperty(
        default=False)
    bpy.types.Scene.rsm_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.inout_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.renderadj_expand = bpy.props.BoolProperty(default=False)

