import bpy
from mathutils import Vector


class OBJECT_OT_MoveOrigin(bpy.types.Operator):
    bl_idname = "object.move_origin"
    bl_label = "调整原点"
    bl_options = {'REGISTER', 'UNDO'}

    axis_direction: bpy.props.EnumProperty(
        name="Axis Direction",
        items=[
            ('+X', "+ X", ""),
            ('-X', "- X", ""),
            ('+Y', "+ Y", ""),
            ('-Y', "- Y", ""),
            ('+Z', "+ Z", ""),
            ('-Z', "- Z", "")
        ],
        default='-Z'
    )

    @classmethod
    def poll(cls, context):
        return context.selected_objects

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            # Make sure to operate only within the context of each object
            context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)

            bbox_corners = [obj.matrix_world @ Vector(point) for point in obj.bound_box]
            axis_idx = 'XYZ'.index(self.axis_direction[1])

            if self.axis_direction[0] == '+':
                target = max(bbox_corners, key=lambda c: c[axis_idx])[axis_idx]
            else:
                target = min(bbox_corners, key=lambda c: c[axis_idx])[axis_idx]

            new_origin = list(obj.location)
            new_origin[axis_idx] = target
            bpy.context.scene.cursor.location = new_origin
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

            # Deselect current object to avoid side effects on the next loop
            obj.select_set(False)

        # Restore selection of all originally selected objects
        for obj in selected_objects:
            obj.select_set(True)

        return {'FINISHED'}

def register():
    bpy.utils.register_class(OBJECT_OT_MoveOrigin)
    bpy.types.Scene.axis_direction_enum = bpy.props.EnumProperty(
        name="Axis Direction",
        items=[
            ('+X', "+ X", ""),
            ('-X', "- X", ""),
            ('+Y', "+ Y", ""),
            ('-Y', "- Y", ""),
            ('+Z', "+ Z", ""),
            ('-Z', "- Z", "")
        ],
        default='-Z'
    )
def unregister():
    bpy.utils.unregister_class(OBJECT_OT_MoveOrigin)
    del bpy.types.Scene.axis_direction_enum

if __name__ == "__main__":
    register()