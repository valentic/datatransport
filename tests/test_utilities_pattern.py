
import pytest
import zoneinfo

from datetime import datetime, timedelta, timezone
from datatransport.utilities import PatternTemplate

def test_pattern_replace():
    replaceRule = PatternTemplate('rule')
    src = '<rule>'
    value = 'hello world'
    result = replaceRule(src, value)
    assert result == f'{value}' 

def test_pattern_embedded():
    replaceRule = PatternTemplate('rule')
    src = 'Before <rule> after'
    value = 'hello world'
    result = replaceRule(src, value)
    assert result == f'Before {value} after'

def test_pattern_group():
    replaceGroup = PatternTemplate('group', sep='.')
    src = 'More complicated example: <group[0:2]> <group[-1]>'
    group = 'comp.lang.python'
    result = replaceGroup(src, group)
    assert result == 'More complicated example: comp.lang python'

def test_pattern_dict():
    replaceDict = PatternTemplate('header')
    src = 'Using a dictionary: <header["x-transport-date"]>'
    header = {'newsgroup': 'transport.data', 'x-transport-date': '2005-06-15'}
    result = replaceDict(src, header)
    assert result == 'Using a dictionary: 2005-06-15'

def test_pattern_cache():
    replaceDict = PatternTemplate('header')
    src = 'Using a dictionary: <header["x-transport-date"]>'
    header = {'newsgroup': 'transport.data', 'x-transport-date': '2005-06-15'}
    replaceDict.set_value(header)
    result = replaceDict(src)
    assert result == 'Using a dictionary: 2005-06-15'

