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


def unregister():
    bpy.utils.unregister_class(SelectSmallObjectsOperator)
    bpy.utils.unregister_class(SelectLargeObjectsOperator)
    bpy.utils.unregister_class(SelectObjectsWithoutTextureOperator)
    del bpy.types.Scene.select_large_objects_threshold
    del bpy.types.Scene.select_small_objects_threshold

if __name__ == "__main__":
    register()