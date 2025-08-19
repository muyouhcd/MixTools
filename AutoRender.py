import bpy
import mathutils
from bpy import context as C
import os
import traceback

from bpy.props import BoolProperty, EnumProperty, CollectionProperty# type: ignore

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
                    focus_only_faces=False, use_compositor=True, auto_keyframe=False, report_callback=None) -> None:
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
        self.focus_only_faces = focus_only_faces
        self.use_compositor = use_compositor
        self.auto_keyframe = auto_keyframe
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
            
            # 过滤出可见的物体
            visible_objects = [obj for obj in all_related_objects if obj.hide_render == False]
            
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
                        
                        # 自动关键帧：记录相机位置和旋转
                        print(f"检查是否需要添加关键帧: self.auto_keyframe = {self.auto_keyframe}")
                        if self.auto_keyframe:
                            print("✓ 启用自动关键帧，开始添加关键帧...")
                            self.auto_keyframe_camera()
                        else:
                            print("⚠ 自动关键帧未启用")
                        
                        break

    def auto_keyframe_camera(self):
        """自动为相机添加关键帧，记录当前位置、旋转和焦距"""
        try:
            current_frame = bpy.context.scene.frame_current
            camera = self.cam
            
            print(f"开始为相机 '{camera.name}' 添加关键帧...")
            print(f"当前帧: {current_frame}")
            print(f"相机位置: {camera.location}")
            print(f"相机旋转: {camera.rotation_euler}")
            if camera.data:
                print(f"相机焦距: {camera.data.lens}")
            
            # 为相机位置添加关键帧
            camera.keyframe_insert(data_path="location", frame=current_frame)
            print(f"✓ 位置关键帧添加成功")
            
            # 为相机旋转添加关键帧
            camera.keyframe_insert(data_path="rotation_euler", frame=current_frame)
            print(f"✓ 旋转关键帧添加成功")
            
            # 为相机焦距添加关键帧
            if camera.data:
                camera.data.keyframe_insert(data_path="lens", frame=current_frame)
                print(f"✓ 焦距关键帧添加成功")
            
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
        """清除相机的所有关键帧"""
        try:
            camera = self.cam
            if not camera:
                print("⚠ 未找到相机对象")
                return False
            
            # 清除位置关键帧
            if camera.animation_data and camera.animation_data.action:
                for fcurve in camera.animation_data.action.fcurves:
                    if fcurve.data_path == "location":
                        fcurve.keyframe_points.clear()
            
            # 清除旋转关键帧
            if camera.animation_data and camera.animation_data.action:
                for fcurve in camera.animation_data.action.fcurves:
                    if fcurve.data_path == "rotation_euler":
                        fcurve.keyframe_points.clear()
            
            # 清除焦距关键帧
            if camera.data and camera.data.animation_data and camera.data.animation_data.action:
                for fcurve in camera.data.animation_data.action.fcurves:
                    if fcurve.data_path == "lens":
                        fcurve.keyframe_points.clear()
            
            print(f"✓ 已清除相机 '{camera.name}' 的所有关键帧")
            return True
            
        except Exception as e:
            print(f"⚠ 清除关键帧时出错: {str(e)}")
            return False

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
        for top_parent_name, objects in groups.items():
            print(f"\n渲染顶级父物体分组: {top_parent_name}，包含 {len(objects)} 个对象")
            self.report_info({'INFO'}, f"正在渲染: {top_parent_name}")
            
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
                
                focus_msg = f"聚焦到对象组: {top_parent_name}，包含 {len(focus_objects)} 个物体"
                print(focus_msg)
                try:
                    self.focus_object(focus_objects)  # 聚焦到确定的物体列表
                except Exception as e:
                    error_msg = f"聚焦对象时出错: {str(e)}"
                    print(error_msg)
                    self.report_info({'WARNING'}, error_msg)
            
            # 渲染当前分组中的所有物体
            print("执行渲染操作...")
            try:
                # 文件名使用顶级父级名称，如果物体没有父物体，则使用物体本身名称
                filename = top_parent_name if top_parent_name != objects[0].name else objects[0].name
                filepath = os.path.join(self.output_path, "{}.{}".format(filename, self.output_format.lower()))
                print(f"准备保存渲染结果到: {filepath}")

                # 设置渲染输出路径
                bpy.context.scene.render.filepath = filepath
                
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
                error_msg = f"渲染操作失败: {str(e)}"
                print(error_msg)
                self.report_info({'ERROR'}, error_msg)
                raise
            
            # 注意：渲染结果已经通过 write_still=True 自动保存到指定路径
            # 不需要再次保存，避免覆盖合成器效果
            
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

    def generate_keyframes_only(self, collection_name: str):
        """仅生成关键帧，不进行渲染"""
        print(f"\n--- 开始为集合生成关键帧: {collection_name} ---")
        
        try:
            # 更新预期的集合参考
            self.intended_collection = bpy.data.collections[collection_name]
            print(f"获取集合 '{collection_name}' 成功，包含 {len(self.intended_collection.objects)} 个对象")
        except KeyError:
            error_msg = f"找不到集合 '{collection_name}'"
            print(f"错误: {error_msg}")
            self.report_info({'ERROR'}, error_msg)
            raise KeyError(error_msg)
        
        # 对集合中的物体按顶级父物体分组
        print("按顶级父物体分组中...")
        groups = self.group_objects_by_top_parent(self.intended_collection.objects)
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
            'use_nodes': scene.use_nodes
        }
        
        print("保存原始渲染设置:")
        for key, value in original_settings.items():
            print(f"  - {key}: {value}")
        
        return original_settings
    
    def restore_render_settings(self, original_settings):
        """恢复原始渲染设置"""
        scene = bpy.context.scene
        
        print("恢复原始渲染设置:")
        for key, value in original_settings.items():
            setattr(scene.render if key.startswith('use_') and key != 'use_nodes' else scene, key, value)
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
                                        output_format=output_format, focus_each_object=focus_each_object,
                                        focus_only_faces=focus_only_faces, use_compositor=use_compositor, 
                                        auto_keyframe=auto_keyframe, report_callback=self.report)
            
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