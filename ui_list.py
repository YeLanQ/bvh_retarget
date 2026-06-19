"""
BVH Retarget — UI Lists
Custom UIList for bone mapping display.
"""

import bpy
from bpy.types import UIList


class BVHRETARGET_UL_BoneMappings(UIList):
    """UIList for bone mapping items."""
    bl_idname = "BVHRETARGET_UL_BoneMappings"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)

            # Enabled checkbox
            row.prop(item, "enabled", text="", emboss=False,
                     icon='CHECKBOX_HLT' if item.enabled else 'CHECKBOX_DEHLT')

            # Source bone
            row.prop(item, "source_bone", text="", emboss=False)

            # Arrow
            row.label(text="", icon='TRIA_RIGHT')

            # Target bone
            row.prop(item, "target_bone", text="", emboss=False)

            # Retarget mode
            row.prop(item, "retarget_mode", text="")

            # Remove single constraints button
            if item.target_bone:
                op = row.operator("bvh_retarget.remove_single_retargeting",
                                  text="", icon='X', emboss=False)
                op.bone_name = item.target_bone

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='BONE_DATA')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = [
    BVHRETARGET_UL_BoneMappings,
]


def _safe_register_class(cls):
    """Register a class only if not already registered."""
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # already registered


def _safe_unregister_class(cls):
    """Unregister a class only if registered."""
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass  # not registered


def register():
    for cls in _classes:
        _safe_register_class(cls)


def unregister():
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
