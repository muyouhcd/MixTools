import bpy

#选择尺寸超过指定值的物体
def is_object_size_above_threshold(obj, threshold):
    dimensions = obj.dimensions
    max_size = max(dimensions)
    return max_size > threshold

def is_object_size_below_threshold(obj, threshold):
    dimensions = obj.dimensions
    max_size = max(dimensions)
    return max_size < threshold

def has_texture(obj):
    for mat_slot in obj.material_slots:
        material = mat_slot.material
        if material and material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    return True
    return False
    
class SelectLargeObjectsOperator(bpy.types.Operator):
    bl_idname = "object.select_large_objects"
    bl_label = "选择过大物体"
    bl_options = {'REGISTER', 'UNDO'}

    threshold_meters: bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters",
        default=8.0,
        min=0.0
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and is_object_size_above_threshold(obj, self.threshold_meters):
                obj.select_set(True)
        return {'FINISHED'}

class SelectSmallObjectsOperator(bpy.types.Operator):
    bl_idname = "object.select_small_objects"
    bl_label = "选择过小物体"
    bl_options = {'REGISTER', 'UNDO'}

    threshold_meters: bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters",
        default=1.0,
        min=0.0
    )

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and is_object_size_below_threshold(obj, self.threshold_meters):
                obj.select_set(True)
        return {'FINISHED'}
        
class SelectObjectsWithoutTextureOperator(bpy.types.Operator):
    bl_idname = "object.select_objects_without_texture"
    bl_label = "选择没有贴图的物体"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and not has_texture(obj):
                obj.select_set(True)
        return {'FINISHED'}


def update_large_objects_threshold(self, context):
    bpy.types.Scene.select_large_objects_threshold = context.scene.select_large_objects_threshold

def update_small_objects_threshold(self, context):
    bpy.types.Scene.select_small_objects_threshold = context.scene.select_small_objects_threshold


# 按体积筛选物体
class SelectByVolume(bpy.types.Operator):
    bl_idname = "object.miao_select_by_volume"
    bl_label = "按体积筛选物体"

    filter_mode: bpy.props.EnumProperty(
        name="Filter Mode",
        description="筛选大于或小于给定体积的物体",
        items=[
            ("GREATER_THAN", "大于", "选择体积大于给定阈值的物体"),
            ("LESS_THAN", "小于", "选择体积小于给定阈值的物体")
        ],
        default="GREATER_THAN",
    )

    volume_threshold: bpy.props.FloatProperty(
        name="体积阈值",
        description="根据筛选模式选择大于或小于此值的物体",
        default=0.0,
        min=0.0,
        max=float('inf'),
        soft_min=0,
        soft_max=1000.0,
        step=1,
        precision=2,
    )

    select: bpy.props.BoolProperty(
        name="选择物体",
        description="若选中，满足条件的物体将被选择；若不选中，满足条件的物体将被取消选择",
        default=True,
    )

    def execute(self, context):
        scene = bpy.context.scene

        for obj in scene.objects:
            if obj.type == "MESH":
                volume = obj.dimensions.x * obj.dimensions.y * obj.dimensions.z

                if self.filter_mode == "GREATER_THAN":
                    condition = volume > self.volume_threshold
                else:
                    condition = volume < self.volume_threshold

                if condition:
                    obj.select_set(self.select)
                else:
                    obj.select_set(not self.select)
        return {"FINISHED"}




def register():
    bpy.utils.register_class(SelectLargeObjectsOperator)
    bpy.utils.register_class(SelectSmallObjectsOperator)
    bpy.utils.register_class(SelectObjectsWithoutTextureOperator)
    bpy.types.Scene.select_large_objects_threshold = bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters for large objects",
        default=8.0,
        min=0.0,
        update=update_large_objects_threshold
    )
    bpy.types.Scene.select_small_objects_threshold = bpy.props.FloatProperty(
        name="Threshold (Meters)",
        description="Threshold size in meters for small objects",
        default=1.0,
        min=0.0,
        update=update_small_objects_threshold
    )
    bpy.utils.register_class(SelectByVolume)


def unregister():
    bpy.utils.unregister_class(SelectSmallObjectsOperator)
    bpy.utils.unregister_class(SelectLargeObjectsOperator)
    bpy.utils.unregister_class(SelectObjectsWithoutTextureOperator)
    del bpy.types.Scene.select_large_objects_threshold
    del bpy.types.Scene.select_small_objects_threshold
    bpy.utils.unregister_class(SelectByVolume)

if __name__ == "__main__":
    register()