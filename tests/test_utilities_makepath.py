import pathlib

from datatransport.utilities import make_path 

def test_make_path_name_as_string(fs):
    filename = 'dir1/dir2/demo.txt'
    make_path(filename)
    assert pathlib.Path(filename).parents[0].exists() 
 
def test_make_path_name_as_path(fs):
    filename = pathlib.Path('dir1/dir2/demo.txt')
    make_path(filename)
    assert filename.parents[0].exists() 
  
def test_make_path_name_exists(fs):
    filename = pathlib.Path('dir1/dir2/demo.txt')
    fs.create_dir(filename.parents[0])
    make_path(filename)
    assert filename.parents[0].exists() 

def test_make_path_mode(fs):
    filename = pathlib.Path('dir1/dir2/demo.txt')
    make_path(filename, mode=0o777)
    assert filename.parents[0].stat().st_mode == 0o40777
    assert filename.parents[1].stat().st_mode == 0o40777
    
            
