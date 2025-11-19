import bpy
import random
import math
import mathutils


class RandomPlacement(bpy.types.Operator):
    bl_idname = "object.mian_random_placement"
    bl_label = "随机放置"
    bl_description = "在指定范围内随机分布所选物体的位置"

    def execute(self, context):
        # 获取自定义属性的值
        extent = bpy.context.scene.random_placement_extent

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        # Scatter the objects randomly in the defined area
        for obj in objects:
            obj.location = (random.uniform(-extent[0], extent[0]),
                            random.uniform(-extent[1], extent[1]),
                            random.uniform(-extent[2], extent[2]))

        return {'FINISHED'}


class RandomScale(bpy.types.Operator):
    bl_idname = "object.mian_random_scale"
    bl_label = "随机缩放"
    bl_description = "在指定范围内随机缩放所选物体，可分别设置X、Y、Z轴的缩放范围"

    def execute(self, context):
        # 获取自定义属性的值
        scale_extent_x = bpy.context.scene.random_scale_extent_x
        scale_extent_y = bpy.context.scene.random_scale_extent_y
        scale_extent_z = bpy.context.scene.random_scale_extent_z

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        # Scale the objects randomly within the defined range for each axis
        for obj in objects:
            scale_factor_x = random.uniform(
                scale_extent_x[0], scale_extent_x[1])
            scale_factor_y = random.uniform(
                scale_extent_y[0], scale_extent_y[1])
            scale_factor_z = random.uniform(
                scale_extent_z[0], scale_extent_z[1])
            obj.scale = (scale_factor_x, scale_factor_y, scale_factor_z)

        return {'FINISHED'}


class RandomRotation(bpy.types.Operator):
    bl_idname = "object.mian_random_rotation"
    bl_label = "随机旋转"
    bl_description = "对所选物体进行指定轴向的随机旋转"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取自定义属性的值
        rotation_extent_x = bpy.context.scene.random_rotation_extent_x
        rotation_extent_y = bpy.context.scene.random_rotation_extent_y
        rotation_extent_z = bpy.context.scene.random_rotation_extent_z

        objects = sorted(list(bpy.context.selected_objects),
                         key=lambda obj: obj.name)

        if not objects:
            self.report({'WARNING'}, "请先选择要旋转的物体")
            return {'CANCELLED'}

        # 对每个物体进行随机旋转
        for obj in objects:
            # 保存原始旋转模式
            original_rotation_mode = obj.rotation_mode
            
            # 确保使用欧拉角模式
            if obj.rotation_mode != 'XYZ':
                obj.rotation_mode = 'XYZ'
            
            # 获取当前旋转值
            current_rotation = obj.rotation_euler.copy()
            
            # 计算随机旋转角度（弧度）
            random_rotation_x = math.radians(random.uniform(-rotation_extent_x, rotation_extent_x))
            random_rotation_y = math.radians(random.uniform(-rotation_extent_y, rotation_extent_y))
            random_rotation_z = math.radians(random.uniform(-rotation_extent_z, rotation_extent_z))
            
            # 应用随机旋转
            new_rotation = mathutils.Euler((
                current_rotation[0] + random_rotation_x,
                current_rotation[1] + random_rotation_y,
                current_rotation[2] + random_rotation_z
            ), 'XYZ')
            
            obj.rotation_euler = new_rotation
            
            # 恢复原始旋转模式（如果需要）
            # obj.rotation_mode = original_rotation_mode

        self.report({'INFO'}, f"已对 {len(objects)} 个物体应用随机旋转")
        return {'FINISHED'}


classes = [
    RandomPlacement,
    RandomScale,
    RandomRotation,
]


def register():
    # 随机放置属性
    bpy.types.Scene.random_placement_extent = bpy.props.FloatVectorProperty(
        name="范围大小",
        description="设置随机放置的范围大小",
        default=(10, 10, 10),
        size=3
    )
    
    # 随机缩放属性
    bpy.types.Scene.random_scale_extent_x = bpy.props.FloatVectorProperty(
        name="X轴缩放范围(min, max)",
        description="设置X轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    bpy.types.Scene.random_scale_extent_y = bpy.props.FloatVectorProperty(
        name="Y轴缩放范围(min, max)",
        description="设置Y轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    bpy.types.Scene.random_scale_extent_z = bpy.props.FloatVectorProperty(
        name="Z轴缩放范围(min, max)",
        description="设置Z轴随机缩放的范围",
        default=(1, 1),
        size=2
    )
    
    # 随机旋转属性
    bpy.types.Scene.random_rotation_extent_x = bpy.props.FloatProperty(
        name="X轴旋转范围(度)",
        description="设置X轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )
    bpy.types.Scene.random_rotation_extent_y = bpy.props.FloatProperty(
        name="Y轴旋转范围(度)",
        description="设置Y轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )
    bpy.types.Scene.random_rotation_extent_z = bpy.props.FloatProperty(
        name="Z轴旋转范围(度)",
        description="设置Z轴随机旋转的角度范围",
        default=0.0,
        min=0.0,
        max=360.0
    )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass  # 类已经注册，忽略该异常


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass  # 类未注册，忽略该异常
    
    del bpy.types.Scene.random_placement_extent
    del bpy.types.Scene.random_scale_extent_x
    del bpy.types.Scene.random_scale_extent_y
    del bpy.types.Scene.random_scale_extent_z
    del bpy.types.Scene.random_rotation_extent_x
    del bpy.types.Scene.random_rotation_extent_y
    del bpy.types.Scene.random_rotation_extent_z

