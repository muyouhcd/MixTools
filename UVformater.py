import bpy
import bmesh
import math
import mathutils




def area_quad(v1, v2, v3, v4):
    """Calculate the area of a quad by dividing it into two triangles."""
    return mathutils.geometry.area_tri(v1, v2, v3) + mathutils.geometry.area_tri(v1, v3, v4)

def scale_uv_to_match_texture(obj, pixel_per_meter=32, texture_size=128):
    """Adjust UVs of each face in the object so that the texture density matches size requirements."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)

    if not mesh.uv_layers.active:
        print(f"{obj.name} 没有UV映射。")
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    
    uv_layer = bm.loops.layers.uv.active
    texture_meter_size = texture_size / pixel_per_meter

    for face in bm.faces:
        world_verts = [obj.matrix_world @ v.co for v in face.verts]
        face_area_world = (
            mathutils.geometry.area_tri(*world_verts)
            if len(world_verts) == 3
            else area_quad(*world_verts)
        )
        
        if face_area_world <= 0:
            print(f"警告: 对象 {obj.name} 的一个面具有零或负的世界面积，跳过该面。")
            continue
        
        uv_coords = [l[uv_layer].uv.copy() for l in face.loops]

        face_area_uv = (
            mathutils.geometry.area_tri(*uv_coords)
            if len(uv_coords) == 3
            else area_quad(*uv_coords)
        )
        
        if face_area_uv <= 0:
            print(f"警告: 对象 {obj.name} 的一个面具有零或负的 UV 面积，跳过该面。")
            continue

        current_pixel_density = face_area_uv / face_area_world
        target_pixel_density = 1.0 / (texture_meter_size ** 2)
        scale_uv_factor = math.sqrt(target_pixel_density / current_pixel_density)

        center_uv = sum(uv_coords, mathutils.Vector((0, 0))) / len(uv_coords)

        for loop in face.loops:
            loop_uv = loop[uv_layer].uv
            loop_uv.x = (loop_uv.x - center_uv.x) * scale_uv_factor + center_uv.x
            loop_uv.y = (loop_uv.y - center_uv.y) * scale_uv_factor + center_uv.y

    bmesh.update_edit_mesh(mesh)
    bpy.ops.object.mode_set(mode='OBJECT')

class UVformater(bpy.types.Operator):
    bl_idname = "object.uv_formater"
    bl_label = "uv统一规格尺寸"
    bl_description = "批量调整选中对象中的 UV 映射"
    bl_options = {'REGISTER', 'UNDO'}

    pixel_per_meter: bpy.props.IntProperty(
        name="像素/米",
        default=32,
        min=1,
        description="每米的像素数"
    )

    texture_size: bpy.props.IntProperty(
        name="纹理尺寸",
        default=128,
        min=1,
        description="纹理的像素尺寸"
    )
    

    def execute(self, context):
        selected_objects = context.selected_objects
        for obj in selected_objects:
            if obj.type == 'MESH':
                scale_uv_to_match_texture(obj, self.pixel_per_meter, self.texture_size)
            else:
                self.report({'WARNING'}, f"{obj.name} 不是一个网格对象，跳过。")
        return {'FINISHED'}

    
def register():
    bpy.utils.register_class(UVformater)
def unregister():
    bpy.utils.unregister_class(UVformater)