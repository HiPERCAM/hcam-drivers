from __future__ import print_function, unicode_literals, absolute_import
from twisted.web import http


class RtplotHandler(http.Request):
    """
    Server for requests from rtplot.
    The response delivers the binning factors, number of windows and
    their positions.
    """
    def process(self):
        "Send window params."
        try:
            self.setHeader('Content-Type', 'text/plain')
            wins = self.channel.instpars.getRtplotWins()
            if wins == '':
                self.write('No valid data available\r\n'.encode())
            else:
                self.write(wins.encode())
            self.finish()
        except Exception as err:
            self.channel.globals.clog.warn('RtplotServer: ', err)


class RtplotChannel(http.HTTPChannel):
    requestFactory = RtplotHandler

    def __init__(self, instpars, globals):
        http.HTTPChannel.__init__(self)
        self.instpars = instpars
        self.globals = globals


class RtplotFactory(http.HTTPFactory):
    def __init__(self, instpars, globals, **kwargs):
        self.instpars = instpars
        self.globals = globals
        http.HTTPFactory.__init__(self, **kwargs)

    def buildProtocol(self, addr):
        return RtplotChannel(self.instpars, self.globals)
