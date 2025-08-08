import bpy
import random

def test_empty_display_size():
    # 清除所有物体
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 创建一些测试物体
    test_objects = []
    
    # 创建几个空物体，设置不同的初始显示尺寸
    for i in range(5):
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(i*2, 0, 0))
        empty_obj = bpy.context.active_object
        empty_obj.name = f"Empty_{i+1}"
        # 设置随机的初始显示尺寸
        empty_obj.empty_display_size = random.uniform(0.5, 3.0)
        test_objects.append(empty_obj)
    
    # 创建一些非空物体（网格、相机等）
    bpy.ops.mesh.primitive_cube_add(location=(0, 3, 0))
    cube = bpy.context.active_object
    cube.name = "TestCube"
    
    bpy.ops.object.camera_add(location=(0, -3, 0))
    camera = bpy.context.active_object
    camera.name = "TestCamera"
    
    print("=== 测试前状态 ===")
    print(f"场景中共有 {len(bpy.context.scene.objects)} 个物体")
    print("空物体的初始显示尺寸:")
    for obj in test_objects:
        print(f"  {obj.name}: {obj.empty_display_size}")
    
    # 选择所有空物体
    bpy.ops.object.select_all(action='DESELECT')
    for obj in test_objects:
        obj.select_set(True)
    
    print(f"\n选中了 {len([obj for obj in bpy.context.selected_objects if obj.type == 'EMPTY'])} 个空物体")
    
    # 设置场景的显示尺寸属性为2.5
    bpy.context.scene.empty_display_size = 2.5
    print(f"设置场景属性 empty_display_size = {bpy.context.scene.empty_display_size}")
    
    # 执行设置空物体显示尺寸的操作
    print("\n=== 执行设置操作 ===")
    bpy.ops.object.set_empty_display_size()
    
    print("\n=== 测试后状态 ===")
    print("空物体的最终显示尺寸:")
    for obj in test_objects:
        print(f"  {obj.name}: {obj.empty_display_size}")
    
    # 验证结果
    expected_size = bpy.context.scene.empty_display_size
    all_correct = True
    for obj in test_objects:
        if abs(obj.empty_display_size - expected_size) > 0.001:
            print(f"错误: {obj.name} 的显示尺寸为 {obj.empty_display_size}, 期望 {expected_size}")
            all_correct = False
    
    if all_correct:
        print(f"\n✅ 测试成功! 所有空物体的显示尺寸都正确设置为 {expected_size}")
    else:
        print("\n❌ 测试失败! 部分空物体的显示尺寸设置不正确")
    
    # 测试不同的显示尺寸值
    print("\n=== 测试不同显示尺寸值 ===")
    test_values = [0.5, 1.0, 2.0, 5.0]
    
    for test_value in test_values:
        print(f"\n测试显示尺寸值: {test_value}")
        bpy.context.scene.empty_display_size = test_value
        
        # 重新选择空物体
        bpy.ops.object.select_all(action='DESELECT')
        for obj in test_objects:
            obj.select_set(True)
        
        # 执行操作
        bpy.ops.object.set_empty_display_size()
        
        # 验证结果
        all_correct = True
        for obj in test_objects:
            if abs(obj.empty_display_size - test_value) > 0.001:
                all_correct = False
                break
        
        if all_correct:
            print(f"✅ 显示尺寸 {test_value} 测试成功")
        else:
            print(f"❌ 显示尺寸 {test_value} 测试失败")

if __name__ == "__main__":
    test_empty_display_size()
