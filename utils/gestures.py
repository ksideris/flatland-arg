#!/usr/bin/env python
# encoding: utf-8
"""
gestures.py

"""

import os
import sys
import getopt
import pickle
import atexit
import accelreader
from copy import deepcopy
import pygame.time


help_message = '''
Use -l, --limits to set the min and max limits for the sensor
Use -c or --calibrate with name of pattern you want to calibrate
e.g. scan, build or attack


-l, --limits will set the range of the accelerometer
-m, --getSample will take sample data and compare it with save patterns
'''

reader = accelreader.AccelReader()

# these are used to define the limits of the sensor
maxData = [0,0,0]
minData = [255,255,255]


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "hc:lm", ["help", "calibrate=", "limits", "match"])
        except getopt.error, msg:
            raise Usage(msg)
            
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-c", "--calibrate"):
                calibratePattern(value)
            if option in ("-l", "--limits"):
                defineLimits()
            if option in ("-m", "match"):
                matchPattern()
                
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2


def calibratePattern(pattern):
    try:
        tempPattern = loadPattern("pickles/"+pattern+"Pattern.pickle")
    except IOError:
        print "can't find saved data"
        tempPattern = None

    if tempPattern: tempPattern = getSampleData(100,tempPattern)
    else: tempPattern = getSampleData(100)

    print "pattern calibrated"
    savePattern(tempPattern, "pickles/"+pattern+"Pattern.pickle")



def matchPattern():
    scanRight = loadPattern("pickles/scanRightPattern.pickle")
    scanLeft = loadPattern("pickles/scanLeftPattern.pickle")
    attack = loadPattern("pickles/attackPattern.pickle")
    build = loadPattern("pickles/buildPattern.pickle")
    bestFit = {}
    sample = None
    while 1:
        sample = getSampleData(2, sample)
        bestFit['scanRight'] = patternDifference(sample, scanRight)
        bestFit['scanLeft'] = patternDifference(sample, scanLeft)
        bestFit['build'] = patternDifference(sample, build)
        bestFit['attack'] = patternDifference(sample, attack)
        print min(bestFit, key=bestFit.get)

def patternDifference(a,b):
    totalDifference = float(sys.maxint)
    for i in a.keys():
        for j in a[i].keys():
            totalDifference -= abs( a[i][j] - b[i][j] )
    totalDifference = sys.maxint - totalDifference
    return totalDifference

def defineLimits():
    while True:
        try:
            dynamicAvg = [0, 0, 0]
            avg = [0, 0, 0]
            lastOne = [0, 0, 0]
            nChecks = 0
            nCycles = 75
        
            for i in range(0, nCycles):
                data =  reader.get_pos()
                
                newToOldRatio = .2
                    
                for i in range(0,3):
                    #dynamicAvg[i] = dynamicAvg[i] + (data[i] - lastOne[i])*(data[i] - lastOne[i])
                    #avg[i] = avg[i] + data[i]*data[i]*getSignMultiplier(data[i])
                    
                    dynamicAvg[i] = (1 - newToOldRatio)*dynamicAvg[i] + newToOldRatio*(data[i] - lastOne[i])*(data[i] - lastOne[i])
                    avg[i]        = (1 - newToOldRatio)*avg[i] + newToOldRatio*data[i]*data[i]*getSignMultiplier(data[i])
                    
                    lastOne[i] = data[i]
                    
                nChecks = (nChecks + 1) % nCycles
                pygame.time.wait(10)
                
            
            #=======================================================================
            
            movingTooMuchForUpgrade = False
            movingSlowEnoughForUpgrade = True
            
            signlessAvg = avg
            for i in range(0,3):
                #dynamicAvg[i] = dynamicAvg[i] #/ nCycles
                #avg[i] = avg[i] #/ nCycles
                signlessAvg[i] = abs(dynamicAvg[i])
                movingTooMuchForUpgrade = movingTooMuchForUpgrade or signlessAvg[i] > 20000
                movingSlowEnoughForUpgrade = movingSlowEnoughForUpgrade and signlessAvg[i] < 5
            
            
            stormiestDimension = dynamicAvg.index(max(dynamicAvg))
            
#                check for the upgrading gesture (static)
            if lastOne.index(max(lastOne)) == 0 and lastOne[0] > 900 and not movingTooMuchForUpgrade and movingSlowEnoughForUpgrade:
                print("upgrade")
#                #self._startedAction(UPGRADE)
#            #check for dynamic gestures
            
            elif movingTooMuchForUpgrade:
#                if signlessAvg.index(max(signlessAvg)) == 0 and avg[0] > 0 and stormiestDimension == 2:
#                    print("upgrade")
#                el
                if stormiestDimension == 0:
                    print("attack")
                    #self._startedAction(ATTACK)
                elif stormiestDimension == 1:
                    print("scan")
                    #self._startedAction(SCAN)
                elif stormiestDimension == 2:
                    print("build")
                    #self._startedAction(BUILD)
            else:
                print("none")
            
            # ===== print totals ====== 
            print "\njerk:\nX: " + str(dynamicAvg[0]) +"\nY: " +  str(dynamicAvg[1]) + "\nZ: " + str(dynamicAvg[2])
            print "\nlast:\nX: " + str(lastOne[0]) +"\nY: " +  str(lastOne[1]) + "\nZ: " + str(lastOne[2]) + "\n"
            #print "\nacc:\nX: " + str(avg[0]) +"\nY: " +  str(avg[1]) + "\nZ: " + str(avg[2]) + "\n\n"
            
            #=======================================================================
        except KeyboardInterrupt:
            resetLimits()
            break

def defineLimitsNotSoOld():
    
    dynamicAvg = [0, 0, 0]
    avg = [0, 0, 0]
    lastOne = [0, 0, 0]
    nChecks = 0
    nCycles = 200
    
    
    while True:
        try:
            data = reader.get_pos()
            
            newToOldRatio = .2
            
            if nChecks == 0:
                signlessAvg = avg
                for i in range(0,3):
                    #dynamicAvg[i] = dynamicAvg[i] #/ nCycles
                    #avg[i] = avg[i] #/ nCycles
                    signlessAvg[i] = abs(avg[i])
                
                os.system('clear')
                
                stormiestDimension = dynamicAvg.index(max(dynamicAvg))
                
                #check for the upgrading gesture (static)
                if signlessAvg.index(max(signlessAvg)) == 0 and avg[0] > 0:
                    print('UPGRADING')
                #check for dynamic gestures
                elif stormiestDimension == 0:
                    print('ATTACK')
                elif stormiestDimension == 1:
                    print('SCAN')
                elif stormiestDimension == 2:
                    print('BUILD')
                
                # ===== print totals ====== 
                #print "\nX: " + str(dynamicAvg[0]) +"\nY: " +  str(dynamicAvg[1]) + "\nZ: " + str(dynamicAvg[2])
                
                
                print "\nX: " + str(avg[0]) +"\nY: " +  str(avg[1]) + "\nZ: " + str(avg[2])
                
            for i in range(0,3):
                #dynamicAvg[i] = dynamicAvg[i] + (data[i] - lastOne[i])*(data[i] - lastOne[i])
                #avg[i] = avg[i] + data[i]*data[i]*getSignMultiplier(data[i])
                
                dynamicAvg[i] = (1 - newToOldRatio)*dynamicAvg[i] + newToOldRatio*(data[i] - lastOne[i])*(data[i] - lastOne[i])
                avg[i]        = (1 - newToOldRatio)*avg[i] + newToOldRatio*data[i]*data[i]*getSignMultiplier(data[i])
                
                lastOne[i] = data[i]
                
            nChecks = (nChecks + 1) % nCycles
            
        
        except KeyboardInterrupt:
            resetLimits()
            break
        
def getSignMultiplier(num):
    if num < 0:
        return -1
    else:
        return 1
        
def defineLimitsOld():
    """
    Run this function to find the limits of the accelerometer. Constantly reads the values and keeps track of the min
    and max on each access. When keyboard interrupts, the min and max values are used to create a range and three regions
    on each axis. the regions are used later on when creating patterns and sample data
    """
    while True:
        try:
            data = reader.get_pos()
            for i in range(len(maxData)):
                if data[i] > maxData[i]:
                    maxData[i] = data[i]

                if data[i] < minData[i]:
                    if data[i] < -1000: minData[i] = -1000
                    else: minData[i] = data[i]
                
            printResults(minData, maxData)
        
        except KeyboardInterrupt:
            resetLimits()
            break
        



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
    while counter < sampleLength:
        data = reader.get_pos()
        keys = ['x', 'y', 'z']
        data = {'x': data[0], 'y': data[1], 'z': data[2]}
        results = {}
        for k in keys:
            if data[k] < areas[k][0]: results[k] = 0
            elif data[k] < areas[k][1]: results[k] = 1
            else: results[k] = 2

        currentPosition = (results['x'], results['y'], results['z'])
                
        if lastPosition != currentPosition:
            #print "here is current position: " + repr(currentPosition)
            sampleData[lastPosition][currentPosition]+=1
            lastPosition = currentPosition
            counter+=1

    
    #print "done taking samples"
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
    #savePattern(sampleData, "pickles/sampleData.pickle")


def readSerial():
    data = reader.get_pos()


def printResults(*arg):
    os.system('clear')
    for value in arg:
        print repr(value)



def savePattern(pattern, fileName):
    f = open(str(fileName), 'wb')
    pickle.dump(pattern, f)
    f.close()

#    with open(str(fileName), 'wb') as f:
#        pickle.dump(pattern, f)


def loadPattern(fileName):
    f = open(str(fileName), 'rb')
    return pickle.load(f)

#    with open(str(fileName), 'rb') as f:
#        return pickle.load(f)


def initPattern(level):
    p = {}
    for i in range(3):
        for j in range(3):
            for k in range(3):
                if level > 0:
                    p[i,j,k] = initPattern(level-1)
                else:
                    p[i,j,k] = 0
                    
    return p

def resetLimits():
    """
    Quantize the range on each axis of the accelerometer, save range and areas to three seperate pickles
    areas is a dictionary that defines the minimum, 1/3, 2/3 and maximum of the range on each axsis of the accelererometer
    
    """
    areas = {}
    xRange = maxData[0] - minData[0]
    yRange = maxData[1] - minData[1]
    zRange = maxData[2] - minData[2]
    
    areas["x"] = (minData[0] + (xRange/3), minData[0] + (xRange/3)*2)
    areas["y"] = (minData[1] + (yRange/3), minData[1] + (yRange/3)*2)
    areas["z"] = (minData[2] + (zRange/3), minData[2] + (zRange/3)*2)

    savePattern(areas, "pickles/areas.pickle")
    print "everything saved"

def loadLimits():
    areas = loadPattern("pickles/areas.pickle")
    return areas



if __name__ == "__main__":
    sys.exit(main())
