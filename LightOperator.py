import bpy
import mathutils

class LinkSimilarLights(bpy.types.Operator):
    bl_idname = "object.link_similar_lights"
    bl_label = "关联相似灯光"
    bl_description = "将场景中参数相似的灯光关联起来"
    bl_options = {'REGISTER', 'UNDO'}
    
    tolerance: bpy.props.FloatProperty(
        name="容差值",
        description="相似度判断的容差值",
        default=0.01,
        min=0.0,
        max=1.0
    ) # type: ignore
    
    def compare_lights(self, light1, light2, tolerance):
        """比较两个灯光的参数是否相似"""
        if light1.type != light2.type:
            return False
            
        # 比较基本参数
        if abs(light1.energy - light2.energy) > tolerance * max(1.0, light1.energy):
            return False
            
        if abs(light1.color[0] - light2.color[0]) > tolerance or \
           abs(light1.color[1] - light2.color[1]) > tolerance or \
           abs(light1.color[2] - light2.color[2]) > tolerance:
            return False
            
        # 根据不同灯光类型比较特定参数
        if light1.type == 'POINT':
            if abs(light1.shadow_soft_size - light2.shadow_soft_size) > tolerance * max(0.1, light1.shadow_soft_size):
                return False
                
        elif light1.type == 'SPOT':
            if abs(light1.shadow_soft_size - light2.shadow_soft_size) > tolerance * max(0.1, light1.shadow_soft_size) or \
               abs(light1.spot_size - light2.spot_size) > tolerance * light1.spot_size or \
               abs(light1.spot_blend - light2.spot_blend) > tolerance * max(0.1, light1.spot_blend):
                return False
                
        elif light1.type == 'SUN':
            if abs(light1.angle - light2.angle) > tolerance * max(0.1, light1.angle):
                return False
                
        elif light1.type == 'AREA':
            if light1.shape != light2.shape:
                return False
                
            if abs(light1.size - light2.size) > tolerance * light1.size:
                return False
                
            if light1.shape in ['RECTANGLE', 'ELLIPSE']:
                if abs(light1.size_y - light2.size_y) > tolerance * light1.size_y:
                    return False
        
        return True
    
    def execute(self, context):
        # 获取场景中的所有灯光
        all_lights = [obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']
        
        if len(all_lights) < 2:
            self.report({'WARNING'}, "场景中需要至少两个灯光才能进行关联")
            return {'CANCELLED'}
        
        # 用于跟踪已处理的灯光组
        processed_lights = set()
        light_groups = []
        
        # 分组相似灯光
        for i, light1 in enumerate(all_lights):
            if light1 in processed_lights:
                continue
                
            # 创建一个新组并添加当前灯光
            current_group = [light1]
            processed_lights.add(light1)
            
            # 查找与当前灯光相似的其他灯光
            for light2 in all_lights[i+1:]:
                if light2 not in processed_lights and self.compare_lights(light1.data, light2.data, self.tolerance):
                    current_group.append(light2)
                    processed_lights.add(light2)
            
            # 如果找到多个相似灯光，添加到组列表
            if len(current_group) > 1:
                light_groups.append(current_group)
        
        # 关联每个组中的灯光
        linked_count = 0
        
        for group in light_groups:
            # 获取主灯光（作为源）
            source_light_obj = group[0]
            source_light_data = source_light_obj.data
            
            # 为源灯光创建一个集合来帮助识别
            group_name = f"LightGroup_{source_light_obj.name}"
            if group_name not in bpy.data.collections:
                light_collection = bpy.data.collections.new(group_name)
                bpy.context.scene.collection.children.link(light_collection)
            else:
                light_collection = bpy.data.collections[group_name]
            
            # 将所有灯光添加到集合中
            for light in group:
                if light.name not in light_collection.objects:
                    light_collection.objects.link(light)
            
            # 关联组中其他灯光的数据到源灯光
            for target_light_obj in group[1:]:
                # 保存原始数据链接以防止数据丢失
                original_data = target_light_obj.data
                
                # 关联到源灯光的数据
                target_light_obj.data = source_light_data
                
                # 如果原始数据没有其他用户引用，则删除它
                if original_data.users == 0:
                    bpy.data.lights.remove(original_data)
                
                linked_count += 1
        
        if linked_count > 0:
            self.report({'INFO'}, f"成功关联了 {len(light_groups)} 组灯光，共 {linked_count} 个关联")
        else:
            self.report({'INFO'}, "没有找到需要关联的相似灯光")
            
        return {'FINISHED'}

class AdjustLightIntensity(bpy.types.Operator):
    bl_idname = "object.adjust_light_intensity"
    bl_label = "调整灯光强度"
    bl_description = "将所选灯光的强度乘以指定数值"
    bl_options = {'REGISTER', 'UNDO'}
    
    intensity_multiplier: bpy.props.FloatProperty(
        name="强度倍数",
        description="灯光强度的倍数",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=3
    ) # type: ignore
    
    def execute(self, context):
        # 获取选中的灯光对象
        selected_lights = [obj for obj in context.selected_objects if obj.type == 'LIGHT']
        
        if not selected_lights:
            self.report({'WARNING'}, "请先选择至少一个灯光对象")
            return {'CANCELLED'}
        
        # 调整每个选中灯光的强度
        adjusted_count = 0
        for light_obj in selected_lights:
            light_data = light_obj.data
            # 直接设置为倍数，而不是乘以倍数，避免重复应用导致的天文数字
            light_data.energy = self.intensity_multiplier
            adjusted_count += 1
        
        self.report({'INFO'}, f"已调整 {adjusted_count} 个灯光的强度为: {self.intensity_multiplier}")
        return {'FINISHED'}

class MultiplyLightIntensity(bpy.types.Operator):
    bl_idname = "object.multiply_light_intensity"
    bl_label = "乘以强度倍数"
    bl_description = "将所选灯光的强度乘以指定数值（相对调整）"
    bl_options = {'REGISTER', 'UNDO'}
    
    intensity_multiplier: bpy.props.FloatProperty(
        name="强度倍数",
        description="灯光强度的倍数",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.1,
        soft_max=10.0,
        precision=3
    ) # type: ignore
    
    def execute(self, context):
        # 获取选中的灯光对象
        selected_lights_objects = [obj for obj in context.selected_objects if obj.type == 'LIGHT']
        
        if not selected_lights_objects:
            self.report({'WARNING'}, "请先选择至少一个灯光对象")
            return {'CANCELLED'}
        
        # Collect unique light data blocks to avoid exponential multiplication on linked data
        unique_light_data_blocks = set()
        for light_obj in selected_lights_objects:
            unique_light_data_blocks.add(light_obj.data)

        adjusted_count = 0
        for light_data in unique_light_data_blocks:
            # 确保倍数在合理范围内
            if self.intensity_multiplier > 1000 or self.intensity_multiplier < 0.001:
                self.report({'ERROR'}, f"倍数 {self.intensity_multiplier} 超出安全范围 (0.001-1000)")
                return {'CANCELLED'}
            
            new_energy = light_data.energy * self.intensity_multiplier
            light_data.energy = new_energy
            adjusted_count += 1
        
        self.report({'INFO'}, f"已将 {adjusted_count} 个唯一灯光数据块的强度乘以: {self.intensity_multiplier}")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(LinkSimilarLights)
    bpy.utils.register_class(AdjustLightIntensity)
    bpy.utils.register_class(MultiplyLightIntensity)

def unregister():
    bpy.utils.unregister_class(LinkSimilarLights)
    bpy.utils.unregister_class(AdjustLightIntensity)
    bpy.utils.unregister_class(MultiplyLightIntensity) 