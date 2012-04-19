#!/usr/bin/env python

from liblo import *
import sys

DEBUG=False
class TrackingServer(ServerThread):

    positions = []
    ids = []
    ready=False
    reading=False
    def __init__(self):
        ServerThread.__init__(self, 1234)

    @make_method('/trackingPoints', 'iff')
    def PointsCallback(self, path, args):
        i, x, y = args
        if(not self.reading):
        	self.ids.append(i)
        	self.positions.append((x,y))
        if(DEBUG):
        	print "received message '%s' with arguments: %d, %f, %f" % (path, i, x, y)
        
    @make_method('/Start', None)
    def StartCallBack(self, path, args):
    	if(not self.reading):
	    	self.positions = []
	    	self.ids = []
	    	self.ready=False
        if(DEBUG):
        	print  "received '%s' message " % path

    @make_method('/End', None)
    def EndCallBack(self, path, args):
    	if(not self.reading):
    		self.ready=True
        if(DEBUG):
        	print "received '%s' message " % path
        
    @make_method(None, None)
    def fallback(self, path, args):
        if(DEBUG):
        	print "received unknown message '%s'" % path

    def ReadPoints():
    	self.reading = True
    	if(self.ready):
    		self.reading = False
    		return self.ids,self.positions
    	else:
    		self.reading = False
    		return False,False
'''    		
try:
    server = TrackingServer()
except ServerError, err:
    print str(err)
    sys.exit()

server.start()
raw_input("press enter to quit...\n")
'''
