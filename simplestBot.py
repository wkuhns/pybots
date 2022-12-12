# Code for simplest possible robot

# 'import' lines add Python capabilities that you might need. 
# You can add others, but leave this one.
import warbot_lib.userRobot as userRobot

# This creates your robot. Do not change this line
mybot = userRobot.mybot

# ******************* Make changes below this line. ******************

# Create variables. Names must be in the form mybot.myxxx
# No variables in this simplest example

# The setup function is run once at startup.

def setup():
    mybot.set_name("Simplest")  # Set our name.
    mybot.set_autopilot()       # Set 'autopilot' option
    mybot.set_autoscan()        # Set 'autoscan' option

# This gets run whenever your robot is scanned by an enemy.

def ping(enemy):
    pass        # 'pass' means don't do anything

# This gets run about 20 times per second while your robot is alive.
# This is where you put almost all of your strategy.

def move():
    pass        # pass since we have autopilot and autoscan

# ******************* Do not change below this line ******************


mybot.move = move
mybot.ping = ping
mybot.setup = setup
mybot.main()


