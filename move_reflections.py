# this file moves all pdf files into a folder called "reflections", which will be made if necessary

import os

# https://stackoverflow.com/questions/8858008/how-to-move-a-file, 
# answered by Peter Vlaar

import os, shutil, pathlib, fnmatch

def move_dir(src: str, dst: str, pattern: str = '*'):
    if not os.path.isdir(dst):
        pathlib.Path(dst).mkdir(parents=True, exist_ok=True)
    for f in fnmatch.filter(os.listdir(src), pattern):
        shutil.move(os.path.join(src, f), os.path.join(dst, f))


move_dir('./','./_reflections/','*reflection*.pdf')
move_dir('./','./_reflections/','*Reflection*.pdf')

