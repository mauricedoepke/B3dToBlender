## Features

What it does import:
 - meshes
 - materials
 - textures
 - uv mapping
 - bones
 - bone weights

What it does not import:
 - animations: I did some experiments on this as well, but the necessary effort wasn't justified in my case.
 
## Limitations
 - Blender 2.7x
 - I think I did not implement the whole B3d spec, but only the subset I needed for my files. If your files don't convert correctly, feel free to raise an issue.
 
 
## Why creating this when there is [Assimp](http://www.assimp.org/) ?
Assimmp did neither import bones nor bone weights correctly. I chose to do this In python as I felt it to be easier than to 

## How to use it
 - Start Blender 2.7x
 - Delete your Scene [optional]
 - Paste the script from import.py into the Blender editor
 - Replace "!!!!!PATH_TO_B3D_FILE!!!!!" in line 8 with the path of your B3d file
 - Hit the "Run Script" button
