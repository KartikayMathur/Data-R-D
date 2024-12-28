import bpy
from bpy.app.handlers import persistent

def setup_bevel_defaults():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.default
    
    if kc:
        # Get the Mesh keymap
        km = kc.keymaps.get('Mesh')
        if km:
            # First, remove existing bevel keymaps to avoid duplicates
            for kmi in km.keymap_items:
                if kmi.idname == 'mesh.bevel':
                    km.keymap_items.remove(kmi)
            
            # Add Vertex Bevel (Ctrl+Shift+B)
            kmi = km.keymap_items.new('mesh.bevel', 'B', 'PRESS', ctrl=True, shift=True)
            kmi.properties.affect = 'VERTICES'
            kmi.properties.offset_type = 'OFFSET'
            kmi.properties.profile = 0.085
            kmi.properties.segments = 6
            kmi.properties.harden_normals = False
            
            # Add Edge/Face Bevel (Ctrl+B)
            kmi = km.keymap_items.new('mesh.bevel', 'B', 'PRESS', ctrl=True)
            kmi.properties.affect = 'EDGES'
            kmi.properties.offset_type = 'OFFSET'
            kmi.properties.profile = 0.5
            kmi.properties.segments = 6
            kmi.properties.harden_normals = True

            print("Bevel keymaps set successfully!")
            return True
    return False

class VIEW3D_OT_setup_bevel_defaults(bpy.types.Operator):
    bl_idname = "view3d.setup_bevel_defaults"
    bl_label = "Setup Bevel Defaults"
    bl_description = "Setup custom bevel defaults for vertex, edge, and face modes"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if setup_bevel_defaults():
            self.report({'INFO'}, "Bevel defaults configured successfully!")
        else:
            self.report({'ERROR'}, "Failed to configure bevel defaults")
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(VIEW3D_OT_setup_bevel_defaults.bl_idname)

def register():
    bpy.utils.register_class(VIEW3D_OT_setup_bevel_defaults)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu_func)

def unregister():
    bpy.utils.unregister_class(VIEW3D_OT_setup_bevel_defaults)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)

if __name__ == "__main__":
    register()
    # Run setup immediately when script is executed
    setup_bevel_defaults()