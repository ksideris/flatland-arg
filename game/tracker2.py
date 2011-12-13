#import os
#os.environ['KIVY_WINDOW'] = 'None'
import kivy
kivy.require('1.0.6')

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Point, GraphicException
from random import random
from math import sqrt
from kivy.uix.widget import Widget
from kivy.graphics.instructions import Canvas

class TrackerListenerChild(FloatLayout):

    

    def on_touch_move(self, touch):
        #x, y = self.rectify(touch)
        x = touch.x
        y = touch.y
        print "TEH PTS: ", x, y
        '''
        

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
        
        '''

    def on_touch_up(self, touch):
        pass
        '''
        ud = touch.ud
        self.canvas.remove_group(ud['group'])
        self.remove_widget(ud['label'])
        '''


class NonCanvas(Canvas):
    def draw(self):
        print('MOTH!!!!!!!!!')
        pass
    def clear(self):
        pass

class TrackerListener(App):
    title = 'Touchtracer'
    icon = 'icon.png'

    def build(self):
        
        parent = TrackerListenerChild()
        self.canvas = NonCanvas();

        return parent

    
TrackerListener().run()