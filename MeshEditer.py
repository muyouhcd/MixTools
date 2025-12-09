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
                    
                    # 计算原始物体的尺寸作为参考（用于过滤小碎片）
                    original_x_size = max_x - min_x
                    original_y_size = max_y - min_y
                    original_z_size = max_z - min_z
                    
                    # 计算预期的每个网格块的尺寸
                    expected_x_size = original_x_size / x_segments
                    expected_y_size = original_y_size / y_segments
                    
                    # 过滤掉太小的物体（小碎片）
                    # 使用更严格的判断标准，删除切分时产生的小碎片
                    valid_objects = []
                    small_fragments = []
                    
                    # 计算预期的每个网格块的最小尺寸（用于判断是否为碎片）
                    min_expected_volume = (expected_x_size * expected_y_size * original_z_size) * 0.05  # 5%的预期体积
                    
                    for sep_obj in separated_objects:
                        # 计算物体的尺寸（使用包围盒）
                        sep_bbox = [sep_obj.matrix_world @ Vector(corner) for corner in sep_obj.bound_box]
                        sep_x_size = max(c.x for c in sep_bbox) - min(c.x for c in sep_bbox)
                        sep_y_size = max(c.y for c in sep_bbox) - min(c.y for c in sep_bbox)
                        sep_z_size = max(c.z for c in sep_bbox) - min(c.z for c in sep_bbox)
                        sep_volume = sep_x_size * sep_y_size * sep_z_size
                        
                        # 获取几何体数量
                        vertex_count = len(sep_obj.data.vertices)
                        face_count = len(sep_obj.data.polygons)
                        edge_count = len(sep_obj.data.edges)
                        
                        # 更严格的判断标准：删除小碎片
                        # 1. 没有面（只有点或边）
                        # 2. 顶点数极少（少于4个顶点）
                        # 3. 体积太小（小于预期体积的5%，且顶点数少于10个）
                        # 4. XY平面尺寸都异常小（可能是切分线上的碎片）
                        size_threshold_x = expected_x_size * 0.05  # 5%的预期尺寸
                        size_threshold_y = expected_y_size * 0.05
                        
                        is_fragment = (face_count < 1) or \
                                     (vertex_count < 4) or \
                                     (sep_volume < min_expected_volume and vertex_count < 10) or \
                                     (sep_x_size < size_threshold_x and sep_y_size < size_threshold_y and vertex_count < 8)
                        
                        if is_fragment:
                            small_fragments.append(sep_obj)
                        else:
                            valid_objects.append(sep_obj)
                    
                    # 删除小碎片
                    fragments_removed = 0
                    for fragment in small_fragments:
                        try:
                            bpy.data.objects.remove(fragment, do_unlink=True)
                            fragments_removed += 1
                        except:
                            pass
                    
                    # 如果有小碎片被删除，报告信息
                    if fragments_removed > 0:
                        self.report({'INFO'}, f"物体 '{obj.name}' 切分时删除了 {fragments_removed} 个小碎片")
                    
                    # 只对有效物体进行重命名
                    # 使用字典来跟踪每个索引位置的物体，避免重名
                    grid_objects = {}  # {(grid_x, grid_y): [objects]}
                    
                    for sep_obj in valid_objects:
                        # 计算这个物体属于哪个网格区域
                        sep_bbox = [sep_obj.matrix_world @ Vector(corner) for corner in sep_obj.bound_box]
                        sep_center_x = sum(c.x for c in sep_bbox) / len(sep_bbox)
                        sep_center_y = sum(c.y for c in sep_bbox) / len(sep_bbox)
                        
                        # 计算网格索引
                        # 最小X、最小Y的位置对应索引(0,0)
                        # 最大X、最大Y的位置对应索引(x_segments-1, y_segments-1)
                        if x_segment_size > 0.001:
                            # 计算X索引：从min_x开始，每段大小为x_segment_size
                            grid_x = int((sep_center_x - min_x) / x_segment_size)
                            # 确保索引在有效范围内 [0, x_segments-1]
                            grid_x = max(0, min(grid_x, x_segments - 1))
                        else:
                            grid_x = 0
                        
                        if y_segment_size > 0.001:
                            # 计算Y索引：从min_y开始，每段大小为y_segment_size
                            grid_y = int((sep_center_y - min_y) / y_segment_size)
                            # 确保索引在有效范围内 [0, y_segments-1]
                            grid_y = max(0, min(grid_y, y_segments - 1))
                        else:
                            grid_y = 0
                        
                        # 将物体添加到对应索引位置
                        grid_key = (grid_x, grid_y)
                        if grid_key not in grid_objects:
                            grid_objects[grid_key] = []
                        grid_objects[grid_key].append(sep_obj)
                    
                    # 处理每个网格位置的物体
                    for (grid_x, grid_y), objects_at_position in grid_objects.items():
                        if len(objects_at_position) == 1:
                            # 只有一个物体，直接命名
                            objects_at_position[0].name = f"{original_name}_{grid_x}_{grid_y}"
                        else:
                            # 多个物体在同一位置（可能是碎片或重叠）
                            # 选择体积最大的物体作为主物体，其他作为碎片删除
                            def get_volume(obj):
                                bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                                x_size = max(c.x for c in bbox) - min(c.x for c in bbox)
                                y_size = max(c.y for c in bbox) - min(c.y for c in bbox)
                                z_size = max(c.z for c in bbox) - min(c.z for c in bbox)
                                return x_size * y_size * z_size
                            
                            objects_at_position.sort(key=get_volume, reverse=True)
                            
                            # 主物体使用标准命名
                            main_obj = objects_at_position[0]
                            main_obj.name = f"{original_name}_{grid_x}_{grid_y}"
                            
                            # 其他物体作为碎片删除
                            for fragment in objects_at_position[1:]:
                                try:
                                    bpy.data.objects.remove(fragment, do_unlink=True)
                                    fragments_removed += 1
                                except:
                                    pass
                
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


class OBJECT_OT_apply_modifiers(Operator):
    """批量应用选中物体的修改器"""
    bl_idname = "object.apply_modifiers"
    bl_label = "应用修改器"
    bl_description = "批量应用选中物体的所有修改器，按顺序从第一个到最后一个应用"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """检查是否有选中的物体且有修改器"""
        if not context.selected_objects:
            return False
        # 检查是否有任何选中的物体有修改器
        return any(
            obj.type == 'MESH' and obj.modifiers 
            for obj in context.selected_objects
        )

    def execute(self, context):
        """执行批量应用修改器操作"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个网格物体")
            return {'CANCELLED'}

        # 保存当前模式
        original_mode = context.mode
        original_active = context.view_layer.objects.active
        
        total_modifiers_applied = 0
        objects_processed = 0
        
        try:
            # 确保处于对象模式
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            for obj in selected_objects:
                if not obj.modifiers:
                    continue
                
                try:
                    # 确保物体被选中并激活
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    
                    # 确保物体处于对象模式
                    if obj.mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # 获取修改器名称列表的副本（因为应用修改器会改变列表）
                    # 按顺序保存修改器名称，确保从第一个到最后一个应用
                    modifiers_names = [mod.name for mod in obj.modifiers]
                    
                    if not modifiers_names:
                        continue
                    
                    # 按顺序应用每个修改器（从第一个到最后一个）
                    # 每次应用后，第一个修改器会被移除，所以总是应用第一个
                    while modifiers_names:
                        modifier_name = modifiers_names[0]
                        
                        # 检查修改器是否仍然存在（可能在应用过程中被移除）
                        if modifier_name not in obj.modifiers:
                            modifiers_names.pop(0)
                            continue
                        
                        try:
                            # 应用修改器（总是应用第一个，因为应用后会移除）
                            bpy.ops.object.modifier_apply(modifier=modifier_name)
                            total_modifiers_applied += 1
                            # 移除已应用的修改器名称
                            modifiers_names.pop(0)
                        except Exception as e:
                            self.report({'WARNING'}, 
                                      f"应用物体 '{obj.name}' 的修改器 '{modifier_name}' 时出错: {str(e)}")
                            # 如果应用失败，移除该修改器名称并继续下一个
                            modifiers_names.pop(0)
                            continue
                    
                    objects_processed += 1
                    
                except Exception as e:
                    self.report({'ERROR'}, f"处理物体 '{obj.name}' 时出错: {str(e)}")
                    continue
        
        finally:
            # 恢复原始选中状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected_objects:
                obj.select_set(True)
            if original_active and original_active.name in context.view_layer.objects:
                context.view_layer.objects.active = original_active
            
            # 恢复原始模式
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
        
        if total_modifiers_applied > 0:
            self.report({'INFO'}, 
                       f"成功为 {objects_processed} 个物体应用了 {total_modifiers_applied} 个修改器")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "没有修改器被应用")
            return {'CANCELLED'}


class OBJECT_OT_edge_lock_decimate(Operator):
    """锁边精简：将非边缘顶点加入inner顶点组，然后添加精简修改器"""
    bl_idname = "object.edge_lock_decimate"
    bl_label = "锁边精简"
    bl_description = "将所选物体的非边缘顶点加入inner顶点组，然后添加精简修改器，只精简内部顶点，保留边缘"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """检查是否有选中的网格物体"""
        return context.selected_objects and any(
            obj.type == 'MESH' for obj in context.selected_objects
        )

    def execute(self, context):
        """执行锁边精简操作"""
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个网格物体")
            return {'CANCELLED'}

        # 从场景属性获取精简比率
        decimate_ratio = context.scene.edge_lock_decimate_ratio
        
        if decimate_ratio <= 0.0 or decimate_ratio > 1.0:
            self.report({'ERROR'}, "精简比率必须在0到1之间")
            return {'CANCELLED'}

        # 保存当前模式
        original_mode = context.mode
        original_active = context.view_layer.objects.active
        
        processed_count = 0
        
        try:
            # 确保处于对象模式
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            
            for obj in selected_objects:
                try:
                    # 确保物体被选中并激活
                    bpy.ops.object.select_all(action='DESELECT')
                    obj.select_set(True)
                    context.view_layer.objects.active = obj
                    
                    # 确保物体处于对象模式
                    if obj.mode != 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')
                    
                    # 确保网格数据独立
                    if obj.data.users > 1:
                        obj.data = obj.data.copy()
                    
                    # 创建bmesh对象来分析边缘
                    # 直接使用原始网格数据，确保顶点索引匹配
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)
                    
                    # 确保查找表已更新
                    bm.verts.ensure_lookup_table()
                    bm.edges.ensure_lookup_table()
                    bm.faces.ensure_lookup_table()
                    
                    # 找到所有边界边（boundary edges）
                    # 边界边是只属于一个面的边（或没有面的边）
                    boundary_vertices_bm = set()
                    for edge in bm.edges:
                        # 如果边只连接一个面或没有面，则是边界边
                        if len(edge.link_faces) <= 1:
                            boundary_vertices_bm.add(edge.verts[0])
                            boundary_vertices_bm.add(edge.verts[1])
                    
                    # 获取inner顶点的索引（非边界顶点）
                    inner_vertex_indices = [v.index for v in bm.verts if v not in boundary_vertices_bm]
                    bm.free()
                    
                    # 创建或获取inner顶点组
                    vertex_group_name = "inner"
                    vg = None
                    for existing_vg in obj.vertex_groups:
                        if existing_vg.name == vertex_group_name:
                            vg = existing_vg
                            break
                    
                    if vg is None:
                        vg = obj.vertex_groups.new(name=vertex_group_name)
                    else:
                        # 清空现有顶点组
                        vg.remove(range(len(obj.data.vertices)))
                    
                    # 将inner顶点添加到顶点组，权重为1.0
                    if inner_vertex_indices:
                        vg.add(inner_vertex_indices, 1.0, 'REPLACE')
                    
                    # 检查是否已存在同名的精简修改器
                    existing_modifier = None
                    for mod in obj.modifiers:
                        if mod.name == "EdgeLockDecimate" and mod.type == 'DECIMATE':
                            existing_modifier = mod
                            break
                    
                    if existing_modifier is None:
                        # 添加精简修改器
                        decimate_mod = obj.modifiers.new(name="EdgeLockDecimate", type='DECIMATE')
                    else:
                        decimate_mod = existing_modifier
                    
                    # 设置精简修改器参数
                    decimate_mod.decimate_type = 'COLLAPSE'  # 使用折叠类型
                    decimate_mod.ratio = decimate_ratio
                    
                    # 设置顶点组（只精简inner顶点组中的顶点）
                    decimate_mod.vertex_group = vertex_group_name
                    decimate_mod.invert_vertex_group = False  # 不反转，只精简inner组中的顶点
                    
                    processed_count += 1
                    
                except Exception as e:
                    self.report({'ERROR'}, f"处理物体 '{obj.name}' 时出错: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        finally:
            # 恢复原始选中状态
            bpy.ops.object.select_all(action='DESELECT')
            for obj in selected_objects:
                obj.select_set(True)
            if original_active and original_active.name in context.view_layer.objects:
                context.view_layer.objects.active = original_active
            
            # 恢复原始模式
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
        
        if processed_count > 0:
            self.report({'INFO'}, f"成功为 {processed_count} 个物体添加锁边精简修改器")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "没有物体被成功处理")
            return {'CANCELLED'}


# 注册类列表
classes = [
    OBJECT_OT_mesh_grid_cut_top_view,
    OBJECT_OT_apply_modifiers,
    OBJECT_OT_edge_lock_decimate,
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

