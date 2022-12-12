import userbot
import random
import time

# Create my robot - don't change this line
mybot = userbot.mybot

# Create variables - they should start with 'my'

heading = 0         # heading is the direction I want to go
myspeed = 35        # myspeed is the speed I want to go

mybot.scan_direction = 0
mybot.run_timer = 0

def setup():
  global heading, myspeed

  mybot.set_name("Sample")
  mybot.drive(heading, 35)

def ping(enemy):
global heading, myspeed
  print ("Ouch! pinged by", enemy)
  myspeed = 100
  mybot.drive(heading, myspeed)
  mybot.run_timer = time.time() + 3

def move():
  global heading, myspeed
  
  # See if we need to turn
  olddir = heading
  if (mybot.x() > 900 and (heading > 270 or heading < 90)):
    heading = random.randint(90, 270)

  if (mybot.x() < 100 and (heading < 270 and heading > 90)):
    heading = (heading + 180) % 360

  if (mybot.y() > 900 and (heading > 0 and heading < 180)):
    heading = random.randint(180, 360)

  if (mybot.y() < 100 and (heading > 180 and heading < 360)):
    heading = random.randint(0, 90)

  # If we're turning, set new scandir and slow down
  if heading != olddir:
    myspeed = 15
    mybot.drive(heading, myspeed)
  # If we're not turning, go as fast as we can
  else:
    if (time.time() > mybot.run_timer):
      myspeed = 35
    mybot.drive(heading, myspeed)

  # Scan and increment scan direction
  result = mybot.scan(mybot.scan_direction, 10)
  if (result > 0):
    mybot.fire(mybot.scan_direction, result)
  mybot.scan_direction = (mybot.scan_direction + 10) % 360

mybot.process_move = move
mybot.ping = ping
mybot.setup = setup

userbot.main()

