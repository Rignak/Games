from . import Highlight, Map, util, Effect
import random
from os.path import join
import pyganim
from math import ceil
import pygame
import json
import numpy as np
from random import uniform

class Skill():
    def __init__(self, file):
        self.FromJSON(file)

    def FromJSON(self, file):
        self.name = file
        with open(join('res','json', 'skill', file+'.json'), 'r') as file:
            data = json.load(file)['skill']
        self.cara = data['cara']
        self.sprite = {'values': data['sprite']}
        self.sheetName = data['sheet']
        self.CreateSprite()
        self.effects = {'values':data['effects'], 'effects':[]}
        if self.effects['values']:
            for e in self.effects['values']:
                effect = Effect.Effect(e['type'], e['power'], e['duration'], self.name)
                self.effects['effects'].append(effect)

        self.tileEffects = {'values':data['tileEffects'], 'effects':[]}
        for e in self.tileEffects['values']:
            effect = Effect.Effect(e['type'], e['power'], e['duration'], self.name)
            self.tileEffects['effects'].append(effect)
        self.sound = pygame.mixer.Sound(join('res', 'sound', data['sound']))

    def ToJSON(self):
        """Write the character in a .json
        Input :
        self - a character

        Output :
        Nothing, but a .json est written"""
        temp = {'cara':self.cara, 'sprite':self.sprite['values'],
                'sheet':self.sheetName, 'effects':self.effects}
        util.WriteJSON({'character':temp}, self.cara['name'])

    def CreateSprite(self):
        name = self.sheetName
        rows = self.sprite['values']['rows']
        cols = self.sprite['values']['cols']
        begin, end = self.sprite['values']['action']
        self.sprite['action'] = self.AddSprite(name, rows, cols, begin, end)

    def AddSprite(self, name, rows, cols, begin, end):
        """Make a sprite (animated or not) from a sheet

        Output:
        obj - a sprite"""
        fullname = join('res', 'sprite', 'effect', name)
        perso = pyganim.getImagesFromSpriteSheet(fullname,cols=cols,rows=rows)[begin:end]
        if end > begin+1:
            frames = list(zip(perso, [100]*(end-begin)))
            obj = pyganim.PygAnimation(frames)
            obj.play()
        else:
            obj = perso[0]
        return obj

    def Aim(self, character, screen):
        """Return the tiles aimed by the skill
        Input:
        self - skill
        character - character: the one using the skill
        screen - screen

        Output:
        blue - dictionary
            key - tuple of two int
            value - highlight"""
        center = (int(character.pos['px'][0]/screen.tileSize),
                  int(character.pos['px'][1]/screen.tileSize))

        aimable = self.GetAimable(center,screen, character)
        highlighted = Highlight.HighlightTiles(screen.tileSize, aimable,60, (0, 0,255))
        blue = {}
        for pos in highlighted:
            blue[pos] = screen.AddHighlight(highlighted[pos], priority=False)
        return blue

    def AOE(self, tile_pos, character, screen):
        """Return the tiles included in the AOE
        Input:
        self - skill
        tile_pos - tuple of two int: center of the AOE
        character - character using the skill
        screen - screen

        Output:
        finalTiles - list of tuple of two int"""
        tiles = [tile_pos]
        if self.cara['size'] == 1:
            pass
        elif self.cara['AOE'] == 'null':
            for i in range(self.cara['size']):
                j = 0
                while j+i < self.cara['size']:
                    tiles.append([tile_pos[0]-i, tile_pos[1]-j])
                    tiles.append([tile_pos[0]+i, tile_pos[1]-j])
                    tiles.append([tile_pos[0]-i, tile_pos[1]+j])
                    tiles.append([tile_pos[0]+i, tile_pos[1]+j])
                    j+=1
        elif self.cara['AOE'] == 'parallel':
            if tile_pos[0] != character.pos['tile'][0]:
                for i in range(self.cara['size']):
                    tiles.append([tile_pos[0], tile_pos[1]+i])
                    tiles.append([tile_pos[0], tile_pos[1]-i])
            elif tile_pos[1] != character.pos['tile'][1]:
                for i in range(self.cara['size']):
                    tiles.append([tile_pos[0]+i, tile_pos[1]])
                    tiles.append([tile_pos[0]-i, tile_pos[1]])
        elif self.cara['AOE'] == 'orthogonal':
            if tile_pos[0] != character.pos['tile'][0]:
                for i in range(self.cara['size']):
                    tiles.append([tile_pos[0]-i, tile_pos[1]])
                    tiles.append([tile_pos[0]+i, tile_pos[1]])
            elif tile_pos[1] != character.pos['tile'][1]:
                for i in range(self.cara['size']):
                    tiles.append([tile_pos[0], tile_pos[1]+i])
                    tiles.append([tile_pos[0], tile_pos[1]-i])
        finalTiles = []
        for tile in tiles:
            if tile not in finalTiles:
                finalTiles.append(tuple(tile))
        return finalTiles

    def Affect(self, character, allAffected, tiles, screen):
        """Use the skill and apply it's effect on the targets
        Input:
        self - skill
        character - character
        allAffected - list of character
        tiles - list of tuple of two int (target of the skill)
        screen - screen

        Output:
        xp - int: xp earn from the attack
        The effects are applied on the targets (character or tile)"""
        xp = 0
        drop = []
        animated = []
        for tile in tiles:
            for effect in self.tileEffects['effects']:
                screen.tileEffects.append([tile, effect])
        for i, affected in enumerate(allAffected):
            cara = affected.cara
            w, s = util.WeakAgainst(cara['type'])
            tileType = Map.CheckProperties(affected.pos['tile'], 'type',
                                            screen.mapData, screen.tileSize)
            if tileType == w:
                affected.cara['defense'] -= 56
                affected.cara['avoid'] -= 56
                affected.cara['speed'] -= 56
                affected.cara['resistance'] -= 56
                affected.cara['elementalRes'][w] -= 56
            elif w and tileType == cara['type']:
                affected.cara['defense'] += 56
                affected.cara['avoid'] += 56
                affected.cara['speed'] += 56
                affected.cara['resistance'] += 56
                affected.cara['elementalRes'][w] += 56
            else:
                w, s = util.WeakAgainst(tileType)
                if w:
                    affected.cara['elementalRes'][w] -= 23
                    affected.cara['elementalRes'][s] += 23


            if character.aiming == affected.pos['tile']:
                direction = util.GetDirection(affected.pos['tile'], character.pos['tile'])
            else:
                direction = util.GetDirection(affected.pos['tile'], character.aiming)
            if direction - affected.direction in [-2,2]:
                dmg = self.cara['damage'] * 1.5
                affected.cara['avoid'] = int(affected.cara['avoid']*0.75)
            elif direction - affected.direction in [-3,-1,1,3]:
                dmg = self.cara['damage'] * 1.25
                affected.cara['avoid'] = int(affected.cara['avoid']*0.5)
            else:
                dmg = self.cara['damage']
            if self.cara['type'] == 'magic':
                dmg = character.MagicalDmg(dmg)
                dmg = affected.MagicalReduction(dmg, self.cara['ele'])
            elif self.cara['type'] == 'physic':
                dmg = character.PhysicalDmg(dmg)
                dmg = affected.PhysicalReduction(dmg, self.cara['ele'])
            else:    # skill.type == 'heal'
                dmg = -character.MagicalDmg(self.cara['damage'])
            hit = affected.getCara('avoid')/character.getCara('hit')*self.cara['hit']
            r = random.random()
            affected.cara = cara
            if r < hit:
                animated.append(affected.pos['tile'])
                xp += affected.Affect(dmg, screen)
                for effect in self.effects['effects']:
                    xp += affected.Affect(effect, screen)
                if affected.dead:
                    for name, proba in affected.drop:
                        if uniform(0.0, 1.0) < proba:
                            drop.append(name)
        animations = []
        for tile in animated:
            pos = tuple(x*screen.tileSize for x in tile)
            animations.append(screen.AddSprite(self.sprite['action'], pos))
        if animations != []:
            mainClock = pygame.time.Clock()
            for i in range(25):
                screen.refresh()
                mainClock.tick(100)
            [screen.RemoveObject(index) for index in animations]
        if drop:
            character.Drop(drop, screen)
        return xp

    def GetAimable(self, pos, screen, character):
        """
        Input:
        self - skill
        pos - tuple of two int: origin of the attack
        screen - screen
        character - character using the attack

        Output:
        list of tuple of two int"""
        mapData, tileSize = screen.mapData, screen.tileSize
        aimable = set()
        scope = self.cara['range']
        p = 'transparent'
        pos = (int(pos[0]), int(pos[1]))
        for x in range(max(pos[0]-scope, 0), pos[0]+scope+1):
            diffX = x-pos[0]
            for y in range(max(pos[1]-scope,0), pos[1]+scope+1):
                diffY = y-pos[1]
                transparent = True
                if ((self.cara['AOE'] == 'parallel' or self.cara['AOE'] == 'orthogonal') and x != pos[0] and y!= pos[1])\
                    or abs(diffX) + abs(diffY) > scope\
                    or x >= screen.size[0]/tileSize or y >= screen.size[1]/tileSize \
                    or not Map.CheckProperties((x*tileSize, y*tileSize), p, mapData, tileSize):
                    transparent = False
                elif diffY != 0 or diffX != 0:
                    tileRange = Trajectory((x,y), pos, (diffX, diffY))
                    for x_c, y_c in tileRange:
                        if not Map.CheckProperties((x_c*tileSize, y_c*tileSize), p, mapData, tileSize)\
                            and (x_c, y_c) != pos:
                            transparent = False
                            break
                        if not self.cara['perce']:
                            for atlChar in screen.characters:
                                if atlChar.pos['tile'] == (x_c, y_c) and atlChar.team != character.team:
                                    transparent = False
                                    break
                if transparent:
                    aimable.add((x, y))
        aimable.add(pos)
        character.aiming = pos
        return list(aimable)

def Trajectory(xy, pos, diff):
    x, y = xy
    diffX, diffY = diff
    R = abs(diffY)+abs(diffX)
    yStep = diffY/R
    xStep = diffX/R
    if x < pos[0] and y < pos[1]:
        x, y = pos
        pos = xy
        yStep,xStep = -yStep, -xStep
    if xStep != 0:
        xRange = np.arange(pos[0], x, xStep)
    else:
        xRange = [x for i in range(R+1)]
    if yStep != 0:
        yRange = np.arange(pos[1], y, yStep)
    else:
        yRange = [y for i in range(R+1)]
    tileRange = []
    for x, y in zip(xRange, yRange):
        if abs(x%1-0.5) > 0.01 or abs(y%1-0.5) > 0.01:
            tileRange.append((round(x), round(y)))
    return tileRange