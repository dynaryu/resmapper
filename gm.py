class GM(object):

    def __init__(self, **kwaargs):

        self.GIS_ID = kwargs['GIS_ID']
        self.Mw = kwargs['Mw']
        self.PGA = kwargs['PGA']
        self.Sa1 = kwargs['Sa1g']

    def __repr__(self):
        return repr(f'Mw: {self.Mw}, PGA: {self.PGA}, Sa1: {self.Sa1}')

