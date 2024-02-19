import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict
from mathutils.bvhtree import BVHTree
from mathutils.bvhtree import BVHTree
from mathutils import kdtree

class CharOperaterBoneWeight(bpy.types.Operator):
    bl_idname = "object.char_operater_bone_weight"
    bl_label = "执行自定义操作"

    def execute(self, context):

        def rename_all_children_based_on_collection(empty_coll_name):
            # 获取包含空物体的集合
            empty_collection = bpy.data.collections[empty_coll_name]

            # 初始化一个字典来保存BVH树
            objects_bvh = {}

            def create_bvh_tree(obj):
                bm = bmesh.new()
                bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
                bmesh.ops.transform(bm, verts=bm.verts, matrix=obj.matrix_world)
        
                bvh = BVHTree.FromBMesh(bm)
                bm.free()
                return bvh

            # 遍历场景中的所有物体，为所有的模型物体创建BVH树
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    objects_bvh[obj] = create_bvh_tree(obj)
        
            # 初始化一个字典来过滤已经被重新命名的物体
            renamed_objects = {}

            # 遍历空物体集合中的所有物体
            for obj in empty_collection.objects:
                if "_example" in obj.name and obj.type == 'EMPTY':
                    # 获取不包含"example"的名称
                    new_name = obj.name.replace("_example", "")
                    
                    # 检查每个模型物体是否包含这个空物体
                    for other_obj, _ in objects_bvh.items():
                        # 如果物体被修改了，我们需要重新生成bvh tree
                        if other_obj.is_modified(bpy.context.scene, 'PREVIEW'):
                            objects_bvh[other_obj] = create_bvh_tree(other_obj)

                        # 获取空物体的全局位置
                        global_location = obj.matrix_world.translation

                        intersection_count = 0
                        ray_origin = global_location
                        ray_direction = Vector((0, 0, -1))
                        bvh = objects_bvh[other_obj]

                        while True:
                            hit, _, _, _ = bvh.ray_cast(ray_origin, ray_direction)
                            if hit is None:
                                break
                            intersection_count += 1
                            ray_origin = hit + ray_direction * 0.00001  

                        # 如果交叉次数为奇数，则该点在物体内部
                        if intersection_count % 2 == 1:
                            if other_obj not in renamed_objects:
                                other_obj.name = new_name
                                renamed_objects[other_obj] = True
                                
        # 检查一个物体及其所有的子物体是否为Empty类型
        def all_children_empty(object):
            if object.type != 'EMPTY':
                return False
            for child in object.children:
                if not all_children_empty(child):
                    return False
            return True

        def duplicate_bones_to_objects():
            scene_objects = bpy.data.objects

            bip001_bone = bpy.data.objects.get('Bip001_example')  # 获取名为Bip001的骨架

            if not bip001_bone or bip001_bone.type != 'ARMATURE':  # 确保Bip001存在且是骨架类型
                print('Bip001 armature not found or not of ARMATURE type.')
                return

            for object in scene_objects:
                if object.parent is None:  # 找到顶级父物体
                    # 如果物体以及所有的子物体都为Empty类型，那么跳过
                    if all_children_empty(object):
                        continue
                    dup_bone = bip001_bone.copy()  # 复制骨架，会包含所有骨骼
                    dup_bone.name = 'Bip001'
                    dup_bone.data = bip001_bone.data.copy()  # 复制骨架的Armature数据
                    dup_bone.data.name = "Bip001" 

                    # 把复制的骨架移动到父物体的集合中
                    object.users_collection[0].objects.link(dup_bone)

                    dup_bone.matrix_world = bip001_bone.matrix_world  # 设置复制骨架的位置为原骨架位置

                    dup_bone.parent = object  # 设置原父物体为复制骨架的父物体

                    # 绑定过程
                    for child_obj in object.children:
                        if child_obj.type == 'MESH':
                            #对象与骨骼名字的比较规则改为物体名称前加 "Bip001 "
                            bone_name = "Bip001 " + child_obj.name.split('.')[0]

                            # 创建骨骼修改器
                            modifier = child_obj.modifiers.new(name='ArmatureMod', type='ARMATURE')
                            modifier.object = dup_bone
                            modifier.use_vertex_groups = True

                            # 添加顶点组并设置权重为 1
                            group = child_obj.vertex_groups.new(name=bone_name)
                            for v in child_obj.data.vertices:
                                group.add([v.index], 1.0, 'ADD')

        def get_top_parent(obj):
            """此函数用于获取物体的顶级父物体"""
            while obj.parent is not None:
                obj = obj.parent
            return obj if obj else None

        def create_parent_dict(name_list):
            # 使用字典保存顶级父物体的mesh子物体
            top_parents = {}  
            for obj in bpy.context.scene.objects:  # 遍历场景中的所有物体
                # 如果物体是mesh并且名字中包含给定的关键字
                if obj.type == 'MESH' and any(name in obj.name for name in name_list):
                    top_parent = get_top_parent(obj)
                    if top_parent is None:
                        top_parent = obj  # 如果没有父对象，则顶级父对象是对象本身
                    if top_parent not in top_parents:
                        top_parents[top_parent] = []
                    top_parents[top_parent].append(obj)
            return top_parents

        def join_objects(parent_dict, new_name):
            for top_parent, objects in parent_dict.items():
                bpy.ops.object.select_all(action='DESELECT')  # 全部取消选中
                for obj in objects:
                    obj.select_set(True)  # 设置物体为选中

                if bpy.context.selected_objects:  # 如果有选中的物体
                    ctx = bpy.context.copy()
                    ctx['active_object'] = bpy.context.selected_objects[0]
                    ctx['selected_editable_objects'] = bpy.context.selected_objects
                    bpy.ops.object.join(ctx)  # 合并选中的物体

        def create_contact_vertex_groups(input_objects, threshold_distance):
            # 设定已存在的物体名
            objects = {obj.name: obj for obj in input_objects}

            # 提前设定好每个物体的KD树和BMesh实例
            kdtrees = {}
            bm_objects = {}
            for obj_name, obj in objects.items():
                bm_objects[obj_name] = bmesh.new()
                bm_objects[obj_name].from_mesh(obj.data)
                kdtrees[obj_name] = kdtree.KDTree(len(bm_objects[obj_name].verts))
                for i, v in enumerate(bm_objects[obj_name].verts):
                    kdtrees[obj_name].insert(obj.matrix_world @ v.co, i)
                kdtrees[obj_name].balance()

            # 准备顶点组字典
            vertex_groups = defaultdict(dict)

            for obj_a in input_objects:
                obj_a_name = obj_a.name
                # 准备与其他物体的联系顶点组
                for obj_b in input_objects:
                    if obj_a != obj_b:
                        group_name = f'Bip001 {obj_b.name}'
                        vertex_groups[obj_a][obj_b] = (obj_a.vertex_groups.new(name=group_name)
                                                    if group_name not in obj_a.vertex_groups else
                                                    obj_a.vertex_groups[group_name])

            for obj_a in input_objects:
                obj_a_name = obj_a.name
                bm_a = bm_objects[obj_a_name]
                kd_tree_a = kdtrees[obj_a_name]
                for obj_b in input_objects:
                    if obj_a != obj_b:
                        kd_tree_b = kdtrees[obj_b.name]
                        vertex_group = vertex_groups[obj_a][obj_b]
                        # 遍历对象A的每个顶点，识别接触面顶点并分配权重给顶点组
                        for i, v in enumerate(bm_a.verts):
                            global_v_co = obj_a.matrix_world @ v.co
                            closest_co, closest_index, dist = kd_tree_b.find(global_v_co)
                            if dist < threshold_distance:
                                weight = 1.0 - dist / threshold_distance
                                vertex_group.add([v.index], weight, 'REPLACE')

            # 释放BMesh资源
            for bm in bm_objects.values():
                bm.free()

            # 更新网格数据以反映改变
            for obj in input_objects:
                obj.data.update()

            print("Contact weights assigned for all object combinations, and self vertex groups created with full weight.")
          
        def filter_objects_by_name_patterns(objects, name_patterns):
            filtered_objects = []
            for obj in objects:
                if obj.type == 'MESH' and any(name_pattern in obj.name for name_pattern in name_patterns):
                    filtered_objects.append(obj)
            return filtered_objects

        name_groups = [
            (["Head", "Neck"], "Face"),
        #    (["Head", ], "Face"),
            (["Spine", "UpperArm", "Forearm", "Hand", "Finger"], "UpperBody"),
            (["Pelvis",], "Pelvis"),
            (["Thigh", "Calf",], "LowerBody"),
            (["Foot", "Toe0",], "Feet")
        ]

        named_group = [
            {'L Finger11', 'L Finger1'},
            {'L Finger01', 'L Finger0'},
            {'L Finger21', 'L Finger2'},
            {'R Finger11', 'R Finger1'},
            {'R Finger01', 'R Finger0'},
            {'R Finger21', 'R Finger2'},
            {'Pelvis', 'Spine2', 'Spine1', 'Spine'}
        ]
        
        #清理场景
        bpy.ops.object.miao_clean_sense()
        #按照空物体标记重命名物体
        rename_all_children_based_on_collection("name_example")

        def process_contact_weights():
            threshold_distance = bpy.context.scene.threshold_distance
            if bpy.context.scene.assign_contact_weights:
                print("Processing contact weights...")
                # 对每个顶级父物体和每对分组应用接触检测和权重赋值操作
                all_objects = bpy.context.scene.objects
                # 针对每个名称组过滤物体并计算接触权重
                for name_patterns in named_group:
                    # 过滤物体
                    group_objects = filter_objects_by_name_patterns(all_objects, name_patterns)
                    # 计算接触权重，只有当组内至少有两个物体时才进行操作
                    create_contact_vertex_groups(group_objects, threshold_distance)
                pass
            else:
                print("Skipping contact weight assignment...")

        #判定是否需要赋予权重
        process_contact_weights()
        #绑定骨骼
        duplicate_bones_to_objects()
        #合并身体部件
        parent_dict_list = [(create_parent_dict(name_list), new_name) for name_list, new_name in name_groups]
        for parent_dict, new_name in parent_dict_list:
            join_objects(parent_dict, new_name)
        rename_all_children_based_on_collection("name_example_comb")

        return {'FINISHED'}
    

def register():
    bpy.utils.register_class(CharOperaterBoneWeight)

def unregister():
    bpy.utils.unregister_class(CharOperaterBoneWeight)
