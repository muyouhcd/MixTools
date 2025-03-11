import bpy
import os

class ChangeResolutionProperties(bpy.types.PropertyGroup):
    
    input_dir: bpy.props.StringProperty(
        name="Input Directory",
        description="Directory containing input .blend files",
        default="",
        maxlen=1024,
        subtype="DIR_PATH",# type: ignore
    )

    output_dir: bpy.props.StringProperty(
        name="Output Directory",
        description="Directory to save output .blend files",
        default="",
        maxlen=1024,
        subtype="DIR_PATH",# type: ignore
    )

    output_resolution_x: bpy.props.IntProperty(
        name="Resolution X",
        description="Output resolution width",
        default=1920,
        min=1,# type: ignore
    )

    output_resolution_y: bpy.props.IntProperty(
        name="Resolution Y",
        description="Output resolution height",
        default=1080,
        min=1,# type: ignore
    )

    resolution_percentage: bpy.props.IntProperty(
        name="Resolution Percentage",
        description="Percentage of output resolution",
        default=100,
        min=1,
        max=100,# type: ignore
    )

    output_frame_rate: bpy.props.IntProperty(
        name="Frame Rate",
        description="Output frame rate",
        default=24,
        min=1,
        max=100,# type: ignore
    )

    render_engine: bpy.props.EnumProperty(
        name="Render Engine",
        description="Choose the render engine",
        items=[
            ('BLENDER_EEVEE', "Eevee", "Eevee Render Engine"),
            ('BLENDER_WORKBENCH', "Workbench", "Workbench Render Engine"),
            ('CYCLES', "Cycles", "Cycles Render Engine"),
        ],
        default='CYCLES',# type: ignore
    )
    
    output_format: bpy.props.EnumProperty(
        name="Output Format",
        description="Choose the output format",
        items=[
            ('AVI_JPEG', "AVI JPEG", "Output video in AVI JPEG format"),
            ('PNG', "PNG", "Output image in PNG format")
        ],
        default='AVI_JPEG',# type: ignore
    )
    
    output_file: bpy.props.StringProperty(
        name="Output File",
        description="File path to save the output",
        default="",
        maxlen=1024,
        subtype='FILE_PATH',# type: ignore
    )


class BATCH_RESOLUTION_OT_ExecuteButton(bpy.types.Operator):
    bl_idname = "batch_resolution.execute_button"
    bl_label = "执行"

    render_engine: bpy.props.StringProperty()# type: ignore
    output_format: bpy.props.StringProperty()# type: ignore
    input_dir: bpy.props.StringProperty()# type: ignore
    output_dir: bpy.props.StringProperty()# type: ignore
    output_resolution_x: bpy.props.StringProperty()# type: ignore
    output_resolution_y: bpy.props.StringProperty()# type: ignore
    resolution_percentage: bpy.props.StringProperty()# type: ignore
    output_frame_rate: bpy.props.StringProperty()# type: ignore
    output_file: bpy.props.StringProperty()# type: ignore
    change_resolution_prop: bpy.props.PointerProperty(type=ChangeResolutionProperties)# type: ignore

    def change_resolution(self, input_path, output_path):
        bpy.ops.wm.open_mainfile(filepath=input_path)
        
        self.clean_blend_file()

        # 尝试进行打包，如果遇到问题则忽略
        try:
            bpy.ops.file.pack_all()
        except Exception:
            pass
        scene = bpy.context.scene

        scene.render.resolution_x = int(self.output_resolution_x)
        scene.render.resolution_y = int(self.output_resolution_y)
        scene.render.resolution_percentage = int(self.resolution_percentage)
        scene.render.fps = int(self.output_frame_rate)
        scene.render.engine = self.render_engine
        scene.render.image_settings.file_format = self.output_format
        
        # 设置输出路径为 output_dir 和场景名称
        # scene.render.filepath = os.path.join(bpy.path.abspath(self.output_file), scene.name)

        # bpy.ops.wm.save_mainfile(filepath=output_path)

        blend_file_name = os.path.splitext(os.path.basename(input_path))[0]
        scene.render.filepath = os.path.join(bpy.path.abspath(self.output_file), blend_file_name)
        
        # 保存修改后的.blend文件
        bpy.ops.wm.save_mainfile(filepath=output_path)

    def clean_blend_file(self):
        bpy.ops.outliner.orphans_purge(do_recursive=True)

        

    def execute(self, context):
        # 存储当前打开的 .blend 文件的路径
        current_filepath = bpy.data.filepath

        prop = context.scene.change_resolution_prop

        absolute_input_dir = os.path.abspath(prop.input_dir)
        absolute_output_dir = os.path.abspath(prop.output_dir)

        with os.scandir(absolute_input_dir) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith(".blend"):
                    input_path = entry.path
                    output_path = os.path.join(absolute_output_dir, entry.name)
                    self.change_resolution(input_path, output_path)

        self.report({"INFO"}, "All files successfully modified!")

        # 使用之前存储的当前文件路径重新加载 .blend 文件
        if current_filepath:
            bpy.ops.wm.open_mainfile(filepath=current_filepath)

        return {"FINISHED"}

classes = (ChangeResolutionProperties,
           BATCH_RESOLUTION_OT_ExecuteButton,
           )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.change_resolution_prop = bpy.props.PointerProperty(type=ChangeResolutionProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.change_resolution_prop
