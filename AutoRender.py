import bpy
import mathutils
from bpy import context as C
import os
import traceback

from bpy.props import BoolProperty, EnumProperty, CollectionProperty# type: ignore
from bpy_extras.io_utils import ImportHelper # type: ignore

# 尝试导入PIL库，如果不存在则记录警告
PIL_AVAILABLE = False
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
    print("PIL库已成功导入，边框添加功能可用")
except ImportError:
    print("警告: 未能导入PIL库 (Pillow)，边框添加功能将被禁用")
    print("提示: 要启用边框功能，请在Blender的Python环境中安装Pillow库")
    print("可以通过Blender的Python或系统命令行运行: pip install Pillow")

class AutoRenderer():
    def __init__(self, collections: list, camera_name="Camera", 
                    output_path="./", output_name="", 
                    output_format="PNG", focus_each_object=False,
                    report_callback=None) -> None:
        """
        集合：字符串列表，每个字符串都是一个集合的名称
        report_callback: 可选的回调函数，用于向Blender信息窗口报告信息
        """
        self.collections = collections
        self.cam = bpy.data.objects.get(camera_name)  # 通过参数传递的 camera_name 获取相机对象
        if not self.cam:
            error_msg = f'找不到相机: "{camera_name}"'
            print(error_msg)
            if report_callback:
                report_callback({'ERROR'}, error_msg)
            raise KeyError(f'bpy_prop_collection[key]: key "{camera_name}" not found')
        self.output_path = output_path
        self.output_name = output_name
        self.output_format = output_format
        self.focus_each_object = focus_each_object
        self.report_callback = report_callback

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

    def report_info(self, info_type, message):
        """向控制台和Blender信息窗口报告信息"""
        print(message)
        if self.report_callback:
            self.report_callback(info_type, message)

    def render_collection(self, collection_name: str):
        print(f"\n--- 开始渲染集合: {collection_name} ---")
        # 更新预期的集合参考
        try:
            self.intended_collection = bpy.data.collections[collection_name]
            print(f"获取集合 '{collection_name}' 成功，包含 {len(self.intended_collection.objects)} 个对象")
        except KeyError:
            error_msg = f"找不到集合 '{collection_name}'"
            print(f"错误: {error_msg}")
            self.report_info({'ERROR'}, error_msg)
            raise KeyError(error_msg)
        
        # 确认透明背景设置
        background_is_transparent = bpy.context.scene.render.film_transparent
        print(f"渲染背景透明度设置: {background_is_transparent}")
        
        # 对集合中的物体按顶级父物体分组
        print("按顶级父物体分组中...")
        groups = self.group_objects_by_top_parent(self.intended_collection.objects)
        print(f"共找到 {len(groups)} 个顶级父物体分组")
        
        if not groups:
            warning_msg = f"集合 '{collection_name}' 中没有可渲染的对象"
            print(f"警告: {warning_msg}")
            self.report_info({'WARNING'}, warning_msg)
            return

        # 渲染每个分组的物体
        for top_parent_name, objects in groups.items():
            print(f"\n渲染顶级父物体分组: {top_parent_name}，包含 {len(objects)} 个对象")
            self.report_info({'INFO'}, f"正在渲染: {top_parent_name}")
            
            # 暂存当前集合内所有物体的渲染可见性
            original_hide_render = {o: o.hide_render for o in self.intended_collection.objects}
            print(f"保存了 {len(original_hide_render)} 个对象的原始渲染可见性")
            
            # 为渲染分组中的物体设置可见性
            print("设置渲染可见性...")
            for obj in self.intended_collection.objects:
                obj.hide_render = not obj in objects
            
            # 如果需要聚焦到对象
            if self.focus_each_object:
                focus_msg = f"聚焦到对象: {objects[0].name}"
                print(focus_msg)
                try:
                    self.focus_object(objects[0])
                except Exception as e:
                    error_msg = f"聚焦对象时出错: {str(e)}"
                    print(error_msg)
                    self.report_info({'WARNING'}, error_msg)
            
            # 渲染当前分组中的所有物体
            print("执行渲染操作...")
            try:
                # 设置渲染输出路径
                bpy.context.scene.render.filepath = filepath
                # 执行渲染并保存
                bpy.ops.render.render(write_still=True)
                print("渲染操作完成")
                save_msg = f"已保存: {filepath}"
                print(save_msg)
                self.report_info({'INFO'}, save_msg)
            except Exception as e:
                error_msg = f"渲染操作失败: {str(e)}"
                print(error_msg)
                self.report_info({'ERROR'}, error_msg)
                raise
            
            # 文件名使用顶级父级名称，如果物体没有父物体，则使用物体本身名称
            filename = top_parent_name if top_parent_name != objects[0].name else objects[0].name
            filepath = os.path.join(self.output_path, "{}.{}".format(filename, self.output_format.lower()))
            print(f"准备保存渲染结果到: {filepath}")

            # 保存渲染结果
            try:
                bpy.data.images["Render Result"].save_render(filepath=filepath)
                save_msg = f"已保存: {filepath}"
                print(save_msg)
                self.report_info({'INFO'}, save_msg)
            except Exception as e:
                error_msg = f"保存渲染结果失败: {str(e)}"
                print(error_msg)
                self.report_info({'ERROR'}, error_msg)
                raise
            
            # 添加边框并保存图像
            try:
                margin_distance = bpy.context.scene.auto_render_settings.margin_distance
                print(f"添加边框，边距: {margin_distance}像素")
                self.add_image_border(filepath, margin_distance, background_is_transparent)
                print("边框添加成功")
            except Exception as e:
                warning_msg = f"添加边框失败: {str(e)}"
                print(warning_msg)
                self.report_info({'WARNING'}, warning_msg)
                # 边框添加失败不影响主要功能，继续执行
                print("继续执行，忽略边框添加错误")

            # 恢复集合内其他物体的原始渲染可见性
            print("恢复原始渲染可见性...")
            for other_obj, visibility in original_hide_render.items():
                other_obj.hide_render = visibility
            
            print(f"完成渲染分组: {top_parent_name}")
        
        complete_msg = f"完成渲染集合: {collection_name}"
        print(f"--- {complete_msg} ---\n")
        self.report_info({'INFO'}, complete_msg)

    def add_image_border(self, image_path, margin_distance, background_is_transparent):
        """在图像周围添加边框，并根据背景透明度调整边框"""
        # 如果没有设置边框距离，则跳过
        if margin_distance <= 0:
            print(f"边框距离为 {margin_distance}，跳过边框添加")
            return
            
        # 检查PIL库是否可用
        if not PIL_AVAILABLE:
            print("PIL库不可用，跳过边框添加功能")
            return
            
        print(f"尝试为图像添加边框: {image_path}")
        
        try:
            with Image.open(image_path) as img:
                print(f"成功打开图像，尺寸: {img.size}, 模式: {img.mode}")
                
                # 确保图像是RGBA模式以支持透明度
                if img.mode != 'RGBA':
                    print(f"图像模式不是RGBA，正在从 {img.mode} 转换为RGBA")
                    img = img.convert('RGBA')
                
                # 确定边框填充颜色
                fill_color = (0, 0, 0, 0) if background_is_transparent else (0, 0, 0)
                print(f"边框颜色设置为: {fill_color} (RGBA)")
                
                # 使用PIL的ImageOps.expand来扩展边框
                print(f"正在添加边框，宽度: {margin_distance}")
                img_with_border = ImageOps.expand(img, border=margin_distance, fill=fill_color)
                print(f"边框添加成功，新尺寸: {img_with_border.size}")
                
                # 保存修改后的图像
                print(f"正在保存带边框的图像到: {image_path}")
                img_with_border.save(image_path)
                print("图像保存成功")
                
        except FileNotFoundError:
            print(f"错误: 找不到图像文件: {image_path}")
            return
        except Exception as e:
            print(f"添加边框时发生错误: {type(e).__name__}: {str(e)}")
            traceback.print_exc()
            return

    def auto_render(self):
        """
        在实例化时呈现提供列表中的所有集合。
        """
        print("\n=== 自动渲染开始 ===")
        print(f"要渲染的集合列表: {self.collections}")
        self.report_info({'INFO'}, "开始渲染流程")
        
        if not self.collections:
            warning_msg = "没有指定要渲染的集合"
            print(f"错误: {warning_msg}")
            self.report_info({'WARNING'}, warning_msg)
            return
        
        for collection_name in self.collections:
            print(f"处理集合: {collection_name}")
            try:
                self.render_collection(collection_name)
                print(f"集合 {collection_name} 渲染完成")
            except Exception as e:
                error_msg = f"渲染集合 {collection_name} 时出错: {str(e)}"
                print(error_msg)
                self.report_info({'ERROR'}, error_msg)
                raise
        
        complete_msg = "所有集合渲染完成"
        print(f"=== {complete_msg} ===\n")
        self.report_info({'INFO'}, complete_msg)

def get_all_cameras(self, context):
    return [(obj.name, obj.name, obj.name) for obj in bpy.context.scene.objects if obj.type == 'CAMERA']

def get_all_collections(self, context):
    return [(collection.name, collection.name, collection.name) for collection in bpy.data.collections]

class AUTO_RENDER_OneClick(bpy.types.Operator):
    bl_idname = "auto_render.oneclick"
    bl_label = "一键处理导入模型"
    bl_description = "一键处理导入模型"

    def execute(self, context):

        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.set_roughness(roughness=10)
        bpy.ops.object.set_emission_strength(strength=0)
        bpy.ops.object.set_texture_interpolation()
        bpy.ops.object.miao_queue_up()
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}



class AutoRenderSettings(bpy.types.PropertyGroup):
    output_path: bpy.props.StringProperty(
        name="Output Path",
        description="Output directory for rendered images",
        default="./",
        maxlen=1024,
        subtype='DIR_PATH'
    ) # type: ignore
    output_name: bpy.props.StringProperty(
        name="Output Name",
        description="Name of the rendered images",
        default=""
    ) # type: ignore
    output_format: bpy.props.EnumProperty(
        name="Output Format",
        description="Image format of the rendered images",
        items=[('PNG', 'PNG', 'PNG'), ('JPEG', 'JPEG', 'JPEG'), ('BMP', 'BMP', 'BMP'), ('TIFF', 'TIFF', 'TIFF')]
    ) # type: ignore
    collections: bpy.props.EnumProperty(
        name="Collections",
        description="Choose a collection to be rendered",
        default=None,
        items=get_all_collections
    ) # type: ignore
    cameras: bpy.props.EnumProperty(
        name="Cameras",
        description="Camera to be used for rendering",
        default=None,
        items=get_all_cameras
    ) # type: ignore # type: ignore
    focus_each_object: bpy.props.BoolProperty(
        name="Focus Each Object",
        description="Enable to focus camera on each object before rendering",
        default=False
    ) # type: ignore
    margin_distance: bpy.props.IntProperty(
        name="Margin Distance (px)",
        description="Margin distance between object and frame border in pixels",
        default=0,  # Default margin value in pixels
        min=0,
        max=1000
    ) # type: ignore
class AUTO_RENDER_OT_Execute(bpy.types.Operator):
    bl_idname = "auto_render.execute"
    bl_label = "渲染"
    bl_description = "Render the specified collections"

    def execute(self, context):
        print("\n=== 开始执行渲染操作 ===")
        scene = context.scene
        auto_render_settings = scene.auto_render_settings

        # 打印当前设置
        print(f"输出路径: {auto_render_settings.output_path}")
        print(f"输出名称: {auto_render_settings.output_name}")
        print(f"输出格式: {auto_render_settings.output_format}")
        print(f"选中的集合: {auto_render_settings.collections}")
        print(f"选中的相机: {auto_render_settings.cameras}")
        print(f"聚焦到每个物体: {auto_render_settings.focus_each_object}")
        print(f"边框距离: {auto_render_settings.margin_distance}")

        try:
            # 获取集合名称
            collection_name = auto_render_settings.collections
            if not collection_name:
                print("错误: 未选择任何集合")
                self.report({'ERROR'}, "请选择一个要渲染的集合")
                return {'CANCELLED'}
            print(f"准备渲染集合: {collection_name}")

            # 获取相机名称
            camera_name = auto_render_settings.cameras
            if not camera_name:
                print("错误: 未选择任何相机")
                self.report({'ERROR'}, "请选择一个用于渲染的相机")
                return {'CANCELLED'}
            print(f"使用相机: {camera_name}")

            # 检查相机是否存在
            cam = bpy.data.objects.get(camera_name)
            if not cam or cam.type != 'CAMERA':
                print(f"错误: 相机 '{camera_name}' 不存在或不是相机类型")
                self.report({'ERROR'}, f"相机 '{camera_name}' 不存在或不是相机类型")
                return {'CANCELLED'}
            print(f"相机对象验证通过: {cam.name}")

            # 检查集合是否存在
            col = bpy.data.collections.get(collection_name)
            if not col:
                print(f"错误: 集合 '{collection_name}' 不存在")
                self.report({'ERROR'}, f"集合 '{collection_name}' 不存在")
                return {'CANCELLED'}
            print(f"集合验证通过: {col.name}, 包含 {len(col.objects)} 个对象")

            # 检查输出路径
            output_path = auto_render_settings.output_path
            if not output_path:
                print("警告: 未设置输出路径，使用默认路径")
                output_path = "./"
            elif not os.path.exists(output_path):
                print(f"输出路径不存在，尝试创建: {output_path}")
                try:
                    os.makedirs(output_path, exist_ok=True)
                    print(f"成功创建输出路径: {output_path}")
                except Exception as e:
                    print(f"创建输出目录失败: {str(e)}")
                    self.report({'ERROR'}, f"无法创建输出目录: {str(e)}")
                    return {'CANCELLED'}

            output_name = auto_render_settings.output_name
            output_format = auto_render_settings.output_format
            focus_each_object = auto_render_settings.focus_each_object

            print("创建AutoRenderer实例...")
            # 传递self.report作为回调函数
            auto_renderer = AutoRenderer([collection_name], camera_name=camera_name,
                                        output_path=output_path, output_name=output_name,
                                        output_format=output_format, focus_each_object=focus_each_object,
                                        report_callback=self.report)
            
            print("开始执行渲染...")
            auto_renderer.auto_render()
            
            print(f"渲染完成，文件已保存到 {output_path}")
            self.report({'INFO'}, f"渲染完成，文件已保存到 {output_path}")
            print("=== 渲染操作结束 ===\n")
            
        except KeyError as e:
            print(f"KeyError: {str(e)}")
            self.report({'ERROR'}, f"键错误: {str(e)}")
            return {'CANCELLED'}
        except FileNotFoundError as e:
            print(f"FileNotFoundError: {str(e)}")
            self.report({'ERROR'}, f"文件未找到: {str(e)}")
            return {'CANCELLED'}
        except Exception as e:
            print(f"渲染过程中发生异常: {str(e)}")
            print(f"异常类型: {type(e).__name__}")
            traceback.print_exc()
            self.report({'ERROR'}, f"渲染失败: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

class BatchRenderOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "auto_render.batch_render"
    bl_label = "选择文件渲染"

    filename_ext = ".blend"

    filter_glob: bpy.props.StringProperty(
        default="*.blend",
        options={'HIDDEN'},
    ) # type: ignore

    files: CollectionProperty(name='File Path', type=bpy.types.OperatorFileListElement) # type: ignore

    render_as_animation: bpy.props.BoolProperty(
        name="Render as Animation",
        default=True,
        description="Enable to render as animation",
    ) # type: ignore
    

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
    bpy.utils.register_class(AUTO_RENDER_OneClick)

def unregister():
    bpy.utils.unregister_class(AUTO_RENDER_OT_Execute)
    del bpy.types.Scene.auto_render_settings
    bpy.utils.unregister_class(AutoRenderSettings)
    bpy.utils.unregister_class(BatchRenderOperator)
    del bpy.types.Scene.render_as_animation
    bpy.utils.unregister_class(AUTO_RENDER_OneClick)

if __name__ == "__main__":
    register()