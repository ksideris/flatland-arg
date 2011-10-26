from twisted.internet.task import LoopingCall
from twisted.internet import reactor
import math

import pygame.event
import pygame.mouse
import pygame.time
import sys


from pygame import (K_s as START_GAME,
                    K_r as RESET_GAME,
                    K_e as END_GAME,
                    K_ESCAPE as QUIT,
                    K_DOWN as MOVE_DOWN,
                    K_UP as MOVE_UP,
                    K_LEFT as MOVE_LEFT,
                    K_RIGHT as MOVE_RIGHT,)

class ServerController(object):
    def __init__(self, realm, view):
        print('server cont!')
        self.realm = realm
        self.view = view
        
    def _handleInput(self):
        """
        Handle currently available pygame input events.
        """
        for event in pygame.event.get():
            if (event.type == pygame.QUIT) or ((event.type == pygame.KEYDOWN) and (event.key == QUIT)):
                reactor.stop()
                sys.exit()
                
            if (event.type == pygame.KEYDOWN):
                if (event.key == START_GAME):
                    self.realm.environment.startGame()
                elif (event.key == RESET_GAME):
                    self.realm.environment.setPreGame()
    
    def go(self):
        self.previousTime = pygame.time.get_ticks()
        self._inputCall = LoopingCall(self._handleInput)
        d = self._inputCall.start(0.03)
        return d


    def stop(self):
        self._inputCall.stop()
