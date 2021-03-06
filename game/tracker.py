import kivy
kivy.require('1.0.6')

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Point, GraphicException
from random import random
from math import sqrt

from kivy.support import install_twisted_reactor
install_twisted_reactor()
from twisted.internet import reactor
from twisted.application import internet
from twisted.internet import protocol
from twisted.protocols.basic import LineReceiver
import cPickle


class TrackingClient(LineReceiver):
    def connectionMade(self):
        print "connected"
        self.factory.clients.append(self)

    def connectionLost(self, raisin):
        self.factory.clients.remove(self)

    def lineReceived(self, line):
        pass

    def send(self, msg):
        self.sendLine(msg)

class Tracker(FloatLayout):
    def connect(self):
        self.numCorners = 0
        win = self.get_parent_window()

        # SETUP
        self.flip = False

        self.real_start_y = 12
        self.real_height = -24

        self.real_start_x = -20
        #self.real_start_x = 0
        self.real_width = 20

        #print self.real_height, self.real_width

        self._ready = False;
        self._corners = [];

        self.factory = protocol.ServerFactory()
        self.factory.protocol = TrackingClient
        self.factory.clients = []

        reactor.listenTCP(1025, self.factory)

    def send(self, data):
        msg = cPickle.dumps(data)

        for c in self.factory.clients:
            c.send(msg)

    def _init_corner(self, touch):
        print len(self._corners)
        self._corners.append(touch)
        self.numCorners += 1
        if self.numCorners == 4:
            self._init_keystone()
            self._ready = True

    def _init_keystone(self):
        self._corners.sort(key = lambda touch: touch.y)

        if self._corners[0].x > self._corners[1].x:
            temp = self._corners[0]
            self._corners[0] = self._corners[1]
            self._corners[1] = temp

        if self._corners[2].x > self._corners[3].x:
            temp = self._corners[2]
            self._corners[2] = self._corners[3]
            self._corners[3] = temp

        self.start_y = self._corners[0].y
        self.height1 = self._corners[2].y - self.start_y

        self.start_x1 = self._corners[0].x
        self.start_x2 = self._corners[2].x
        self.width1 = self._corners[1].x - self._corners[0].x
        self.width2 = self._corners[3].x - self._corners[2].x

        #print (self._corners[0].x, self._corners[0].y)
        #print (self._corners[1].x, self._corners[1].y)
        #print (self._corners[2].x, self._corners[2].y)
        #print (self._corners[3].x, self._corners[3].y)


    def rectify(self, touch):
        y_percent = (touch.y - self.start_y) / self.height1

        start_x = (1 - y_percent) * self.start_x1 + y_percent * self.start_x2
        width = (1 - y_percent) * self.width1 + y_percent * self.width2
        x_percent = (touch.x - start_x) / width

        if self.flip:
            temp = x_percent
            x_percent = y_percent
            y_percent = temp

        y = self.real_start_y + (self.real_height * y_percent)
        x = self.real_start_x + (self.real_width * x_percent)

        #TODO rectify smarter
        x = touch.x
        y = touch.y

        return x, y

    def isCorner(self, touch):
        def dist2(t1, t2):
            dx = t1.x - t2.x
            dy = t1.y - t2.y
            return dx*dx + dy * dy

        for c in self._corners:
            if dist2(c, touch) < 500:
                self._corners.remove(c)
                return True

        return False

    def on_touch_down(self, touch):
        pass
        '''ud = touch.ud
        ud['group'] = g = str(touch.uid)

        #if not self._ready:
        #    self._init_corner(touch)
        #    return;

        #if self.numCorners != 4 and self.isCorner(touch):
        #    self._init_corner(touch)
        #    return

        #x, y = self.rectify(touch)
        x = touch.x
        y = touch.y
        print "TEH PTS: ", touch.x, touch.y

        ud = touch.ud
        ud['group'] = g = str(touch.uid)
        with self.canvas:
            ud['color'] = Color(random(), 1, 1, mode='hsv', group=g)
            ud['lines'] = Point(
                points = (x, y),
                source = 'particle.png',
                pointsize = 5,
                group=g)

        #self.send({'type': 'new', 'id': touch.uid, 'pos': (x, y)})
        '''

    def on_touch_move(self, touch):
        if touch in self._corners:
            return

        #x, y = self.rectify(touch)
        x = touch.x
        y = touch.y
        print "TEH PTS: ", touch.x, touch.y

        ud = touch.ud
        ud['group'] = g = str(touch.uid)
        self.canvas.remove_group(ud['group'])
        with self.canvas:
            ud['color'] = Color(touch.uid, 1, 1, mode='hsv', group=g)
            ud['lines'] = Point(
                points = (x, y),
                source = 'particle.png',
                pointsize = 5,
                group=g)

        '''try:
            ud['lines'] = Point(
                points = (x, y),
                source = 'particle.png',
                pointsize = 5,
                group=ud['group'])
        except GraphicException:
            pass
            '''

        self.send({'type': 'mov', 'id': touch.uid, 'pos': (x, y)})


    def on_touch_up(self, touch):
        pass
        '''
        if touch in self._corners:
            #self.numCorners -= 1
            return

        ud = touch.ud
        self.canvas.remove_group(ud['group'])

        self.send({'type': 'del', 'id': touch.uid})
        '''


    def update_touch_label(self, label, touch):
        pass
        '''
        label.text = 'ID: %s\nPos: (%d, %d)\nClass: %s' % (
            touch.id, touch.x, touch.y, touch.__class__.__name__)
        label.texture_update()
        label.pos = touch.pos
        label.size = label.texture_size[0] + 20, label.texture_size[1] + 20
        '''


class TrackerApp(App):
    title = 'Touchtracer'
    icon = 'icon.png'

    def build(self):
        return Tracker()

    def on_start(self):
        pass
        self.root.connect()
#        reactor.run()

if __name__ in ('__main__', '__android__'):
    TrackerApp().run()
