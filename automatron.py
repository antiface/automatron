import functools
import pygame
import numpy as np
import code
import threading
import multiprocessing
import sys

pygame.surfarray.use_arraytype("numpy")

from Tkinter import *

class Command(object):
    def __init__(self, action, *params):
        self.action = action
        self.params = params

class UIProcess(multiprocessing.Process):
    def __init__(self, pipe,rules, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self.pipe = pipe
        self.rules = rules
        self.daemon = True

    def run(self):
        root = Tk()
        root.title("Automatron Control Panel")
        root.resizable(False, False)

        base = Frame(root)
        base.pack()

        Label(base, text="Rule").grid(row=0, column=0, padx=5, pady=5)
        OptionMenu(base, StringVar(value="lamer"), *self.rules,
                   command=lambda rule: self.pipe.send(Command("rule", rule))).grid(row=0, column=1, padx=5, pady=5)

        buttonframe = Frame(base)
        buttonframe.grid(row=1, column=0, columnspan=2)

        self.pausebutton = Button(buttonframe, text="Pause",
               command=self.toggle_pause)
        self.pausebutton.pack(side=LEFT, padx=5, pady=5)

        Button(buttonframe, text="Step",
               command=self.do_step).pack(side=LEFT, padx=5, pady=5)

        Button(buttonframe, text="Reset",
               command=lambda: self.pipe.send(Command("reset"))).pack(side=LEFT, padx=5, pady=5)

        Button(buttonframe, text="Quit",
               command=lambda: self.pipe.send(Command("quit"))).pack(side=LEFT, padx=5, pady=5)

        root.mainloop()

        self.pipe.send(Command("quit"))

    def toggle_pause(self):
        self.pipe.send(Command("pause"))
        self.pausebutton['text'] = self.pausebutton['text'] == "Pause" and \
            "Unpause" or \
            "Pause"

    def do_step(self):
        self.pipe.send(Command("step"))
        self.pausebutton['text'] = "Unpause"

class ConsoleThread(threading.Thread):
    def __init__(self, slave, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self.slave = slave
        self.console = code.InteractiveConsole({ "self" : self.slave })

    def run(self):
        self.console.interact("Automatron Console\n"+
                              "Use self to access Automatron object.")
        self.slave.running = False

def rule_to_expression(rule):
    birth, survival = rule.split("/")

    births = [ int(x) for x in birth[1:] ]
    survivals = [ int(x) for x in survival[1:] ]

    def _closure(grid, neighbors):
        return \
        (
            (grid == 0) & reduce(
                lambda acc, v: (neighbors == v) | acc,
                births,
                grid == -1
            )
        ) | \
        (
            (grid == 1) & \
            reduce(
                lambda acc, v: (neighbors == v) | acc,
                survivals,
                grid == -1
            )
        )

    return _closure

class Automatron(object):
    SIZE = (512, 512)

    RULES = {
        "lamer"         : rule_to_expression("B/S"),

        "gnarl"         : rule_to_expression("B1/S1"),
        "replicator"    : rule_to_expression("B1357/S1357"),
        "fredkin"       : rule_to_expression("B1357/S02648"),
        "seeds"         : rule_to_expression("B2/S"),
        "lfod"          : rule_to_expression("B2/S0"),
        "serviettes"    : rule_to_expression("B234/S"),
        "dotlife"       : rule_to_expression("B3/S023"),
        "lwod"          : rule_to_expression("B3/S012345678"),
        "mazectric"     : rule_to_expression("B3/S1234"),
        "maze"          : rule_to_expression("B3/S12345"),       
        "life"          : rule_to_expression("B3/S23"),
        "coral"         : rule_to_expression("B3/S45678"),
        "34life"        : rule_to_expression("B34/S34"),
        "assimilation"  : rule_to_expression("B345/S4567"),
        "longlife"      : rule_to_expression("B345/S5"),
        "diamoeba"      : rule_to_expression("B35678/S5678"),
        "amoeba"        : rule_to_expression("B357/S1358"),
        "pseudolife"    : rule_to_expression("B357/S238"),
        "2x2"           : rule_to_expression("B36/S125"),
        "highlife"      : rule_to_expression("B36/S23"),
        "move"          : rule_to_expression("B368/S245"),
        "stains"        : rule_to_expression("B3678/S235678"),
        "daynight"      : rule_to_expression("B3678/S34678"),
        "drylife"       : rule_to_expression("B37/S23"),
        "coagulations"  : rule_to_expression("B378/S235678"),
        "walledcities"  : rule_to_expression("B45678/S2345"),
        "vote45"        : rule_to_expression("B4678/S35678"),
        "vote"          : rule_to_expression("B5678/S45678"),
        "inverselife"   : rule_to_expression("B0123478/S34678"),
    }

    def __init__(self):
        self.clock = pygame.time.Clock()
        self.running = True

        self.grid = np.zeros(self.SIZE, dtype=np.bool)

        self.rule = "lamer"
        self.cursor_size = 5
        self.paused = False

        self.screen = pygame.display.set_mode(self.SIZE)
        pygame.display.set_caption("Automatron")

        ConsoleThread(self).start()

        self.pipe, endpoint = multiprocessing.Pipe()
        UIProcess(endpoint, sorted(self.RULES.keys())).start()

    def tick(self):
        neighbors = np.zeros(self.grid.shape)

        neighbors[ 1:,  1:] += self.grid[:-1, :-1]
        neighbors[ 1:, :-1] += self.grid[:-1,  1:]
        neighbors[:-1,  1:] += self.grid[ 1:, :-1]
        neighbors[:-1, :-1] += self.grid[ 1:,  1:]
        neighbors[:-1,   :] += self.grid[ 1:,   :]
        neighbors[ 1:,   :] += self.grid[:-1,   :]
        neighbors[  :, :-1] += self.grid[  :,  1:]
        neighbors[  :,  1:] += self.grid[  :, :-1]

        self.grid = self.RULES[self.rule](
            self.grid,
            neighbors
        )

    def run(self):
        generations = 0

        while self.running:
            step = False

            # handle Tk things
            while self.pipe.poll():
                command = self.pipe.recv()

                if command.action == "rule":
                    self.rule = command.params[0]

                if command.action == "pause":
                    self.paused = not self.paused

                if command.action == "step":
                    self.paused = True
                    step = True

                if command.action == "reset":
                    self.grid = np.zeros(self.SIZE, dtype=np.bool)

                if command.action == "quit":
                    self.running = False

            event = pygame.event.poll()

            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    self.cursor_size += 1
                if event.button == 5:
                    self.cursor_size = max(0, self.cursor_size - 1)

            if not self.paused or step:
                self.tick()
                generations += 1

            mb1, mb2, mb3 = pygame.mouse.get_pressed()
            mposx, mposy = pygame.mouse.get_pos()

            if mb1:
                self.grid[max(0, mposx - self.cursor_size):
                          min(mposx + self.cursor_size + 1, self.SIZE[0]),
                          max(0, mposy - self.cursor_size):
                          min(mposy + self.cursor_size + 1, self.SIZE[1])] = \
                    True

            if mb3:
                self.grid[max(0, mposx - self.cursor_size):
                          min(mposx + self.cursor_size + 1, self.SIZE[0]),
                          max(0, mposy - self.cursor_size):
                          min(mposy + self.cursor_size + 1, self.SIZE[1])] = \
                    False

            channel = (1 - self.grid.clip(0, 1)) * 255
            pixmap = np.dstack([channel, channel, channel])

            pygame.surfarray.blit_array(self.screen, pixmap)
            pygame.display.flip()

            self.clock.tick(60)

        print "Ran for %d generations, ended with %d cells alive." % (
            generations,
            np.sum(self.grid)
        )

if __name__ == "__main__":
    Automatron().run()
