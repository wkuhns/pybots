import pygame
from pygame.locals import *
#from graphics import *
import time
import socket
import sys
import selectors
import types
import random
import math

botGroup = pygame.sprite.Group()
shellGroup = pygame.sprite.Group()

botIcons = ["redbot.png", "greenbot.png", "bluebot.png", "yellowbot.png"]

QUANTA = 30            # frames per second
startTime = 0

class quad:
  def __init__(self):
    self.used = 0
    self.x = 0
    self.y = 0

quads = [quad(), quad(), quad(), quad()]
quads[0].x = 100
quads[0].y = 100
quads[1].x = 100
quads[1].y = 600
quads[2].x = 600
quads[2].y = 100
quads[3].x = 600
quads[3].y = 600

class shell(pygame.sprite.Sprite):

  def __init__(self, arena):
    pygame.sprite.Sprite.__init__(self)
    self.image = pygame.Surface([5, 5])
    self.image.fill((0, 0, 0))
    self.rect = self.image.get_rect()
    self.arena = arena
    #print ("Shell Initialized")

  def fire(self, xr, yr, dir, dist):
    rtheta = dir / 57.3
    self.xt = xr + dist * math.cos(rtheta)
    self.yt = 1000 - (yr + dist * math.sin(rtheta))
    #self.xt = xt
    #self.yt = 1000-yt
    self.startx = xr
    self.starty = 1000-yr
    self.rect.centerx = xr
    self.rect.centery = 1000-yr
    self.ticks = dist / 200 * QUANTA
    self.tickCount = self.ticks
    self.deltax = dist * math.cos(rtheta) / self.ticks
    self.deltay = dist * math.sin(rtheta) / self.ticks * -1
    self.ticks = int(self.ticks)
    pygame.draw.circle(self.arena, (255, 0, 0), (self.xt, self.yt), 4)
    shellGroup.add(self)

  def update(self):
    #pygame.draw.circle(self.arena, (255, 0, 0), (self.xt, self.yt), 4)
    pygame.draw.line(self.arena, (255, 0, 0), (self.xt - 10, self.yt), (self.xt+10, self.yt))
    pygame.draw.line(self.arena, (255, 0, 0), (self.xt, self.yt - 10), (self.xt, self.yt + 10))
    self.ticks += -1
    if self.ticks <= 0:
      shellGroup.remove(self)
      self.explode()
      print("Removed: ", self.rect.centerx, self.rect.centery)

    dx = (self.startx + (self.deltax * int(self.tickCount - self.ticks))) - self.rect.centerx
    dy = (self.starty + (self.deltay * int(self.tickCount - self.ticks))) - self.rect.centery
    self.rect.move_ip(dx, dy)

  def explode(self):
    pygame.draw.circle(self.arena, (255, 0, 0), (self.xt, self.yt), 40)

    for r in botGroup.sprites():
      dist = math.sqrt((self.xt - r.x)**2 + (1000 - self.yt - r.y)**2)
      damage = 0
      if dist < 40:
        damage = 3
      if dist < 20:
        damage = 7
      if dist < 10:
        damage = 12
      if dist < 6:
        damage = 25
      if damage > 0:
        r.wound(damage)

class bot(pygame.sprite.Sprite):
  lastReport = 0
  braking = False
  coasting = False

  def __init__(self, index, arena):
    pygame.sprite.Sprite.__init__(self)
    self.index = index
    self.arena = arena
    messages = [b""]
    self.used = 0
    self.name = "Robot"
    self.quadrant = 0
    self.deltax = 0
    self.deltay = 0
    self.sinfactor = 0   # sin(dir) in radians divided by tick rate
    self.cosfactor = 0
    self.status = "D"
    self.color = 0
    self.pingnotify = 0   # ID of bot who scanned me
    self.proc = 0        # pointer to object in user#s program space
                          # containing ping and die methods
    self.dir = 45
    self.dirgoal = 45
    self.dirdelta = 0    # +/- increment to turn
    self.speed = 1       # current speed in meters/sec
    self.speedgoal = 0   # requested speed in meters/sec
    self.speedx = 0
    self.speedy = 0      # current axis movement in pixels per tick
    self.shells = 4
    self.mHeat = 0       # motor heat
    self.bHeat = 0       # barrel heat
    self.reload = 0      # ticks till ready
    self.fire = 0        # ticks till shell hits
    self.newshot = 0     # flag for new shell. Cleared by display
    self.tx = 0          # target x,y
    self.ty = 0
    self.dx = 0          # shell x, y
    self.dy = 0
    self.scan = 0       # scanning flag - at present,
                          # set by scan method and cleared
                          # when display accesses scan data
    self.sdir = 45
    self.sres = 10
    self.lastscanned = 0  # ID of last 'bot who I scanned
    self.health = 100
    self.maxSpeed = 20

  def send_message(self,reply):
    #print("sending: ", reply)
    reply = reply + ':'
    self.sock.send(reply.encode("utf-8"))
    #time.sleep(.001)

  def myScan(self, dir, res):
    self.sdir = dir
    self.sres = res

    theta1 = (self.sdir - self.sres/2)
    if theta1 < 0:
      theta1 += 360
    theta2 = (self.sdir + self.sres/2)
    endx = (1500 * math.cos(theta1 / 57.3)) + self.x
    endy = (1500 * math.sin(theta1 / 57.3)) + self.y  
    pygame.draw.line(self.arena, (0, 0, 0), (self.x,1000-self.y), (endx,1000-endy))

    endx = (1500 * math.cos(theta2 / 57.3)) + self.x
    endy = (1500 * math.sin(theta2 / 57.3)) + self.y  
    pygame.draw.line(self.arena, (0, 0, 0), (self.x,1000-self.y), (endx,1000-endy))

    # See if we saw anyone
    dist = 0
    for r in robots:
      if r.status == "A" and r.index != self.index:
        rtheta = math.atan2((r.y - self.y), (r.x - self.x))
        if rtheta < 0:
          rtheta += (2 * math.pi)
        rtheta = rtheta * 57.3

        if rtheta > theta1 and rtheta < theta2:
          dist = math.sqrt((r.y - self.y)**2 + (r.x - self.x)**2)
          self.ping(r.index)

    # Add in errors: error based on scan width
    if self.bHeat > 35:
      dist = 0

    if dist > 0:
      dist += random.randint(-1 * self.sres, self.sres)
      print (dist)
      # Barrel heat
      if random.randint(0,1):
        dist += self.bHeat
      else:
        dist -= self.bHeat

    #print("Dist, bheat", dist, self.bHeat)

    reply = "%d;scan;%d;%d" % (self.index, dist, dir)
    self.send_message(reply)
  
  def myFire(self, dir, range):
    if range >= 40 and range <= 700 and dir >= 0 and dir <= 359: 
      shells[self.index-1].fire(self.x, self.y, dir, range)
      self.bHeat += 20;
      reply = "%d;fire;0" % (self.index)
    else:
      reply = "%d;fire;-1" % (self.index)
    self.send_message(reply)

  def report(self):
    speed = int(self.speed*100/self.maxSpeed)
    dir = (360 - self.dir) % 360
    reply = "%d;status;%d;%d;%d;%d;%d;%d;%d" % (self.index,self.x,self.y,self.health,self.mHeat,speed,dir,self.pingnotify)
    self.send_message(reply)

  def ping(self, enemy):
    reply = "%d;ping;%d" % (enemy, self.index)
    robots[enemy-1].sock.send(reply.encode("utf-8"))

  def blitRotateCenter(arena, image, topleft, angle):
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)
    arena.blit(rotated_image, new_rect)

  def place(self,sock):
    x = 0
    for q in range (0, 3):
      if quads[q].used == 0:
        x = 1
    
    if x == 0:
      print("Quadrant allocation error. Start over.")
      return 0

    self.sock = sock
    # Pick a random quadrant
    q = random.randint(0,3)
    while quads[q].used == 1:
      q = random.randint(0,3)
    print (f"picked {q}")
    quads[q].used = 1
    
    self.image = pygame.image.load(botIcons[q])
    self.rect = self.image.get_rect()
    self.rect.center=(random.randint(40,1000-40),500)
    self.x = self.rect.centerx
    self.y = 999 - self.rect.centery

    self.name = "Temp"
    self.used = 1
    self.quadrant = q
    self.x = random.randint(0,300) + quads[q].x
    self.y = random.randint(0,300) + quads[q].y
    self.speed = 0
    self.speedgoal = 0
    self.dir = random.randint(0,359)
    self.sinfactor = math.sin(self.dir / 57.3)
    self.cosfactor = math.cos(self.dir / 57.3)
    self.deltax = 0
    self.deltay = 0
    self.dirgoal = self.dir
    self.dirdelta = 0
    self.health = 100
    self.shells = 4
    self.status = "A"
    self.mHeat = 0
    self.bHeat = 0
    self.reload = 0
    self.fire = 0
    self.scan = 0
    #blitRotateCenter(arena, self.image, self.x, angle):
    self.lastReport = time.time()
    print (f"Placed x {self.x} y {self.y}")
    reply = "0;place;%d;%d;%d;%d" % (self.index,self.x,self.y,self.dir)
    print(reply)
    self.send_message(reply)
    return self.index

  # set direction and speed
  def drive(self, direction, speed):
    #print (f"Processing {direction} {speed}")
    speed = max(speed,0)
    speed = min(speed,100)
    # commanded speed in m/sec
    speed = speed / 100 * self.maxSpeed

    if (self.speed == 0):
      self.coasting = False

    # Are we coasting? do nothing until stopped
    if self.coasting:
      return

    # Are we braking? Don't change speed goal
    if (self.braking and self.speed <= self.speedgoal):
      self.braking = False

    if (not self.braking):
      self.speedgoal = speed

    self.dirgoal = (360-direction) % 360
    delta = self.dirgoal - self.dir

    if delta > 180:
      delta = delta - 360
    if delta <= -180:
      delta = delta + 360

    # Is commanded speed too fast? Coast to stop in current dir.
    if abs(delta) > 75 and speed > 4 and self.speed > 4:
        self.coasting = True
    if abs(delta) > 50 and speed > 7.5 and self.speed > 7.5:
        self.coasting = True
    if abs(delta) > 25 and speed > 10 and self.speed > 10:
        self.coasting = True

    # is current speed too fast?
    if abs(delta) > 75 and self.speed > 4:
        self.braking = True
        self.speedgoal = 4
    if abs(delta) > 50 and self.speed > 7.5:
        self.braking = True
        self.speedgoal = 7.5
    if abs(delta) > 25 and self.speed > 10:
        self.braking = True
        self.speedgoal = 10

    if self.coasting:
      delta = 0
      self.speedgoal = 0
      self.dirgoal = self.dir

    self.dirdelta = delta
    #print (f"Speed goal = {self.speedgoal}, dirgoal = {self.dirgoal}")

  def update(self):
    if self.used == 0:
      return
    #print(f"Processing {self.index}")
    # adjust heading if we're turning
    if self.dirdelta != 0:
      # calculate turning rate
      newrate = int(self.speed / 25)
      if newrate == 4: 
          rate = 30 / QUANTA
      elif newrate == 3: 
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
      # Cos(dir) in radians
      # Precalculated to avoid doing it every frame
      self.cosfactor = math.cos(self.dir / 57.3)
      self.sinfactor = math.sin(self.dir / 57.3)
      self.deltax = self.speed * self.cosfactor / QUANTA
      self.deltay = self.speed * self.sinfactor / QUANTA * -1

    # barrel cooling
    self.bHeat = self.bHeat - (2 / QUANTA)
    if self.bHeat < 0:
      self.bHeat = 0
    
    # motor heating
    heat = (self.speed - 35) / (5 * QUANTA)
    # accelerate cooling
    if heat <= 0:
      heat = heat * (30 / QUANTA) - 2
    self.mHeat = self.mHeat + heat
    if self.mHeat >= 200:
        self.mHeat = 200
        self.speed = 35
        self.speedgoal = 35
        self.deltax = self.speed * self.cosfactor / QUANTA
        self.deltay = self.speed * self.sinfactor / QUANTA * -1
    
    if self.mHeat < 0:
      self.mHeat = 0

    # adjust speed
    delta = self.speedgoal - self.speed
    if delta != 0:
      if (delta > (10 / QUANTA)):
        delta = (10 / QUANTA)
      if (delta < (-10 / QUANTA)):
        delta = (-10 / QUANTA)
      self.speed = self.speed + delta
      # calculate per tick movement
      self.deltax = self.speed * self.cosfactor / QUANTA
      self.deltay = self.speed * self.sinfactor / QUANTA * -1
      #print("Speed: ", self.speed, "Direction: ", self.dir, "Coasting: ", self.coasting, "Braking: ", self.braking)


    # Move the puppy
    newx = self.x + self.deltax
    if newx > 999 or newx < 0:
      self.speed = 0
      self.speedgoal = 0
      self.deltax = 0
      self.deltay = 0
      #Call wound(i, 5)
    else:
      self.x = newx
    
    # y is upside down - 0 at top
    newy = self.y + self.deltay
    if newy > 999 or newy < 0:
      self.speed = 0
      self.speedgoal = 0
      self.deltax = 0
      self.deltay = 0
      #Call wound(i, 5)
    else:
        self.y = newy

    self.rect.move_ip(int(self.x-self.rect.centerx), int(1000-self.y-self.rect.centery))

    if self.reload > 0:
      self.reload = self.reload - 1 / QUANTA

    if((time.time() - self.lastReport) > .5):
      #print ("Setting...")
      self.lastReport = time.time()
      #print("Reporting...")
      self.report()
      #print("scanning")
      #self.myScan()

  def wound(self, damage):
    self.health -= damage
    print (f"Robot {self.index-1} health: {self.health}")
    if self.health <= 0:
      print ("Robot dead: ", self.index-1)
      self.status = "D"
      botGroup.remove(self)

robots = []

sel = selectors.DefaultSelector()

def placeBot(sock):
  r = len(robots)
  print(f"placing {r+1}")
  robots.append(bot(r+1, arena))
  robots[r].place(sock)  
  print(f"Bots: {robots[r].index}")

  botGroup.add(robots[r])

  print (f"placed {r}")
  return(robots[r].index)

def serviceConnection(key, mask):
  sock = key.fileobj
  data = key.data
  if mask & selectors.EVENT_READ:
    recv_data = sock.recv(1024)  # Should be ready to read
    if recv_data:
      data.outb = recv_data
      #print(f"Command {data.outb!r} from {data.addr}")
      cms = data.outb.decode("utf-8")
      cmds = cms.split(";")
      botIndex = int(cmds[0]) - 1
      botCmd = cmds[1]
      if botCmd == "scan":
        #print("Scan commd: ", cms)
        botParm1 = cmds[2]
        botParm2 = cmds[3]
        robots[botIndex].myScan(int(botParm1),int(botParm2))
      if botCmd == "place":
        botIndex = placeBot(sock)
        recv_data = ""
        data.outb = ""
        return
      if botCmd == "drive":
        #print(f"Drive #{botIndex}: {cmds[2]} {cmds[3]}")
        botParm1 = cmds[2]
        botParm2 = cmds[3]
        robots[botIndex].drive(int(botParm1),int(botParm2))
        data.outb = ""
        recv_data = ""
        return
      if botCmd == "fire":
        botParm1 = cmds[2]
        botParm2 = cmds[3]
        robots[botIndex].myFire(int(botParm1),int(botParm2))
        data.outb = ""
        recv_data = ""
        return
      if botCmd == "setDirection":
        botParm1 = cmds[2]
        robots[botIndex].setSpeedGoal(int(botParm1))
        #reply = "%d;%d" % (robots[botIndex].x, 4)
        data.outb = ""
        recv_data = ""
        return
    else:
      # Client has closed socket, close our end too
      print(f"Closing connection to {data.addr}")
      sel.unregister(sock)
      sock.close()
    data.outb = ""


def accept_wrapper(sock):
  conn, addr = sock.accept()  # Should be ready to read
  print(f"Accepted connection from {addr}")
  conn.setblocking(False)
  data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
  events = selectors.EVENT_READ | selectors.EVENT_WRITE
  sel.register(conn, events, data=data)

frame = pygame.display.set_mode((1400,1020))
arena = pygame.Surface((1000, 1000))
frame.blit(arena, (10, 10))

shells = [shell(arena), shell(arena), shell(arena), shell(arena)]

def main():
  pygame.init()

  pblack = pygame.Color(0, 0, 0)
  pred = pygame.Color(255, 0, 0)
  pgreen = pygame.Color(64, 196, 64)
  pblue = pygame.Color(0, 0, 255)

  clock = pygame.time.Clock()
  startTime = time.time()

  frame.fill(pblue)
  arena.fill(pgreen)
  pygame.display.set_caption("Arena")

  pygame.display.update()

  HOST = "127.0.0.1"               # Symbolic name meaning all available interfaces
  PORT = 50007              # Arbitrary non-privileged port

  lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  lsock.bind((HOST, PORT))
  lsock.listen()
  print(f"Listening on {(HOST, PORT)}")
  lsock.setblocking(False)
  sel.register(lsock, selectors.EVENT_READ, data=None)

  try:
    while True:
      # don't block
      events = sel.select(timeout=-10)
      for key, mask in events:
        # listening socket
        if key.data is None:
          accept_wrapper(key.fileobj)
        else:
          serviceConnection(key, mask)
      for r in botGroup.sprites():
        r.update()
      for s in shellGroup.sprites():
        s.update()
      botGroup.draw(arena)
      shellGroup.draw(arena)
      frame.blit(arena, (10, 10))
      pygame.display.flip()
      clock.tick(QUANTA)
      arena.fill(pgreen)
  except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
  finally:
    sel.close()
    pygame.quit()
    sys.exit()
  

main()