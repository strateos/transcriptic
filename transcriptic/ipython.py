import json

class Render(object):
  def __init__(self, obj):
    self.obj = obj

  def _repr_html_(self):
    if self.obj.__class__.__name__ == 'Protocol':
      p = json.dumps(self.obj.as_dict())
      return """<div id='cards'></div><script type='text/javascript'>
        React.render(rtag(RunInstructions, { run: Run.fromRaw(%s)}), document.getElementById('cards'))""" % p
    else:
      return "<h1>" + self.obj.__class__.__name__ + "</h1>"
