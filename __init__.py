bl_info = {
    "name": "World Space UV Unwrap",
    "description": "Unwrap UVs in world space coordinates",
    "author": "Dmitry Prikhodko",
    "wiki_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap#readme",
    "tracker_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap/issues",
    "doc_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap#readme",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "UV > Unwrap",
    "category": "UV",
}


import bpy
import bmesh
import math


def planar_axes(normal):
    """ Given a normal vector, return two orthogonal axes for planar mapping """
    nx, ny, nz = abs(normal.x), abs(normal.y), abs(normal.z)

    if nx > ny and nx > nz:
        return (0, 1, 0), (0, 0, 1)
    elif ny > nz:
        return (1, 0, 0), (0, 0, 1)
    else:
        return (1, 0, 0), (0, 1, 0)


class UV_OT_WorldSpaceUnwrap(bpy.types.Operator):
    bl_idname = "uv.world_space_unwrap"
    bl_label = "Unwrap World Space"
    bl_description = "Unwrap UVs in world space coordinates"
    bl_options = {'REGISTER', 'UNDO'}

    scale: bpy.props.FloatProperty(
        name="Scale",
        description="UV tiling scale",
        default=1.0,
        min=0.001,
        soft_min=0.001
    )
    offset: bpy.props.FloatVectorProperty(
        name="Offset",
        description="UV offset in texture space",
        size=2,
        default=(0.0, 0.0)
    )
    rotation: bpy.props.FloatProperty(
        name="Rotation",
        description="UV rotation in degrees",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION'
    )
    normalize: bpy.props.BoolProperty(
        name="Normalize",
        description="Moves each polygon's UVs into a single tile",
        default=False
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.verify()
        matrix_world = obj.matrix_world

        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)

        for face in bm.faces:
            if not face.select:
                continue  # unwrap only selected faces

            u_axis, v_axis = planar_axes(face.normal)

            # World to UV
            for loop in face.loops:
                world_pos = matrix_world @ loop.vert.co

                u = world_pos.dot(u_axis)
                v = world_pos.dot(v_axis)

                # Scale
                u /= self.scale
                v /= self.scale

                # Rotate
                u_rot = u * cos_r - v * sin_r
                v_rot = u * sin_r + v * cos_r

                # Offset
                u = u_rot + self.offset[0]
                v = v_rot + self.offset[1]

                loop[uv_layer].uv = (u, v)

            # (Optional) 2'nd pass: normalize UVs
            if self.normalize:

                min_u = min_v = float(' inf')
                max_u = max_v = float('-inf')
                for loop in face.loops:
                    u, v = loop[uv_layer].uv
                    if u < min_u: min_u = u
                    if v < min_v: min_v = v
                    if u > max_u: max_u = u
                    if v > max_v: max_v = v

                origin_u = round((min_u + max_u) * 0.5 - 0.5)
                origin_v = round((min_v + max_v) * 0.5 - 0.5)

                for loop in face.loops:
                    u, v = loop[uv_layer].uv

                    # Normalize
                    u -= origin_u
                    v -= origin_v

                    loop[uv_layer].uv = (u, v)

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}


def uv_menu(self, context):
    self.layout.separator()
    self.layout.operator(
        UV_OT_WorldSpaceUnwrap.bl_idname,
        text=UV_OT_WorldSpaceUnwrap.bl_label
    )


def register():
    bpy.utils.register_class(UV_OT_WorldSpaceUnwrap)
    bpy.types.IMAGE_MT_uvs_unwrap.append(uv_menu)


def unregister():
    bpy.types.IMAGE_MT_uvs_unwrap.remove(uv_menu)
    bpy.utils.unregister_class(UV_OT_WorldSpaceUnwrap)


if __name__ == "__main__":
    register()