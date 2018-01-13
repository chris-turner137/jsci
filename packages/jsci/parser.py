"""
Tools for transforming JSON data in a memory-conscious manner.
Elements of this file were adapted from the JSON example in the lark repository.
"""
from lark import Lark, inline_args, Transformer
from abc import ABCMeta, abstractmethod

json_grammar = """
?start: value

value: object
    | array
    | string
    | SIGNED_NUMBER      -> number
    | "true"             -> true
    | "false"            -> false
    | "null"             -> null

array       : start_array [element ("," element)*] end_array
start_array : "["
end_array   : "]"
object  : "{" [pair ("," pair)*] "}"
pair    : key ":" value
key     : string
element : value

string : ESCAPED_STRING

%import common.ESCAPED_STRING
%import common.SIGNED_NUMBER
%import common.WS

%ignore WS
"""

class DefaultTransformer(Transformer):
  """
  Transformer from the abstract syntax tree to the canonical Python
  representation for JSON data.
  """
  def _get_func(self, name):
    return getattr(self, '_' + name)

  @inline_args
  def _string(self, s):
    return s[1:-1].replace('\\"', '"')

  def parser(self):
    """
    Produces a callback which can be used to parse files, strings etc.
    """
    return Lark(json_grammar, parser='lalr', transformer=self).parse

  _array = lambda self, s: list(s[1:-1])
  _pair = tuple
  _object = dict
  _number = inline_args(float)

  _null = lambda self, _: None
  _true = lambda self, _: True
  _false = lambda self, _: False
  _key = lambda self, s: s[0]
  _value = lambda self, s: s[0]
  _element = lambda self, s: s[0]
  _start_array = lambda self, _: None
  _end_array = lambda self, _: None

class SelectorTransformer(DefaultTransformer,metaclass=ABCMeta):
  """
  Pushdown automaton tracking context as a building block for transforming
  subtrees of the JSON tree
  """
  @abstractmethod
  def value(self, s, x):
    """
    Abstract method to be overrided for implementing subtree transformations.
    The selector is provided to give context for the subtree.

    Parameters
    ----------
    s : Selector for the subset within the provided dataset.
    x : Transformed data for that subset.
    """
    raise NotImplementedError

  def __init__(self):
    self._stack = []

  def _key(self, s):
    self._stack.append(s[0])
    return s[0]

  def _value(self, s):
    return self.value(self._stack, s[0])

  def _pair(self, s):
    self._stack.pop()
    return tuple(s)

  def _array(self, s):
    return s[1:-1]

  def _start_array(self, s):
    self._stack.append(0)
    return None

  def _end_array(self, s):
    self._stack.pop()
    return None

  def _element(self, s):
    self._stack[-1] += 1
    return s[0]

class CallbackSelectorTransformer(SelectorTransformer):
  """
  Delegates the transformer definition to a callback function.
  """
  def __init__(self, callback):
    """
    Parameters
    ----------
    callback : Function to bind.
    """
    super().__init__()
    self._callback = callback

  def value(self, s, x):
    return self._callback(s, x)

class PrintingTransformer(SelectorTransformer):
  def value(self, s, x):
    print(".{} = {}".format('.'.join(map(str, s)), x))
    return x

if __name__ == '__main__':
  import json
  test_json = '''
    {
      "empty_object" : {},
      "empty_array"  : [],
      "booleans"     : { "YES" : true, "NO" : false },
      "numbers"      : [ 0, 1, -2, 3.3, 4.4e5, 6.6e-7 ],
      "strings"      : [ "This", [ "And" , "That", "And a \\"b" ] ],
      "nothing"      : null
    }
  '''
  parse = PrintingTransformer().parser()
  j = parse(test_json)
  print(j)
  assert j == json.loads(test_json)
