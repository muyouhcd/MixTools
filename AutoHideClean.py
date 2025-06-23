import bpy
import bmesh
import math
from bpy.props import BoolProperty
from bpy.types import Operator
import mathutils
from mathutils import Vector, Matrix
import bpy_extras
from bpy_extras.object_utils import world_to_camera_view

class AutoHideCleanOperator(Operator):
    bl_idname = "object.auto_hide_clean"
    bl_label = "创建AutoHidden集合并隐藏"
    bl_description = "检查每一帧镜头，将拍摄不到的物体放入AutoHidden集合并隐藏"
    
    def execute(self, context):
        # 获取当前场景
        scene = context.scene
        
        # 检查是否有相机
        if not scene.camera:
            self.report({'ERROR'}, "场景中没有设置相机")
            return {'CANCELLED'}
        
        # 检查是否有动画帧
        if scene.frame_start == scene.frame_end:
            self.report({'WARNING'}, "场景中没有动画帧，将只检查当前帧")
        
        # 创建或获取AutoHidden集合
        auto_hidden_collection = self.get_or_create_collection("AutoHidden")
        
        # 获取所有网格物体
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.visible_get()]
        
        if not mesh_objects:
            self.report({'WARNING'}, "场景中没有可见的网格物体")
            return {'CANCELLED'}
        
        # 存储需要隐藏的物体
        objects_to_hide = set()
        
        # 检查每一帧
        original_frame = scene.frame_current
        frame_range = range(scene.frame_start, scene.frame_end + 1)
        
        for frame in frame_range:
            scene.frame_set(frame)
            self.report({'INFO'}, f"正在检查第 {frame} 帧...")
            
            # 检查当前帧中不可见的物体
            hidden_in_frame = self.check_frame_visibility(scene, mesh_objects)
            objects_to_hide.update(hidden_in_frame)
        
        # 恢复原始帧
        scene.frame_set(original_frame)
        
        # 将物体移动到AutoHidden集合
        moved_count = 0
        for obj in objects_to_hide:
            if obj.name in bpy.data.objects:  # 确保物体仍然存在
                # 从原集合中移除
                for collection in obj.users_collection:
                    collection.objects.unlink(obj)
                
                # 添加到AutoHidden集合
                auto_hidden_collection.objects.link(obj)
                moved_count += 1
        
        # 隐藏AutoHidden集合
        auto_hidden_collection.hide_viewport = True
        auto_hidden_collection.hide_render = True
        
        self.report({'INFO'}, f"已将 {moved_count} 个物体移动到AutoHidden集合并隐藏")
        return {'FINISHED'}
    
    def get_or_create_collection(self, collection_name):
        """创建或获取指定名称的集合"""
        if collection_name in bpy.data.collections:
            return bpy.data.collections[collection_name]
        else:
            new_collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(new_collection)
            return new_collection
    
    def check_frame_visibility(self, scene, mesh_objects):
        """检查当前帧中哪些物体不可见"""
        camera = scene.camera
        hidden_objects = set()
        
        # 获取相机参数
        camera_matrix = camera.matrix_world
        camera_data = camera.data
        
        # 检查每个网格物体
        for obj in mesh_objects:
            if not self.is_object_visible_to_camera(obj, camera, camera_matrix, camera_data, mesh_objects):
                hidden_objects.add(obj)
        
        return hidden_objects
    
    def is_object_visible_to_camera(self, obj, camera, camera_matrix, camera_data, all_objects):
        """检查物体是否对相机可见"""
        # 检查物体是否在相机视野内
        if not self.is_object_in_camera_frustum(obj, camera_matrix, camera_data):
            return False
        
        # 检查物体是否被其他物体遮挡
        if self.is_object_occluded(obj, camera, all_objects):
            return False
        
        return True
    
    def is_object_in_camera_frustum(self, obj, camera_matrix, camera_data):
        """检查物体是否在相机视锥体内"""
        # 获取物体的边界框
        bbox_corners = self.get_object_bbox_corners(obj)
        
        # 将边界框转换到相机空间
        camera_space_corners = []
        for corner in bbox_corners:
            camera_space_corner = camera_matrix.inverted() @ corner
            camera_space_corners.append(camera_space_corner)
        
        # 检查是否在视锥体内
        for corner in camera_space_corners:
            # 检查Z轴（深度）
            if corner.z > 0:  # 在相机后面
                continue
            
            # 检查X和Y轴（视野范围）
            if camera_data.type == 'PERSP':
                # 透视相机
                fov_x = camera_data.angle_x
                fov_y = camera_data.angle_y
                
                # 计算视野范围
                max_x = abs(corner.z) * math.tan(fov_x / 2)
                max_y = abs(corner.z) * math.tan(fov_y / 2)
                
                if abs(corner.x) <= max_x and abs(corner.y) <= max_y:
                    return True
            else:
                # 正交相机
                ortho_scale = camera_data.ortho_scale
                max_x = ortho_scale / 2
                max_y = ortho_scale / 2
                
                if abs(corner.x) <= max_x and abs(corner.y) <= max_y:
                    return True
        
        return False
    
    def get_object_bbox_corners(self, obj):
        """获取物体的边界框角点"""
        bbox_corners = []
        
        # 获取物体的边界框
        bbox_min = obj.bound_box[0]
        bbox_max = obj.bound_box[6]
        
        # 计算8个角点
        corners = [
            (bbox_min[0], bbox_min[1], bbox_min[2]),
            (bbox_max[0], bbox_min[1], bbox_min[2]),
            (bbox_max[0], bbox_max[1], bbox_min[2]),
            (bbox_min[0], bbox_max[1], bbox_min[2]),
            (bbox_min[0], bbox_min[1], bbox_max[2]),
            (bbox_max[0], bbox_min[1], bbox_max[2]),
            (bbox_max[0], bbox_max[1], bbox_max[2]),
            (bbox_min[0], bbox_max[1], bbox_max[2])
        ]
        
        # 转换到世界空间
        obj_matrix = obj.matrix_world
        for corner in corners:
            world_corner = obj_matrix @ Vector(corner)
            bbox_corners.append(world_corner)
        
        return bbox_corners
    
    def is_object_occluded(self, obj, camera, all_objects):
        """检查物体是否被其他物体完全遮挡（严格版本）"""
        # 获取物体中心点
        obj_center = obj.matrix_world @ Vector((0, 0, 0))
        camera_pos = camera.matrix_world @ Vector((0, 0, 0))
        
        # 获取物体的边界框角点作为采样点
        bbox_corners = self.get_object_bbox_corners(obj)
        
        # 检查所有采样点，如果所有点都被遮挡，则认为物体完全被遮挡
        total_points = len(bbox_corners) + 1  # +1 for center point
        occluded_points = 0
        
        # 检查中心点
        if self.is_point_occluded(obj_center, camera_pos, all_objects, obj):
            occluded_points += 1
        
        # 检查边界框角点
        for corner in bbox_corners:
            if self.is_point_occluded(corner, camera_pos, all_objects, obj):
                occluded_points += 1
        
        # 只有当所有点都被遮挡时，才认为物体完全被遮挡
        return occluded_points == total_points
    
    def is_point_occluded(self, point, camera_pos, all_objects, exclude_obj):
        """检查单个点是否被遮挡"""
        direction = (point - camera_pos).normalized()
        point_distance = (point - camera_pos).length
        
        # 检查是否有其他物体在射线路径上且距离更近
        for other_obj in all_objects:
            if other_obj == exclude_obj:
                continue
            
            # 检查其他物体的边界框是否在射线路径上
            if self.ray_intersects_bbox(camera_pos, direction, other_obj):
                # 计算遮挡物体的最近距离
                other_bbox_corners = self.get_object_bbox_corners(other_obj)
                min_other_distance = float('inf')
                
                # 找到遮挡物体中距离相机最近的点
                for corner in other_bbox_corners:
                    corner_distance = (corner - camera_pos).length
                    if corner_distance < min_other_distance:
                        min_other_distance = corner_distance
                
                # 如果遮挡物体的最近点比目标点更近，则认为该点被遮挡
                if min_other_distance < point_distance:
                    return True
        
        return False
    
    def ray_intersects_bbox(self, ray_origin, ray_direction, obj):
        """检查射线是否与物体的边界框相交"""
        # Get world-aligned AABB of the object
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        world_bbox_min = Vector((min(c.x for c in bbox_corners), min(c.y for c in bbox_corners), min(c.z for c in bbox_corners)))
        world_bbox_max = Vector((max(c.x for c in bbox_corners), max(c.y for c in bbox_corners), max(c.z for c in bbox_corners)))

        # Kay/Kajiya slab method for ray-AABB intersection
        t_near = -math.inf
        t_far = math.inf

        for i in range(3): # for x, y, z axes
            if ray_direction[i] == 0:
                if ray_origin[i] < world_bbox_min[i] or ray_origin[i] > world_bbox_max[i]:
                    return False  # Ray is parallel to slab and outside
            else:
                t1 = (world_bbox_min[i] - ray_origin[i]) / ray_direction[i]
                t2 = (world_bbox_max[i] - ray_origin[i]) / ray_direction[i]

                if t1 > t2:
                    t1, t2 = t2, t1  # Ensure t1 is intersection with near plane

                if t1 > t_near:
                    t_near = t1

                if t2 < t_far:
                    t_far = t2

                if t_near > t_far:  # Box is missed
                    return False
        
        # Box is intersected, if t_far < 0, intersection is behind the ray's origin
        if t_far < 0:
            return False

        return True


class AutoHideDeleteOperator(Operator):
    bl_idname = "object.auto_hide_delete"
    bl_label = "直接删除不可见物体"
    bl_description = "检查每一帧镜头，直接删除拍摄不到的物体"
    
    def execute(self, context):
        # 获取当前场景
        scene = context.scene
        
        # 检查是否有相机
        if not scene.camera:
            self.report({'ERROR'}, "场景中没有设置相机")
            return {'CANCELLED'}
        
        # 检查是否有动画帧
        if scene.frame_start == scene.frame_end:
            self.report({'WARNING'}, "场景中没有动画帧，将只检查当前帧")
        
        # 获取所有网格物体
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.visible_get()]
        
        if not mesh_objects:
            self.report({'WARNING'}, "场景中没有可见的网格物体")
            return {'CANCELLED'}
        
        # 存储需要删除的物体
        objects_to_delete = set()
        
        # 检查每一帧
        original_frame = scene.frame_current
        frame_range = range(scene.frame_start, scene.frame_end + 1)
        
        for frame in frame_range:
            scene.frame_set(frame)
            self.report({'INFO'}, f"正在检查第 {frame} 帧...")
            
            # 检查当前帧中不可见的物体
            hidden_in_frame = self.check_frame_visibility(scene, mesh_objects)
            objects_to_delete.update(hidden_in_frame)
        
        # 恢复原始帧
        scene.frame_set(original_frame)
        
        # 删除不可见的物体
        deleted_count = 0
        for obj in objects_to_delete:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
                deleted_count += 1
        
        self.report({'INFO'}, f"已删除 {deleted_count} 个不可见物体")
        return {'FINISHED'}
    
    def check_frame_visibility(self, scene, mesh_objects):
        """检查当前帧中哪些物体不可见（复用AutoHideCleanOperator的方法）"""
        camera = scene.camera
        hidden_objects = set()
        
        # 获取相机参数
        camera_matrix = camera.matrix_world
        camera_data = camera.data
        
        # 检查每个网格物体
        for obj in mesh_objects:
            if not self.is_object_visible_to_camera(obj, camera, camera_matrix, camera_data, mesh_objects):
                hidden_objects.add(obj)
        
        return hidden_objects
    
    def is_object_visible_to_camera(self, obj, camera, camera_matrix, camera_data, all_objects):
        """检查物体是否对相机可见（复用AutoHideCleanOperator的方法）"""
        # 检查物体是否在相机视野内
        if not self.is_object_in_camera_frustum(obj, camera_matrix, camera_data):
            return False
        
        # 检查物体是否被其他物体遮挡
        if self.is_object_occluded(obj, camera, all_objects):
            return False
        
        return True
    
    def is_object_in_camera_frustum(self, obj, camera_matrix, camera_data):
        """检查物体是否在相机视锥体内（复用AutoHideCleanOperator的方法）"""
        # 获取物体的边界框
        bbox_corners = self.get_object_bbox_corners(obj)
        
        # 将边界框转换到相机空间
        camera_space_corners = []
        for corner in bbox_corners:
            camera_space_corner = camera_matrix.inverted() @ corner
            camera_space_corners.append(camera_space_corner)
        
        # 检查是否在视锥体内
        for corner in camera_space_corners:
            # 检查Z轴（深度）
            if corner.z > 0:  # 在相机后面
                continue
            
            # 检查X和Y轴（视野范围）
            if camera_data.type == 'PERSP':
                # 透视相机
                fov_x = camera_data.angle_x
                fov_y = camera_data.angle_y
                
                # 计算视野范围
                max_x = abs(corner.z) * math.tan(fov_x / 2)
                max_y = abs(corner.z) * math.tan(fov_y / 2)
                
                if abs(corner.x) <= max_x and abs(corner.y) <= max_y:
                    return True
            else:
                # 正交相机
                ortho_scale = camera_data.ortho_scale
                max_x = ortho_scale / 2
                max_y = ortho_scale / 2
                
                if abs(corner.x) <= max_x and abs(corner.y) <= max_y:
                    return True
        
        return False
    
    def get_object_bbox_corners(self, obj):
        """获取物体的边界框角点（复用AutoHideCleanOperator的方法）"""
        bbox_corners = []
        
        # 获取物体的边界框
        bbox_min = obj.bound_box[0]
        bbox_max = obj.bound_box[6]
        
        # 计算8个角点
        corners = [
            (bbox_min[0], bbox_min[1], bbox_min[2]),
            (bbox_max[0], bbox_min[1], bbox_min[2]),
            (bbox_max[0], bbox_max[1], bbox_min[2]),
            (bbox_min[0], bbox_max[1], bbox_min[2]),
            (bbox_min[0], bbox_min[1], bbox_max[2]),
            (bbox_max[0], bbox_min[1], bbox_max[2]),
            (bbox_max[0], bbox_max[1], bbox_max[2]),
            (bbox_min[0], bbox_max[1], bbox_max[2])
        ]
        
        # 转换到世界空间
        obj_matrix = obj.matrix_world
        for corner in corners:
            world_corner = obj_matrix @ Vector(corner)
            bbox_corners.append(world_corner)
        
        return bbox_corners
    
    def is_object_occluded(self, obj, camera, all_objects):
        """检查物体是否被其他物体完全遮挡（严格版本）"""
        # 获取物体中心点
        obj_center = obj.matrix_world @ Vector((0, 0, 0))
        camera_pos = camera.matrix_world @ Vector((0, 0, 0))
        
        # 获取物体的边界框角点作为采样点
        bbox_corners = self.get_object_bbox_corners(obj)
        
        # 检查所有采样点，如果所有点都被遮挡，则认为物体完全被遮挡
        total_points = len(bbox_corners) + 1  # +1 for center point
        occluded_points = 0
        
        # 检查中心点
        if self.is_point_occluded(obj_center, camera_pos, all_objects, obj):
            occluded_points += 1
        
        # 检查边界框角点
        for corner in bbox_corners:
            if self.is_point_occluded(corner, camera_pos, all_objects, obj):
                occluded_points += 1
        
        # 只有当所有点都被遮挡时，才认为物体完全被遮挡
        return occluded_points == total_points
    
    def is_point_occluded(self, point, camera_pos, all_objects, exclude_obj):
        """检查单个点是否被遮挡"""
        direction = (point - camera_pos).normalized()
        point_distance = (point - camera_pos).length
        
        # 检查是否有其他物体在射线路径上且距离更近
        for other_obj in all_objects:
            if other_obj == exclude_obj:
                continue
            
            # 检查其他物体的边界框是否在射线路径上
            if self.ray_intersects_bbox(camera_pos, direction, other_obj):
                # 计算遮挡物体的最近距离
                other_bbox_corners = self.get_object_bbox_corners(other_obj)
                min_other_distance = float('inf')
                
                # 找到遮挡物体中距离相机最近的点
                for corner in other_bbox_corners:
                    corner_distance = (corner - camera_pos).length
                    if corner_distance < min_other_distance:
                        min_other_distance = corner_distance
                
                # 如果遮挡物体的最近点比目标点更近，则认为该点被遮挡
                if min_other_distance < point_distance:
                    return True
        
        return False
    
    def ray_intersects_bbox(self, ray_origin, ray_direction, obj):
        """检查射线是否与物体的边界框相交"""
        # Get world-aligned AABB of the object
        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        world_bbox_min = Vector((min(c.x for c in bbox_corners), min(c.y for c in bbox_corners), min(c.z for c in bbox_corners)))
        world_bbox_max = Vector((max(c.x for c in bbox_corners), max(c.y for c in bbox_corners), max(c.z for c in bbox_corners)))

        # Kay/Kajiya slab method for ray-AABB intersection
        t_near = -math.inf
        t_far = math.inf

        for i in range(3): # for x, y, z axes
            if ray_direction[i] == 0:
                if ray_origin[i] < world_bbox_min[i] or ray_origin[i] > world_bbox_max[i]:
                    return False  # Ray is parallel to slab and outside
            else:
                t1 = (world_bbox_min[i] - ray_origin[i]) / ray_direction[i]
                t2 = (world_bbox_max[i] - ray_origin[i]) / ray_direction[i]

                if t1 > t2:
                    t1, t2 = t2, t1  # Ensure t1 is intersection with near plane

                if t1 > t_near:
                    t_near = t1

                if t2 < t_far:
                    t_far = t2

                if t_near > t_far:  # Box is missed
                    return False
        
        # Box is intersected, if t_far < 0, intersection is behind the ray's origin
        if t_far < 0:
            return False

        return True


def register():
    bpy.utils.register_class(AutoHideCleanOperator)
    bpy.utils.register_class(AutoHideDeleteOperator)

def unregister():
    bpy.utils.unregister_class(AutoHideDeleteOperator)
    bpy.utils.unregister_class(AutoHideCleanOperator)
