import bpy
import os
from mathutils import Vector
from collections import defaultdict
import re
import numpy as np
from bpy.props import PointerProperty
from PIL import Image

# 自动绑定汽车（改名）
bpy.types.Scene.move_children_to_same_level = bpy.props.BoolProperty(
    name="Move children to same level",
    description="将所有后代移动到与车身直系子级相同的级别",
    default=False
)

# 计算物体体积
def calc_volume(obj):
    mesh = obj.data
    volume = 0.0
    for p in mesh.polygons:
        v1, v2, v3 = [obj.matrix_world @ Vector(v.co) for v in [mesh.vertices[p.vertices[i]] for i in range(3)]]
        volume += (v1.dot(v2.cross(v3))) / 6.0
    return abs(volume)

# 根据几何体积更改名字
def change_name_based_on_geometry():
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            max_volume = None
            target_child = None
            for child in obj.children:
                if child.type == "MESH":
                    volume = calc_volume(child)
                    if max_volume is None or volume > max_volume:
                        max_volume = volume
                        target_child = child
            if target_child is not None:
                target_child.name = obj.name + "_col"

# 对物体进行纹理采样
def sample_texture_on_object(obj):
    if obj.type != 'MESH' or not obj.data.uv_layers.active: 
        return None
    
    uv_loop = obj.data.uv_layers.active.data
    faces = obj.data.polygons
    uv_map = [uv.uv for uv in uv_loop]
    
    pixels = []
    img_path = ''
    
    if obj.data.materials:
        for slot in obj.material_slots:
            if slot.material and slot.material.use_nodes:
                for node in slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        img_path = bpy.path.abspath(node.image.filepath)
                        break
                        
        if os.path.exists(img_path):
            img = Image.open(img_path).convert("RGBA")
            width, height = img.size
            
            for face in faces:
                for i in face.loop_indices:
                    uv = uv_map[i]
                    x, y = int(uv.x * (width - 1)), int((1 - uv.y) * (height - 1))
                    r, g, b, a = img.getpixel((x, y))
                    pixels.append([r, g, b, a])
                    
    if pixels:
        avg_color = np.average([px[:3] for px in pixels], axis=0, weights=[px[3] for px in pixels])
        avg_color_hex = '#{:02x}{:02x}{:02x}'.format(int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))
        return avg_color_hex

# 根据颜色重命名物体
def rename_object_based_on_color(objects, target_color_hex, new_name_suffix, tolerance=0.05):
    target_color = np.array([
            int(target_color_hex[i:i+2], 16)
            for i in (1, 3 ,5)
        ])
    for obj in objects:
        avg_color_hex = sample_texture_on_object(obj)
        if avg_color_hex is not None:
            avg_color = np.array([
                int(avg_color_hex[i:i+2], 16)
                for i in (1, 3 ,5)
            ])
            diff_color = np.abs(target_color - avg_color)
            # color difference
            diff = np.max(np.abs((avg_color - target_color) / np.clip(target_color, 0.001, None)))

            # If there is less than 5% difference and the name doesn't already contain the suffix
            if diff <= tolerance and (new_name_suffix not in obj.name):
                # Adding suffix to the existing name
                obj.name += new_name_suffix

# 计算物体的深度
def calculate_depth(obj, depth=0):
    if obj.parent is None:
        return depth
    else:
        return calculate_depth(obj.parent, depth + 1)

# 将名称中的数字移动到末尾
# def move_digits_to_end(name):
#     # Split the name by '.' and look for parts that are digits
#     parts = re.split('\.', name)
#     non_digit_parts = [part for part in parts if not re.fullmatch('\d+', part)]
#     digit_parts = [part for part in parts if re.fullmatch('\d+', part)]
    
#     # Join all non-digit parts into a new name, append digit parts at the end
#     return '_'.join(non_digit_parts + digit_parts)


def move_digits_to_end(name):
    # 以 '.' 分割名称，寻找数字部分
    parts = name.split('.')
    non_digit_parts = [part for part in parts if not re.fullmatch('\d+', part)]
    digit_parts = [part for part in parts if re.fullmatch('\d+', part)]
    
    # 将所有非数字部分重新连接成一个新的名字，将数字部分附在最后
    # 而且把 '.' 替换为 '_'
    return '_'.join(non_digit_parts + digit_parts)

class AutoRenameCar(bpy.types.Operator):
    bl_idname = "object.miao_auto_rename_car"
    bl_label = "自动重命名汽车For Unity(-y朝前)"
    
    def execute(self, context):
        def flatten_hierarchy():
            def is_root_obj(obj):
                return obj.parent is None

            def move_children_up(obj):
                # Recurse into children
                for child in obj.children:
                    move_children_up(child)

                # If object is not root, move its children to parent
                if not is_root_obj(obj):
                    for child in obj.children:
                        # Save global transform
                        global_transform = child.matrix_world.copy()

                        # Clear parent but keep transformation
                        child.parent = None
                        
                        # Set the child's parent to be the grandparent 
                        child.parent = obj.parent

                        # Restore global transform
                        child.matrix_world = global_transform

            # Start with root objects
            for obj in bpy.context.scene.objects:
                if is_root_obj(obj):
                    move_children_up(obj)

            # Start with root objects
            for obj in bpy.context.scene.objects:
                if is_root_obj(obj):
                    move_children_up(obj)

        def rename_largest_objects_to_body(objects):

            def get_original_name_without_suffix(obj_name):
                return obj_name.split('.')[0]
            # 创建一个字典，用于存储每个顶级父级的对象
            objects_by_parent = {}

            for obj in objects:
                # 找到顶级父级
                top_parent = obj
                while top_parent.parent:
                    top_parent = top_parent.parent

                # 根据顶级父级对对象进行分组，并将其添加到字典中
                if top_parent not in objects_by_parent:
                    objects_by_parent[top_parent] = []

                objects_by_parent[top_parent].append(obj)

            for parent, child_objects in objects_by_parent.items():
                # 寻找体积最大的物体
                largest_volume = float('-inf')
                largest_volume_object = None

                for obj in child_objects:
                    # 检查物体名字是否只包含父级名字和数字编号
                    if not re.match(r"[A-Za-z]+_[0-9]+", obj.name):
                        continue

                    if obj.type != 'MESH' or obj.name.endswith(('_Ft_L', '_Ft_R', '_Bk_L', '_Bk_R')):
                        continue

                    volume = obj.dimensions.x * obj.dimensions.y * obj.dimensions.z
                    if volume > largest_volume:
                        largest_volume_object = obj
                        largest_volume = volume

                # 修改找到的物体的名称，并在原名称后添加 '_Body' 后缀
                if largest_volume_object is not None:
                    original_name = get_original_name_without_suffix(largest_volume_object.name)
                    # 如果名称中不包含'_Body'，才添加后缀
                    if '_Body' not in original_name:
                        largest_volume_object.name = f"{original_name}_Body"

        # 在您的操作中调用此函数，并传递所选对象列表
        selected_objects = bpy.context.selected_objects
        rename_largest_objects_to_body(selected_objects)

        def rename_four_lowest_z_vertex_objects_with_position_suffixes(objects):
            def object_lowest_z_vertex(obj):
                world_vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
                return min(world_vertices, key=lambda v: v.z).z

            def get_original_name_without_suffix(obj_name):
                return obj_name.split('_')[0]

            # 创建一个字典，用于存储每个顶级父级的子对象
            objects_by_parent = {}

            for obj in objects:
                # 找到顶级父级
                top_parent = obj
                while top_parent.parent:
                    top_parent = top_parent.parent

                # 根据顶级父级对对象进行分组，并将其添加到字典中
                if top_parent not in objects_by_parent:
                    objects_by_parent[top_parent] = []

                objects_by_parent[top_parent].append(obj)

            for parent, child_objects in objects_by_parent.items():
                objects_lowest_z_vertices = [{'object': obj, 'lowest_z': object_lowest_z_vertex(
                    obj)} for obj in child_objects if obj.type == 'MESH']
                objects_lowest_z_vertices.sort(key=lambda o: o['lowest_z'])

                lowest_four_objects = [d['object']
                                    for d in objects_lowest_z_vertices[:4]]
                lower_half = sorted(lowest_four_objects,
                                    key=lambda o: o.location.y)[:2]
                upper_half = sorted(lowest_four_objects,
                                    key=lambda o: o.location.y)[2:]

                for group in (lower_half, upper_half):
                    if len(group) < 2:
                        continue
                    # 判断左右位置
                    sorted_group = sorted(
                        group, key=lambda o: o.location.x, reverse=True)
                    left_object = sorted_group[0]
                    right_object = sorted_group[1]

                    # 根据 y 轴位置确定 Ft 或 Bk 后缀
                    if group is lower_half:
                        position_suffix = "Ft"
                    else:
                        position_suffix = "Bk"

                    # 同时更改物体名称，避免名称重复
                    left_object.name = f"{get_original_name_without_suffix(left_object.name)}_Wheel_{position_suffix}_L"
                    right_object.name = f"{get_original_name_without_suffix(right_object.name)}_Wheel_{position_suffix}_R"

        # 在您的操作中调用此函数，并传递所选对象列表
        selected_objects = bpy.context.selected_objects
        

        flatten_hierarchy()
        # change_name_based_on_geometry()
        rename_four_lowest_z_vertex_objects_with_position_suffixes(selected_objects)
        # rename_largest_objects_to_body()
        rename_object_based_on_color(bpy.context.selected_objects, "#6699cc", '_glass')
        
        #重新对名称格式化
        # Move digits to the end for selected objects
        for obj in bpy.context.selected_objects:
            obj.name = move_digits_to_end(obj.name)

        # Create a dictionary to store the counter for each object base name
        name_counters = defaultdict(int)

        # Create a list of all selected objects, with their depth level
        objects_with_depth = [(obj, calculate_depth(obj)) for obj in bpy.context.selected_objects if re.search('\.\d+$', obj.name)]

        # Sort the list by depth level, from high to low
        objects_with_depth.sort(key=lambda x: -x[1])

        # Iterate through all selected objects
        for obj, depth in objects_with_depth:
            # Extract base name (name without the trailing number)
            base_name = re.sub("\.\d+$", '', obj.name)
            # Set the object name to the base name plus the count for that base name
            obj.name = base_name + '_' + str(name_counters[base_name]).zfill(3)
            # Increment the counter for that base name
            name_counters[base_name] += 1
            
        # Visit all objects in the selected objects
        for obj in bpy.context.selected_objects:
            # Check whether the object is of type mesh
            if obj.type == 'MESH':
                # Change the name of the mesh data block to the name of the object
                obj.data.name = obj.name
        return {"FINISHED"}
    
class AutoRenameCarForRigCar(bpy.types.Operator):
    bl_idname = "object.miao_auto_rename_car_for_rigcar"
    bl_label = "自动重命名汽车For Rig-car(-y朝前)"

    def execute(self, context):
        def set_remaining_objects_as_children_of_body():
            selected_objects = bpy.context.selected_objects

            def is_descendant(obj, child):
                while child.parent:
                    if child.parent == obj:
                        return True
                    child = child.parent
                return False

            # 获取名为“*body”的物体
            body_object = None
            for obj in selected_objects:
                if ".Body" in obj.name:
                    body_object = obj
                    break

            # 如果找到了“body”，设置剩余物体为其子级，同时保持物体的世界坐标不变
            if body_object:
                for obj in selected_objects:
                    if obj != body_object and not obj.name.endswith(('.Ft.L', '.Ft.R', '.Bk.L', '.Bk.R')):

                        # 跳过已经是 body 的子级的物体
                        if is_descendant(body_object, obj) or obj == body_object:
                            continue
                        bpy.ops.object.select_all(action='DESELECT')
                        
                        obj.select_set(True)
                        #body_object.select_set(True)
                        bpy.context.view_layer.objects.active = body_object
                        
                        
                        try:
                            bpy.ops.object.parent_set(type='OBJECT', keep_transform=True)
                        except RuntimeError:
                            print(f"循环父级错误：无法将 {obj.name} 设置为 {body_object.name} 的子级。")

                pass

        def rename_largest_remaining_object_to_body():
            selected_objects = bpy.context.selected_objects

            # 寻找体积最大的物体
            largest_volume = float('-inf')
            largest_volume_object = None

            for obj in selected_objects:
                if obj.type != 'MESH' or obj.name.endswith(('.Ft.L', '.Ft.R', '.Bk.L', '.Bk.R')):
                    continue
                volume = obj.dimensions.x * obj.dimensions.y * obj.dimensions.z
                if volume > largest_volume:
                    largest_volume_object = obj
                    largest_volume = volume
            
            # 修改找到的物体的名称，并在原名称后添加 '-body' 后缀
            if largest_volume_object is not None:
                    original_name = get_original_name_without_suffix(largest_volume_object.name)
                    # 如果名称中不包含'.Body'，才添加后缀
                    if '.Body' not in original_name:
                        largest_volume_object.name = f"{original_name}.Body"
                
                
            pass

        def get_original_name_without_suffix(obj_name):
            return obj_name.split('.')[0]

        def rename_four_lowest_z_vertex_objects_with_position_suffixes():

            def object_lowest_z_vertex(obj):
                world_vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
                return min(world_vertices, key=lambda v: v.z).z

            def get_original_name_without_suffix(obj_name):
                return obj_name.split('.')[0]

            selected_objects = bpy.context.selected_objects
            objects_lowest_z_vertices = [{'object': obj, 'lowest_z': object_lowest_z_vertex(obj)} for obj in selected_objects if obj.type == 'MESH']
            objects_lowest_z_vertices.sort(key=lambda o: o['lowest_z'])

            lowest_four_objects = [d['object'] for d in objects_lowest_z_vertices[:4]]
            lower_half = sorted(lowest_four_objects, key=lambda o: o.location.y)[:2]
            upper_half = sorted(lowest_four_objects, key=lambda o: o.location.y)[2:]

            for group in (lower_half, upper_half):
                # 判断左右位置
                sorted_group = sorted(group, key=lambda o: o.location.x, reverse=True)
                left_object = sorted_group[0]
                right_object = sorted_group[1]

                # 根据 y 轴位置确定 Ft 或 Bk 后缀
                if group is lower_half:
                    position_suffix = "Ft"
                else:
                    position_suffix = "Bk"

                # 同时更改物体名称，避免名称重复
                left_object.name = f"{get_original_name_without_suffix(left_object.name)}.Wheel.{position_suffix}.L"
                right_object.name = f"{get_original_name_without_suffix(right_object.name)}.Wheel.{position_suffix}.R"

            pass


        rename_four_lowest_z_vertex_objects_with_position_suffixes()
        rename_largest_remaining_object_to_body()
        set_remaining_objects_as_children_of_body()


        return {"FINISHED"} 

def register():
    bpy.utils.register_class(AutoRenameCar)
    bpy.utils.register_class(AutoRenameCarForRigCar)

def unregister():
    bpy.utils.unregister_class(AutoRenameCar)
    bpy.utils.unregister_class(AutoRenameCarForRigCar)