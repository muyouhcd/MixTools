bl_info = {
    "name": "MiAO",
    "author": "MuyouHCD",
    "version": (4,6,6),
    "blender": (3, 6, 1),
    "location": "View3D",
    "description": "python.exe -m pip install pillow",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

import bpy
from . import update
from . import operators
from . import panels
from . import CorrectRotation
from . import renderconfig
from . import remove_unused_material_slots
from . import auto_render
from . import AutoRenameCar
from . import ExportFbx
from . import Voxelizer
from . import AutoRig
from . import AutolinkTexture
from . import MoveOrigin
from . import AutoBake
from . import AutoBakeRemesh

def register():
    
    update.register()
    operators.register()
    renderconfig.register()
    CorrectRotation.register()
    remove_unused_material_slots.register()
    auto_render.register()
    panels.register()
    AutoRenameCar.register()
    ExportFbx.register()
    Voxelizer.register()
    AutoRig.register()
    AutolinkTexture.register()
    MoveOrigin.register()
    AutoBake.register()
    AutoBakeRemesh.register()



def unregister():
    update.unregister()
    operators.unregister()
    panels.unregister()
    auto_render.unregister()
    renderconfig.unregister()
    CorrectRotation.unregister()
    remove_unused_material_slots.unregister()
    AutoRenameCar.unregister()
    ExportFbx.unregister()
    Voxelizer.unregister()
    AutoRig.unregister()
    AutolinkTexture.unregister()
    MoveOrigin.unregister()
    AutoBake.unregister()
    AutoBakeRemesh.unregister()


if __name__ == "__main__":
    register()