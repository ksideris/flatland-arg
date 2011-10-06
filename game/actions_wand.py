"""
Input handling via wand
"""

from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import math

import pygame.event
import pygame.mouse
import pygame.time
import sys

#Added these imports for gesture recognition
import accelreader
import pickle
from copy import deepcopy


# TODO: Can we have a keymap file?
from pygame import (K_a as ATTACK,
                    K_s as SCAN,
                    K_d as BUILD,
                    K_w as UPGRADE,
                    K_ESCAPE as QUIT)

from game.vector import Vector2D


class PlayerController(object):
    """
    Input handler for L{game.player.Player} objects.

    @ivar player: The player being controlled.
    @ivar downDirections: List of currently held arrow keys.
    """
    BUTTON = 3
    JITTER_COUNT = 3
    JITTER_VOTES = 2

    def __init__(self, perspective, view):
        self.perspective = perspective
        self.position = Vector2D(0, 0)
        self.speed = 10
        self.view = view
        self._actionQueue = []
        self._currentAction = None

        #Added these for gesture recognition
        self._scan = self._loadPattern("game/pickles/scanRightPattern.pickle")
        self._upgrade = self._loadPattern("game/pickles/scanLeftPattern.pickle")
        self._attack = self._loadPattern("game/pickles/attackPattern.pickle")
        self._build = self._loadPattern("game/pickles/buildPattern.pickle")
        self._areas = self._loadPattern("game/pickles/areas.pickle")
        #this is a list of area transitions
        self._sampleData = self._initPattern(1)
        self._transitionAverages = self._initPattern(1)
        #this is the current serial data
        self._serialData = {}
        self._serialData[self.BUTTON] = 0
        self._currentPattern = None
        self._sampleCnt = 0
        self._lastPosition = (0,0,0)
        self._ser = accelreader.AccelReader()
        
        self.accelerometerPollFunc = None



    def go(self):
        self.previousTime = pygame.time.get_ticks()
        self._inputCall = LoopingCall(self._handleInput)
        d = self._inputCall.start(0.03)
        return d


    def stop(self):
        self._inputCall.stop()


    def _updatePosition(self, dt):
        if not pygame.mouse.get_focused() or not dt:
            return
        destination = self.view.worldCoord(Vector2D(pygame.mouse.get_pos()))
        direction = destination - self.position
        if direction < (self.speed * dt):
            #self.position = destination
            pass
        else:
            #self.position += (dt * self.speed) * direction.norm()
            pass
        self.perspective.callRemote('updatePosition', self.position)
        self.view.setCenter(self.position)


    def _startedAction(self, action):
        self._currentAction = action
        if self._currentAction == ATTACK:
            self.perspective.callRemote('startAttacking')
        elif self._currentAction == BUILD:
            self.perspective.callRemote('startBuilding')
        elif self._currentAction == SCAN:
            self.perspective.callRemote('startScanning')
            self.view.addAction("sweep")
        elif self._currentAction == UPGRADE:
            self.perspective.callRemote('startUpgrading')
        else:
            self._currentAction = None


    def _finishedAction(self):
        if self._currentAction == ATTACK:
            self.perspective.callRemote('finishAttacking')
        elif self._currentAction == BUILD:
            self.perspective.callRemote('finishBuilding')
        elif self._currentAction == SCAN:
            self.perspective.callRemote('finishScanning')
        elif self._currentAction == UPGRADE:
            self.perspective.callRemote('finishUpgrading')
        self._currentAction = None
        return

    def pollAccelerometer(self):
        dynamicAvg = [0, 0, 0]
        avg = [0, 0, 0]
        lastOne = [0, 0, 0]
        nChecks = 0
        nCycles = 150
    
        for i in range(0, nCycles):
            data = self._readSerial()#reader.get_pos()
            
            newToOldRatio = .2
                
            for i in range(0,3):
                #dynamicAvg[i] = dynamicAvg[i] + (data[i] - lastOne[i])*(data[i] - lastOne[i])
                #avg[i] = avg[i] + data[i]*data[i]*getSignMultiplier(data[i])
                
                dynamicAvg[i] = (1 - newToOldRatio)*dynamicAvg[i] + newToOldRatio*(data[i] - lastOne[i])*(data[i] - lastOne[i])
                avg[i]        = (1 - newToOldRatio)*avg[i] + newToOldRatio*data[i]*data[i]*self.getSignMultiplier(data[i])
                
                lastOne[i] = data[i]
                
            nChecks = (nChecks + 1) % nCycles
            
        
        #=======================================================================
        
        movingTooMuchForUpgrade = True
        
        signlessAvg = avg
        for i in range(0,3):
            #dynamicAvg[i] = dynamicAvg[i] #/ nCycles
            #avg[i] = avg[i] #/ nCycles
            signlessAvg[i] = abs(avg[i])
            movingTooMuchForUpgrade = movingTooMuchForUpgrade and dynamicAvg[i] > 7
        
        
        stormiestDimension = dynamicAvg.index(max(dynamicAvg))
        
        if self._currentAction == None:
            #check for the upgrading gesture (static)
            if signlessAvg.index(max(signlessAvg)) == 0 and avg[0] > 0 and not movingTooMuchForUpgrade:
                self._startedAction(UPGRADE)
            #check for dynamic gestures
            elif stormiestDimension == 0:
                self._startedAction(ATTACK)
            elif stormiestDimension == 1:
                self._startedAction(SCAN)
            elif stormiestDimension == 2:
                self._startedAction(BUILD)
        
        # ===== print totals ====== 
        #print "\njerk:\nX: " + str(dynamicAvg[0]) +"\nY: " +  str(dynamicAvg[1]) + "\nZ: " + str(dynamicAvg[2])
        
        
        #print "\nacc:\nX: " + str(avg[0]) +"\nY: " +  str(avg[1]) + "\nZ: " + str(avg[2]) + "\n\n"
        #=======================================================================
        


    def getSignMultiplier(self,num):
        if num < 0:
            return -1
        else:
            return 1

    def startGestureListen(self):
        self.accelerometerPollFunc = LoopingCall(self.pollAccelerometer)
        self.accelerometerPollFunc.start(.65, now=True)
        #don't start immediately because people tend not to start flailing until *after* they press the screen 

    def stopGestureListen(self):
        if self.accelerometerPollFunc and self.accelerometerPollFunc.running:
            self.accelerometerPollFunc.stop()
        self._finishedAction()
            
    def _handleInput(self):
        """
        Handle currently available pygame input events.
        """
        time = pygame.time.get_ticks()
        self._updatePosition((time - self.previousTime) / 1000.0)
        self.previousTime = time

        #If player is pressing red self.BUTTON on scepter take two samples, add them to the average, match to predefined patterns
        #updated for lack of scepter button, replacement will be if player is pressing screen
        #don't know if this is the right way to get mouse buttons from event queue
        
        for event in pygame.event.get():
            onDown = self._serialData[self.BUTTON] == 0
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._serialData[self.BUTTON] = 1
                if onDown:
                    self.startGestureListen()
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                self._serialData[self.BUTTON] = 0
                self.stopGestureListen()
        
        #buttons = pygame.mouse.get_pressed()
        #self._serialData[self.BUTTON] = buttons[0]
        #print str(self._serialData[self.BUTTON]) 

#        if self._serialData[self.BUTTON] == 1:
#            self._buildSampleData()
#            if self._sampleCnt == 2:
#                self._averageSampleData()
#                self._currentPattern = self._matchPattern()
#
#                if self._currentPattern != self._currentAction:
#                    self._actionQueue.append(self._currentPattern)
#                    if self._currentAction:
#                        self._finishedAction();
#
#        elif self._serialData[self.BUTTON] == 0 and self._currentPattern:
#            self._actionQueue = []
#            self._finishedAction()
#            #no action self.BUTTON pressed after matching a pattern; reset
#            self._currentPattern = None
#            #this could cause problems with unreliable serial connection, need to test
#            self._transitionAverages = self._initPattern(1)

        if (not self._currentAction) and self._actionQueue:
            self._startedAction(self._actionQueue.pop())

    def _matchPattern(self):
        bestFit = {
            ATTACK : self._patternDifference(self._transitionAverages, self._attack),
            UPGRADE : self._patternDifference(self._transitionAverages, self._upgrade),
            BUILD : self._patternDifference(self._transitionAverages, self._build),
            #SCAN : self._patternDifference(self._transitionAverages, self._scan),
        }

        # Returns the key (ATTACK, UPGRADE, etc) with the smallest value assigned
        return min(bestFit, key=bestFit.get)

    def _patternDifference(self,a,b):
        totalDifference = float(sys.maxint)
        for i in a.keys():
            for j in a[i].keys():
                totalDifference -= abs( a[i][j] - b[i][j] )
        totalDifference = sys.maxint - totalDifference
        return totalDifference

    def _buildSampleData(self):
        """
        reads the accelerometer and finds what area it's in.
        if the area is different from the last area checked, record the transition in self._sampleData
        """
        keys = ['x', 'y', 'z']
        #TODO [!!!] restore this line!
        data = self._readSerial()

        data = {'x': data[0], 'y': data[1], 'z': data[2]}
        results = {}
        for k in keys:
            if data[k] < self._areas[k][0]: results[k] = 0
            elif data[k] < self._areas[k][1]: results[k] = 1
            else: results[k] = 2
        currentPosition = (results['x'], results['y'], results['z'])
        if self._lastPosition != currentPosition:
            self._sampleData[self._lastPosition][currentPosition] += 1
            self._lastPosition = currentPosition
            self._sampleCnt += 1

    def _averageSampleData(self):
        """
        when two new transitions have been recorded by buildSampleData()
        this function takes self._tempData and averages it with self._sampleData
        """
        temp = self._sampleData
        for i in temp.keys():
            for j in temp[i].keys():
                self._sampleData[i][j] = temp[i][j] / float(self._sampleCnt)
        if self._transitionAverages:
            temp = deepcopy(self._transitionAverages)
            for i in temp.keys():
                for j in temp[i]:
                    self._transitionAverages[i][j] = ( temp[i][j] + self._sampleData[i][j] ) / 2.0
        #reset vars for buildSampleData()
        self._sampleData = self._initPattern(1)
        self._sampleCnt = 0


    def _readSerial(self):
        return self._ser.get_pos()


    def _initPattern(self,level):
        p = {}
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if level > 0:
                        p[i,j,k] = self._initPattern(level-1)
                    else:
                        p[i,j,k] = 0
        return p


    def _loadPattern(self,fileName):
        #with open(str(fileName), 'rb') as f:
        #    return pickle.load(f)
        try:
            f = open(str(fileName), 'rb')
            return pickle.load(f)
        finally:
            f.close()
