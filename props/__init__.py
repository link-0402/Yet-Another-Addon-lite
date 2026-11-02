import bpy

from bpy.props import PointerProperty

from .studio   import YAStudioProps, YASStorage, YASUIList,  CLASSES as STUDIO_CLS
from .window   import YAWindowProps, CLASSES as WIN_CLS
from .getters  import get_studio_props, get_window_props, get_devkit_props, get_devkit_win_props
from .handlers import set_handlers, remove_handlers


def set_addon_properties() -> None:
    bpy.types.WindowManager.ya_window_props = PointerProperty(
        type=YAWindowProps)

    bpy.types.Scene.ya_studio_props = PointerProperty(
        type=YAStudioProps)
    
    bpy.types.Object.yas = PointerProperty(name="YAS Weight Storage",
        type=YASStorage)
    
    YAWindowProps.ui_buttons()
    YAWindowProps.set_extra_options()
    
def remove_addon_properties() -> None:
    del bpy.types.WindowManager.ya_window_props
    del bpy.types.Scene.ya_studio_props
    del bpy.types.Object.yas

CLASSES = WIN_CLS + STUDIO_CLS
