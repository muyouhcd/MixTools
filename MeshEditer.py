import bpy
import bmesh
from mathutils import Vector, Matrix
from bpy.props import IntProperty
from bpy.types import Operator


class OBJECT_OT_mesh_grid_cut_top_view(Operator):
    """从顶视图（Z轴视角）对物体进行网格状切分"""
    bl_idname = "object.mesh_grid_cut_top_view"
    bl_label = "顶视图网格切分"
    bl_description = "将指定物体以顶视图（Z轴视角）进行网格状切分，根据包围盒尺寸按段数切分"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """检查是否有选中的网格物体"""
        return context.selected_objects and any(
            obj.type == 'MESH' for obj in context.selected_objects
        )

    def execute(self, context):
        """执行网格切分操作"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个网格物体")
            return {'CANCELLED'}

        # 从场景属性获取切分段数
        x_segments = context.scene.mesh_grid_cut_x_segments
        y_segments = context.scene.mesh_grid_cut_y_segments
        
        if x_segments < 1 or y_segments < 1:
            self.report({'ERROR'}, "切分段数必须大于等于1")
            return {'CANCELLED'}

        processed_count = 0
        
        for obj in selected_objects:
            try:
                # 确保物体处于对象模式
                if obj.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                # 确保网格数据独立
                if obj.data.users > 1:
                    obj.data = obj.data.copy()
                
                # 获取物体的世界空间包围盒
                bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                
                # 计算包围盒在XY平面的范围
                min_x = min(corner.x for corner in bbox_corners)
                max_x = max(corner.x for corner in bbox_corners)
                min_y = min(corner.y for corner in bbox_corners)
                max_y = max(corner.y for corner in bbox_corners)
                
                # 计算包围盒范围
                x_range = max_x - min_x
                y_range = max_y - min_y
                
                if x_range < 0.001 or y_range < 0.001:
                    self.report({'WARNING'}, f"物体 '{obj.name}' 在XY平面上尺寸过小，跳过")
                    continue
                
                # 创建bmesh对象
                bm = bmesh.new()
                depsgraph = context.evaluated_depsgraph_get()
                
                # 从物体创建bmesh（自动应用修改器）
                bm.from_object(obj, depsgraph)
                
                # 应用物体的世界变换到bmesh（将局部坐标转换为世界坐标）
                bm.transform(obj.matrix_world)
                
                # 根据段数计算每段的尺寸
                x_segment_size = x_range / x_segments
                y_segment_size = y_range / y_segments
                
                # 计算切分线位置
                x_cuts = []
                y_cuts = []
                
                # X方向的切分线（垂直于X轴，沿Y方向）
                # 从第一段边界开始，到倒数第二段边界结束（不切分边界）
                for i in range(1, x_segments):
                    x_pos = min_x + i * x_segment_size
                    x_cuts.append(x_pos)
                
                # Y方向的切分线（垂直于Y轴，沿X方向）
                # 从第一段边界开始，到倒数第二段边界结束（不切分边界）
                for i in range(1, y_segments):
                    y_pos = min_y + i * y_segment_size
                    y_cuts.append(y_pos)
                
                # 获取Z轴中心位置（用于切分平面）
                min_z = min(corner.z for corner in bbox_corners)
                max_z = max(corner.z for corner in bbox_corners)
                z_center = (min_z + max_z) / 2
                
                # 执行X方向的切分（垂直于X轴的平面）
                for x_pos in x_cuts:
                    # 切分平面：垂直于X轴，通过点(x_pos, y_center, z_center)
                    plane_co = Vector((x_pos, (min_y + max_y) / 2, z_center))
                    plane_no = Vector((1, 0, 0))  # 法向量指向X轴正方向
                    
                    # 执行切分
                    bmesh.ops.bisect_plane(
                        bm,
                        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                        plane_co=plane_co,
                        plane_no=plane_no,
                        clear_inner=False,
                        clear_outer=False
                    )
                
                # 执行Y方向的切分（垂直于Y轴的平面）
                for y_pos in y_cuts:
                    # 切分平面：垂直于Y轴，通过点(x_center, y_pos, z_center)
                    plane_co = Vector(((min_x + max_x) / 2, y_pos, z_center))
                    plane_no = Vector((0, 1, 0))  # 法向量指向Y轴正方向
                    
                    # 执行切分
                    bmesh.ops.bisect_plane(
                        bm,
                        geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                        plane_co=plane_co,
                        plane_no=plane_no,
                        clear_inner=False,
                        clear_outer=False
                    )
                
                # 确保所有边都被分割（断开连接）
                # bisect_plane 创建了新的边，但可能仍然连接着两边的网格
                # 我们需要分割这些边来真正断开连接
                bm.edges.ensure_lookup_table()
                bm.verts.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                
                # 找到所有在切分线上的边
                tolerance = 0.001
                edges_to_split = []
                
                for edge in bm.edges:
                    v1 = edge.verts[0].co
                    v2 = edge.verts[1].co
                    
                    # 检查边是否在X切分线上
                    for x_pos in x_cuts:
                        # 检查边的两个顶点是否都在切分线附近
                        v1_on_line = abs(v1.x - x_pos) < tolerance
                        v2_on_line = abs(v2.x - x_pos) < tolerance
                        if v1_on_line and v2_on_line:
                            if edge not in edges_to_split:
                                edges_to_split.append(edge)
                            break
                    
                    # 检查边是否在Y切分线上
                    for y_pos in y_cuts:
                        v1_on_line = abs(v1.y - y_pos) < tolerance
                        v2_on_line = abs(v2.y - y_pos) < tolerance
                        if v1_on_line and v2_on_line:
                            if edge not in edges_to_split:
                                edges_to_split.append(edge)
                            break
                
                # 分割这些边以断开连接
                if edges_to_split:
                    try:
                        bmesh.ops.split_edges(bm, edges=edges_to_split)
                    except Exception as e:
                        # 如果批量分割失败，尝试逐个分割
                        for edge in list(edges_to_split):
                            try:
                                if edge.is_valid:
                                    bmesh.ops.split_edges(bm, edges=[edge])
                            except:
                                pass
                
                # 将bmesh转换回局部空间
                bm.transform(obj.matrix_world.inverted())
                
                # 更新网格
                bm.normal_update()
                bm.to_mesh(obj.data)
                bm.free()
                
                # 更新物体
                obj.data.update()
                
                # 进入编辑模式并分离网格
                # 先确保物体被选中并激活
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 进入编辑模式
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有几何体
                bpy.ops.mesh.select_all(action='SELECT')
                
                # 分离所有不连接的部分
                # 这会根据切分线创建的边界自动分离
                result = bpy.ops.mesh.separate(type='LOOSE')
                
                # 返回对象模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                # 重命名分离出的物体
                if 'FINISHED' in result:
                    # 获取所有选中的物体（包括原物体和分离出的物体）
                    separated_objects = [o for o in context.selected_objects if o.type == 'MESH']
                    
                    # 保存原始物体名称
                    original_name = obj.name
                    
                    for sep_obj in separated_objects:
                        # 计算这个物体属于哪个网格区域
                        sep_bbox = [sep_obj.matrix_world @ Vector(corner) for corner in sep_obj.bound_box]
                        sep_center_x = sum(c.x for c in sep_bbox) / len(sep_bbox)
                        sep_center_y = sum(c.y for c in sep_bbox) / len(sep_bbox)
                        
                        # 确定网格位置（在世界坐标系中）
                        grid_x = int((sep_center_x - min_x) / x_segment_size) if x_segment_size > 0.001 else 0
                        grid_y = int((sep_center_y - min_y) / y_segment_size) if y_segment_size > 0.001 else 0
                        grid_x = max(0, min(grid_x, x_segments - 1))
                        grid_y = max(0, min(grid_y, y_segments - 1))
                        
                        if sep_obj == obj:
                            # 原物体重命名为第一个网格块
                            sep_obj.name = f"{original_name}_grid_{grid_x}_{grid_y}"
                        else:
                            # 分离出的物体
                            sep_obj.name = f"{original_name}_grid_{grid_x}_{grid_y}"
                
                processed_count += 1
                
            except Exception as e:
                self.report({'ERROR'}, f"处理物体 '{obj.name}' 时出错: {str(e)}")
                continue
        
        if processed_count > 0:
            self.report({'INFO'}, f"成功切分 {processed_count} 个物体")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "没有物体被成功切分")
            return {'CANCELLED'}


# 注册类列表
classes = [
    OBJECT_OT_mesh_grid_cut_top_view,
]


def register():
    """注册操作符"""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """注销操作符"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

