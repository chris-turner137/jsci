import json

def iterload(f, **kwargs):
  """
  Takes a stream of JSON values concatenated (and perhaps separated by
  whitespace) and generates Python representations for each value. The entirety
  of a single value must be read into memory.

  This idea comes from a stackoverflow post I saw a while back.
  """
  seek = 0
  while True:
    try:
      item = json.load(f, **kwargs)
      yield item
      return
    except json.JSONDecodeError as e:
      # The exception tells you where the error is. Assume this was due to 
      # the next value following the first value, this tells you where to chop.
      f.seek(seek)
      item = json.loads(f.read(e.pos), **kwargs)
      seek += e.pos
      yield item
