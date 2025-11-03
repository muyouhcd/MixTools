import bpy
import os
from bpy.types import Operator, Panel, Collection
from mathutils import Vector
from collections import defaultdict
import re
import numpy as np
from bpy.props import PointerProperty

# 延迟导入PIL
def get_pil_image():
    """安全地导入PIL Image"""
    try:
        from PIL import Image
        return Image
    except ImportError:
        return None


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
    bl_description = "将贴图名称改为原始文件名（去除扩展名）"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rename_texture()
        print("重命名完成")
        return {'FINISHED'}
    
#去除名称后缀
class RemoveNameSuffix(bpy.types.Operator):
    bl_idname = "object.mian_remove_name_suffix"
    bl_label = "移除名称后缀"
    bl_description = "移除所选物体名称中的后缀（如_001、-01、.001等）"

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
    bl_description = "移除顶级物体的数字后缀，如有重名则交换名称"
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

#移除所选物体顶级父级名称中的.00n后缀
class OBJECT_OT_remove_top_level_suffix(Operator):
    bl_idname = "object.remove_top_level_suffix"
    bl_label = "移除顶级父级.00n后缀"
    bl_description = "移除所选物体顶级父级名称中的.00n后缀，如有重名则保持顶级无后缀，冲突物体加后缀"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "请先选择物体")
            return {'CANCELLED'}
        
        # 正则表达式匹配各种数字后缀格式
        # 支持 .001, .002, .01, .1, .0001 等格式
        suffix_patterns = [
            re.compile(r"\.\d{3}$"),  # .001, .002, .003
            re.compile(r"\.\d{2}$"),  # .01, .02, .03
            re.compile(r"\.\d{1}$"),  # .1, .2, .3
            re.compile(r"\.\d{4,}$"), # .0001, .00001 等
        ]
        
        # 存储顶级父级对象
        top_level_objects = set()
        
        # 找到所有选中物体的顶级父级
        for obj in selected_objects:
            top_parent = obj
            while top_parent.parent:
                top_parent = top_parent.parent
            top_level_objects.add(top_parent)
        
        processed_count = 0
        skipped_count = 0
        
        # 预处理：收集所有需要重命名的物体信息
        rename_tasks = []
        for top_obj in top_level_objects:
            print(f"分析顶级父级: {top_obj.name}")
            
            # 检查是否有数字后缀
            matched_pattern = None
            for pattern in suffix_patterns:
                if pattern.search(top_obj.name):
                    matched_pattern = pattern
                    break
            
            if matched_pattern:
                new_name = re.sub(matched_pattern, "", top_obj.name)
                rename_tasks.append({
                    'object': top_obj,
                    'old_name': top_obj.name,
                    'new_name': new_name,
                    'pattern': matched_pattern
                })
                print(f"  计划重命名: {top_obj.name} -> {new_name}")
            else:
                print(f"  无数字后缀，跳过: {top_obj.name}")
                skipped_count += 1
        
        # 按新名称分组，处理重名冲突
        name_groups = {}
        for task in rename_tasks:
            new_name = task['new_name']
            if new_name not in name_groups:
                name_groups[new_name] = []
            name_groups[new_name].append(task)
        
        # 处理每个名称组
        for new_name, tasks in name_groups.items():
            print(f"处理名称组: {new_name} (共{len(tasks)}个物体)")
            
            # 检查是否与现有物体重名
            existing_obj = bpy.data.objects.get(new_name)
            if existing_obj:
                print(f"  发现现有物体重名: {existing_obj.name}")
                # 将现有物体也加入重命名任务
                tasks.append({
                    'object': existing_obj,
                    'old_name': existing_obj.name,
                    'new_name': new_name,
                    'pattern': None,
                    'is_existing': True
                })
            
            # 为每个任务分配唯一名称
            used_names = set()  # 跟踪已使用的名称
            for i, task in enumerate(tasks):
                if i == 0 and not task.get('is_existing', False):
                    # 第一个物体保持原名称
                    final_name = new_name
                else:
                    # 其他物体添加后缀
                    counter = 1
                    while True:
                        final_name = f"{new_name}.{str(counter).zfill(3)}"
                        # 检查名称是否已被使用或已存在
                        if final_name not in used_names and not bpy.data.objects.get(final_name):
                            break
                        counter += 1
                        if counter > 999:
                            final_name = f"{new_name}_conflict_{counter}"
                            break
                
                # 将分配的名称加入已使用集合
                used_names.add(final_name)
                task['final_name'] = final_name
                print(f"  分配名称: {task['old_name']} -> {final_name}")
        
        # 执行重命名
        for task in rename_tasks:
            top_obj = task['object']
            final_name = task['final_name']
            
            print(f"执行重命名: {top_obj.name} -> {final_name}")
            
            try:
                top_obj.name = final_name
                print(f"  成功重命名为: {top_obj.name}")
                processed_count += 1
            except Exception as e:
                print(f"  重命名失败: {e}")
                self.report({'ERROR'}, f"重命名 {top_obj.name} 失败: {e}")
        
        self.report({'INFO'}, f"已处理 {processed_count} 个顶级父级物体，跳过 {skipped_count} 个")
        return {'FINISHED'}

#更改mesh名称为物体名称
class RenameMeshesOperator(bpy.types.Operator):
    """Rename Meshes to their object names"""      
    bl_idname = "object.rename_meshes"  
    bl_label = "重命名Meshes为物体名称"
    bl_description = "将所选物体的Mesh数据块名称改为物体名称"
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
    bl_description = "将所选物体的名称改为其Mesh数据块的名称"
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
    bl_idname = "object.mian_rename_collections"
    bl_label = "Rename Collections"
    bl_description = "根据空间位置关系自动重命名集合：将目标集合中的子集合重命名为参考集合中位置最接近的物体名称。需要先选择参考集合(collectionA)和目标集合(collectionB)。"

    def execute(self, context):
        rename_collections(self, context)
        return {'FINISHED'}

# 按照空间前后顺序对所选物体重命名
class RenameByLocation(bpy.types.Operator):
    bl_idname = "object.mian_rename_location"
    bl_label = "按轴空间顺序重命名"
    bl_description = "根据所选物体在指定轴向上的空间位置顺序进行重命名"

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
    bl_description = "将所选物体的名称改为其所在集合的名称"

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



#---------------------------------汽车重命名-------------------------------------
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
            Image = get_pil_image()
            if Image is None:
                print("PIL库不可用，跳过图像处理")
                return
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



def move_digits_to_end(name):
    # 以 '.' 分割名称，寻找数字部分
    parts = name.split('.')
    non_digit_parts = [part for part in parts if not re.fullmatch('\d+', part)]
    digit_parts = [part for part in parts if re.fullmatch('\d+', part)]
    
    # 将所有非数字部分重新连接成一个新的名字，将数字部分附在最后
    # 而且把 '.' 替换为 '_'
    return '_'.join(non_digit_parts + digit_parts)

class AutoRenameCar(bpy.types.Operator):
    bl_idname = "object.mian_auto_rename_car"
    bl_label = "自动重命名汽车For Unity(-y朝前)"
    bl_description = "自动重命名汽车模型，适用于Unity引擎，包括车身、车轮等部件的智能命名"
    
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
    bl_idname = "object.mian_auto_rename_car_for_rigcar"
    bl_label = "自动重命名汽车For Rig-car(-y朝前)"
    bl_description = "自动重命名汽车模型，适用于Rig-car系统，包括层级结构和命名规范"

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

#批量更改子级名称为顶级父级，忽略隐藏物体
class RenameByParent(bpy.types.Operator):
    bl_idname = "object.mian_rename_by_parent"
    bl_label = "更改所选物体为其顶级名称"
    bl_description = "将所选子物体的名称更改为其顶级父物体的名称"

    def execute(self, context):

        def rename_selected_objects_with_sequential_suffixes():
            def get_sequential_suffix(name_base, current_number):
                return f"{name_base}.{current_number:03d}"

            # 获取所有已选择的物体
            all_objects = bpy.data.objects
            selected_objects = bpy.context.selected_objects

            # 遍历所有已选择的物体
            for obj in selected_objects:
                # 检查物体是否有父级，并获得物体的顶级父级
                if obj.parent is None:
                    continue
                top_parent = obj.parent
                while top_parent.parent is not None:
                    top_parent = top_parent.parent

                # 检查物体是否在视口中隐藏，如果是，则跳过
                if obj.hide_viewport:
                    continue

                # 移除顶级父级物体名称的数字后缀
                top_parent_name_no_suffix = top_parent.name.split('.')[0]
                top_parent.name = top_parent_name_no_suffix

                # 获取顶级父级物体的直接子物体
                direct_children = [
                    child for child in selected_objects if child.parent == top_parent]

                # 为顶级父级物体的直接子物体分配连贯的数字后缀
                for index, child in enumerate(direct_children, start=1):
                    new_name = get_sequential_suffix(
                        top_parent_name_no_suffix, index)
                    child.name = new_name

        # 在 Blender 中执行该函数
        rename_selected_objects_with_sequential_suffixes()
        return {"FINISHED"}


def register():     
    bpy.utils.register_class(RenameTextureOrign)
    bpy.utils.register_class(RemoveNameSuffix)
    bpy.utils.register_class(OBJECT_OT_remove_suffix_and_resolve_conflicts)
    bpy.utils.register_class(OBJECT_OT_remove_top_level_suffix)
    bpy.utils.register_class(RenameMeshesOperator)
    bpy.utils.register_class(RenameObjectsOperator)
    bpy.utils.register_class(OBJECT_OT_RenameButton)
    bpy.utils.register_class(RenameByLocation)
    bpy.utils.register_class(RenameSelectedObjects)
    bpy.utils.register_class(AutoRenameCar)
    bpy.utils.register_class(AutoRenameCarForRigCar)
    bpy.utils.register_class(RenameByParent)

def unregister():
    bpy.utils.unregister_class(RenameTextureOrign)
    bpy.utils.unregister_class(RemoveNameSuffix)
    bpy.utils.unregister_class(OBJECT_OT_remove_suffix_and_resolve_conflicts)
    bpy.utils.unregister_class(OBJECT_OT_remove_top_level_suffix)
    bpy.utils.unregister_class(RenameMeshesOperator)
    bpy.utils.unregister_class(RenameObjectsOperator)
    bpy.utils.unregister_class(OBJECT_OT_RenameButton)
    bpy.utils.unregister_class(RenameByLocation)
    bpy.utils.unregister_class(RenameSelectedObjects)
    bpy.utils.unregister_class(AutoRenameCar)
    bpy.utils.unregister_class(AutoRenameCarForRigCar)
    bpy.utils.unregister_class(RenameByParent)


