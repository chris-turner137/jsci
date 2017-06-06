import json
from contextlib import contextmanager
try:
  from enum import Enum # This package doesn't seem to be available on Polaris.
except:
  Enum = object
from abc import ABCMeta, abstractmethod

class WriteStream(object):
  """
  Interface which accepts a stream of JSON events as method calls. Includes
  some convenience methods implemented in terms of the abstract methods.
  """
  __metaclass__ = ABCMeta

  @abstractmethod
  def flush(self):
    """
    Flush any underlying file object etc. In other cases should be taken as
    encouragement to eagerly process any buffered data.
    """
    raise NotImplementedError

  @abstractmethod
  def enter_array(self):
    """
    Starts an array. Use wrap_array instead of this method.
    """
    raise NotImplementedError

  @abstractmethod
  def exit_array(self):
    """
    Ends an array. Use wrap_array instead of this method.
    """
    raise NotImplementedError

  @abstractmethod
  def enter_object(self):
    """
    Starts an object. Use wrap_object instead of this method.
    """
    raise NotImplementedError

  @abstractmethod
  def exit_object(self):
    """
    Ends an object. Use wrap_object instead of this method.
    """
    raise NotImplementedError

  @contextmanager
  def wrap_array(self):
    """
    Context manager for wrapping the values of an array in an exception safe
    manner.
    """
    self.enter_array()
    try:
      yield
    finally:
      self.exit_array()

  @contextmanager
  def wrap_object(self):
    """
    Context manager for wrapping the key-value pairs of an array in an exception
    safe manner.
    """
    self.enter_object()
    try:
      yield
    finally:
      self.exit_object()

  @abstractmethod
  def write_key(self, key):
    """
    Write the key for a key-value pair.

    Parameters
    ----------
    key : The key for the key-value pair.
    """
    raise NotImplementedError

  @abstractmethod
  def write_value(self, value, cls=None):
    """
    Write a value as an element of an array of as the value of a key-value pair.

    Parameters
    ----------
    value : Value to write as element of an array or value of a key-value pair.
    cls   : json.JSONEncoder implementation to pass the value through.
    """
    raise NotImplementedError

  def write_pair(self, key, value, cls=None):
    """
    Write a key-value pair into the current object. If writing the value raises
    an exception then 'null' is written.

    Parameters
    ----------
    key   : (string) Key for the pair.
    value : Value for the pair.
    cls   : json.JSONEncoder implementation to pass the value through.
    """
    self.write_key(key)
    try:
      self.write_value(value, cls)
    except:
      self.write_value(None)
      raise

  @abstractmethod
  def unwind(self):
    """
    Reset the stream to the root level finishing all arrays, object and pairs.
    """
    raise NotImplementedError

class NullWriteStream(WriteStream):
  """
  Trivial implementation of the WriteStream interface which happily ignores
  all messages received.
  """
  def __init__(self):
    pass

  def flush(self):
    pass

  def enter_array(self):
    pass

  def exit_array(self):
    pass

  def enter_object(self):
    pass

  def exit_object(self):
    pass

  def write_key(self, key):
    pass

  def write_value(self, value, cls=None):
    pass

  def unwind(self):
    pass

class StreamState(Enum):
  predoc    = 1 # Initial state
  postdoc   = 2 # After finishing a root value
  in_array  = 3 # After '['
  in_object = 4 # After '{'
  in_pair   = 5 # After ':' separator in a key-value pair
  post_pair = 6 # After value in key-value pair; before ',' separator
  post_elem = 7 # After value in array; before ',' separator

class FileWriteStream(WriteStream):
  """
  Implementation of the WriteStream interface which serialises JSON from events
  to text and writes it to a file object.
  """
  def __init__(self, file, indent=0):
    self.file = file
    self.indent = indent
    self.depth = 0
    self.stack = [StreamState.predoc]

  def flush(self):
    self.file.flush()

  def enter_array(self):
    prev = self.stack[-1]
    if prev == StreamState.post_pair or prev == StreamState.post_elem:
      self.file.write(',\n' + ' '*(self.depth * self.indent))
    elif prev != StreamState.in_pair:
      self.file.write('\n' + ' '*(self.depth * self.indent))
    self.file.write('[')
    self.depth += 1
    self.stack.append(StreamState.in_array)

  def _post_value(self):
    """ State transitions for after a value is finished. """
    if self.stack[-1] == StreamState.in_pair:
      self.stack[-1] = StreamState.post_pair
    if self.stack[-1] == StreamState.predoc:
      self.stack[-1] = StreamState.postdoc
    if self.stack[-1] == StreamState.in_array:
      self.stack[-1] = StreamState.post_elem

  def exit_array(self):
    if self.stack[-1] == StreamState.post_elem:
      self.stack[-1] = StreamState.in_array
      self.file.write('\n')
      return self.exit_array()
    if self.stack[-1] != StreamState.in_array:
      raise RuntimeError(self.stack[-1])
    self.stack.pop()
    self.depth -= 1
    self.file.write(' '*(self.depth * self.indent) + ']')
    self._post_value()

  def enter_object(self):
    prev = self.stack[-1]
    if prev == StreamState.in_pair:
      pass
    elif prev == StreamState.predoc:
      self.file.write(' '*(self.depth * self.indent))
    elif prev == StreamState.post_pair or prev == StreamState.post_elem:
      self.file.write(',\n' + ' '*(self.depth * self.indent))
    else:
      self.file.write('\n' + ' '*(self.depth * self.indent))
    self.file.write('{\n')
    self.depth += 1
    self.stack.append(StreamState.in_object)

  def exit_object(self):
    if self.stack[-1] == StreamState.post_pair:
      self.stack[-1] = StreamState.in_object
      self.file.write('\n')
      return self.exit_object()
    if self.stack[-1] != StreamState.in_object:
      raise RuntimeError
    self.stack.pop()
    self.depth -= 1
    self.file.write(' '*(self.depth * self.indent) + '}')
    self._post_value()

  def write_key(self, key):
    if self.stack[-1] == StreamState.post_pair:
      self.file.write(',\n')
    elif self.stack[-1] != StreamState.in_object:
      raise RuntimeError
    self.file.write(' '*(self.depth * self.indent) + json.dumps(key) + ': ')
    self.stack[-1] = StreamState.in_pair

  def write_value(self, obj, cls=None):
    if self.stack[-1] == StreamState.in_object:
      raise RuntimeError
    elif self.stack[-1] == StreamState.in_array:
      self.file.write('\n' + ' '*(self.depth * self.indent))
      s = json.dumps(obj, cls=cls, indent=self.indent)
      self.file.write(s.replace('\n', '\n' + ' '*(self.depth * self.indent)))
      self.stack[-1] = StreamState.post_elem
    elif self.stack[-1] == StreamState.post_elem:
      self.file.write(',')
      self.stack[-1] = StreamState.in_array
      return self.write_value(obj, cls)
    elif self.stack[-1] == StreamState.in_pair:
      s = json.dumps(obj, cls=cls, indent=self.indent)
      self.file.write(s.replace('\n', '\n' + ' '*(self.depth * self.indent)))
      self.stack[-1] = StreamState.post_pair
    elif self.stack[-1] == StreamState.predoc:
      s = json.dumps(obj, cls=cls, indent=self.indent)
      self.file.write(s.replace('\n', '\n' + ' '*(self.depth * self.indent)))
      self.stack[-1] = StreamState.post_pair
    else:
      raise RuntimeError(self.stack[-1])

  def unwind(self):
    while self.stack[-1] != self.predoc and self.stack[-1] != self.predoc:
      state = self.stack[-1]
      if state == StreamState.in_array or state == StreamState.post_elem:
        exit_array()
      elif state == StreamState.in_object or state == StreamState.post_pair:
        exit_object()
      elif state == StreamState.in_pair:
        self.write_value(None)
      else:
        break

class MemoryWriteStream(WriteStream):
  """
  Implement of the WriteStream interface which constructs an in memory
  representation of the event stream.
  """
  def __init__(self):
    self.state = [StreamState.predoc]
    self.value = [[]]

  def flush(self):
    pass

  def enter_array(self):
    value = []
    self.write_value(value)
    self.state.append(StreamState.in_array)
    self.value.append(value)

  def exit_array(self):
    prev_state = self.state[-1]
    if (prev_state != StreamState.post_elem
        and prev_state != StreamState.in_array):
      raise ValueError(prev_state)
    self.state.pop()
    self.value.pop()

  def enter_object(self):
    value = {}
    self.write_value(value)
    self.state.append(StreamState.in_object)
    self.value.append(value)

  def exit_object(self):
    prev_state = self.state[-1]
    if (prev_state != StreamState.post_pair
        and prev_state != StreamState.in_object):
      raise ValueError(prev_state)
    self.state.pop()
    self.value.pop()

  def write_key(self, key):
    prev_state = self.state[-1]
    if (prev_state != StreamState.post_pair
        and prev_state != StreamState.in_object):
      raise ValueError(prev_state)
    self.key = key
    self.state[-1] = StreamState.in_pair

  def write_value(self, value, cls=None):
    if cls is not None:
      value = cls().default(value)
    prev_state = self.state[-1]
    if (prev_state == StreamState.in_array
        or prev_state == StreamState.post_elem
        or prev_state == StreamState.predoc
        or prev_state == StreamState.postdoc):
      self.value[-1].append(value)
      self.state[-1] = StreamState.post_elem
    elif prev_state == StreamState.in_pair:
      self.value[-1].update({self.key: value})
      self.state[-1] = StreamState.post_pair
    elif prev_state == StreamState.predoc:
      self.value[-1].append(value)
      self.state[-1] = StreamState.postdoc
    else:
      raise ValueError(prev_state)

  def unwind(self):
    if self.state[-1] == StreamState.predoc:
      return
    else:
      self.state = [StreamState.postdoc]
      self.value = [self.value[0]]

if __name__ == '__main__':
  # TODO: Write some proper unit tests
  import sys
  from builtins import range

  NullWriteStream()

  def write_to(stream):
    stream.enter_array()
    stream.enter_object()
    stream.write_pair('model', {'parameters': {'L': 16, 'J': 1.0}})
    stream.write_key('results')
    with stream.wrap_array():
      stream.write_value([12.0, 15.0, "hi"])
      stream.write_value("long long langweilig")
    stream.exit_object()
    stream.exit_array()

  output = FileWriteStream(sys.stdout, indent=2)
  write_to(output)
  sys.stdout.write('\n')

  def write_to(stream):
    with stream.wrap_array():
      for i in range(10):
        with stream.wrap_array():
          for j in range(10):
            with stream.wrap_object():
              stream.write_pair('key', 'value')

  output = FileWriteStream(sys.stdout, indent=2)
  write_to(output)
  sys.stdout.write('\n')
