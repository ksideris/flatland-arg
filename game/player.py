import math
import pygame.mixer
from twisted.internet import defer
from twisted.spread import pb
from vector import Vector2D
from twisted.internet import reactor

#This comment is still not important.

class PlayerScan:
    def __init__(self):
        self.reset()

    def reset(self):
        self.startTime = 0
        self._radius = 0
        self.resetTimer = None
        self._isScanning = False

    def start(self):
        if self.resetTimer:
            self.resetTimer.cancel()
            self.reset()
        self.startTime = pygame.time.get_ticks()
        self._isScanning = True

    def stop(self):
        self._isScanning = False
        self._radius = self.radius()
        self.startTime = pygame.time.get_ticks()
        self.resetTimer = reactor.callLater(5, self.reset)

    def radius(self):
        if self.startTime == 0:
            return 0
        dt = (pygame.time.get_ticks() - self.startTime)
        if self._radius:
            if dt >= 5000.0:
                return 0;
            else:
                return self._radius * (1 - (dt / 5000.0))
        #return (math.log1p(min(1, (dt / 10000.0) / (math.e - 1))) * .9) + 0.1
        return min(1, (dt / 1000.0)  * .9) + 0.1


    def __nonzero__(self):
        if self.startTime == 0:
            return False
        return True

    def isScanning(self):
        return self._isScanning

class Player(pb.Cacheable, pb.RemoteCache):
    def __init__(self):
        #pb.Cacheable.__init__(self)
        #pb.RemoteCache.__init__(self)
        self.position = Vector2D(0, 0)
        self.sides = 3
        self.resources = 0
        self.observers = []
        self.scanning = PlayerScan()
        self.size = 1
        self.action = None
        self.upgradingAt = None
        self.self = False
        self.events = set()
        self.topEvents = set()
        self.armor = dict()
        self.building = None
        self._buildingReset = None
        self.tooltip = None
        self.lastAction = None
        self.attackFunc = None
        
        #sound related state
        self.playingBuildingCompleteSound = False
        self.actionName = None
        self.scanFadeOutOk = False
        self.stopBuildingChannelOk = True
        self.hadResources = False
        #self.pointsFullPlayOk = True
        #self.sounds = dict()
        #self.sounds['Building 3-Sided'] = pygame.mixer.Sound("data/sfx/alex_sfx/Building 3-sided.wav")

        #sound related state
        self.playingBuildingCompleteSound = False
        self.actionName = None
        self.scanFadeOutOk = False
        self.stopBuildingChannelOk = True
        self.attacking = False

    def _startScanning(self):
        self.scanning.start()

    def startScanning(self):
        self._startScanning()
        for o in self.observers: o.callRemote('startScanning')

    observe_startScanning = _startScanning

    def _finishScanning(self):
        self.scanning.stop()
    def finishScanning(self):
        self._finishScanning()
        for o in self.observers: o.callRemote('finishScanning')
    observe_finishScanning = _finishScanning

    def getScanRadius(self):
        return self.scanning.radius()

    def observe_trapped(self, playSound = True):
        if self.resources:
            self.setResources(0)
        else:
            self.sides = 0

        if (playSound):
            pygame.mixer.Channel(6).play(pygame.mixer.Sound("data/sfx/alex_sfx/Trigger Trap.wav"))
            pygame.mixer.Channel(7).play(pygame.mixer.Sound("data/sfx/alex_sfx/Attack Hit.wav"))

    def trapped(self):
        self.observe_trapped(playSound = False)
        for o in self.observers: o.callRemote('trapped')

    def setAction(self, remote, local):
        self.observe_setAction(remote)
        self.action = local
        if (remote != "Mining" and remote != "Building"):
            pygame.mixer.Channel(7).stop()

        self.actionName = remote

        for o in self.observers: o.callRemote('setAction', remote)
        
    def observe_setAction(self, action):
        # TODO Tooltips no longer used?
        self.tooltip = None
        self.actionName = action
        if action == None:
            self.attacking = False


    def _gainResource(self, playSound = True):
        playResourceFullOk = False
        actuallyGainResource = False

        if self.sides < 3:
            self.sides += 1
            #TODO should probably play some kind of sound here
        elif self.resources < self.sides:
            
            #self.resources += 1
            self.setResources(self.resources + 1)
            
            actuallyGainResource = True
            
            #animation = self.images["ArmorBreak", self.sides, self.resources].copy()
            #animation.startReversed(24)
            
            animation = self.images["Generic_2"].copy()
            #animation.setRotation("45")
            animation.start(12).addCallback(lambda ign: self.events.remove(animation))
            self.events.add(animation)
            
            #self.armor[self.resources] = self.images["Armor", self.sides, self.resources]
            
            playResourceFullOk = True
        
        if (playSound):
            if actuallyGainResource:
                pygame.mixer.Channel(6).play(pygame.mixer.Sound("data/sfx/alex_sfx/gain resource.wav"))
    
                #It's possible if the sound changes, that restarting the mining sound will sound good
                #pygame.mixer.Channel(7).play(pygame.mixer.Sound("data/sfx/alex_sfx/In Resource Pool(loop).wav"))
                
            if self.resources == self.sides:
                pygame.mixer.Channel(7).stop()
                if (playResourceFullOk):
                    self.stopBuildingChannelOk = False
                    pygame.mixer.Channel(5).play(pygame.mixer.Sound("data/sfx/alex_sfx/Points Full.wav"))

    def gainResource(self):
        self._gainResource(playSound = False)

        for o in self.observers: o.callRemote('gainResource')
    observe_gainResource = _gainResource

    def switchTeams(self):
        #print "team: " + str(self.team)
        if self.team == 1:
            self.team = 2
        else:
            self.team = 1
        
    def setResources(self, newAmount):        
        self.resources = newAmount
        self.armor.clear()
        
        for i in range(1, newAmount + 1):
            self.armor[i] = self.images["Armor", self.sides, i]
        
    def _loseResource(self, playSound = True):
        if self.resources:
            if self.building:
                infiniteResources = False
                if not infiniteResources:
                    self.setResources(self.resources - 1)
            
            if playSound:
                #TODO building complete sounds should be played here
                if not self.building:
                    pygame.mixer.Channel(7).stop()
                else:
                    loseResourceSound = pygame.mixer.Sound("data/sfx/alex_sfx/pay resource.wav")
                    loseResourceSound.set_volume(.6)
                    pygame.mixer.Channel(6).play(loseResourceSound)
                    #print "the building : " + str(self.building.sides) + "-sided, resources =" + str(self.building.resources) + "\n"
                    if self.building.resources == 0:#self.building.nResourcesToUpgrade() == 1:#self.building.sides == self.building.resources and self.building.sides >= 3:
                        pygame.mixer.Channel(7).stop()
                        self.playingBuildingCompleteSound = True
                        pygame.mixer.Channel(5).play(pygame.mixer.Sound("data/sfx/alex_sfx/Finish " + str(self.building.sides) + "-sided.wav"), 0)
                        #TODO should reset the building sound too
                    
                    elif self.resources == 0:
                        pygame.mixer.Channel(5).play(pygame.mixer.Sound("data/sfx/alex_sfx/resources depleted.wav"),0)
                

    def loseResource(self):
        self._loseResource(playSound = False)
        for o in self.observers: o.callRemote('loseResource')
    observe_loseResource = _loseResource

    def _attack(self):
        self.attacking = True
        animation = self.images["Attack"].copy()
        animation.start(12).addCallback(lambda ign: self.events.remove(animation))
        self.events.add(animation)
    
    def attack(self):
        self._attack()
        for o in self.observers: o.callRemote('attack')
    
    observe_attack = _attack

    def _updatePosition(self, position, building, playSound=True):
        self.position = position
        # TODO only need this for self.self
        def buildingReset():
            self.building = None
            self._buildingReset = None
#            if hasattr(self.building, 'sides'):# and self.building.sides == 0:# and self.building.resources == 0:
#                print "aborted"
#                self.building.onDestroyed.callback(self.building)
            
        if playSound:
            if self.scanning.isScanning():
                self.scanFadeOutOk = True 
                if not pygame.mixer.Channel(5).get_busy():
                    pygame.mixer.Channel(5).play(pygame.mixer.Sound("data/sfx/alex_sfx/Sweeping.wav"),-1)
                #else:
                #    pygame.mixer.Channel(5).queue(pygame.mixer.Sound("data/sfx/alex_sfx/Sweeping.wav"))
            else:
                if self.scanFadeOutOk:
                    #pygame.mixer.Channel(5).play(pygame.mixer.Sound("data/sfx/alex_sfx/Sweeping.wav"), -1)
                    pygame.mixer.Channel(5).fadeout(4000)
                    self.scanFadeOutOk = False
        
        if building: 
            self.building = building
            if self._buildingReset:
                self._buildingReset.cancel()
            self._buildingReset = reactor.callLater(1, buildingReset)
            
            if (playSound):
                #print('sides : ' + str(hasattr(self.building, 'sides')))
                #print('action: ' + str(self.actionName == 'Building'))
                if (hasattr(self.building, 'sides') and self.actionName == 'Building'):# and self.resources:
                
                    if self.resources == 0:
                        #if not self.playingBuildingCompleteSound or not pygame.mixer.Channel(7).get_busy():
                        #if (not self.playingBuildingCompleteSound or not pygame.mixer.Channel(5).get_busy()):
                        pygame.mixer.Channel(7).stop()
                        #    self.playingBuildingCompleteSound = False
                        
                    else:
                        buildingSideCount = self.building.sides
                        if buildingSideCount < 3:
                            buildingSideCount = 3
                        else:
                            buildingSideCount = min(buildingSideCount + 1, 5)
                        
                        if (not self.playingBuildingCompleteSound or not pygame.mixer.Channel(5).get_busy()):
                            self.playingBuildingCompleteSound = False
                            if not pygame.mixer.Channel(7).get_busy():
                                pygame.mixer.Channel(7).play(pygame.mixer.Sound("data/sfx/alex_sfx/Building "+str(buildingSideCount)+"-sided.wav"))
                            else:
                                pygame.mixer.Channel(7).queue(pygame.mixer.Sound("data/sfx/alex_sfx/Building "+str(buildingSideCount)+"-sided.wav"))                    
                    
                elif self.actionName == 'Mining':
                    if self.resources < self.sides:
                        if not pygame.mixer.Channel(7).get_busy():
                            pygame.mixer.Channel(7).play(pygame.mixer.Sound("data/sfx/alex_sfx/In Resource Pool(loop).wav"))
                        else:
                            pygame.mixer.Channel(7).queue(pygame.mixer.Sound("data/sfx/alex_sfx/In Resource Pool(loop).wav"))
                else:
                        pygame.mixer.Channel(7).stop()

    def updatePosition(self, position, building):
        self._updatePosition(position, building, playSound=False)
        for o in self.observers: o.callRemote('updatePosition', position, building)
    
    observe_updatePosition = _updatePosition

    def _hit(self):
        if self.resources:
            self.setResources(self.resources - 1)
        else:
            animation = self.images["LevelUp"].copy()
            animation.startReversed(72).addCallback(lambda ign: self.topEvents.remove(animation))
            self.topEvents.add(animation)
            self.sides -= 1
            
    def hit(self):
        self._hit()
        for o in self.observers: o.callRemote('hit')
    observe_hit = _hit

    def _levelUp(self):
        self.armor.clear()
        self.setResources(0)
        self.sides += 1

        #animation = self.images["building upgraded"].copy()
        #animation.start(12).addCallback(lambda ign: self.topEvents.remove(animation))
        #self.topEvents.add(animation)
    def levelUp(self):
        self._levelUp()
        for o in self.observers: o.callRemote('levelUp')
    observe_levelUp = _levelUp

    def paint(self, view, position, isTeammate, isVisible):
        # TODO player image deviates from center of screen occasionally
        # likely caused by view.center being updated but not player.position
        # which must wait for the server to update its
        if self.self:
            (cx, cy) = view.screen.get_rect().center
            position = Vector2D(cx,cy) #Vector2D(240, 400)
        # TODO HACK save the view to get images
        self.images = view.images.images

        if isVisible and self.scanning:
            view.images.images["PlayerScan"].drawScaled(view.screen, position, self.getScanRadius())

        for image in self.events:
            image.draw(view.screen, position)

        if isVisible:
            image = view.images.images["Player", (self.self, isTeammate), self.sides]
            image.draw(view.screen, position)
            for image in self.topEvents:
                image.draw(view.screen, position)
            if self.tooltip:
                self.tooltip.draw(view.screen, position + Vector2D(0, -100))
        else:
            image = view.images.images["Enemy"]
            image.draw(view.screen, position)
            return

        for a in self.armor:
            # XXX Must start all clients at the same time or armor is Unpersistable
            self.armor[a].draw(view.screen, position)

    def getStateToCacheAndObserveFor(self, perspective, observer):
        self.observers.append(observer)
        state = pb.Cacheable.getStateToCopyFor(self, perspective).copy()
        del state['observers']
        if self == perspective.player:
            state['self'] = True
        return state

    def setCopyableState(self, state):
        pb.RemoteCache.setCopyableState(self, state)
        self.scanning = PlayerScan()

    def stoppedObserving(self, perspective, observer):
        self.observers.remove(observer)

pb.setUnjellyableForClass(Player, Player)

class Building(pb.Cacheable, pb.RemoteCache):
    def __init__(self):
        self.sides = 0
        self.resources = 0
        self.observers = []
        self.size = 1
        self.onDestroyed = defer.Deferred()
        self.upgrading = None
        self.explosion = None
        self.upgradeAnim = None

    def build(self, player):
        if not player.resources:
            return
        if self.sides == 5 and self.resources == 5:
            if self.upgrading and self.upgrading.sides > 2:
                player.loseResource()
                if self.upgrading.sides == self.upgrading.resources:
                    self.upgrading.levelUp()
                else:
                    self.upgrading.gainResource()
        else:
            self.gainResource()
            player.loseResource() #have player lose resource after, so they can see if a new building got made.
        for o in player.observers: o.callRemote('setAction', "Building")

    def _gainResource(self, playSound=True):
        # Not a full polyfactory
        # if rubble
        buildingLeveledUp = False
        if not self.sides:
            if self.resources == 2:
                self.sides = 3
                self.resources = 0
                buildingLeveledUp = True
            else:
                self.resources += 1
        else:
            # if armor is full
            if self.sides == self.resources:
                self.sides += 1
                self.resources = 0
                buildingLeveledUp = True
            else:
                self.resources += 1
        
        if buildingLeveledUp:
            self.upgradeAnim = self.images["building upgraded"].copy()
            self.upgradeAnim.start(12).addCallback(lambda ign: self.clearUpgradeAnim())
        
    def clearUpgradeAnim(self):
        self.upgradeAnim = None    
        
    def gainResource(self):
        self._gainResource(playSound=False)
        for o in self.observers: o.callRemote('gainResource')
    
    observe_gainResource = _gainResource

    def observe_setResources(self, r):
        self.resources = r

    def drawToolTip(self, view, tip, team = None):
        # TODO No more tool tips?
        pass

    def paint(self, view, position, isTeammate):
        if self.explosion:
           self.explosion.draw(view.screen, position)
           return

        if self.sides == 0 and self.resources == 0:
            return

        if self.sides >= 3:
            view.images.images["Building Zone", self.sides, isTeammate].draw(view.screen, position)

        if self.upgradeAnim:
            self.upgradeAnim.draw(view.screen, position)

        if self.sides:
            view.images.images["Building", self.sides, isTeammate].draw(view.screen, position)
            view.images.images["BuildingHealth", isTeammate, self.sides, self.resources].draw(view.screen, position)
        else:
            image = view.images.images["Building", self.resources, isTeammate].draw(view.screen, position)

    def getStateToCacheAndObserveFor(self, perspective, observer):
        self.observers.append(observer)
        state = pb.Cacheable.getStateToCopyFor(self, perspective).copy()
        del state['observers']
        return state

    def stoppedObserving(self, perspective, observer):
        self.observers.remove(observer)

    def hit(self):
        if not (self.sides and self.resources):
            self.onDestroyed.callback(self)
        elif self.resources:
            self.resources -= 1
            for o in self.observers: o.callRemote('setResources', self.resources)

    def _explode(self):
        #TODO a delay to the explosion would be nice.
        self.explosion = self.images["TrapExplosion"].copy()
        return self.explosion.start(4)
    
    def explode(self):
        self._explode().addCallback(lambda ign: self.onDestroyed.callback(self))
        for o in self.observers: o.callRemote('explode')
    observe_explode = _explode

    def isTrap(self):
        if self.sides == 3 and not self.explosion:
            return True
        return False

    def isSentry(self):
        return self.sides == 4

    def isPolyFactory(self):
        return self.sides == 5

pb.setUnjellyableForClass(Building, Building)

class ResourcePool(pb.Copyable, pb.RemoteCopy):
    def __init__(self, size):
        self.size = 3

    def build(self, player):
        player.gainResource()
        for o in player.observers: o.callRemote('setAction', "Mining")

    def addBuilder(self, player):
        pass

    def removeBuilder(self, player):
        pass

    def drawToolTip(self, view, tip, team):
        # TODO No more tool tips?
        pass

    def paint(self, view, position):
        view.images.images["resource_pool_zone"].draw(view.screen, position)
        view.images.images["resource_pool"].draw(view.screen, position)

pb.setUnjellyableForClass(ResourcePool, ResourcePool)
