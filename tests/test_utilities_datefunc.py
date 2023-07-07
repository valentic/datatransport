
import pytest
import zoneinfo

from datetime import datetime, timedelta, timezone
from datatransport.utilities import datefunc 

@pytest.mark.parametrize('timedelta_str, expected_result', [
    ('0', timedelta()),
    ('9', timedelta(seconds=9)),
    ('5s', timedelta(seconds=5)),
    ('2:23', timedelta(minutes=2, seconds=23)),
    ('43:23', timedelta(minutes=43, seconds=23)),
    ('23:32:43', timedelta(hours=23, minutes=32, seconds=43)),
    ('1 day', timedelta(days=1)),
    ('2 days', timedelta(days=2)),
    ('2.5 days', timedelta(days=2, hours=12)),
    ('1 days 12:34:45', timedelta(days=1, hours=12, minutes=34, seconds=45)),
    ])

def test_datefunc_parse_timedelta(timedelta_str, expected_result):
    result = datefunc.parse_timedelta(timedelta_str) 
    assert result == expected_result 

@pytest.mark.parametrize('bad_timedelta_str', [
    '32:2',
    '1 days 2',
    '1 days 23:23',
    '',
    'abc'
    ])

def test_datefunc_parse_timedelta_failures(bad_timedelta_str):
    with pytest.raises(TypeError):
        result = datefunc.parse_timedelta(bad_timedelta_str) 

def test_datefunc_timedelta_as_seconds():
    td = timedelta(days=1, hours=2, minutes=3, seconds=4, microseconds=5)
    result = datefunc.timedelta_as_seconds(td)
    assert result == 93784.000005

def test_datefunc_datetime_as_seconds():
    now = datetime.now()
    result = datefunc.datetime_as_seconds(now)
    assert result == now.timestamp()

def test_datefunc_datetime_as_seconds_utc():
    now = datetime.now(timezone.utc)
    result = datefunc.datetime_as_seconds(now)
    assert result == now.timestamp()

def test_datefunc_strptime():
    s = '2004-12-25 12:34:56'
    fmt = '%Y-%m-%d %H:%M:%S'
    result = datefunc.strptime(s, fmt) 
    assert result.strftime(fmt) == s

