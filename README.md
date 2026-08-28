# alttablavistababy

Simple window search list for Niri : "alt+tab la vista, baby!" will display a list of windows so you can switch to it. Yes, like you would do with https://github.com/abenz1267/walker.
This is a https://github.com/mohitraghav1318/NiriSeek port in python for no good reason.

Install : well generally you just put the python code somewhere and bind it

    Mod+Return { spawn-sh "/path/to/niri-seek.py" ;}


But i use NixOS by the way, so nothing works. Just ignore the ridiculous wrapper i asked AI to write :(
If ever you are on the same boat, then rather bind key to niri-seek.
Invoke the wrapper to *install* 

    nix-env -f /path/to/niriseek-wrapper.nix -iA niri-seek

