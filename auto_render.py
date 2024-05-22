import bpy
import mathutils
from bpy import context as C
from bpy.props import BoolProperty, EnumProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper
import os
from PIL import Image, ImageOps

class AutoRenderer():
    def __init__(self, collections: list, camera_name="Camera", 
                    output_path="./", output_name="auto_render", 
                    output_format="PNG", focus_each_object=False) -> None:
        """
        集合：字符串列表，每个字符串都是一个集合的名称
        """
        self.collections = collections
        self.cam = bpy.data.objects.get(camera_name)  # 通过参数传递的 camera_name 获取相机对象
        if not self.cam:
            raise KeyError(f'bpy_prop_collection[key]: key "{camera_name}" not found')
        self.output_path = output_path
        self.output_name = output_name
        self.output_format = output_format
        self.focus_each_object = focus_each_object

        self.intended_collection = None

    def activate_all_collections(self):
        """
       将所有集合标记为活动。
        """
        for layer_collection in bpy.context.view_layer.layer_collection.children:
            layer_collection.exclude = False

    def deactivate_all_other_collection(self, collection_name: str):
        """
        仅将预期的集合保留为活动状态。
        """
        for layer_collection in bpy.context.view_layer.layer_collection.children:
            if layer_collection.name != collection_name:
                layer_collection.exclude = True
            else:
                layer_collection.exclude = False

    def get_top_parent_name(self, obj):
        """
        获取顶级父物体的名称。如果物体没有父物体，则返回物体本身的名称。
        """
        top_parent = obj
        while top_parent.parent:
            top_parent = top_parent.parent
        return top_parent.name
    
    def group_objects_by_top_parent(self, objects):
        """
        将给定物体按顶级父物体分组。
        """
        groups = {}
        for obj in objects:
            top_parent = self.get_top_parent_name(obj)
            if top_parent not in groups:
                groups[top_parent] = []
            groups[top_parent].append(obj)
        return groups


    def focus_object(self, obj):
        """聚焦到指定的对象"""
        # 选择目标对象
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        
        # 将视图切换到相机视图
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                bpy.context.scene.camera = self.cam
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        area.spaces.active.region_3d.update()
                        
                        # 调整相机的距离以添加边框距离
                        bpy.ops.view3d.camera_to_view_selected()
                        margin = bpy.context.scene.auto_render_settings.margin_distance
                        bpy.context.scene.camera.data.lens *= (1.0 + margin * 0.1)
                        
                        break

    def render_collection(self, collection_name: str):
        # 更新预期的集合参考
        self.intended_collection = bpy.data.collections[collection_name]
        
        # 确认透明背景设置
        background_is_transparent = bpy.context.scene.render.film_transparent
        
        # 对集合中的物体按顶级父物体分组
        groups = self.group_objects_by_top_parent(self.intended_collection.objects)

        # 渲染每个分组的物体
        for top_parent_name, objects in groups.items():
            # 暂存当前集合内所有物体的渲染可见性
            original_hide_render = {o: o.hide_render for o in self.intended_collection.objects}
            
            # 为渲染分组中的物体设置可见性
            for obj in self.intended_collection.objects:
                obj.hide_render = not obj in objects

            # 如果需要聚焦到对象
            if self.focus_each_object:
                self.focus_object(objects[0])

            # 渲染当前分组中的所有物体
            bpy.ops.render.render()

            # 文件名使用顶级父级名称，如果物体没有父物体，则使用物体本身名称
            filename = top_parent_name if top_parent_name != objects[0].name else objects[0].name
            filepath = os.path.join(self.output_path, "{}.{}".format(filename, self.output_format.lower()))

            # 保存渲染结果
            bpy.data.images["Render Result"].save_render(filepath=filepath)
            
            # 添加边框并保存图像
            margin_distance = bpy.context.scene.auto_render_settings.margin_distance
            self.add_image_border(filepath, margin_distance, background_is_transparent)

            # 恢复集合内其他物体的原始渲染可见性
            for other_obj, visibility in original_hide_render.items():
                other_obj.hide_render = visibility
    def add_image_border(self, image_path, margin_distance, background_is_transparent):
        """在图像周围添加边框，并根据背景透明度调整边框"""
        with Image.open(image_path) as img:
            # 确保图像是RGBA模式以支持透明度
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 确定边框填充颜色
            fill_color = (0, 0, 0, 0) if background_is_transparent else (0, 0, 0)

            # 使用PIL的ImageOps.expand来扩展边框
            img_with_border = ImageOps.expand(img, border=margin_distance, fill=fill_color)
            img_with_border.save(image_path)

    def auto_render(self):
        """
        在实例化时呈现提供列表中的所有集合。
        """
        for collection_name in self.collections:
            self.render_collection(collection_name)

def get_all_cameras(self, context):
    return [(obj.name, obj.name, obj.name) for obj in bpy.context.scene.objects if obj.type == 'CAMERA']

def get_all_collections(self, context):
    return [(collection.name, collection.name, collection.name) for collection in bpy.data.collections]

class AutoRenderSettings(bpy.types.PropertyGroup):
    output_path: bpy.props.StringProperty(
        name="Output Path",
        description="Output directory for rendered images",
        default="./",
        maxlen=1024,
        subtype='DIR_PATH'
    )
    output_name: bpy.props.StringProperty(
        name="Output Name",
        description="Name of the rendered images",
        default="auto_render"
    )
    output_format: bpy.props.EnumProperty(
        name="Output Format",
        description="Image format of the rendered images",
        items=[('PNG', 'PNG', 'PNG'), ('JPEG', 'JPEG', 'JPEG'), ('BMP', 'BMP', 'BMP'), ('TIFF', 'TIFF', 'TIFF')]
    )
    collections: bpy.props.EnumProperty(
        name="Collections",
        description="Choose a collection to be rendered",
        default=None,
        items=get_all_collections
    )
    cameras: bpy.props.EnumProperty(
        name="Cameras",
        description="Camera to be used for rendering",
        default=None,
        items=get_all_cameras
    )
    focus_each_object: bpy.props.BoolProperty(
        name="Focus Each Object",
        description="Enable to focus camera on each object before rendering",
        default=False
    )
    margin_distance: bpy.props.IntProperty(
        name="Margin Distance (px)",
        description="Margin distance between object and frame border in pixels",
        default=0,  # Default margin value in pixels
        min=0,
        max=1000
    )
class AUTO_RENDER_OT_Execute(bpy.types.Operator):
    bl_idname = "auto_render.execute"
    bl_label = "渲染"
    bl_description = "Render the specified collections"

    def execute(self, context):
        scene = context.scene
        auto_render_settings = scene.auto_render_settings

        collections = auto_render_settings.collections.split(',')
        camera_name = auto_render_settings.cameras
        output_path = auto_render_settings.output_path
        output_name = auto_render_settings.output_name
        output_format = auto_render_settings.output_format
        focus_each_object = auto_render_settings.focus_each_object

        auto_renderer = AutoRenderer(collections, camera_name=camera_name,
                                      output_path=output_path, output_name=output_name,
                                      output_format=output_format, focus_each_object=focus_each_object)
        auto_renderer.auto_render()

        return {'FINISHED'}

class BatchRenderOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "auto_render.batch_render"
    bl_label = "选择文件渲染"

    filename_ext = ".blend"

    filter_glob: bpy.props.StringProperty(
        default="*.blend",
        options={'HIDDEN'},
    )

    files: CollectionProperty(name='File Path', type=bpy.types.OperatorFileListElement)

    render_as_animation: bpy.props.BoolProperty(
        name="Render as Animation",
        default=True,
        description="Enable to render as animation",
    )
    

    def execute(self, context):
        directory = os.path.dirname(self.filepath)

        for f in self.files:
            output_file = os.path.join(directory, f.name.split('.blend')[0])
            print(f"Rendering to {output_file}")
            bpy.context.scene.render.filepath = output_file
            file_path = os.path.join(directory, f.name)

            bpy.ops.wm.open_mainfile(filepath=file_path)

            if self.render_as_animation:
                bpy.ops.render.render(animation=True)
            else:
                bpy.ops.render.render(write_still=True)

        return {'FINISHED'}

def register():
    bpy.utils.register_class(AutoRenderSettings)
    bpy.types.Scene.auto_render_settings = bpy.props.PointerProperty(type=AutoRenderSettings)
    bpy.utils.register_class(AUTO_RENDER_OT_Execute)
    bpy.utils.register_class(BatchRenderOperator)
    bpy.types.Scene.render_as_animation = bpy.props.BoolProperty(
        name="Render as Animation",
        default=False,
    )

def unregister():
    bpy.utils.unregister_class(AUTO_RENDER_OT_Execute)
    del bpy.types.Scene.auto_render_settings
    bpy.utils.unregister_class(AutoRenderSettings)

    bpy.utils.unregister_class(BatchRenderOperator)
    del bpy.types.Scene.render_as_animation

if __name__ == "__main__":
    register()