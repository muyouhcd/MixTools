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
                
                obj.hide_viewport = False
                for child in obj.children_recursive:
                    child.hide_viewport = False
                
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                for child in obj.children_recursive:
                    child.select_set(True)
                
                bpy.context.view_layer.objects.active = obj
                setup_view_for_preview(obj)
                
            except Exception as e:
                print(f"准备物体 {obj.name} 时出错: {str(e)}")

        def create_empty_parent(obj):
            try:
                empty = bpy.data.objects.new(f"Empty_{obj.name}", None)
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
                time.sleep(0.5)

                if create_top_level_parent:
                    empty = create_empty_parent(obj)
                    if empty is None:
                        return 0

                bpy.ops.machin3.create_assembly_asset(override)
                time.sleep(0.8)

                if original_parent is not None and obj.name in bpy.data.objects:
                    obj = bpy.data.objects[obj.name]
                    if obj.name in bpy.context.view_layer.objects:
                        obj.parent = original_parent

                self.report({'INFO'}, f"成功处理物体: {obj.name}")
                return 1

            except Exception as e:
                self.report({'ERROR'}, f"处理物体 {obj.name} 时出错: {str(e)}")
                return 0

            finally:
                restore_scene_state(scene_state)
                bpy.context.view_layer.update()
                time.sleep(0.3)

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

        try:
            top_level_objects = [obj for obj in collection.objects if obj.parent is None]
            
            if not top_level_objects:
                self.report({'WARNING'}, "集合中没有顶级物体")
                return {'CANCELLED'}
            
            self.report({'INFO'}, f"开始逐个处理 {len(top_level_objects)} 个物体")
            
            for i, obj in enumerate(top_level_objects):
                if context.window_manager.get('cancel_operation', False):
                    self.report({'INFO'}, "操作被用户取消")
                    return {'CANCELLED'}
                
                self.report({'INFO'}, f"处理物体 {i+1}/{len(top_level_objects)}: {obj.name}")
                
                processed = process_single_object(obj, viewport_area, viewport_region, create_top_level_parent)
                total_processed += processed
                
                bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
                bpy.context.view_layer.update()
                time.sleep(0.3)
                
                import gc
                gc.collect()

            if total_processed > 0:
                self.report({'INFO'}, f"成功处理 {total_processed} 个资产")
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

def unregister():
    bpy.utils.unregister_class(CreateAssemblyAsset)
    
    del bpy.types.Scene.create_top_level_parent
    del bpy.types.Scene.asset_collection

if __name__ == "__main__":
    register() 