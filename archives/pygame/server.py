import pygame
from pygame.locals import *
#from graphics import *
import time
import socket
import sys
#import selectors
import types
import random
import asyncore, asynchat



class MainServerSocket(asyncore.dispatcher):
  def __init__(self, port):
    print ('initing MSS')
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.bind(('',port))
    self.listen(5)
  def handle_accept(self):
    newSocket, address = self.accept(  )
    print ("Connected from", address)
    SecondaryServerSocket(newSocket)

class SecondaryServerSocket(asynchat.async_chat):
    def __init__(self, *args):
        print ('initing SSS')
        asynchat.async_chat.__init__(self, *args)
        self.set_terminator('\n')
        self.data = []
    def collect_incoming_data(self, data):
        self.data.append(data.encode('utf-8'))
    def found_terminator(self):
        self.push(b''.join(self.data))
        print("Data: ". self.data)
        self.data = []
    def handle_close(self):
        print ("Disconnected")
        self.close(  )


class bot:
  def __init__(self):
    self.x = 0
    self.y = 0
    self.name = "Robot"
    self.quadrant = 0
    self.deltax = 0
    self.deltay = 0
    self.sinfactor = 0   # sin(dir) in radians divided by tick rate
    self.cosfactor = 0
    self.status = "Dead"
    self.color = 0
    self.pingnotify = 0   # ID of bot who scanned me
    self.proc = 0        # pointer to object in user#s program space
                          # containing ping and die methods
    self.dir = 0
    self.dirgoal = 0
    self.dirdelta = 0    # +/- increment to turn
    self.speed = 0
    self.speedgoal = 0
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
    self.sdir = 0
    self.sres = 0
    self.lastscanned = 0  # ID of last 'bot who I scanned
    self.health = 100
    self.sprite = pygame.sprite.Sprite
    self.sprite.image = pygame.image.load("redbot.png")
    self.sprite.rect = self.sprite.image.get_rect()
    self.sprite.rect.center=(random.randint(40,1000-40),500)
     
  def draw(self, surface):
    surface.blit(self.sprite.image, self.sprite.rect)

  def move(self):
    self.sprite.rect.move_ip(0,10)
    print(".")
    if (self.sprite.rect.bottom > 900):
      self.sprite.rect.top = 100

 
#sel = selectors.DefaultSelector()

def service_connection(key, mask):
  sock = key.fileobj
  data = key.data
  if mask & selectors.EVENT_READ:
    recv_data = sock.recv(1024)  # Should be ready to read
    if recv_data:
      data.outb += recv_data
    else:
      print(f"Closing connection to {data.addr}")
      sel.unregister(sock)
      sock.close()
  if mask & selectors.EVENT_WRITE:
    if data.outb:
      print(f"Echoing {data.outb!r} to {data.addr}")
      sent = sock.send(data.outb)  # Should be ready to write
      data.outb = data.outb[sent:]

def accept_wrapper(sock):
  conn, addr = sock.accept()  # Should be ready to read
  print(f"Accepted connection from {addr}")
  conn.setblocking(False)
  data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
  events = selectors.EVENT_READ | selectors.EVENT_WRITE
  sel.register(conn, events, data=data)

def main():

  #win = GraphWin('Arena',1000,1000)
  #win.yUp()
  #pt = Point(100, 50)
  #pt.draw(win)
  #cir = Circle(pt, 25)
  #cir.draw(win)
  #cir.setOutline('red')
  #cir.setFill('blue')
  #rect = Rectangle(Point(20, 10), pt)
  #rect.draw(win)

  robots = [bot(), bot(), bot(), bot()]

  pygame.init()

  surf = pygame.display.set_mode((1000,1000))
  pblack = pygame.Color(0, 0, 0)
  pred = pygame.Color(255, 0, 0)
  pgreen = pygame.Color(0, 128, 0)
  pblue = pygame.Color(0, 0, 255)

  #FPS = pygame.time.Clock()
  #FPS.tick(30)
  FPS = 30
  FramePerSec = pygame.time.Clock()

  surf.fill(pgreen)
  pygame.display.set_caption("Arena")
  
  robots[1].draw(surf)

  #pygame.draw.circle(surf, pblue, (100,50), 30)
  pygame.display.update()

  MainServerSocket(50007)
  asyncore.loop(  )

  while True:
    try:
      robots[1].move()
      surf.fill(pgreen)
      robots[1].draw(surf)
      pygame.display.update()
      FramePerSec.tick(FPS)

    except KeyboardInterrupt:
      print("Caught keyboard interrupt, exiting")
    finally:
      sel.close()
      pygame.quit()
      sys.exit()
  
  #win.getMouse()
  #win.close() 

main()