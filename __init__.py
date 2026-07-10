bl_info = {
    "name": "World Space UV Unwrap",
    "description": "Unwrap UVs in world space coordinates",
    "author": "Dmitry Prikhodko",
    "wiki_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap#readme",
    "tracker_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap/issues",
    "doc_url": "https://github.com/koshkokoshka/blender-world-space-uv-unwrap#readme",
    "version": (1, 2, 0),
    "blender": (4, 2, 0),
    "location": "UV > Unwrap",
    "category": "UV",
}


import bpy
import bmesh
import math


def planar_axes(normal):
    """Given a normal vector, return two orthogonal axes for planar mapping"""
    nx, ny, nz = abs(normal.x), abs(normal.y), abs(normal.z)

    if nx > ny and nx > nz:
        return (0, 1, 0), (0, 0, 1)
    elif ny > nz:
        return (1, 0, 0), (0, 0, 1)
    else:
        return (1, 0, 0), (0, 1, 0)


def get_material_image(material):
    """Get image assigned to the material"""
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            return node.image
    return None


def safe_get(array, index, default=None):
    """Safely get an element from an array by index"""
    if not array or (index < 0 or index >= len(array)):
        return default
    return array[index]


class UV_OT_WorldSpaceUnwrap(bpy.types.Operator):
    bl_idname = "uv.world_space_unwrap"
    bl_label = "Unwrap World Space"
    bl_description = "Unwrap UVs in world space coordinates"
    bl_options = {'REGISTER', 'UNDO'}

    scale_method: bpy.props.EnumProperty(
        name="Method",
        items=[
            ('FACTOR', "Factor", "UV tiling scale"),
            ('TEXEL_DENSITY', "Texel Density", "Pixels per 1 world unit"),
        ],
        default='FACTOR'
    )
    scale_value: bpy.props.FloatProperty(
        name="Scale",
        description="UV tiling scale",
        default=1.0,
        min=0.001,
        soft_min=0.001
    )
    texel_density: bpy.props.IntProperty(
        name="Pixels",
        description="Pixels per 1 world unit",
        default=64,
        min=2,
        soft_min=2,
        subtype='PIXEL',
    )
    offset: bpy.props.FloatVectorProperty(
        name="Offset",
        description="UV offset in texture space",
        size=2,
        default=(0.0, 0.0),
        step=5  # 0.05 per step
    )
    rotation: bpy.props.FloatProperty(
        name="Rotation",
        description="UV rotation in degrees",
        default=0.0,
        subtype='ANGLE',
        unit='ROTATION',
        step=100  # 1 deg per step (1/100th)
    )
    normalize: bpy.props.BoolProperty(
        name="Normalize",
        description="Moves each polygon's UVs into a single tile",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.prop(self, "scale_method")
        if self.scale_method == 'FACTOR': layout.prop(self, "scale_value")
        elif self.scale_method == 'TEXEL_DENSITY': layout.prop(self, "texel_density")
        layout.prop(self, "offset")
        layout.prop(self, "rotation")
        layout.prop(self, "normalize")


    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        # Get mesh data
        obj = context.object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.verify()
        vertex_transform_matrix = obj.matrix_world
        normal_rotation_matrix = obj.matrix_world.to_3x3().inverted().transposed()

        # Get projection parameters
        use_texel_density = self.scale_method == 'TEXEL_DENSITY'

        if use_texel_density:
            # Scale Method: Texel Density
            texel_density = self.texel_density
            texture_sizes = []  # array: material index -> texture image size
            for slot in obj.material_slots:
                image = get_material_image(slot.material)
                texture_sizes.append(image.size if image else None)
        else:
            # Scale Method: Factor
            inv_scale = 1.0 / self.scale_value

        offset_x, offset_y = self.offset

        cos_r = math.cos(self.rotation)
        sin_r = math.sin(self.rotation)

        # Perform UV projection
        for face in bm.faces:
            if not face.select:
                continue  # unwrap only selected faces

            # Determine UV scale
            if use_texel_density:
                texture_size = safe_get(texture_sizes, face.material_index)
                if texture_size:
                    u_scale = texel_density / texture_size[0]  # convert texel density to scale factor
                    v_scale = texel_density / texture_size[1]
                else:
                    u_scale = 1  # fallback when material has no texture image
                    v_scale = 1
            else:
                u_scale = inv_scale
                v_scale = inv_scale

            # Calculate axes for planar mapping
            normal = (normal_rotation_matrix @ face.normal).normalized()
            u_axis, v_axis = planar_axes(normal)

            # Project every vertex from world-space to UV-space
            for loop in face.loops:
                world_pos = vertex_transform_matrix @ loop.vert.co

                # Project onto UV plane
                u = world_pos.dot(u_axis)
                v = world_pos.dot(v_axis)

                # Scale
                u *= u_scale
                v *= v_scale

                # Rotate
                u, v = (
                    u * cos_r - v * sin_r,
                    u * sin_r + v * cos_r,
                )

                # Offset
                u += offset_x
                v += offset_y

                loop[uv_layer].uv = (u, v)

            # (Optional) 2'nd pass: normalize UVs so its center lies inside the [0..1] tile
            if self.normalize:

                min_u = min_v = float(' inf')
                max_u = max_v = float('-inf')
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    if uv.x < min_u: min_u = uv.x
                    if uv.y < min_v: min_v = uv.y
                    if uv.x > max_u: max_u = uv.x
                    if uv.y > max_v: max_v = uv.y

                origin_u = round((min_u + max_u) * 0.5 - 0.5)
                origin_v = round((min_v + max_v) * 0.5 - 0.5)

                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    uv.x -= origin_u
                    uv.y -= origin_v

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