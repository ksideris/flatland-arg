'''
This inappropriately named file, is in fact the *game* server.

After you run the game server, you can control the game with the keyboard:
    's' to start
    'escape' to close the server
    'r' to reset the game
    
See ServerKeyboardController.py for more information, or to add new controls.
'''


# for getting tracker messages
from TuioListener import TuioListener

import pygame.event

from game.environment import Environment
from game.view import Window

from zope.interface import implements

from twisted.cred import checkers, portal
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from twisted.spread import pb
from twisted.internet.protocol import DatagramProtocol

from game.ServerKeyboardController import ServerController

from vector import Vector2D
#costas
hasTrackingServer = True
try:
    from TrackingServer import *
except ImportError:
    hasTrackingServer = False
    print "WARNING! TrackingServer module not found. Obviously, tracking won't work"


MAX_DISTANCE2 = 5
MAX_SPEED = 10

class GameRealm:
    implements(portal.IRealm)

    def __init__(self):
        self._team = 1

    def _getTeam(self):
        if self._team == 1:
            self._team = 2
            
        elif self._team == 2:
            self._team = 1
            
        return self._team

    def requestAvatar(self, avatarId, mind, *interfaces):
        assert pb.IPerspective in interfaces
        assert avatarId is checkers.ANONYMOUS
        avatar = GameAvatar(self.environment, self._getTeam())
        return pb.IPerspective, avatar, avatar.disconnect

class GameAvatar(pb.Avatar):
    def __init__(self, environment, team):
        self.environment = environment
        self.player = self.environment.createPlayer(team)
        #tm.addPlayer(self.player)
    def disconnect(self):
        self.environment.removePlayer(self.player)
    def perspective_startAttacking(self):
        self.environment.startAttacking(self.player)
    def perspective_finishAttacking(self):
        self.environment.finishAction(self.player)
    def perspective_startBuilding(self):
        self.environment.startBuilding(self.player)
    def perspective_finishBuilding(self):
        self.environment.finishAction(self.player)
    def perspective_startScanning(self):
        self.player.startScanning()
    def perspective_finishScanning(self):
        self.player.finishScanning()
    def perspective_startUpgrading(self):
        self.environment.startUpgrading(self.player)
    def perspective_finishUpgrading(self):
        self.environment.finishUpgrading(self.player)
    def perspective_updatePosition(self, position):

        #TODO tracker is doing some kind of update too.
        #make it such that keyboard and server don't "fight"
        self.environment.updatePlayerPosition(self.player, position)

    def perspective_getEnvironment(self):
        return self.environment
    def perspective_getTeam(self):
        return self.player.team
    def perspective_switchTeams(self):
        return self.environment.switchTeams(self.player)
    #TODO could we add a perspective_getPosition and perspective_getIRTargetStatus here
    #TODO otherwise, how do we do remote call on a client?


pygame.init()
pygame.display.set_mode((1600, 960), pygame.DOUBLEBUF)#| pygame.FULLSCREEN)
realm = GameRealm()
env = Environment()
view = Window(env)

# [!!!] initialize and run the server keyboard listener
controller = ServerController(realm, view)
controller.go()
'''
class MovidTuioListener(TuioListener):
    def idAndPositionCallback(self, ids, positions):
    	for i in range(len(ids)):
            #print 'id: ', ids[i], ' > ', positions[i]
            
            px = 50*(positions[i][0] - .5)
            py = 50*(positions[i][1] - .5)
            env.updatePlayerPositionByIndex(ids[i]%10, Vector2D(px, py))

# [!!!] Listen for TUIO events from the tracker
tu = MovidTuioListener(None, # listen at IP:port
'127.0.0.1:3333') #This is the ip:port for Movid
# '127.0.0.1:7500') # reactiVISION's deafault ip and port
#tu.start()
'''
if hasTrackingServer:
    class TrackingListener(TrackingServer):
        def ReadPoints(self):
        	if(self.ready):
        		self.reading = True
    	    	for i in range(len(self.ids)):
    			print 'id: ', self.ids[i], ' > ', self.positions[i]
    			    
    			px = 50*(self.positions[i][0] - .5)
    			py = 50*(self.positions[i][1] - .5)
    			env.updatePlayerPositionByIndex(self.ids[i]%10, Vector2D(px, py))
    		self.reading = False
    
    
    Tracker = TrackingListener();
    Tracker.start()
    
    
    def readTrackPoints():
       # tu.update()
       Tracker.ReadPoints()
    
    LoopingCall(readTrackPoints).start(0.06)

realm.environment = env
view.start('Server')
LoopingCall(lambda: pygame.event.pump()).start(0.03)

controller = ServerController(realm, view)
controller.go()

portal = portal.Portal(realm, [checkers.AllowAnonymousAccess()])

reactor.listenTCP(8800, pb.PBServerFactory(portal))


from twisted.protocols.basic import LineReceiver
from twisted.internet import protocol
import cPickle

p = reactor.listenUDP(0, DatagramProtocol())
LoopingCall(lambda: p.write("FlatlandARG!!!", ("224.0.0.1", 8000))).start(1)
reactor.run()
