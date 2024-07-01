# Vector Graphics Editor
A minimalistic vector graphics editor designed for quickly creating svg 
images. This package aims to provide .....


# Configuration
In order to start the editor you must run `python -m main_gui.py` with the
optional flag '-f --file' which allows you to open an svg file with the editor.
For convenience there is a `vector_graphics.sh` file that will run the project. By
adding 
`alias "{command_name_of_your_choice}="{path_to_project}/./vector_graphics.sh"`
to your shell profile (.zprofile, .bashrc, ect) you can open the editor with a
command. Note that you may need to run `chmod +x
{path_to_project}/vector_graphics.sh` before this will work. 
This should work on macOS, however small changes may be needed in order to run
on other operating system.
