#!/usr/bin/env python
# Copyright (c) 2009-2010 Twisted Matrix Laboratories.
# See LICENSE for details.

import environment
import player
import vector
from game.view import Window
from twisted.spread import pb
from twisted.internet import defer
from twisted.internet import reactor
from twisted.cred import credentials
from twisted.internet.protocol import DatagramProtocol
import pygame
import os
from game.player import _initSounds

USE_FULL_SCREEN = False

if os.environ.get("FARG_INPUT") == "wand":
    from game.actions_wand import PlayerController
    USE_FULL_SCREEN = True
    print("full screen")
else:
    from game.actions_keyboard import PlayerController

class Bootstrap(DatagramProtocol):
    def datagramReceived(self, datagram, address):
        if datagram == "FlatlandARG!!!":
            self.port.stopListening()
            ip, port = address
            Client().connect(ip)


class Client():
    def connect(self, ip):
        factory = pb.PBClientFactory()
        reactor.connectTCP(ip, 8800, factory)
        d = factory.login(credentials.Anonymous())
        d.addCallback(self.connected)

    @defer.inlineCallbacks
    def connected(self, perspective):
        self.perspective = perspective
        self.environment = yield perspective.callRemote('getEnvironment')
        self.environment.team = yield perspective.callRemote('getTeam')
        self.view = Window(self.environment)
        self.view.start("Client - %d" % (self.environment.team, ))
        self.controller = PlayerController(self.perspective, self.view)
        self.controller.go()

    def shutdown(self, result):
        reactor.stop()

    pygame.mixer.pre_init(frequency=16000,size=8,channels=1,buffer=1024)#, size=-8, channels=1)
pygame.init()
#pygame.display.set_mode((480, 800), pygame.DOUBLEBUF)#for computers
_initSounds()

displayFlags = pygame.DOUBLEBUF
if USE_FULL_SCREEN:
    displayFlags = displayFlags | pygame.FULLSCREEN
    pygame.mouse.set_visible(False)
pygame.display.set_mode((800, 480), displayFlags)#for phone
# TODO: restore background music
#pygame.mixer.music.load("data/sfx/background.mp3")
#pygame.mixer.music.play(-1)

bootstrap = Bootstrap()
bootstrap.port = reactor.listenUDP(8000, bootstrap)
reactor.run()
