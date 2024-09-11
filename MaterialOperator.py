import bpy



bpy.types.Scene.emission_strength = bpy.props.FloatProperty(
    name="强度",
    description="设置发光强度",
    default=0.2,
    min=0.0,
    max=10.0
        )

#批量设置发光亮度
class SetEmissionStrength(bpy.types.Operator):
    bl_idname = "material.set_emission_strength"
    bl_label = "设置发光强度"

    strength : bpy.props.FloatProperty(
        name="强度",
        description="设置发光强度",
        default=0.2,
        min=0.0
    )

    def set_emission_strength(self, material, strength):
        if not material.use_nodes:
            return

        for node in material.node_tree.nodes:
            if node.type == 'EMISSION':
                node.inputs['Strength'].default_value = strength
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Emission Strength'].default_value = strength

    def process_selected_objects(self, strength):
        for obj in bpy.context.selected_objects:
            if obj.data.materials:
                for mat in obj.data.materials:
                    if mat.node_tree is not None:
                        self.set_emission_strength(mat, strength)

    def execute(self, context):
        strength = context.scene.emission_strength
        self.process_selected_objects(strength)
        return {'FINISHED'}

def register():     

    bpy.utils.register_class(SetEmissionStrength)

def unregister():
    # del bpy.types.Scene.emission_strength
    bpy.utils.unregister_class(SetEmissionStrength)
