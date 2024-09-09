import bpy
import os


def rename_texture():
        # 遍历场景中的所有物体
        for obj in bpy.data.objects:
            # 只处理有材质的对象
            if obj.data and hasattr(obj.data, "materials"):
                for mat in obj.data.materials:
                    if mat and mat.node_tree:
                        # 遍历材质节点
                        for node in mat.node_tree.nodes:
                            # 关注Image Texture节点
                            if node.type == 'TEX_IMAGE':
                                if node.image:
                                    # 获取图片的文件路径和名称
                                    image_filepath = node.image.filepath_raw
                                    image_filename = os.path.basename(image_filepath)
                                    image_name, _ = os.path.splitext(image_filename)

                                    # 将贴图的名称改为图片名称
                                    node.image.name = image_name

                                    print(f"更改贴图名称{image_name} <----- {mat.name}.")

        print("All image names have been updated.")

class RenameTextureOrign(bpy.types.Operator):
    bl_idname = "object.rename_texture_orign"
    bl_label = "rename texture name to orign"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rename_texture()
        print("重命名完成")
        return {'FINISHED'}
    
    


def register():     
    bpy.utils.register_class(RenameTextureOrign)

def unregister():
    bpy.utils.unregister_class(RenameTextureOrign)
