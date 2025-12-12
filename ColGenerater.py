import bpy
import bmesh
import math
from mathutils import Vector, Matrix, Quaternion

# 尝试导入numpy，如果不可用则使用备用方法
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from bpy.props import IntProperty, FloatProperty, BoolProperty, StringProperty
from bpy.types import Operator


class OBJECT_OT_generate_box_collision(Operator):
    """生成Box碰撞盒工具"""
    bl_idname = "object.generate_box_collision"
    bl_label = "生成Box碰撞盒"
    bl_description = "为选中的物体生成一系列box碰撞盒，每个box都是独立物体，具有自身的缩放和旋转"
    bl_options = {'REGISTER', 'UNDO'}

    # 属性定义
    detail_size: FloatProperty(
        name="细节值",
        description="体素尺寸（每个box的边长），也是最小box尺寸",
        default=0.1,
        min=0.001
    )
    
    use_voxel_method: BoolProperty(
        name="使用体素算法",
        description="使用体素算法生成碰撞盒，而不是基于面的方法",
        default=True
    )
    
    max_box_count: IntProperty(
        name="Box数量限制",
        description="最多生成的box数量，0表示不限制",
        default=0,
        min=0,
        max=10000
    )
    
    collection_name: StringProperty(
        name="集合名称",
        description="生成的碰撞盒将放入此集合（留空则使用默认集合）",
        default="CollisionBoxes"
    )

    @classmethod
    def poll(cls, context):
        """检查是否有选中的网格物体"""
        return context.selected_objects and any(
            obj.type == 'MESH' for obj in context.selected_objects
        )

    def execute(self, context):
        """执行生成碰撞盒操作"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个网格物体")
            return {'CANCELLED'}

        # 从场景属性读取参数（如果UI面板设置了这些属性）
        scene = context.scene
        if hasattr(scene, 'collision_box_detail_size'):
            self.detail_size = scene.collision_box_detail_size
        if hasattr(scene, 'collision_box_use_voxel'):
            self.use_voxel_method = scene.collision_box_use_voxel
        if hasattr(scene, 'collision_box_max_count'):
            self.max_box_count = scene.collision_box_max_count
        if hasattr(scene, 'collision_box_collection_name'):
            self.collection_name = scene.collision_box_collection_name

        # 创建或获取集合
        collection = None
        if self.collection_name:
            if self.collection_name in bpy.data.collections:
                collection = bpy.data.collections[self.collection_name]
            else:
                collection = bpy.data.collections.new(self.collection_name)
                context.scene.collection.children.link(collection)
        else:
            collection = context.collection

        total_boxes = 0
        
        for obj in selected_objects:
            try:
                # 检查是否已达到全局数量限制
                if self.max_box_count > 0 and total_boxes >= self.max_box_count:
                    break
                
                if self.use_voxel_method:
                    boxes_created = self.generate_voxel_collision_boxes(
                        context, obj, collection, total_boxes
                    )
                else:
                    boxes_created = self.generate_collision_boxes_for_object(
                        context, obj, collection, total_boxes
                    )
                total_boxes += boxes_created
            except Exception as e:
                self.report({'ERROR'}, f"处理物体 '{obj.name}' 时出错: {str(e)}")
                import traceback
                traceback.print_exc()

        self.report({'INFO'}, f"成功生成 {total_boxes} 个碰撞盒")
        return {'FINISHED'}

    def generate_collision_boxes_for_object(self, context, obj, collection, boxes_created_so_far=0):
        """为单个物体生成碰撞盒 - 基于面的生成方法
        
        Args:
            context: Blender上下文
            obj: 要处理的物体
            collection: 目标集合
            boxes_created_so_far: 已经创建的box数量（用于全局数量限制）
        """
        # 确保物体处于对象模式
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # 获取mesh数据（应用修改器）
        depsgraph = context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        
        # 创建bmesh用于mesh操作
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.transform(obj.matrix_world)  # 转换到世界空间
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        
        if len(bm.faces) == 0:
            bm.free()
            obj_eval.to_mesh_clear()
            return 0
        
        boxes_created = 0
        
        # 遍历每个面，为每个面生成一个box
        for face_idx, face in enumerate(bm.faces):
            # 检查是否达到全局数量限制（在开始处理面之前检查）
            total_boxes = boxes_created_so_far + boxes_created
            if self.max_box_count > 0 and total_boxes >= self.max_box_count:
                break
            
            # 获取面的法向量和中心
            face_normal = face.normal.copy()
            face_center = face.calc_center_median()
            
            # 获取面的所有顶点
            face_verts = [v.co.copy() for v in face.verts]
            
            if len(face_verts) < 3:
                continue
            
            # 计算面在局部坐标系中的边界（投影到面的平面上）
            # 创建局部坐标系：Z轴是法向量，X和Y轴在面内
            if abs(face_normal.dot(Vector((1, 0, 0)))) < 0.9:
                local_x = face_normal.cross(Vector((1, 0, 0)))
            else:
                local_x = face_normal.cross(Vector((0, 1, 0)))
            local_x.normalize()
            local_y = face_normal.cross(local_x)
            local_y.normalize()
            local_z = face_normal.copy()
            
            # 创建旋转矩阵（从局部坐标系到世界坐标系）
            rotation_matrix = Matrix([
                [local_x.x, local_y.x, local_z.x],
                [local_x.y, local_y.y, local_z.y],
                [local_x.z, local_y.z, local_z.z]
            ])
            
            # 将面的顶点投影到局部坐标系（面的平面）
            local_verts_2d = []
            for vert in face_verts:
                # 相对于面中心的向量
                rel_vec = vert - face_center
                # 投影到面的平面（X和Y方向）
                local_x_component = rel_vec.dot(local_x)
                local_y_component = rel_vec.dot(local_y)
                local_verts_2d.append(Vector((local_x_component, local_y_component)))
            
            # 计算面在局部坐标系中的2D边界
            min_x_2d = min(v.x for v in local_verts_2d)
            max_x_2d = max(v.x for v in local_verts_2d)
            min_y_2d = min(v.y for v in local_verts_2d)
            max_y_2d = max(v.y for v in local_verts_2d)
            
            # 计算面的尺寸
            face_size_x = max_x_2d - min_x_2d
            face_size_y = max_y_2d - min_y_2d
            
            # 检查面的尺寸是否小于阈值
            if face_size_x < self.detail_size or face_size_y < self.detail_size:
                continue
            
            # 计算面的中心在局部坐标系中的位置
            face_center_local_2d = Vector((
                (min_x_2d + max_x_2d) / 2,
                (min_y_2d + max_y_2d) / 2
            ))
            
            # 计算box的深度（沿法向量方向的厚度）
            # 目标：box的一个面与模型表面重合，其余面在模型内部
            
            # 方法：找到mesh中所有顶点，计算它们到这个面的距离
            # 找到在mesh内部（法向量反方向）的最大距离
            max_internal_depth = 0.0
            
            # 遍历所有顶点，计算到面的距离
            for vert in bm.verts:
                vert_pos = vert.co
                # 计算顶点到面的距离（带符号）
                rel_vec = vert_pos - face_center
                distance = rel_vec.dot(face_normal)
                
                # 只考虑在mesh内部的点（负距离表示在法向量反方向，即mesh内部）
                if distance < 0:  # 在mesh内部
                    depth = abs(distance)
                    if depth > max_internal_depth:
                        max_internal_depth = depth
            
            # box的深度是从面到mesh内部的最大距离
            # 如果深度太小，使用默认值
            box_depth = max(max_internal_depth, self.detail_size)
            
            # 计算box的中心（在面的平面上，但向mesh内部偏移深度的一半）
            # 这样box的一个面会与模型表面重合，另一个面在模型内部
            box_center_offset = face_normal * (box_depth / 2)
            box_center_world = face_center - box_center_offset  # 向mesh内部偏移
            
            # 计算box的尺寸
            box_size_x = face_size_x
            box_size_y = face_size_y
            box_size_z = box_depth
            
            # 检查最小尺寸
            if (box_size_x < self.detail_size or 
                box_size_y < self.detail_size or 
                box_size_z < self.detail_size):
                continue
            
            # 创建box物体
            bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
            box_obj = context.active_object
            box_obj.name = f"{obj.name}_CollisionBox_{face_idx}"
            box_obj.data.name = box_obj.name
            
            # 设置位置
            box_obj.location = box_center_world
            
            # 设置旋转（从旋转矩阵转换为欧拉角）
            box_obj.rotation_euler = rotation_matrix.to_euler()
            
            # 设置缩放
            box_obj.scale = (box_size_x, box_size_y, box_size_z)
            
            # 将box添加到集合
            if collection:
                collection.objects.link(box_obj)
                # 从默认集合中移除
                if box_obj.name in context.scene.collection.objects:
                    context.scene.collection.objects.unlink(box_obj)
            
            boxes_created += 1
        
        # 清理
        bm.free()
        obj_eval.to_mesh_clear()
        
        return boxes_created



def register():
    """注册操作符"""
    bpy.utils.register_class(OBJECT_OT_generate_box_collision)


def unregister():
    """注销操作符"""
    bpy.utils.unregister_class(OBJECT_OT_generate_box_collision)

