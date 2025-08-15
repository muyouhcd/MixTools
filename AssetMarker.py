import bpy
import time
from mathutils import Vector

class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "object.mian_create_assembly_asset"
    bl_label = "批量标记资产（需要m3插件）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not hasattr(bpy.ops, 'machin3'):
            self.report({'ERROR'}, "请先安装并启用 Machin3tools 插件")
            return {'CANCELLED'}

        def get_top_level_name(obj):
            """获取物体的顶级父级名称，如果没有父级则返回物体自身名称"""
            current_obj = obj
            while current_obj.parent is not None:
                current_obj = current_obj.parent
            return current_obj.name

        def get_3d_view_region():
            for area in bpy.context.window.screen.areas:
                if area.type == 'VIEW_3D':
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            return area, region
            return None, None

        def save_scene_state():
            try:
                state = {
                    'visible_objects': {ob.name: ob.hide_viewport for ob in bpy.context.visible_objects},
                    'selected_objects': {ob.name: ob.select_get() for ob in bpy.context.visible_objects},
                    'active_object': bpy.context.active_object.name if bpy.context.active_object else None,
                    'view_settings': {
                        'view_perspective': context.space_data.region_3d.view_perspective,
                        'view_rotation': context.space_data.region_3d.view_rotation.copy(),
                        'view_distance': context.space_data.region_3d.view_distance
                    }
                }
                return state
            except Exception as e:
                print(f"保存场景状态时出错: {str(e)}")
                return None

        def restore_scene_state(state):
            if state is None:
                return
            try:
                for obj_name, visibility in state['visible_objects'].items():
                    if obj_name in bpy.data.objects:
                        obj = bpy.data.objects[obj_name]
                        if obj.name in bpy.context.view_layer.objects:
                            obj.hide_viewport = visibility
                
                for obj_name, selected in state['selected_objects'].items():
                    if obj_name in bpy.data.objects:
                        obj = bpy.data.objects[obj_name]
                        if obj.name in bpy.context.view_layer.objects:
                            obj.select_set(selected)
                
                if state['active_object'] and state['active_object'] in bpy.data.objects:
                    active_obj = bpy.data.objects[state['active_object']]
                    if active_obj.name in bpy.context.view_layer.objects:
                        bpy.context.view_layer.objects.active = active_obj

                if 'view_settings' in state:
                    context.space_data.region_3d.view_perspective = state['view_settings']['view_perspective']
                    context.space_data.region_3d.view_rotation = state['view_settings']['view_rotation']
                    context.space_data.region_3d.view_distance = state['view_settings']['view_distance']

            except Exception as e:
                print(f"恢复场景状态时出错: {str(e)}")

        def setup_view_for_preview(obj):
            try:
                # 收集所有mesh物体（包括主物体和子物体）
                mesh_objects = []
                
                # 添加主物体（如果是mesh类型）
                if obj.type == 'MESH':
                    mesh_objects.append(obj)
                
                # 添加所有子物体中的mesh物体
                for child in obj.children_recursive:
                    if child.type == 'MESH':
                        mesh_objects.append(child)
                
                if not mesh_objects:
                    # 如果没有mesh物体，使用原始方法
                    bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                    min_corner = Vector((min(c.x for c in bbox_corners),
                                       min(c.y for c in bbox_corners),
                                       min(c.z for c in bbox_corners)))
                    max_corner = Vector((max(c.x for c in bbox_corners),
                                       max(c.y for c in bbox_corners),
                                       max(c.z for c in bbox_corners)))
                else:
                    # 计算所有mesh物体的边界框
                    all_corners = []
                    for mesh_obj in mesh_objects:
                        if hasattr(mesh_obj, 'bound_box') and mesh_obj.bound_box:
                            corners = [mesh_obj.matrix_world @ Vector(corner) for corner in mesh_obj.bound_box]
                            all_corners.extend(corners)
                    
                    if all_corners:
                        min_corner = Vector((min(c.x for c in all_corners),
                                           min(c.y for c in all_corners),
                                           min(c.z for c in all_corners)))
                        max_corner = Vector((max(c.x for c in all_corners),
                                           max(c.y for c in all_corners),
                                           max(c.z for c in all_corners)))
                    else:
                        # 如果无法获取边界框，使用原始方法
                        bbox_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                        min_corner = Vector((min(c.x for c in bbox_corners),
                                           min(c.y for c in bbox_corners),
                                           min(c.z for c in bbox_corners)))
                        max_corner = Vector((max(c.x for c in bbox_corners),
                                           max(c.y for c in bbox_corners),
                                           max(c.z for c in bbox_corners)))
                
                center = (min_corner + max_corner) / 2
                size = max_corner - min_corner
                max_dim = max(size.x, size.y, size.z)
                
                current_view = context.space_data.region_3d.view_rotation.copy()
                current_distance = context.space_data.region_3d.view_distance
                current_perspective = context.space_data.region_3d.view_perspective
                
                context.space_data.region_3d.view_distance = max_dim * 2
                context.space_data.region_3d.view_rotation = current_view
                context.space_data.region_3d.view_perspective = current_perspective
                context.space_data.region_3d.update()
                
            except Exception as e:
                print(f"设置预览视图时出错: {str(e)}")

        def prepare_object_for_asset(obj):
            try:
                for ob in bpy.context.visible_objects:
                    if ob != obj and ob not in obj.children_recursive:
                        ob.hide_viewport = True
                
                # 显示主物体和所有子物体
                obj.hide_viewport = False
                for child in obj.children_recursive:
                    child.hide_viewport = False
                
                bpy.ops.object.select_all(action='DESELECT')
                
                # 选中完整的资产结构
                obj.select_set(True)
                for child in obj.children_recursive:
                    child.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # 使用mesh物体计算视图距离，但不改变选中状态
                mesh_objects = []
                if obj.type == 'MESH':
                    mesh_objects.append(obj)
                for child in obj.children_recursive:
                    if child.type == 'MESH':
                        mesh_objects.append(child)
                
                # 如果有mesh物体，使用mesh物体计算视图距离
                if mesh_objects:
                    setup_view_for_preview(obj)
                else:
                    setup_view_for_preview(obj)
                
            except Exception as e:
                print(f"准备物体 {obj.name} 时出错: {str(e)}")

        def create_empty_parent(obj):
            try:
                # 使用顶级名称创建空物体，添加序号避免重名
                top_level_name = get_top_level_name(obj)
                
                # 生成唯一的空物体名称
                base_name = f"Empty_{top_level_name}"
                counter = 1
                empty_name = base_name
                
                # 检查名称是否已存在，如果存在则添加序号
                while empty_name in bpy.data.objects:
                    empty_name = f"{base_name}_{counter:03d}"
                    counter += 1
                
                empty = bpy.data.objects.new(empty_name, None)
                scene = bpy.context.scene
                scene.collection.objects.link(empty)

                obj_old_parent = obj.parent
                obj.parent = empty
                empty.parent = obj_old_parent

                return empty
            except Exception as e:
                print(f"创建空物体父级时出错: {str(e)}")
                return None

        def process_single_object(obj, viewport_area, viewport_region, create_top_level_parent):
            # 只处理顶级物体（没有父级的物体）
            if obj.parent is not None:
                return 0

            try:
                if obj.name not in bpy.data.objects:
                    print(f"对象 {obj.name} 已不存在于场景中")
                    return 0

                if not obj or obj.type not in ['MESH', 'EMPTY', 'CURVE', 'SURFACE', 'META', 'FONT', 'ARMATURE', 'LATTICE']:
                    print(f"跳过无效对象: {obj.name}")
                    return 0

                scene_state = save_scene_state()
                original_parent = obj.parent

                prepare_object_for_asset(obj)

                override = context.copy()
                override['area'] = viewport_area
                override['region'] = viewport_region

                bpy.ops.view3d.view_selected(override)
                bpy.context.view_layer.update()
                time.sleep(0.3)  # 减少等待时间

                # 获取顶级名称
                top_level_name = get_top_level_name(obj)
                
                # 保存原始名称
                original_name = obj.name
                
                # 临时重命名物体为顶级名称，这样资产名称就会使用顶级名称
                obj.name = top_level_name
                
                # 如果有资产数据，也预先设置资产名称
                if hasattr(obj, 'asset_data') and obj.asset_data:
                    try:
                        if hasattr(obj.asset_data, 'name'):
                            obj.asset_data.name = top_level_name
                    except:
                        pass
                
                if create_top_level_parent:
                    empty = create_empty_parent(obj)
                    if empty is None:
                        return 0
                    else:
                        self.report({'INFO'}, f"为物体 {original_name} 创建了顶级父物体: {empty.name}")

                # 记录创建资产前的物体列表
                objects_before = set(bpy.data.objects.keys())
                
                bpy.ops.machin3.create_assembly_asset(override)
                
                # 等待一下让 Machin3tools 完成资产创建
                time.sleep(0.8)  # 减少等待时间
                
                # 恢复原始名称
                obj.name = original_name
                
                # 检测新创建的资产对象
                objects_after = set(bpy.data.objects.keys())
                new_objects = objects_after - objects_before
                
                # 处理新创建的资产对象
                for new_obj_name in new_objects:
                    new_obj = bpy.data.objects[new_obj_name]
                    if hasattr(new_obj, 'asset_data') and new_obj.asset_data:
                        # 调试信息：打印资产数据的属性
                        self.report({'INFO'}, f"检测到新资产对象: {new_obj_name}")
                        self.report({'INFO'}, f"资产数据类型: {type(new_obj.asset_data)}")
                        self.report({'INFO'}, f"资产数据属性: {dir(new_obj.asset_data)}")
                        
                        # 尝试直接修改物体名称，这可能会影响资产名称
                        if new_obj.name != top_level_name:
                            original_obj_name = new_obj.name
                            new_obj.name = top_level_name
                            self.report({'INFO'}, f"已修改物体名称: {original_obj_name} -> {top_level_name}")
                        
                        # 尝试修改资产数据
                        try:
                            # 尝试不同的方法修改资产名称
                            if hasattr(new_obj.asset_data, 'name'):
                                new_obj.asset_data.name = top_level_name
                                self.report({'INFO'}, f"已修改资产数据名称: {new_obj.asset_data.name}")
                            
                            # 尝试通过资产库修改
                            if hasattr(bpy.data, 'assets'):
                                for asset in bpy.data.assets:
                                    if asset.name == original_obj_name or asset.name.endswith('AssemblyAsset'):
                                        asset.name = top_level_name
                                        self.report({'INFO'}, f"已修改资产库中的资产名称: {asset.name}")
                                        break
                            
                            # 尝试通过资产标记修改
                            if hasattr(new_obj, 'asset_mark'):
                                new_obj.asset_mark = top_level_name
                                self.report({'INFO'}, f"已修改资产标记: {new_obj.asset_mark}")
                                
                        except Exception as e:
                            self.report({'WARNING'}, f"修改资产名称时出错: {str(e)}")
                        
                        # 强制更新资产库
                        try:
                            bpy.ops.asset.library_refresh()
                            self.report({'INFO'}, "已刷新资产库")
                        except:
                            pass
                time.sleep(0.5)  # 减少等待时间

                if original_parent is not None and obj.name in bpy.data.objects:
                    obj = bpy.data.objects[obj.name]
                    if obj.name in bpy.context.view_layer.objects:
                        obj.parent = original_parent

                # 使用顶级名称报告处理结果
                self.report({'INFO'}, f"成功处理物体: {original_name} -> 资产名称: {top_level_name}")
                return 1

            except Exception as e:
                self.report({'ERROR'}, f"处理物体 {obj.name} 时出错: {str(e)}")
                return 0

            finally:
                restore_scene_state(scene_state)
                bpy.context.view_layer.update()
                time.sleep(0.2)  # 减少等待时间

        def process_batch(objects_batch, viewport_area, viewport_region, create_top_level_parent, batch_num, total_batches):
            """处理一批物体"""
            batch_processed = 0
            self.report({'INFO'}, f"开始处理第 {batch_num}/{total_batches} 批，包含 {len(objects_batch)} 个物体")
            
            for i, obj in enumerate(objects_batch):
                if context.window_manager.get('cancel_operation', False):
                    self.report({'INFO'}, "操作被用户取消")
                    return batch_processed
                
                top_level_name = get_top_level_name(obj)
                self.report({'INFO'}, f"批次 {batch_num}: 处理物体 {i+1}/{len(objects_batch)}: {obj.name} (顶级名称: {top_level_name})")
                
                processed = process_single_object(obj, viewport_area, viewport_region, create_top_level_parent)
                batch_processed += processed
                
                # 每处理几个物体后进行一次轻量级更新
                if (i + 1) % 3 == 0:
                    bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                    bpy.context.view_layer.update()
            
            return batch_processed

        def cleanup_between_batches():
            """在批次之间进行清理"""
            try:
                # 强制垃圾回收
                import gc
                gc.collect()
                
                # 清理未使用的数据块
                bpy.ops.outliner.orphans_purge(do_recursive=True)
                
                # 刷新视图层
                bpy.context.view_layer.update()
                
                # 短暂休息让系统恢复
                time.sleep(0.5)
                
                self.report({'INFO'}, "批次间清理完成")
                
            except Exception as e:
                self.report({'WARNING'}, f"批次间清理时出错: {str(e)}")

        collection_name = context.scene.asset_collection.name
        collection = bpy.data.collections.get(collection_name)

        if not collection:
            self.report({'ERROR'}, "没有选择任何集合")
            return {'CANCELLED'}

        viewport_area, viewport_region = get_3d_view_region()
        if not viewport_area:
            self.report({'ERROR'}, "没有找到 3D 视口")
            return {'CANCELLED'}

        create_top_level_parent = context.scene.create_top_level_parent
        total_processed = 0

        def get_all_objects_recursive(collection):
            """递归获取集合及其子集合中的所有物体"""
            objects = []
            
            # 添加当前集合中的物体
            for obj in collection.objects:
                objects.append(obj)
            
            # 递归处理子集合
            for child_collection in collection.children:
                objects.extend(get_all_objects_recursive(child_collection))
            
            return objects
        
        try:
            # 递归获取所有物体
            all_objects = get_all_objects_recursive(collection)
            
            # 过滤出顶级物体（没有父级的物体）
            top_level_objects = [obj for obj in all_objects if obj.parent is None]
            
            if not top_level_objects:
                self.report({'WARNING'}, "集合及其子集合中没有顶级物体")
                return {'CANCELLED'}
            
            # 获取批次大小设置
            batch_size = context.scene.batch_size
            
            # 将物体分组
            total_objects = len(top_level_objects)
            total_batches = (total_objects + batch_size - 1) // batch_size  # 向上取整
            
            self.report({'INFO'}, f"总共 {total_objects} 个物体，将分为 {total_batches} 批处理，每批最多 {batch_size} 个物体")
            
            # 分批处理
            for batch_num in range(total_batches):
                if context.window_manager.get('cancel_operation', False):
                    self.report({'INFO'}, "操作被用户取消")
                    break
                
                # 计算当前批次的物体
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, total_objects)
                current_batch = top_level_objects[start_idx:end_idx]
                
                # 处理当前批次
                batch_processed = process_batch(
                    current_batch, 
                    viewport_area, 
                    viewport_region, 
                    create_top_level_parent,
                    batch_num + 1,
                    total_batches
                )
                
                total_processed += batch_processed
                
                # 如果不是最后一批，进行批次间清理
                if batch_num < total_batches - 1:
                    self.report({'INFO'}, f"第 {batch_num + 1} 批处理完成，已处理 {total_processed} 个物体，开始清理...")
                    cleanup_between_batches()
                
                # 更新进度
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                bpy.context.view_layer.update()

            if total_processed > 0:
                self.report({'INFO'}, f"所有批次处理完成！成功处理 {total_processed} 个资产")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "没有处理任何资产")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"发生错误: {str(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(CreateAssemblyAsset)
    
    bpy.types.Scene.create_top_level_parent = bpy.props.BoolProperty(
        name="创建顶级父物体",
        description="设置是否为每个资产创建一个顶级父物体",
        default=True
    )
    bpy.types.Scene.asset_collection = bpy.props.PointerProperty(
        name="集合",
        description="选择将要标记资产的集合",
        type=bpy.types.Collection
    )
    bpy.types.Scene.batch_size = bpy.props.IntProperty(
        name="批次大小",
        description="每批处理的物体数量，较小的批次可以防止性能下降",
        default=5,
        min=1,
        max=20
    )

def unregister():
    bpy.utils.unregister_class(CreateAssemblyAsset)
    
    del bpy.types.Scene.create_top_level_parent
    del bpy.types.Scene.asset_collection
    del bpy.types.Scene.batch_size

if __name__ == "__main__":
    register() 