import random
import math
import time
from tkinter import *

QUANTA = 30
colors = ["dodger blue", "lightgreen", "red", "yellow"]

# Code for robot instance on server
class ServerRobot():
  lastreport = 0
  braking = False
  coasting = False

  # for automatic functions
  autopilot = False
  autoscan = False
  heading = 0
  scandirection = 0
  lastScanTime = time.time()

  # for transient graphics
  scanLine1 = 0
  scanLine2 = 0
  scantime = 0
  bombIcon = 0
  bombTime = 0

  # for loading shells
  loadingFinishTime = 0
  loading = False
  shells = 4

  # For performance stats
  shots = 0
  damage = 0
  misfires = 0

  sock = 0
  armor = 50
  scan_accuracy = 50
  maxSpeedMPS = 32

  def __init__(self, index, arena, robots, q):
    self.my_init(index, arena, robots, q)

  def my_init(self, index, arena, robots, q):
    self.index = index
    self.arena = arena
    self.robots = robots
    self.used = False
    self.name = "Robot"
    self.deltax = 0
    self.deltay = 0
    self.status = "D"
    self.color = 0
    self.pingnotify = 0   # ID of bot who scanned me
    self.q = q            # Quad that we're in

    self.dir = 45
    self.dirgoal = 45
    self.dirdelta = 0    # +/- increment to turn
    self.currentSpeedMPS = 1       # current speed in meters/sec
    self.speedGoalMPS = 0   # requested speed in meters/sec
    self.shells = 4
    self.mHeat = 0       # motor heat
    self.bHeat = 0       # barrel heat
    self.tx = 0          # target x,y
    self.ty = 0
    self.sdir = 45
    self.sres = 10
    self.lastscanned = 0  # ID of last 'bot who I scanned
    self.health = 100

    # Shell variables
    self.ticks = 0
    self.my_bomb_img = PhotoImage(file = "archives/pygame/bluebot.png")

  def set_armor(self, lvl):
    self.armor = lvl
    self.maxSpeedMPS = 41.2 - (lvl+50)**3 * 0.00000924
    #print ("Max", self.armor, self.maxSpeedMPS)

  def do_autopilot(self):

    # Are we close to the east wall and heading more or less east?
    if (self.x > 900 and (self.heading > 270 or self.heading < 90)):
      # Change to a random direction between 90 and 270 (west-ish)
      self.heading = random.randint(90, 270)

    # Same question, but avoid hitting west wall
    if (self.x < 100 and (self.heading < 270 and self.heading > 90)):
      self.heading = (self.heading + 180) % 360

    # Avoid south wall
    if (self.y > 900 and (self.heading > 0 and self.heading < 180)):
      self.heading = random.randint(180, 360)

    # Avoid north wall
    if (self.y < 100 and (self.heading > 180 and self.heading < 360)):
      self.heading = random.randint(0, 90)
    self.drive(self.heading, 100)

  def do_autoscan(self):
    if time.time() < self.lastScanTime + .4:
      return

    self.lastScanTime = time.time()

    result = self.scan(self.scandirection, 10)

    # If there's someone there, shoot at them
    if (result > 0):
      self.fire(self.scandirection, result)
    # Increment scan direction
    self.scandirection = (self.scandirection + 10) % 360

  def post(self, msg):
    msg = msg[:43]
    #self.panel.msgBox.insert('1.0', msg + '\n')
    self.panel.msgBox.insert(END, '\n' + msg)
    self.panel.msgBox.see(END)

  def time():
    return self.arena.time()

  def send_message(self,reply):
    #print("sending: ", reply)
    reply = reply + ':'
    self.sock.send(reply.encode("utf-8"))
    #time.sleep(.001)

  def report(self):
    speed = int(self.currentSpeedMPS*100/self.maxSpeedMPS)
    dir = (360 + self.dir) % 360
    reply = "%d;status;%d;%d;%d;%d;%d;%d;%f" % (self.index,self.x,self.y,self.health,self.mHeat,speed,dir,self.arena.gametime)
    self.send_message(reply)

  def fire(self, dir, range):
    # Return with no action if robot is dead or game is paused
    if self.status != "A" or self.arena.status != "R":
      reply = "%d;fire;-1" % (self.index)
      self.send_message(reply)
      return

    #print("Firing", dir, range)
    goodToFire = True
    if range < 40:
      goodToFire = False

    if range > 700:
      goodToFire = False

    if dir < 0 or dir > 359:
      goodToFire = False

    if time.time() < self.loadingFinishTime:
      goodToFire = False

    if goodToFire == True:
      self.clear_scans()
      self.clear_bomb()
        
      dist = range
      rtheta = dir / 57.3
      self.xt = self.x + dist * math.cos(rtheta)
      self.yt = self.y + dist * math.sin(rtheta)
      self.tick1 = self.arena.line(self.xt-10, self.yt, self.xt+10, self.yt, fill=colors[self.index-1])
      self.tick2 = self.arena.line(self.xt, self.yt-10, self.xt, self.yt+10, fill=colors[self.index-1])
      self.startx = self.x
      self.starty = self.y
      self.ticks = dist / 200 * QUANTA
      self.tickCount = self.ticks
      self.shelldx = dist * math.cos(rtheta) / self.ticks
      self.shelldy = dist * math.sin(rtheta) / self.ticks
      self.ticks = int(self.ticks)
      self.shellIcon = self.arena.circle(self.x, self.y, 4, fill=colors[self.index-1])

      self.bHeat += 20
      self.shells -= 1
      self.loadingFinishTime = time.time() + 4
      self.loading = True
      #print("Shells left", self.index, self.shells)
      if self.shells == 0:
        #print("Reloading", self.index)
        self.loadingFinishTime += 8
        self.shells = 4
      self.shots += 1
      reply = "%d;fire;0" % (self.index)
    else:
      self.misfires += 1
      reply = "%d;fire;-1" % (self.index)
    self.send_message(reply)

  def place(self,sock, x, y):
    
    self.botIcon = self.arena.makebot(x, y, colors[self.index-1])
    #self.x = self.rect.centerx
    #self.y = 999 - self.rect.centery
    self.sock = sock
    self.name = "Temp"
    self.used = 1
    #self.quadrant = q
    self.x = x
    self.y = y
    self.currentSpeedMPS = 0
    self.speedGoalMPS = 0
    self.dir = random.randint(0,359)
    self.deltax = 0
    self.deltay = 0
    self.dirgoal = self.dir
    self.dirdelta = 0
    self.health = 100
    self.shells = 4
    self.status = "A"
    self.mHeat = 50
    self.bHeat = 0
    self.reload = 0
    self.cooling = False
    #self.scan = 0
    #blitRotateCenter(arena, self.image, self.x, angle):
    self.lastreport = time.time()
    #print (f"Placed x {self.x} y {self.y}")
    reply = "0;place;%d;%d;%d;%d" % (self.index,self.x,self.y,self.dir)
    #print(reply)
    self.send_message(reply)
    return self.index

  # set direction and speed
  def drive(self, direction, speed):
    # Return with no action if robot is dead or game is paused
    if self.status != "A" or self.arena.status != "R":
      return

    #print (f"Processing {direction} {speed}")
    speed = max(speed,0)
    speed = min(speed,100)
    # commanded speed in m/sec
    speed = speed / 100 * self.maxSpeedMPS

    if (self.currentSpeedMPS == 0):
      self.coasting = False

    # Are we coasting? do nothing until stopped
    if self.coasting:
      return

    # Are we braking? Don't change speed goal
    if (self.braking and self.currentSpeedMPS <= self.speedGoalMPS):
      self.braking = False

    if (not self.braking):
      self.speedGoalMPS = speed

    #self.dirgoal = (360-direction) % 360
    self.dirgoal = direction
    delta = self.dirgoal - self.dir

    if delta > 180:
      delta = delta - 360
    if delta <= -180:
      delta = delta + 360

    # Is commanded speed too fast? Coast to stop in current dir.
    if abs(delta) > 75 and speed > 4 and self.currentSpeedMPS > 4:
        self.coasting = True
    if abs(delta) > 50 and speed > 7.5 and self.currentSpeedMPS > 7.5:
        self.coasting = True
    if abs(delta) > 25 and speed > 10 and self.currentSpeedMPS > 10:
        self.coasting = True

    # is current speed too fast?
    if abs(delta) > 75 and self.currentSpeedMPS > 4:
        self.braking = True
        self.speedGoalMPS = 4
    if abs(delta) > 50 and self.currentSpeedMPS > 7.5:
        self.braking = True
        self.speedGoalMPS = 7.5
    if abs(delta) > 25 and self.currentSpeedMPS > 10:
        self.braking = True
        self.speedGoalMPS = 10

    if self.coasting:
      delta = 0
      self.speedGoalMPS = 0
      self.dirgoal = self.dir

    self.dirdelta = delta
    #print (f"Speed goal = {self.speedGoalMPS}, dirgoal = {self.dirgoal}")

  def clear_scans(self):
    if self.scanLine1 != 0:
        self.arena.delete(self.scanLine1)
        self.arena.delete(self.scanLine2)
        self.scanLine1 = 0

  def clear_bomb(self):
    if self.bombIcon != 0:
      self.arena.delete(self.bombIcon)
      #self.bombIcon.destroy()

  def update(self):
    #print("bot update")
    
    # Speed in percent
    speed = int(self.currentSpeedMPS*100/self.maxSpeedMPS)

    self.shell_update()
    if self.used == 0 or self.status == "D" or self.arena.status != "R":
      return
    
    if self.autopilot == True:
      self.do_autopilot()

    if self.autoscan == True:
      self.do_autoscan()

    if ((self.scantime + 0.1) < time.time()):
      self.clear_scans()

    if time.time() > self.bombTime:
      self.clear_bomb()

    if self.dirdelta != 0:
      # calculate turning rate
      newrate = int(speed / 25)
      if newrate >= 3: 
          rate = 30 / QUANTA
      elif newrate == 2: 
          rate = 40 / QUANTA
      elif newrate == 1: 
          rate = 60 / QUANTA
      elif newrate == 0: 
          rate = 90 / QUANTA
      
      delta = self.dirdelta
      if (delta > rate):
        delta = rate
      if (delta < rate * -1):
        delta = rate * -1
      self.dir = (self.dir + delta) % 360
      #print("dir: ", self.dir)
      self.dirdelta = self.dirdelta - delta
      self.deltax = self.currentSpeedMPS * math.cos(self.dir / 57.3) / QUANTA
      self.deltay = self.currentSpeedMPS * math.sin(self.dir / 57.3) / QUANTA

    # barrel cooling
    self.bHeat = self.bHeat - (2 / QUANTA)

    if self.bHeat < 0:
      self.bHeat = 0

    # motor heating
    speedPct = self.currentSpeedMPS * 100 / self.maxSpeedMPS
    # heating is 4 degrees per second at 35%, 8 degree per second at 70%, 12 at 105%
    # cooling is 2 degrees per second at 100 deg, 4 at 200
    # equilibrium is 100 deg at 35%, 200 deg at 70% 300 at 105%
    heat = speedPct * 5 / 35 - 3
    heat = max(heat,0)
    cool = self.mHeat * 3 / 100
    #print("temp %0.0f speedPct %0.0f heat %0.0f cool %0.0f" % (self.mHeat, speedPct, heat, cool))
    self.mHeat = self.mHeat + (heat - cool) / QUANTA
    if self.mHeat < 50:
      self.mHeat = 50

    if self.mHeat >= 200:
      self.cooling = True
      self.mHeat = 200
    
    # Check if we overheated and are cooling
    if self.cooling:
      self.currentSpeedMPS = min(self.maxSpeedMPS * .35, self.currentSpeedMPS)
      self.speedGoalMPS = min(self.maxSpeedMPS * .35, self.speedGoalMPS)
      self.deltax = self.currentSpeedMPS * math.cos(self.dir / 57.3) / QUANTA
      self.deltay = self.currentSpeedMPS * math.sin(self.dir / 57.3) / QUANTA
      if self.mHeat <= 180:
        self.cooling = False

    if self.mHeat < 0:
      self.mHeat = 0

    # adjust speed
    delta = self.speedGoalMPS - self.currentSpeedMPS
    if delta != 0:
      if (delta > (10 / QUANTA)):
        delta = (10 / QUANTA)
      if (delta < (-10 / QUANTA)):
        delta = (-10 / QUANTA)
      self.currentSpeedMPS = self.currentSpeedMPS + delta
      # calculate per tick movement
      self.deltax = self.currentSpeedMPS * math.cos(self.dir / 57.3) / QUANTA
      self.deltay = self.currentSpeedMPS * math.sin(self.dir / 57.3) / QUANTA
      #print("Speed: ", self.currentSpeedMPS, "Direction: ", self.dir, "Coasting: ", self.coasting, "Braking: ", self.braking)

    # Move the puppy
    newx = self.x + self.deltax
    if newx > 999 or newx < 0:
      self.currentSpeedMPS = 0
      self.speedGoalMPS = 0
      self.deltax = 0
      self.deltay = 0
      #Call wound(i, 5)
    else:
      self.x = newx
    
    # y is upside down - 0 at top
    newy = self.y + self.deltay
    if newy > 999 or newy < 0:
      self.currentSpeedMPS = 0
      self.speedGoalMPS = 0
      self.deltax = 0
      self.deltay = 0
      #Call wound(i, 5)
    else:
        self.y = newy
    #print(self.deltax, self.deltay)
    self.arena.move(self.botIcon, self.deltax, self.deltay)

    if self.reload > 0:
      self.reload = self.reload - 1 / QUANTA

    if((time.time() - self.lastreport) > .5):
      #print ("Setting...")
      self.lastreport = time.time()
      #print("Reporting...")
      self.panel.set_speed(self.currentSpeedMPS)
      self.panel.set_mheat(self.mHeat,self.cooling)
      self.panel.set_dir(self.dir)
      self.panel.set_bheat(self.bHeat)
      self.report()
      #print("scanning")
      #self.myScan()

  def shell_update(self):
    if self.ticks == 0:
      return
    self.ticks += -1
    if self.ticks <= 0:
      self.ticks = 0;
      self.explode()
      return
    coords = self.arena.center(self.shellIcon)
    self.shellx = coords[0]
    self.shelly = coords[1]

    dx = (self.startx + (self.shelldx * int(self.tickCount - self.ticks))) - self.shellx
    dy = (self.starty + (self.shelldy * int(self.tickCount - self.ticks))) - self.shelly
    self.arena.move(self.shellIcon, dx, dy)    

  def explode(self):
    self.arena.delete(self.tick1)
    self.arena.delete(self.tick2)
    self.arena.delete(self.shellIcon)
    self.bombIcon = self.arena.circle(self.xt, self.yt, 40, fill="red")
    #self.bombIcon = Label(self.arena, compound='top', image=self.my_bomb_img)
    #self.bombIcon.place(x = self.arena.xscale * self.xt, y = self.arena.height - self.arena.yscale * self.yt)
    self.bombTime = time.time() + .1

    for r in self.robots:
      if r.used == True:
        #print("Bot", r.index)
        dist = math.sqrt((self.xt - r.x)**2 + (self.yt - r.y)**2)
        if dist < 40:
          #print("3")
          max_damage = 10.5 - (200-(50+r.armor))**3 * -0.0000117
          if dist < 5:
            damage = max_damage
          else:
            damage = max_damage / dist * 5
          if damage > 0:
            #print("wounding", r.index, r.armor, dist, damage)
            r.wound(damage)
            self.damage += damage

  def scan(self, dir, res):
    self.clear_scans()
    # Return with no action if robot is dead or game is paused
    if (self.status != "A" or self.arena.status != "R") and self.autoscan == False:
      reply = "%d;scan;0;0" % (self.index)
      self.send_message(reply)
      return

    self.sdir = dir
    self.sres = res
    theta1 = (self.sdir - self.sres)
    if theta1 < 0:
      theta1 += 360
    theta2 = (self.sdir + self.sres)
    #print("dir", dir, "t1", theta1, "t2", theta2)
    endx = (1500 * math.cos(theta1 / 57.3)) + self.x
    endy = (1500 * math.sin(theta1 / 57.3)) + self.y
    #print("bot:", int(self.x), int(self.y), int(endx), int(endy))
    #print(self.x, self.y, endx, endy) 
    #pygame.draw.line(self.arena, (0, 0, 0), (self.x,1000-self.y), (endx,1000-endy))
    self.scanLine1 = self.arena.line(self.x, self.y, endx, endy, fill=colors[self.index-1])
    #print (type(self.scanLine1))
    endx = (1500 * math.cos(theta2 / 57.3)) + self.x
    endy = (1500 * math.sin(theta2 / 57.3)) + self.y  
    #pygame.draw.line(self.arena, (0, 0, 0), (self.x,1000-self.y), (endx,1000-endy))
    self.scanLine2 = self.arena.line(self.x, self.y, endx, endy, fill=colors[self.index-1])
    self.scantime = time.time()
    # See if we saw anyone

    dist = 2000
    closest = 0
    for r in self.robots:

      if r.status == "A" and r.index != self.index:

        rtheta = math.atan2((r.y - self.y), (r.x - self.x))

        if rtheta < 0:
          rtheta += (2 * math.pi)
        rtheta = rtheta * 57.3

        if rtheta > theta1 and rtheta < theta2:
          myDist = math.sqrt((r.y - self.y)**2 + (r.x - self.x)**2)
          if myDist < dist:
            dist = myDist
            closest = r.index
          reply = "%d;ping;%d:" % (r.index, self.index)
          self.robots[r.index-1].sock.send(reply.encode("utf-8"))

    if dist == 2000:
      dist = 0

    # Add in errors: error based on scan width
    if self.bHeat > 35:
      dist = 0
      closest = 0

    if dist > 0:
      dist += random.randint(-5 * self.sres, 5 * self.sres)
      #print (dist)
      # Barrel heat
      if random.randint(0,1):
        dist += self.bHeat
      else:
        dist -= self.bHeat

    #print("Dist, bheat", dist, self.bHeat)
    if self.autoscan == False:
      reply = "%d;scan;%d;%d" % (self.index, dist, closest)
      self.send_message(reply)
    return dist

  def pause(self):
    reply = "%d;pause" % (self.index)
    self.send_message(reply)
    
  def resume(self):
    reply = "%d;resume" % (self.index)
    self.send_message(reply)

  def cross_out(self):
    self.arena.line(self.x-6, self.y-6, self.x+7, self.y+7, fill="black", width=2)
    self.arena.line(self.x-6, self.y+7, self.x+7, self.y-6, fill="black", width=2)

  def wound(self, damage):
    self.health -= damage
    #print (f"Robot {self.index-1} health: {self.health}")
    self.panel.set_health(self.health)
    if self.health <= 0:
      print ("Robot dead: ", self.index-1)
      self.clear_scans()
      self.clear_bomb()
      self.speedGoalMPS = 0
      self.currentSpeedMPS = 0
      self.status = "D"
      self.cross_out()

