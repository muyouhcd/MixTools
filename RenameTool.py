import bpy
import os
from bpy.types import Operator, Panel, Collection


def rename_texture():
        # 遍历场景中的所有物体
        for obj in bpy.data.objects:
            # 只处理有材质的对象
            if obj.data and hasattr(obj.data, "materials"):
                for mat in obj.data.materials:
                    if mat and mat.node_tree:
                        # 遍历材质节点
                        for node in mat.node_tree.nodes:
                            # 关注Image Texture节点
                            if node.type == 'TEX_IMAGE':
                                if node.image:
                                    # 获取图片的文件路径和名称
                                    image_filepath = node.image.filepath_raw
                                    image_filename = os.path.basename(image_filepath)
                                    image_name, _ = os.path.splitext(image_filename)

                                    # 将贴图的名称改为图片名称
                                    node.image.name = image_name

                                    print(f"更改贴图名称{image_name} <----- {mat.name}.")

        print("All image names have been updated.")

class RenameTextureOrign(bpy.types.Operator):
    bl_idname = "object.rename_texture_orign"
    bl_label = "rename texture name to orign"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rename_texture()
        print("重命名完成")
        return {'FINISHED'}
    
#去除名称后缀
class RemoveNameSuffix(bpy.types.Operator):
    bl_idname = "object.miao_remove_name_suffix"
    bl_label = "移除名称后缀"

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        name_dict = {}

        # 移除后缀，并储存重名的物体
        for obj in selected_objects:
            obj.name = re.sub("(_.*|-.*|\.\d{3}$)", "", obj.name)
            if obj.name in name_dict:
                name_dict[obj.name].append(obj)
            else:
                name_dict[obj.name] = []

        # 根据需要添加后缀
        for obj_name, duplicate_objs in name_dict.items():
            for i, obj in enumerate(duplicate_objs):
                obj.name = obj_name + '.' + str(i + 1).zfill(3)

        return {"FINISHED"}

#移除顶级物体名称后缀，重名则交换
class OBJECT_OT_remove_suffix_and_resolve_conflicts(Operator):
    bl_idname = "object.remove_suffix_and_resolve"
    bl_label = "移除后缀数字，保持顶级无后缀"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 正则表达式，“.数字”的格式
        suffix_pattern = re.compile(r"\.\d+$")

        for obj in bpy.data.objects:
            # 只处理顶级父物体
            if obj.parent == None:
                # 找到并删除后缀
                new_name = re.sub(suffix_pattern, "", obj.name)

                # 检查是否存在名称冲突的子对象
                conflict_child = None
                for child in obj.children:
                    if child.name == new_name:
                        conflict_child = child
                        break

                if conflict_child:  # 如果找到冲突的子对象
                    # 交换名称
                    conflict_child.name = obj.name
                    obj.name = new_name
                else:  # 无冲突的情况下正常改名
                    obj.name = new_name
        return {'FINISHED'}

#更改mesh名称为物体名称
class RenameMeshesOperator(bpy.types.Operator):
    """Rename Meshes to their object names"""      
    bl_idname = "object.rename_meshes"  
    bl_label = "重命名Meshes为物体名称"         
    bl_options = {'REGISTER', 'UNDO'}  
    
    def execute(self, context):       

        # 访问场景中的所有对象
        for obj in bpy.context.scene.objects:
            # 检查对象是否为mesh
            if obj.type == 'MESH':
                # 更改 mesh 数据块的名称为该对象的名称
                obj.data.name = obj.name

        return {'FINISHED'}

class RenameObjectsOperator(bpy.types.Operator):
    """Rename Objects to their mesh names"""
    bl_idname = "object.rename_objects"
    bl_label = "重命名物体为Mesh名称"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                obj.name = obj.data.name

        return {'FINISHED'}

#按照集合中物体位置对应修改名称
def distance(vecA, vecB):
    delta = np.array(vecB) - np.array(vecA)
    return np.linalg.norm(delta)

def center(collection):
    centers = []
    for obj in collection.objects:
        if obj.type == 'MESH':
            world_vertex_coordinates = [obj.matrix_world @ v.co for v in obj.data.vertices]
            center = np.mean(world_vertex_coordinates, axis=0)
            centers.append(center)
    return np.mean(centers, axis=0)

def rename_collections(self, context):
    collectionA = context.scene.collectionA
    collectionB = context.scene.collectionB
    collections_in_B = [coll for coll in collectionB.children]
    top_level_objs_in_A = [obj for obj in collectionA.objects if obj.parent is None]

    for collB in collections_in_B:
        closest_top_objA = min(top_level_objs_in_A, key=lambda objA: distance(center(collB), objA.location))
        collB.name = closest_top_objA.name

class OBJECT_OT_RenameButton(bpy.types.Operator):
    bl_idname = "object.miao_rename_collections"
    bl_label = "Rename Collections"
    bl_description = "Rename collections based on closest object in target collection"

    def execute(self, context):
        rename_collections(self, context)
        return {'FINISHED'}

# 按照空间前后顺序对所选物体重命名
class RenameByLocation(bpy.types.Operator):
    bl_idname = "object.miao_rename_location"
    bl_label = "按轴空间顺序重命名"

    def execute(self, context):

        rename_axis = bpy.context.scene.rename_axis
        rename_order = bpy.context.scene.rename_order

        # 获取所选轴的整数索引
        axis_index = "XYZ".index(rename_axis)

        selected_objs = bpy.context.selected_objects
        locations = [(obj.name, obj.location) for obj in selected_objs]

        # 按轴空间顺序排序
        locations_sorted = sorted(locations, key=lambda x: x[1][axis_index])
        if rename_order == "DESC":
            locations_sorted.reverse()

        # 遍历排序后的物体列表，对每个物体进行重命名
        for i, loc in enumerate(locations_sorted):
            obj_name = 'Object{}'.format(i+1)
            bpy.data.objects[loc[0]].name = obj_name

        return {"FINISHED"}

#重命名为所处集合名称
class RenameSelectedObjects(bpy.types.Operator):
    bl_idname = "object.rename_to_collection"
    bl_label = "所选物体命名为其所在集合名称"

    def execute(self, context):
        # 获取当前选中的物体
        selected_objects = context.selected_objects
        
        for obj in selected_objects:
            # 创建一个列表用来存储obj的所有父集合
            parents = []
            
            # 遍历所有集合以找到obj的父辈
            for coll in bpy.data.collections:
                if obj.name in coll.objects:
                    parents.append(coll)
            
            # 只有当obj有父集合时，才给obj重命名
            if parents:
                # 根据索引，obj的新名字将等于第一个父集合的名字
                obj.name = parents[0].name

        return {"FINISHED"}


def register():     
    bpy.utils.register_class(RenameTextureOrign)
    bpy.utils.register_class(RemoveNameSuffix)
    bpy.utils.register_class(OBJECT_OT_remove_suffix_and_resolve_conflicts)
    bpy.utils.register_class(RenameMeshesOperator)
    bpy.utils.register_class(RenameObjectsOperator)
    bpy.utils.register_class(OBJECT_OT_RenameButton)
    bpy.utils.register_class(RenameByLocation)
    bpy.utils.register_class(RenameSelectedObjects)

def unregister():
    bpy.utils.unregister_class(RenameTextureOrign)
    bpy.utils.unregister_class(RemoveNameSuffix)
    bpy.utils.unregister_class(OBJECT_OT_remove_suffix_and_resolve_conflicts)
    bpy.utils.unregister_class(RenameMeshesOperator)
    bpy.utils.unregister_class(RenameObjectsOperator)
    bpy.utils.unregister_class(OBJECT_OT_RenameButton)
    bpy.utils.unregister_class(RenameByLocation)
    bpy.utils.unregister_class(RenameSelectedObjects)


