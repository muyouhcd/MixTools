import os
import bpy
import subprocess
from bpy.props import StringProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import BoolProperty



major, minor = bpy.app.version[:2]
version2 = f"{major}.{minor}"
print(version2)


class MySettings(PropertyGroup):

    path : StringProperty(
            name="obj文件路径",
            description="Path to Directory",
            default="",
            maxlen=1024,
            subtype='DIR_PATH')

    voxelizer_path : StringProperty(
            name="cuda_voxelizer文件路径",
            description="Path to Cuda Voxelizer",
            default=f"C:\\Users\\admin\\AppData\\Roaming\\Blender Foundation\\Blender\\{version2}\\scripts\\addons\\miaotools\\",
            maxlen=1024,
            subtype='DIR_PATH')

class VOXELIZER_OT_convert(Operator):
    bl_idname = "object.convert_voxelizer"
    bl_label = "Voxelizer Converter"
    
    def execute(self, context):
        scene = context.scene
        #设置路径
        obj_dir = context.scene.voxelizer_tool.path
        voxelizer_path = context.scene.voxelizer_tool.voxelizer_path
        results = []

        for obj_file in os.listdir(obj_dir):
            if obj_file.endswith(".obj"):          
                obj_name = os.path.splitext(obj_file)[0]    

                print(obj_name)
                
                bpy.ops.import_scene.obj(filepath=os.path.join(obj_dir, obj_file))

                # 设置对象名称为文件名称
                bpy.context.selected_objects[0].name = obj_name  
                
                if obj_name in bpy.data.objects:
                    dimensions = bpy.data.objects[obj_name].dimensions
                    max_dim = max(dimensions.x, dimensions.y, dimensions.z)
                    result = round(max_dim * 32)   

                    if context.scene.generate_solid:
                        solid = " -solid"
                    else:
                        solid = " "

                    results.append(f"cuda_voxelizer -f {obj_dir}{obj_name}.obj -o vox -s {result} {solid}")

                
                    bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
                    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        print("All Results:")
        for result in results:
            print(result)
#按照生成指令逐个运行
        for result in results:
            p = subprocess.Popen('cmd', 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE,
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)

            switch_path_command = f'cd {voxelizer_path}\n'.encode('utf-8')
            p.stdin.write(switch_path_command)
            p.stdin.flush()
            command = f'{result}\n'.encode('utf-8')
            print(switch_path_command)
            print(command)
            p.stdin.write(command)
            p.stdin.flush()
            p.stdin.close()
            p.wait()
#去除生成的vox文件中的额外字符
        for filename in os.listdir(obj_dir):
            if filename.endswith(".vox"):
                obj_name = filename.split(".obj")[0]
                vox_name = obj_name + ".vox"
                os.rename(os.path.join(obj_dir, filename),  
                        os.path.join(obj_dir, vox_name))
        
        return {'FINISHED'}
    
class VOXELIZER_OT_convert_with_color(Operator):
    bl_idname = "object.convert_voxelizer_color"
    bl_label = "Voxelizer Converter"
    
    def execute(self, context):
        scene = context.scene
        #设置路径
        obj_dir = context.scene.voxelizer_tool.path
        voxelizer_path = context.scene.voxelizer_tool.voxelizer_path
        results = []

        for obj_file in os.listdir(obj_dir):
            if obj_file.endswith(".obj"):          
                obj_name = os.path.splitext(obj_file)[0]    
                print(obj_name)
                bpy.ops.import_scene.obj(filepath=os.path.join(obj_dir, obj_file))
                # 设置对象名称为文件名称
                bpy.context.selected_objects[0].name = obj_name  
                if obj_name in bpy.data.objects:
                    dimensions = bpy.data.objects[obj_name].dimensions
                    max_dim = max(dimensions.x, dimensions.y, dimensions.z)
                    result = round(max_dim * 32)

                    results.append(f"obj2voxel {obj_dir}{obj_name}.obj {obj_dir}{obj_name}.vox -r {result} -p xZy")
                    print(results)
    
                    bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
                    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        print("All Results:")
        for result in results:
            print(result)
#按照生成指令逐个运行
        for result in results:
            p = subprocess.Popen('cmd', 
                                 stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE,
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)

            switch_path_command = f'cd {voxelizer_path}\n'.encode('utf-8')

            p.stdin.write(switch_path_command)
            p.stdin.flush()
            command = f'{result}\n'.encode('utf-8')
            print(switch_path_command)
            print(command)
            p.stdin.write(command)
            p.stdin.flush()
            p.stdin.close()
            p.wait()
   
        return {'FINISHED'}
        

def register():
    bpy.types.Scene.generate_solid = bpy.props.BoolProperty(
            name="实心转换",
            default=False,
            )

    bpy.utils.register_class(MySettings)
    bpy.types.Scene.voxelizer_tool = bpy.props.PointerProperty(type=MySettings)
    bpy.utils.register_class(VOXELIZER_OT_convert)
    bpy.utils.register_class(VOXELIZER_OT_convert_with_color)
    

    
def unregister():

    bpy.utils.unregister_class(VOXELIZER_OT_convert)
    bpy.utils.unregister_class(MySettings)
    bpy.utils.unregister_class(VOXELIZER_OT_convert_with_color)
    del bpy.types.Scene.voxelizer_tool

    try:
        del bpy.types.Scene.generate_solid
    except:
        print('generate_solid 取消注册失败')
        pass  # 类未注册，忽略该异常
    

if __name__ == "__main__":
    register()