need to figure out how _updatePosition will corrdinate with a position tracker with communication going through the server

Here is where _updatePosition in contrller.py tells game server about it's position:

```python
self.perspective.callRemote('updatePosition', self.position)
```

In chatclient.py when it's setting up it does this:

```python
self.environment = yield perspective.callRemote('getEnvironment')
```

in chatserver.py there's a class called GameAvatar that has a funciton called perspective_getEnviornment that returns self.enviornment

It would be good if chatserver.py was fed player positions from the tracker and then in controller.py when a player is updating their position they just do something like this:

```python
self.perspective.callRemote('getPosition', self.position)
```

This should return an estimated position and a boolean for if that player's tracking target should be on or not. 

Additionally the chatclient should recieve a list of player positions and a list of tracking on / off commands from the tracker every update

The tracker should have some functions:

- make some sets of sparse players based on current estimated positions (to avoid blinking close players)
- request game server to turn off a set of player targets, get the difference in frames between all players on and subset of turned off players
- match each player in subset to closest newly discovered player
- return list of most reciently estimated position for each player and a list of players that should be turned off next


Need to find a way to parse TUIO data in python without using Kivy

Pair up each of the points found by the tracker:

- Pick a random point and take it out of the list
- Pick the point farthest from the previous point and take it out of the list
- Pick the point farthest from all of the previous points in the list and take it out of the list
- Repeat last step until points are all picked