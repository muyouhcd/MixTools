import bpy
from mathutils import Vector

def merge_objects_with_same_world_origin():
        origin_dict = {}

        # 遍历场景中的所有物体
        for obj in bpy.context.scene.objects:
            # 只处理网格对象，忽略空物体
            if obj.type == 'MESH':
                # 获取物体的世界坐标
                world_origin = tuple(obj.matrix_world.translation)

                if world_origin not in origin_dict:
                    origin_dict[world_origin] = []

                origin_dict[world_origin].append(obj)

        # 遍历字典中的所有物体列表，并合并具有相同世界坐标的物体
        for world_origin, objects in origin_dict.items():
            if len(objects) > 1:
                bpy.ops.object.select_all(action='DESELECT')

                # 选中这些拥有相同世界坐标的物体
                for obj in objects:
                    obj.select_set(True)
                
                # 设置活动对象
                bpy.context.view_layer.objects.active = objects[0]

                # 合并物体
                bpy.ops.object.join()

                print(f"合并了 {len(objects)} 个在世界坐标 {world_origin} 的物体。")


class CombinSameOriginObject(bpy.types.Operator):
    """合并同原点物体"""
    bl_idname = "object.combin_same_origin_object"
    bl_label = "combin same origin object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        merge_objects_with_same_world_origin()
        print("所有相同世界坐标的物体已合并。")
        return {'FINISHED'}
    
    
def register():
    bpy.utils.register_class(CombinSameOriginObject)

def unregister():
    bpy.utils.unregister_class(CombinSameOriginObject)
