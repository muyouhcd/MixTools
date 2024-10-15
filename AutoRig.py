import bpy
import bmesh
import random
from mathutils import Vector
from collections import defaultdict
from mathutils.bvhtree import BVHTree
from mathutils import kdtree
import math



name_groups = [
    (["Head", "Neck"], "Face"),
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
empty_coords_name_example = [
    ("R Toe0_example", Vector((-0.0922, -0.1240, 0.0156))),
    ("R Foot_example", Vector((-0.0938, -0.0028, 0.0340))),
    ("R Calf_example", Vector((-0.0938, 0.0321, 0.2991))),
    ("L Toe0_example", Vector((0.0922, -0.1240, 0.0156))),
    ("L Foot_example", Vector((0.0938, -0.0028, 0.0340))),
    ("L Calf_example", Vector((0.0938, 0.0321, 0.2991))),
    ("Spine_example", Vector((0.0000, 0.0270, 1.0378))),
    ("Spine2_example", Vector((0.0000, 0.0171, 1.2895))),
    ("Spine1_example", Vector((0.0000, 0.0134, 1.1500))),
    ("R UpperArm_example", Vector((-0.2765, 0.0021, 1.3281))),
    ("R Thigh_example", Vector((-0.0952, 0.0234, 0.6991))),
    ("R Hand_example", Vector((-0.6875, 0.0076, 1.3359))),
    ("R Forearm_example", Vector((-0.5391, 0.0076, 1.3359))),
    ("R Finger2_example", Vector((-0.7500, 0.0232, 1.3438))),
    ("R Finger21_example", Vector((-0.7878, 0.0212, 1.3438))),
    ("R Finger1_example", Vector((-0.7500, -0.0237, 1.3438))),
    ("R Finger11_example", Vector((-0.7891, -0.0237, 1.3438))),
    ("R Finger0_example", Vector((-0.7109, -0.0471, 1.3125))),
    ("R Finger01_example", Vector((-0.7422, -0.0471, 1.3125))),
    ("Pelvis_example", Vector((0.0000, 0.0306, 0.9380))),
    ("L UpperArm_example", Vector((0.2765, 0.0021, 1.3281))),
    ("L Thigh_example", Vector((0.0952, 0.0234, 0.6991))),
    ("L Hand_example", Vector((0.6875, 0.0076, 1.3359))),
    ("L Forearm_example", Vector((0.5391, 0.0076, 1.3359))),
    ("L Finger2_example", Vector((0.7500, 0.0232, 1.3438))),
    ("L Finger21_example", Vector((0.7891, 0.0284, 1.3438))),
    ("L Finger1_example", Vector((0.7500, -0.0237, 1.3438))),
    ("L Finger11_example", Vector((0.7891, -0.0237, 1.3438))),
    ("L Finger0_example", Vector((0.7109, -0.0471, 1.3125))),
    ("L Finger01_example", Vector((0.7422, -0.0471, 1.3125))),
    ("Neck_example", Vector((0.0000, 0.0156, 1.4141))),
    ("Head_example", Vector((0.0000, 0.0020, 1.5260))),
]
empty_coords_name_example_comb = [
    ("Head_example", Vector((0.0000, 0.0020, 1.5260))),
    ("Feet_example", Vector((-0.0938, -0.0028, 0.0340))),
    ("UpperBody_example", Vector((-0.0006, 0.0136, 1.2599))),
    ("Face_example", Vector((0.0000, 0.0020, 1.5260))),
    ("LowerBody_example", Vector((-0.0952, 0.0234, 0.6991))),

]
bone_data = {
"Bip001 Pelvis": {"parent": None, "head": Vector((0.0000, 0.0302, 0.9065)), "tail": Vector((0.0000, -0.0659, 0.9065))},
"Bip001 Spine": {"parent": "Bip001 Pelvis", "head": Vector((0.0000, 0.0303, 0.9910)), "tail": Vector((-0.0000, -0.0954, 0.9909))},
"Bip001 Spine1": {"parent": "Bip001 Spine", "head": Vector((0.0000, 0.0303, 1.1168)), "tail": Vector((0.0000, -0.0448, 1.1167))},
"Bip001 Spine2": {"parent": "Bip001 Spine1", "head": Vector((0.0000, 0.0303, 1.1918)), "tail": Vector((0.0000, -0.1392, 1.1917))},
"Bip001 Neck": {"parent": "Bip001 Spine2", "head": Vector((0.0000, 0.0302, 1.3777)), "tail": Vector((0.0000, -0.0197, 1.3776))},
"Bip001 Head": {"parent": "Bip001 Neck", "head": Vector((0.0000, 0.0302, 1.4276)), "tail": Vector((0.0000, -0.2875, 1.4276))},
"Bip001 HeadNub": {"parent": "Bip001 Head", "head": Vector((0.0000, 0.0302, 1.7453)), "tail": Vector((0.0000, -0.2875, 1.7453))},
"Bip001 L Clavicle": {"parent": "Bip001 Spine2", "head": Vector((0.0797, 0.0219, 1.3319)), "tail": Vector((0.0797, 0.0763, 1.3319))},
"Bip001 L UpperArm": {"parent": "Bip001 L Clavicle", "head": Vector((0.1341, 0.0219, 1.3319)), "tail": Vector((0.1248, 0.3161, 1.3612))},
"Bip001 L Forearm": {"parent": "Bip001 L UpperArm", "head": Vector((0.4297, 0.0308, 1.3368)), "tail": Vector((0.4376, 0.2493, 1.3588))},
"Bip001 L Hand": {"parent": "Bip001 L Forearm", "head": Vector((0.6492, 0.0226, 1.3390)), "tail": Vector((0.6503, 0.0306, 1.2590))},
"Bip001 L Finger0": {"parent": "Bip001 L Hand", "head": Vector((0.6986, -0.0302, 1.3176)), "tail": Vector((0.6985, -0.0302, 1.2885))},
"Bip001 L Finger01": {"parent": "Bip001 L Finger0", "head": Vector((0.7276, -0.0313, 1.3175)), "tail": Vector((0.7275, -0.0313, 1.2902))},
"Bip001 L Finger0Nub": {"parent": "Bip001 L Finger01", "head": Vector((0.7549, -0.0323, 1.3173)), "tail": Vector((0.7547, -0.0323, 1.2901))},
"Bip001 L Finger1": {"parent": "Bip001 L Hand", "head": Vector((0.7272, -0.0117, 1.3426)), "tail": Vector((0.7276, -0.0117, 1.2966))},
"Bip001 L Finger11": {"parent": "Bip001 L Finger1", "head": Vector((0.7732, -0.0119, 1.3430)), "tail": Vector((0.7734, -0.0119, 1.3142))},
"Bip001 L Finger1Nub": {"parent": "Bip001 L Finger11", "head": Vector((0.8020, -0.0121, 1.3433)), "tail": Vector((0.8022, -0.0121, 1.3145))},
"Bip001 L Finger2": {"parent": "Bip001 L Hand", "head": Vector((0.7283, 0.0366, 1.3435)), "tail": Vector((0.7287, 0.0366, 1.2989))},
"Bip001 L Finger21": {"parent": "Bip001 L Finger2", "head": Vector((0.7729, 0.0356, 1.3439)), "tail": Vector((0.7732, 0.0356, 1.3141))},
"Bip001 L Finger2Nub": {"parent": "Bip001 L Finger21", "head": Vector((0.8027, 0.0349, 1.3442)), "tail": Vector((0.8030, 0.0349, 1.3144))},
"Bip001 R Clavicle": {"parent": "Bip001 Spine2", "head": Vector((-0.0797, 0.0219, 1.3319)), "tail": Vector((-0.0797, 0.0763, 1.3319))},
"Bip001 R UpperArm": {"parent": "Bip001 R Clavicle", "head": Vector((-0.1341, 0.0219, 1.3319)), "tail": Vector((-0.1248, 0.3161, 1.3612))},
"Bip001 R Forearm": {"parent": "Bip001 R UpperArm", "head": Vector((-0.4297, 0.0308, 1.3368)), "tail": Vector((-0.4376, 0.2493, 1.3588))},
"Bip001 R Hand": {"parent": "Bip001 R Forearm", "head": Vector((-0.6492, 0.0226, 1.3390)), "tail": Vector((-0.6503, 0.0306, 1.2590))},
"Bip001 R Finger0": {"parent": "Bip001 R Hand", "head": Vector((-0.6986, -0.0302, 1.3176)), "tail": Vector((-0.6985, -0.0302, 1.2885))},
"Bip001 R Finger01": {"parent": "Bip001 R Finger0", "head": Vector((-0.7276, -0.0313, 1.3175)), "tail": Vector((-0.7275, -0.0313, 1.2902))},
"Bip001 R Finger0Nub": {"parent": "Bip001 R Finger01", "head": Vector((-0.7549, -0.0323, 1.3173)), "tail": Vector((-0.7547, -0.0323, 1.2901))},
"Bip001 R Finger1": {"parent": "Bip001 R Hand", "head": Vector((-0.7272, -0.0117, 1.3426)), "tail": Vector((-0.7276, -0.0117, 1.2966))},
"Bip001 R Finger11": {"parent": "Bip001 R Finger1", "head": Vector((-0.7732, -0.0119, 1.3430)), "tail": Vector((-0.7734, -0.0119, 1.3142))},
"Bip001 R Finger1Nub": {"parent": "Bip001 R Finger11", "head": Vector((-0.8020, -0.0121, 1.3433)), "tail": Vector((-0.8022, -0.0121, 1.3145))},
"Bip001 R Finger2": {"parent": "Bip001 R Hand", "head": Vector((-0.7283, 0.0366, 1.3435)), "tail": Vector((-0.7287, 0.0366, 1.2989))},
"Bip001 R Finger21": {"parent": "Bip001 R Finger2", "head": Vector((-0.7729, 0.0356, 1.3439)), "tail": Vector((-0.7732, 0.0356, 1.3141))},
"Bip001 R Finger2Nub": {"parent": "Bip001 R Finger21", "head": Vector((-0.8027, 0.0349, 1.3442)), "tail": Vector((-0.8030, 0.0349, 1.3144))},
"Bip001 L Thigh": {"parent": "Bip001 Pelvis", "head": Vector((0.1019, 0.0302, 0.9065)), "tail": Vector((0.1023, -0.3781, 0.9377))},
"Bip001 L Calf": {"parent": "Bip001 L Thigh", "head": Vector((0.0968, -0.0009, 0.4983)), "tail": Vector((0.0964, -0.4253, 0.4654))},
"Bip001 L Foot": {"parent": "Bip001 L Calf", "head": Vector((0.0915, 0.0320, 0.0739)), "tail": Vector((0.0915, -0.1194, 0.0739))},
"Bip001 L Toe0": {"parent": "Bip001 L Foot", "head": Vector((0.0915, -0.1007, 0.0011)), "tail": Vector((0.0915, -0.1007, 0.0214))},
"Bip001 L Toe0Nub": {"parent": "Bip001 L Toe0", "head": Vector((0.0915, -0.1210, 0.0011)), "tail": Vector((0.0915, -0.1210, 0.0214))},
"Bip001 R Thigh": {"parent": "Bip001 Pelvis", "head": Vector((-0.1019, 0.0302, 0.9065)), "tail": Vector((-0.1023, -0.3781, 0.9377))},
"Bip001 R Calf": {"parent": "Bip001 R Thigh", "head": Vector((-0.0968, -0.0009, 0.4983)), "tail": Vector((-0.0964, -0.4253, 0.4654))},
"Bip001 R Foot": {"parent": "Bip001 R Calf", "head": Vector((-0.0915, 0.0320, 0.0739)), "tail": Vector((-0.0915, -0.1194, 0.0739))},
"Bip001 R Toe0": {"parent": "Bip001 R Foot", "head": Vector((-0.0915, -0.1007, 0.0011)), "tail": Vector((-0.0915, -0.1007, 0.0214))},
"Bip001 R Toe0Nub": {"parent": "Bip001 R Toe0", "head": Vector((-0.0915, -0.1210, 0.0011)), "tail": Vector((-0.0915, -0.1210, 0.0214))},

       
}



class CharOperater(bpy.types.Operator):
    bl_idname = "object.miao_char_operater"
    bl_label = "角色一键处理"
    
    def apply_transforms_recursive(self, obj):
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.select_set(False)

        if obj.children:
            for child in obj.children:
                self.apply_transforms_recursive(child)

    def execute(self, context):
        print("开始处理顶点")
        bpy.ops.object.vox_operation()
        print("开始处理碰撞")
        bpy.ops.object.miao_parent_byboundingbox()

        def apply_change_to_scene():
            def set_material_to_objects(objects, material):
                for obj in objects:
                    if len(obj.data.materials):
                        obj.data.materials[0] = material
                    else:
                        obj.data.materials.append(material)

            top_level_parents = [obj for obj in bpy.data.objects if obj.parent is None and 'example' not in obj.name.lower()]

            for parent_obj in top_level_parents:
                parent_obj.scale *= 0.5
                parent_obj.location = (0, 0, 0)

                if parent_obj.children:
                    children_with_materials = [child for child in parent_obj.children if len(child.data.materials) > 0]
                    if children_with_materials:
                        child_with_random_material = random.choice(children_with_materials)
                        random_material = child_with_random_material.data.materials[0]
                        set_material_to_objects(parent_obj.children, random_material)
    
        apply_change_to_scene()

        for parent_obj in bpy.context.scene.objects:
            if parent_obj.parent is None:
                self.apply_transforms_recursive(parent_obj)
        
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

class CharOperaterBoneWeight(bpy.types.Operator):
    bl_idname = "object.char_operater_bone_weight"
    bl_label = "执行自定义操作"

    def execute(self, context):
        def create_armature_with_bones(armature_name, bone_data):
            # 获取骨架的起始位置
            # origin = bone_data.get("origin", Vector((0.0, 0.030188, 0.914863)))

            origin = bone_data.get("origin", Vector((0.0, 0.0, 0.0)))

            # 设置正确的上下文和模式
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            # 创建骨架
            bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
            armature = bpy.context.object
            armature.name = armature_name

            armature_data = armature.data
            armature_data.name = armature_name

            edit_bones = armature_data.edit_bones

            # 删除默认添加的骨骼
            default_bone = edit_bones.get('Bone')
            if default_bone:
                edit_bones.remove(default_bone)

            default_bone = edit_bones.get('骨骼')
            if default_bone:
                edit_bones.remove(default_bone)


            created_bones = {}

            for bone_name, data in bone_data.items():
                if bone_name == "origin":
                    continue  # 跳过 "origin" 键
                new_bone = edit_bones.new(name=bone_name)
                new_bone.head = data['head'] + origin
                new_bone.tail = data['tail'] + origin
                created_bones[bone_name] = new_bone

            # 设置父子关系
            for bone_name, data in bone_data.items():
                if bone_name == "origin":
                    continue  # 跳过 "origin" 键
                if data['parent']:
                    created_bone = created_bones[bone_name]
                    parent_bone = created_bones[data['parent']]
                    created_bone.parent = parent_bone


            return armature

        def rename_all_children_based_on_coords(empty_coords):
            objects_bvh = {}

            def create_bvh_tree(obj):
                bm = bmesh.new()
                bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
                bmesh.ops.transform(bm, verts=bm.verts, matrix=obj.matrix_world)
                bvh = BVHTree.FromBMesh(bm)
                bm.free()
                return bvh

            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    objects_bvh[obj] = create_bvh_tree(obj)

            renamed_objects = {}

            for name, coord in empty_coords:
                intersection_count = defaultdict(int)

                for other_obj, bvh in objects_bvh.items():
                    ray_origin = coord
                    ray_direction = Vector((0, 0, -1))

                    hit, _, _, _ = bvh.ray_cast(ray_origin, ray_direction)
                    while hit:
                        intersection_count[other_obj] += 1
                        hit += ray_direction * 0.00001
                        hit, _, _, _ = bvh.ray_cast(hit, ray_direction)

                for other_obj, count in intersection_count.items():
                    if count % 2 == 1:
                        new_name = name.replace("_example", "")
                        if other_obj not in renamed_objects:
                            other_obj.name = new_name
                            renamed_objects[other_obj] = True

        def duplicate_bones_to_objects():
            # 先删除命名为 "BOX" 的物体
            boxes_to_delete = [obj for obj in bpy.data.objects if obj.name.startswith("BOX")]
            bpy.ops.object.select_all(action='DESELECT')
            for box in boxes_to_delete:
                box.select_set(True)
            bpy.ops.object.delete()

            scene_objects = bpy.data.objects

            for object in scene_objects:
                if object.parent is None:
                    # 创建一个新的骨架并为每个顶级父对象命名
                    armature_name = f'{object.name}_armature'
                    armature = create_armature_with_bones(armature_name, bone_data)

                    collection = object.users_collection[0]

                    # 检查集合中是否已经包含了这个 armature
                    if armature.name not in collection.objects:
                        collection.objects.link(armature)

                    armature.matrix_world = object.matrix_world

                    armature.parent = object

                    for child_obj in object.children:
                        if child_obj.type == 'MESH':
                            bone_name = "Bip001 " + child_obj.name.split('.')[0]

                            modifier = child_obj.modifiers.new(name='ArmatureMod', type='ARMATURE')
                            modifier.object = armature
                            modifier.use_vertex_groups = True

                            group = child_obj.vertex_groups.new(name=bone_name)
                            for v in child_obj.data.vertices:
                                group.add([v.index], 1.0, 'ADD')

        def get_top_parent(obj):
            while obj.parent is not None:
                obj = obj.parent
            return obj if obj else None

        def create_parent_dict(name_list):
            top_parents = {}
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH' and any(name in obj.name for name in name_list):
                    top_parent = get_top_parent(obj)
                    if top_parent is None:
                        top_parent = obj
                    if top_parent not in top_parents:
                        top_parents[top_parent] = []
                    top_parents[top_parent].append(obj)
            return top_parents

        def join_objects(parent_dict, new_name):
            for top_parent, objects in parent_dict.items():
                if len(objects) <= 1:
                    continue

                # 确保所有对象都在 OBJECT 模式下
                if bpy.context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                bpy.ops.object.select_all(action='DESELECT')
                for obj in objects:
                    obj.select_set(True)

                if bpy.context.selected_objects:
                    # 设置第一个选中的对象为活动对象
                    bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
                    bpy.ops.object.join()

                bpy.context.object.name = new_name

        def create_contact_vertex_groups(input_objects, threshold_distance):
            objects = {obj.name: obj for obj in input_objects}

            kdtrees = {}
            bm_objects = {}
            for obj_name, obj in objects.items():
                bm_objects[obj_name] = bmesh.new()
                bm_objects[obj_name].from_mesh(obj.data)
                kdtrees[obj_name] = kdtree.KDTree(len(bm_objects[obj_name].verts))
                for i, v in enumerate(bm_objects[obj_name].verts):
                    kdtrees[obj_name].insert(obj.matrix_world @ v.co, i)
                kdtrees[obj_name].balance()

            vertex_groups = defaultdict(dict)

            for obj_a in input_objects:
                obj_a_name = obj_a.name
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
                        for i, v in enumerate(bm_a.verts):
                            global_v_co = obj_a.matrix_world @ v.co
                            closest_co, closest_index, dist = kd_tree_b.find(global_v_co)
                            if dist < threshold_distance:
                                weight = 1.0 - dist / threshold_distance
                                vertex_group.add([v.index], weight, 'REPLACE')

            for bm in bm_objects.values():
                bm.free()

            for obj in input_objects:
                obj.data.update()

            print("Contact weights assigned for all object combinations, and self vertex groups created with full weight.")

        def filter_objects_by_name_patterns(objects, name_patterns):
            filtered_objects = []
            for obj in objects:
                if obj.type == 'MESH' and any(name_pattern in obj.name for name_pattern in name_patterns):
                    filtered_objects.append(obj)
            return filtered_objects

        bpy.ops.object.miao_clean_sense()
        rename_all_children_based_on_coords(empty_coords_name_example)

        def process_contact_weights():
            threshold_distance = bpy.context.scene.threshold_distance
            if bpy.context.scene.assign_contact_weights:
                print("Processing contact weights...")
                all_objects = bpy.context.scene.objects
                for name_patterns in named_group:
                    group_objects = filter_objects_by_name_patterns(all_objects, name_patterns)
                    create_contact_vertex_groups(group_objects, threshold_distance)
                pass
            else:
                print("Skipping contact weight assignment...")

        process_contact_weights()
        duplicate_bones_to_objects()
        parent_dict_list = [(create_parent_dict(name_list), new_name) for name_list, new_name in name_groups]
        for parent_dict, new_name in parent_dict_list:
            join_objects(parent_dict, new_name)
        rename_all_children_based_on_coords(empty_coords_name_example_comb)

        return {'FINISHED'}

def register():
    bpy.utils.register_class(CharOperater)
    bpy.utils.register_class(CharOperaterBoneWeight)

def unregister():
    bpy.utils.unregister_class(CharOperater)
    bpy.utils.unregister_class(CharOperaterBoneWeight)