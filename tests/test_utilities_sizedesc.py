
from datatransport.utilities import size_desc 

def test_sizedesc_metric_b():
    value = 200 
    result = size_desc(value, metric=True) 
    assert result == '200.0 B' 

def test_sizedesc_kb():
    value = 2000 
    result = size_desc(value, metric=True) 
    assert result == '2.0 kB' 

def test_sizedesc_mb():
    value = 2000000 
    result = size_desc(value, metric=True) 
    assert result == '2.0 MB' 

def test_sizedesc_gb():
    value = 2000000000 
    result = size_desc(value, metric=True) 
    assert result == '2.0 GB' 

def test_sizedesc_tb():
    value = 2000000000000
    result = size_desc(value, metric=True) 
    assert result == '2.0 TB' 

def test_sizedesc_kib():
    value = 2000 
    result = size_desc(value) 
    assert result == '2.0 KiB' 

def test_sizedesc_mib():
    value = 2000000 
    result = size_desc(value) 
    assert result == '1.9 MiB' 

def test_sizedesc_gib():
    value = 2000000000 
    result = size_desc(value) 
    assert result == '1.9 GiB' 

def test_sizedesc_tib():
    value = 2000000000000
    result = size_desc(value) 
    assert result == '1.8 TiB' 

def test_sizedesc_precision_2():
    value = 1234 
    result = size_desc(value, metric=True, precision=2) 
    assert result == '1.23 kB' 

def test_sizedesc_precision_3():
    value = 1234 
    result = size_desc(value, metric=True, precision=3) 
    assert result == '1.234 kB' 

def test_sizedesc_boundary():
    value = 1023.95 
    result = size_desc(value, metric=True, precision=0) 
    assert result == '1 kB' 

def test_sizedesc_negative():
    value = -600 
    result = size_desc(value, metric=True, precision=0) 
    assert result == '-600 B' 



