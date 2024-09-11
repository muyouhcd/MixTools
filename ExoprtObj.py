
import bpy


# 批量导出obj
class ExporteObjOperator(bpy.types.Operator):
  bl_label = "批量导出Obj"
  bl_idname = "object.export_objs"

  def execute(self, context):
    
    output_dir = context.scene.export_directory
    
    selected_objects = context.selected_objects
    
    if not selected_objects:
      self.report({'INFO'}, "No objects selected")
      return {'FINISHED'}

    for obj in selected_objects:
        
      obj_name = obj.name
      export_path = os.path.join(output_dir, obj_name + ".obj")
    
      bpy.ops.object.select_all(action='DESELECT')
      obj.select_set(True)
      bpy.context.view_layer.objects.active = obj
      bpy.ops.export_scene.obj(
        filepath = export_path,
        check_existing=True, 
        axis_forward='-Z', 
        axis_up='Y', 
        use_selection=True, 
        use_animation=False, 
        use_mesh_modifiers=True, 
        use_edges=True, 
        use_smooth_groups=False, 
        use_smooth_groups_bitflags=False, 
        use_normals=True, 
        use_uvs=True, 
        use_materials=True, 
        use_triangles=False, 
        use_nurbs=False, 
        use_vertex_groups=False, 
        use_blen_objects=True, 
        group_by_object=False, 
        group_by_material=False, 
        keep_vertex_order=True, 
        global_scale=1, 
        path_mode='COPY',
      )

      self.report({'INFO'}, f"Exported {obj_name} to {export_path}")
      
    return {'FINISHED'}



def register():     
    bpy.utils.register_class(ExporteObjOperator)


def unregister():
    bpy.utils.unregister_class(ExporteObjOperator)

