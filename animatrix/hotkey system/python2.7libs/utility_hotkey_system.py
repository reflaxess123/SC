import hou, nodegraph, os, csv, sys
import hdefereval
import types
import ctypes
from PySide2 import QtCore, QtWidgets, QtGui
from utility_ui import *
from canvaseventtypes import *
from utility_ui import *
from utility_generic import *
from collections import defaultdict
from nodegraphpopupmenus import MenuProvider
import nodegraphbase as base



this = sys.modules[__name__]

currentdir = os.path.dirname(os.path.realpath(__file__))
hotkeysfile = os.path.join(currentdir, "..", "hotkeys.csv")

showstatus = False

__actions = None
def __load_actions():
    if showstatus:
        print ("Reloading hotkeys...")

    global __actions
    __actions = defaultdict(lambda: defaultdict(list))
    with open(hotkeysfile) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for context in ("OBJECT", "SOP", "VOP", "DOP", "COP", "CHOP", "SHOP", "ROP", "TOP", "LOP"):
                if row[context] != '':
                    __actions[context][row["Key Name"]].append(row[context])
__load_actions()

this.fs_watcher = QtCore.QFileSystemWatcher()
this.fs_watcher.addPath(hotkeysfile)
this.fs_watcher.fileChanged.connect(__load_actions)

showstatus = True



def invokeActionFromKey(uievent):
    editor = uievent.editor

    key = ''
    if isinstance(uievent, KeyboardEvent):
        key = getUnshiftedKey(uievent.key, uievent.modifierstate)
        if key == ',':
            key = 'Comma'
    elif isinstance(uievent, MouseEvent):
        if uievent.eventtype == 'doubleclick':
            key = 'doubleclick'
        else:
            if uievent.mousestate.lmb:
                key = 'LMB'
            elif uievent.mousestate.mmb:
                key = 'MMB'
            elif uievent.mousestate.rmb:
                key = 'RMB'

    context = editor.pwd().childTypeCategory().name().upper()
    if context in __actions and key in __actions[context]:
        action = __actions[context][key]
        if action:
            return None, executeActionString(uievent, action[0], context)

    return None, False



class CustomMouseHandler(base.EventHandler):
    def handleEvent(self, uievent, pending_actions):
        print (uievent.eventtype)
        #if uievent.eventtype == 'keyhit':
            #print ("keyhit invoke")
            #return invokeActionFromKey(uievent, ContextActions)
        #if uievent.eventtype == 'mouseup':
            #print ("MOUSE UP")
            #return None, True

        #return self



def getPopupMenuResult(menu_provider, uievent, context):
    # If we have no menu items, don't pop up the menu. This action will
    # be completed on the next event.
    if len(menu_provider.menuitems) == 0:
        result = menu_provider.result
    else:
        menu = FixKeyPressBugMenu(hou.qt.mainWindow(), uievent, context)
        buildMenu(menu, menu_provider.title, menu_provider.menuitems, context)
        result = menu.exec_(QtCore.QPoint(QtGui.QCursor.pos()))
        if result is not None:
           result = result.data()

    return result



# At least on mac, keyboard shortcuts for menus added to the main window
# simply do not work. This class intercepts keypresses to ensure they
# and handles them directly.
class FixKeyPressBugMenu(QtWidgets.QMenu):
    def __init__(self, parent, uievent, context):
        super(FixKeyPressBugMenu, self).__init__(parent)
        self.uievent = uievent
        self.context = context
        self.triggered.connect(self.actionClicked)


    def actionClicked(self, action):
        executeActionString(self.uievent, action.data(), self.context, bypassKeyboardModifiers=True)
        return True


    def keyPressEvent(self, event):
        for action in self.actions():
            if action.shortcut()[0] == (event.key() | event.modifiers()):
                self.close()
                executeActionString(self.uievent, action.data(), self.context, bypassKeyboardModifiers=True)
                return True

        super(FixKeyPressBugMenu, self).keyPressEvent(event)



def buildMenu(menu, title, menuitems, context):
    menu.setStyleSheet(hou.ui.qtStyleSheet())
    menu.setMinimumWidth(550)

    if title:
        action = menu.addAction(title)
        action.setEnabled(False)
        menu.addSeparator()

    for item in menuitems:
        if item is None:
            menu.addSeparator()
        elif isinstance(item[1], str):
            nodetype = findNodeByType(context, item[-2][3:])

            name = item[0]
            if len(item) == 2 and nodetype:
                name = nodetype.description()

            action = menu.addAction(name)
            action.setText(name)
            action.setData(item[-2])
            action.setShortcut(item[-1])
            action.setEnabled(True)

            icon = None
            if nodetype:
                try:
                    icon = hou.qt.Icon(nodetype.icon())
                except:
                    boxtype = findNodeByType("Sop", "box")
                    icon = hou.qt.Icon(boxtype.icon())
            else:
                boxtype = findNodeByType("Sop", "box")
                icon = hou.qt.Icon(boxtype.icon())

            if icon:
                action.setIcon(icon)
        else:
            submenu = menu.addMenu(item[0])
            buildMenu(submenu, None, item[1])



def getActiveModifierStates(mousestate, modifierstate):
    mods = []
    selectionMods = ""

    if bool(modifierstate.ctrl):
        mods.append('C')
    if bool(modifierstate.alt):
        mods.append('A')
    if bool(modifierstate.shift):
        mods.append('S')

    if getSessionVariable("spaceKeyIsDown") and hou.session.spaceKeyIsDown:
        mods.append('P')

    #if bool(mousestate.lmb):
    #    mods.append('L')
    #if bool(mousestate.rmb):
    #    mods.append('R')
    #if bool(mousestate.mmb):
    #    mods.append('M')

    #if isCapsLockOn():
    #    mods.append('CL')

    if len(hou.selectedNodes()) > 0:
        selectionMods = 'SE'
    else:
        selectionMods = 'NS'

    return " ".join(sorted(mods)), selectionMods



def getModifiersFromActionString(action):
    mods = ""
    selectionMods = ""

    index = action.find('<')
    if index != -1:
        mods = action[index+1:-1]
        mods = sorted(mods.split(" "))

        if "SE" in mods:
            selectionMods = "SE"
            mods.remove("SE")

        if "NS" in mods:
            selectionMods = "NS"
            mods.remove("NS")

        mods = " ".join(mods)

    return mods, selectionMods



def performAction(uievent, context, action):
    success = False
    
    opcode = action[:2]
    opfunc = action[3:]
    index = opfunc.find('<')
    if index != -1:
        opfunc = opfunc[:index]

    if opcode == 'op':
        if doesNodeTypeExist(context, opfunc):
            createNewNode(uievent, opfunc)
            success = True
    elif opcode == 'fn':
        with hou.undos.group("Invoke Custom Function"):
            exec(opfunc)
            success = True
    elif opcode == 'mn':
        menu = MenuProvider()
        try:
            menu.menuitems = eval(opfunc, {}, {'uievent': uievent, 'hou': hou, })
            getPopupMenuResult(menu, uievent, context)
            success = True
        except Exception as e:
            print (e)

    return success



def executeActionString(uievent, action, context, bypassKeyboardModifiers=False, debug=False):
    editor = uievent.editor
    mousestate = uievent.mousestate
    modifierstate = uievent.modifierstate
    pwd = editor.pwd()
    context = pwd.childTypeCategory().name()
    actions = action.split('~')
    success = False

    actionsWithModsSelection = []
    actionsWithModsNoSelection = []
    actionsWithSelection = []
    actionWithoutMods = []
    for a in actions:
        if debug:
            print (a)

        #   First separate actions with explicit modifiers (Ctrl, Alt, Shift, Space, LMB, RMB, MMB)
        currentmods, currentSelectionMods = getModifiersFromActionString(a)
        if currentmods and currentSelectionMods:
            actionsWithModsSelection.append(a)
        elif currentmods and not currentSelectionMods:
            actionsWithModsNoSelection.append(a)
        elif currentSelectionMods:
            actionsWithSelection.append(a)
        else:
            actionWithoutMods.append(a)

    if debug:
        print ("actionsWithModsSelection", actionsWithModsSelection)
        print ("actionsWithModsNoSelection", actionsWithModsNoSelection)
        print ("actionsWithSelection", actionsWithSelection)
        print ("actionWithoutMods", actionWithoutMods)

    activemods, activeSelectionMods = getActiveModifierStates(mousestate, modifierstate)
    if bypassKeyboardModifiers:
        currentmods, currentSelectionMods = getModifiersFromActionString(a)
        activemods = currentmods

    if debug:
        print ("active modes", activemods, activeSelectionMods)

    #   First match the actions with explicit modifiers (Ctrl, Alt, Shift, Space, LMB, RMB, MMB)
    for a in actionsWithModsSelection:
        currentmods, currentSelectionMods = getModifiersFromActionString(a)
        if currentmods == activemods and currentSelectionMods == activeSelectionMods:
            return performAction(uievent, context, a)

    for a in actionsWithModsNoSelection:
        currentmods, currentSelectionMods = getModifiersFromActionString(a)
        if currentmods == activemods:
            return performAction(uievent, context, a)

    if not activemods:
        for a in actionsWithSelection:
            currentmods, currentSelectionMods = getModifiersFromActionString(a)
            if currentSelectionMods == activeSelectionMods:
                return performAction(uievent, context, a)

        for a in actionWithoutMods:
            return performAction(uievent, context, a)

    return success