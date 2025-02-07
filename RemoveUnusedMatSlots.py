import bpy

class UNUSED_MATERIAL_SLOTS_OT_Remove(bpy.types.Operator):
    bl_idname = "object.remove_unused_material_slots"
    bl_label = "Remove Unused Material Slots"
    bl_description = "Removes unused material slots from selected objects"

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        selected_objects = context.selected_objects
        
        for obj in selected_objects:
            if obj.type == 'MESH':
                obj.update_from_editmode()
                used_material_indices = set()
                material_index_mapping = {}
                for poly in obj.data.polygons:
                    used_material_indices.add(poly.material_index)
                    material_index_mapping[poly.index] = poly.material_index
                    
                used_material_slots = [obj.material_slots[index].material for index in sorted(used_material_indices)]

                for _ in range(len(obj.material_slots)):
                    bpy.ops.object.material_slot_remove({'object': obj})

                for material in used_material_slots:
                    obj.data.materials.append(material)

                for poly in obj.data.polygons:
                    original_index = material_index_mapping[poly.index]
                    poly.material_index = used_material_slots.index(obj.material_slots[original_index].material)

        return {'FINISHED'}
    
# class UNUSED_MATERIAL_SLOTS_PT_Panel(bpy.types.Panel):
#     bl_label = "Remove Unused Slots"
#     bl_idname = "UNUSED_MATERIAL_SLOTS_PT_Panel"
#     bl_space_type = "VIEW_3D"
#     bl_region_type = "UI"
#     bl_category = "Remove Unused Slots"

#     def draw(self, context):
#         layout = self.layout
#         layout.operator("object.remove_unused_material_slots")

    

def register():
    bpy.utils.register_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    # bpy.utils.register_class(UNUSED_MATERIAL_SLOTS_PT_Panel)

def unregister():
    bpy.utils.unregister_class(UNUSED_MATERIAL_SLOTS_OT_Remove)
    # bpy.utils.unregister_class(UNUSED_MATERIAL_SLOTS_PT_Panel)

if __name__ == "__main__":
    register()