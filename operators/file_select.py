import bpy

from pathlib         import Path
from bpy.types       import Operator, Context
from bpy.props       import StringProperty

from ..props         import get_window_props


class FileSelector(Operator):
    bl_idname      = "ya.file_selector"
    bl_label       = "Select File"
    bl_description = "Select file"
    bl_options     = {'UNDO'}

    filepath: StringProperty(options={'HIDDEN'}) # type: ignore
    category: StringProperty(options={'HIDDEN'}) # type: ignore
    filter_glob: bpy.props.StringProperty(
        subtype='FILE_PATH',
        options={'HIDDEN'}) # type: ignore
    
    def invoke(self, context: Context, event):
        if self.category.startswith("INSP"):
            self.filter_glob = "*.phyb;*.mdl"

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        file = Path(self.filepath)

        if not file.is_file():
            self.report({"ERROR"}, "Not a valid file!")
            return {'FINISHED'}
        
        setattr(get_window_props(), self.attr_from_category(), self.filepath)
        self.report({"INFO"}, "File selected!")
        
        return {'FINISHED'}

    def attr_from_category(self) -> str:
        if self.category == "INSP1":
            return "insp_file1"
        elif self.category == "INSP2":
            return "insp_file2"


CLASSES = [
    FileSelector,
]
