import bpy
import mathutils
import math
from bpy import context as C
import os
import traceback
import time

from bpy.props import BoolProperty, EnumProperty, CollectionProperty# type: ignore

# 检查Blender版本兼容性
def is_blender_4_3_or_later():
    """检查是否为Blender 4.3或更高版本"""
    version = bpy.app.version
    return version >= (4, 3, 0)

def has_use_zbuffer_attribute():
    """检查ImageFormatSettings是否有use_zbuffer属性"""
    try:
        # 尝试访问use_zbuffer属性
        bpy.context.scene.render.image_settings.use_zbuffer
        return True
    except AttributeError:
        return False

# PIL库可用性标志，延迟检查
PIL_AVAILABLE = None

def check_pil_availability():
    """检查PIL库是否可用"""
    global PIL_AVAILABLE
    if PIL_AVAILABLE is None:
        try:
            from PIL import Image, ImageOps
            PIL_AVAILABLE = True
            print("PIL库已成功导入，边框添加功能可用")
        except ImportError:
            PIL_AVAILABLE = False
            print("警告: 未能导入PIL库 (Pillow)，边框添加功能将被禁用")
            print("提示: 要启用边框功能，请在Blender的Python环境中安装Pillow库")
    return PIL_AVAILABLE
    print("可以通过Blender的Python或系统命令行运行: pip install Pillow")

class AutoRenderer():
    def __init__(self, collections: list, camera_name="Camera", 
                    output_path="./", output_name="", output_format="PNG",
                                         naming_mode='AUTO', focus_each_object=False,
                     focus_only_faces=False, use_compositor=True, auto_keyframe=False, 
                     enable_resize=False, pixel_margin=0, render_each_object_individually=False,
                     report_callback=None) -> None:
        """
        集合：字符串列表，每个字符串都是一个集合的名称
        report_callback: 可选的回调函数，用于向Blender信息窗口报告信息
        """
        # 显示Blender版本兼容性信息
        version = bpy.app.version
        print(f"ℹ Blender版本: {version[0]}.{version[1]}.{version[2]}")
        if is_blender_4_3_or_later():
            print("ℹ 检测到Blender 4.3+，已适配use_zbuffer属性移除的变更")
        if not has_use_zbuffer_attribute():
            print("ℹ use_zbuffer属性不可用，将跳过Z缓冲相关设置")
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
        self.naming_mode = naming_mode
        self.focus_each_object = focus_each_object
        self.focus_only_faces = focus_only_faces
        self.use_compositor = use_compositor
        self.auto_keyframe = auto_keyframe
        self.enable_resize = enable_resize
        self.pixel_margin = pixel_margin
        self.render_each_object_individually = render_each_object_individually
        self.report_callback = report_callback
        
        # 包围盒缓存，避免重复计算
        self.bbox_cache = {}
        
        # 预计算包围盒标志
        self.bboxes_precomputed = False
        
        # 渲染状态标志
        self.is_rendering = False
        self.intended_collection = None
        
    def convert_exr_to_png(self, exr_filepath):
        """将EXR文件转换为PNG格式"""
        try:
            print(f"开始将EXR转换为PNG: {exr_filepath}")
            
            # 检查EXR文件是否存在
            if not os.path.exists(exr_filepath):
                print(f"❌ EXR文件不存在: {exr_filepath}")
                return False
            
            # 生成PNG文件路径
            png_filepath = exr_filepath.replace('.exr', '.png')
            print(f"PNG输出路径: {png_filepath}")
            
            # 使用Blender内置的图像处理功能进行转换
            try:
                # 加载EXR图像
                exr_image = bpy.data.images.load(exr_filepath, check_existing=False)
                print(f"✓ EXR图像加载成功: {exr_image.name}")
                
                # 设置PNG格式
                exr_image.file_format = 'PNG'
                exr_image.filepath_raw = png_filepath
                
                # 保存为PNG
                exr_image.save()
                print(f"✓ PNG图像保存成功: {png_filepath}")
                
                # 清理内存中的图像
                bpy.data.images.remove(exr_image)
                
                # 删除原始EXR文件
                if os.path.exists(exr_filepath):
                    os.remove(exr_filepath)
                    print(f"✓ 原始EXR文件已删除: {exr_filepath}")
                
                return True
                
            except Exception as e:
                print(f"⚠ Blender内置转换失败: {str(e)}")
                print("尝试使用PIL库进行转换...")
                
                # 回退到PIL库转换
                if check_pil_availability():
                    try:
                        from PIL import Image
                        
                        with Image.open(exr_filepath) as img:
                            # 确保图像是RGBA模式
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            
                            # 保存为PNG
                            img.save(png_filepath, 'PNG', optimize=True)
                            print(f"✓ PIL转换成功: {png_filepath}")
                            
                            # 删除原始EXR文件
                            if os.path.exists(exr_filepath):
                                os.remove(exr_filepath)
                                print(f"✓ 原始EXR文件已删除: {exr_filepath}")
                            
                            return True
                            
                    except Exception as pil_error:
                        print(f"❌ PIL转换也失败: {str(pil_error)}")
                        return False
                else:
                    print("❌ PIL库不可用，无法进行转换")
                    return False
                    
        except Exception as e:
            print(f"❌ EXR转PNG过程中发生错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    def generate_filename(self, top_parent_name, object_name):
        """根据命名模式生成文件名"""
        if self.naming_mode == 'AUTO':
            # 自动命名：使用顶级父级名称
            return top_parent_name
        elif self.naming_mode == 'CUSTOM':
            # 自定义名称：使用手动输入的名称
            if self.output_name:
                return self.output_name
            else:
                # 如果没有输入自定义名称，回退到自动命名
                print("⚠ 警告: 自定义名称模式下未输入名称，回退到自动命名")
                return top_parent_name
        elif self.naming_mode == 'HYBRID':
            # 混合命名：顶级父级名称 + 自定义名称
            if self.output_name:
                return f"{top_parent_name}_{self.output_name}"
            else:
                # 如果没有输入自定义名称，回退到自动命名
                print("⚠ 警告: 混合命名模式下未输入名称，回退到自动命名")
                return top_parent_name
        elif self.naming_mode == 'OBJECT':
            # 物体名称：使用物体本身的名称
            return object_name
        else:
            # 默认回退到自动命名
            print(f"⚠ 警告: 未知的命名模式 '{self.naming_mode}'，回退到自动命名")
            return top_parent_name

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

    def get_visible_children(self, obj):
        """获取物体的所有可见子物体（递归）"""
        visible_children = []
        
        # 检查物体本身是否可见
        if obj.type != 'EMPTY' and obj.hide_render == False:
            visible_children.append(obj)
        
        # 递归检查所有子物体
        for child in obj.children:
            visible_children.extend(self.get_visible_children(child))
            
        return visible_children
    
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
        将给定物体按顶级父物体分组，并确保包含所有可见的子物体。
        """
        groups = {}
        for obj in objects:
            top_parent = self.get_top_parent_name(obj)
            if top_parent not in groups:
                groups[top_parent] = []
            groups[top_parent].append(obj)
        
        # 扩展每个组，包含所有可见的子物体
        expanded_groups = {}
        for top_parent_name, objects in groups.items():
            # 获取该顶级父物体的所有相关子物体
            all_related_objects = self.get_all_related_objects(top_parent_name)
            
            # 临时保存原始可见性状态
            original_visibility = {}
            for obj in all_related_objects:
                original_visibility[obj] = obj.hide_render
            
            # 临时设置所有相关物体为可见，以便正确识别
            for obj in all_related_objects:
                obj.hide_render = False
            
            # 过滤出可见的物体（现在应该都能看到）
            visible_objects = [obj for obj in all_related_objects if not obj.hide_render]
            
            # 恢复原始可见性状态
            for obj, visibility in original_visibility.items():
                obj.hide_render = visibility
            
            if visible_objects:
                expanded_groups[top_parent_name] = visible_objects
                print(f"顶级父物体 '{top_parent_name}' 包含 {len(visible_objects)} 个可见子物体")
            else:
                print(f"警告: 顶级父物体 '{top_parent_name}' 没有可见的子物体")
        
        return expanded_groups

    def focus_object(self, objects):
        """聚焦到指定的对象组，确保能看到所有子集"""
        # 选择所有目标对象
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        
        # 预计算包围盒，提高后续计算性能
        self._precompute_bboxes(objects)
        
        # 在渲染模式下，更安全地处理关键帧影响
        original_frame = bpy.context.scene.frame_current
        original_animation_data = None
        if hasattr(self, 'is_rendering') and self.is_rendering:
            print("ℹ 渲染模式：安全处理关键帧影响，确保相机位置准确")
            # 保存当前帧的动画数据状态，但不完全禁用
            if self.cam.animation_data:
                original_animation_data = self.cam.animation_data
                # 记录当前帧，确保使用正确的关键帧数据
                current_frame = bpy.context.scene.frame_current
                print(f"ℹ 当前帧: {current_frame}")
        
        # 自动激活选中的相机
        print(f"ℹ 自动激活相机: {self.cam.name}")
        bpy.context.scene.camera = self.cam
        
        # 检查相机类型并应用相应的聚焦策略
        camera_data = self.cam.data
        is_orthographic = camera_data.type == 'ORTHO'
        
        print(f"ℹ 相机类型: {'正交相机' if is_orthographic else '透视相机'}")
        
        # 将视图切换到相机视图
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
                        area.spaces.active.region_3d.update()
                        
                        # 根据相机类型执行不同的聚焦逻辑
                        if is_orthographic:
                            self._focus_orthographic_camera(objects, camera_data)
                        else:
                            self._focus_perspective_camera(objects, camera_data)
                        
                        # 不再需要恢复动画数据，因为我们没有禁用它们
                        print(f"ℹ 相机聚焦完成，保持动画数据有效")
                        
                        # 验证相机位置是否正确对准物体
                        print("ℹ 验证相机位置...")
                        if self.verify_camera_position(objects):
                            print("✓ 相机位置验证通过")
                        else:
                            print("⚠ 相机位置验证失败，可能需要手动调整")
                        
                        # 自动关键帧：记录相机位置和旋转
                        print(f"检查是否需要添加关键帧: self.auto_keyframe = {self.auto_keyframe}")
                        if self.auto_keyframe:
                            print("✓ 启用自动关键帧，开始添加关键帧...")
                            self.auto_keyframe_camera()
                        else:
                            print("⚠ 自动关键帧未启用")
                        
                        break
    
    def _calculate_orthographic_scale(self, bbox_size, camera_data):
        """计算正交相机需要的缩放值（独立方法）"""
        try:
            if self.pixel_margin <= 0:
                return 0
            
            print(f"ℹ 计算正交相机缩放: 像素边距={self.pixel_margin}px")
            
            # 获取渲染分辨率
            render_width = bpy.context.scene.render.resolution_x
            render_height = bpy.context.scene.render.resolution_y
            print(f"ℹ 渲染分辨率: {render_width}x{render_height}")
            
            # 正交相机：精确的边距计算
            max_size = max(bbox_size)
            
            # 修正的像素到世界单位转换
            # 正交相机的视野由 ortho_scale 决定
            # 像素边距应该基于当前的正交缩放来计算
            current_ortho_scale = camera_data.ortho_scale
            
            # 计算像素边距对应的世界边距
            # 使用更精确的比例：当前缩放 / 渲染分辨率
            pixel_to_world_ratio = current_ortho_scale / min(render_width, render_height)
            world_margin = self.pixel_margin * pixel_to_world_ratio
            
            # 计算需要的正交缩放
            required_ortho_scale = max_size + world_margin * 2
            
            print(f"ℹ 正交相机缩放计算: 物体尺寸={max_size:.2f}, 像素边距={self.pixel_margin}px")
            print(f"ℹ 当前缩放={current_ortho_scale:.2f}, 像素比例={pixel_to_world_ratio:.6f}")
            print(f"ℹ 世界边距={world_margin:.2f}, 需要缩放={required_ortho_scale:.2f}")
            
            return required_ortho_scale
                
        except Exception as e:
            print(f"⚠ 计算正交相机缩放时出错: {str(e)}")
            return 0
    
    def _calculate_perspective_distance(self, bbox_size, camera_data):
        """计算透视相机需要的距离值（独立方法）"""
        try:
            if self.pixel_margin <= 0:
                return 0
            
            print(f"ℹ 计算透视相机距离: 像素边距={self.pixel_margin}px")
            
            # 获取渲染分辨率
            render_width = bpy.context.scene.render.resolution_x
            render_height = bpy.context.scene.render.resolution_y
            print(f"ℹ 渲染分辨率: {render_width}x{render_height}")
            
            # 透视相机：精确的边距计算
            max_size = max(bbox_size)
            fov_degrees = 2 * math.degrees(math.atan(16 / camera_data.lens))
            fov_radians = math.radians(fov_degrees)
            
            # 计算基础距离（无边距）
            base_distance = (max_size / 2) / math.tan(fov_radians / 2)
            
            # 修正的像素边距计算
            # 基于视野角度和基础距离计算
            fov_half_radians = fov_radians / 2
            
            # 像素边距在世界空间中的对应距离
            # 使用三角函数关系：tan(fov/2) = (size/2) / distance
            # 因此：pixel_margin_world = pixel_margin * (max_size/2) / (render_width/2) / tan(fov/2)
            pixel_margin_world = (self.pixel_margin * (max_size / 2)) / (render_width / 2) / math.tan(fov_half_radians)
            
            # 计算带边距的距离
            required_distance = base_distance + pixel_margin_world
            
            print(f"ℹ 透视相机距离计算: 物体尺寸={max_size:.2f}, 像素边距={self.pixel_margin}px")
            print(f"ℹ 视野角度={fov_degrees:.2f}°, 基础距离={base_distance:.2f}")
            print(f"ℹ 像素边距世界距离={pixel_margin_world:.2f}, 需要距离={required_distance:.2f}")
            
            return required_distance
                
        except Exception as e:
            print(f"⚠ 计算透视相机距离时出错: {str(e)}")
            return 0
    
    def _verify_camera_view_coverage(self, objects, camera_data, is_orthographic):
        """验证相机视野是否足够覆盖所有物体"""
        try:
            print("ℹ 验证相机视野覆盖...")
            
            # 计算所有物体的边界框
            bbox_min, bbox_max = self._calculate_group_bbox(objects)
            if not bbox_min or not bbox_max:
                print("⚠ 无法计算边界框，跳过视野验证")
                return
            
            bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
            max_size = max(bbox_size)
            
            if is_orthographic:
                # 验证正交相机视野
                current_scale = camera_data.ortho_scale
                coverage_ratio = current_scale / max_size
                
                print(f"ℹ 正交相机视野验证: 当前缩放={current_scale:.2f}, 物体尺寸={max_size:.2f}, 覆盖比例={coverage_ratio:.2f}")
                
                # 更保守的验证：只在实际不足时才调整
                if coverage_ratio < 1.05:  # 降低阈值到1.05
                    safety_scale = max_size * 1.05  # 只增加5%的安全边距
                    camera_data.ortho_scale = safety_scale
                    print(f"⚠ 视野不足，增加正交缩放到: {safety_scale:.2f}")
                else:
                    print("✓ 正交相机视野充足")
                    
            else:
                # 验证透视相机视野
                bbox_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
                camera_to_center = (self.cam.location - mathutils.Vector(bbox_center)).length
                
                fov_degrees = 2 * math.degrees(math.atan(16 / camera_data.lens))
                fov_radians = math.radians(fov_degrees)
                
                # 计算当前视野下的物体覆盖情况
                required_distance = (max_size / 2) / math.tan(fov_radians / 2)
                coverage_ratio = camera_to_center / required_distance
                
                print(f"ℹ 透视相机视野验证: 当前距离={camera_to_center:.2f}, 需要距离={required_distance:.2f}, 覆盖比例={coverage_ratio:.2f}")
                
                # 更保守的验证：只在实际不足时才调整
                if coverage_ratio < 1.05:  # 降低阈值到1.05
                    safety_distance = required_distance * 1.05  # 只增加5%的安全边距
                    direction = (self.cam.location - mathutils.Vector(bbox_center)).normalized()
                    new_position = mathutils.Vector(bbox_center) + direction * safety_distance
                    self.cam.location = new_position
                    print(f"⚠ 视野不足，增加相机距离到: {safety_distance:.2f}")
                else:
                    print("✓ 透视相机视野充足")
                    
        except Exception as e:
            print(f"⚠ 视野验证时出错: {str(e)}")
    
    # 像素边距控制属性已移动到AutoRenderSettings类中
    
    # 像素边距控制属性已移动到AutoRenderSettings类中
    
    # 视野验证和微调功能已移除，现在使用统一的标准聚焦方法
    
    def focus_single_object(self, obj):
        """聚焦到单个物体，为关键帧生成做准备"""
        try:
            print(f"ℹ 开始聚焦到单个物体: {obj.name}")
            
            # 选择单个物体
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            
            # 自动激活选中的相机
            print(f"ℹ 自动激活相机: {self.cam.name}")
            bpy.context.scene.camera = self.cam
            
            # 将视图切换到相机视图
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.region_3d.view_perspective = 'CAMERA'
                            area.spaces.active.region_3d.update()
                            
                            # 使用与渲染时相同的聚焦逻辑，确保位置一致
                            # 根据相机类型执行不同的聚焦策略
                            camera_data = self.cam.data
                            if camera_data.type == 'ORTHO':
                                # 正交相机：调整正交缩放
                                self._focus_orthographic_camera_for_keyframe(obj, camera_data)
                            else:
                                # 透视相机：调整距离，不改变焦距
                                self._focus_perspective_camera_for_keyframe(obj, camera_data)
                            
                            # 如果启用了自动关键帧，为单个物体添加关键帧
                            if self.auto_keyframe:
                                print(f"✓ 为物体 '{obj.name}' 添加关键帧")
                                self.auto_keyframe_camera()
                            
                            break
            
            print(f"✓ 成功聚焦到物体: {obj.name}")
            
        except Exception as e:
            print(f"⚠ 聚焦到物体 '{obj.name}' 时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _adjust_camera_for_object(self, obj):
        """为单个物体调整相机的距离和视野，确保物体完美框住"""
        try:
            print(f"ℹ 开始调整相机参数以完美框住物体: {obj.name}")
            
            # 获取相机数据
            camera_data = self.cam.data
            margin = bpy.context.scene.auto_render_settings.margin_distance
            
            # 计算物体的边界框
            bbox_min, bbox_max = self._calculate_object_bbox(obj)
            if not bbox_min or not bbox_max:
                print("⚠ 无法计算物体边界框，跳过相机调整")
                return
            
            # 计算边界框的中心和尺寸
            bbox_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
            bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
            
            print(f"ℹ 物体边界框: 中心={bbox_center}, 尺寸={bbox_size}")
            
            if camera_data.type == 'ORTHO':
                # 正交相机：不调整参数，边距通过图像处理添加
                print("ℹ 正交相机：保持原始参数，边距通过图像处理添加")
            else:
                # 透视相机：只调整距离，不改变朝向和焦距
                self._adjust_perspective_camera_position_only(bbox_center, bbox_size, margin)
            
            print("✓ 相机参数调整完成")
            
        except Exception as e:
            print(f"⚠ 调整相机参数时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _calculate_object_bbox(self, obj):
        """计算物体的世界空间边界框（优化版：使用Blender内置包围盒+缓存）"""
        try:
            if obj.type != 'MESH' or not obj.data:
                print(f"⚠ 物体 '{obj.name}' 不是网格或没有数据")
                return None, None
            
            # 检查缓存
            # 使用矩阵的字符串表示作为缓存键，因为matrix_world没有hash方法
            matrix_str = str(obj.matrix_world)
            cache_key = f"{obj.name}_{hash(matrix_str)}"
            if cache_key in self.bbox_cache:
                print(f"ℹ 使用缓存的包围盒: {obj.name}")
                return self.bbox_cache[cache_key]
            
            # 使用Blender内置的包围盒计算，性能更好
            # 获取物体的本地包围盒
            local_bbox = obj.bound_box
            
            # 转换为世界空间包围盒
            bbox_min = [float('inf')] * 3
            bbox_max = [float('-inf')] * 3
            
            # 将本地包围盒的8个顶点转换到世界空间
            for vertex in local_bbox:
                world_pos = obj.matrix_world @ mathutils.Vector(vertex)
                for i in range(3):
                    bbox_min[i] = min(bbox_min[i], world_pos[i])
                    bbox_max[i] = max(bbox_max[i], world_pos[i])
            
            # 缓存结果
            result = (bbox_min, bbox_max)
            self.bbox_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"⚠ 计算边界框时出错: {str(e)}")
            return None, None
    
    def _focus_orthographic_camera(self, objects, camera_data):
        """正交相机聚焦逻辑（完全独立）"""
        try:
            print("ℹ 执行正交相机聚焦策略")
            
            # 使用标准聚焦方法
            bpy.ops.view3d.camera_to_view_selected()
            
            # 如果设置了像素边距，调整正交缩放
            if self.pixel_margin > 0:
                # 计算物体的边界框
                bbox_min, bbox_max = self._calculate_group_bbox(objects)
                if bbox_min and bbox_max:
                    bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
                    required_scale = self._calculate_orthographic_scale(bbox_size, camera_data)
                    if required_scale > 0:
                        camera_data.ortho_scale = required_scale
                        print(f"ℹ 正交相机：调整缩放到 {required_scale:.2f} (像素边距: {self.pixel_margin}px)")
            else:
                print("ℹ 正交相机：保持原始参数，边距通过图像处理添加")
                
        except Exception as e:
            print(f"⚠ 正交相机聚焦时出错: {str(e)}")
    
    def _focus_perspective_camera(self, objects, camera_data):
        """透视相机聚焦逻辑（完全独立）"""
        try:
            print("ℹ 执行透视相机聚焦策略")
            
            # 使用标准聚焦方法
            bpy.ops.view3d.camera_to_view_selected()
            
            # 如果设置了像素边距，调整相机距离
            if self.pixel_margin > 0:
                # 计算物体的边界框
                bbox_min, bbox_max = self._calculate_group_bbox(objects)
                if bbox_min and bbox_max:
                    bbox_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
                    bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
                    required_distance = self._calculate_perspective_distance(bbox_size, camera_data)
                    if required_distance > 0:
                        # 调整相机距离
                        bbox_center_vec = mathutils.Vector(bbox_center)
                        direction = (self.cam.location - bbox_center_vec).normalized()
                        new_position = bbox_center_vec + direction * required_distance
                        self.cam.location = new_position
                        print(f"ℹ 透视相机：调整距离到 {required_distance:.2f} (像素边距: {self.pixel_margin}px)")
            else:
                print(f"ℹ 透视相机：保持原始参数，焦距: {camera_data.lens:.2f}mm")
                
        except Exception as e:
            print(f"⚠ 透视相机聚焦时出错: {str(e)}")
    
    def _focus_orthographic_camera_for_keyframe(self, obj, camera_data):
        """正交相机关键帧聚焦逻辑（独立方法）"""
        try:
            print(f"ℹ 正交相机关键帧聚焦: {obj.name}")
            
            # 使用标准聚焦方法
            bpy.ops.view3d.camera_to_view_selected()
            
            # 如果设置了像素边距，调整正交缩放
            if self.pixel_margin > 0:
                bbox_min, bbox_max = self._calculate_object_bbox(obj)
                if bbox_min and bbox_max:
                    bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
                    required_scale = self._calculate_orthographic_scale(bbox_size, camera_data)
                    if required_scale > 0:
                        camera_data.ortho_scale = required_scale
                        print(f"ℹ 关键帧生成：调整正交缩放到 {required_scale:.2f} (像素边距: {self.pixel_margin}px)")
            else:
                print("ℹ 关键帧生成：保持原始正交缩放")
                
        except Exception as e:
            print(f"⚠ 正交相机关键帧聚焦时出错: {str(e)}")
    
    def _focus_perspective_camera_for_keyframe(self, obj, camera_data):
        """透视相机关键帧聚焦逻辑（独立方法）"""
        try:
            print(f"ℹ 透视相机关键帧聚焦: {obj.name}")
            
            # 使用标准聚焦方法
            bpy.ops.view3d.camera_to_view_selected()
            
            # 如果设置了像素边距，调整相机距离
            if self.pixel_margin > 0:
                bbox_min, bbox_max = self._calculate_object_bbox(obj)
                if bbox_min and bbox_max:
                    bbox_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
                    bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
                    required_distance = self._calculate_perspective_distance(bbox_size, camera_data)
                    if required_distance > 0:
                        bbox_center_vec = mathutils.Vector(bbox_center)
                        direction = (self.cam.location - bbox_center_vec).normalized()
                        new_position = bbox_center_vec + direction * required_distance
                        self.cam.location = new_position
                        print(f"ℹ 关键帧生成：调整相机距离到 {required_distance:.2f} (像素边距: {self.pixel_margin}px)")
            else:
                print(f"ℹ 关键帧生成：保持原始参数，焦距: {camera_data.lens:.2f}mm")
                
        except Exception as e:
            print(f"⚠ 透视相机关键帧聚焦时出错: {str(e)}")
    
    def _precompute_bboxes(self, objects):
        """预计算所有物体的包围盒，提高性能"""
        try:
            if self.bboxes_precomputed:
                print("ℹ 包围盒已预计算，跳过")
                return
            
            print("ℹ 开始预计算包围盒...")
            start_time = time.time()
            
            for obj in objects:
                if obj.type == 'MESH' and obj.data:
                    # 预计算并缓存包围盒
                    self._calculate_object_bbox(obj)
            
            self.bboxes_precomputed = True
            end_time = time.time()
            print(f"✓ 包围盒预计算完成，耗时: {end_time - start_time:.3f}秒")
            
        except Exception as e:
            print(f"⚠ 预计算包围盒时出错: {str(e)}")
    
    def _calculate_group_bbox(self, objects):
        """计算整个物体组的世界空间边界框（优化版：使用包围盒+调试）"""
        try:
            bbox_min = [float('inf')] * 3
            bbox_max = [float('-inf')] * 3
            
            print(f"ℹ 开始计算组边界框，物体数量: {len(objects)}")
            
            for obj in objects:
                if obj.type == 'MESH' and obj.data:
                    print(f"ℹ 处理物体: {obj.name}")
                    print(f"  - 类型: {obj.type}")
                    print(f"  - 顶点数: {len(obj.data.vertices)}")
                    print(f"  - 变换矩阵: {obj.matrix_world}")
                    
                    # 使用优化后的单个物体包围盒计算
                    obj_bbox_min, obj_bbox_max = self._calculate_object_bbox(obj)
                    if obj_bbox_min and obj_bbox_max:
                        print(f"  - 物体边界框: 最小={obj_bbox_min}, 最大={obj_bbox_max}")
                        
                        # 合并到组边界框
                        for i in range(3):
                            bbox_min[i] = min(bbox_min[i], obj_bbox_min[i])
                            bbox_max[i] = max(bbox_max[i], obj_bbox_max[i])
                    else:
                        print(f"  ⚠ 物体 '{obj.name}' 边界框计算失败")
                else:
                    print(f"ℹ 跳过物体: {obj.name} (类型: {obj.type})")
            
            # 检查是否找到了有效的边界框
            if bbox_min[0] == float('inf'):
                print("⚠ 未找到有效的网格物体")
                return None, None
            
            print(f"ℹ 组边界框计算结果:")
            print(f"  - 最小: {bbox_min}")
            print(f"  - 最大: {bbox_max}")
            print(f"  - 尺寸: {[bbox_max[i] - bbox_min[i] for i in range(3)]}")
            
            return bbox_min, bbox_max
            
        except Exception as e:
            print(f"⚠ 计算组边界框时出错: {str(e)}")
            return None, None
    
    # 正交相机使用简单的缩放调整，不需要复杂的计算方法
    # 原始逻辑：camera_data.ortho_scale *= (1.0 + margin * 0.1)
    
    def _adjust_perspective_camera_position_only(self, bbox_center, bbox_size, margin):
        """调整透视相机的参数（只调整位置，保持焦距和朝向不变）"""
        try:
            print("ℹ 调整透视相机位置...")
            
            camera_data = self.cam.data
            bbox_center_vec = mathutils.Vector(bbox_center)
            
            # 记录原始焦距
            original_lens = camera_data.lens
            print(f"ℹ 原始焦距: {original_lens:.2f}mm")
            
            # 获取相机的视野角度
            fov_degrees = 2 * math.degrees(math.atan(16 / camera_data.lens))
            print(f"ℹ 相机视野角度: {fov_degrees:.2f}度")
            print(f"ℹ 严格保持焦距和朝向不变，只调整相机位置")
            
            # 计算需要的距离以确保物体完全可见
            max_size = max(bbox_size)
            fov_radians = math.radians(fov_degrees)
            required_distance = (max_size / 2) / math.tan(fov_radians / 2)
            
            # 不添加边框距离，边距通过图像处理添加
            print(f"ℹ 计算的基础距离: {required_distance:.2f}")
            print(f"ℹ 边距将通过图像处理添加，不调整相机距离")
            
            # 计算从物体中心到相机的方向向量
            direction = (self.cam.location - bbox_center_vec).normalized()
            
            # 将相机移动到合适的位置
            new_position = bbox_center_vec + direction * required_distance
            self.cam.location = new_position
            
            print(f"ℹ 调整相机位置: {new_position}")
            print(f"ℹ 保持相机原始朝向: {self.cam.rotation_euler}")
            
            # 验证焦距没有改变
            if abs(camera_data.lens - original_lens) > 0.001:
                print(f"⚠ 警告: 焦距被意外改变，恢复原始值")
                camera_data.lens = original_lens
            
            print(f"✓ 透视相机调整完成: 距离={required_distance:.2f}, 焦距保持={camera_data.lens:.2f}mm")
            
        except Exception as e:
            print(f"⚠ 调整透视相机时出错: {str(e)}")
            # 如果出错，确保焦距恢复
            if 'original_lens' in locals():
                camera_data.lens = original_lens
                print(f"ℹ 已恢复原始焦距: {original_lens:.2f}mm")
    
    def _ensure_camera_looks_at(self, target_point):
        """确保相机朝向目标点"""
        try:
            direction = (target_point - self.cam.location).normalized()
            
            # 计算旋转矩阵
            rot_quat = direction.to_track_quat('-Z', 'Y')
            self.cam.rotation_euler = rot_quat.to_euler()
            
            print(f"ℹ 调整相机朝向: {self.cam.rotation_euler}")
            
        except Exception as e:
            print(f"⚠ 调整相机朝向时出错: {str(e)}")
    
    def _fine_tune_perspective_fov(self, bbox_center, bbox_size, fov_degrees):
        """微调透视相机的视野（保持焦距不变）"""
        try:
            camera_data = self.cam.data
            
            # 计算当前视野下的物体覆盖情况
            camera_to_center = (self.cam.location - bbox_center).length
            max_size = max(bbox_size)
            current_fov = 2 * math.degrees(math.atan(16 / camera_data.lens))
            
            # 计算物体在当前距离下的视野角度
            object_fov = 2 * math.degrees(math.atan((max_size / 2) / camera_to_center))
            
            print(f"ℹ 视野分析: 相机视野={current_fov:.2f}°, 物体视野={object_fov:.2f}°")
            print(f"ℹ 焦距保持: {camera_data.lens:.2f}mm (不自动调整)")
            
            # 如果物体视野过大，只记录信息，不调整焦距
            if object_fov > current_fov * 0.8:
                print(f"ℹ 注意: 物体视野({object_fov:.2f}°)较大，但焦距保持{camera_data.lens:.2f}mm不变")
                print(f"ℹ 如需调整视野，请手动修改相机焦距设置")
            
        except Exception as e:
            print(f"⚠ 微调视野时出错: {str(e)}")

    def auto_keyframe_camera(self):
        """自动为相机添加关键帧，根据相机类型使用不同策略"""
        try:
            current_frame = bpy.context.scene.frame_current
            camera = self.cam
            camera_data = camera.data
            
            print(f"开始为相机 '{camera.name}' 添加关键帧...")
            print(f"当前帧: {current_frame}")
            print(f"相机类型: {'正交相机' if camera_data.type == 'ORTHO' else '透视相机'}")
            print(f"相机位置: {camera.location}")
            print(f"相机旋转: {camera.rotation_euler}")
            
            # 为相机位置添加关键帧
            camera.keyframe_insert(data_path="location", frame=current_frame)
            print(f"✓ 位置关键帧添加成功")
            
            # 为相机旋转添加关键帧
            camera.keyframe_insert(data_path="rotation_euler", frame=current_frame)
            print(f"✓ 旋转关键帧添加成功")
            
            # 根据相机类型添加不同的关键帧
            if camera_data.type == 'ORTHO':
                # 正交相机：添加正交缩放关键帧
                camera_data.keyframe_insert(data_path="ortho_scale", frame=current_frame)
                print(f"✓ 正交缩放关键帧添加成功: {camera_data.ortho_scale:.2f}")
            else:
                # 透视相机：不添加焦距关键帧，保持焦距不变
                print(f"ℹ 透视相机：保持焦距 {camera_data.lens:.2f}mm 不变，不生成焦距关键帧")
            
            # 验证关键帧是否添加成功
            if camera.animation_data and camera.animation_data.action:
                print(f"✓ 相机动画数据验证成功")
                print(f"  - 动作名称: {camera.animation_data.action.name}")
                print(f"  - 总F曲线数: {len(camera.animation_data.action.fcurves)}")
            else:
                print("⚠ 警告: 相机没有动画数据")
            
            print(f"✓ 已为相机 '{camera.name}' 在第 {current_frame} 帧添加关键帧")
            
        except Exception as e:
            print(f"⚠ 添加关键帧时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def clear_all_camera_keyframes(self):
        """清除相机的所有关键帧（完整版）"""
        try:
            camera = self.cam
            if not camera:
                print("⚠ 未找到相机对象")
                return False
            
            print(f"ℹ 开始清除相机 '{camera.name}' 的关键帧...")
            
            # 保存相机当前位置和旋转，防止清除关键帧后位置丢失
            original_location = camera.location.copy()
            original_rotation = camera.rotation_euler.copy()
            original_scale = camera.scale.copy()
            
            # 保存相机数据的关键参数
            camera_data = camera.data
            original_lens = camera_data.lens if hasattr(camera_data, 'lens') else 50.0
            original_ortho_scale = camera_data.ortho_scale if hasattr(camera_data, 'ortho_scale') else 6.0
            original_clip_start = camera_data.clip_start if hasattr(camera_data, 'clip_start') else 0.1
            original_clip_end = camera_data.clip_end if hasattr(camera_data, 'clip_end') else 1000.0
            
            print(f"ℹ 保存相机原始参数:")
            print(f"  - 位置: {original_location}")
            print(f"  - 旋转: {original_rotation}")
            print(f"  - 缩放: {original_scale}")
            print(f"  - 焦距: {original_lens}")
            print(f"  - 正交缩放: {original_ortho_scale}")
            
            # 清除相机对象的关键帧
            if camera.animation_data and camera.animation_data.action:
                print(f"ℹ 清除相机对象关键帧...")
                for fcurve in camera.animation_data.action.fcurves:
                    if fcurve.data_path == "location":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除位置关键帧")
                    elif fcurve.data_path == "rotation_euler":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除旋转关键帧")
                    elif fcurve.data_path == "scale":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除缩放关键帧")
            
            # 清除相机数据的关键帧
            if camera.data and camera.data.animation_data and camera.data.animation_data.action:
                print(f"ℹ 清除相机数据关键帧...")
                for fcurve in camera.data.animation_data.action.fcurves:
                    if fcurve.data_path == "lens":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除焦距关键帧")
                    elif fcurve.data_path == "ortho_scale":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除正交缩放关键帧")
                    elif fcurve.data_path == "clip_start":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除近裁剪面关键帧")
                    elif fcurve.data_path == "clip_end":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除远裁剪面关键帧")
                    elif fcurve.data_path == "sensor_width":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除传感器宽度关键帧")
                    elif fcurve.data_path == "sensor_height":
                        fcurve.keyframe_points.clear()
                        print(f"  ✓ 清除传感器高度关键帧")
            
            # 统计清除的关键帧数量
            total_cleared = 0
            if camera.animation_data and camera.animation_data.action:
                total_cleared += len(camera.animation_data.action.fcurves)
            if camera.data and camera.data.animation_data and camera.data.animation_data.action:
                total_cleared += len(camera.data.animation_data.action.fcurves)
            
            # 恢复相机位置和参数，确保清除关键帧后相机仍然在正确位置
            print(f"ℹ 恢复相机原始参数...")
            camera.location = original_location
            camera.rotation_euler = original_rotation
            camera.scale = original_scale
            
            if hasattr(camera_data, 'lens'):
                camera_data.lens = original_lens
            if hasattr(camera_data, 'ortho_scale'):
                camera_data.ortho_scale = original_ortho_scale
            if hasattr(camera_data, 'clip_start'):
                camera_data.clip_start = original_clip_start
            if hasattr(camera_data, 'clip_end'):
                camera_data.clip_end = original_clip_end
            
            print(f"✓ 已清除相机 '{camera.name}' 的所有关键帧 (共 {total_cleared} 个曲线)")
            print(f"✓ 相机位置和参数已恢复，确保渲染正常")
            return True
            
        except Exception as e:
            print(f"⚠ 清除关键帧时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def report_info(self, info_type, message):
        """向控制台和Blender信息窗口报告信息"""
        print(message)
        if self.report_callback:
            self.report_callback(info_type, message)

    def render_collection(self, collection_name: str):
        print(f"\n--- 开始渲染集合: {collection_name} ---")
        
        # 在开始渲染前清理相机关键帧，避免所有图像都是同一张图的问题
        print("ℹ 开始渲染前清理相机关键帧...")
        try:
            if self.clear_all_camera_keyframes():
                print("✓ 相机关键帧清理完成")
            else:
                print("⚠ 相机关键帧清理失败，但继续渲染")
        except Exception as e:
            print(f"⚠ 清理关键帧时出错: {str(e)}，但继续渲染")
        
        # 设置渲染状态标志
        self.is_rendering = True
        
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
        
        # 确保相机被激活
        print(f"ℹ 确保相机 '{self.cam.name}' 被激活...")
        bpy.context.scene.camera = self.cam
        print(f"✅ 相机已激活: {bpy.context.scene.camera.name}")
        
        # 对集合中的物体按顶级父物体分组
        print("按顶级父物体分组中...")
        
        # 在Blender 4.3中，需要确保集合对象列表是最新的
        # 强制刷新集合对象列表（仅在4.3+版本中可用）
        if is_blender_4_3_or_later():
            try:
                self.intended_collection.objects.update()
                print("ℹ 已刷新集合对象列表（Blender 4.3+）")
            except AttributeError:
                print("ℹ 集合对象列表刷新不可用，使用默认行为")
        else:
            print("ℹ 使用Blender 3.6兼容模式")
        
        # 获取集合中的所有对象，包括嵌套集合中的对象
        all_objects = []
        for obj in self.intended_collection.objects:
            all_objects.append(obj)
        
        # 递归获取嵌套集合中的对象
        def get_nested_objects(collection):
            nested_objects = []
            for obj in collection.objects:
                nested_objects.append(obj)
            for child_collection in collection.children:
                nested_objects.extend(get_nested_objects(child_collection))
            return nested_objects
        
        nested_objects = get_nested_objects(self.intended_collection)
        all_objects.extend(nested_objects)
        
        print(f"集合 '{collection_name}' 包含 {len(all_objects)} 个对象（包括嵌套集合）")
        
        groups = self.group_objects_by_top_parent(all_objects)
        print(f"共找到 {len(groups)} 个顶级父物体分组")
        
        # 打印分组详情
        for top_parent_name, objects in groups.items():
            print(f"分组 '{top_parent_name}':")
            for obj in objects:
                print(f"  - {obj.name} (类型: {obj.type}, 隐藏渲染: {obj.hide_render})")
        
        if not groups:
            warning_msg = f"集合 '{collection_name}' 中没有可渲染的对象"
            print(f"警告: {warning_msg}")
            self.report_info({'WARNING'}, warning_msg)
            return

        # 渲染每个分组的物体
        total_groups = len(groups)
        current_group = 0
        for top_parent_name, objects in groups.items():
            current_group += 1
            print(f"\n=== 渲染第 {current_group}/{total_groups} 个顶级父物体分组 ===")
            print(f"分组名称: {top_parent_name}，包含 {len(objects)} 个对象")
            self.report_info({'INFO'}, f"正在渲染第 {current_group}/{total_groups} 个分组: {top_parent_name}")
            
            # 打印详细的物体信息用于调试
            print(f"该组包含的物体:")
            for obj in objects:
                print(f"  - {obj.name} (类型: {obj.type}, 隐藏渲染: {obj.hide_render})")
            
            # 检查是否有可见的物体
            visible_objects = [obj for obj in objects if obj.hide_render == False]
            if not visible_objects:
                warning_msg = f"分组 '{top_parent_name}' 中没有可见的物体，跳过渲染"
                print(f"警告: {warning_msg}")
                self.report_info({'WARNING'}, warning_msg)
                continue
            
            print(f"可见物体数量: {len(visible_objects)}")
            
            # 如果启用了仅聚焦有面的物体，显示相关信息
            if self.focus_only_faces:
                faces_objects = [obj for obj in visible_objects if self.has_faces(obj)]
                print(f"有面的物体数量: {len(faces_objects)}")
                if faces_objects:
                    print("有面的物体列表:")
                    for obj in faces_objects:
                        print(f"  - {obj.name} (面数: {len(obj.data.polygons) if obj.data else 0})")
                else:
                    print("警告: 没有找到有面的物体")
            
            # 暂存当前集合内所有物体的渲染可见性
            original_hide_render = {o: o.hide_render for o in self.intended_collection.objects}
            print(f"保存了 {len(original_hide_render)} 个对象的原始渲染可见性")
            
            # 为渲染分组中的物体设置可见性
            print("设置渲染可见性...")
            for obj in self.intended_collection.objects:
                obj.hide_render = not obj in objects
            
            # 如果需要聚焦到对象
            if self.focus_each_object:
                # 确定要聚焦的物体列表
                focus_objects = visible_objects
                if self.focus_only_faces:
                    focus_objects = [obj for obj in visible_objects if self.has_faces(obj)]
                    if not focus_objects:
                        print("警告: 没有找到有面的物体用于聚焦，跳过聚焦")
                        focus_objects = visible_objects  # 回退到所有可见物体
                
                # 真正的"聚焦到每个物体"：逐个聚焦到每个物体
                print(f"ℹ 开始逐个聚焦到每个物体，共 {len(focus_objects)} 个物体")
                for i, focus_obj in enumerate(focus_objects):
                    print(f"ℹ 聚焦到第 {i+1}/{len(focus_objects)} 个物体: {focus_obj.name}")
                    try:
                        self.focus_single_object(focus_obj)  # 聚焦到单个物体
                    except Exception as e:
                        error_msg = f"聚焦物体 '{focus_obj.name}' 时出错: {str(e)}"
                        print(error_msg)
                        self.report_info({'WARNING'}, error_msg)
                
                # 最后聚焦到整个物体组（用于渲染）
                focus_msg = f"最终聚焦到对象组: {top_parent_name}，包含 {len(focus_objects)} 个物体"
                print(focus_msg)
                try:
                    self.focus_object(focus_objects)  # 聚焦到整个物体组用于渲染
                except Exception as e:
                    error_msg = f"聚焦对象组时出错: {str(e)}"
                    print(error_msg)
                    self.report_info({'WARNING'}, error_msg)
            
            # 渲染当前分组中的所有物体
            print("执行渲染操作...")
            try:
                # 根据命名模式生成文件名
                filename = self.generate_filename(top_parent_name, objects[0].name)
                
                # 根据输出格式确定文件扩展名和路径
                if self.output_format == 'EXR_TO_PNG':
                    # EXR→PNG模式：先渲染为EXR，然后转换
                    temp_extension = 'exr'
                    final_extension = 'png'
                    is_exr_to_png_mode = True
                elif self.output_format == 'EXR':
                    file_extension = 'exr'
                    is_exr_to_png_mode = False
                else:
                    file_extension = self.output_format.lower()
                    is_exr_to_png_mode = False
                
                # 生成临时文件路径（用于渲染）
                if is_exr_to_png_mode:
                    temp_filepath = os.path.join(self.output_path, "{}.{}".format(filename, temp_extension))
                    final_filepath = os.path.join(self.output_path, "{}.{}".format(filename, final_extension))
                    filepath = temp_filepath  # 渲染时使用临时EXR路径
                else:
                    filepath = os.path.join(self.output_path, "{}.{}".format(filename, file_extension))
                
                print(f"命名模式: {self.naming_mode}")
                print(f"顶级父级名称: {top_parent_name}")
                print(f"物体名称: {objects[0].name}")
                print(f"生成的文件名: {filename}")
                print(f"输出格式: {self.output_format}")
                if is_exr_to_png_mode:
                    print(f"临时EXR路径: {temp_filepath}")
                    print(f"最终PNG路径: {final_filepath}")
                else:
                    print(f"输出路径: {filepath}")
                print(f"准备保存渲染结果到: {filepath}")

                # 设置渲染输出路径
                bpy.context.scene.render.filepath = filepath
                
                # 根据输出格式设置渲染格式
                if self.output_format in ['EXR', 'EXR_TO_PNG']:
                    if self.output_format == 'EXR_TO_PNG':
                        print("ℹ 检测到EXR→PNG模式，先渲染为EXR...")
                    else:
                        print("ℹ 检测到EXR格式，应用特殊设置...")
                    
                    # 设置EXR格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'OPEN_EXR'
                    bpy.context.scene.render.image_settings.exr_codec = 'ZIP'  # 使用ZIP压缩
                    # 检查是否有use_zbuffer属性（Blender 4.3+移除了此属性）
                    if has_use_zbuffer_attribute():
                        bpy.context.scene.render.image_settings.use_zbuffer = True  # 启用Z缓冲
                    else:
                        print("ℹ Blender 4.3+: use_zbuffer属性已移除，跳过Z缓冲设置")
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    print("✓ EXR格式设置完成")
                    
                elif self.output_format == 'TIFF':
                    print("ℹ 检测到TIFF格式，应用TIFF设置...")
                    # 设置TIFF格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'TIFF'
                    bpy.context.scene.render.image_settings.tiff_codec = 'DEFLATE'  # 使用DEFLATE压缩
                    # 检查是否有use_zbuffer属性（Blender 4.3+移除了此属性）
                    if has_use_zbuffer_attribute():
                        bpy.context.scene.render.image_settings.use_zbuffer = True  # 启用Z缓冲
                    else:
                        print("ℹ Blender 4.3+: use_zbuffer属性已移除，跳过Z缓冲设置")
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    print("✓ TIFF格式设置完成")
                    
                elif self.output_format == 'PNG':
                    print("ℹ 检测到PNG格式，应用PNG设置...")
                    # 设置PNG格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'PNG'
                    # 检查是否有use_zbuffer属性（Blender 4.3+移除了此属性）
                    if has_use_zbuffer_attribute():
                        bpy.context.scene.render.image_settings.use_zbuffer = True  # 启用Z缓冲
                    else:
                        print("ℹ Blender 4.3+: use_zbuffer属性已移除，跳过Z缓冲设置")
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    print("✓ PNG格式设置完成")
                    
                elif self.output_format == 'JPEG':
                    print("ℹ 检测到JPEG格式，应用JPEG设置...")
                    # 设置JPEG格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'JPEG'
                    bpy.context.scene.render.image_settings.quality = 95  # 设置高质量
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    print("✓ JPEG格式设置完成")
                    
                elif self.output_format == 'BMP':
                    print("ℹ 检测到BMP格式，应用BMP设置...")
                    # 设置BMP格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'BMP'
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    print("✓ BMP格式设置完成")
                    
                elif self.output_format == 'TARGA':
                    print("ℹ 检测到TGA格式，应用TGA设置...")
                    # 设置TGA格式的渲染设置
                    bpy.context.scene.render.image_settings.file_format = 'TARGA'
                    bpy.context.scene.render.image_settings.use_preview = False  # 禁用预览
                    # TGA格式强制启用透明背景以支持Alpha通道
                    bpy.context.scene.render.film_transparent = True
                    print("✓ TGA格式设置完成，已启用透明背景")
                
                # 确保渲染设置一致性
                original_render_settings = self.ensure_render_settings_consistency()
                
                # 检查合成器状态
                compositor_status = self.check_compositor_status()
                print(f"合成器状态检查结果:")
                print(f"  - 启用节点: {compositor_status['use_nodes']}")
                print(f"  - 节点树存在: {compositor_status['node_tree_exists']}")
                print(f"  - 节点树类型: {compositor_status['node_tree_type']}")
                print(f"  - 渲染合成器: {compositor_status['use_compositing']}")
                print(f"  - 合成器节点数量: {compositor_status['total_nodes']}")
                print(f"  - 合成器节点: {compositor_status['compositor_nodes']}")
                
                # 验证合成器设置
                is_valid = False
                validation_message = ""
                if self.use_compositor:
                    # 显示详细的合成器调试信息
                    self.debug_compositor_nodes()
                    
                    is_valid, validation_message = self.validate_compositor_setup()
                    print(f"合成器验证结果: {'✓' if is_valid else '⚠'} {validation_message}")
                
                # 检查是否启用了合成器渲染
                if self.use_compositor:
                    if (compositor_status['use_nodes'] and 
                        compositor_status['node_tree_exists'] and
                        compositor_status['node_tree_type'] == 'COMPOSITING' and
                        compositor_status['total_nodes'] > 0 and
                        is_valid):
                        
                        print("✓ 检测到有效的合成器节点树，使用合成器渲染以包含辉光等效果")
                        
                        # 确保合成器设置正确
                        bpy.context.scene.render.use_compositing = True
                        bpy.context.scene.render.use_sequencer = False
                        
                        # 使用合成器渲染，包含所有节点效果
                        # 注意：write_still=True 会自动保存到指定路径，不需要再次保存
                        bpy.ops.render.render(write_still=True, use_viewport=False)
                        print("✓ 合成器渲染完成，包含辉光等效果")
                        
                        # 验证渲染结果
                        if os.path.exists(filepath):
                            print(f"✓ 渲染文件已保存: {filepath}")
                            # 检查文件大小，确保不是空文件
                            file_size = os.path.getsize(filepath)
                            print(f"  - 文件大小: {file_size} 字节")
                            if file_size < 1000:
                                print("⚠ 警告: 文件大小过小，可能渲染失败")
                        else:
                            print("⚠ 警告: 渲染文件未找到")
                            
                    else:
                        print("⚠ 未检测到有效的合成器节点树，尝试强制启用...")
                        
                        # 尝试强制启用合成器
                        try:
                            self.force_enable_compositor()
                            
                            # 重新验证
                            is_valid, validation_message = self.validate_compositor_setup()
                            print(f"强制启用后验证结果: {'✓' if is_valid else '⚠'} {validation_message}")
                            
                            if is_valid:
                                print("✓ 强制启用成功，使用合成器渲染")
                                bpy.ops.render.render(write_still=True, use_viewport=False)
                                print("✓ 合成器渲染完成，包含辉光等效果")
                                
                                # 验证渲染结果
                                if os.path.exists(filepath):
                                    print(f"✓ 渲染文件已保存: {filepath}")
                                    file_size = os.path.getsize(filepath)
                                    print(f"  - 文件大小: {file_size} 字节")
                                    if file_size < 1000:
                                        print("⚠ 警告: 文件大小过小，可能渲染失败")
                                else:
                                    print("⚠ 警告: 渲染文件未找到")
                            else:
                                print("⚠ 强制启用失败，回退到标准渲染")
                                bpy.context.scene.render.use_compositing = False
                                bpy.ops.render.render(write_still=True)
                                print("✓ 标准渲染完成")
                                
                        except Exception as e:
                            print(f"⚠ 强制启用合成器时出错: {str(e)}")
                            print("回退到标准渲染")
                            bpy.context.scene.render.use_compositing = False
                            bpy.ops.render.render(write_still=True)
                            print("✓ 标准渲染完成")
                            
                else:
                    print("ℹ 用户选择不使用合成器渲染，使用标准渲染")
                    
                    # 确保合成器被禁用
                    bpy.context.scene.render.use_compositing = False
                    
                    # 标准渲染
                    bpy.ops.render.render(write_still=True)
                    print("✓ 标准渲染完成")
                
                print("渲染操作完成")
                save_msg = f"已保存: {filepath}"
                print(save_msg)
                self.report_info({'INFO'}, save_msg)
                
                # 恢复原始渲染设置
                self.restore_render_settings(original_render_settings)
                
            except Exception as e:
                error_msg = f"渲染分组 '{top_parent_name}' 失败: {str(e)}"
                print(error_msg)
                self.report_info({'ERROR'}, error_msg)
                print(f"跳过分组 '{top_parent_name}'，继续渲染其他分组...")
                # 恢复原始渲染可见性
                for other_obj, visibility in original_hide_render.items():
                    other_obj.hide_render = visibility
                continue  # 继续渲染下一个分组，而不是中断整个渲染过程
            
            # 注意：渲染结果已经通过 write_still=True 自动保存到指定路径
            # 不需要再次保存，避免覆盖合成器效果
            
            # EXR→PNG转换（如果启用）
            try:
                if self.output_format == 'EXR_TO_PNG' and os.path.exists(filepath):
                    print("🔄 开始EXR→PNG转换...")
                    if self.convert_exr_to_png(filepath):
                        print("✓ EXR→PNG转换完成")
                        # 更新文件路径为最终的PNG文件
                        filepath = filepath.replace('.exr', '.png')
                        print(f"最终输出文件: {filepath}")
                    else:
                        print("⚠ EXR→PNG转换失败，保留原始EXR文件")
                else:
                    print("ℹ EXR→PNG转换未启用，跳过")
            except Exception as e:
                warning_msg = f"EXR→PNG转换失败: {str(e)}"
                print(warning_msg)
                self.report_info({'WARNING'}, warning_msg)
                # 转换失败不影响主要功能，继续执行
                print("继续执行，忽略转换错误")
            
            # 图像尺寸调节（优先处理）
            # 添加边框并保存图像（在尺寸调节之前）
            try:
                margin_distance = bpy.context.scene.auto_render_settings.margin_distance
                print(f"添加边框，边距: {margin_distance}像素")
                
                # 检查文件格式，EXR→PNG模式现在应该已经是PNG了
                current_extension = os.path.splitext(filepath)[1].lower()
                if current_extension in ['.png', '.tga']:
                    print(f"ℹ 检测到{current_extension.upper()}格式，支持边框添加")
                    self.add_image_border(filepath, margin_distance, background_is_transparent)
                    print("边框添加成功")
                else:
                    print(f"⚠ 当前文件格式 {current_extension} 不支持边框添加，跳过")
            except Exception as e:
                warning_msg = f"添加边框失败: {str(e)}"
                print(warning_msg)
                self.report_info({'WARNING'}, warning_msg)
                # 边框添加失败不影响主要功能，继续执行
                print("继续执行，忽略边框添加错误")
            
            # 图像尺寸调节（在边框添加之后，确保最终尺寸包含边框）
            try:
                if self.enable_resize:
                    final_width = bpy.context.scene.auto_render_settings.final_width
                    final_height = bpy.context.scene.auto_render_settings.final_height
                    print(f"开始图像尺寸调节，目标最终尺寸: {final_width} x {final_height}（包含边框）")
                    
                    # 检查文件格式，EXR→PNG模式现在应该已经是PNG了
                    current_extension = os.path.splitext(filepath)[1].lower()
                    if current_extension in ['.png', '.tga']:
                        print(f"ℹ 检测到{current_extension.upper()}格式，支持图像尺寸调节")
                        if self.resize_image(filepath, final_width, final_height):
                            print("✓ 图像尺寸调节完成，最终尺寸包含边框")
                        else:
                            print("⚠ 图像尺寸调节失败")
                    else:
                        print(f"⚠ 当前文件格式 {current_extension} 不支持图像尺寸调节，跳过")
                else:
                    print("ℹ 图像尺寸调节未启用，跳过")
            except Exception as e:
                warning_msg = f"图像尺寸调节失败: {str(e)}"
                print(warning_msg)
                self.report_info({'WARNING'}, warning_msg)
                # 尺寸调节失败不影响主要功能，继续执行
                print("继续执行，忽略尺寸调节错误")

            # 恢复集合内其他物体的原始渲染可见性
            print("恢复原始渲染可见性...")
            for other_obj, visibility in original_hide_render.items():
                other_obj.hide_render = visibility
            
            print(f"完成渲染分组: {top_parent_name}")
        
        complete_msg = f"完成渲染集合: {collection_name}"
        print(f"--- {complete_msg} ---\n")
        self.report_info({'INFO'}, complete_msg)
        
        # 重置渲染状态标志
        self.is_rendering = False

    def generate_keyframes_only(self, collection_name: str):
        """仅生成关键帧，不进行渲染"""
        print(f"\n--- 开始为集合生成关键帧: {collection_name} ---")
        
        # 确保不是渲染模式
        self.is_rendering = False
        
        try:
            # 更新预期的集合参考
            self.intended_collection = bpy.data.collections[collection_name]
            print(f"获取集合 '{collection_name}' 成功，包含 {len(self.intended_collection.objects)} 个对象")
        except KeyError:
            error_msg = f"找不到集合 '{collection_name}'"
            print(f"错误: {error_msg}")
            self.report_info({'ERROR'}, error_msg)
            raise KeyError(error_msg)
        
        # 确保相机被激活
        print(f"ℹ 确保相机 '{self.cam.name}' 被激活...")
        bpy.context.scene.camera = self.cam
        print(f"✅ 相机已激活: {bpy.context.scene.camera.name}")
        
        # 对集合中的物体按顶级父物体分组
        print("按顶级父物体分组中...")
        
        # 在Blender 4.3中，需要确保集合对象列表是最新的
        # 强制刷新集合对象列表（仅在4.3+版本中可用）
        if is_blender_4_3_or_later():
            try:
                self.intended_collection.objects.update()
                print("ℹ 已刷新集合对象列表（Blender 4.3+）")
            except AttributeError:
                print("ℹ 集合对象列表刷新不可用，使用默认行为")
        else:
            print("ℹ 使用Blender 3.6兼容模式")
        
        # 获取集合中的所有对象，包括嵌套集合中的对象
        all_objects = []
        for obj in self.intended_collection.objects:
            all_objects.append(obj)
        
        # 递归获取嵌套集合中的对象
        def get_nested_objects(collection):
            nested_objects = []
            for obj in collection.objects:
                nested_objects.append(obj)
            for child_collection in collection.children:
                nested_objects.extend(get_nested_objects(child_collection))
            return nested_objects
        
        nested_objects = get_nested_objects(self.intended_collection)
        all_objects.extend(nested_objects)
        
        print(f"集合 '{collection_name}' 包含 {len(all_objects)} 个对象（包括嵌套集合）")
        
        groups = self.group_objects_by_top_parent(all_objects)
        print(f"共找到 {len(groups)} 个顶级父物体分组")
        
        if not groups:
            warning_msg = f"集合 '{collection_name}' 中没有可渲染的对象"
            print(f"警告: {warning_msg}")
            self.report_info({'WARNING'}, warning_msg)
            return
        
        # 为每个分组生成关键帧
        frame_counter = 1
        for top_parent_name, objects in groups.items():
            print(f"\n处理分组: {top_parent_name}，包含 {len(objects)} 个对象")
            
            # 检查是否有可见的物体
            visible_objects = [obj for obj in objects if obj.hide_render == False]
            if not visible_objects:
                print(f"分组 '{top_parent_name}' 中没有可见的物体，跳过")
                continue
            
            # 确定要聚焦的物体列表
            focus_objects = visible_objects
            if self.focus_only_faces:
                focus_objects = [obj for obj in visible_objects if self.has_faces(obj)]
                if not focus_objects:
                    print("警告: 没有找到有面的物体用于聚焦，跳过")
                    continue
            
            print(f"为 {len(focus_objects)} 个物体生成关键帧")
            
            # 设置当前帧
            bpy.context.scene.frame_current = frame_counter
            print(f"设置当前帧为: {frame_counter}")
            
            # 聚焦到物体并生成关键帧
            try:
                self.focus_object(focus_objects)
                print(f"✓ 已为分组 '{top_parent_name}' 生成关键帧")
                frame_counter += 1
            except Exception as e:
                error_msg = f"为分组 '{top_parent_name}' 生成关键帧时出错: {str(e)}"
                print(error_msg)
                self.report_info({'WARNING'}, error_msg)
        
        complete_msg = f"完成为集合 '{collection_name}' 生成关键帧，共 {frame_counter - 1} 帧"
        print(f"--- {complete_msg} ---\n")
        self.report_info({'INFO'}, complete_msg)
        
        # 设置场景的帧范围
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = frame_counter - 1
        print(f"已设置场景帧范围: {bpy.context.scene.frame_start} - {bpy.context.scene.frame_end}")

    def resize_image(self, image_path, target_width, target_height):
        """将图像缩放至指定尺寸"""
        # 检查PIL库是否可用
        if not check_pil_availability():
            print("PIL库不可用，跳过图像缩放功能")
            return False
            
        print(f"开始缩放图像: {image_path}")
        print(f"目标尺寸: {target_width} x {target_height}")
        
        # 检查文件格式
        file_extension = os.path.splitext(image_path)[1].lower()
        if file_extension == '.exr':
            print("⚠ 警告: EXR格式不支持PIL缩放，跳过图像尺寸调节")
            print("建议: 使用Blender内置的渲染尺寸设置或保持原始尺寸")
            return False
            
        try:
            with Image.open(image_path) as img:
                original_size = img.size
                print(f"原始尺寸: {original_size[0]} x {original_size[1]}")
                
                # 检查是否需要缩放
                if original_size[0] == target_width and original_size[1] == target_height:
                    print("图像尺寸已符合要求，无需缩放")
                    return True
                
                # 使用LANCZOS重采样进行高质量缩放
                resized_img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                print(f"缩放完成，新尺寸: {resized_img.size}")
                
                # 保存缩放后的图像
                resized_img.save(image_path, quality=95)
                print("缩放后的图像已保存")
                return True
                
        except Exception as e:
            print(f"图像缩放时发生错误: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def add_image_border(self, image_path, margin_distance, background_is_transparent):
        """在图像周围添加边框，并根据背景透明度调整边框"""
        # 如果没有设置边框距离，则跳过
        if margin_distance <= 0:
            print(f"边框距离为 {margin_distance}，跳过边框添加")
            return
            
        # 检查文件格式
        file_extension = os.path.splitext(image_path)[1].lower()
        if file_extension == '.exr':
            print("⚠ 警告: EXR格式不支持PIL边框添加，跳过边框功能")
            print("建议: 使用Blender内置的渲染边框设置或保持原始尺寸")
            return
            
        # 检查PIL库是否可用
        if not check_pil_availability():
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
        
        # 在开始自动渲染前清理相机关键帧，确保每次渲染都是独立的
        print("ℹ 开始自动渲染前清理相机关键帧...")
        try:
            if self.clear_all_camera_keyframes():
                print("✓ 相机关键帧清理完成，确保渲染独立性")
            else:
                print("⚠ 相机关键帧清理失败，但继续渲染")
        except Exception as e:
            print(f"⚠ 清理关键帧时出错: {str(e)}，但继续渲染")
        
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

    def has_faces(self, obj):
        """检查物体是否具有面"""
        if obj.type != 'MESH':
            return False
        
        # 检查是否有网格数据
        if not obj.data:
            return False
        
        # 检查是否有面
        if len(obj.data.polygons) > 0:
            return True
        
        return False
    
    def get_all_related_objects(self, top_parent_name):
        """获取顶级父物体的所有相关子物体，包括空物体的情况"""
        related_objects = []
        
        # 找到顶级父物体
        top_parent = bpy.data.objects.get(top_parent_name)
        if not top_parent:
            return related_objects
        
        # 递归获取所有子物体
        def collect_children(obj):
            children = []
            # 添加物体本身（如果不是空物体）
            if obj.type != 'EMPTY':
                # 如果启用了只聚焦有面的物体，则检查是否有面
                if self.focus_only_faces:
                    if self.has_faces(obj):
                        children.append(obj)
                else:
                    children.append(obj)
            
            # 递归添加所有子物体
            for child in obj.children:
                children.extend(collect_children(child))
            
            return children
        
        related_objects = collect_children(top_parent)
        
        # 如果顶级父物体是空物体且没有找到任何子物体，尝试包含顶级父物体本身
        if top_parent.type == 'EMPTY' and not related_objects:
            # 检查顶级父物体本身是否可见
            if not top_parent.hide_render:
                related_objects.append(top_parent)
                print(f"ℹ 顶级父物体 '{top_parent_name}' 是空物体且没有子物体，包含其本身")
        
        # 如果启用了只聚焦有面的物体，但顶级父物体是空物体且没有找到有面的子物体
        # 则至少包含顶级父物体本身，确保分组不被完全跳过
        if self.focus_only_faces and top_parent.type == 'EMPTY' and not related_objects:
            # 检查是否有任何子物体（不管是否有面）
            all_children = []
            def collect_all_children(obj):
                all_children.append(obj)
                for child in obj.children:
                    collect_all_children(child)
            
            collect_all_children(top_parent)
            # 过滤出可见的物体
            visible_children = [obj for obj in all_children if obj.hide_render == False]
            if visible_children:
                related_objects = visible_children
                print(f"⚠️ 顶级父物体 '{top_parent_name}' 是空物体，但包含可见子物体，已包含在分组中")
        
        return related_objects
    
    def check_compositor_status(self):
        """检查合成器状态，返回详细的合成器信息"""
        scene = bpy.context.scene
        
        # 检查基础设置
        use_nodes = scene.use_nodes
        node_tree = scene.node_tree
        
        # 检查渲染设置
        use_compositing = scene.render.use_compositing
        use_sequencer = scene.render.use_sequencer
        
        # 检查合成器节点树
        compositor_nodes = []
        if node_tree and node_tree.type == 'COMPOSITING':
            compositor_nodes = [node.name for node in node_tree.nodes if node.type != 'R_LAYERS']
        
        # 检查是否有输出节点
        has_output = False
        if node_tree:
            for node in node_tree.nodes:
                if node.type == 'OUTPUT_FILE' or node.type == 'COMPOSITE':
                    has_output = True
                    break
        
        status_info = {
            'use_nodes': use_nodes,
            'node_tree_exists': node_tree is not None,
            'node_tree_type': node_tree.type if node_tree else None,
            'use_compositing': use_compositing,
            'use_sequencer': use_sequencer,
            'compositor_nodes': compositor_nodes,
            'has_output': has_output,
            'total_nodes': len(compositor_nodes)
        }
        
        return status_info
    
    def ensure_render_settings_consistency(self):
        """确保渲染设置与直接渲染一致"""
        scene = bpy.context.scene
        
        # 保存原始设置
        original_settings = {
            'use_compositing': scene.render.use_compositing,
            'use_sequencer': scene.render.use_sequencer,
            'use_nodes': scene.use_nodes,
            # 保存图像设置
            'file_format': scene.render.image_settings.file_format,
            'exr_codec': scene.render.image_settings.exr_codec,
            'tiff_codec': scene.render.image_settings.tiff_codec,
            'quality': scene.render.image_settings.quality,
            'use_preview': scene.render.image_settings.use_preview
        }
        
        # 检查是否有use_zbuffer属性（Blender 4.3+移除了此属性）
        if has_use_zbuffer_attribute():
            original_settings['use_zbuffer'] = scene.render.image_settings.use_zbuffer
        
        print("保存原始渲染设置:")
        for key, value in original_settings.items():
            print(f"  - {key}: {value}")
        
        return original_settings
    
    def restore_render_settings(self, original_settings):
        """恢复原始渲染设置"""
        scene = bpy.context.scene
        
        print("恢复原始渲染设置:")
        for key, value in original_settings.items():
            if key in ['file_format', 'exr_codec', 'tiff_codec', 'quality', 'use_preview']:
                # 恢复图像设置
                setattr(scene.render.image_settings, key, value)
            elif key == 'use_zbuffer' and has_use_zbuffer_attribute():
                # 恢复use_zbuffer设置（仅在支持时）
                setattr(scene.render.image_settings, key, value)
            elif key.startswith('use_') and key != 'use_nodes':
                # 恢复渲染设置
                setattr(scene.render, key, value)
            else:
                # 恢复场景设置
                setattr(scene, key, value)
            print(f"  - {key}: {value}")
    
    def force_enable_compositor(self):
        """强制启用合成器设置"""
        scene = bpy.context.scene
        
        print("强制启用合成器设置:")
        
        # 确保场景启用节点
        if not scene.use_nodes:
            scene.use_nodes = True
            print("  - 已启用场景节点")
        
        # 确保有合成器节点树
        if not scene.node_tree or scene.node_tree.type != 'COMPOSITING':
            # 创建新的合成器节点树
            scene.node_tree = bpy.data.node_groups.new(type='COMPOSITING', name='Compositor')
            print("  - 已创建新的合成器节点树")
        
        # 强制启用渲染合成器
        scene.render.use_compositing = True
        scene.render.use_sequencer = False
        
        print("  - 已启用渲染合成器")
        print("  - 已禁用渲染序列器")
        
        return True
    
    def validate_compositor_setup(self):
        """验证合成器设置是否正确"""
        scene = bpy.context.scene
        
        if not scene.use_nodes or not scene.node_tree:
            return False, "场景未启用节点或没有节点树"
        
        if scene.node_tree.type != 'COMPOSITING':
            return False, f"节点树类型不是合成器 ({scene.node_tree.type})"
        
        # 检查是否有渲染层节点
        render_layers = [node for node in scene.node_tree.nodes if node.type == 'R_LAYERS']
        if not render_layers:
            return False, "合成器中没有渲染层节点"
        
        # 检查是否有输出节点
        output_nodes = [node for node in scene.node_tree.nodes if node.type in ['COMPOSITE', 'OUTPUT_FILE']]
        if not output_nodes:
            return False, "合成器中没有输出节点"
        
        # 检查节点连接 - 更宽松的验证
        for output_node in output_nodes:
            if not output_node.inputs:
                continue
            for input_socket in output_node.inputs:
                if input_socket.links:
                    return True, "合成器节点连接正常"
        
        # 如果没有检测到连接，但仍然有节点，也认为是有效的
        if len(scene.node_tree.nodes) > 2:  # 至少有渲染层和输出节点
            return True, "合成器节点存在，连接状态未知"
        
        return False, "合成器节点未正确连接"
    
    def debug_compositor_nodes(self):
        """调试合成器节点状态"""
        scene = bpy.context.scene
        
        print("\n=== 合成器节点调试信息 ===")
        
        if not scene.use_nodes:
            print("❌ 场景未启用节点")
            return
        
        if not scene.node_tree:
            print("❌ 场景没有节点树")
            return
        
        print(f"节点树类型: {scene.node_tree.type}")
        print(f"节点树名称: {scene.node_tree.name}")
        print(f"总节点数量: {len(scene.node_tree.nodes)}")
        
        print("\n节点列表:")
        for i, node in enumerate(scene.node_tree.nodes):
            print(f"  {i+1}. {node.name} (类型: {node.type})")
            
            # 检查输入连接
            if hasattr(node, 'inputs'):
                for j, input_socket in enumerate(node.inputs):
                    if input_socket.links:
                        from_node = input_socket.links[0].from_node
                        from_socket = input_socket.links[0].from_socket
                        print(f"    输入 {j+1}: 连接到 {from_node.name}.{from_socket.name}")
                    else:
                        print(f"    输入 {j+1}: 未连接")
        
        print("\n渲染设置:")
        print(f"  use_compositing: {scene.render.use_compositing}")
        print(f"  use_sequencer: {scene.render.use_sequencer}")
        print("=== 调试信息结束 ===\n")

    def verify_camera_position(self, target_objects):
        """验证相机位置是否正确对准目标物体"""
        try:
            print("\n=== 相机位置验证 ===")
            
            if not target_objects:
                print("⚠ 没有目标物体，无法验证相机位置")
                return False
            
            camera = self.cam
            camera_data = camera.data
            
            print(f"相机信息:")
            print(f"  - 名称: {camera.name}")
            print(f"  - 位置: {camera.location}")
            print(f"  - 旋转: {camera.rotation_euler}")
            print(f"  - 类型: {'正交相机' if camera_data.type == 'ORTHO' else '透视相机'}")
            
            if camera_data.type == 'ORTHO':
                print(f"  - 正交缩放: {camera_data.ortho_scale}")
            else:
                print(f"  - 焦距: {camera_data.lens}mm")
                print(f"  - 视野角度: {2 * math.degrees(math.atan(16 / camera_data.lens)):.2f}°")
            
            # 计算目标物体的边界框
            bbox_min, bbox_max = self._calculate_group_bbox(target_objects)
            if not bbox_min or not bbox_max:
                print("⚠ 无法计算目标物体边界框")
                return False
            
            bbox_center = [(bbox_min[i] + bbox_max[i]) / 2 for i in range(3)]
            bbox_size = [bbox_max[i] - bbox_min[i] for i in range(3)]
            
            print(f"\n目标物体信息:")
            print(f"  - 边界框中心: {bbox_center}")
            print(f"  - 边界框尺寸: {bbox_size}")
            print(f"  - 最大尺寸: {max(bbox_size):.2f}")
            
            # 计算相机到物体中心的距离
            camera_to_center = (camera.location - mathutils.Vector(bbox_center)).length
            print(f"  - 相机到物体中心距离: {camera_to_center:.2f}")
            
            # 验证相机是否能看到物体
            if camera_data.type == 'ORTHO':
                # 正交相机验证
                required_scale = max(bbox_size) * 1.1  # 增加10%安全边距
                if camera_data.ortho_scale >= required_scale:
                    print(f"✓ 正交相机视野充足: 当前缩放={camera_data.ortho_scale:.2f}, 需要={required_scale:.2f}")
                else:
                    print(f"⚠ 正交相机视野不足: 当前缩放={camera_data.ortho_scale:.2f}, 需要={required_scale:.2f}")
                    return False
            else:
                # 透视相机验证
                fov_radians = math.radians(2 * math.degrees(math.atan(16 / camera_data.lens)))
                required_distance = (max(bbox_size) / 2) / math.tan(fov_radians / 2)
                
                if camera_to_center <= required_distance * 1.5:  # 允许1.5倍的安全距离
                    print(f"✓ 透视相机距离合适: 当前={camera_to_center:.2f}, 需要={required_distance:.2f}")
                else:
                    print(f"⚠ 透视相机距离过远: 当前={camera_to_center:.2f}, 需要={required_distance:.2f}")
                    return False
            
            # 检查相机是否朝向物体
            direction_to_center = (mathutils.Vector(bbox_center) - camera.location).normalized()
            camera_forward = camera.matrix_world.to_quaternion() @ mathutils.Vector((0, 0, -1))
            
            angle = direction_to_center.angle(camera_forward)
            angle_degrees = math.degrees(angle)
            
            print(f"  - 相机朝向角度: {angle_degrees:.2f}°")
            
            if angle_degrees < 45:  # 相机朝向物体（45度以内）
                print(f"✓ 相机朝向正确，对准物体")
            else:
                print(f"⚠ 相机朝向可能不正确，角度过大: {angle_degrees:.2f}°")
                return False
            
            print("✓ 相机位置验证通过")
            return True
            
        except Exception as e:
            print(f"⚠ 相机位置验证时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


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
        bpy.ops.object.mian_queue_up()
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
    # 命名模式选择
    naming_mode: bpy.props.EnumProperty(
        name="Naming Mode",
        description="选择渲染文件的命名方式",
        items=[
            ('AUTO', '自动命名', '使用顶级父级名称'),
            ('CUSTOM', '自定义名称', '使用手动输入的名称'),
            ('HYBRID', '混合命名', '顶级父级名称 + 自定义名称'),
            ('OBJECT', '物体名称', '使用物体本身的名称')
        ],
        default='AUTO'
    ) # type: ignore
    
    output_name: bpy.props.StringProperty(
        name="Custom Name",
        description="自定义名称（仅在'自定义名称'或'混合命名'模式下使用）",
        default=""
    ) # type: ignore
    output_format: bpy.props.EnumProperty(
        name="Output Format",
        description="Image format of the rendered images",
        items=[
            ('PNG', 'PNG', 'PNG - 支持透明通道，文件较小'),
            ('JPEG', 'JPEG', 'JPEG - 压缩率高，不支持透明'),
            ('BMP', 'BMP', 'BMP - 无压缩，文件较大'),
            ('TIFF', 'TIFF', 'TIFF - 高质量，支持透明'),
            ('TARGA', 'TGA', 'TGA - 支持透明通道，无压缩，适合游戏开发'),
            ('EXR', 'EXR', 'EXR - 高动态范围，完美支持透明和32位色彩'),
            ('EXR_TO_PNG', 'EXR→PNG', 'EXR→PNG - 先渲染EXR再转换为PNG，完美解决alpha硬裁切问题')
        ]
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
    focus_only_faces: bpy.props.BoolProperty(
        name="Focus Only Objects with Faces",
        description="When enabled, only focus on objects that have faces, ignoring empty objects, points, and lines. This is useful when parent objects are empty and you want to focus on the actual visible geometry.",
        default=False
    ) # type: ignore
    use_compositor: bpy.props.BoolProperty(
        name="Use Compositor",
        description="Enable to include compositor effects (glow, color correction, etc.) in the rendered images. This will apply all nodes in the compositor including glow effects.",
        default=True
    ) # type: ignore
    auto_keyframe: bpy.props.BoolProperty(
        name="Auto Keyframe Camera",
        description="Enable to automatically keyframe the camera's position, rotation, and focal length when focusing on objects.",
        default=False
    ) # type: ignore
    
    # 图像尺寸调节
    final_width: bpy.props.IntProperty(
        name="Final Width",
        description="Final output image width in pixels. The rendered image will be scaled to this size.",
        default=1920,
        min=1,
        max=10000
    ) # type: ignore
    
    final_height: bpy.props.IntProperty(
        name="Final Height",
        description="Final output image height in pixels. The rendered image will be scaled to this size.",
        default=1080,
        min=1,
        max=10000
    ) # type: ignore
    
    enable_resize: bpy.props.BoolProperty(
        name="Enable Image Resize",
        description="Enable to resize the final output image to the specified dimensions.",
        default=False
    ) # type: ignore
    
    # 像素边距控制
    pixel_margin: bpy.props.IntProperty(
        name="像素边距",
        description="相机与物体的像素边距，相机会自动调整距离以产生指定的像素边距",
        default=0,
        min=0,
        max=1000
    ) # type: ignore
    
    # 增强透视相机聚焦功能已移除

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
        print(f"命名模式: {auto_render_settings.naming_mode}")
        print(f"自定义名称: {auto_render_settings.output_name}")
        print(f"输出格式: {auto_render_settings.output_format}")
        print(f"选中的集合: {auto_render_settings.collections}")
        print(f"选中的相机: {auto_render_settings.cameras}")
        print(f"聚焦到每个物体: {auto_render_settings.focus_each_object}")
        print(f"仅聚焦有面的物体: {auto_render_settings.focus_only_faces}")
        print(f"使用合成器: {auto_render_settings.use_compositor}")
        print(f"边框距离: {auto_render_settings.margin_distance}")
        print(f"自动关键帧: {auto_render_settings.auto_keyframe}")

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
            focus_only_faces = auto_render_settings.focus_only_faces
            use_compositor = auto_render_settings.use_compositor
            auto_keyframe = auto_render_settings.auto_keyframe

            print("创建AutoRenderer实例...")
            # 传递self.report作为回调函数
            auto_renderer = AutoRenderer([collection_name], camera_name=camera_name,
                                        output_path=output_path, output_name=output_name,
                                        output_format=output_format, naming_mode=auto_render_settings.naming_mode,
                                        focus_each_object=focus_each_object,
                                        focus_only_faces=focus_only_faces, use_compositor=use_compositor, 
                                        auto_keyframe=auto_keyframe, enable_resize=auto_render_settings.enable_resize,
                                        pixel_margin=auto_render_settings.pixel_margin,
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

# 清除相机关键帧操作器
class AUTO_RENDER_OT_ClearCameraKeyframes(bpy.types.Operator):
    """清除当前场景相机的所有关键帧"""
    bl_idname = "auto_render.clear_camera_keyframes"
    bl_label = "清除相机关键帧"
    bl_description = "清除当前场景相机的所有位置、旋转和焦距关键帧"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        auto_render_settings = scene.auto_render_settings
        
        # 获取当前场景的相机
        camera_name = auto_render_settings.cameras
        if not camera_name:
            self.report({'ERROR'}, "请先选择一个相机")
            return {'CANCELLED'}
        
        # 获取相机对象
        camera = bpy.data.objects.get(camera_name)
        if not camera or camera.type != 'CAMERA':
            self.report({'ERROR'}, f"找不到相机对象: {camera_name}")
            return {'CANCELLED'}
        
        try:
            # 创建临时AutoRenderer实例来调用清除方法
            temp_renderer = AutoRenderer([], camera_name=camera_name)
            success = temp_renderer.clear_all_camera_keyframes()
            
            if success:
                self.report({'INFO'}, f"已成功清除相机 '{camera_name}' 的所有关键帧")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, f"清除相机 '{camera_name}' 关键帧时出现问题")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"清除关键帧时出错: {str(e)}")
            return {'CANCELLED'}

# 仅生成关键帧操作器
class AUTO_RENDER_OT_GenerateKeyframesOnly(bpy.types.Operator):
    """仅生成相机关键帧，不进行渲染"""
    bl_idname = "auto_render.generate_keyframes_only"
    bl_label = "仅生成关键帧"
    bl_description = "为选中的集合生成相机关键帧动画，不进行渲染"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        scene = context.scene
        auto_render_settings = scene.auto_render_settings
        
        # 获取集合名称
        collection_name = auto_render_settings.collections
        if not collection_name:
            self.report({'ERROR'}, "请先选择一个要处理的集合")
            return {'CANCELLED'}
        
        # 获取相机名称
        camera_name = auto_render_settings.cameras
        if not camera_name:
            self.report({'ERROR'}, "请先选择一个相机")
            return {'CANCELLED'}
        
        # 检查相机是否存在
        cam = bpy.data.objects.get(camera_name)
        if not cam or cam.type != 'CAMERA':
            self.report({'ERROR'}, f"相机 '{camera_name}' 不存在或不是相机类型")
            return {'CANCELLED'}
        
        # 检查集合是否存在
        col = bpy.data.collections.get(collection_name)
        if not col:
            self.report({'ERROR'}, f"集合 '{collection_name}' 不存在")
            return {'CANCELLED'}
        
        try:
            print("=== 开始仅生成关键帧操作 ===")
            print(f"集合: {collection_name}")
            print(f"相机: {camera_name}")
            print(f"聚焦到每个物体: {auto_render_settings.focus_each_object}")
            print(f"仅聚焦有面的物体: {auto_render_settings.focus_only_faces}")
            print(f"自动关键帧: {auto_render_settings.auto_keyframe}")
            
            # 创建AutoRenderer实例
            auto_renderer = AutoRenderer([collection_name], camera_name=camera_name,
                                        focus_each_object=True,  # 强制启用聚焦
                                        focus_only_faces=auto_render_settings.focus_only_faces,
                                        auto_keyframe=True,  # 强制启用关键帧
                                        naming_mode=auto_render_settings.naming_mode,
                                        enable_resize=auto_render_settings.enable_resize,
                                        pixel_margin=auto_render_settings.pixel_margin,
                                        report_callback=self.report)
            
            # 仅生成关键帧
            auto_renderer.generate_keyframes_only(collection_name)
            
            self.report({'INFO'}, f"已成功为集合 '{collection_name}' 生成关键帧动画")
            print("=== 仅生成关键帧操作完成 ===\n")
            
            return {'FINISHED'}
            
        except Exception as e:
            error_msg = f"生成关键帧时出错: {str(e)}"
            print(f"错误: {error_msg}")
            self.report({'ERROR'}, error_msg)
            return {'CANCELLED'}

def register():
    bpy.utils.register_class(AUTO_RENDER_OT_Execute)
    bpy.utils.register_class(AUTO_RENDER_OneClick)
    bpy.utils.register_class(AUTO_RENDER_OT_ClearCameraKeyframes)
    bpy.utils.register_class(AUTO_RENDER_OT_GenerateKeyframesOnly)
    bpy.utils.register_class(AutoRenderSettings)
    bpy.types.Scene.auto_render_settings = bpy.props.PointerProperty(type=AutoRenderSettings)

def unregister():
    bpy.utils.unregister_class(AUTO_RENDER_OT_Execute)
    bpy.utils.unregister_class(AUTO_RENDER_OneClick)
    bpy.utils.unregister_class(AUTO_RENDER_OT_ClearCameraKeyframes)
    bpy.utils.unregister_class(AUTO_RENDER_OT_GenerateKeyframesOnly)
    bpy.utils.unregister_class(AutoRenderSettings)
    try:
        delattr(bpy.types.Scene, "auto_render_settings")
    except AttributeError:
        pass

if __name__ == "__main__":
    register()