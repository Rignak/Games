"""
"""
import sys
import pygame
from . import Map, TextBox, Skill, Highlight, util
from os.path import join
from pygame.locals import *  # Import the event

def IfDeplacement(char, key, screen):
    """Move a character on the screen, after checking if the move is allowed

    Input:
    char - character
    key - K_DOWN, K_UP, K_LEFT or K_RIGHT
    screen - screen
    """
    oldPos = char.pos['tile']
    tileSize = screen.tileSize
    if key == K_DOWN and oldPos[1] < screen.size[0]//tileSize:
        newPos = (oldPos[0], oldPos[1]+1)
    elif key == K_UP and oldPos[1] > 0:
        newPos = (oldPos[0], oldPos[1]-1)
    elif key == K_LEFT and oldPos[0] > 0:
        newPos = (oldPos[0]-1, oldPos[1])
    elif key == K_RIGHT and oldPos[0] < screen.size[1]//tileSize:
        newPos = (oldPos[0]+1, oldPos[1])
    else:
        newPos = oldPos
    print('Move from', oldPos, 'to', newPos)
    px_pos = newPos[0]*screen.tileSize, newPos[1]*screen.tileSize
    change = True
    for altChar in screen.characters:
        if not altChar.dead and altChar.pos['px'] == px_pos and char != altChar:
            change = False
    p = int(Map.CheckProperties(px_pos, 'slowness', screen.mapData, tileSize))
    if p == -1 or p > char.cara['PM']:
        change = False
    if change:
        char.Move(screen, p, char.pos['tile'], newPos)
    return

def AimingLoop(char, screen, skill):
    """Action Loop: character choose a target for it's skill or return
    char - character
    screen - screen
    skill - skill

    Output
    boolean - True if a skill is used, else False"""
    blue = skill.Aim(char, screen)
    alpha = 80
    color = (255, 0, 0)
    red = {}
    tile = char.pos['tile']
    change = True
    end = False
    mainClock = pygame.time.Clock()
    skillDetails = screen.AddTextBox(TextBox.SkillDetails(skill, char),
                                     (screen.size[0]-128,screen.size[1]-2*100))
    while True:
        screen.refresh()
        mainClock.tick(30)
        for event in pygame.event.get():
            if event.type == QUIT:  # The game is closed
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                change = True
                if event.key == K_RETURN and char.cara['PA'] > skill.cara['cost']:
                    char.Attack(skill, red, screen, tile)
                    end = True
                    screen.UpdateStatus(char)
                    for i in screen.ui['hovering']:
                        screen.RemoveObject(i)
                    screen.ui['hovering'] = []
                elif event.key == K_DOWN and (tile[0], tile[1]+1) in blue:
                        tile = (tile[0], tile[1]+1)
                elif event.key == K_UP and (tile[0], tile[1]-1) in blue:
                        tile = (tile[0], tile[1]-1)
                elif event.key == K_LEFT and (tile[0]-1, tile[1]) in blue:
                        tile = (tile[0]-1, tile[1])
                elif event.key == K_RIGHT and  (tile[0]+1, tile[1]) in blue:
                    tile = (tile[0]+1, tile[1])
            elif event.type == MOUSEMOTION:
                mouse_pos = screen.onHover(event.pos)
                if mouse_pos in blue:
                    change = True
                    tile = mouse_pos

            if (event.type == KEYDOWN and event.key == K_ESCAPE) or end:# Return to skill menu
                print('Return to skill menu')
                for index in list(blue.values()) + list(red.values()) + skillDetails:
                    screen.RemoveObject(index)
                if end:
                    return True
                return False

            if change:
                change = False
                tiles = skill.AOE(tile, char, screen)
                s = Highlight.HighlightTiles(screen.tileSize, tiles, alpha, color)
                for index in list(red.values()):
                    screen.RemoveObject(index)
                red = {}
                for pos in s:
                        red[pos] = screen.AddHighlight(s[pos])
                screen.onHover((tile[0]*screen.tileSize, tile[1]*screen.tileSize))

def MenusLoop(menu, screen, char=None):
    """Action Loop: character navigate in the menus
    menu - string: name of the menu entered
    char - character
    screen - screen

    Output
    None if a skill is used
    'Exit' or 'End Turn': reason to quit the menus"""
    skills = Skill.ListSkills()
    implemented_menu = TextBox.ListMenus()
    menus = [menu]
    select = 1
    menuIndex, selectId = screen.OpenMenu(menu)
    choice = None
    mainClock = pygame.time.Clock()
    while True:
        screen.refresh()
        mainClock.tick(30)
        for event in pygame.event.get():
            if event.type == QUIT:  # The game is closed
                pygame.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                ####### We are doing something in the menu ######
                if event.key == K_RETURN:  # We open a menu
                    choice = screen.objects[menuIndex[0]][0].string[select-1]
                    if char and choice in skills: # We use a skill
                        for skill in char.skills:
                            if choice == skill.cara['name']:
                                print('Aim with skill', choice)
                                screen.QuitMenu(menuIndex, selectId)
                                select = 1
                                use = AimingLoop(char, screen, skill)
                                if not use:
                                    menuIndex, selectId = screen.OpenMenu(menus[-1], char=char)
                                else:
                                    return

                    elif choice in implemented_menu:
                        print('Open menu:', choice)
                        menus.append(choice)
                        old_menuIndex, old_selectId = menuIndex, selectId
                        menuIndex, selectId = screen.OpenMenu(menus[-1], char=char)
                        screen.QuitMenu(old_menuIndex, old_selectId)
                        select = 1
                    else: # Nothing
                        pass
                if event.key == K_UP or event.key == K_DOWN:  # We navigate through the menu
                    select, selectId = screen.MenuNavigation(event.key, menuIndex, select, selectId)
                if screen.charBox != -1 and (event.key == K_RIGHT or event.key == K_LEFT):
                    screen.QuitMenu(menuIndex, selectId)
                    if event.key == K_RIGHT:
                        j = -1
                    else:
                        j = 1
                    screen.charBox = (screen.charBox+j)%len(screen.characters)
                    menuIndex, selectId = screen.OpenMenu('Status')
                    screen.RemoveObject(selectId)
                ##### We are closing a menu #####
                if event.key == K_ESCAPE or choice == 'Exit' or choice == 'End Turn':
                    for index in screen.ui['childBox'] + screen.ui['hovering']:
                        screen.RemoveObject(index)
                    screen.ui['childBox'] = []
                    screen.ui['hovering'] = []
                    if len(menus) > 1:  # Go to the previous menu
                        menus.pop(-1)
                        print('Return to menu:', menus[-1])
                        screen.QuitMenu(menuIndex, selectId)
                        menuIndex, selectId = screen.OpenMenu(menus[-1], char=char)
                        select = 1
                        screen.charBox = -1
                    else: # We quit the last menu
                        menus = []
                        screen.QuitMenu(menuIndex, selectId)
                        return choice

def MovementLoop(char, screen):
    """Action Loop: character move on the map
    char - character
    screen - screen"""
    mainClock = pygame.time.Clock()
    while True:
        screen.refresh()
        mainClock.tick(30)
        for event in pygame.event.get():
            if event.type == QUIT:  # The game is closed
                pygame.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                if event.key == K_RETURN:
                    print('Opening main menu')
                    return 'MainMenu'
                if event.key in [K_UP, K_DOWN, K_RIGHT, K_LEFT]:
                    # We move the current character
                    IfDeplacement(char, event.key, screen)

            elif event.type == MOUSEMOTION:
                screen.onHover(event.pos)

def PlacementLoop(iniTiles, screen):
    """Action Loop: the player pos it's char on the map
    iniTiles - list of tuple of two int
    screen - screen"""
    highlighted = Highlight.HighlightTiles(screen.tileSize, iniTiles,60, (0, 0,255))
    blue, red = {}, [False, False]
    for pos in highlighted:
        blue[pos] = screen.AddHighlight(highlighted[pos])
    l = list(blue.keys())
    select = 0
    selectMenu = 0
    s = Highlight.HighlightTiles(screen.tileSize,[l[select]], 120, (255, 0, 0))
    red = [screen.AddHighlight(s[l[select]]), l[select]]

    mainClock = pygame.time.Clock()
    chars = {}
    menu_open = False
    j = False
    available = []
    for i, char in enumerate(screen.characters):
        if char.team == 1:
            screen.charBox = i
            available.append(char)
    max_chara = len(available)
    while True:
        screen.refresh()
        mainClock.tick(30)
        change = False
        for event in pygame.event.get():
            if event.type == QUIT:  # The game is closed
                pygame.quit()
                sys.exit()

            elif event.type == KEYDOWN:
                if menu_open:
                    if event.key == K_RETURN:
                        chars[l[screen.charBox]] = screen.characters[screen.charBox]
                        screen.characters[screen.charBox].UpdatePos(screen.tileSize, posTile = l[select])
                        screen.characters[screen.charBox].index = screen.AddCharacter(screen.characters[screen.charBox], 'standing')
                        change = True
                        for i, char in enumerate(available):
                            if char == screen.characters[screen.charBox]:
                                available.pop(i)
                                break
                        if len(available) == 0:
                            screen.RemoveObject(red[0])
                            for tile in list(blue.values()) + screen.ui['childBox']:
                                screen.RemoveObject(tile)
                            screen.ui['childBox'] = []
                            screen.QuitMenu(menuIndex, selectId)
                            screen.charBox = -1
                            return chars
                        screen.charBox = (screen.charBox+1)%len(l)
                        while screen.characters[screen.charBox].team == 1:
                            screen.charBox = (screen.charBox+1)%len(l)
                        event.key = K_ESCAPE
                    elif event.key in [K_UP, K_DOWN]:  # We navigate through the menu
                        selectMenu, selectId = screen.MenuNavigation(event.key, menuIndex, selectMenu, selectId)
                    elif event.key in [K_RIGHT, K_LEFT]:
                        screen.QuitMenu(menuIndex, selectId)
                        if event.key == K_RIGHT:
                            j = -1
                        else:
                            j = 1
                        screen.charBox = (screen.charBox+j)%len(screen.characters)
                        while screen.characters[screen.charBox] not in available:
                            screen.charBox = (screen.charBox+j)%len(screen.characters)
                        menuIndex, selectId = screen.OpenMenu('Status')

                    if event.key == K_ESCAPE:
                        for index in screen.ui['childBox']:
                            screen.RemoveObject(index)
                        screen.ui['childBox'] = []
                        screen.QuitMenu(menuIndex, selectId)
                        screen.charBox = -1
                        menu_open = False
                else:
                    if event.key == K_RETURN:
                        if l[select] in [char.pos['tile'] for char in screen.characters]:
                            for char in screen.characters:
                                if char.pos['tile'] == l[select]:
                                    available.append(char)
                                    char.UpdatePos(screen.tileSize)
                                    for index in char.index:
                                        screen.RemoveObject(index)
                        else:
                            screen.charBox = 1
                            while screen.characters[screen.charBox] not in available:
                                screen.charBox = (screen.charBox+1)%len(screen.characters)
                            menuIndex, selectId = screen.OpenMenu('Status')
                            menu_open = True
                    elif event.key == K_RIGHT:
                        select = (select+1)%len(l)
                        change = True
                    elif event.key == K_LEFT:
                        select = (select-1)%len(l)
                        change = True
                    elif event.key == K_ESCAPE and len(available)!=max_chara:
                        screen.RemoveObject(red[0])
                        for tile in blue:
                            screen.RemoveObject(blue[tile])
                        return chars
            elif event.type == MOUSEMOTION and not menu_open:
                mouse_pos = screen.onHover(event.pos)
                for i, tile in enumerate(l):
                    if mouse_pos == tile:
                        print(mouse_pos)
                        select = i
                        change = True
                        break
            if change:
                change = False
                screen.RemoveObject(red[0])
                s = Highlight.HighlightTiles(screen.tileSize,[l[select]],
                                             120, (255, 0, 0))
                red = [screen.AddHighlight(s[l[select]]), l[select]]


def VNLoop(screen, lines):
    """Action Loop: visual novel part
    screen - screen
    lines - list of string: lines of the script"""
    on_screen = {}
    mainClock = pygame.time.Clock()
    for line in lines:
        change = False
        if ':' in line:  # This is a declaration
            box = TextBox.Dialog(util.FormatText(line, 42))
            pos = (int((screen.size[0]-box.size[0])/2),screen.size[1]-box.size[1])
            current_dialog = screen.AddTextBox(box, pos)
        else:  # A character enter or leave
            change = True
            line = line.split()
            if line[0] == 'enter':
                char, file, transf, pos = line[1:]
                x, y = tuple([int(ele) for ele in pos.split(',')])
                if x < 0:
                    x = screen.size[0]+x
                if y < 0:
                    y = screen.size[1]+y
                img = pygame.image.load(join('res', 'sprite',
                                        file.split('_')[0], file))
                if transf == 'sym':
                    sprite = pygame.transform.flip(img, True, False)
                else:
                    sprite = img
                on_screen[char] = screen.AddSprite(sprite, (x, y))
            elif line[0] == 'leave':
                screen.RemoveObject(on_screen[line[1]])
        while change == False:
            screen.refresh()
            mainClock.tick(30)
            for event in pygame.event.get():
                if event.type == QUIT:  # The game is closed
                    pygame.quit()
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_RETURN:
                        change = True
                        [screen.RemoveObject(index) for index in current_dialog]
    [screen.RemoveObject(i) for i in current_dialog + list(on_screen.values())]
    print('Dialog end')

