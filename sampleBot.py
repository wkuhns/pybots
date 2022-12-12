# Code for sample robot

# 'import' lines add Python capabilities that you might need. 
# You can add others, but leave these.
import warbot_lib.userRobot as userRobot
import random
import time

# This creates your robot. Do not change this line
mybot = userRobot.mybot

# ******************* Make changes below this line. ******************

# Create variables. Names must be in the form mybot.myxxx

mybot.heading = 45          # heading is the direction I want to go
mybot.myspeed = 35          # myspeed is the speed I want to go
mybot.scan_direction = 0    # The direction to scan for enemies
mybot.run_timer = 0         # Timer for running fast after being scanned

# The setup function is run once at startup. Edit this as desired
def setup():
    mybot.set_name("Sample")
    mybot.drive(35, mybot.heading)
    mybot.set_armor(70)     # Bulk up our armor a bit

# This gets run whenever your robot is scanned by an enemy.
def ping(enemy):
    # If we got scanned, run for three seconds
    mybot.post(f"Ouch: scanned by {enemy}")
    mybot.myspeed = 100
    mybot.drive(mybot.myspeed, mybot.heading)
    mybot.run_timer = time.time() + 3

# This gets run about 20 times per second while your robot is alive.
# This is where you put almost all of your strategy.
def move():
    # See if we need to turn - remember our original planned direction
    old_dir = mybot.heading

    # Are we close to the right wall and heading more or less rightward?
    if mybot.x() > 900 and (mybot.heading > 270 or mybot.heading < 90):
        # Change to a random direction between 90 and 270 (left-ish)
        mybot.heading = random.randint(90, 270)

    # Same question, but avoid hitting left wall
    if mybot.x() < 100 and (270 > mybot.heading > 90):
        mybot.heading = (mybot.heading + 180) % 360

    # Avoid bottom wall
    if mybot.y() > 900 and (0 < mybot.heading < 180):
        mybot.heading = random.randint(180, 360)

    # Avoid top wall
    if mybot.y() < 100 and (180 < mybot.heading < 360):
        mybot.heading = random.randint(0, 90)

    # If we have a new direction, slow down for turn
    if mybot.heading != old_dir:
        mybot.myspeed = 15

    # If we're not turning or running, just mosey along
    else:
        if time.time() > mybot.run_timer:
            mybot.myspeed = 35
    
    mybot.drive(mybot.myspeed, mybot.heading)

    # Scan
    result = mybot.scan(mybot.scan_direction, 10)

    # If there's someone there, shoot at them
    if result > 0:
        mybot.fire(mybot.scan_direction, result)
        mybot.post("Bang! %d %d" % (mybot.scan_direction, result))

    # Increment scan direction
    mybot.scan_direction = (mybot.scan_direction + 10) % 360

# ******************* Do not change below this line ******************
mybot.move = move
mybot.ping = ping
mybot.setup = setup
mybot.main()
