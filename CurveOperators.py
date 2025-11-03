import bpy

#曲线精简到两个端点
class SimplifyCurveToEndpoints(bpy.types.Operator):
    """将所选曲线精简到仅剩两个端点"""
    bl_idname = "object.simplify_curve_to_endpoints"
    bl_label = "曲线精简到端点"
    bl_description = "将所选曲线精简到仅剩两个端点"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # 获取当前的选中物体
        selected_objects = context.selected_objects
        
        if not selected_objects:
            self.report({'WARNING'}, "请选择至少一个曲线物体")
            return {'CANCELLED'}

        processed_count = 0
        curve_objects = []

        # 筛选出曲线物体
        for obj in selected_objects:
            if obj.type == 'CURVE':
                curve_objects.append(obj)

        if not curve_objects:
            self.report({'WARNING'}, "所选物体中没有曲线物体")
            return {'CANCELLED'}

        # 处理每个曲线物体
        for obj in curve_objects:
            try:
                # 进入编辑模式
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                
                # 选择所有控制点
                bpy.ops.curve.select_all(action='SELECT')
                
                # 使用精简操作，将曲线精简到最少点数
                # 这里我们使用一个循环来逐步精简，直到只剩下两个点
                bpy.ops.curve.decimate(ratio=0.1)
                
                # 如果还有超过2个点，继续精简
                while True:
                    # 获取当前选中的点数
                    bpy.ops.curve.select_all(action='SELECT')
                    selected_count = len([p for p in obj.data.splines[0].points if p.select])
                    
                    if selected_count <= 2:
                        break
                    
                    # 进一步精简
                    bpy.ops.curve.decimate(ratio=0.5)
                
                # 返回对象模式
                bpy.ops.object.mode_set(mode='OBJECT')
                
                processed_count += 1
                
            except Exception as e:
                print(f"处理曲线 {obj.name} 时出错: {e}")
                # 确保返回对象模式
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except:
                    pass
                continue

        if processed_count > 0:
            self.report({'INFO'}, f"成功精简了 {processed_count} 个曲线物体")
        else:
            self.report({'WARNING'}, "没有成功处理任何曲线物体")

        return {'FINISHED'}

classes = [
    SimplifyCurveToEndpoints,
]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            pass  # 类已经注册，忽略该异常

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except ValueError:
            pass  # 类未注册，忽略该异常

