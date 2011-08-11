# -*- test-case-name: game.test.test_controller -*-

"""
Input handling.
"""

from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import math

import pygame.event
import pygame.mouse
import pygame.time
import sys

#Added these imports for gesture recognition
import os
import serial
import pickle
import atexit
import time
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
    _actions = set([ATTACK, SCAN, BUILD, UPGRADE])
    
    def __init__(self, perspective, view):
        self.perspective = perspective
        self.position = Vector2D(0, 0)
        self.speed = 10
        self.view = view
        self._actionQueue = []
        self._currentAction = None

        #Added these for gesture recognition
        self._attackRight = loadPattern("pickles/attackRightPattern.pickle")
        self._attackLeft = loadPattern("pickles/attackLeftPattern.pickle")
        self._scan = loadPattern("pickles/scanPattern.pickle")
        self._build = loadPattern("pickles/buildPattern.pickle")
        self._bestFit = {}
        self._sample = None
        self._currentSerialData = None
        self._scepterBtnPressed = False
        try:
            self._ser = serial.Serial('/dev/ttyUSB0', 9600)
            self._ser.readline()
            self._ser.readline()
            self._ser.flush()
        except serial.serialutil.SerialException as detail:
            print 'Serial error:', detail


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
            self.position = destination
        else:
            self.position += (dt * self.speed) * direction.norm()
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


    def _handleInput(self):
        """
        Handle currently available pygame input events.
        """
        time = pygame.time.get_ticks()
        self._updatePosition((time - self.previousTime) / 1000.0)
        self.previousTime = time
        #If player is pressing red button on scepter take two samples and add them to the average
        self._serialData = readSerial()
        if (self._serialData[3]):
            # TODO: To make this non blocking we would want to do this in two stages
            # essentially rewrite getSampleData as two seperate functions:
            # buildSampleData() and averageSampleData()
            self._sample = getSampleData(2, self._sample)
            currentPattern = matchPattern()
        else:
            currentPattern = None
            

        for event in pygame.event.get():
            if (event.type == pygame.QUIT) or ((event.type == pygame.KEYDOWN) and (event.key == QUIT)):
                reactor.stop()
                sys.exit()
            if (event.type == pygame.KEYDOWN) and (event.key in self._actions):
                self._actionQueue.append(event.key)
            elif (event.type == pygame.KEYUP) and (event.key in self._actions):
                if self._currentAction == event.key:
                    self._finishedAction()
                else:
                    self._actionQueue.remove(event.key)

        if (not self._currentAction) and self._actionQueue:
            self._startedAction(self._actionQueue.pop())

    def matchPattern(self):
        bestFit['attackRight'] = patternDifference(self._sample, attackRight)
        bestFit['attackLeft'] = patternDifference(self._sample, attackLeft)
        bestFit['build'] = patternDifference(self._sample, build)
        bestFit['scan'] = patternDifference(self._sample, scan)
        return min(bestFit, key=bestFit.get)

    def patternDifference(a,b):
        totalDifference = float(sys.maxint)
        for i in a.keys():
            for j in a[i].keys():
                totalDifference -= abs( a[i][j] - b[i][j] )
        totalDifference = sys.maxint - totalDifference
        return totalDifference


    def getSampleData(sampleLength, averageSoFar=None):
        """
        Get some sample data in the form of a nested dictionary.m length
        Value is the percentage of times a transition happened, transition is defined in the dictionary
        Keys of dictionaries are tuples that represent spacial coordinates.
        """
        sampleData = initPattern(1)
        lastPosition = (0,0,0)
        areas = loadPattern("pickles/areas.pickle")
        counter = 0
        #here we would get rid of the while loop and just do this once per call in buildSampleData()
        while counter < sampleLength:
            keys = ['x', 'y', 'z']
            data = {'x': self._serialData[0], 'y': self._serialData[1], 'z': self._serialData[2]}
            results = {}
            for k in keys:
                if data[k] < areas[k][0]: results[k] = 0
                elif data[k] < areas[k][1]: results[k] = 1
                else: results[k] = 2

            currentPosition = (results['x'], results['y'], results['z'])
            if lastPosition != currentPosition:
                sampleData[lastPosition][currentPosition]+=1
                lastPosition = currentPosition
                #this counter could be a global property that is used to decide when sample data is built and ready to be averaged
                counter+=1

        #here is where we would break off the function to build averageSampleData()
        temp = deepcopy(sampleData)
        for i in temp.keys():
            for j in temp[i].keys():
                sampleData[i][j] = temp[i][j] / float(sampleLength)
        if averageSoFar:
            temp = deepcopy(sampleData)
            for i in temp.keys():
                for j in temp[i]:
                    sampleData[i][j] = (temp[i][j] + averageSoFar[i][j]) / 2.0
        return sampleData



    def readSerial():
        try:
            data = ser.readline()
        except (KeyboardInterrupt, SystemExit):
            raise
        except serial.serialutil.SerialException as detail:
            print 'Serial error:', detail
        else:
            data = data.split()
            for i in range(len(data)): data[i] = int(data[i])
            return data
