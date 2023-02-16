class Node(object):

    def __init__(self, **kwargs):

        self.GIS_ID = kwargs['GIS_ID']
        self.type = kwargs['type']
        assert isinstance(kwargs['clearPriority'], bool), 'clearPriority must be either 1 (yes) or 0 (no).'
        self.clearPriority = kwargs['clearPriority']

    def __repr__(self):
        return repr(f'type: {self.type}, clearPriority: {self.clearPriority}')


