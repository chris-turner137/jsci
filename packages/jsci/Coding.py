import json
import numpy as np
from collections import OrderedDict

class NumericEncoder(json.JSONEncoder):
  def default(self, obj):
    # Encoding complex numbers
    if isinstance(obj, complex):
      return OrderedDict([('real', obj.real), ('imag', obj.imag)])

    # Encoding numpy arrays
    if isinstance(obj, np.ndarray):
      data = obj.view(dtype=np.float64) if obj.dtype == np.complex128 else obj
      return OrderedDict([('dtype', str(obj.dtype)), ('array', data.tolist())])

    return super(NumericEncoder, self).default(obj)

class NumericDecoder(json.JSONDecoder):
  def __init__(self, encoding=None):
    json.JSONDecoder.__init__(self, encoding, object_hook=self.dict_to_object)

  def dict_to_object(self, d):
    if 'real' in d and 'imag' in d:
      real = d.pop('real')
      imag = d.pop('imag')

      if isinstance(real, float) and isinstance(imag, float):
        return complex(real, imag)

    if 'dtype' in d and 'array' in d:
      dtype = np.dtype(d.pop('dtype'))
      array = d.pop('array')

      if dtype == np.complex128:
        return np.array(array, np.float64).view(dtype=np.complex128)
      return np.array(array, dtype)
    return d

if __name__ == '__main__':
  c = 17.2 + 5.0J
  print c

  s = json.dumps(c, cls=NumericEncoder)
  print s

  print json.loads(s, cls=NumericDecoder)

  from numpy import array
  A = np.random.rand(4,4) + 1.0j * np.random.rand(4,4)
  print A

  s = json.dumps(A, cls=NumericEncoder)
  print s

  Ap = json.loads(s, cls=NumericDecoder)
  print Ap

  print np.linalg.norm(A - Ap)
