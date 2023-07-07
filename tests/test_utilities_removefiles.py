import os
import pathlib

from datatransport.utilities import remove_file

def test_remove_name_as_string(fs):
    filename = 'demo.txt'
    fs.create_file(filename)
    remove_file(filename)
    assert not os.path.exists(filename)
    
def test_remove_name_as_bytes(fs):
    filename = b'demo.txt'
    fs.create_file(filename)
    remove_file(filename)
    assert not os.path.exists(str(filename))
     
def test_remove_name_as_path(fs):
    filename = pathlib.Path('demo.txt')
    fs.create_file(filename)
    remove_file(filename)
    assert not os.path.exists(filename)

def test_remove_list(fs):
    filenames = ['a','b','c']
    for filename in filenames:
        fs.create_file(filename)
    remove_file(filenames)
    for filename in filenames:
        assert not os.path.exists(filename)

def test_remove_list_mixed(fs):
    filenames = ['a',b'b',pathlib.Path('c')]
    for filename in filenames:
        fs.create_file(filename)
    remove_file(filenames)
    for filename in filenames:
        assert not os.path.exists(str(filename))

def test_remove_missing(fs):
    filename = 'demo.txt'
    remove_file(filename)
    assert not os.path.exists(filename)
