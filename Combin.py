import bpy
import bmesh

def merge_objects_with_same_world_origin():
    origin_dict = {}
    wm = bpy.context.window_manager

    # 统计物体的原点坐标
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            world_origin = tuple(obj.matrix_world.translation)
            if world_origin not in origin_dict:
                origin_dict[world_origin] = []
            origin_dict[world_origin].append(obj)

    total_groups = len(origin_dict)
    wm.progress_begin(0, total_groups)
    
    # 遍历字典，并分批合并具有相同世界坐标的物体
    for index, (world_origin, objects) in enumerate(origin_dict.items(), start=1):
        if len(objects) > 1:
            # 更新进度条
            wm.progress_update(index)
            # 只合并具有相同坐标的物体
            merge_objects_bmesh(objects)
            print(f"合并了 {len(objects)} 个在世界坐标 {world_origin} 的物体。")
    
    wm.progress_end()
    bpy.context.view_layer.update()  # 在所有操作都完成之后再进行视图更新

def merge_objects_bmesh(objects):
    # 创建一个新的BMesh对象
    bm = bmesh.new()

    # 使用depsgraph获取评估后的对象数据
    depsgraph = bpy.context.evaluated_depsgraph_get()
    
    for obj in objects:
        # 建立新网格数据并转换为BMesh
        ob_eval = obj.evaluated_get(depsgraph)
        mesh = ob_eval.to_mesh()
        bmesh_data = bmesh.new()
        bmesh_data.from_mesh(mesh)
        
        # 将变换后的网格数据复制到BMesh中
        transform_matrix = obj.matrix_world
        bmesh.ops.transform(bmesh_data, matrix=transform_matrix, verts=bmesh_data.verts)
        bm.from_mesh(mesh)
        
        # 清理并释放临时网格数据
        bmesh_data.free()
        ob_eval.to_mesh_clear()

    # 创建一个新的网格并将合并后的BMesh指定给它
    new_mesh = bpy.data.meshes.new("Merged_Mesh")
    bm.to_mesh(new_mesh)
    bm.free()

    new_object = bpy.data.objects.new("Merged_Object", new_mesh)
    bpy.context.collection.objects.link(new_object)

    # 保持新对象在第一个对象的位置
    new_object.matrix_world = objects[0].matrix_world

    # 删除原始对象
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)

class CombinSameOriginObject(bpy.types.Operator):
    """合并同原点物体"""
    bl_idname = "object.combin_same_origin_object"
    bl_label = "Combin Same Origin Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merge_objects_with_same_world_origin()
        print("所有相同世界坐标的物体已合并。")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(CombinSameOriginObject)

def unregister():
    bpy.utils.unregister_class(CombinSameOriginObject)
