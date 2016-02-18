# jsci
Python library for processing numerical JSON data.

## Installation

Simply clone this repository and put the packages subdirectory on your PYTHONPATH environment variable.

## Usage

### WriteStream: streaming JSON output

The `WriteStream` interface accepts messages defining a stream of JSON events. The `FileWriteStream` implementation demonstrated here
converts this into a character stream written to a file.

```python
from jsci.WriteStream import FileWriteStream

out = FileWriteStream(sys.stdout, indent=2)
with out.wrap_array():
  for i in xrange(3):
    with out.wrap_object():
      out.write_pair('iteration', i)
      out.write_key('data')
      with out.wrap_array():
        for s in ['a','b','c']:
          out.write_value(s * i)
```

This writes the following to standard output
```javascript
[
  {
    "iteration": 0,
    "data": [
      "",
      "",
      ""
    ]
  },
  {
    "iteration": 1,
    "data": [
      "a",
      "b",
      "c"
    ]
  },
  {
    "iteration": 2,
    "data": [
      "aa",
      "bb",
      "cc"
    ]
  }
]
```

### NumericEncoder and NumericDecoder: handling NumPy arrays

NumericEncoder and NumericDecoder interface with the python standard library to serialise (and deserialise respectively) NumPy arrays and complex number to a JSON representation.

```python
import json
import numpy as np
from jsci.Coding import NumericEncoder, NumericDecoder

data = {
  'T': np.array([1.0, 2.0, 7.0]),
  'lambda': np.array([1.0+0.1j, 19-0.2j])
}

strep = json.dumps(data, cls=NumericEncoder)
print(strep)

print(json.loads(strep, cls=NumericDecoder))
```

This writes the following to standard output
```javascripts
{"T": {"dtype": "float64", "array": [1.0, 2.0, 7.0]}, "lambda": {"dtype": "complex128", "array": [1.0, 0.1, 19.0, -0.2]}}
{u'T': array([ 1.,  2.,  7.]), u'lambda': array([  1.+0.1j,  19.-0.2j])}
```
