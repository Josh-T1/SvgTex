# Vector Graphics Editor
A minimalistic vector graphics editor designed for creating mathematical diagrams containing latex. Work in progress, use at your own risk.


## Using latex in image
Write the latex code surrounded by single `$`. Pressing `ctrl-c` will compile any latex inside of a text box, if latex compilation fails 
you will get an pop up error. 

* What packages are supported?
* Can users add new packages?
* Comment on error message

# Shortcuts
1. These should not be cntrl, or atelast sum
* `ctrl-c`: compiles latex inside of text boxes.
* `ctrl-l`: select line tool
* `ctrl-t`: text box tool
* `ctrl-r`: rectangle tool
* `ctrl-b`: brush tool
* `ctrl-p`: pen tool
* `ctrl-s`: selector tool
* `ctrl-n`: cycle through elements under cursor
* `ctrl-v`: paste item
* `ctrl-c`: copy item

# Configuration
In order to start the editor you must run `python -m main_gui.py`. Flags include
- '-f  --file': select an svg file to edit

For convenience there is a `vector_graphics.sh` file that will run the project. By
adding 
`alias "{command_name_of_your_choice}="{path_to_project}/./vector_graphics.sh"`
to your shell profile (.zprofile, .bashrc, ect) you can open the editor with a
command. Note that you may need to run `chmod +x
{path_to_project}/vector_graphics.sh` before this will work. 
This should work on macOS, however `vector_graphics.sh` needs to be adjusted for
other operating systems as paths have different formats.
