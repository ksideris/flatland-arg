'''
Created on Oct 5, 2011

@author: xander
'''

class GestureDecider(object):
    '''
    classdocs
    '''


    def __init__(self):
        '''
        Constructor
        ''' 

        
    def pollAccelerometer(self, accelReader):
        dynamicAvg = None#[0, 0, 0]
        avg = None#[0, 0, 0]
        lastOne = None#[0, 0, 0]
        nCycles = 200
        newToOldRatio = .2
        data = accelReader.get_pos()
        
        # Read the accelerometer for a fixed amount of time, to get a good average
        for nTimes in range(0, nCycles):
            for i in range(0,3):
                #dynamicAvg[i] = dynamicAvg[i] + (data[i] - lastOne[i])*(data[i] - lastOne[i])
                #avg[i] = avg[i] + data[i]*data[i]*getSignMultiplier(data[i])
                
                # calculate an average CHANGE in acceleration for each axis
                accelChange = data[i] - lastOne[i]
                dynamicAvg[i] = (
                    (1 - newToOldRatio) * dynamicAvg[i] 
                    + 
                    newToOldRatio * accelChange * accelChange
                                    )
                
                # calculate an average acceleration for each axis
                avg[i] = (
                               (1 - newToOldRatio)*avg[i] 
                               + 
                               newToOldRatio * data[i] * data[i] * getSignMultiplier(data[i])
                               )
                
                lastOne[i] = data[i]
                time.sleep(1.0/100)
                #should wait some period of time before trying to read it again
        
        signlessAvg = avg
        for i in range(0,3):
            #dynamicAvg[i] = dynamicAvg[i] #/ nCycles
            #avg[i] = avg[i] #/ nCycles
            signlessAvg[i] = abs(avg[i])
        
        #os.system('clear')
        
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
        #print "\nX: " + str(avg[0]) +"\nY: " +  str(avg[1]) + "\nZ: " + str(avg[2])
