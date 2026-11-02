# Yet Another Addon (Lite)
This is a Blender add-on which aims to give various tools to aid in XIV Modding workflows. This is the lite version: model import/export, Penumbra modpacking, .pose and scaling import, and the model overview have been removed in favour of Instant Edit. What remains:
* Fix for transparent meshes made in Blender.
* Shape key transfer and modifier application for meshes with shape keys.
* Backface creation and XIV flow data tools.
* YAS weight management, including storing and restoring YAS weights on devkit meshes.
* Syncing the devkit's Mannequin to its separate body parts: with "Sync Mannequin to Body Parts" on (Devkit panel, Body), size and shape changes made on the Mannequin also go to the torso, legs, hands and feet.

You'll find most of the features under the "XIV Kit" tab in the 3D Viewport.

## Removed from the full add-on
* Native XIV model import/export (.mdl).
* File export with the ability to retain XIV specific properties.
* Penumbra compatible modpackaging.
* XIV .pose and scaling import (the clipboard permission for pasting bone scaling is gone with it).
* The model overview.

These features are superseded by [MagicFit](https://github.com/link-0402/MagicFit) (editing tools) and [Instant Edit](https://github.com/link-0402/XIV-Instant-Edit) (model export/import, among other things). 

The [wiki](https://github.com/Arrenval/Yet-Another-Addon/wiki) belongs to the full add-on, so it also describes features that are not in this version. It still covers the remaining tools and the compatible YAB+ Devkit.

## Blender support
Works with Blender 4.2 through 5.2. The manifest allows 4.2.0 up to, but not including, 5.3.0. Blender 5.x API changes, such as animation selection, are handled.

## Installing
Download the add-on zip and install it from Blender's Preferences, in the Add-ons / Extensions tab, with "Install from Disk".

The lite version uses the same extension ID as the full add-on, so installing one over the other replaces it and resets user preferences. Don't add the full add-on's extension repository (`Arrenval/Yet-Another-Addon`) while using this version: it would offer the full version as an update.

## Licensing
The remaining code within this tool is made for the Blender API and follows its GPL3 licensing, read the *LICENSE.md* for details. However, I do humbly request that it does not be used for creating mods or assets that are behind a permanent paywall. 

##### Final Fantasy XIV © SQUARE ENIX CO., LTD. All Rights Reserved. This add-on is not affiliated with SQUARE ENIX CO., LTD. in any way.
