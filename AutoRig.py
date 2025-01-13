# import bpy
# import bmesh
# import random
# from mathutils import Vector
# from collections import defaultdict
# from mathutils.bvhtree import BVHTree
# from mathutils import kdtree


# name_groups = [
#     (["Head", "Neck"], "Face"),
#     (["Spine", "UpperArm", "Forearm", "Hand", "Finger"], "UpperBody"),
#     (["Pelvis",], "Pelvis"),
#     (["Thigh", "Calf",], "LowerBody"),
#     (["Foot", "Toe0",], "Feet")
# ]
# named_group = [
#     {'L Finger11', 'L Finger1'},
#     {'L Finger01', 'L Finger0'},
#     {'L Finger21', 'L Finger2'},
#     {'R Finger11', 'R Finger1'},
#     {'R Finger01', 'R Finger0'},
#     {'R Finger21', 'R Finger2'},
#     {'Pelvis', 'Spine2', 'Spine1', 'Spine'}
# ]

# empty_coords_femal_name_example = [
#     ("R Toe0_example", Vector((-0.0922, -0.1240, 0.0156))),
#     ("R Foot_example", Vector((-0.0938, -0.0028, 0.0340))),
#     ("R Calf_example", Vector((-0.0938, 0.0321, 0.2991))),
#     ("L Toe0_example", Vector((0.0922, -0.1240, 0.0156))),
#     ("L Foot_example", Vector((0.0938, -0.0028, 0.0340))),
#     ("L Calf_example", Vector((0.0938, 0.0321, 0.2991))),
#     ("Spine_example", Vector((0.0000, 0.0270, 1.0378))),
#     ("Spine2_example", Vector((0.0000, 0.0171, 1.2895))),
#     ("Spine1_example", Vector((0.0000, 0.0134, 1.1500))),
#     ("R UpperArm_example", Vector((-0.2765, 0.0021, 1.3281))),
#     ("R Thigh_example", Vector((-0.0952, 0.0234, 0.6991))),
#     ("R Hand_example", Vector((-0.6875, 0.0076, 1.3359))),
#     ("R Forearm_example", Vector((-0.5391, 0.0076, 1.3359))),
#     ("R Finger2_example", Vector((-0.7500, 0.0232, 1.3438))),
#     ("R Finger21_example", Vector((-0.7878, 0.0212, 1.3438))),
#     ("R Finger1_example", Vector((-0.7500, -0.0237, 1.3438))),
#     ("R Finger11_example", Vector((-0.7891, -0.0237, 1.3438))),
#     ("R Finger0_example", Vector((-0.7109, -0.0471, 1.3125))),
#     ("R Finger01_example", Vector((-0.7422, -0.0471, 1.3125))),
#     ("Pelvis_example", Vector((0.0000, 0.0306, 0.9380))),
#     ("L UpperArm_example", Vector((0.2765, 0.0021, 1.3281))),
#     ("L Thigh_example", Vector((0.0952, 0.0234, 0.6991))),
#     ("L Hand_example", Vector((0.6875, 0.0076, 1.3359))),
#     ("L Forearm_example", Vector((0.5391, 0.0076, 1.3359))),
#     ("L Finger2_example", Vector((0.7500, 0.0232, 1.3438))),
#     ("L Finger21_example", Vector((0.7891, 0.0284, 1.3438))),
#     ("L Finger1_example", Vector((0.7500, -0.0237, 1.3438))),
#     ("L Finger11_example", Vector((0.7891, -0.0237, 1.3438))),
#     ("L Finger0_example", Vector((0.7109, -0.0471, 1.3125))),
#     ("L Finger01_example", Vector((0.7422, -0.0471, 1.3125))),
#     ("Neck_example", Vector((0.0000, 0.0156, 1.4141))),
#     ("Head_example", Vector((0.0000, 0.0020, 1.5260))),
# ]
# empty_coords_femal_name_example_comb = [

#     ("Feet_example", Vector((-0.0938, -0.0028, 0.0340))),
#     ("UpperBody_example", Vector((-0.0006, 0.0136, 1.2599))),
#     ("Face_example", Vector((0.0000, 0.0020, 1.5260))),
#     ("LowerBody_example", Vector((-0.0952, 0.0234, 0.6991))),

# ]
# femal_bone_data = {
# "origin": Vector((0.0,0.030188,0.90654)), # 添加这个键来定义骨架的原点位置,模板骨骼记住要应用掉旋转信息再进行输出数据
# "Bip001 Pelvis": {"parent": None, "head": Vector((0.0000, 0.0000, 0.0000)), "tail": Vector((0.0000, -0.0961, -0.0000))},
# "Bip001 Spine": {"parent": "Bip001 Pelvis", "head": Vector((0.0000, 0.0001, 0.0845)), "tail": Vector((-0.0000, -0.1256, 0.0844))},
# "Bip001 Spine1": {"parent": "Bip001 Spine", "head": Vector((0.0000, 0.0001, 0.2102)), "tail": Vector((0.0000, -0.0750, 0.2102))},
# "Bip001 Spine2": {"parent": "Bip001 Spine1", "head": Vector((0.0000, 0.0001, 0.2853)), "tail": Vector((0.0000, -0.1686, 0.2851))},
# "Bip001 Neck": {"parent": "Bip001 Spine2", "head": Vector((0.0000, 0.0000, 0.4711)), "tail": Vector((0.0000, -0.0499, 0.4711))},
# "Bip001 Head": {"parent": "Bip001 Neck", "head": Vector((0.0000, -0.0000, 0.5211)), "tail": Vector((0.0000, -0.3177, 0.5211))},
# "Bip001 HeadNub": {"parent": "Bip001 Head", "head": Vector((0.0000, -0.0000, 0.8388)), "tail": Vector((0.0000, -0.3177, 0.8388))},
# "Bip001 L Clavicle": {"parent": "Bip001 Spine2", "head": Vector((0.0797, -0.0243, 0.4220)), "tail": Vector((0.0797, 0.0301, 0.4220))},
# "Bip001 L UpperArm": {"parent": "Bip001 L Clavicle", "head": Vector((0.1341, -0.0243, 0.4220)), "tail": Vector((0.1248, 0.2699, 0.4513))},
# "Bip001 L Forearm": {"parent": "Bip001 L UpperArm", "head": Vector((0.4297, -0.0154, 0.4269)), "tail": Vector((0.4376, 0.2030, 0.4489))},
# "Bip001 L Hand": {"parent": "Bip001 L Forearm", "head": Vector((0.6492, -0.0236, 0.4291)), "tail": Vector((0.6503, -0.0156, 0.3492))},
# "Bip001 L Finger0": {"parent": "Bip001 L Hand", "head": Vector((0.6986, -0.0764, 0.4077)), "tail": Vector((0.6985, -0.0764, 0.3787))},
# "Bip001 L Finger01": {"parent": "Bip001 L Finger0", "head": Vector((0.7276, -0.0775, 0.4076)), "tail": Vector((0.7275, -0.0775, 0.3803))},
# "Bip001 L Finger0Nub": {"parent": "Bip001 L Finger01", "head": Vector((0.7549, -0.0785, 0.4075)), "tail": Vector((0.7547, -0.0785, 0.3802))},
# "Bip001 L Finger1": {"parent": "Bip001 L Hand", "head": Vector((0.7272, -0.0579, 0.4327)), "tail": Vector((0.7276, -0.0579, 0.3867))},
# "Bip001 L Finger11": {"parent": "Bip001 L Finger1", "head": Vector((0.7732, -0.0582, 0.4331)), "tail": Vector((0.7734, -0.0582, 0.4043))},
# "Bip001 L Finger1Nub": {"parent": "Bip001 L Finger11", "head": Vector((0.8020, -0.0583, 0.4334)), "tail": Vector((0.8022, -0.0583, 0.4046))},
# "Bip001 L Finger2": {"parent": "Bip001 L Hand", "head": Vector((0.7283, -0.0096, 0.4336)), "tail": Vector((0.7287, -0.0096, 0.3890))},
# "Bip001 L Finger21": {"parent": "Bip001 L Finger2", "head": Vector((0.7729, -0.0106, 0.4341)), "tail": Vector((0.7732, -0.0106, 0.4043))},
# "Bip001 L Finger2Nub": {"parent": "Bip001 L Finger21", "head": Vector((0.8027, -0.0113, 0.4343)), "tail": Vector((0.8030, -0.0113, 0.4046))},
# "Bip001 R Clavicle": {"parent": "Bip001 Spine2", "head": Vector((-0.0797, -0.0243, 0.4220)), "tail": Vector((-0.0797, 0.0301, 0.4220))},
# "Bip001 R UpperArm": {"parent": "Bip001 R Clavicle", "head": Vector((-0.1341, -0.0243, 0.4220)), "tail": Vector((-0.1248, 0.2699, 0.4513))},
# "Bip001 R Forearm": {"parent": "Bip001 R UpperArm", "head": Vector((-0.4297, -0.0154, 0.4269)), "tail": Vector((-0.4376, 0.2030, 0.4489))},
# "Bip001 R Hand": {"parent": "Bip001 R Forearm", "head": Vector((-0.6492, -0.0236, 0.4291)), "tail": Vector((-0.6503, -0.0156, 0.3492))},
# "Bip001 R Finger0": {"parent": "Bip001 R Hand", "head": Vector((-0.6986, -0.0764, 0.4077)), "tail": Vector((-0.6985, -0.0764, 0.3787))},
# "Bip001 R Finger01": {"parent": "Bip001 R Finger0", "head": Vector((-0.7276, -0.0775, 0.4076)), "tail": Vector((-0.7275, -0.0775, 0.3803))},
# "Bip001 R Finger0Nub": {"parent": "Bip001 R Finger01", "head": Vector((-0.7549, -0.0785, 0.4075)), "tail": Vector((-0.7547, -0.0785, 0.3802))},
# "Bip001 R Finger1": {"parent": "Bip001 R Hand", "head": Vector((-0.7272, -0.0579, 0.4327)), "tail": Vector((-0.7276, -0.0579, 0.3867))},
# "Bip001 R Finger11": {"parent": "Bip001 R Finger1", "head": Vector((-0.7732, -0.0582, 0.4331)), "tail": Vector((-0.7734, -0.0582, 0.4043))},
# "Bip001 R Finger1Nub": {"parent": "Bip001 R Finger11", "head": Vector((-0.8020, -0.0583, 0.4334)), "tail": Vector((-0.8022, -0.0583, 0.4046))},
# "Bip001 R Finger2": {"parent": "Bip001 R Hand", "head": Vector((-0.7283, -0.0096, 0.4336)), "tail": Vector((-0.7287, -0.0096, 0.3890))},
# "Bip001 R Finger21": {"parent": "Bip001 R Finger2", "head": Vector((-0.7729, -0.0106, 0.4341)), "tail": Vector((-0.7732, -0.0106, 0.4043))},
# "Bip001 R Finger2Nub": {"parent": "Bip001 R Finger21", "head": Vector((-0.8027, -0.0113, 0.4343)), "tail": Vector((-0.8030, -0.0113, 0.4046))},
# "Bip001 L Thigh": {"parent": "Bip001 Pelvis", "head": Vector((0.1019, -0.0000, -0.0000)), "tail": Vector((0.1023, -0.4083, 0.0311))},
# "Bip001 L Calf": {"parent": "Bip001 L Thigh", "head": Vector((0.0968, -0.0311, -0.4083)), "tail": Vector((0.0964, -0.4555, -0.4412))},
# "Bip001 L Foot": {"parent": "Bip001 L Calf", "head": Vector((0.0915, 0.0018, -0.8326)), "tail": Vector((0.0915, -0.1496, -0.8326))},
# "Bip001 L Toe0": {"parent": "Bip001 L Foot", "head": Vector((0.0915, -0.1309, -0.9054)), "tail": Vector((0.0915, -0.1309, -0.8851))},
# "Bip001 L Toe0Nub": {"parent": "Bip001 L Toe0", "head": Vector((0.0915, -0.1512, -0.9054)), "tail": Vector((0.0915, -0.1512, -0.8851))},
# "Bip001 R Thigh": {"parent": "Bip001 Pelvis", "head": Vector((-0.1019, -0.0000, 0.0000)), "tail": Vector((-0.1023, -0.4083, 0.0311))},
# "Bip001 R Calf": {"parent": "Bip001 R Thigh", "head": Vector((-0.0968, -0.0311, -0.4083)), "tail": Vector((-0.0964, -0.4555, -0.4412))},
# "Bip001 R Foot": {"parent": "Bip001 R Calf", "head": Vector((-0.0915, 0.0018, -0.8326)), "tail": Vector((-0.0915, -0.1496, -0.8326))},
# "Bip001 R Toe0": {"parent": "Bip001 R Foot", "head": Vector((-0.0915, -0.1309, -0.9054)), "tail": Vector((-0.0915, -0.1309, -0.8851))},
# "Bip001 R Toe0Nub": {"parent": "Bip001 R Toe0", "head": Vector((-0.0915, -0.1512, -0.9054)), "tail": Vector((-0.0915, -0.1512, -0.8851))},

# }

# empty_coords_male_name_example = [
#     ("R Toe0_example", Vector((-0.0922, -0.1240, 0.0156))),
#     ("R Foot_example", Vector((-0.0938, 0.0124, 0.0340))),
#     ("R Calf_example", Vector((-0.0938, 0.0110, 0.2991))),
#     ("L Toe0_example", Vector((0.0922, -0.1240, 0.0156))),
#     ("L Foot_example", Vector((0.0938, 0.0124, 0.0340))),
#     ("L Calf_example", Vector((0.0938, 0.0110, 0.2991))),
#     ("Spine_example", Vector((0.0000, 0.0270, 1.0378))),
#     ("Spine2_example", Vector((0.0000, 0.0171, 1.2895))),
#     ("Spine1_example", Vector((0.0000, 0.0134, 1.1500))),
#     ("R UpperArm_example", Vector((-0.3006, 0.0021, 1.4002))),
#     ("R Thigh_example", Vector((-0.0952, 0.0023, 0.6991))),
#     ("R Hand_example", Vector((-0.7474, 0.0076, 1.4080))),
#     ("R Forearm_example", Vector((-0.5861, 0.0076, 1.4080))),
#     ("R Finger2_example", Vector((-0.8154, 0.0232, 1.4158))),
#     ("R Finger21_example", Vector((-0.8565, 0.0212, 1.4158))),
#     ("R Finger1_example", Vector((-0.8154, -0.0237, 1.4158))),
#     ("R Finger11_example", Vector((-0.8579, -0.0237, 1.4158))),
#     ("R Finger0_example", Vector((-0.7729, -0.0471, 1.3846))),
#     ("R Finger01_example", Vector((-0.8069, -0.0471, 1.3846))),
#     ("Pelvis_example", Vector((0.0000, 0.0306, 0.9380))),
#     ("L UpperArm_example", Vector((0.3006, 0.0021, 1.4002))),
#     ("L Thigh_example", Vector((0.0952, 0.0023, 0.6991))),
#     ("L Hand_example", Vector((0.7474, 0.0076, 1.4080))),
#     ("L Forearm_example", Vector((0.5861, 0.0076, 1.4080))),
#     ("L Finger2_example", Vector((0.8154, 0.0232, 1.4158))),
#     ("L Finger21_example", Vector((0.8579, 0.0284, 1.4158))),
#     ("L Finger1_example", Vector((0.8154, -0.0237, 1.4158))),
#     ("L Finger11_example", Vector((0.8579, -0.0237, 1.4158))),
#     ("L Finger0_example", Vector((0.7729, -0.0471, 1.3846))),
#     ("L Finger01_example", Vector((0.8069, -0.0471, 1.3846))),
#     ("Neck_example", Vector((0.0000, 0.0156, 1.4677))),
#     ("Head_example", Vector((0.0000, 0.0020, 1.5260))),

# ]
# empty_coords_male_name_example_comb = [

#     ("Feet_example", Vector((-0.0938, 0.0124, 0.0340))),
#     ("UpperBody_example", Vector((-0.0006, 0.0136, 1.2599))),
#     ("Face_example", Vector((0.0000, 0.0020, 1.5260))),
#     ("LowerBody_example", Vector((-0.0952, 0.0023, 0.6991))),

# ]
# male_bone_data = {
#     "origin": Vector((0.0,0.016025, 0.878018)), # 添加这个键来定义骨架的原点位置
#     "Bip001 Pelvis": {"parent": None, "head": Vector((0.0000, 0.0000, 0.0000)), "tail": Vector((0.0000, -0.1038, -0.0000))},
#     "Bip001 Spine": {"parent": "Bip001 Pelvis", "head": Vector((0.0000, 0.0001, 0.1077)), "tail": Vector((-0.0000, -0.1256, 0.1076))},
#     "Bip001 Spine1": {"parent": "Bip001 Spine", "head": Vector((0.0000, 0.0001, 0.2334)), "tail": Vector((0.0000, -0.1299, 0.2334))},
#     "Bip001 Spine2": {"parent": "Bip001 Spine1", "head": Vector((0.0000, 0.0002, 0.3635)), "tail": Vector((0.0000, -0.1855, 0.3633))},
#     "Bip001 Neck": {"parent": "Bip001 Spine2", "head": Vector((0.0000, 0.0001, 0.5589)), "tail": Vector((0.0000, -0.0655, 0.5589))},
#     "Bip001 Head": {"parent": "Bip001 Neck", "head": Vector((0.0000, -0.0000, 0.6245)), "tail": Vector((0.0000, -0.3177, 0.6245))},
#     "Bip001 HeadNub": {"parent": "Bip001 Head", "head": Vector((0.0000, -0.0000, 0.9422)), "tail": Vector((0.0000, -0.3177, 0.9422))},
#     "Bip001 L Clavicle": {"parent": "Bip001 Spine2", "head": Vector((0.0797, -0.0082, 0.5256)), "tail": Vector((0.0797, 0.0777, 0.5256))},
#     "Bip001 L UpperArm": {"parent": "Bip001 L Clavicle", "head": Vector((0.1657, -0.0082, 0.5256)), "tail": Vector((0.1559, 0.3003, 0.5563))},
#     "Bip001 L Forearm": {"parent": "Bip001 L UpperArm", "head": Vector((0.4757, 0.0011, 0.5307)), "tail": Vector((0.4843, 0.2361, 0.5543))},
#     "Bip001 L Hand": {"parent": "Bip001 L Forearm", "head": Vector((0.7119, -0.0078, 0.5330)), "tail": Vector((0.7130, 0.0002, 0.4536))},
#     "Bip001 L Finger0": {"parent": "Bip001 L Hand", "head": Vector((0.7608, -0.0587, 0.5116)), "tail": Vector((0.7607, -0.0587, 0.4826))},
#     "Bip001 L Finger01": {"parent": "Bip001 L Finger0", "head": Vector((0.7899, -0.0598, 0.5115)), "tail": Vector((0.7897, -0.0598, 0.4843))},
#     "Bip001 L Finger0Nub": {"parent": "Bip001 L Finger01", "head": Vector((0.8171, -0.0608, 0.5114)), "tail": Vector((0.8170, -0.0608, 0.4841))},
#     "Bip001 L Finger1": {"parent": "Bip001 L Hand", "head": Vector((0.7899, -0.0421, 0.5366)), "tail": Vector((0.7903, -0.0421, 0.4906))},
#     "Bip001 L Finger11": {"parent": "Bip001 L Finger1", "head": Vector((0.8359, -0.0423, 0.5371)), "tail": Vector((0.8362, -0.0423, 0.5083))},
#     "Bip001 L Finger1Nub": {"parent": "Bip001 L Finger11", "head": Vector((0.8647, -0.0424, 0.5373)), "tail": Vector((0.8649, -0.0424, 0.5085))},
#     "Bip001 L Finger2": {"parent": "Bip001 L Hand", "head": Vector((0.7910, 0.0062, 0.5376)), "tail": Vector((0.7914, 0.0062, 0.4929))},
#     "Bip001 L Finger21": {"parent": "Bip001 L Finger2", "head": Vector((0.8356, 0.0052, 0.5380)), "tail": Vector((0.8359, 0.0052, 0.5082))},
#     "Bip001 L Finger2Nub": {"parent": "Bip001 L Finger21", "head": Vector((0.8654, 0.0046, 0.5383)), "tail": Vector((0.8657, 0.0046, 0.5085))},
#     "Bip001 R Clavicle": {"parent": "Bip001 Spine2", "head": Vector((-0.0797, -0.0082, 0.5256)), "tail": Vector((-0.0797, 0.0777, 0.5256))},
#     "Bip001 R UpperArm": {"parent": "Bip001 R Clavicle", "head": Vector((-0.1657, -0.0082, 0.5256)), "tail": Vector((-0.1559, 0.3003, 0.5563))},
#     "Bip001 R Forearm": {"parent": "Bip001 R UpperArm", "head": Vector((-0.4757, 0.0011, 0.5307)), "tail": Vector((-0.4843, 0.2361, 0.5543))},
#     "Bip001 R Hand": {"parent": "Bip001 R Forearm", "head": Vector((-0.7119, -0.0078, 0.5330)), "tail": Vector((-0.7130, 0.0002, 0.4536))},
#     "Bip001 R Finger0": {"parent": "Bip001 R Hand", "head": Vector((-0.7608, -0.0587, 0.5116)), "tail": Vector((-0.7607, -0.0587, 0.4826))},
#     "Bip001 R Finger01": {"parent": "Bip001 R Finger0", "head": Vector((-0.7899, -0.0598, 0.5115)), "tail": Vector((-0.7897, -0.0598, 0.4843))},
#     "Bip001 R Finger0Nub": {"parent": "Bip001 R Finger01", "head": Vector((-0.8171, -0.0608, 0.5114)), "tail": Vector((-0.8170, -0.0608, 0.4841))},
#     "Bip001 R Finger1": {"parent": "Bip001 R Hand", "head": Vector((-0.7899, -0.0421, 0.5366)), "tail": Vector((-0.7903, -0.0421, 0.4906))},
#     "Bip001 R Finger11": {"parent": "Bip001 R Finger1", "head": Vector((-0.8359, -0.0423, 0.5371)), "tail": Vector((-0.8362, -0.0423, 0.5083))},
#     "Bip001 R Finger1Nub": {"parent": "Bip001 R Finger11", "head": Vector((-0.8647, -0.0424, 0.5373)), "tail": Vector((-0.8649, -0.0424, 0.5085))},
#     "Bip001 R Finger2": {"parent": "Bip001 R Hand", "head": Vector((-0.7910, 0.0062, 0.5376)), "tail": Vector((-0.7914, 0.0062, 0.4929))},
#     "Bip001 R Finger21": {"parent": "Bip001 R Finger2", "head": Vector((-0.8356, 0.0052, 0.5380)), "tail": Vector((-0.8359, 0.0052, 0.5082))},
#     "Bip001 R Finger2Nub": {"parent": "Bip001 R Finger21", "head": Vector((-0.8654, 0.0046, 0.5383)), "tail": Vector((-0.8657, 0.0046, 0.5085))},
#     "Bip001 L Thigh": {"parent": "Bip001 Pelvis", "head": Vector((0.1019, -0.0000, -0.0000)), "tail": Vector((0.1023, -0.3769, 0.0318))},
#     "Bip001 L Calf": {"parent": "Bip001 L Thigh", "head": Vector((0.0967, -0.0318, -0.3768)), "tail": Vector((0.0963, -0.4565, -0.4062))},
#     "Bip001 L Foot": {"parent": "Bip001 L Calf", "head": Vector((0.0908, -0.0024, -0.8014)), "tail": Vector((0.0908, -0.1631, -0.8014))},
#     "Bip001 L Toe0": {"parent": "Bip001 L Foot", "head": Vector((0.0908, -0.1442, -0.8770)), "tail": Vector((0.0908, -0.1442, -0.8567))},
#     "Bip001 L Toe0Nub": {"parent": "Bip001 L Toe0", "head": Vector((0.0908, -0.1645, -0.8770)), "tail": Vector((0.0908, -0.1645, -0.8567))},
#     "Bip001 R Thigh": {"parent": "Bip001 Pelvis", "head": Vector((-0.1019, -0.0000, 0.0000)), "tail": Vector((-0.1023, -0.3769, 0.0318))},
#     "Bip001 R Calf": {"parent": "Bip001 R Thigh", "head": Vector((-0.0967, -0.0318, -0.3768)), "tail": Vector((-0.0963, -0.4565, -0.4062))},
#     "Bip001 R Foot": {"parent": "Bip001 R Calf", "head": Vector((-0.0908, -0.0024, -0.8014)), "tail": Vector((-0.0908, -0.1631, -0.8014))},
#     "Bip001 R Toe0": {"parent": "Bip001 R Foot", "head": Vector((-0.0908, -0.1442, -0.8770)), "tail": Vector((-0.0908, -0.1442, -0.8567))},
#     "Bip001 R Toe0Nub": {"parent": "Bip001 R Toe0", "head": Vector((-0.0908, -0.1645, -0.8770)), "tail": Vector((-0.0908, -0.1645, -0.8567))},
# }

# def get_top_parent(obj):
#     while obj.parent is not None:
#         obj = obj.parent
#     return obj if obj else None

# def create_parent_dict(name_list):
#     top_parents = {}
#     for obj in bpy.context.scene.objects:
#         if obj.type == 'MESH' and any(name in obj.name for name in name_list):
#             top_parent = get_top_parent(obj)
#             if top_parent is None:
#                 top_parent = obj
#             if top_parent not in top_parents:
#                 top_parents[top_parent] = []
#             top_parents[top_parent].append(obj)
#     return top_parents

# def join_objects(parent_dict, new_name):
#     for top_parent, objects in parent_dict.items():
#         if len(objects) <= 1:
#             continue

#         # 确保所有对象都在 OBJECT 模式下
#         if bpy.context.mode != 'OBJECT':
#             bpy.ops.object.mode_set(mode='OBJECT')

#         bpy.ops.object.select_all(action='DESELECT')
#         for obj in objects:
#             obj.select_set(True)

#         if bpy.context.selected_objects:
#             # 设置第一个选中的对象为活动对象
#             bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
#             bpy.ops.object.join()

#         bpy.context.object.name = new_name

# def filter_objects_by_name_patterns(objects, name_patterns):
#     filtered_objects = []
#     for obj in objects:
#         if obj.type == 'MESH' and any(name_pattern in obj.name for name_pattern in name_patterns):
#             filtered_objects.append(obj)
#     return filtered_objects

# def rename_all_children_based_on_coords(empty_coords):
#         objects_bvh = {}

#         def create_bvh_tree(obj):
#             bm = bmesh.new()
#             bm.from_object(obj, bpy.context.evaluated_depsgraph_get())
#             bmesh.ops.transform(bm, verts=bm.verts, matrix=obj.matrix_world)
#             bvh = BVHTree.FromBMesh(bm)
#             bm.free()
#             return bvh

#         for obj in bpy.context.scene.objects:
#             if obj.type == 'MESH':
#                 objects_bvh[obj] = create_bvh_tree(obj)

#         renamed_objects = {}

#         for name, coord in empty_coords:
#             intersection_count = defaultdict(int)

#             for other_obj, bvh in objects_bvh.items():
#                 ray_origin = coord
#                 ray_direction = Vector((0, 0, -1))

#                 hit, _, _, _ = bvh.ray_cast(ray_origin, ray_direction)
#                 while hit:
#                     intersection_count[other_obj] += 1
#                     hit += ray_direction * 0.00001
#                     hit, _, _, _ = bvh.ray_cast(hit, ray_direction)

#             for other_obj, count in intersection_count.items():
#                 if count % 2 == 1:
#                     new_name = name.replace("_example", "")
#                     if other_obj not in renamed_objects:
#                         other_obj.name = new_name
#                         renamed_objects[other_obj] = True

# def process_contact_weights():
#     threshold_distance = bpy.context.scene.threshold_distance
#     if bpy.context.scene.assign_contact_weights:
#         print("Processing contact weights...")
#         all_objects = bpy.context.scene.objects
#         for name_patterns in named_group:
#             group_objects = filter_objects_by_name_patterns(all_objects, name_patterns)
#             create_contact_vertex_groups(group_objects, threshold_distance)
#         pass
#     else:
#         print("Skipping contact weight assignment...")

# def create_contact_vertex_groups(input_objects, threshold_distance):
#     objects = {obj.name: obj for obj in input_objects}

#     kdtrees = {}
#     bm_objects = {}
#     for obj_name, obj in objects.items():
#         bm_objects[obj_name] = bmesh.new()
#         bm_objects[obj_name].from_mesh(obj.data)
#         kdtrees[obj_name] = kdtree.KDTree(len(bm_objects[obj_name].verts))
#         for i, v in enumerate(bm_objects[obj_name].verts):
#             kdtrees[obj_name].insert(obj.matrix_world @ v.co, i)
#         kdtrees[obj_name].balance()

#     vertex_groups = defaultdict(dict)

#     for obj_a in input_objects:
#         obj_a_name = obj_a.name
#         for obj_b in input_objects:
#             if obj_a != obj_b:
#                 group_name = f'Bip001 {obj_b.name}'
#                 vertex_groups[obj_a][obj_b] = (obj_a.vertex_groups.new(name=group_name)
#                                             if group_name not in obj_a.vertex_groups else
#                                             obj_a.vertex_groups[group_name])

#     for obj_a in input_objects:
#         obj_a_name = obj_a.name
#         bm_a = bm_objects[obj_a_name]
#         kd_tree_a = kdtrees[obj_a_name]
#         for obj_b in input_objects:
#             if obj_a != obj_b:
#                 kd_tree_b = kdtrees[obj_b.name]
#                 vertex_group = vertex_groups[obj_a][obj_b]
#                 for i, v in enumerate(bm_a.verts):
#                     global_v_co = obj_a.matrix_world @ v.co
#                     closest_co, closest_index, dist = kd_tree_b.find(global_v_co)
#                     if dist < threshold_distance:
#                         weight = 1.0 - dist / threshold_distance
#                         vertex_group.add([v.index], weight, 'REPLACE')

#     for bm in bm_objects.values():
#         bm.free()

#     for obj in input_objects:
#         obj.data.update()

#     print("Contact weights assigned for all object combinations, and self vertex groups created with full weight.")

# class CharOperater(bpy.types.Operator):
#     bl_idname = "object.miao_char_operater"
#     bl_label = "角色一键处理"
    
#     def apply_transforms_recursive(self, obj):
#         obj.select_set(True)
#         bpy.context.view_layer.objects.active = obj
#         bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
#         obj.select_set(False)

#         if obj.children:
#             for child in obj.children:
#                 self.apply_transforms_recursive(child)

#     def execute(self, context):
#         print("开始处理顶点")
#         bpy.ops.object.vox_operation()
#         print("开始处理碰撞")
#         bpy.ops.object.miao_parent_byboundingbox()

#         def apply_change_to_scene():
#             def set_material_to_objects(objects, material):
#                 for obj in objects:
#                     if len(obj.data.materials):
#                         obj.data.materials[0] = material
#                     else:
#                         obj.data.materials.append(material)

#             top_level_parents = [obj for obj in bpy.data.objects if obj.parent is None and 'example' not in obj.name.lower()]

#             for parent_obj in top_level_parents:
#                 parent_obj.scale *= 0.5
#                 parent_obj.location = (0, 0, 0)

#                 if parent_obj.children:
#                     children_with_materials = [child for child in parent_obj.children if len(child.data.materials) > 0]
#                     if children_with_materials:
#                         child_with_random_material = random.choice(children_with_materials)
#                         random_material = child_with_random_material.data.materials[0]
#                         set_material_to_objects(parent_obj.children, random_material)
    
#         apply_change_to_scene()

#         for parent_obj in bpy.context.scene.objects:
#             if parent_obj.parent is None:
#                 self.apply_transforms_recursive(parent_obj)
        
#         bpy.ops.object.select_all(action='DESELECT')

#         return {'FINISHED'}

# class FemaleCharOperaterBone(bpy.types.Operator):
#     bl_idname = "object.char_operater_bone_weight"
#     bl_label = "女性骨骼绑定"

#     def execute(self, context):
#         def create_femal_armature_with_bones(armature_name, femal_bone_data):
#             # 获取骨架的起始位置

#             origin = femal_bone_data.get("origin", Vector((0.0, 0.0, 0.0)))
#             # 获取当前场景中所有对象的列表
#             all_objects = bpy.data.objects

#             # 确保列表中有对象
#             if all_objects:
#                 # 选择任意对象，这里使用第一个对象
#                 first_object = all_objects[0]
                
#                 # 设置此对象为活动对象
#                 bpy.context.view_layer.objects.active = first_object
                
#                 # 确保对象被选中
#                 first_object.select_set(True)

#                 # 现在可以执行如切换模式的操作
#                 bpy.ops.object.mode_set(mode='OBJECT')
#                 bpy.ops.object.select_all(action='SELECT')

#             # 设置正确的上下文和模式
#             bpy.ops.object.mode_set(mode='OBJECT')
#             bpy.ops.object.select_all(action='SELECT')

#             # 创建骨架
#             bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
#             armature = bpy.context.object
#             armature.name = armature_name

#             armature_data = armature.data
#             armature_data.name = armature_name

#             edit_bones = armature_data.edit_bones

#             # 删除默认添加的骨骼
#             default_bone = edit_bones.get('Bone')
#             if default_bone:
#                 edit_bones.remove(default_bone)

#             default_bone = edit_bones.get('骨骼')
#             if default_bone:
#                 edit_bones.remove(default_bone)


#             created_bones = {}

#             for bone_name, data in femal_bone_data.items():
#                 if bone_name == "origin":
#                     continue  # 跳过 "origin" 键
#                 new_bone = edit_bones.new(name=bone_name)
#                 new_bone.head = data['head'] + origin
#                 new_bone.tail = data['tail'] + origin
#                 created_bones[bone_name] = new_bone

#             # 设置父子关系
#             for bone_name, data in femal_bone_data.items():
#                 if bone_name == "origin":
#                     continue  # 跳过 "origin" 键
#                 if data['parent']:
#                     created_bone = created_bones[bone_name]
#                     parent_bone = created_bones[data['parent']]
#                     created_bone.parent = parent_bone


#             return armature

#         def duplicate_bones_to_objects():
#             # 先删除命名为 "BOX" 的物体
#             boxes_to_delete = [obj for obj in bpy.data.objects if obj.name.startswith("BOX")]
#             bpy.ops.object.select_all(action='DESELECT')
#             for box in boxes_to_delete:
#                 box.select_set(True)
#             bpy.ops.object.delete()

#             scene_objects = bpy.data.objects

#             for object in scene_objects:
#                 if object.parent is None:
#                     # 创建一个新的骨架并为每个顶级父对象命名
#                     armature_name = f'{object.name}_armature'
#                     armature = create_femal_armature_with_bones(armature_name, femal_bone_data)

#                     collection = object.users_collection[0]

#                     # 检查集合中是否已经包含了这个 armature
#                     if armature.name not in collection.objects:
#                         collection.objects.link(armature)

#                     armature.matrix_world = object.matrix_world

#                     armature.parent = object

#                     for child_obj in object.children:
#                         if child_obj.type == 'MESH':
#                             bone_name = "Bip001 " + child_obj.name.split('.')[0]

#                             modifier = child_obj.modifiers.new(name='ArmatureMod', type='ARMATURE')
#                             modifier.object = armature
#                             modifier.use_vertex_groups = True

#                             group = child_obj.vertex_groups.new(name=bone_name)
#                             for v in child_obj.data.vertices:
#                                 group.add([v.index], 1.0, 'ADD')
        
#         bpy.ops.object.miao_clean_sense()
#         rename_all_children_based_on_coords(empty_coords_femal_name_example)

#         process_contact_weights()
#         duplicate_bones_to_objects()
#         parent_dict_list = [(create_parent_dict(name_list), new_name) for name_list, new_name in name_groups]
#         for parent_dict, new_name in parent_dict_list:
#             join_objects(parent_dict, new_name)
#         rename_all_children_based_on_coords(empty_coords_femal_name_example_comb)

#         return {'FINISHED'}

# class MaleCharOperaterBone(bpy.types.Operator):
#     bl_idname = "object.char_operater_male_bone_weight"
#     bl_label = "男性骨骼绑定"

#     def execute(self, context):
#         def create_male_armature_with_bones(armature_name, male_bone_data):
#             # 获取骨架的起始位置
#             # origin = femal_bone_data.get("origin", Vector((0.0, 0.030188, 0.914863)))

#             origin = male_bone_data.get("origin", Vector((0.0, 0.0, 0.0)))

#             all_objects = bpy.data.objects

#             # 确保列表中有对象
#             if all_objects:
#                 # 选择任意对象，这里使用第一个对象
#                 first_object = all_objects[0]
                
#                 # 设置此对象为活动对象
#                 bpy.context.view_layer.objects.active = first_object
                
#                 # 确保对象被选中
#                 first_object.select_set(True)

#                 # 现在可以执行如切换模式的操作
#                 bpy.ops.object.mode_set(mode='OBJECT')
#                 bpy.ops.object.select_all(action='SELECT')

#             # 创建骨架
#             bpy.ops.object.armature_add(enter_editmode=True, location=(0,0,0))
#             armature = bpy.context.object
#             armature.name = armature_name

#             armature_data = armature.data
#             armature_data.name = armature_name

#             edit_bones = armature_data.edit_bones

#             # 删除默认添加的骨骼
#             default_bone = edit_bones.get('Bone')
#             if default_bone:
#                 edit_bones.remove(default_bone)

#             default_bone = edit_bones.get('骨骼')
#             if default_bone:
#                 edit_bones.remove(default_bone)


#             created_bones = {}

#             for bone_name, data in male_bone_data.items():
#                 if bone_name == "origin":
#                     continue  # 跳过 "origin" 键
#                 new_bone = edit_bones.new(name=bone_name)
#                 new_bone.head = data['head'] + origin
#                 new_bone.tail = data['tail'] + origin
#                 created_bones[bone_name] = new_bone

#             # 设置父子关系
#             for bone_name, data in male_bone_data.items():
#                 if bone_name == "origin":
#                     continue  # 跳过 "origin" 键
#                 if data['parent']:
#                     created_bone = created_bones[bone_name]
#                     parent_bone = created_bones[data['parent']]
#                     created_bone.parent = parent_bone


#             return armature

#         def duplicate_bones_to_objects():
#             # 先删除命名为 "BOX" 的物体
#             boxes_to_delete = [obj for obj in bpy.data.objects if obj.name.startswith("BOX")]
#             bpy.ops.object.select_all(action='DESELECT')
#             for box in boxes_to_delete:
#                 box.select_set(True)
#             bpy.ops.object.delete()

#             scene_objects = bpy.data.objects

#             for object in scene_objects:
#                 if object.parent is None:
#                     # 创建一个新的骨架并为每个顶级父对象命名
#                     armature_name = f'{object.name}_armature'
#                     armature = create_male_armature_with_bones(armature_name, male_bone_data)

#                     collection = object.users_collection[0]

#                     # 检查集合中是否已经包含了这个 armature
#                     if armature.name not in collection.objects:
#                         collection.objects.link(armature)

#                     armature.matrix_world = object.matrix_world

#                     armature.parent = object

#                     for child_obj in object.children:
#                         if child_obj.type == 'MESH':
#                             bone_name = "Bip001 " + child_obj.name.split('.')[0]

#                             modifier = child_obj.modifiers.new(name='ArmatureMod', type='ARMATURE')
#                             modifier.object = armature
#                             modifier.use_vertex_groups = True

#                             group = child_obj.vertex_groups.new(name=bone_name)
#                             for v in child_obj.data.vertices:
#                                 group.add([v.index], 1.0, 'ADD')

#         bpy.ops.object.miao_clean_sense()
#         rename_all_children_based_on_coords(empty_coords_male_name_example)
#         process_contact_weights()
#         duplicate_bones_to_objects()
#         parent_dict_list = [(create_parent_dict(name_list), new_name) for name_list, new_name in name_groups]
#         for parent_dict, new_name in parent_dict_list:
#             join_objects(parent_dict, new_name)
#         rename_all_children_based_on_coords(empty_coords_male_name_example_comb)

#         return {'FINISHED'}

# #生成骨骼数据（命名为Bip001_example）
# class BoneDataGenerator(bpy.types.Operator):
#     bl_idname = "object.bone_data_generator"
#     bl_label = "生成骨骼数据"
#     bl_options = {'REGISTER', 'UNDO'}
#     def execute(self, context):
#         def get_bone_data_with_scaling(template_armature_name):
#             bone_data = {}
#             template_armature = bpy.data.objects.get(template_armature_name)
            
#             if template_armature and template_armature.type == 'ARMATURE':
#                 object_scale = template_armature.scale  # Get the scale of the armature object.
                
#                 bpy.context.view_layer.objects.active = template_armature
#                 bpy.ops.object.mode_set(mode='EDIT')
#                 for bone in template_armature.data.edit_bones:
#                     # Apply the object scale to the head and tail positions.
#                     head_scaled = Vector(bone.head) * object_scale
#                     tail_scaled = Vector(bone.tail) * object_scale
                    
#                     bone_data[bone.name] = {
#                         "parent": bone.parent.name if bone.parent else None,
#                         "head": head_scaled,
#                         "tail": tail_scaled
#                     }
#                 bpy.ops.object.mode_set(mode='OBJECT')
            
#             return bone_data

#         # Usage example
#         template_armature_name = "Bip001_example"
#         bone_data = get_bone_data_with_scaling(template_armature_name)

#         # Format output to ensure each bone is output on one line
#         output_lines = []
#         for bone_name, data in bone_data.items():
#             parent_str = f'"{data["parent"]}"' if data["parent"] else "None"
#             head_str = f"Vector(({data['head'].x:.4f}, {data['head'].y:.4f}, {data['head'].z:.4f}))"
#             tail_str = f"Vector(({data['tail'].x:.4f}, {data['tail'].y:.4f}, {data['tail'].z:.4f}))"
#             output_lines.append(f'"{bone_name}": {{"parent": {parent_str}, "head": {head_str}, "tail": {tail_str}}},')

#         # Output each line
#         for line in output_lines:
#             print(line)

#         return {'FINISHED'}
# class PointDataGenerator(bpy.types.Operator):
#     bl_idname = "object.point_data_generator"
#     bl_label = "生成点数据"
#     bl_options = {'REGISTER', 'UNDO'}
#     def execute(self, context):
#         # 在这里添加你的代码来生成点数据
#         def get_empty_objects_data(objects_list):
#             empty_coords = []
#             for obj_name in objects_list:
#                 obj = bpy.data.objects.get(obj_name)
#                 if obj and obj.type == 'EMPTY':
#                     empty_coords.append((obj.name, Vector(obj.location)))
#             return empty_coords

#         # 示例：你想提取这些空物体的信息
#         empty_objects_example = [
#             "R Toe0_example",
#             "R Foot_example",
#             "R Calf_example",
#             "L Toe0_example",
#             "L Foot_example",
#             "L Calf_example",
#             "Spine_example",
#             "Spine2_example",
#             "Spine1_example",
#             "R UpperArm_example",
#             "R Thigh_example",
#             "R Hand_example",
#             "R Forearm_example",
#             "R Finger2_example",
#             "R Finger21_example",
#             "R Finger1_example",
#             "R Finger11_example",
#             "R Finger0_example",
#             "R Finger01_example",
#             "Pelvis_example",
#             "L UpperArm_example",
#             "L Thigh_example",
#             "L Hand_example",
#             "L Forearm_example",
#             "L Finger2_example",
#             "L Finger21_example",
#             "L Finger1_example",
#             "L Finger11_example",
#             "L Finger0_example",
#             "L Finger01_example",
#             "Neck_example",
#             "Head_example",
#             "Feet_example",
#             "UpperBody_example",
#             "Face_example",
#             "LowerBody_example"
            
#         ]

#         # 提取信息并生成数据结构
#         empty_coords_data = get_empty_objects_data(empty_objects_example)

#         # 打印结果，每行输出一个空物体的名称和坐标
#         for name, location in empty_coords_data:
#             location_str = f"Vector(({location.x:.4f}, {location.y:.4f}, {location.z:.4f}))"
#             print(f'("{name}", {location_str}),')
#         return {'FINISHED'}

# def register():
    # None
    # bpy.utils.register_class(CharOperater)
    # bpy.utils.register_class(FemaleCharOperaterBone)
    # bpy.utils.register_class(MaleCharOperaterBone)
    # bpy.utils.register_class(BoneDataGenerator)
    # bpy.utils.register_class(PointDataGenerator)

# def unregister():
    # None
    # bpy.utils.unregister_class(CharOperater)
    # bpy.utils.unregister_class(FemaleCharOperaterBone)
    # bpy.utils.unregister_class(MaleCharOperaterBone)
    # bpy.utils.unregister_class(BoneDataGenerator)
    # bpy.utils.unregister_class(PointDataGenerator)

    