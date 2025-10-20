import bpy
from bpy.props import StringProperty, FloatProperty, BoolProperty, EnumProperty, PointerProperty, CollectionProperty
from bpy.types import Panel, PropertyGroup
from .MaterialOperator import SetEmissionStrength, SetMaterialRoughness, ReplaceMaterialOperator, ReplaceMaterialByKeywordOperator
from .renderconfig import BATCH_RESOLUTION_OT_ExecuteButton

# 材质属性组
class MaterialPropertyGroup(PropertyGroup):
    material: PointerProperty(
        type=bpy.types.Material,
        name="材质"
    )

class CustomFunctionsPanel(Panel):
    bl_label = "工具箱"
    bl_idname = "VIEW3D_PT_custom_functions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "工具箱"
    
    # 类变量用于缓存PIL检查结果
    _pil_available = None
    _pil_checked = False
    
    @classmethod
    def _check_pil_dependency(cls):
        """检查PIL依赖是否可用，只检查一次并缓存结果"""
        if not cls._pil_checked:
            try:
                # 尝试导入PIL模块
                import PIL
                # 进一步验证PIL功能是否可用
                from PIL import Image, ImageOps
                cls._pil_available = True
                print(f"✅ PIL依赖检查通过 (版本: {PIL.__version__})")
            except ImportError as e:
                cls._pil_available = False
                print(f"❌ PIL依赖检查失败: {e}")
            except Exception as e:
                cls._pil_available = False
                print(f"⚠️ PIL依赖检查异常: {e}")
            cls._pil_checked = True
        return cls._pil_available

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # 检查PIL依赖是否可用 - 全局缓存版本，只检查一次
        can_load_safely = self._check_pil_dependency()
        
        # 编辑工具
        col_edit_tools = layout.column()
        col_edit_tools.prop(scene, "edit_tools_expand", text="编辑工具", emboss=False,
                           icon='TRIA_DOWN' if context.scene.edit_tools_expand else 'TRIA_RIGHT')
        if scene.edit_tools_expand:
            # 基础编辑工具
            edit_box = col_edit_tools.box()
            edit_box.label(text="基础编辑工具:", icon='TOOL_SETTINGS')
            edit_box.operator("object.remove_modifiers", text="移除修改器", icon='MODIFIER')
            edit_box.operator("object.remove_constraints", text="移除约束", icon='CONSTRAINT')
            edit_box.operator("object.make_single_user_operator", text="批量独立化物体", icon='UNLINKED')
            edit_box.operator("object.mian_correct_rotation", text="矫正旋转", icon='CON_ROTLIMIT')
            
            # 合并工具
            merge_box = col_edit_tools.box()
            merge_box.label(text="合并工具:", icon='SNAP_MIDPOINT')
            merge_box.operator("object.combin_same_origin_object", text="合并同原点物体", icon='PIVOT_BOUNDBOX')

        # 清理简化工具
        col_clean_tools = layout.column()
        col_clean_tools.prop(scene, "clean_tools_expand", text="清理简化工具", emboss=False,
                            icon='TRIA_DOWN' if context.scene.clean_tools_expand else 'TRIA_RIGHT')
        if scene.clean_tools_expand:
            # 基础清理工具
            clean_box = col_clean_tools.box()
            clean_box.label(text="基础清理工具:", icon='BRUSH_DATA')
            clean_box.operator("object.mian_clean_collection", text="清空空集合", icon='OUTLINER_COLLECTION')
            clean_box.operator("object.clean_empty", text="清除无子集空物体", icon='OUTLINER_OB_EMPTY')
            clean_box.operator("object.clean_empty_recursive", text="自动递归清理", icon='PARTICLEMODE')
            
            # 空物体显示尺寸设置
            empty_size_row = clean_box.row(align=True)
            empty_size_row.prop(context.scene, "empty_display_size", text="空物体显示尺寸")
            empty_size_row.operator("object.set_empty_display_size", text="应用", icon='EMPTY_DATA')
            
            clean_box.operator("object.clear_animation_data", text="批量清空动画", icon='ANIM_DATA')
            clean_box.operator("object.clean_meshes_without_faces", text="清理无实体物体", icon='MESH_DATA')
            clean_box.operator("object.uv_cleaner", text="清理UV非法数据", icon='UV')
            clean_box.operator("image.remove_broken", text="清理丢失图像", icon='IMAGE_DATA')
            
            # 顶点组清理工具
            vertex_group_clean_box = clean_box.box()
            vertex_group_clean_box.label(text="顶点组清理:", icon='GROUP_VERTEX')
            vertex_group_clean_box.operator("object.mian_remove_vertex_group", text="移除所有顶点组", icon='GROUP_VERTEX')
            vertex_group_clean_box.operator("object.mian_remove_empty_vertex_groups", text="移除空顶点组", icon='GROUP_VERTEX')
            
            # 场景简化工具
            scene_clean_box = col_clean_tools.box()
            scene_clean_box.label(text="场景简化工具:", icon='VIEW_CAMERA')
            scene_clean_box.operator("object.auto_hide_clean", text="将相机拍不到的物体放入集合并隐藏", icon='HIDE_OFF')
            scene_clean_box.operator("object.auto_hide_delete", text="直接删除不可见物体", icon='TRASH')
            
            # 实例化工具
            instance_box = col_clean_tools.box()
            instance_box.label(text="实例化工具:", icon='DUPLICATE')
            instance_box.operator("object.object_instance", text="对所选物体进行转换实例化", icon='DUPLICATE')
            instance_box.operator("object.geometry_matcher", text="对全场景进行几何相同性检测并实例化", icon='MESH_DATA')
            instance_box.operator("object.remove_instance_duplicates", text="删除实例化物体重复项", icon='TRASH')

        # 生成工具
        col_gen_tools = layout.column()
        col_gen_tools.prop(scene, "gen_tools_expand", text="生成工具", emboss=False,
                          icon='TRIA_DOWN' if context.scene.gen_tools_expand else 'TRIA_RIGHT')
        if scene.gen_tools_expand:
            # 基础生成工具
            gen_box = col_gen_tools.box()
            gen_box.label(text="基础生成工具:", icon='SHADERFX')
            gen_box.operator("object.mian_boundbox_gen", text="生成包围盒", icon='CUBE')
            gen_box.operator("object.convex_hull_creator", text="生成凸包", icon='META_CUBE')
            gen_box.operator("object.mian_safecombin", text="安全合并", icon='AUTOMERGE_ON')
            
            # 批量顶点组工具
            vertex_group_box = col_gen_tools.box()
            vertex_group_box.label(text="批量顶点组工具:", icon='GROUP_VERTEX')
            vertex_group_row = vertex_group_box.row(align=True)
            vertex_group_row.prop(scene, "vertex_group_name", text="顶点组名称")
            vertex_group_row.operator("object.batch_create_vertex_group", text="创建顶点组", icon='ADD')


        # 选择工具
        col_select_tools = layout.column()
        col_select_tools.prop(scene, "select_tools_expand", text="选择工具", emboss=False,
                             icon='TRIA_DOWN' if context.scene.select_tools_expand else 'TRIA_RIGHT')
        if scene.select_tools_expand:
            # 基础选择工具
            select_box = col_select_tools.box()
            select_box.label(text="基础选择工具:", icon='RESTRICT_SELECT_OFF')
            select_box.operator("object.match_uv", text="选取同UV物体", icon='GROUP_UVS')
            select_box.operator("object.select_large_objects", text="选择过大物体", icon='FULLSCREEN_ENTER')
            select_box.operator("object.select_small_objects", text="选择过小物体", icon='FULLSCREEN_EXIT')
            select_box.operator("object.select_objects_without_texture", text="选择没有贴图物体", icon='TEXTURE')
            select_box.operator("object.select_objects_without_vertex_groups", text="选择没有顶点组物体", icon='GROUP_VERTEX')
            
            # 按名称列表筛选工具
            namelist_select_box = col_select_tools.box()
            namelist_select_box.label(text="按名称列表筛选:", icon='OUTLINER_OB_GROUP_INSTANCE')
            namelist_select_box.label(text="要保留的物体名称列表:", icon='TEXT')
            
            # 使用简单的输入框显示当前内容
            box_text = namelist_select_box.box()
            if scene.object_names_list:
                lines = scene.object_names_list.split('\n')
                if len(lines) > 5:  # 如果超过5行，只显示前5行和计数
                    for line in lines[:5]:
                        box_text.label(text=line)
                    box_text.label(text=f"... 共{len(lines)}行")
                else:
                    for line in lines:
                        box_text.label(text=line)
            else:
                box_text.label(text="(空)")
            
            # 添加编辑按钮
            edit_row = namelist_select_box.row(align=True)
            edit_row.operator("object.edit_names_list", text="在外部编辑器中编辑列表", icon='TEXT')
            if scene.temp_names_file_path:
                edit_row.operator("object.read_names_from_temp_file", text="加载已编辑的列表", icon='IMPORT')
            
            # 添加提示
            namelist_select_box.label(text="(编辑后保存文件，然后点击'加载已编辑的列表')")
            
            row = namelist_select_box.row()
            row.prop(scene, "delete_lights_option", text="删除所有灯光")
            row.prop(scene, "show_report_option", text="显示报告")
            namelist_select_box.operator("object.select_and_delete_by_name_list", text="按名称列表筛选物体", icon='TRASH')

            
# 绑定操作
        col_BindOperation = layout.column()
        col_BindOperation.prop(scene, "BindOperation_expand", text="关联与绑定工具", emboss=False,
                               icon='TRIA_DOWN' if context.scene.BindOperation_expand else 'TRIA_RIGHT')
        if context.scene.BindOperation_expand:
            # 碰撞检测与集合绑定
            collision_box = col_BindOperation.box()
            collision_box.label(text="碰撞检测与集合绑定:", icon='MOD_BOOLEAN')
            row1 = collision_box.row(align=True)
            row1.operator("object.mian_collection_byboundingbox", text="检测碰撞归集合", icon='SNAP_VOLUME')
            row1.operator("object.mian_parent_byboundingbox", text="检测碰撞归子集", icon='SNAP_FACE')
            collision_box.operator("object.collection_by_attached", text="检测并合并碰撞", icon='FACE_MAPS')
            
            # 集合父级设置
            parent_box = col_BindOperation.box()
            parent_box.label(text="集合父级设置:", icon='GROUP')
            parent_box.label(text="以集合物体绑定子集合父级", icon='INFO')
            parent_box.prop(scene, "collectionA", text="父级集合", icon='COLLECTION_COLOR_01')
            parent_box.prop(scene, "collectionB", text="子级集合", icon='COLLECTION_COLOR_04')
            parent_box.operator("object.mian_set_parent_collections", text="设置父级关系", icon='LINKED')

            # 空物体父级绑定
            empty_box = col_BindOperation.box()
            empty_box.label(text="空物体父级绑定:", icon='EMPTY_DATA')
            empty_box.prop(scene, "multiple_object_binding", text="为多个物体创建共同父级")
            empty_box.operator("object.mian_create_empty_at_bottom", text="创建空物体父级", icon='EMPTY_ARROWS')

# 材质操作
        col_meterialoperation = layout.column()
        col_meterialoperation.prop(scene, "meterialoperation_expand", text="材质与纹理工具", emboss=False,
                                   icon='TRIA_DOWN' if context.scene.meterialoperation_expand else 'TRIA_RIGHT')

        if context.scene.meterialoperation_expand:
            # UV操作
            uv_box = col_meterialoperation.box()
            uv_box.label(text="UV操作:", icon='MOD_UVPROJECT')
            row = uv_box.row(align=True)
            row.operator("object.uv_formater", text="UV尺寸校准", icon='UV_DATA')
            row.operator("object.correct_uv_rotation", text="UV旋转矫正", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            uv_box.operator("object.quad_uv_aligner", text="UV铺满展开", icon='FULLSCREEN_ENTER')

            # 材质强度调整
            emission_box = col_meterialoperation.box()
            emission_box.label(text="材质强度调整:", icon='MATERIAL')
            row = emission_box.row()
            row.prop(context.scene, "emission_strength", text="发光强度", slider=True)
            row.operator(SetEmissionStrength.bl_idname, text="应用", icon='CHECKMARK').strength = context.scene.emission_strength
            
            row = emission_box.row()
            row.prop(context.scene, "roughness_strength", text="粗糙强度", slider=True)
            row.operator(SetMaterialRoughness.bl_idname, text="应用", icon='CHECKMARK').roughness = context.scene.roughness_strength

            row = emission_box.row()
            row.prop(context.scene, "metallic_strength", text="金属强度", slider=True)
            row.operator("object.set_metallic", text="应用", icon='CHECKMARK').metallic = context.scene.metallic_strength

            row = emission_box.row()
            row.prop(context.scene, "specular_strength", text="高光强度", slider=True)
            row.operator("object.set_specular", text="应用", icon='CHECKMARK').specular = context.scene.specular_strength

            row = emission_box.row()
            row.prop(context.scene, "specular_tint_strength", text="光泽度", slider=True)
            row.operator("object.set_specular_tint", text="应用", icon='CHECKMARK').specular_tint = context.scene.specular_tint_strength

            # 材质节点操作
            material_operations_box = col_meterialoperation.box()
            material_operations_box.label(text="材质节点操作:", icon='NODETREE')
            
            row1 = material_operations_box.row(align=True)
            row1.operator("object.alpha_node_connector", text="连接Alpha", icon='NODE_COMPOSITING')
            row1.operator("object.alpha_node_disconnector", text="断开Alpha", icon='TRACKING_REFINE_BACKWARDS')
            
            row2 = material_operations_box.row(align=True)
            row2.operator("object.alpha_to_skin", text="Alpha设为肤色", icon='OUTLINER_OB_ARMATURE')
            row2.operator("object.set_texture_interpolation", text="硬边缘采样", icon='SNAP_INCREMENT')
            
            row3 = material_operations_box.row(align=True)
            row3.operator("object.set_material_alpha_clip", text="设置Alpha裁剪模式", icon='CLIPUV_HLT')
            row3.operator("object.set_material_alpha_blend", text="设置Alpha混合模式", icon='SNAP_VOLUME')
            
            row3_5 = material_operations_box.row(align=True)
            row3_5.operator("object.set_material_opaque", text="设置Opaque模式", icon='MATERIAL')
            
            row4 = material_operations_box.row(align=True)
            row4.operator("object.set_shadow_invisible", text="设置选中物体阴影不可见", icon='GHOST_ENABLED')
            row4.operator("object.set_shadow_visible", text="设置选中物体阴影可见", icon='GHOST_DISABLED')

            row5 = material_operations_box.row(align=True)
            row5.operator("object.set_texture_alpha_packing", text="设置Alpha通道打包", icon='PACKAGE')

            # 贴图自动链接
            texture_operater_box = col_meterialoperation.box()
            texture_operater_box.label(text="贴图自动链接", icon='TEXTURE')
            
            col = texture_operater_box.column()
            col.prop(context.scene, "texture_dir", text="贴图路径", icon='FILE_FOLDER')
            col.prop(scene, "ignore_fields_input", text="忽略字段列表", icon='FILE_TEXT')
            
            # 匹配方法子框
            matching_methods_box = texture_operater_box.box()
            matching_methods_box.label(text="纹理匹配方法:", icon='IMGDISPLAY')
            
            # 基础匹配方法
            basic_matching_box = matching_methods_box.box()
            basic_matching_box.label(text="基础匹配:", icon='OBJECT_DATA')
            col = basic_matching_box.column(align=True)
            col.operator("object.apply_texture_operator", 
                       text="按物体名称匹配(完整)", 
                       icon='OBJECT_DATA')
            col.operator("object.apply_texture_to_selected_objects", 
                       text="按物体名称匹配(忽略字段)", 
                       icon='TOOL_SETTINGS')
            col.operator("object.apply_texture_to_materials", 
                       text="按材质名称匹配", 
                       icon='MATERIAL')
            col.operator("object.apply_texture_by_parent", 
                       text="按顶级父级名称匹配", 
                       icon='OUTLINER_OB_EMPTY')

            # 智能匹配方法
            smart_matching_box = matching_methods_box.box()
            smart_matching_box.label(text="智能匹配:", icon='AUTOMERGE_ON')
            col = smart_matching_box.column(align=True)
            col.operator("object.apply_texture_by_object_name",
                       text="按物体名称包含匹配",
                       icon='TEXTURE')
            col.operator("object.apply_texture_by_similarity",
                       text="按相似度匹配",
                       icon='SORTALPHA')
           
            # 材质管理
            material_manager_box = col_meterialoperation.box()
            material_manager_box.label(text="材质管理:", icon='MATERIAL_DATA')
            
            row1 = material_manager_box.row(align=True)
            row1.operator("object.mian_material_sort", text="材质球排序", icon='SORTSIZE')
            row1.operator("scene.random_meterial", text="随机材质", icon='NODE_TEXTURE')
            
            row2 = material_manager_box.row(align=True)
            row2.operator("object.mian_merge_material", text="清除材质", icon='TRASH')
            row2.operator("object.remove_unused_material_slots", text="清理空材质槽", icon='PANEL_CLOSE')
            
            row3 = material_manager_box.row(align=True)
            row3.operator("object.material_cleaner", text="合并重复材质(.00x后缀)", icon='DUPLICATE')
            row3.operator("object.merge_duplicate_materials", text="合并同名及相同参数材质", icon='MATERIAL')
            
            row4 = material_manager_box.row(align=True)
            row4.operator("object.clean_unused_materials", text="清理未使用材质及插槽", icon='X')
            
            # 材质替换功能
            material_replace_box = col_meterialoperation.box()
            material_replace_box.label(text="材质替换:", icon='MATERIAL')
            
            # 基于关键字的材质替换
            keyword_replace_box = material_replace_box.box()
            keyword_replace_box.label(text="按关键字替换:", icon='VIEWZOOM')
            
            # 添加关键字和目标材质名称的输入框
            keyword_replace_box.prop(context.scene, "keyword_search", text="搜索关键字")
            keyword_replace_box.prop(context.scene, "keyword_target_material", text="目标材质")
            
            # 执行替换按钮
            keyword_replace_box.operator("object.replace_material_by_keyword", text="执行关键字替换", icon='MATERIAL')
            
            # 材质拆分功能
            material_split_box = material_replace_box.box()
            material_split_box.label(text="材质拆分:", icon='MOD_BOOLEAN')
            material_split_box.prop(context.scene, "split_material", text="拆分材质")
            material_split_box.operator("object.split_mesh_by_material", text="按材质拆分Mesh", icon='MOD_BOOLEAN')
            
            # 传统材质替换
            traditional_replace_box = material_replace_box.box()
            traditional_replace_box.label(text="传统材质替换:", icon='MATERIAL')
            
            # 添加和清空按钮放在顶部
            row = traditional_replace_box.row(align=True)
            row.operator("object.add_source_material", text="添加源材质", icon='ADD')
            row.operator("object.clear_source_materials", text="清空列表", icon='TRASH')
            
            # 源材质列表
            traditional_replace_box.label(text="源材质列表:")
            for i, item in enumerate(context.scene.source_materials):
                row = traditional_replace_box.row(align=True)
                row.prop(item, "material", text="")
                row.operator("object.remove_source_material", text="", icon='X').index = i
            
            # 目标材质选择
            traditional_replace_box.prop(context.scene, "target_material", text="目标材质")
            
            # 执行替换按钮
            traditional_replace_box.operator("object.replace_material", text="执行材质替换", icon='MATERIAL')

# 命名操作
        col_renameoperation = layout.column()
        col_renameoperation.prop(scene, "renameoperation_expand", text="重命名与命名管理", emboss=False,
                                 icon='TRIA_DOWN' if context.scene.renameoperation_expand else 'TRIA_RIGHT')

        if context.scene.renameoperation_expand:
            # 车辆部件命名
            box_auto_rename_car = col_renameoperation.box()
            box_auto_rename_car.label(text="车辆部件自动重命名:", icon='AUTO')
            row = box_auto_rename_car.row(align=True)
            row.operator("object.mian_auto_rename_car", text="Unity车辆命名", icon='EVENT_U')
            row.operator("object.mian_auto_rename_car_for_rigcar", text="RigCar命名", icon='EVENT_R')

            # 层级与集合命名
            spatial_rename_box = col_renameoperation.box()
            spatial_rename_box.label(text="层级与集合命名:", icon='OUTLINER')
            row = spatial_rename_box.row(align=True)
            row.operator("object.mian_rename_by_parent", text="子级命名为顶级", icon='OUTLINER_OB_EMPTY')
            row.operator("object.rename_to_collection", text="命名为所处集合", icon='GROUP')

            # 后缀管理
            remove_suffix_box = col_renameoperation.box()
            remove_suffix_box.label(text="名称后缀管理:", icon='SORTALPHA')
            row = remove_suffix_box.row(align=True)
            row.operator("object.mian_remove_name_suffix", text="移除后缀", icon='X')
            row.operator("object.remove_suffix_and_resolve", text="移除后缀并解决重名", icon='DECORATE_KEYFRAME')
            row = remove_suffix_box.row(align=True)
            row.operator("object.remove_top_level_suffix", text="移除顶级父级.00n后缀", icon='OUTLINER_OB_EMPTY')
            
            # 数据命名同步
            naming_convention_box = col_renameoperation.box()
            naming_convention_box.label(text="数据命名同步:", icon='COMMUNITY')
            row = naming_convention_box.row(align=True)
            row.operator("object.rename_meshes", text="Mesh命名为物体", icon='OUTLINER_DATA_MESH')
            row.operator("object.rename_objects", text="物体命名为Mesh", icon='OBJECT_DATA')

            # 贴图改名
            texture_rename_box = col_renameoperation.box()
            texture_rename_box.label(text="贴图重命名:", icon='IMAGE_DATA')
            texture_rename_box.operator("object.rename_texture_orign", text="贴图改名为原始名称", icon='FILE_REFRESH')

            # 按位置重命名
            position_rename_box = col_renameoperation.box()
            position_rename_box.label(text="按位置重命名:", icon='SNAP_GRID')
            
            # 集合内位置重命名
            box_rename_by_collections = position_rename_box.box()
            box_rename_by_collections.label(text="集合内位置重命名:")
            box_rename_by_collections.prop(context.scene, "collectionA", text="集合 A")
            box_rename_by_collections.prop(context.scene, "collectionB", text="集合 B")
            box_rename_by_collections.operator("object.mian_rename_collections", text="按位置重命名集合", icon='COLLECTION_NEW')
            
            # 空间顺序重命名
            box_rename_by_location = position_rename_box.box()
            box_rename_by_location.label(text="空间顺序重命名:")
            row = box_rename_by_location.row(align=True)
            row.prop(context.scene, "rename_axis", text="轴向")
            row.prop(context.scene, "rename_order", text="排序类型")
            box_rename_by_location.operator("object.mian_rename_location", text="按空间顺序重命名", icon='SORTSIZE')

# 旋转缩放位移操作
        col_rsm = layout.column()
        col_rsm.prop(scene, "rsm_expand", text="变换工具", emboss=False,
                     icon='TRIA_DOWN' if context.scene.rsm_expand else 'TRIA_RIGHT')
        if context.scene.rsm_expand:
            # 对齐工具
            align_box = col_rsm.box()
            align_box.label(text="对齐工具:", icon='ORIENTATION_GLOBAL')
            align_box.prop(context.scene, "axis_direction_enum", text="轴向选择")
            op = align_box.operator("object.move_origin", text="移动原点")
            op.axis_direction = context.scene.axis_direction_enum
            align_box.operator("object.reset_z_axis", text="Z轴归零", icon='AXIS_TOP')
            align_box.operator("object.align_object_origin", text="对齐物体原点", icon='PIVOT_CURSOR')
            
            # 下落至表面
            surface_box = col_rsm.box()
            surface_box.label(text="放置与对齐:", icon='SNAP_FACE')
            surface_box.operator("object.move_to_surface", text="下落至表面", icon='ORIENTATION_NORMAL')
            
            # 列队工具
            queue_up_box = col_rsm.box()
            queue_up_box.label(text="列队排列:", icon='OUTLINER_OB_POINTCLOUD')
            
            col = queue_up_box.column()
            row = col.row()
            row.prop(context.scene, "queue_up_distance", text="间距")
            row.prop(context.scene, "queue_up_axis", text="轴向")
            
            col.prop(context.scene, "use_bounding_box", text="使用包围盒")
            col.operator("object.mian_queue_up", text="执行列队排列", icon='MOD_ARRAY')
            
            # 随机放置工具
            random_box = col_rsm.box()
            random_box.label(text="随机变换:", icon='MOD_NOISE')
            
            # 随机位置
            random_placement_box = random_box.box()
            random_placement_box.label(text="随机位置:", icon='DRIVER_TRANSFORM')
            random_placement_box.prop(context.scene, "random_placement_extent", text="随机范围")
            random_placement_box.operator("object.mian_random_placement", text="随机分布位置", icon='STICKY_UVS_DISABLE')
            
            # 随机缩放
            random_scale_box = random_box.box()
            random_scale_box.label(text="随机缩放:", icon='FULLSCREEN_ENTER')
            col = random_scale_box.column(align=True)
            col.prop(context.scene, "random_scale_extent_x", text="X轴范围")
            col.prop(context.scene, "random_scale_extent_y", text="Y轴范围")
            col.prop(context.scene, "random_scale_extent_z", text="Z轴范围")
            random_scale_box.operator("object.mian_random_scale", text="应用随机缩放", icon='ARROW_LEFTRIGHT')
            
            # 随机旋转
            random_rotation_box = random_box.box()
            random_rotation_box.label(text="随机旋转:", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            col = random_rotation_box.column(align=True)
            col.prop(context.scene, "random_rotation_extent_x", text="X轴范围(度)")
            col.prop(context.scene, "random_rotation_extent_y", text="Y轴范围(度)")
            col.prop(context.scene, "random_rotation_extent_z", text="Z轴范围(度)")
            random_rotation_box.operator("object.mian_random_rotation", text="应用随机旋转", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            
            # 对齐集合顶级父级
            align_parent_box = col_rsm.box()
            align_parent_box.label(text="集合对齐:", icon='CON_TRACKTO')
            col = align_parent_box.column()
            col.prop(context.scene, "collectionA", text="参考集合", icon='COLLECTION_COLOR_01')
            col.prop(context.scene, "collectionB", text="目标集合", icon='COLLECTION_COLOR_02')
            align_parent_box.operator("object.align_operator", text="批量对齐顶级父物体", icon='SNAP_ON')

# 灯光工具
        col_light_tools = layout.column()
        col_light_tools.prop(scene, "light_tools_expand", text="灯光工具", emboss=False,
                          icon='TRIA_DOWN' if context.scene.light_tools_expand else 'TRIA_RIGHT')
        
        if scene.light_tools_expand:
            # 灯光关联工具
            light_tools_box = col_light_tools.box()
            light_tools_box.label(text="灯光关联工具:", icon='LIGHT')
            
            # 容差设置
            light_tools_box.prop(context.scene, "light_linking_tolerance", text="相似度容差")
            
            # 关联灯光按钮
            op = light_tools_box.operator("object.link_similar_lights", text="关联相似灯光", icon='LINKED')
            op.tolerance = context.scene.light_linking_tolerance
            
            # 灯光强度调整工具
            intensity_box = col_light_tools.box()
            intensity_box.label(text="灯光强度调整:", icon='LIGHT')
            
            # 强度倍数设置
            intensity_row = intensity_box.row(align=True)
            intensity_row.prop(context.scene, "light_intensity_multiplier", text="强度倍数", slider=True)
            
            # 两个操作按钮
            button_row = intensity_box.row(align=True)
            op1 = button_row.operator("object.adjust_light_intensity", text="设置为", icon='CHECKMARK')
            op1.intensity_multiplier = context.scene.light_intensity_multiplier
            
            op2 = button_row.operator("object.multiply_light_intensity", text="乘以", icon='MODIFIER')
            op2.intensity_multiplier = context.scene.light_intensity_multiplier
            

# 动画处理工具
        col_animation = layout.column()
        col_animation.prop(scene, "animation_tools_expand", text="动画工具", emboss=False,
                          icon='TRIA_DOWN' if context.scene.animation_tools_expand else 'TRIA_RIGHT')
        
        if scene.animation_tools_expand:

            


            # 动画清理工具
            animation_tools_box = col_animation.box()
            animation_tools_box.label(text="动画清理工具:", icon='ANIM_DATA')
            
            row1 = animation_tools_box.row(align=True)
            row1.operator("animation.clear_scale_animation", text="清除缩放动画", icon='FULLSCREEN_ENTER')
            row1.operator("animation.clear_location_animation", text="清除位移动画", icon='ANCHOR_TOP')
            
            row2 = animation_tools_box.row(align=True)
            row2.operator("animation.clear_rotation_animation", text="清除旋转动画", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            row2.operator("animation.clear_all_animation", text="清除所有动画", icon='CANCEL')
            
            # 移除重复帧工具
            duplicate_frames_box = animation_tools_box.box()
            duplicate_frames_box.label(text="移除重复帧:", icon='KEYFRAME_HLT')
            
            # 检测模式选择
            duplicate_frames_box.prop(context.scene, "duplicate_frames_detection_mode", text="检测模式")
            
            # 检测阈值设置
            threshold_row = duplicate_frames_box.row(align=True)
            threshold_row.prop(context.scene, "duplicate_frames_threshold", text="检测阈值")
            
            # 执行按钮
            duplicate_frames_box.operator("animation.remove_duplicate_frames", text="移除重复帧", icon='KEYFRAME_HLT')
            
            # 动画修改器工具
            animation_modifier_box = col_animation.box()
            animation_modifier_box.label(text="动画修改器工具:", icon='MODIFIER')
            
            row1 = animation_modifier_box.row(align=True)
            row1.operator("animation.paste_modifiers", text="添加循环修改器(带偏移)", icon='PASTEDOWN')
            row1.operator("animation.add_cycle_modifier_no_offset", text="添加循环修改器(无偏移)", icon='PASTEDOWN')
            
            row2 = animation_modifier_box.row(align=True)
            row2.operator("animation.remove_all_modifiers", text="移除所有修改器", icon='X')
            
            # 约束工具
            constraint_tools_box = col_animation.box()
            constraint_tools_box.label(text="约束工具:", icon='CONSTRAINT')
            
            # 添加跟随曲线约束工具
            follow_path_box = constraint_tools_box.box()
            follow_path_box.label(text="跟随曲线约束:", icon='CURVE_DATA')
            
            # 添加曲线闭合选项
            follow_path_box.prop(context.scene, "curve_closed_option", text="创建闭合曲线", icon='CURVE_DATA')
            
            follow_path_box.operator("animation.add_follow_path_constraint", text="添加跟随曲线约束", icon='CONSTRAINT')
            
            # 动画随机偏移工具
            random_offset_box = col_animation.box()
            random_offset_box.label(text="动画随机偏移工具:", icon='MOD_NOISE')
            
            # 执行按钮
            random_offset_box.operator("animation.random_offset_animation", text="随机偏移动画", icon='MOD_NOISE')
            
            # 骨架操作工具
            armature_tools_box = col_animation.box()
            armature_tools_box.label(text="骨架操作工具:", icon='ARMATURE_DATA')
            
            # 添加骨架位置设置工具
            armature_position_box = armature_tools_box.box()
            armature_position_box.label(text="骨架位置设置:", icon='ARMATURE_DATA')
            row = armature_position_box.row(align=True)
            row.operator("armature.set_to_rest_position", text="设置为静止位置", icon='ARMATURE_DATA')
            row.operator("armature.set_to_pose_position", text="设置为姿态位置", icon='POSE_HLT')
            
            # 添加空物体转骨骼工具
            empty_to_bone_box = armature_tools_box.box()
            empty_to_bone_box.label(text="空物体转骨骼:", icon='EMPTY_DATA')
            empty_to_bone_box.operator("object.convert_empties_to_bones", text="转换空物体为骨骼", icon='ARMATURE_DATA')
            
            # 添加骨骼参数复制面板
            bone_params_box = armature_tools_box.box()
            bone_params_box.label(text="骨骼参数复制:", icon='ARMATURE_DATA')
            
            # 源骨架和目标骨架选择
            bone_params_box.prop(context.scene, "source_armature", text="源骨架")
            bone_params_box.prop(context.scene, "target_armature", text="目标骨架")
            
            # 执行按钮
            bone_params_box.operator("object.copy_bone_parameters", text="复制骨骼参数", icon='ARMATURE_DATA')

# 曲线工具
        col_curve_tools = layout.column()
        col_curve_tools.prop(scene, "curve_tools_expand", text="曲线工具", emboss=False,
                            icon='TRIA_DOWN' if context.scene.curve_tools_expand else 'TRIA_RIGHT')
        
        if scene.curve_tools_expand:
            # 曲线编辑工具
            curve_tools_box = col_curve_tools.box()
            curve_tools_box.label(text="曲线编辑工具:", icon='CURVE_DATA')
            
            curve_tools_box.operator("object.simplify_curve_to_endpoints", text="曲线精简到端点", icon='IPO_LINEAR')


# 导入导出操作
        col_inout = layout.column()
        col_inout.prop(scene, "inout_expand", text="导入导出工具", emboss=False,
                       icon='TRIA_DOWN' if context.scene.inout_expand else 'TRIA_RIGHT')

        if context.scene.inout_expand:
            # 批量导入
            import_box = col_inout.box()
            import_box.label(text="批量导入:", icon='IMPORT')
            import_box.operator("operation.batch_import_fbx", text="批量导入FBX（原生）", icon='FILE_3D')
            import_box.operator("operation.batch_import_obj", text="批量导入OBJ（原生）", icon='FILE_3D')
            
            # Better FBX导入
            better_fbx_box = import_box.box()
            better_fbx_box.label(text="Better FBX导入:", icon='ARMATURE_DATA')
            better_fbx_box.prop(context.scene, "better_fbx_import_directory", text="3D文件目录", icon='FILE_FOLDER')
            
            # 添加格式选择
            format_row = better_fbx_box.row(align=True)
            format_row.prop(context.scene, "batch_import_file_format", text="文件格式", icon='FILE_3D')
            
            # 添加重命名选项
            rename_row = better_fbx_box.row(align=True)
            rename_row.prop(context.scene, "fbx_rename_top_level", text="重命名顶级父级为文件名称", icon='OUTLINER_OB_EMPTY')
            
            row = better_fbx_box.row(align=True)
            row.operator("better_fbx.batch_import", text="批量导入", icon='IMPORT')
            row.operator("better_fbx.batch_import_files", text="选择多个文件", icon='DOCUMENTS')
            
            # 按名称列表批量导入
            name_list_box = better_fbx_box.box()
            name_list_box.label(text="按名称列表批量导入:", icon='TEXT')
            
            # 名称列表输入区域
            text_box = name_list_box.box()
            text_box.label(text="名称列表 (用空格或逗号分隔):", icon='TEXT')
            
            # 输入框和编辑按钮在同一行
            input_row = text_box.row(align=True)
            input_row.prop(context.scene, "fbx_name_list_text", text="", icon='TEXT')
            input_row.operator("object.edit_names_list", text="编辑", icon='TEXT')
            if scene.fbx_temp_names_file_path:
                input_row.operator("object.read_names_from_temp_file", text="加载", icon='IMPORT')
            
            
            name_list_box.prop(context.scene, "fbx_search_directory", text="搜索目录", icon='FILE_FOLDER')
            
            # 添加重命名选项（放在导入按钮前）
            rename_row = name_list_box.row()
            rename_row.prop(context.scene, "fbx_rename_top_level", text="重命名顶级父级为文件名称", icon='OUTLINER_OB_EMPTY')
            
            # 在名称列表导入中也添加格式选择
            name_format_row = name_list_box.row(align=True)
            name_format_row.prop(context.scene, "batch_import_file_format", text="文件格式", icon='FILE_3D')
            name_format_row.operator("better_fbx.batch_import_by_name_list", text="按名称列表导入", icon='IMPORT')
            
            # Better FBX导出
            better_fbx_export_box = import_box.box()
            better_fbx_export_box.label(text="Better FBX导出:", icon='EXPORT')
            better_fbx_export_box.prop(context.scene, "better_fbx_export_directory", text="FBX导出目录", icon='FILE_FOLDER')
            
            better_fbx_export_box.operator("better_fbx.batch_export_by_top_level", text="按顶级物体批量导出", icon='EXPORT')
            
            # 批量导出
            export_box = col_inout.box()
            export_box.label(text="批量导出:", icon='EXPORT')
            export_box.prop(context.scene, "export_directory", text="导出目录", icon='FILE_FOLDER')
            
            # 添加导出配置选项
            export_config_box = export_box.box()
            export_config_box.label(text="导出配置:", icon='SETTINGS')
            export_config_box.prop(context.scene, "export_config", text="")
            export_config_box.prop(context.scene, "clear_parent_on_export", text="清除父级关系", icon='UNLINKED')
            
            col = export_box.column(align=True)
            col.operator("scene.export_fbx_by_parent", text="按顶级父物体导出FBX", icon='OUTLINER_OB_EMPTY')
            col.operator("scene.export_fbx_by_col_mark", text="按.col标记导出FBX", icon='BOOKMARKS')
            col.operator("object.mian_output_fbx_as_collection", text="按集合分文件夹导出FBX", icon='OUTLINER_COLLECTION')
            col.operator("object.export_objs", text="批量导出OBJ", icon='EXPORT')
            
            # 批量关联场景
            link_scenes_batch_box = col_inout.box()
            link_scenes_batch_box.label(text="场景关联与排序:", icon='SCENE_DATA')
            link_scenes_batch_box.prop(context.scene, "export_directory", text=".Blender文件目录", icon='BLENDER')
            
            col = link_scenes_batch_box.column(align=True)
            col.operator("scene.link_scenes_batch", text="从.blend文件关联场景", icon='LINK_BLEND')
            col.operator("scene.sort_scenes", text="按名称排序场景", icon='SORTALPHA')
            col.operator("scene.add_sorted_scenes_to_sequencer", text="批量添加场景至时间轴", icon='SEQ_SEQUENCER')

# 资产操作
        col_assestoperation = layout.column()
        col_assestoperation.prop(scene, "assestoperation_expand", text="资产转换工具", emboss=False,
                                 icon='TRIA_DOWN' if context.scene.assestoperation_expand else 'TRIA_RIGHT')
        if context.scene.assestoperation_expand:
            # VOX处理
            box_vox = col_assestoperation.box()
            box_vox.label(text="VOX模型处理:", icon='MESH_GRID')
            box_vox.operator("object.vox_operation", text="导入VOX一键处理", icon='IMPORT')

            # 批量处理步骤
            box_assestoperation = col_assestoperation.box()
            box_assestoperation.label(text="模型预处理流程:", icon='PRESET_NEW')
            col = box_assestoperation.column(align=True)
            col.operator("object.mian_apply_and_separate", text="1.独立化应用所有变换", icon='OBJECT_DATA')
            col.operator("object.mian_merge_top_level", text="2.按顶级层级合并", icon='OUTLINER_OB_GROUP_INSTANCE')
            col.operator("object.mian_reset_normals", text="3.重置所选矢量", icon='NORMALS_VERTEX')
            col.operator("object.mian_clean_empty", text="4.清理所选空物体", icon='OUTLINER_OB_EMPTY')
            col.operator("object.mian_clean_sense", text="5.递归清理场景", icon='PARTICLEMODE')

            # 批量标记资产
            assembly_asset_box = col_assestoperation.box()
            assembly_asset_box.label(text="批量标记资产:", icon='ASSET_MANAGER')
            assembly_asset_box.prop(context.scene, "asset_collection", text="目标集合", icon='COLLECTION_COLOR_04')
            assembly_asset_box.prop(context.scene, "create_top_level_parent", text="创建顶级父级")
            
            row = assembly_asset_box.row()
            row.operator("object.mian_create_assembly_asset", text="创建装配资产", icon='CHECKMARK')
            # row.operator("object.mian_create_asset_library_outline", text="创建分类大纲", icon='OUTLINER_COLLECTION')
            
            # 隐藏导入集合管理
            hidden_collection_box = col_assestoperation.box()
            hidden_collection_box.label(text="隐藏导入集合管理:", icon='HIDE_OFF')
            
            # 操作按钮行
            hidden_row1 = hidden_collection_box.row(align=True)
            op1 = hidden_row1.operator("object.mian_manage_hidden_collection", text="显示集合", icon='HIDE_OFF')
            op1.action = 'SHOW'
            op2 = hidden_row1.operator("object.mian_manage_hidden_collection", text="隐藏集合", icon='HIDE_ON')
            op2.action = 'HIDE'
            
            hidden_row2 = hidden_collection_box.row(align=True)
            op3 = hidden_row2.operator("object.mian_manage_hidden_collection", text="显示信息", icon='INFO')
            op3.action = 'INFO'
            op4 = hidden_row2.operator("object.mian_manage_hidden_collection", text="清空集合", icon='TRASH')
            op4.action = 'CLEAR'

            # Voxelizer设置
            box_voxelizer = col_assestoperation.box()
            box_voxelizer.label(text="Voxelizer工具:", icon='CUBE')
            box_voxelizer.prop(context.scene.voxelizer_tool, "path", text="模型路径", icon='FILE_3D')
            box_voxelizer.prop(context.scene.voxelizer_tool, "voxelizer_path", text="Voxelizer路径", icon='TOOL_SETTINGS')
            
            row = box_voxelizer.row(align=True)
            row.operator("object.convert_voxelizer", text="转换为VOX", icon='MESH_CUBE')
            row.operator("object.convert_voxelizer_color", text="转换为VOX(带颜色)", icon='COLOR')

            # 体素转换
            convert_box = col_assestoperation.box()
            convert_box.label(text="体素化设置:", icon='LIGHTPROBE_GRID')
            convert_box.operator("object.voxel_converter", text="生成体素化指令", icon='CONSOLE')
            convert_box.prop(scene, "resolution_factor", text="分辨率因子")

#批量渲染
        col_autorender = layout.column()
        col_autorender.prop(scene, "autorender_expand", text="渲染工具", emboss=False, 
                            icon='TRIA_DOWN' if scene.autorender_expand else 'TRIA_RIGHT')

        if scene.autorender_expand:
            # 快速处理显示效果
            quick_render_box = col_autorender.box()
            quick_render_box.label(text="快速处理:", icon='SHADING_RENDERED')
            
            # 条件显示渲染按钮
            if can_load_safely:
                # 检查操作符是否已注册
                if hasattr(bpy.types, 'AUTO_RENDER_OT_oneclick'):
                    quick_render_box.operator("auto_render.oneclick", 
                                           text="优化体素模型显示效果", 
                                           icon='SHADERFX')
                    # 移除调试打印，减少控制台输出
                    # print("✅ 渲染按钮显示正常")
                else:
                    quick_render_box.label(text="⚠️ 渲染操作符未注册", icon='ERROR')
                    # 只在首次检查失败时打印
                    if not hasattr(self, '_render_op_error_shown'):
                        print("❌ 渲染操作符未注册")
                        self._render_op_error_shown = True
            else:
                # 受限模式：显示禁用按钮
                disabled_row = quick_render_box.row()
                disabled_row.enabled = False
                disabled_row.operator("auto_render.oneclick", 
                                   text="优化体素模型显示效果 (需要PIL)", 
                                   icon='SHADERFX')
                
                # 显示安装提示
                info_box = quick_render_box.box()
                info_box.label(text="⚠️ 此功能需要PIL依赖", icon='ERROR')
                info_box.label(text="安装命令: python.exe -m pip install pillow")
                info_box.label(text="安装后请重启插件")
            
            # 批量渲染设置
            box_autorender = col_autorender.box()
            box_autorender.label(text="批量渲染", icon='RENDER_STILL')
            
            # 检查auto_render_settings是否可用
            if hasattr(bpy.context.scene, 'auto_render_settings'):
                # 输出设置
                output_col = box_autorender.column(align=True)
                output_col.prop(bpy.context.scene.auto_render_settings, "output_path", text="路径", icon='FILE_FOLDER')
                
                # 命名模式选择
                naming_row = output_col.row(align=True)
                naming_row.prop(bpy.context.scene.auto_render_settings, "naming_mode", text="命名模式", icon='OUTLINER_OB_FONT')
                
                # 自定义名称输入（仅在需要时显示）
                if bpy.context.scene.auto_render_settings.naming_mode in ['CUSTOM', 'HYBRID']:
                    output_col.prop(bpy.context.scene.auto_render_settings, "output_name", text="自定义名称", icon='FILE_BLANK')
                
                output_row = output_col.row(align=True)
                output_row.prop(bpy.context.scene.auto_render_settings, "output_format", text="格式", icon='FILE_IMAGE')
                
                # EXR格式说明
                if bpy.context.scene.auto_render_settings.output_format == 'EXR':
                    exr_info = output_col.box()
                    exr_info.label(text="EXR格式特性:", icon='INFO')
                    exr_info.label(text="• 完美支持透明通道和32位色彩")
                    exr_info.label(text="• 高动态范围，适合后期处理")
                    exr_info.label(text="• 不支持图像尺寸调节和边框添加")
                    exr_info.label(text="• 建议使用Blender内置设置")
                elif bpy.context.scene.auto_render_settings.output_format == 'EXR_TO_PNG':
                    exr_to_png_info = output_col.box()
                    exr_to_png_info.label(text="EXR→PNG模式特性:", icon='INFO')
                    exr_to_png_info.label(text="• 先渲染为EXR，完美支持透明通道")
                    exr_to_png_info.label(text="• 自动转换为PNG，解决alpha硬裁切问题")
                    exr_to_png_info.label(text="• 支持图像尺寸调节和边框添加")
                    exr_to_png_info.label(text="• 最终输出为PNG格式")

                # 最终图像尺寸设置
                final_size_col = box_autorender.column(align=True)
                # 图像尺寸设置（始终显示）
                final_size_row = final_size_col.row(align=True)
                final_size_row.prop(bpy.context.scene.auto_render_settings, "final_width", text="宽度")
                final_size_row.prop(bpy.context.scene.auto_render_settings, "final_height", text="高度")
                
                # 边框距离设置
                final_size_row = final_size_col.row(align=True)
                final_size_row.prop(bpy.context.scene.auto_render_settings, "margin_distance", text="边框距离")
                
                # 动态显示最大边框距离限制
                final_width = bpy.context.scene.auto_render_settings.final_width
                final_height = bpy.context.scene.auto_render_settings.final_height
                max_margin = min(final_width, final_height) // 2
                margin_distance = bpy.context.scene.auto_render_settings.margin_distance
                
                if margin_distance > max_margin:
                    warning_row = final_size_col.row(align=True)
                    warning_row.label(text=f"⚠️ 边框距离过大！最大允许: {max_margin}px", icon='ERROR')
                else:
                    info_row = final_size_col.row(align=True)
                    info_row.label(text=f"最大允许边框距离: {max_margin}px (基于尺寸: {final_width}x{final_height})")
                
                final_size_row = final_size_col.row(align=True)
                final_size_row.label(text="(缩放图像保持边距)")
                
                # 渲染对象
                render_col = box_autorender.column()
                render_row = render_col.row(align=True)
                render_row.prop(bpy.context.scene.auto_render_settings, "collections", text="集合", icon='OUTLINER_COLLECTION')
                render_row.prop(bpy.context.scene.auto_render_settings, "cameras", text="相机", icon='CAMERA_DATA')
                
                # 相机设置
                camera_col = box_autorender.column()
                # 功能选项 - 放在一排
                options_row = camera_col.row()
                options_row.prop(bpy.context.scene.auto_render_settings, "focus_each_object", text="聚焦到物体")
                options_row.prop(bpy.context.scene.auto_render_settings, "focus_only_faces", text="仅聚焦有面")
                options_row.prop(bpy.context.scene.auto_render_settings, "auto_keyframe", text="自动关键帧")
                options_row.prop(bpy.context.scene.auto_render_settings, "use_compositor", text="合成器效果")
                
                # 透视相机增强聚焦选项
                if bpy.context.scene.auto_render_settings.focus_each_object:
                    perspective_row = camera_col.row()
                    # 增强透视相机聚焦功能已移除
                
                # 关键帧管理
                keyframe_col = box_autorender.column()
                keyframe_row = keyframe_col.row(align=True)
                keyframe_row.operator("auto_render.generate_keyframes_only", text="仅生成关键帧", icon='KEY_HLT')
                keyframe_row.operator("auto_render.clear_camera_keyframes", text="清除关键帧", icon='KEY_DEHLT')
                
                # 执行按钮
                if can_load_safely:
                    box_autorender.operator("auto_render.execute", text="执行渲染", icon='RENDER_STILL')
                else:
                    # 受限模式：显示禁用按钮
                    disabled_row = box_autorender.row()
                    disabled_row.enabled = False
                    disabled_row.operator("auto_render.execute", text="执行渲染 (需要PIL)", icon='RENDER_STILL')
            else:
                # auto_render_settings不可用时的提示
                info_box = box_autorender.box()
                info_box.label(text="⚠️ 渲染设置不可用", icon='ERROR')
                info_box.label(text="请确保AutoRender模块已正确注册")
            
            # 批量调整渲染设置
            box_renderadj = col_autorender.box()
            box_renderadj.label(text="批量调整渲染设置:", icon='PREFERENCES')
            
            change_resolution_prop = context.scene.change_resolution_prop
            
            # 文件路径设置
            path_col = box_renderadj.column()
            path_col.label(text="文件路径:", icon='FILE_FOLDER')
            path_col.prop(change_resolution_prop, "input_dir", text="输入目录")
            path_col.prop(change_resolution_prop, "output_dir", text="输出目录")
            path_col.prop(change_resolution_prop, "output_file", text="渲染输出路径")
            
            # 渲染设置
            render_settings_col = box_renderadj.column()
            render_settings_col.label(text="渲染设置:", icon='SCENE')
            
            row = render_settings_col.row(align=True)
            row.prop(change_resolution_prop, "render_engine", text="引擎")
            row.prop(change_resolution_prop, "output_format", text="格式")
            
            # 分辨率设置
            res_col = box_renderadj.column()
            res_col.label(text="分辨率设置:", icon='FULLSCREEN_ENTER')
            
            row1 = res_col.row(align=True)
            row1.prop(change_resolution_prop, "output_resolution_x", text="宽度")
            row1.prop(change_resolution_prop, "output_resolution_y", text="高度")
            
            row2 = res_col.row(align=True)
            row2.prop(change_resolution_prop, "resolution_percentage", text="质量百分比")
            row2.prop(change_resolution_prop, "output_frame_rate", text="帧率")
            
            # 执行按钮
            operator_instance = box_renderadj.operator(BATCH_RESOLUTION_OT_ExecuteButton.bl_idname, text="执行批量设置", icon='PLAY')

            # 传递参数
            operator_instance.output_file = change_resolution_prop.output_file
            operator_instance.render_engine = change_resolution_prop.render_engine
            operator_instance.output_format = change_resolution_prop.output_format
            operator_instance.input_dir = change_resolution_prop.input_dir
            operator_instance.output_dir = change_resolution_prop.output_dir
            operator_instance.output_resolution_x = str(change_resolution_prop.output_resolution_x)
            operator_instance.output_resolution_y = str(change_resolution_prop.output_resolution_y)
            operator_instance.resolution_percentage = str(change_resolution_prop.resolution_percentage)
            operator_instance.output_frame_rate = str(change_resolution_prop.output_frame_rate)


            
class AddSourceMaterialOperator(bpy.types.Operator):
    bl_idname = "object.add_source_material"
    bl_label = "添加源材质"
    bl_description = "添加材质到源材质列表"
    
    def execute(self, context):
        # 直接添加一个空的材质槽
        new_item = context.scene.source_materials.add()
        new_item.material = None
        return {'FINISHED'}

class RemoveSourceMaterialOperator(bpy.types.Operator):
    bl_idname = "object.remove_source_material"
    bl_label = "移除源材质"
    bl_description = "从源材质列表移除材质"
    
    index: bpy.props.IntProperty(
        name="索引",
        default=0
    ) # type: ignore
    
    def execute(self, context):
        if 0 <= self.index < len(context.scene.source_materials):
            context.scene.source_materials.remove(self.index)
            return {'FINISHED'}
        return {'CANCELLED'}

class ClearSourceMaterialsOperator(bpy.types.Operator):
    bl_idname = "object.clear_source_materials"
    bl_label = "清空源材质列表"
    bl_description = "清空源材质列表"
    
    def execute(self, context):
        context.scene.source_materials.clear()
        return {'FINISHED'}



def register():
    bpy.utils.register_class(MaterialPropertyGroup)
    bpy.utils.register_class(CustomFunctionsPanel)
    bpy.utils.register_class(AddSourceMaterialOperator)
    bpy.utils.register_class(RemoveSourceMaterialOperator)
    bpy.utils.register_class(ClearSourceMaterialsOperator)
    
    # 注册场景属性
    bpy.types.Scene.source_materials = CollectionProperty(type=MaterialPropertyGroup)
    bpy.types.Scene.target_material = PointerProperty(
        type=bpy.types.Material,
        name="目标材质"
    )
    
    # 基于关键字的材质替换属性
    bpy.types.Scene.keyword_search = bpy.props.StringProperty(
        name="搜索关键字",
        description="要搜索的材质名称关键字",
        default="",
        maxlen=100
    )
    bpy.types.Scene.keyword_target_material = bpy.props.PointerProperty(
        type=bpy.types.Material,
        name="目标材质",
        description="替换后的目标材质"
    )
    
    # 材质拆分属性
    bpy.types.Scene.split_material = bpy.props.PointerProperty(
        type=bpy.types.Material,
        name="拆分材质",
        description="要拆分的材质"
    )
    
    # 新的独立工具分类属性
    bpy.types.Scene.edit_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.clean_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.gen_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.select_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.namelist_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.BindOperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.meterialoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.renameoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.rsm_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.anm_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.inout_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.assestoperation_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.autorender_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.light_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.animation_tools_expand = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.curve_tools_expand = bpy.props.BoolProperty(default=False)

    
    # 灯光关联工具参数
    bpy.types.Scene.light_linking_tolerance = bpy.props.FloatProperty(
        name="相似度容差",
        description="判断灯光相似性的容差值",
        default=0.01,
        min=0.001,
        max=0.5,
        soft_min=0.005,
        soft_max=0.1,
        precision=3
    )
    
    # 灯光强度调整参数
    bpy.types.Scene.light_intensity_multiplier = bpy.props.FloatProperty(
        name="强度倍数",
        description="灯光强度的倍数",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=3
    )

    # 源骨架属性
    bpy.types.Scene.source_armature = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="源骨架",
        description="选择带动画的源骨架",
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

    # 目标骨架属性
    bpy.types.Scene.target_armature = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="目标骨架",
        description="选择要接收动画的目标骨架",
        poll=lambda self, obj: obj.type == 'ARMATURE'
    )

    # 骨骼动画转移参数
    bpy.types.Scene.transfer_bone_animation_keyframe_sample_rate = bpy.props.IntProperty(
        name="关键帧采样率",
        description="每多少帧采样一次关键帧",
        default=1,
        min=1
    )

    bpy.types.Scene.transfer_bone_animation_batch_size = bpy.props.IntProperty(
        name="批处理帧数",
        description="每次处理多少帧",
        default=10,
        min=1
    )

    bpy.types.Scene.transfer_bone_animation_show_detailed_info = bpy.props.BoolProperty(
        name="显示详细信息",
        description="是否显示详细的处理信息",
        default=False
    )
    
    # FBX名称列表批量导入相关属性
    bpy.types.Scene.fbx_name_list_text = bpy.props.StringProperty(
        name="FBX名称列表",
        description="要查找的FBX文件名称列表，用空格或逗号分隔多个名称。例如：my_model my_character 或 my_model,my_character",
        default="",
    )
    bpy.types.Scene.fbx_search_directory = bpy.props.StringProperty(
        name="搜索目录",
        description="要搜索FBX文件的目录路径",
        subtype='DIR_PATH',
        default="",
    )
    
    # 添加临时文件路径属性
    bpy.types.Scene.fbx_temp_names_file_path = bpy.props.StringProperty(
        name="临时文件路径",
        description="临时文件路径",
        default="",
    )
    
    # Better FBX导入相关属性
    bpy.types.Scene.better_fbx_import_directory = bpy.props.StringProperty(
        name="3D文件目录",
        description="批量导入的3D文件目录",
        subtype='DIR_PATH',
        default=""
    )
    
    # 批量导入文件格式选择
    bpy.types.Scene.batch_import_file_format = bpy.props.EnumProperty(
        name="文件格式",
        description="选择要导入的文件格式",
        items=[
            ('FBX', 'FBX', '导入FBX文件'),
            ('OBJ', 'OBJ', '导入OBJ文件'),
        ],
        default='FBX'
    )
    
    # FBX重命名选项
    bpy.types.Scene.fbx_rename_top_level = bpy.props.BoolProperty(
        name="重命名顶级父级为文件名称",
        description="导入后将顶级父级重命名为FBX文件名",
        default=False
    )
    
    # Better FBX导出相关属性
    bpy.types.Scene.better_fbx_export_directory = bpy.props.StringProperty(
        name="FBX导出目录",
        description="批量导出的FBX文件保存目录",
        subtype='DIR_PATH',
        default=""
    )

    # 添加工具搜索功能
    bpy.types.Scene.tool_search_text = bpy.props.StringProperty(
        name="搜索工具",
        description="输入关键词快速查找工具",
        default="",
        maxlen=100,
    )
    bpy.types.Scene.show_quick_tools = bpy.props.BoolProperty(
        name="显示常用工具",
        description="在面板顶部显示常用工具",
        default=True,
    )
    
    # 批量顶点组工具属性
    bpy.types.Scene.vertex_group_name = bpy.props.StringProperty(
        name="顶点组名称",
        description="要创建的顶点组名称",
        default="VertexGroup",
        maxlen=100,
    )
    
    # 曲线闭合选项属性
    bpy.types.Scene.curve_closed_option = bpy.props.BoolProperty(
        name="创建闭合曲线",
        description="是否创建闭合的曲线路径",
        default=True
    )
    
    # 移除重复帧工具属性
    bpy.types.Scene.duplicate_frames_detection_mode = bpy.props.EnumProperty(
        name="检测模式",
        description="选择检测重复帧的算法模式",
        items=[
            ('FAST', "快速模式", "使用向量化操作，适合大量关键帧"),
            ('PRECISE', "精确模式", "逐帧检测，确保100%准确"),
            ('SMART', "智能模式", "自动选择最佳检测方式")
        ],
        default='SMART'
    )
    
    bpy.types.Scene.duplicate_frames_threshold = bpy.props.FloatProperty(
        name="检测阈值",
        description="检测重复帧的精度阈值（数值越小检测越精确）",
        default=0.001,
        min=0.0001,
        max=1.0
    )
    
    
    


def unregister():
    bpy.utils.unregister_class(CustomFunctionsPanel)
    bpy.utils.unregister_class(MaterialPropertyGroup)
    bpy.utils.unregister_class(AddSourceMaterialOperator)
    bpy.utils.unregister_class(RemoveSourceMaterialOperator)
    bpy.utils.unregister_class(ClearSourceMaterialsOperator)
    
    # 注销场景属性
    properties_to_remove = [
        # 基础属性
        "edit_tools_expand",
        "clean_tools_expand", 
        "gen_tools_expand",
        "align_tools_expand",
        "select_tools_expand",
        "namelist_tools_expand",
        "BindOperation_expand",
        "meterialoperation_expand",
        "renameoperation_expand",
        "rsm_expand",
        "anm_expand",
        "inout_expand",
        "assestoperation_expand",
        "autorender_expand",
        "light_tools_expand",
        "animation_tools_expand",
        "curve_tools_expand",
        
        # 材质相关属性
        "source_materials",
        "target_material",
        "keyword_search",
        "keyword_target_material",
        "split_material",
        
        # 灯光关联工具参数
        "light_linking_tolerance",
        "light_intensity_multiplier",
        
        # 骨架相关属性
        "source_armature",
        "target_armature",
        
        # 骨骼动画转移参数
        "transfer_bone_animation_keyframe_sample_rate",
        "transfer_bone_animation_batch_size",
        "transfer_bone_animation_show_detailed_info",
        
        # FBX名称列表批量导入相关属性
        "fbx_name_list_text",
        "fbx_search_directory",
        
        # Better FBX导入相关属性
        "better_fbx_import_directory",
        "batch_import_file_format",
        "fbx_rename_top_level",
        
        # Better FBX导出相关属性
        "better_fbx_export_directory",

        # 添加工具搜索功能
        "tool_search_text",
        "show_quick_tools",
        
        # 批量顶点组工具属性
        "vertex_group_name",
        
        # 曲线闭合选项属性
        "curve_closed_option",
        

    ]
    
    # 安全地删除所有属性
    for prop in properties_to_remove:
        try:
            delattr(bpy.types.Scene, prop)
        except AttributeError:
            pass  # 如果属性不存在，就跳过
