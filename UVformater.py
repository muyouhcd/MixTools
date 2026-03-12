import bpy
import bmesh
import math
import mathutils
import numpy as np

def area_quad(v1, v2, v3, v4):
    """Calculate the area of a quad by dividing it into two triangles."""
    return mathutils.geometry.area_tri(v1, v2, v3) + mathutils.geometry.area_tri(v1, v3, v4)

def scale_uv_to_match_texture(obj, pixel_per_meter=32, texture_size=128, angle_threshold=5.0):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if not mesh.uv_layers.active:
        print(f"{obj.name} 没有UV映射。")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    
    uv_layer = bm.loops.layers.uv.active
    texture_meter_size = texture_size / pixel_per_meter
    angle_rad_threshold = math.radians(angle_threshold)

    def get_adjacent_faces(face):
        for edge in face.edges:
            for linked_face in edge.link_faces:
                if linked_face != face:
                    yield linked_face

    visited_faces = set()
    
    for face in bm.faces:
        if face in visited_faces:
            continue
        
        connected_faces = set([face])
        queue = [face]
        
        while queue:
            current_face = queue.pop()
            visited_faces.add(current_face)
            face_normal = current_face.normal
            face_material = current_face.material_index  # Get the material index of the current face

            for adj_face in get_adjacent_faces(current_face):
                if adj_face in visited_faces:
                    continue
                if adj_face.material_index != face_material:
                    continue
                angle = face_normal.angle(adj_face.normal)
                if angle < angle_rad_threshold:
                    connected_faces.add(adj_face)
                    queue.append(adj_face)
        
        # Process connected faces
        world_verts = [obj.matrix_world @ v.co for f in connected_faces for v in f.verts]
        face_area_world = 0.0
        face_area_uv = 0.0

        uv_coords = []

        for f in connected_faces:
            verts = [obj.matrix_world @ v.co for v in f.verts]
            uvs = [l[uv_layer].uv.copy() for l in f.loops]
            num_verts = len(verts)

            if num_verts == 3:
                face_area_world += mathutils.geometry.area_tri(*verts)
                face_area_uv += mathutils.geometry.area_tri(*uvs)
            elif num_verts == 4:
                face_area_world += area_quad(*verts)
                face_area_uv += area_quad(*uvs)
            else:
                print(f"警告: 对象 {obj.name} 包含非三角形或四边形面，跳过该面。")
                continue

            uv_coords.extend(uvs)

        if face_area_world <= 0:
            print(f"警告: 对象 {obj.name} 的一组相连面具有零或负的世界面积，跳过该组。")
            continue

        if face_area_uv <= 0:
            print(f"警告: 对象 {obj.name} 的一组相连面具有零或负的 UV 面积，跳过该组。")
            continue

        current_pixel_density = face_area_uv / face_area_world
        target_pixel_density = 1.0 / (texture_meter_size ** 2)
        scale_uv_factor = math.sqrt(target_pixel_density / current_pixel_density)

        center_uv = sum(uv_coords, mathutils.Vector((0, 0))) / len(uv_coords)

        for f in connected_faces:
            for loop in f.loops:
                loop_uv = loop[uv_layer].uv
                loop_uv.x = (loop_uv.x - center_uv.x) * scale_uv_factor + center_uv.x
                loop_uv.y = (loop_uv.y - center_uv.y) * scale_uv_factor + center_uv.y

    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode='OBJECT')
def align_quad_uv_to_corners(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if not mesh.uv_layers:
        mesh.uv_layers.new()
    
    uv_layer = bm.loops.layers.uv.active

    for face in bm.faces:
        if len(face.verts) == 4:
            # 对齐四边形面到UV边界的四个角
            uv_coords = [(0, 0), (1, 0), (1, 1), (0, 1)]
            for loop, (u, v) in zip(face.loops, uv_coords):
                loop[uv_layer].uv = (u, v)
        else:
            print(f"面 {face.index} 不是四边形，跳过。")

    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode='OBJECT')
class UVformater(bpy.types.Operator):
    bl_idname = "object.uv_formater"
    bl_label = "uv统一规格尺寸"
    bl_description = "批量调整选中对象中的 UV 映射"
    bl_options = {'REGISTER', 'UNDO'}

    pixel_per_meter: bpy.props.IntProperty(
        name="像素/米",
        default=32,
        min=1,
        description="每米的像素数"
    )

    texture_size: bpy.props.IntProperty(
        name="纹理尺寸",
        default=128,
        min=1,
        description="纹理的像素尺寸"
    )

    angle_threshold: bpy.props.FloatProperty(
        name="角度阈值",
        default=5.0,
        min=0.0,
        max=180.0,
        description="在组内合并处理面时的最大角度差"
    )

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                scale_uv_to_match_texture(obj, self.pixel_per_meter, self.texture_size, self.angle_threshold)
            else:
                self.report({'WARNING'}, f"{obj.name} 不是一个网格对象，跳过。")
        return {'FINISHED'}
class QuadUVAligner(bpy.types.Operator):
    bl_idname = "object.quad_uv_aligner"
    bl_label = "四边形UV对齐"
    bl_description = "对选定对象的四边形面将UV对齐到UV空间的四个角"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                align_quad_uv_to_corners(obj)
            else:
                self.report({'WARNING'}, f"{obj.name} 不是一个网格对象，跳过。")
        return {'FINISHED'}
def correct_uv_rotation(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if not mesh.uv_layers:
        mesh.uv_layers.new()
    
    uv_layer = bm.loops.layers.uv.active
    visited_faces = set()

    def get_adjacent_faces(face):
        for edge in face.edges:
            for linked_face in edge.link_faces:
                if linked_face != face:
                    yield linked_face

    def align_uv_to_reference(ref_face, face):
        ref_uvs = [ref_face.loops[i][uv_layer].uv.copy() for i in range(len(ref_face.verts))]
        uvs = [face.loops[i][uv_layer].uv.copy() for i in range(len(face.verts))]

        ref_center = sum(ref_uvs, mathutils.Vector((0.0, 0.0))) / len(ref_uvs)
        face_center = sum(uvs, mathutils.Vector((0.0, 0.0))) / len(uvs)

        ref_uvs_rel = [uv - ref_center for uv in ref_uvs]
        uvs_rel = [uv - face_center for uv in uvs]

        def find_rotation_scale(a, b):
            a1, a2 = a
            b1, b2 = b
            rot_angle = (b1 - b2).to_2d().angle_signed((a1 - a2).to_2d())
            scale = ((b1 - b2).length) / ((a1 - a2).length)
            return rot_angle, scale

        rotation, scale = find_rotation_scale(ref_uvs_rel[:2], uvs_rel[:2])

        transform = mathutils.Matrix.Translation(ref_center) @ \
                    mathutils.Matrix.Scale(scale, 2) @ \
                    mathutils.Matrix.Rotation(rotation, 2) @ \
                    mathutils.Matrix.Translation(-face_center)

        for i, loop in enumerate(face.loops):
            loop_uv = loop[uv_layer].uv
            loop_uv.xy = transform @ uvs[i]

    for face in bm.faces:
        if face in visited_faces or len(face.verts) != 4:
            continue
        
        # Find connected coplanar faces
        connected_faces = {face}
        queue = [face]

        while queue:
            current_face = queue.pop(0)
            visited_faces.add(current_face)
            face_normal = current_face.normal

            for adj_face in get_adjacent_faces(current_face):
                if adj_face not in visited_faces and len(adj_face.verts) == 4:
                    angle_between_faces = face_normal.angle(adj_face.normal)
                    if angle_between_faces < math.radians(1):
                        queue.append(adj_face)
                        connected_faces.add(adj_face)

        # Align all connected faces to the reference face
        reference_face = face
        for connected_face in connected_faces:
            if connected_face != reference_face:
                align_uv_to_reference(reference_face, connected_face)

    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode='OBJECT')

class CorrectUVRotationOperator(bpy.types.Operator):
    bl_idname = "object.correct_uv_rotation"
    bl_label = "矫正 UV 旋转"
    bl_description = "矫正选定对象的四边形面 UV 旋转，以第一个面为基准进行对齐。"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                correct_uv_rotation(obj)
            else:
                self.report({'WARNING'}, f"{obj.name} 不是一个网格对象，跳过。")
        return {'FINISHED'}

# UV孤岛对齐功能 - 基于UV坐标的纯UV空间处理
def get_selected_uv_islands(obj, debug=False):
    """
    直接从UV坐标数据获取选中的UV孤岛
    完全基于UV空间，通过UV坐标连续性判定孤岛，不依赖mesh拓扑结构
    """
    if obj.type != 'MESH':
        if debug:
            print(f"[DEBUG] 对象 {obj.name} 不是网格对象")
        return []
    
    # 确保在编辑模式（用于读取选择状态）
    if obj.mode != 'EDIT':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
    
    mesh = obj.data
    
    # 刷新选择状态
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
    except:
        pass
    
    bmesh.update_edit_mesh(mesh)
    bm = bmesh.from_edit_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.loops.ensure_lookup_table()
    
    if not mesh.uv_layers.active:
        if debug:
            print("[DEBUG] 对象没有活动的UV层")
        return []
    
    uv_layer = bm.loops.layers.uv.active
    uv_data = mesh.uv_layers.active.data  # 直接访问UV层数据
    
    if debug:
        print(f"[DEBUG] ========== 开始检测选中的UV孤岛（基于UV坐标），对象: {obj.name} ==========")
        print(f"[DEBUG] 总loop数: {len(uv_data)}, 总面数: {len(bm.faces)}")
    
    # UV容差（用于判定UV坐标是否相同）
    uv_tolerance = 1e-5
    
    def get_uv_key(u, v):
        """将UV坐标转换为可比较的键"""
        return (round(u / uv_tolerance), round(v / uv_tolerance))
    
    # 第一步：直接从UV数据构建映射
    # uv_key -> set of (face_idx, loop_idx_in_face)
    uv_key_to_loops = {}  # UV坐标 -> [(face_idx, loop_idx_in_face, is_selected), ...]
    face_loop_info = {}  # face_idx -> [(loop_idx_in_face, uv_key, is_selected), ...]
    selected_faces = set()  # 包含选中UV元素的面
    
    # 遍历所有loop，直接从UV数据读取
    loop_idx_global = 0
    for face_idx, face in enumerate(bm.faces):
        face_loops = []
        face_has_selection = False
        
        for loop_idx_in_face, loop in enumerate(face.loops):
            # 直接从loop获取UV坐标和选择状态
            uv = loop[uv_layer].uv
            uv_key = get_uv_key(uv.x, uv.y)
            is_selected = loop[uv_layer].select or loop[uv_layer].select_edge
            
            # 记录loop信息
            face_loops.append((loop_idx_in_face, uv_key, is_selected))
            
            # 建立UV坐标到loop的映射
            if uv_key not in uv_key_to_loops:
                uv_key_to_loops[uv_key] = []
            uv_key_to_loops[uv_key].append((face_idx, loop_idx_in_face, is_selected))
            
            if is_selected:
                face_has_selection = True
            
            loop_idx_global += 1
        
        face_loop_info[face_idx] = face_loops
        if face_has_selection:
            selected_faces.add(face_idx)
    
    if debug:
        total_selected_loops = sum(1 for loops in face_loop_info.values() 
                                   for _, _, sel in loops if sel)
        print(f"[DEBUG] 找到 {len(selected_faces)} 个包含选中UV元素的面（总共 {total_selected_loops} 个选中的UV loop）")
        print(f"[DEBUG] 唯一UV坐标数: {len(uv_key_to_loops)}")
        
        if total_selected_loops == 0:
            print(f"[DEBUG] ⚠️ 警告: 未检测到任何UV选择状态！")
            print(f"[DEBUG]   可能的原因:")
            print(f"[DEBUG]   1. 请确保在UV编辑器中选择了一些UV元素")
            print(f"[DEBUG]   2. 请确保物体处于编辑模式")
            print(f"[DEBUG]   3. 请确保选择了正确的UV层")
            print(f"[DEBUG]   4. ⚠️ 重要: 请取消UV编辑器的'选区同步'设置！")
            print(f"[DEBUG]      在UV编辑器顶部工具栏中，找到'选区同步'按钮并关闭它")
            print(f"[DEBUG]   5. 请尝试在UV编辑器中重新选择一些元素")
            print(f"[DEBUG]   6. 确保在UV编辑器中选择模式是'顶点'、'边'或'面'模式")
            return []
    
    if not selected_faces:
        if debug:
            print("[DEBUG] 没有找到任何包含选中UV元素的面")
        return []
    
    # 第二步：通过UV坐标连续性构建孤岛
    # 使用BFS，从选中的面开始，通过共享UV坐标扩展到整个孤岛
    islands = []
    processed_faces = set()
    
    for start_face_idx in selected_faces:
        if start_face_idx in processed_faces:
            continue
        
        # 从这个选中的面开始，找出整个UV孤岛
        island_face_indices = set([start_face_idx])
        queue = [start_face_idx]
        processed_faces.add(start_face_idx)
        
        while queue:
            current_face_idx = queue.pop()
            current_face_loops = face_loop_info[current_face_idx]
            
            # 获取当前面的所有UV坐标
            current_face_uv_keys = set(uv_key for _, uv_key, _ in current_face_loops)
            
            # 通过共享UV坐标找到所有连接的面
            for uv_key in current_face_uv_keys:
                if uv_key in uv_key_to_loops:
                    for linked_face_idx, _, _ in uv_key_to_loops[uv_key]:
                        if linked_face_idx not in processed_faces:
                            # 添加到孤岛（无论是否被选中）
                            island_face_indices.add(linked_face_idx)
                            queue.append(linked_face_idx)
                            processed_faces.add(linked_face_idx)
        
        # 记录这个孤岛
        islands.append(island_face_indices)
        if debug:
            selected_in_island = len([f_idx for f_idx in island_face_indices if f_idx in selected_faces])
            print(f"[DEBUG] 识别到孤岛 {len(islands)}: 包含 {len(island_face_indices)} 个面（整个孤岛，其中 {selected_in_island} 个被选中）")
    
    if debug:
        print(f"[DEBUG] ========== 总共识别到 {len(islands)} 个孤岛 ==========")
        total_faces_in_islands = 0
        for i, island in enumerate(islands):
            selected_in_island = len([f_idx for f_idx in island if f_idx in selected_faces])
            print(f"[DEBUG]   孤岛 {i+1}: {len(island)} 个面（整个孤岛，其中 {selected_in_island} 个被选中）")
            total_faces_in_islands += len(island)
        print(f"[DEBUG] 孤岛总面数: {total_faces_in_islands}, 原始选中面数: {len(selected_faces)}")
        print(f"[DEBUG] 说明: 只要选中了孤岛上的任意元素，整个孤岛都会被移动")
    
    return islands

def safe_get_face(bm, face_idx, debug=False):
    """安全地获取face，处理索引越界等异常"""
    try:
        bm.faces.ensure_lookup_table()
        if face_idx >= len(bm.faces):
            return None
        return bm.faces[face_idx]
    except (IndexError, AttributeError, RuntimeError) as e:
        if debug:
            print(f"[DEBUG]   警告: 无法访问面 {face_idx}: {e}")
        return None

def get_island_bounds(island_face_indices, bm, uv_layer):
    """获取孤岛的边界框（使用face索引）"""
    min_u = float('inf')
    max_u = float('-inf')
    min_v = float('inf')
    max_v = float('-inf')
    
    # 确保bmesh的查找表是最新的
    bm.faces.ensure_lookup_table()
    
    for face_idx in island_face_indices:
        face = safe_get_face(bm, face_idx)
        if face is None:
            continue
        try:
            for loop in face.loops:
                uv = loop[uv_layer].uv
                min_u = min(min_u, uv.x)
                max_u = max(max_u, uv.x)
                min_v = min(min_v, uv.y)
                max_v = max(max_v, uv.y)
        except (AttributeError, RuntimeError) as e:
            # 如果loop或uv访问失败，跳过这个face
            continue
    
    return {
        'min_u': min_u,
        'max_u': max_u,
        'min_v': min_v,
        'max_v': max_v,
        'center_u': (min_u + max_u) / 2.0,
        'center_v': (min_v + max_v) / 2.0,
        'width': max_u - min_u,
        'height': max_v - min_v
    }

def get_selected_uv_islands_multi_objects(context, debug=False):
    """从所有选中的物体中获取选中的UV孤岛（支持跨物体操作）"""
    all_islands = []  # [(obj, island_face_indices), ...]
    
    selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if not selected_objects:
        # 如果没有选中的物体，使用活动物体
        if context.active_object and context.active_object.type == 'MESH':
            selected_objects = [context.active_object]
    
    if debug:
        print(f"[DEBUG] get_selected_uv_islands_multi_objects: 处理 {len(selected_objects)} 个物体")
    
    for obj in selected_objects:
        islands = get_selected_uv_islands(obj, debug=debug)
        if debug:
            print(f"[DEBUG] 物体 {obj.name}: 找到 {len(islands)} 个孤岛")
        for island_face_indices in islands:
            all_islands.append((obj, island_face_indices))
    
    if debug:
        print(f"[DEBUG] 总共找到 {len(all_islands)} 个孤岛（跨所有物体）")
    
    return all_islands

def align_uv_islands(obj=None, align_mode='TOP', debug=False, context=None):
    """对齐选中的UV孤岛（支持跨物体操作）"""
    if context is None:
        context = bpy.context
    
    # 如果指定了obj，只处理该物体；否则处理所有选中的物体
    if obj is not None:
        if obj.type != 'MESH':
            return False
        
        # 确保在编辑模式
        if obj.mode != 'EDIT':
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
        
        mesh = obj.data
        if not mesh.uv_layers.active:
            return False
        
        # 获取选中的孤岛
        islands = get_selected_uv_islands(obj, debug=debug)
        if debug:
            print(f"[DEBUG] align_uv_islands: 获取到 {len(islands)} 个孤岛")
            for i, island in enumerate(islands):
                print(f"[DEBUG]   孤岛 {i+1}: {len(island)} 个面")
        
        if len(islands) < 2:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少2个，当前: {len(islands)}")
            return False
        
        # 重新获取bmesh以确保使用最新的数据
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        
        # 计算所有孤岛的边界
        island_bounds = []
        for i, island_face_indices in enumerate(islands):
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} 边界: U[{bounds['min_u']:.3f}, {bounds['max_u']:.3f}], V[{bounds['min_v']:.3f}, {bounds['max_v']:.3f}]")
    else:
        # 跨物体操作
        all_islands = get_selected_uv_islands_multi_objects(context, debug=debug)
        if len(all_islands) < 2:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少2个，当前: {len(all_islands)}")
            return False
        
        # 为每个物体准备bmesh和uv_layer
        obj_bm_data = {}  # obj -> (bm, uv_layer, mesh)
        for obj, _ in all_islands:
            if obj not in obj_bm_data:
                if obj.mode != 'EDIT':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)
                uv_layer = bm.loops.layers.uv.active
                obj_bm_data[obj] = (bm, uv_layer, mesh)
        
        # 计算所有孤岛的边界
        island_bounds = []
        for obj, island_face_indices in all_islands:
            bm, uv_layer, mesh = obj_bm_data[obj]
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
    
    # 根据对齐模式计算目标位置
    if align_mode == 'TOP':
        # 顶对齐：所有孤岛对齐到最高点的V坐标
        target_v = max(bounds['max_v'] for _, _, bounds, _, _, _ in island_bounds)
        if debug:
            print(f"[DEBUG] 顶对齐 - 目标V坐标: {target_v:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据（因为前面的移动可能已经改变了mesh）
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            # 重新计算边界（因为前面的移动可能已经改变了位置）
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_v = target_v - bounds['max_v']
            if abs(offset_v) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移V = {offset_v:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            bm.faces.ensure_lookup_table()  # 确保查找表是最新的
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.y += offset_v
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
                    
    elif align_mode == 'BOTTOM':
        # 底对齐：所有孤岛对齐到最低点的V坐标
        target_v = min(bounds['min_v'] for _, _, bounds, _, _, _ in island_bounds)
        if debug:
            print(f"[DEBUG] 底对齐 - 目标V坐标: {target_v:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_v = target_v - bounds['min_v']
            if abs(offset_v) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移V = {offset_v:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            bm.faces.ensure_lookup_table()  # 确保查找表是最新的
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.y += offset_v
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
                    
    elif align_mode == 'CENTER_V':
        # 垂直中心对齐：所有孤岛的中心V坐标对齐
        target_v = sum(bounds['center_v'] for _, _, bounds, _, _, _ in island_bounds) / len(island_bounds)
        if debug:
            print(f"[DEBUG] 垂直中心对齐 - 目标V坐标: {target_v:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_v = target_v - bounds['center_v']
            if abs(offset_v) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移V = {offset_v:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            bm.faces.ensure_lookup_table()  # 确保查找表是最新的
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.y += offset_v
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
                    
    elif align_mode == 'LEFT':
        # 左对齐：所有孤岛对齐到最左点的U坐标
        target_u = min(bounds['min_u'] for _, _, bounds, _, _, _ in island_bounds)
        if debug:
            print(f"[DEBUG] 左对齐 - 目标U坐标: {target_u:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_u = target_u - bounds['min_u']
            if abs(offset_u) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移U = {offset_u:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.x += offset_u
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
                    
    elif align_mode == 'RIGHT':
        # 右对齐：所有孤岛对齐到最右点的U坐标
        target_u = max(bounds['max_u'] for _, _, bounds, _, _, _ in island_bounds)
        if debug:
            print(f"[DEBUG] 右对齐 - 目标U坐标: {target_u:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_u = target_u - bounds['max_u']
            if abs(offset_u) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移U = {offset_u:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.x += offset_u
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
                    
    elif align_mode == 'CENTER_H':
        # 水平中心对齐：所有孤岛的中心U坐标对齐
        target_u = sum(bounds['center_u'] for _, _, bounds, _, _, _ in island_bounds) / len(island_bounds)
        if debug:
            print(f"[DEBUG] 水平中心对齐 - 目标U坐标: {target_u:.3f}, 需要处理 {len(island_bounds)} 个孤岛")
        for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds):
            # 重新获取bmesh以确保使用最新数据
            bm = bmesh.from_edit_mesh(mesh)
            uv_layer = bm.loops.layers.uv.active
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            
            offset_u = target_u - bounds['center_u']
            if abs(offset_u) < 1e-6:
                if debug:
                    print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 无需移动（已在目标位置）")
                continue
                
            if debug:
                print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移U = {offset_u:.3f}, 移动 {len(island_face_indices)} 个面")
            # 移动整个孤岛的所有面
            moved_faces = 0
            for face_idx in island_face_indices:
                face = safe_get_face(bm, face_idx, debug=debug)
                if face is None:
                    continue
                try:
                    for loop in face.loops:
                        loop[uv_layer].uv.x += offset_u
                    moved_faces += 1
                except (AttributeError, RuntimeError) as e:
                    if debug:
                        print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                    continue
            bmesh.update_edit_mesh(mesh)  # 移动后立即更新
            if debug:
                print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
    
    return True

def arrange_uv_islands_horizontal(obj=None, spacing=0.1, debug=False, context=None):
    """水平间距排列：只调整X轴（U轴）的间距，保持Y轴位置不变（支持跨物体操作）"""
    if context is None:
        context = bpy.context
    
    # 如果指定了obj，只处理该物体；否则处理所有选中的物体
    if obj is not None:
        if obj.type != 'MESH':
            return False
        
        # 确保在编辑模式
        if obj.mode != 'EDIT':
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
        
        mesh = obj.data
        if not mesh.uv_layers.active:
            return False
        
        # 获取选中的孤岛
        islands = get_selected_uv_islands(obj, debug=debug)
        if debug:
            print(f"[DEBUG] arrange_uv_islands_horizontal: 获取到 {len(islands)} 个孤岛")
        
        if len(islands) < 1:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少1个，当前: {len(islands)}")
            return False
        
        # 重新获取bmesh以确保使用最新的数据
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        
        # 计算所有孤岛的边界
        island_bounds = []
        for island_face_indices in islands:
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
    else:
        # 跨物体操作
        all_islands = get_selected_uv_islands_multi_objects(context, debug=debug)
        if len(all_islands) < 1:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少1个，当前: {len(all_islands)}")
            return False
        
        # 为每个物体准备bmesh和uv_layer
        obj_bm_data = {}  # obj -> (bm, uv_layer, mesh)
        for obj, _ in all_islands:
            if obj not in obj_bm_data:
                if obj.mode != 'EDIT':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)
                uv_layer = bm.loops.layers.uv.active
                obj_bm_data[obj] = (bm, uv_layer, mesh)
        
        # 计算所有孤岛的边界
        island_bounds = []
        for obj, island_face_indices in all_islands:
            bm, uv_layer, mesh = obj_bm_data[obj]
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
    
    # 按照最小U坐标排序（从左到右）
    island_bounds.sort(key=lambda x: x[2]['min_u'])
    
    # 水平排列：保持每个孤岛的V坐标不变，只调整U坐标
    if debug:
        print(f"[DEBUG] 水平间距排列 - 间距: {spacing:.3f}")
        print(f"[DEBUG] 排序后的孤岛顺序:")
        for i, (obj, _, bounds, _, _, _) in enumerate(island_bounds):
            print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): U范围 [{bounds['min_u']:.3f}, {bounds['max_u']:.3f}], 宽度: {bounds['width']:.3f}")
    
    # 第一个孤岛保持原位置，计算下一个位置
    first_obj, first_island, first_bounds, first_bm, first_uv_layer, first_mesh = island_bounds[0]
    current_x = first_bounds['max_u'] + spacing  # 第一个孤岛右边界 + 间距
    
    if debug:
        print(f"[DEBUG]   孤岛 1 (物体: {first_obj.name}): 保持原位置 [U: {first_bounds['min_u']:.3f} - {first_bounds['max_u']:.3f}], 下一个位置: {current_x:.3f}")
    
    # 从第二个孤岛开始排列
    for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds[1:], start=1):
        # 计算需要移动的U偏移量（将孤岛的左边界对齐到current_x）
        offset_u = current_x - bounds['min_u']
        
        if debug:
            print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移U = {offset_u:.3f}, 从 {bounds['min_u']:.3f} 移动到 {current_x:.3f}, 宽度: {bounds['width']:.3f}, 移动 {len(island_face_indices)} 个面")
        
        # 移动整个孤岛的所有面
        moved_faces = 0
        bm.faces.ensure_lookup_table()  # 确保查找表是最新的
        for face_idx in island_face_indices:
            face = safe_get_face(bm, face_idx, debug=debug)
            if face is None:
                continue
            try:
                for loop in face.loops:
                    loop[uv_layer].uv.x += offset_u
                moved_faces += 1
            except (AttributeError, RuntimeError) as e:
                if debug:
                    print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                continue
        
        bmesh.update_edit_mesh(mesh)  # 移动后立即更新
        if debug:
            print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
        
        # 更新下一个位置（移动后的右边界 + 间距）
        # 移动后，新的右边界 = current_x + bounds['width']
        current_x = current_x + bounds['width'] + spacing
    
    if debug:
        print(f"[DEBUG] 水平间距排列完成，处理了 {len(island_bounds)} 个孤岛")
    return True

def arrange_uv_islands_vertical(obj=None, spacing=0.1, debug=False, context=None):
    """垂直间距排列：只调整Y轴（V轴）的间距，保持X轴位置不变（支持跨物体操作）"""
    if context is None:
        context = bpy.context
    
    # 如果指定了obj，只处理该物体；否则处理所有选中的物体
    if obj is not None:
        if obj.type != 'MESH':
            return False
        
        # 确保在编辑模式
        if obj.mode != 'EDIT':
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
        
        mesh = obj.data
        if not mesh.uv_layers.active:
            return False
        
        # 获取选中的孤岛
        islands = get_selected_uv_islands(obj, debug=debug)
        if debug:
            print(f"[DEBUG] arrange_uv_islands_vertical: 获取到 {len(islands)} 个孤岛")
        
        if len(islands) < 1:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少1个，当前: {len(islands)}")
            return False
        
        # 重新获取bmesh以确保使用最新的数据
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        
        # 计算所有孤岛的边界
        island_bounds = []
        for island_face_indices in islands:
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
    else:
        # 跨物体操作
        all_islands = get_selected_uv_islands_multi_objects(context, debug=debug)
        if len(all_islands) < 1:
            if debug:
                print(f"[DEBUG] 孤岛数量不足，需要至少1个，当前: {len(all_islands)}")
            return False
        
        # 为每个物体准备bmesh和uv_layer
        obj_bm_data = {}  # obj -> (bm, uv_layer, mesh)
        for obj, _ in all_islands:
            if obj not in obj_bm_data:
                if obj.mode != 'EDIT':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                mesh = obj.data
                bm = bmesh.from_edit_mesh(mesh)
                uv_layer = bm.loops.layers.uv.active
                obj_bm_data[obj] = (bm, uv_layer, mesh)
        
        # 计算所有孤岛的边界
        island_bounds = []
        for obj, island_face_indices in all_islands:
            bm, uv_layer, mesh = obj_bm_data[obj]
            bounds = get_island_bounds(island_face_indices, bm, uv_layer)
            island_bounds.append((obj, island_face_indices, bounds, bm, uv_layer, mesh))
    
    # 按照最大V坐标排序（从上到下，从大到小）
    island_bounds.sort(key=lambda x: x[2]['max_v'], reverse=True)
    
    # 垂直排列：保持每个孤岛的U坐标不变，只调整V坐标
    if debug:
        print(f"[DEBUG] 垂直间距排列 - 间距: {spacing:.3f}")
        print(f"[DEBUG] 排序后的孤岛顺序:")
        for i, (obj, _, bounds, _, _, _) in enumerate(island_bounds):
            print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): V范围 [{bounds['min_v']:.3f}, {bounds['max_v']:.3f}], 高度: {bounds['height']:.3f}")
    
    # 第一个孤岛保持原位置，计算下一个位置
    first_obj, first_island, first_bounds, first_bm, first_uv_layer, first_mesh = island_bounds[0]
    current_y = first_bounds['min_v'] - spacing  # 第一个孤岛底部 - 间距
    
    if debug:
        print(f"[DEBUG]   孤岛 1 (物体: {first_obj.name}): 保持原位置 [V: {first_bounds['min_v']:.3f} - {first_bounds['max_v']:.3f}], 下一个位置: {current_y:.3f}")
    
    # 从第二个孤岛开始排列
    for i, (obj, island_face_indices, bounds, bm, uv_layer, mesh) in enumerate(island_bounds[1:], start=1):
        # 计算需要移动的V偏移量（将孤岛的顶部对齐到current_y + bounds['height']位置）
        # 注意：V轴从上到下，所以顶部是max_v
        # 我们要将孤岛的顶部放在 current_y + bounds['height'] 位置
        target_top = current_y + bounds['height']
        offset_v = target_top - bounds['max_v']
        
        if debug:
            print(f"[DEBUG]   孤岛 {i+1} (物体: {obj.name}): 偏移V = {offset_v:.3f}, 从 {bounds['max_v']:.3f} 移动到 {target_top:.3f}, 高度: {bounds['height']:.3f}, 移动 {len(island_face_indices)} 个面")
        
        # 移动整个孤岛的所有面
        moved_faces = 0
        bm.faces.ensure_lookup_table()  # 确保查找表是最新的
        for face_idx in island_face_indices:
            face = safe_get_face(bm, face_idx, debug=debug)
            if face is None:
                continue
            try:
                for loop in face.loops:
                    loop[uv_layer].uv.y += offset_v
                moved_faces += 1
            except (AttributeError, RuntimeError) as e:
                if debug:
                    print(f"[DEBUG]   警告: 无法移动面 {face_idx}: {e}")
                continue
        
        bmesh.update_edit_mesh(mesh)  # 移动后立即更新
        if debug:
            print(f"[DEBUG]   孤岛 {i+1}: 实际移动了 {moved_faces} 个面")
        
        # 更新下一个位置（移动后的底部 - 间距）
        # 移动后，新的底部 = current_y
        current_y = current_y - bounds['height'] - spacing
    
    if debug:
        print(f"[DEBUG] 垂直间距排列完成，处理了 {len(island_bounds)} 个孤岛")
    return True

class UVIslandAlignOperator(bpy.types.Operator):
    bl_idname = "uv.island_align"
    bl_label = "UV孤岛对齐"
    bl_description = "对齐选中的UV孤岛"
    bl_options = {'REGISTER', 'UNDO'}
    
    align_mode: bpy.props.EnumProperty(
        name="对齐方式",
        description="选择对齐方式",
        items=[
            ('TOP', '顶对齐', '所有孤岛顶部对齐'),
            ('CENTER_V', '垂直中心对齐', '所有孤岛垂直中心对齐'),
            ('BOTTOM', '底对齐', '所有孤岛底部对齐'),
            ('LEFT', '左对齐', '所有孤岛左对齐'),
            ('CENTER_H', '水平中心对齐', '所有孤岛水平中心对齐'),
            ('RIGHT', '右对齐', '所有孤岛右对齐'),
        ],
        default='TOP'
    )
    
    def execute(self, context):
        # 支持跨物体操作：从所有选中的物体中收集孤岛
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            if context.active_object and context.active_object.type == 'MESH':
                selected_objects = [context.active_object]
            else:
                self.report({'ERROR'}, "请选择一个网格对象")
                return {'CANCELLED'}
        
        print(f"\n[UV对齐] 开始执行 {self.align_mode} 对齐（处理 {len(selected_objects)} 个物体）")
        success = align_uv_islands(obj=None, align_mode=self.align_mode, debug=True, context=context)
        print(f"[UV对齐] 执行完成，结果: {success}\n")
        
        if success:
            mode_name = {
                'TOP': '顶对齐',
                'CENTER_V': '垂直中心对齐',
                'BOTTOM': '底对齐',
                'LEFT': '左对齐',
                'CENTER_H': '水平中心对齐',
                'RIGHT': '右对齐',
            }.get(self.align_mode, '对齐')
            self.report({'INFO'}, f"UV孤岛{mode_name}完成")
        else:
            self.report({'WARNING'}, "请至少选中2个UV孤岛")
        
        return {'FINISHED'}

# UV编辑器侧边栏面板
class UVIslandAlignPanel(bpy.types.Panel):
    bl_label = "UV孤岛对齐"
    bl_idname = "IMAGE_EDITOR_PT_uv_island_align"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "MixtoolsUV"  # 在UV编辑器侧边栏的"MixtoolsUV"标签页显示
    
    @classmethod
    def poll(cls, context):
        # 在UV编辑器中显示，只要有活动对象即可（不强制要求是MESH，因为可能在编辑其他对象）
        return context.active_object is not None
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="对齐方式:", icon='SNAP_MIDPOINT')
        
        # 垂直对齐按钮
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="顶对齐", icon='TRIA_UP')
        op.align_mode = 'TOP'
        
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="垂直中心", icon='ALIGN_MIDDLE')
        op.align_mode = 'CENTER_V'
        
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="底对齐", icon='TRIA_DOWN')
        op.align_mode = 'BOTTOM'
        
        box.separator()
        
        # 水平对齐按钮
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="左对齐", icon='TRIA_LEFT')
        op.align_mode = 'LEFT'
        
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="水平中心", icon='ALIGN_CENTER')
        op.align_mode = 'CENTER_H'
        
        row = box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_align", text="右对齐", icon='TRIA_RIGHT')
        op.align_mode = 'RIGHT'
        
        layout.separator()
        
        # 间距排列功能
        arrange_box = layout.box()
        arrange_box.label(text="间距排列:", icon='GRID')
        
        # 水平间距排列
        spacing_row = arrange_box.row()
        spacing_row.prop(context.scene, "uv_island_spacing_u", text="水平间距")
        row = arrange_box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_arrange_horizontal", text="水平间距排列", icon='ARROW_LEFTRIGHT')
        
        arrange_box.separator()
        
        # 垂直间距排列
        spacing_row = arrange_box.row()
        spacing_row.prop(context.scene, "uv_island_spacing_v", text="垂直间距")
        row = arrange_box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.island_arrange_vertical", text="垂直间距排列", icon='ARROW_LEFTRIGHT')
        
        layout.separator()
        layout.label(text="提示: 在UV编辑器中选中多个UV孤岛后使用", icon='INFO')
        
        # UV填充功能
        fill_box = layout.box()
        fill_box.label(text="UV填充:", icon='TEXTURE')
        row = fill_box.row(align=True)
        row.scale_y = 1.5
        op = row.operator("uv.fill_texture_with_uv", text="使用UV填充贴图", icon='IMAGE_DATA')
        fill_box.label(text="提示: 使用UV坐标填充当前图像", icon='INFO')
        fill_box.label(text="UV未覆盖区域将填充为黑色", icon='INFO')

class UVIslandArrangeHorizontalOperator(bpy.types.Operator):
    bl_idname = "uv.island_arrange_horizontal"
    bl_label = "UV孤岛水平间距排列"
    bl_description = "按照固定水平间距排列选中的UV孤岛（只调整X轴，保持Y轴不变）"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 支持跨物体操作：从所有选中的物体中收集孤岛
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            if context.active_object and context.active_object.type == 'MESH':
                selected_objects = [context.active_object]
            else:
                self.report({'ERROR'}, "请选择一个网格对象")
                return {'CANCELLED'}
        
        spacing = context.scene.uv_island_spacing_u
        
        print(f"\n[UV水平间距] 开始执行，间距: {spacing:.3f}（处理 {len(selected_objects)} 个物体）")
        success = arrange_uv_islands_horizontal(obj=None, spacing=spacing, debug=True, context=context)
        print(f"[UV水平间距] 执行完成，结果: {success}\n")
        
        if success:
            self.report({'INFO'}, f"UV孤岛水平间距排列完成 (间距: {spacing:.2f})")
        else:
            self.report({'WARNING'}, "请至少选中1个UV孤岛")
        
        return {'FINISHED'}

class UVIslandArrangeVerticalOperator(bpy.types.Operator):
    bl_idname = "uv.island_arrange_vertical"
    bl_label = "UV孤岛垂直间距排列"
    bl_description = "按照固定垂直间距排列选中的UV孤岛（只调整Y轴，保持X轴不变）"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 支持跨物体操作：从所有选中的物体中收集孤岛
        selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected_objects:
            if context.active_object and context.active_object.type == 'MESH':
                selected_objects = [context.active_object]
            else:
                self.report({'ERROR'}, "请选择一个网格对象")
                return {'CANCELLED'}
        
        spacing = context.scene.uv_island_spacing_v
        
        print(f"\n[UV垂直间距] 开始执行，间距: {spacing:.3f}（处理 {len(selected_objects)} 个物体）")
        success = arrange_uv_islands_vertical(obj=None, spacing=spacing, debug=True, context=context)
        print(f"[UV垂直间距] 执行完成，结果: {success}\n")
        
        if success:
            self.report({'INFO'}, f"UV孤岛垂直间距排列完成 (间距: {spacing:.2f})")
        else:
            self.report({'WARNING'}, "请至少选中1个UV孤岛")
        
        return {'FINISHED'}

def fill_texture_with_uv(obj, source_image, target_image):
    """
    使用UV坐标填充贴图
    对于目标图像中UV覆盖的区域，从源图像的相同位置复制像素
    UV未覆盖的区域填充为黑色
    
    Args:
        obj: 编辑模式下的网格对象
        source_image: 源图像（当前正在编辑的图像）
        target_image: 目标图像（将被填充的图像，通常是同一个图像）
    """
    if obj.type != 'MESH':
        return False
    
    if obj.mode != 'EDIT':
        return False
    
    mesh = obj.data
    if not mesh.uv_layers.active:
        return False
    
    # 获取bmesh和UV层
    bm = bmesh.from_edit_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    
    # 获取图像尺寸
    width = source_image.size[0]
    height = source_image.size[1]
    channels = source_image.channels
    
    # 从源图像读取像素数据（先保存原始数据）
    # Blender的pixels是扁平化的，按行存储，每个像素的通道值在[0,1]范围
    # 格式：[R, G, B, A, R, G, B, A, ...] 对于RGBA图像
    source_pixels_flat = np.array(source_image.pixels, dtype=np.float32)
    # reshape为(height, width, channels)，注意numpy是行优先（C顺序）
    source_pixels = source_pixels_flat.reshape((height, width, channels))
    
    # 创建目标图像的像素数组（初始化为黑色）
    target_pixels = np.zeros((height, width, channels), dtype=np.float32)
    
    # 创建一个mask来标记哪些像素被UV覆盖
    uv_mask = np.zeros((height, width), dtype=bool)
    
    # 遍历所有面，标记UV覆盖的区域
    for face in bm.faces:
        if len(face.loops) < 3:
            continue
        
        # 获取面的UV坐标
        uv_coords = []
        for loop in face.loops:
            uv = loop[uv_layer].uv
            uv_coords.append((uv.x, uv.y))
        
        # 将UV坐标转换为目标图像的像素坐标
        # UV坐标范围通常是[0,1]，但可能超出（需要处理）
        pixel_coords = []
        for u, v in uv_coords:
            # UV坐标转换为像素坐标
            # 注意：Blender的UV坐标V轴是从下到上，图像坐标系Y轴是从上到下，所以需要翻转V
            x = u * width
            y = (1.0 - v) * height
            pixel_coords.append((x, y))
        
        # 使用扫描线算法填充多边形
        if len(pixel_coords) >= 3:
            # 获取多边形的边界框
            min_x = min(p[0] for p in pixel_coords)
            max_x = max(p[0] for p in pixel_coords)
            min_y = min(p[1] for p in pixel_coords)
            max_y = max(p[1] for p in pixel_coords)
            
            # 转换为整数像素范围，并限制在图像范围内
            min_x_int = max(0, int(min_x))
            max_x_int = min(width - 1, int(max_x) + 1)
            min_y_int = max(0, int(min_y))
            max_y_int = min(height - 1, int(max_y) + 1)
            
            # 对边界框内的每个像素，检查是否在多边形内
            for py in range(min_y_int, max_y_int + 1):
                for px in range(min_x_int, max_x_int + 1):
                    if px < 0 or px >= width or py < 0 or py >= height:
                        continue
                    
                    # 检查像素中心是否在多边形内
                    if point_in_polygon(px + 0.5, py + 0.5, pixel_coords):
                        uv_mask[py, px] = True
                        # 从源图像的相同位置复制像素
                        target_pixels[py, px] = source_pixels[py, px]
    
    # 将结果写回目标图像
    # Blender的pixels是扁平化的数组，范围是[0,1]
    # 使用flatten('C')确保是C顺序（行优先）
    target_image.pixels = target_pixels.flatten('C')
    target_image.update()
    
    return True

def get_uv_at_pixel(px, py, uv_coords, pixel_coords):
    """
    使用重心坐标计算像素位置对应的UV坐标
    """
    if len(uv_coords) < 3:
        return None
    
    # 对于三角形，使用重心坐标
    if len(uv_coords) == 3:
        p0, p1, p2 = pixel_coords[0], pixel_coords[1], pixel_coords[2]
        uv0, uv1, uv2 = uv_coords[0], uv_coords[1], uv_coords[2]
        
        # 计算重心坐标
        v0 = (p2[0] - p0[0], p2[1] - p0[1])
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (px - p0[0], py - p0[1])
        
        dot00 = v0[0] * v0[0] + v0[1] * v0[1]
        dot01 = v0[0] * v1[0] + v0[1] * v1[1]
        dot02 = v0[0] * v2[0] + v0[1] * v2[1]
        dot11 = v1[0] * v1[0] + v1[1] * v1[1]
        dot12 = v1[0] * v2[0] + v1[1] * v2[1]
        
        inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01 + 1e-10)  # 避免除零
        u_bary = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v_bary = (dot00 * dot12 - dot01 * dot02) * inv_denom
        
        if u_bary >= 0 and v_bary >= 0 and (u_bary + v_bary) <= 1.0:
            # 插值UV坐标
            u = uv0[0] + u_bary * (uv1[0] - uv0[0]) + v_bary * (uv2[0] - uv0[0])
            v = uv0[1] + u_bary * (uv1[1] - uv0[1]) + v_bary * (uv2[1] - uv0[1])
            return (u, v)
    
    # 对于四边形或多边形，分解为三角形处理
    if len(uv_coords) >= 4:
        # 尝试前三个顶点
        result = get_uv_at_pixel(px, py, uv_coords[:3], pixel_coords[:3])
        if result:
            return result
        # 尝试第一个、第三个、第四个顶点
        if len(uv_coords) >= 4:
            tri_uv = [uv_coords[0], uv_coords[2], uv_coords[3]]
            tri_px = [pixel_coords[0], pixel_coords[2], pixel_coords[3]]
            result = get_uv_at_pixel(px, py, tri_uv, tri_px)
            if result:
                return result
    
    return None

def point_in_polygon(x, y, polygon):
    """
    使用射线法判断点是否在多边形内
    支持浮点坐标的多边形
    从点向右发射一条水平射线，计算与多边形边的交点数
    """
    n = len(polygon)
    if n < 3:
        return False
    
    inside = False
    p1x, p1y = polygon[0]
    
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        
        # 检查射线是否与边相交
        # 射线是水平向右的，所以只考虑y坐标在范围内的边
        if (p1y > y) != (p2y > y):  # 边跨越了y坐标
            # 计算射线与边的交点的x坐标
            if p2y != p1y:  # 避免除零
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if x < xinters:  # 交点在点的右侧
                    inside = not inside
        
        p1x, p1y = p2x, p2y
    
    return inside

class UVTextureFillerOperator(bpy.types.Operator):
    bl_idname = "uv.fill_texture_with_uv"
    bl_label = "使用UV填充贴图"
    bl_description = "使用UV坐标填充贴图，UV未覆盖的区域填充为黑色"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # 获取当前编辑模式的对象
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "请选择一个对象")
            return {'CANCELLED'}
        
        if obj.type != 'MESH':
            self.report({'ERROR'}, "选中的对象不是网格对象")
            return {'CANCELLED'}
        
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "请先进入编辑模式")
            return {'CANCELLED'}
        
        # 获取当前图像编辑器中正在编辑的图像
        image = None
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                if space.image:
                    image = space.image
                    break
        
        if not image:
            self.report({'ERROR'}, "请在图像编辑器中打开一个图像")
            return {'CANCELLED'}
        
        # 检查图像是否可编辑
        if image.is_float:
            self.report({'ERROR'}, "不支持浮点图像")
            return {'CANCELLED'}
        
        # 执行填充
        try:
            success = fill_texture_with_uv(obj, image, image)
            if success:
                self.report({'INFO'}, f"已使用UV填充图像: {image.name}")
            else:
                self.report({'WARNING'}, "填充失败，请检查对象是否有UV映射")
        except Exception as e:
            self.report({'ERROR'}, f"填充时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(QuadUVAligner)
    bpy.utils.register_class(UVformater)
    bpy.utils.register_class(CorrectUVRotationOperator)
    bpy.utils.register_class(UVIslandAlignOperator)
    bpy.utils.register_class(UVIslandArrangeHorizontalOperator)
    bpy.utils.register_class(UVIslandArrangeVerticalOperator)
    bpy.utils.register_class(UVIslandAlignPanel)
    bpy.utils.register_class(UVTextureFillerOperator)
    
    # 注册场景属性
    bpy.types.Scene.uv_island_spacing_u = bpy.props.FloatProperty(
        name="水平间距",
        description="UV孤岛之间的水平间距",
        default=0.1,
        min=0.0,
        max=10.0,
        step=0.01
    )
    bpy.types.Scene.uv_island_spacing_v = bpy.props.FloatProperty(
        name="垂直间距",
        description="UV孤岛之间的垂直间距",
        default=0.1,
        min=0.0,
        max=10.0,
        step=0.01
    )

def unregister():
    bpy.utils.unregister_class(UVTextureFillerOperator)
    bpy.utils.unregister_class(UVIslandAlignPanel)
    bpy.utils.unregister_class(UVIslandArrangeVerticalOperator)
    bpy.utils.unregister_class(UVIslandArrangeHorizontalOperator)
    bpy.utils.unregister_class(UVIslandAlignOperator)
    bpy.utils.unregister_class(QuadUVAligner)
    bpy.utils.unregister_class(UVformater)
    bpy.utils.unregister_class(CorrectUVRotationOperator)
    
    # 注销场景属性
    del bpy.types.Scene.uv_island_spacing_u
    del bpy.types.Scene.uv_island_spacing_v