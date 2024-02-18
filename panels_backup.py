import bpy
from bpy.props import BoolProperty
from bpy.types import Panel

from .operators import SetEmissionStrength
from .renderconfig import BATCH_RESOLUTION_OT_ExecuteButton
from .operators import CharOperaterBoneWeight

from . import auto_render



class CustomFunctionsPanel(bpy.types.Panel):
    bl_label = "Miao Tools"
    bl_idname = "VIEW3D_PT_custom_functions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MIAO TOOL BOX"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
# 小工具集合
        col_tools = layout.column()
        col_tools.prop(scene, "tools_expand", text="工具集", emboss=False,
                       icon='TRIA_DOWN' if context.scene.tools_expand else 'TRIA_RIGHT')

        # if context.scene.tools_expand:
            
            # 移除选中物体顶点组
            # layout.operator("object.miao_remove_vertex_group")
            # 移除选中物体修改器
            # layout.operator("object.remove_modifiers")
            # 清空空集合
            # layout.operator("object.miao_clean_collection")
            #清除无子集空物体
            # layout.operator("object.clean_empty")
            #批量清空动画
            # layout.operator("object.clear_animation_data")
            #一键批量独立化
            # layout.operator("object.make_single_user_operator")
            # 生成包围盒
            # layout.operator("object.miao_boundbox_gen")
            # 生成凸包
            # layout.operator("object.convex_hull_creator")
            # 安全合并（不破坏集合）
            # layout.operator("object.miao_safecombin")
            # 对齐原点到底部
            # layout.operator("object.miao_alignment_ground")
            #原点批量移动至-y中心
            # operator=layout.operator("object.move_origin_to_bottom")
            # layout.prop(operator, "axis")  
            #选取同uv物体
            # layout.operator("object.match_uv")
            #一键增加精度
            # resize_box = layout.box()
            # resize_box.label(text="校正旋转、缩放以提升精度")
            # resize_box.operator("object.move_outside_operator")
            # resize_box.operator("object.fix_size_operator")

            #选择过大物体
            # layout.operator("object.select_large_objects")
            #选择过小物体
            # layout.operator("object.select_small_objects")
            #生成指令
            # layout.operator("object.voxel_converter")


# 绑定操作
        col_BindOperation = layout.column()
        col_BindOperation.prop(scene, "BindOperation_expand", text="绑定操作集合", emboss=False,
                               icon='TRIA_DOWN' if context.scene.BindOperation_expand else 'TRIA_RIGHT')
        
        # if context.scene.BindOperation_expand:
            # 检测碰撞归为一个集合
            # layout.operator("object.miao_collection_byboundingbox")
            # 检测碰撞归为一个子集
            # layout.operator("object.miao_parent_byboundingbox")
            # 检测碰撞并合并
            # layout.operator("object.collection_by_attached")
            # 按照集合位置划分父级绑定
            # box_parent_by_collections = layout.box()
            # box_parent_by_collections.label(text="以集合物体设置子集合的父级")
            # box_parent_by_collections.prop(context.scene, "collectionA", text="集合A")
            # box_parent_by_collections.prop(context.scene, "collectionB", text="集合B")
            # box_parent_by_collections.operator("object.miao_set_parent_collections", text="设置父级")
            # 为选中物体绑定空物体父级
            # create_empty_at_origin_box = layout.box()
            # create_empty_at_origin_box.prop(scene, "multiple_object_binding", text="为多个物体绑定父级")
            # create_empty_at_origin_box.operator("object.miao_create_empty_at_bottom", text="创建空物体父级")

# 材质操作
        col_meterialoperation = layout.column()
        col_meterialoperation.prop(scene, "meterialoperation_expand", text="材质操作", emboss=False,
                                   icon='TRIA_DOWN' if context.scene.meterialoperation_expand else 'TRIA_RIGHT')

        # if context.scene.meterialoperation_expand:
            # 材质球排序
            # layout.operator("object.miao_material_sort")
            # 随机材质
            # layout.operator("scene.random_meterial")
            # 清理材质
            # layout.operator("object.miao_merge_material")
            #设置所选物体材质为临近采样（硬边缘）
            # layout.operator("object.set_texture_interpolation")
            #清理空的材质槽
            # layout.operator("object.remove_unused_material_slots")
            #批量设置发光强度
            # emission_box = layout.box()
            # emission_box.prop(context.scene, "emission_strength", text="强度", slider=True)
            # emission_box.operator(SetEmissionStrength.bl_idname).strength = context.scene.emission_strength

# 命名操作
        col_renameoperation = layout.column()
        col_renameoperation.prop(scene, "renameoperation_expand", text="重命名操作", emboss=False,
                                 icon='TRIA_DOWN' if context.scene.renameoperation_expand else 'TRIA_RIGHT')

        if context.scene.renameoperation_expand:
            # 自动重命名（汽车绑定用）
            box_set_remaining_objects = col_renameoperation.box()
            box_set_remaining_objects.label(text="车辆部件自动重命名")
            #box_set_remaining_objects.prop(context.scene, "move_children_to_same_level", text="Move children to same level")
            box_set_remaining_objects.operator("object.miao_auto_rename_car")
            box_set_remaining_objects.operator("object.miao_auto_rename_car_for_rigcar")
            #按空间顺序改名
            # layout.operator("object.miao_rename_location")
            # 更改子级名称为顶级物体
            # layout.operator("object.miao_rename_by_parent")
            # 重命名为所处集合名称
            # layout.operator("object.rename_to_collection")
            #去除名称后缀
            # layout.operator("object.miao_remove_name_suffix")
            #移除顶级物体名称后缀，重名则交换
            # layout.operator("object.remove_suffix_and_resolve")
            #命名mesh为物体名称
            # layout.operator("object.rename_meshes")2
            #命名物体为mesh名称
            # layout.operator("object.rename_objects")
            #按位置物体重命名集合内物体名称
            # box_rename_by_collections = col_renameoperation.box()
            # box_rename_by_collections.label(text="按位置物体重命名集合名称")
            # box_rename_by_collections.prop(context.scene, "collectionA", text="集合A(获取物体名称)")
            # box_rename_by_collections.prop(context.scene, "collectionB", text="集合B(重命名集合)")
            # box_rename_by_collections.operator("object.miao_rename_collections", text="重命名")
            #按位置重命名
            # box_enameoperation = col_renameoperation.box()
            # box_enameoperation.label(text="按位置重命名")
            # box_enameoperation.prop(context.scene, "rename_axis", text="轴向")
            # box_enameoperation.prop(context.scene, "rename_order", text="排序类型")

            

# 旋转缩放位移操作
        col_rsm = layout.column()
        col_rsm.prop(scene, "rsm_expand", text="旋转位移缩放操作", emboss=False,
                     icon='TRIA_DOWN' if context.scene.rsm_expand else 'TRIA_RIGHT')
        if context.scene.rsm_expand:
            # 下落至表面
            layout.operator("object.move_to_surface")
            # 创建一个box来包含列队相关功能
            queue_up_box = layout.box()
            queue_up_box.label(text="列队")
            queue_up_box.prop(context.scene, "queue_up_distance")
            queue_up_box.prop(context.scene, "queue_up_axis", text="轴向")
            queue_up_box.operator("object.miao_queue_up")
            # 创建一个box来包含置乱位置相关功能
            random_placement_box = layout.box()
            random_placement_box.label(text="置乱位置")
            random_placement_box.prop(context.scene, "random_placement_extent")
            random_placement_box.operator("object.miao_random_placement")
            # 创建一个box来包含置乱缩放相关功能
            random_scale_box = layout.box()
            random_scale_box.label(text="置乱缩放")
            random_scale_box.prop(context.scene, "random_scale_extent_x")
            random_scale_box.prop(context.scene, "random_scale_extent_y")
            random_scale_box.prop(context.scene, "random_scale_extent_z")
            random_scale_box.operator("object.miao_random_scale")
            #对齐集合顶级父级
            align_parent_box = layout.box()
            align_parent_box.label(text="父级批量对齐")
            align_parent_box.prop(context.scene, "collectionA", text="集合A (参考)")
            align_parent_box.prop(context.scene, "collectionB", text="集合B (对齐的目标)")
            align_parent_box.operator("object.align_operator")
            

# 导入导出操作
        col_inout = layout.column()
        col_inout.prop(scene, "inout_expand", text="导入导出操作", emboss=False,
                       icon='TRIA_DOWN' if context.scene.inout_expand else 'TRIA_RIGHT')

        if context.scene.inout_expand:
            #导出选择器
            export_box = layout.box()
            export_box.label(text="批量导出")
            export_box.prop(context.scene, "export_directory", text="导出目录")  # 添加目录选择器
            # 按顶级父物体导出FBX
            export_box.operator("scene.export_fbx_by_parent", text="按顶级父物体导出（忽略.col标记）")
            # 按 ".col" 标记导出
            export_box.operator("scene.export_fbx_by_col_mark", text="按.col标记导出")
            # 按集合导出fbx
            export_box.operator("object.miao_output_fbx_as_collection", text="按集合分文件夹批量导出")
            #批量导出obj
            export_box.operator("object.export_objs", text="批量导出obj")
            # 批量关联场景
            link_scenes_batch_box = layout.box()
            link_scenes_batch_box.label(text="批量从目录关联场景")
            link_scenes_batch_box.prop(context.scene, "export_directory", text="存放blender文件目录")
            link_scenes_batch_box.operator("scene.link_scenes_batch", text="从 .blend 文件关联场景")

            # 排序场景列表
            layout.operator("scene.sort_scenes", text="按名称排序场景")
            layout.operator("scene.add_sorted_scenes_to_sequencer", text="批量添加场景至剪辑时间轴")

# GTA导出物体处理
        col_GTAtranslate = layout.column()
        col_GTAtranslate.prop(scene, "GTAtranslate_expand", text="gta源文件处理", emboss=False,
                              icon='TRIA_DOWN' if context.scene.GTAtranslate_expand else 'TRIA_RIGHT')

        if context.scene.GTAtranslate_expand:
            # 校正物体旋转
            layout.operator("object.miao_correct_rotation")
            #GTA导入载具一键处理
            # layout.operator("object.process_objects")

# 资产操作
        col_assestoperation = layout.column()
        col_assestoperation.prop(scene, "assestoperation_expand", text="批量转换资产操作", emboss=False,
                                 icon='TRIA_DOWN' if context.scene.assestoperation_expand else 'TRIA_RIGHT')
        if context.scene.assestoperation_expand:
            box_vox = col_assestoperation.box()
            box_vox.operator("object.vox_operation", text="导入VOX一键处理")
            #一键定位并绑定角色
            box_character = col_assestoperation.box()
            box_character.operator("object.miao_char_operater", text="导入角色一键处理")
            box_character.prop(scene,"assign_contact_weights")
            box_character.prop(scene, "threshold_distance")
            box_character.operator(CharOperaterBoneWeight.bl_idname, text="角色一键绑定")
        
            box_assestoperation = col_assestoperation.box()
            box_assestoperation.operator("object.miao_apply_and_separate", text="1.独立化应用所有变换")
            box_assestoperation.operator("object.miao_merge_top_level", text="2.按顶级层级合并")
            box_assestoperation.operator("object.miao_reset_normals", text="3.重置所选矢量")
            box_assestoperation.operator("object.miao_clean_empty", text="4.清理所选空物体")
            box_assestoperation.operator("object.miao_clean_sense", text="5.递归清理场景")

            assembly_asset_box = col_assestoperation.box()
            assembly_asset_box.label(text="批量标记资产设置")
            assembly_asset_box.prop(context.scene, "asset_collection")
            assembly_asset_box.prop(context.scene, "create_top_level_parent")
            assembly_asset_box.operator("object.miao_create_assembly_asset")

            box_voxelizer = layout.box()
            box_voxelizer.prop(context.scene.voxelizer_tool, "path")
            box_voxelizer.prop(context.scene.voxelizer_tool, "voxelizer_path")
            # box_voxelizer.prop(scene, "generate_solid")
            box_voxelizer.operator("object.convert_voxelizer", text="一键转换vox")
            box_voxelizer.operator("object.convert_voxelizer_color", text="一键转换vox(带颜色)")


# 批量调整渲染设置
        col_renderadj = layout.column()
        col_renderadj.prop(scene, "renderadj_expand", text="批量更改渲染设置", emboss=False,
                           icon='TRIA_DOWN' if context.scene.renderadj_expand else 'TRIA_RIGHT')

        if context.scene.renderadj_expand:

            box_renderadj = col_renderadj.box()
            change_resolution_prop = context.scene.change_resolution_prop
            box_renderadj.prop(change_resolution_prop, "input_dir",text="输入路径")
            box_renderadj.prop(change_resolution_prop, "output_dir",text="输出路径")
            box_renderadj.prop(change_resolution_prop, "render_engine", text="渲染引擎")
            box_renderadj.prop(change_resolution_prop, "output_format", text="输出格式")
            box_renderadj.prop(change_resolution_prop, "output_file", text="渲染输出路径")
            box_renderadj.prop(change_resolution_prop, "output_resolution_x", text="宽度分辨率")
            box_renderadj.prop(change_resolution_prop, "output_resolution_y", text="高度分辨率")
            box_renderadj.prop(change_resolution_prop, "resolution_percentage", text="质量百分比")
            box_renderadj.prop(change_resolution_prop, "output_frame_rate", text="帧率")
            
            operator_instance = box_renderadj.operator(BATCH_RESOLUTION_OT_ExecuteButton.bl_idname)

            # 添加操作按钮并传递输入参数
            operator_instance.output_file = change_resolution_prop.output_file
            operator_instance.render_engine = change_resolution_prop.render_engine
            operator_instance.output_format = change_resolution_prop.output_format
            operator_instance.input_dir = change_resolution_prop.input_dir
            operator_instance.output_dir = change_resolution_prop.output_dir
            operator_instance.output_resolution_x = str(change_resolution_prop.output_resolution_x)
            operator_instance.output_resolution_y = str(change_resolution_prop.output_resolution_y)
            operator_instance.resolution_percentage = str(change_resolution_prop.resolution_percentage)
            operator_instance.output_frame_rate = str(change_resolution_prop.output_frame_rate)

#批量渲染
        col_autorender = layout.column()
        col_autorender.prop(scene, "autorender_expand", text="批量渲染", emboss=False, icon='TRIA_DOWN' if scene.autorender_expand else 'TRIA_RIGHT')

        if scene.autorender_expand:
            box_autorender = col_autorender.box()
            box_autorender.prop(bpy.context.scene.auto_render_settings, "output_path", text="输出路径")
            box_autorender.prop(bpy.context.scene.auto_render_settings, "output_name", text="输出名称")
            box_autorender.prop(bpy.context.scene.auto_render_settings, "output_format", text="输出格式")
            box_autorender.prop(bpy.context.scene.auto_render_settings, "collections", text="渲染集合")
            box_autorender.prop(bpy.context.scene.auto_render_settings, "cameras", text="相机（非中文）")
            box_autorender.operator("auto_render.execute")
            box_autorender_blendefile = col_autorender.box()

            box_autorender_blendefile.label(text="批量渲染.blend文件")
            render_operator = box_autorender_blendefile.operator('auto_render.batch_render')
            box_autorender_blendefile.prop(render_operator, 'render_as_animation',text="渲染动画")

def register():
    bpy.utils.register_class(CustomFunctionsPanel)
    

def unregister():
    bpy.utils.unregister_class(CustomFunctionsPanel)
