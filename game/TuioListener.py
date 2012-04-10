'''
TuioListener listens for Tuio messages.  Both reactivision (an off-the-shelf fiducial tracker)
and our custom LED tracking movid module output movid messages.  To use this code,
simply override function idAndPositionCallback().

One unfortunate tidbit is that the messages sent by Movid and reativision
are slightly different, and so at the moment you have to change some 
hard coding in update()
'''

'''
TUIO Input Provider
===================

TUIO is a de facto standard network protocol for the transmission of touch and
fiducial information between a server and a client.
To learn more about TUIO (which is itself based on the OSC protocol), please
refer to http://tuio.org -- The specification should be of special interest.
'''

import time

#__all__ = ('TuioMotionEventProvider', 'Tuio2dCurMotionEvent', 'Tuio2dObjMotionEvent')

#from kivy.lib import osc
import osc

from collections import deque
#from kivy.input.provider import MotionEventProvider
from kivy.input.factory import MotionEventFactory
from kivy.input.motionevent import MotionEvent
from kivy.input.shape import ShapeRect
from kivy.logger import Logger


class TuioListener:
    '''The TUIO provider listens to a socket and handles some of the incoming
    OSC messages:

        * /tuio/2Dcur
        * /tuio/2Dobj

    The TUIO provider can be configured in the configuration file in the
    ``[input]`` section::

        [input]
        # name = tuio,<ip>:<port>
        multitouchtable = tuio,192.168.0.1:3333

    You can easily extend the provider to handle new TUIO paths like so::

        # Create a class to handle the new TUIO type/path
        # Replace NEWPATH with the pathname you want to handle
        class TuioNEWPATHMotionEvent(MotionEvent):
            def __init__(self, id, args):
                super(TuioNEWPATHMotionEvent, self).__init__(id, args)

            def depack(self, args):
                # In this method, implement 'unpacking' for the received
                # arguments. you basically translate from TUIO args to Kivy
                # MotionEvent variables. If all you receive are x and y
                # values, you can do it like this:
                if len(args) == 2:
                    self.sx, self.sy = args
                    self.profile = ('pos', )
                self.sy = 1 - self.sy
                super(TuioNEWPATHMotionEvent, self).depack(args)

        # Register it with the TUIO MotionEvent provider.
        # You obviously need to replace the PATH placeholders appropriately.
        TuioMotionEventProvider.register('/tuio/PATH', TuioNEWPATHMotionEvent)

    .. note::

        The class name is of no technical importance. Your class will be
        associated with the path that you pass to the ``register()``
        function. To keep things simple, you should name your class after the
        path that it handles, though.
    '''

    __handlers__ = {}

    def __init__(self, device, args):
        #super(TuioMotionEventProvider, self).__init__(device, args)
        args = args.split(',')
        if len(args) <= 0:
            Logger.error('Tuio: Invalid configuration for TUIO provider')
            Logger.error('Tuio: Format must be ip:port (eg. 127.0.0.1:3333)')
            err = 'Tuio: Actual configuration is <%s>' % (str(','.join(args)))
            Logger.error(err)
            return None
        ipport = args[0].split(':')
        if len(ipport) != 2:
            Logger.error('Tuio: Invalid configuration for TUIO provider')
            Logger.error('Tuio: Format must be ip:port (eg. 127.0.0.1:3333)')
            err = 'Tuio: Actual configuration is <%s>' % (str(','.join(args)))
            Logger.error(err)
            return None
        self.ip, self.port = args[0].split(':')
        self.port = int(self.port)
        self.handlers = {}
        self.oscid = None
        self.tuio_event_q = deque()
        self.touches = {}

    @staticmethod
    def register(oscpath, classname):
        '''Register a new path to handle in tuio provider'''
        TuioListener.__handlers__[oscpath] = classname

    @staticmethod
    def unregister(oscpath, classname):
        '''Unregister a path to stop handling it in the tuio provider'''
        if oscpath in TuioListener.__handlers__:
            del TuioListener.__handlers__[oscpath]

    @staticmethod
    def create(oscpath, **kwargs):
        '''Create a touch from a tuio path'''
        if oscpath not in TuioListener.__handlers__:
            raise Exception('Unknown %s touch path' % oscpath)
        return TuioListener.__handlers__[oscpath](**kwargs)

    def start(self):
        '''Start the tuio provider'''
        self.oscid = osc.listen(self.ip, self.port)
        
        osc.bind(self.oscid, self._osc_tuio_cb, '')
        self.touches[''] = {}
        
        for oscpath in TuioListener.__handlers__:
            self.touches[oscpath] = {}
            osc.bind(self.oscid, self._osc_tuio_cb, oscpath)

    def stop(self):
        '''Stop the tuio provider'''
        osc.dontListen(self.oscid)

    def update(self):#, dispatch_fn):
        '''Update the tuio provider (pop events from the queue)'''

        # deque osc queue
        osc.readQueue(self.oscid)
        
        positions = []
        ids = []
        idx = 0

        # read the Queue with event
        while True:
            try:
                value = self.tuio_event_q.pop()
                
                #if value:
                #    
            except IndexError:
                # queue is empty, we're done for now
                #print ''
                break
            #print 'aaaaaaaaa_', value
            messageType = value[1][0]
            if messageType == 'set':
                
                # [!!!]
                # Learn to tell the difference between reactivision and Tuio, so you don't
                # have to use this yucky hard coding.
                
                # The Movid messages are formatted thus:
                #player_id = value[1][1]
                #player_position = [ value[1][2], value[1][3] ]
                
                # The Reactivision messages are formatted thus: 
                player_id = value[1][1]
                player_position = [ value[1][2], value[1][3] ]
                
               
                positions.append( player_position )
                ids.append( player_id )
                idx = idx + 1
        
        self.idAndPositionCallback(ids, positions)
            
            
            #self._update(dispatch_fn, value)
    
    '''
    After parsing the TUIO message, this function is called.
    ids is a an array of the ids of the identified markers,
    and positions is a list of the corresponding marker positions
    
    By default this function just prints ids and positions.           
    '''
    def idAndPositionCallback(self, ids, positions):
        print '"""""""""""""""""""""""""'
        for i in range(len(ids)):
            print 'id: ', ids[i], ' > ', positions[i]

    def _osc_tuio_cb(self, *incoming):
        message = incoming[0]
        oscpath, types, args = message[0], message[1], message[2:]
        self.tuio_event_q.appendleft([oscpath, args, types])

    def _update(self, dispatch_fn, value):
        oscpath, args, types = value
        command = args[0]

        # verify commands
        if command not in ['alive', 'set']:
            return

        # move or create a new touch
        if command == 'set':
            id = args[1]
            if id not in self.touches[oscpath]:
                # new touch
                touch = TuioListener.__handlers__[oscpath](
                    self.device, id, args[2:])
                self.touches[oscpath][id] = touch
                dispatch_fn('begin', touch)
            else:
                # update a current touch
                touch = self.touches[oscpath][id]
                touch.move(args[2:])
                dispatch_fn('update', touch)

        # alive event, check for deleted touch
        if command == 'alive':
            alives = args[1:]
            to_delete = []
            for id in self.touches[oscpath]:
                if not id in alives:
                    # touch up
                    touch = self.touches[oscpath][id]
                    if not touch in to_delete:
                        to_delete.append(touch)

            for touch in to_delete:
                dispatch_fn('end', touch)
                del self.touches[oscpath][touch.id]
        

class TuioMotionEvent(MotionEvent):
    '''Abstraction for TUIO touches/fiducials.

    Depending on the tracking software you use (e.g. Movid, CCV, etc.) and its
    TUIO implementation, the TuioMotionEvent object will support multiple
    profiles such as:

        * Fiducial ID: profile name 'markerid', attribute ``.fid``
        * Position: profile name 'pos', attributes ``.x``, ``.y``
        * Angle: profile name 'angle', attribute ``.a``
        * Velocity vector: profile name 'mov', attributes ``.X``, ``.Y``
        * Rotation velocity: profile name 'rot', attribute ``.A``
        * Motion acceleration: profile name 'motacc', attribute ``.m``
        * Rotation acceleration: profile name 'rotacc', attribute ``.r``
    '''
    __attrs__ = ('a', 'b', 'c', 'X', 'Y', 'Z', 'A', 'B', 'C', 'm', 'r')

    def __init__(self, device, id, args):
        super(TuioMotionEvent, self).__init__(device, id, args)
        # Default argument for TUIO touches
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.X = 0.0
        self.Y = 0.0
        self.Z = 0.0
        self.A = 0.0
        self.B = 0.0
        self.C = 0.0
        self.m = 0.0
        self.r = 0.0

    angle = property(lambda self: self.a)
    mot_accel = property(lambda self: self.m)
    rot_accel = property(lambda self: self.r)
    xmot = property(lambda self: self.X)
    ymot = property(lambda self: self.Y)
    zmot = property(lambda self: self.Z)

class Tuio2dCurMotionEvent(TuioMotionEvent):
    '''A 2dCur TUIO touch.'''

    def __init__(self, device, id, args):
        super(Tuio2dCurMotionEvent, self).__init__(device, id, args)

    def depack(self, args):
        self.is_touch = True
        if len(args) < 5:
            self.sx, self.sy = map(float, args[0:2])
            self.profile = ('pos', )
        elif len(args) == 5:
            self.sx, self.sy, self.X, self.Y, self.m = map(float, args[0:5])
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc')
        else:
            self.sx, self.sy, self.X, self.Y = map(float, args[0:4])
            self.m, width, height = map(float, args[4:7])
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc', 'shape')
            if self.shape is None:
                self.shape = ShapeRect()
            self.shape.width = width
            self.shape.height = height
        self.sy = 1 - self.sy
        super(Tuio2dCurMotionEvent, self).depack(args)


class Tuio2dObjMotionEvent(TuioMotionEvent):
    '''A 2dObj TUIO object.
    '''

    def __init__(self, device, id, args):
        super(Tuio2dObjMotionEvent, self).__init__(device, id, args)

    def depack(self, args):
        self.is_touch = True
        if len(args) < 5:
            self.sx, self.sy = args[0:2]
            self.profile = ('pos', )
        elif len(args) == 9:
            self.fid, self.sx, self.sy, self.a, self.X, self.Y = args[:6]
            self.A, self.m, self.r = args[6:9]
            self.Y = -self.Y
            self.profile = ('markerid', 'pos', 'angle', 'mov', 'rot',
                            'motacc', 'rotacc')
        else:
            self.fid, self.sx, self.sy, self.a, self.X, self.Y = args[:6]
            self.A, self.m, self.r, width, height = args[6:11]
            self.Y = -self.Y
            self.profile = ('markerid', 'pos', 'angle', 'mov', 'rot', 'rotacc',
                            'acc', 'shape')
            if self.shape is None:
                self.shape = ShapeRect()
                self.shape.width = width
                self.shape.height = height
        self.sy = 1 - self.sy
        super(Tuio2dObjMotionEvent, self).depack(args)


# registers
TuioListener.register('/tuio/2Dcur', Tuio2dCurMotionEvent)
TuioListener.register('/tuio/2Dobj', Tuio2dObjMotionEvent)
MotionEventFactory.register('tuio', TuioListener)

#tu = TuioListener(None, '192.168.1.100:3333')
#tu.start()
#while 1 == 1:
#    tu.update()
#    time.sleep(.2)
