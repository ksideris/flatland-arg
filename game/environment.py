import pygame
from vector import Vector2D
from game.player import Player, ResourcePool, Building
from twisted.spread import pb
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import time

GAME_DURATION = 15#15 seconds #15 * 60 # 15 minutes
PRESUMED_LATENCY = 1

class Environment(pb.Cacheable, pb.RemoteCache):
    def __init__(self):
        self.observers = []
        self.players = {}
        self.rp = ResourcePool(100)
        self.rp.position = Vector2D(0, 0)
        self.width = 80.0#48.0
        self.height = 48.0#80.0
        self.buildings = {}
        self.team = None
        self.endTime = None
        self.gameOver = False
        self.attackOk = True
        self.lightOn = True

    def resetGame(self):
        #pass
        self.buildings = {}
        for p in self.players:
            self.players[p].reset()

    def _turnOnLight(self):
        self.lightOn = True

    def observe_blinkLight(self, player = None):
        #if player.self:
        print "blinky"
        self.lightOn = False
        reactor.callLater(.4, self._turnOnLight)

    def startGame(self):
        # I'm not sure that this is best way to do this,
        # but by using absolute times, coordination is
        # simpler
        self.observe_startGame(latencyEstimate=0)
        reactor.callLater(GAME_DURATION, self.endGame)
        for o in self.observers:
            o.callRemote('startGame')

    def observe_startGame(self, latencyEstimate=PRESUMED_LATENCY):
        print("start")
        self.observe_updateTimeRemaining(GAME_DURATION, 0)
        self.resetGame()
        self.gameOver = False

    def setPreGame(self):
        for o in self.observers: o.callRemote('blinkLight')
        self.observe_setPreGame()
        for o in self.observers: o.callRemote('setPreGame')

    def observe_setPreGame(self):
        self.endTime = None
        self.gameOver = False


    def updateTimeRemaining(self, timeRemaining):
        self.observe_updateTimeRemaining(timeRemaining, latencyEstimate=0)
        for o in self.observers: o.callRemote('updateTimeRemaining')

    def observe_updateTimeRemaining(self, timeRemaining, latencyEstimate=PRESUMED_LATENCY):
        self.endTime = int(time.time()) + timeRemaining - latencyEstimate


    def endGame(self):
        self.observe_endGame()
        for o in self.observers: o.callRemote('endGame')

    def observe_endGame(self):
        self.gameOver = True
        self.endTime = int(time.time())

    def createPlayer(self, team):
        player = Player()
        player.team = team

        # I have no idea if this is being set somewhere else
        #if self.team == None:
        #    self.team = team

        playerId = id(player)
        self.players[playerId] = player
        for o in self.observers: o.callRemote('createPlayer', playerId, player)
        #player.sounds = self.sounds
        return player

    def observe_createPlayer(self, playerId, player):
        self.players[playerId] = player

    def removePlayer(self, player):
        pid = id(player)
        del self.players[pid]
        for o in self.observers: o.callRemote('removePlayer', pid)
    def observe_removePlayer(self, pid):
        del self.players[pid]

    def createBuilding(self, team, position):
        if (self.rp.position - position) < 6:
            return None
        for b in self.buildings.itervalues():
            if (team == b.team) and (b.position - position) < 6:
                return None
        building = Building()
        building.team = team
        building.position = position
        bid = id(building)
        self.buildings[bid] = building
        building.onDestroyed.addCallback(self.destroyBuilding)
        for o in self.observers: o.callRemote('createBuilding', bid, building)
        return building

    def observe_createBuilding(self, bid, building):
        self.buildings[bid] = building

    def destroyBuilding(self, building):
        bid = id(building)
        del self.buildings[bid]
        for o in self.observers: o.callRemote('destroyBuilding', bid)
    def observe_destroyBuilding(self, bid):
        del self.buildings[bid]

    def attack(self, player):
        #if self.attackOk:
        self.attackOk = False
        reactor.callLater(1.5, self.makeAttackOk)
        distance = 3
        player.attack()
        for p in self.players.itervalues():
            if (p.team != player.team) and (p.position - player.position) < distance:
                p.hit()
        for b in self.buildings.values():
            if (b.position - player.position) < distance:
                b.hit()

    def makeAttackOk(self):
        self.attackOk = True

    def startAttacking(self, player):
#        if player.action == None:
        player.setAction("Attacking", LoopingCall(self.attack, player))
        player.action.start(1.5, now=self.attackOk)
        self.attackOk = False

        #self.attack(player)


    def startBuilding(self, player):
        hadNoBuilding = not player.building
        if hadNoBuilding:
            newBuildingPosition = player.position

            newBuildingPosition.x = newBuildingPosition.x - 2 #TODO this will likely have to change to x for the phone

            building = self.createBuilding(player.team, newBuildingPosition)
            if building:
                player.updatePosition(player.position, building)
            else:
                return
        if player.building == self.rp:
            action = "Mining"
            hadNoBuilding = False
        else:
            action = "Building"
        player.setAction(action, LoopingCall(player.building.build, player))
        player.action.start(2, now=hadNoBuilding)

    def finishAction(self, player):
        if player.action:
            player.action.stop()
            player.setAction(None, None)

    def startUpgrading(self, player):
        player.startAcceptUpgrade()
        for b in self.buildings.itervalues():
            if b.isPolyFactory() and (b.team == player.team) and (b.position - player.position) < 3 and not b.upgrading:
                b.upgrading = player
                player.upgradingAt = b

    def finishUpgrading(self, player):
        if player.upgradingAt:
            player.upgradingAt.upgrading = None
            player.upgradingAt = None

    def updatePlayerPosition(self, player, position):
        building = None
        for b in self.buildings.itervalues():
            if (player.team == b.team) and (b.position - position) < 3:
                building = b
                break
        if not building:
            if (self.rp.position - position) < 3:
                building = self.rp
        player.updatePosition(position, building)

        for b in self.buildings.itervalues():
            if b.isTrap() and (b.team != player.team) and ((b.position - player.position) < 1):
                player.trapped()
                b.explode()
                break

    def isVisible(self, entity):
        # Spectators see all
        if not self.team:
            return True
        # See objects on your team
        if self.team == entity.team:
            return True
        # Object in range of my sentries
        for b in self.buildings.itervalues():
            if b.isSentry() and (b.team == self.team) and (entity.position - b.position) < 13.75:
                return True
        # object in range of a scanning player
        for p in self.players.itervalues():
            if (self.team == p.team):
                if (entity.position - p.position) < p.getScanRadius() * 12.35:
                    return True
        return False

    def paint(self, view):
        for b in self.buildings.itervalues():
            # TODO save the view to get images
            b.images = view.images.images
            if self.isVisible(b) or b.explosion:
                b.paint(view, view.screenCoord(b.position), b.team == self.team)
        self.rp.paint(view, view.screenCoord(self.rp.position))
        for p in self.players.itervalues():
            if p.self:
                view.setCenter(p.position)
            if p.self and p.building:
                p.building.drawToolTip(view, "Build", p.team)
            p.paint(view, view.screenCoord(p.position), self.team == p.team, self.isVisible(p))

        # Draw the score:
        #TODO color appropriately
        font = pygame.font.Font("data/Deutsch.ttf", 35)
        #font = pygame.font.Font(None, 45)
        text = font.render(str(self.calculateScore(self.team)), True, (0,255,255))
        text = pygame.transform.rotate(text, 270)
        textrect = text.get_rect(right =735, bottom = 410)
        view.screen.blit(text,textrect)

        text = font.render(str(self.calculateScore(self.getOpponentTeam())), True, (255, 0, 255))
        text = pygame.transform.rotate(text, 270)
        textrect = text.get_rect(right = 775, bottom = 410)
        view.screen.blit(text,textrect)


        # ======================================================================
        #Draw the time remaining
        minRemaining = 15
        secRemaining = 0
        if self.endTime:
            secRemaining = max(self.endTime - int(time.time()), 0)
            minRemaining = secRemaining / 60
            secRemaining = secRemaining % 60

        secStr = str(secRemaining)
        if secRemaining <= 9: secStr = "0" + secStr

        minStr = str(minRemaining)
        if minRemaining <= 9: minStr = "0" + minStr

        font = pygame.font.Font("data/Deutsch.ttf", 35)
        text = font.render(minStr + ":" + secStr, True, (255, 255, 255))
        text = pygame.transform.rotate(text, 270)
        textrect = text.get_rect(left = 15, bottom = 410)
        view.screen.blit(text,textrect)

        # ======================================================================
        # draw end game message, as appropriate
        if self.gameOver:
            endGameMessage = ""
            if self.team:
                scoreDifference = self.calculateScore(self.team) > self.calculateScore(self.getOpponentTeam())
                if scoreDifference > 0:
                    endGameMessage = "YOU WIN!"
                elif scoreDifference < 0:
                    endGameMessage = "YOU LOSE!"
                else:
                  endGameMessage = "DRAW!"

            else:
                scoreDifference = self.calculateScore(1) - self.calculateScore(2)
                if scoreDifference > 0:
                    endGameMessage = "RED WINS!"
                elif scoreDifference < 0:
                    endGameMessage = "BLUE WINS!"
                else:
                    endGameMessage = "DRAW!"


            font = pygame.font.Font("data/Deutsch.ttf", 70)
            #font = pygame.font.Font(None, 45)
            text = font.render(endGameMessage, True, (255,255,255))
            text = pygame.transform.rotate(text, 270)
            textrect = text.get_rect(centery =240, centerx = 350)
            view.screen.blit(text,textrect)

        # ======================================================================
        # draw draw white square for photo sensor

        sqrSz = 75

        if not self.team == None:
            sensRect = pygame.Rect(0, 0, sqrSz + 5, sqrSz + 10)
            sensRect.right = 800
            sensRect.centery = 240
            pygame.draw.rect(view.screen, (0,0,0), sensRect)

            if self.lightOn:
                sensRect = pygame.Rect(0,0,sqrSz,sqrSz)
                sensRect.right = 800
                sensRect.centery = 240
                pygame.draw.rect(view.screen, (255,255,255), sensRect)


    # pb.Cacheable stuff
    def getStateToCacheAndObserveFor(self, perspective, observer):
        self.observers.append(observer)
        state = pb.Cacheable.getStateToCopyFor(self, perspective).copy()
        del state['observers']
        return state

    def stoppedObserving(self, perspective, observer):
        self.observers.remove(observer)

    def switchTeams(self, player):
        self.team = self.getOpponentTeam()
        player.switchTeams()

    def getOpponentTeam(self):
        if self.team == 1:
            return 2
        else:
            return 1

    def calculateScore(self, team):
        #print "score =================================="
        if team == None:
            team = self.team
#        print "=== Our Team: " + str(team)
        score = 0;
        for playerId in self.players:
            #score = score + 100
            player = self.players[playerId]
            #print "player team: " + str(player.team)
            if player.team == team:
                score = score + player.sides
                score = score + player.resources

        for buildingId in self.buildings:
            #score = score + 10000
            building = self.buildings[buildingId]
            #print "bildg team: " + str(building.team)
            if building.team == team:
                score = score + building.sides
                score = score + building.resources

        return score * 1000;

pb.setUnjellyableForClass(Environment, Environment)
