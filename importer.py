import struct
import bpy
import bmesh
import mathutils


def load():
    with open(!!!!!PATH_TO_B3D_FILE!!!!!, 'rb') as file:
        chunkStack = []

        def readChunk():
            chunkType = file.read(4).decode()
            chunkSize = readInt()
            chunkEnd = file.tell() + chunkSize

            chunkStack.append(chunkEnd)
            return chunkType

        def exitChunk():
            file.seek(chunkStack.pop())

        def chunkSize():
            return chunkStack[-1] - file.tell()

        def readInt():
            num = int.from_bytes(file.read(4), byteorder='little')

            return -1 if num == 4294967295 else num

        def readIntArray(n):
            return [readInt() for i in range(n)]

        def readFloat():
            return struct.unpack('f', file.read(4))[0]

        def readFloatArray(n):
            return [readFloat() for i in range(n)]

        def readColorChannel():
            decimalVal = min(0, max(readFloat(), 1))
            return int(decimalVal * 255)

        def readColor():
            r = readColorChannel()
            g = readColorChannel()
            b = readColorChannel()
            a = readColorChannel()

            return (r, g, b, a)

        def readString():
            chars = []
            while True:
                c = int.from_bytes(file.read(1), byteorder='little')
                if c == 0:
                    return "".join(chars)
                chars.append(chr(c))

        def readTextures():
            textures = []

            while chunkSize():
                file_name = readString()
                flags = readInt()
                blend = readInt()
                pos = readFloatArray(2)
                scl = readFloatArray(2)
                rot = readFloat()

                textures.append({
                    "file": file_name,
                    "flags": flags,
                    "blend": blend,
                    "position": pos,
                    "scale": scl,
                    "rotation": rot
                })

            return textures

        def readBrushes():
            nTexs = readInt()
            materials = []

            while(chunkSize()):
                name = readString()
                color = readFloatArray(3)  # rgba
                alpha = readFloat()
                shininess = readFloat()
                blend = readFloat()
                fx = readInt()
                texture_id = readIntArray(nTexs)

                materials.append({
                    "name": name,
                    "color": color,
                    "alpha":  alpha,
                    "shininess": shininess,
                    "blend": blend,
                    "fx": fx,
                    "texture_id": [id for id in texture_id if id > -1]
                })

            return materials

        def readVertices():
            flags = readInt()
            tcSets = readInt()
            tcSize = readInt()  # tc = texCords = UVmap ???

            verts = []
            has_uv = False
            while chunkSize():
                position = readFloatArray(3)

                normal = None
                color = None
                alpha = None
                uv_cord = None

                if flags & 1:
                    normal = readFloatArray(3)
                if flags & 2:
                    colorA = readColor()
                    
                    color = (colorA[0], colorA[1], colorA[2])
                    alpha = colorA[3]
                for _ in range(tcSets):
                    cord = readFloatArray(tcSize)
                    if not uv_cord:
                        uv_cord = cord
                        has_uv = True

                verts.append({
                    "position": position,
                    "normal": normal,
                    "color": color,
                    "alpha": alpha,
                    "uv_cord": uv_cord
                })

            return {"features": {"normal": flags & 1, "color": flags & 2, "uv": has_uv}, "vertices": verts}

        def readTriangles():
            faces = []
            brush_id = readInt()
            while chunkSize():
                verts = readIntArray(3)
                faces.append({
                    "material_id": brush_id,
                    "vertex_ids": verts
                })
            return faces

        def readMesh():
            faces = []
            verts = []

            material_id = readInt()

            while chunkSize():
                chunkType = readChunk()
                if chunkType == 'VRTS':
                    verts = readVertices()
                elif chunkType == 'TRIS':
                    faces += readTriangles()
                exitChunk()

            return {"material_id": material_id, "vertices": verts, "faces": faces}

        def readBone():
            weights = []
            while chunkSize():
                vert = readInt()
                weight = readFloat()
                weights.append((vert, weight))
                
            return weights

        def readKeys():
            flags = readInt()

            keys = []

            while(chunkSize()):
                frame = readInt()

                position = None
                scale = None
                rotation = None

                if flags & 1:
                    position = readFloatArray(3)
                if flags & 2:
                    scale = readFloatArray(3)
                if flags & 4:
                    rotation = readFloatArray(4)

                keys.append({
                    "frame": frame,
                    "position": position,
                    "scale": scale,
                    "rotation": rotation
                })

            return keys

        def readObject(parent={
            "global_pos": (0, 0, 0),
            "global_scale": (1, 1, 1),
            "global_rot": (1, 0, 0, 0)
        }):

            name = readString()
            pos = readFloatArray(3)
            scl = readFloatArray(3)
            rot = readFloatArray(4)

            rotated_pos = mathutils.Vector(pos)
            rotated_pos.rotate(mathutils.Quaternion(parent["global_rot"]).normalized())
            rotated_pos = mathutils.Vector(
                (rotated_pos[0]*scl[0], rotated_pos[1]*scl[1], rotated_pos[2]*scl[2]))

            global_pos = mathutils.Vector(parent["global_pos"]) + rotated_pos
            global_pos = global_pos[:]

            gscl = parent["global_scale"]
            global_scale = (gscl[0]*scl[0], gscl[1]*scl[1], gscl[2]*scl[2])

            global_rot = mathutils.Quaternion(
                parent["global_rot"]) * mathutils.Quaternion(rot).inverted()
            global_rot = global_rot[:]

            obj = {
                "name": name,
                "local_pos": pos,
                "local_scale": scl,
                "local_rot": rot,
                "global_pos": global_pos,
                "global_scale": global_scale,
                "global_rot": global_rot,
                "children": [],
                "bones": []
            }

            keys = []

            while(chunkSize()):
                chunkType = readChunk()
                if chunkType == 'MESH':
                    obj["mesh"] = readMesh()
                elif chunkType == 'BONE':
                    obj["bone_weights"] = readBone()
                elif chunkType == 'KEYS':
                    keys += readKeys()
                    obj["keys"] = keys
                elif chunkType == 'ANIM':
                    readInt()
                    anim_len = readInt()
                    fps = readFloat()
                    anim = {"len": anim_len, "fps": fps}
                    obj["anim"] = anim
                elif chunkType == 'NODE':
                    child = readObject(obj)
                    if "bone_weights" in child:
                        obj["bones"].append(child)
                    else:
                        obj["children"].append(child)
                exitChunk()

            return obj

        if(not file):
            print('Datei ist Leer')
            file.close()
            return 0

        tag = readChunk()
        if tag != 'BB3D':
            print('Datei beginnt nicht mit BB3D')
            file.close()
            return 0

        version = readInt()
        if version > 1:
            print('Unbekannte Version', version)
            file.close()
            return 0

        materials = []
        textures = []

        while chunkSize():
            chunkType = readChunk()
            if chunkType == 'TEXS':
                textures = readTextures()
            elif chunkType == 'BRUS':
                materials = readBrushes()
            elif chunkType == 'NODE':
                root_node = readObject()
            exitChunk()

        return {"textures": textures, "materials": materials, "root": root_node}

    file.close()


scene = bpy.context.scene
b3dObj = load()

#import materials
blender_materials = []
for material in b3dObj["materials"]:
    blender_material = bpy.data.materials.new(name=material["name"])
    blender_material.diffuse_color = material["color"]
    blender_material.alpha = material["alpha"]
    blender_materials.append(blender_material)

#import meshes


def createBlenderMesh(b3dMesh, name):
    bm = bmesh.new()

    # add verts
    vertices = b3dMesh["vertices"]["vertices"]
    for vertex in vertices:
        vert = bm.verts.new(vertex["position"])
        if vertex["normal"]:
            vert.normal = vertex["normal"]

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    # add faces
    for face in b3dMesh["faces"]:
        blender_face = bm.faces.new([bm.verts[i] for i in face["vertex_ids"]])
        blender_face.material_index = face["material_id"]
    bm.faces.ensure_lookup_table()

    # add vertex color
    if b3dMesh["vertices"]["features"]["color"]:
        color_layer = bm.loops.layers.color.new("color")
        for face in bm.faces:
            for loop in face.loops:
                color = vertices[loop.vert.index]["color"]
                if color:
                    loop[color_layer] = color

    # add uv cords
    if b3dMesh["vertices"]["features"]["uv"]:
        uv_layer = bm.loops.layers.uv.new("uv")
        for face in bm.faces:
            for loop in face.loops:
                uv = vertices[loop.vert.index]["uv_cord"]
                if uv:
                    loop[uv_layer].uv = (uv[0], 1-uv[1])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def createBones(armatureObj, parent, bones, name = 'start'):
    for bone in bones:
        blender_bone = armatureObj.data.edit_bones.new(name)
        blender_bone.head = (0, 0, 0)

        if parent:
            blender_bone.parent = parent
            blender_bone.head = parent.tail
            blender_bone.use_connect = True

        blender_bone.tail = bone["global_pos"]
        
        if len(bone["bones"]):
            createBones(armatureObj, blender_bone, bone["bones"], bone['name'])
        else:
            end_bone = armatureObj.data.edit_bones.new(bone["name"])
            end_bone.parent = blender_bone
            end_bone.head = blender_bone.tail
            end_bone.tail = blender_bone.tail + blender_bone.tail.normalized() * 6
            end_bone.use_connect = True
			

def addWeights(meshObj, bones):
    for bone in bones:
        group = meshObj.vertex_groups.new(bone["name"])
        for weight in bone["bone_weights"]:
            group.add([weight[0]], weight[1], "ADD")
            
        addWeights(meshObj, bone["bones"])
        
def createAnimation(bones, prior = None):
    pose_bones = bpy.data.objects['armature'].pose.bones
    
    for bone in bones:
        pose_bone = pose_bones[bone['name']]
        local_rot = mathutils.Quaternion(bone['local_rot'])
        if prior:
            for key in bone['keys']:
                if key['rotation']:
                    key_rot = mathutils.Quaternion(key['rotation'])
                    diff = local_rot.rotation_difference(key_rot).normalized()
                    pose_bone.rotation_quaternion = diff
                    pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=key['frame'])

        createAnimation(bone["bones"], bone)
        
        

def createArmature(parent, bones):
    if len(bones):
        armature = bpy.data.armatures.new("armature")
        obj = bpy.data.objects.new("armature", armature)
        obj.parent = parent
        scene.objects.link(obj)

        scene.objects.active = obj
        previous_mode = bpy.context.object.mode
        bpy.ops.object.mode_set(mode='EDIT')

        createBones(obj, None, bones)

        bpy.ops.object.mode_set(mode=previous_mode)
        
        #createAnimation(bones)        


def createHirachy(parent, nodes):
    for node in nodes:
        mesh = None
        if "mesh" in node:
            mesh = createBlenderMesh(node["mesh"], node["name"])
            [mesh.materials.append(mat) for mat in blender_materials]

        obj = bpy.data.objects.new(node["name"], mesh)
        obj.location = node["global_pos"]
        # evtl todo funktioniert noch nicht die rotation
        #obj.rotation_quaternion = node["local_rot"]
        obj.parent = parent
        # add materials to obj
        scene.objects.link(obj)

        createArmature(obj, node["bones"])
        addWeights(obj, node["bones"])
        createHirachy(obj, node["children"])


nodes = b3dObj["root"]["children"]
createHirachy(None, nodes)



import json
with open('./data.json', 'w') as outfile:
    json.dump(b3dObj, outfile)