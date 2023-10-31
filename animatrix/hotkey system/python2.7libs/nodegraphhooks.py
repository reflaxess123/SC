"""

Rule Based Context Sensitive Hotkey System


This is an implementation of a rule based hotkey system that can be 
customized per context in Houdini.

The default hotkeys focus on the most commonly performed operations,
rather than only the most useful operations. For example Point Deform SOP
is very useful but it's not common to create dozens of it in rapid succession,
compared to Attribute Wrangle SOP, or Blast SOP.


The current assignment also mostly takes advantage of mnemonics, and key 
layout for similar operations. For example G for Group Create SOP, H for 
Group Delete SOP, J for Group Promote SOP.


This system has support for creating new nodes in many ways, but it also 
supports executing arbitrary functions implemented by the user.

By default all new nodes that are created are automatically connected to the 
selected nodes based on their order. If the new node has only 1 input connection,
it will be connected to the first selected node.

If it has more than 1 input connections, then the selected nodes will be connected 
starting from left to right of the screen.


The new node will also be dropped centered at the cursor position at the time of 
the hotkey invoke.

This provides a very fluid workflow.


The default hotkey template is provided as a CSV file but it can be edited using 
Microsoft Excel or Google Spreadsheets, which is what I use. The syntax is as follows:


op:nodetypename

Specifies creating a node instances of a specific type. You don't need to specify the context.
But you have to specify the full namespace and version if either or both is used in the node 
type name.


fn:functionname()

Specifies calling a custom Python function in the same context as the executeActionString 
function in houdini_extensions.py file. Therefore you have access to local variables like:

uievent
action
editor = uievent.editor
mousestate = uievent.mousestate
modifierstate = uievent.modifierstate
etc


mn:[('Optional Custom Label', 'op:volumesamplefile', 'S'),
('op:volumesamplevfile', 'V'),
('op:volumegradientfile', 'G')]

Allows you to bring up a popup menu with a list of pre-defined operators or any other custom actions.
The first item is an optional label if omitted will be inferred directly from the operator type if possible.
Else it will use the same text for label.

The third item specifies the hotkey to invoke the respective action once the menu is shown on screen.

If the operator type has a valid icon, this will automatically show up in the menu. Else a standard box
icon is used.


Each item, whether op:, fn or mn: must be separated by ~.

You can list as many action items as you want in a single hotkey within the same context.
Only the one that best matches the modifiers that were active at the time of the hotkey invoke 
will be executed.

Here is the list of available modifiers that you can use to overload your actions:


Input Modifiers:

C: Ctrl
A: Alt
S:  Shift
P:  Space
L:  LMB
R:  RMB
M:  MMB

Selection Modifiers:

SE:  Node Selection > 0
NS:  None Selection == 0

Modifiers must be listed between <> i.e. op:bend<C S> for adding Ctrl+Shift modifier key.

The first 7 is very self-explanatory, the last 2 basically allows you to check if there is a 
node selection or not. So using this, you can for example create File Cache SOP if there 
is a selection, but File SOP if there is no selection, which is actually the default action for 
W in SOP context.


Order Of Precedence

There is an order for execution regardless of the order you used to list your actions.

If an action has both input modifiers and selection modifiers, and the currently active 
modifiers perfectly match it, it will be the one executed before any other ones that could 
have matched it.

If there is no match in the above actions, then the actions with only input modifiers without 
any selection modifiers will be tried. If there is no match, then the execution moves to 
testing actions with only selection modifiers. If no action is found, only then the actions 
without any modifiers will be tried.

"""

import hou, nodegraph, os, sys
from collections import defaultdict
from canvaseventtypes import *
from utility_ui import getSessionVariable, setSessionVariable
import utility_hotkey_system
import utility_generic
import traceback
from PySide2 import QtCore, QtWidgets, QtGui
import nodegraphutils as utils
import nodegraphbase as base
import nodegraphstates as states
import importlib

try:
    from utility_overlay_network_editor import setOverlayNetworkEditorVisible
except:
    pass



this = sys.modules[__name__]
currentdir = os.path.dirname(os.path.realpath(__file__))

def __reload_pythonlibs(showstatus=True):
    if showstatus:
        print ("Reloading hotkey system...")

    importlib.reload(this)
    importlib.reload(utility_hotkey_system)

fs_watcher = QtCore.QFileSystemWatcher()
fs_watcher.addPath(os.path.join(currentdir, "nodegraphhooks.py"))
fs_watcher.addPath(os.path.join(currentdir, "utility_hotkey_system.py"))


fs_watcher.fileChanged.connect(__reload_pythonlibs)



class CustomViewPanHandler(base.EventHandler):
    def __init__(self, start_uievent):
        base.EventHandler.__init__(self, start_uievent)
        self.startbounds = start_uievent.editor.visibleBounds()
        self.olddefaultcursor = start_uievent.editor.defaultCursor()
        self.start_uievent.editor.setDefaultCursor(utils.theCursorPan)

    def handleEvent(self, uievent, pending_actions):
        if uievent.eventtype == 'mousedrag':# and delay >= hou.session.MMBSelectNearestNodeTimeLimit * 0.3:
            dist = uievent.mousestartpos - uievent.mousepos
            dist = uievent.editor.sizeFromScreen(dist)
            bounds = hou.BoundingRect(self.startbounds)
            bounds.translate(dist)
            uievent.editor.setVisibleBounds(bounds)
            return self

        # Select Nearest Node using MMB
        elif uievent.eventtype == 'mouseup':
            self.start_uievent.editor.setDefaultCursor(self.olddefaultcursor)
            if hou.session.UseMMBToSelectNearestNode and self.start_uievent.mousestate.mmb:
                delay = uievent.time - hou.session.mouseDownEventTime
                if delay < hou.session.MMBSelectNearestNodeTimeLimit:
                    # Restore network editor visible bounds back because it's not a panning event
                    uievent.editor.setVisibleBounds(hou.session.networkEditorVisibleBounds)
                    utility_generic.selectNearestNode(uievent)
                    return None

            return None

        # Keep handling events until the mouse button is released.
        return self



class CustomBackgroundMouseHandler(base.EventHandler):
    def handleEvent(self, uievent, pending_actions):
        if uievent.eventtype == 'mousedrag':
            handler = None
            if self.start_uievent.mousestate.lmb:
                handler = states.BoxPickHandler(self.start_uievent, True)
            elif base.isPanEvent(self.start_uievent):
                if hou.session.UseMMBToSelectNearestNode:
                    handler = base.CustomViewPanHandler(self.start_uievent)
                else:
                    handler = base.ViewPanHandler(self.start_uievent)
            elif base.isScaleEvent(self.start_uievent):
                handler = base.ViewScaleHandler(self.start_uievent)
            if handler:
                return handler.handleEvent(uievent, pending_actions)

        elif uievent.eventtype == 'mouseup':
            # Select Nearest Node using MMB
            if hou.session.UseMMBToSelectNearestNode and self.start_uievent.mousestate.mmb:
                delay = uievent.time - hou.session.mouseDownEventTime
                if delay < hou.session.MMBSelectNearestNodeTimeLimit:
                    utility_generic.selectNearestNode(uievent)
                    return None

            if self.start_uievent.mousestate.lmb:
                with hou.undos.group('Clear selection'):
                    hou.clearAllSelected()

            elif self.start_uievent.mousestate.rmb:
                uievent.editor.openTabMenu(key = utils.getDefaultTabMenuKey())

            return None

        # deselect TOP workitems
        elif uievent.eventtype == 'mousedown':
            if self.start_uievent.mousestate.lmb:
                pwd = uievent.editor.pwd()
                if len(pwd.children()) > 0:
                    anode = pwd.children()[0]
                    if isinstance(anode, hou.TopNode):
                        anode.setSelectedWorkItem(-1)

        # Select Nearest Node using LMB
        elif uievent.eventtype == 'doubleclick':
            if hou.session.UseLMBToSelectNearestNode and self.start_uievent.mousestate.lmb:
                utility_generic.selectNearestNode(uievent)
                return None

        # Keep handling events until the mouse is dragged, or the mouse button
        # is released.
        return self



class BoxPickHandler(base.EventHandler):
    def __init__(self, start_uievent, set_cursor = False):
        base.EventHandler.__init__(self, start_uievent)
        # Remember the node-space position of where the box starts.
        self.start_pos = start_uievent.mousestartpos
        self.start_pos = start_uievent.editor.posFromScreen(self.start_pos)
        self.set_cursor = set_cursor
        if set_cursor:
            self.oldcursormap = start_uievent.editor.cursorMap()
            self.olddefaultcursor = start_uievent.editor.defaultCursor()
            start_uievent.editor.setCursorMap({})
            self.setSelectCursor(start_uievent)

    def getItemsInBox(self, items):
        items = list(item[0] for item in items)
        # If we have any non-wires in the box, ignore the wires.
        has_non_wire = any((not isinstance(item, hou.NodeConnection)
                            for item in items))
        if has_non_wire:
            items = list(item for item in items
                         if not isinstance(item, hou.NodeConnection))
            # Select box picked nodes in visual order.
            if utils.isNetworkHorizontal(items[0].parent()):
                items.sort(key = lambda item : -item.position().y())
            else:
                items.sort(key = lambda item : item.position().x())

        return items

    def setSelectCursor(self, uievent):
        if self.set_cursor:
            if isinstance(uievent, MouseEvent) or \
               isinstance(uievent, KeyboardEvent):
                if uievent.modifierstate.ctrl and uievent.modifierstate.shift:
                    cursor = utils.theCursorSelectToggle
                elif uievent.modifierstate.ctrl:
                    cursor = utils.theCursorSelectRemove
                elif uievent.modifierstate.shift:
                    cursor = utils.theCursorSelectAdd
                else:
                    cursor = utils.theCursorSelect
                uievent.editor.setDefaultCursor(cursor)

    def handleBoxPickComplete(self, items, uievent):
        view.modifySelection(uievent, None, items)

    def handleEvent(self, uievent, pending_actions):
        # Set the current selection cursor based on our modifier key states.
        self.setSelectCursor(uievent)

        # Check if the user wants to enter the scroll state.
        if isScrollStateEvent(uievent):
            return ScrollStateHandler(uievent, self)

        if uievent.eventtype == 'mousedrag':
            autoscroll.startAutoScroll(self, uievent, pending_actions)
            # Convert the node space position to a screen-space position for
            # the starting point of the box (which may be outside the visible
            # area of the view).
            pos1 = uievent.editor.posToScreen(self.start_pos)
            pos2 = uievent.editor.screenBounds().closestPoint(uievent.mousepos)
            rect = hou.BoundingRect(pos1, pos2)
            pickbox = hou.NetworkShapeBox(rect,
                            hou.ui.colorFromName('GraphPickFill'), 0.3,
                            True, True)
            pickboxborder = hou.NetworkShapeBox(rect,
                            hou.ui.colorFromName('GraphPickFill'), 0.8,
                            False, True)
            self.editor_updates.setOverlayShapes([pickbox, pickboxborder])
            items = uievent.editor.networkItemsInBox(pos1,pos2,for_select=True)
            items = self.getItemsInBox(items)
            uievent.editor.setPreSelectedItems(items)
            return self

        elif uievent.eventtype == 'mouseup':
            pos1 = uievent.editor.posToScreen(self.start_pos)
            pos2 = uievent.editor.screenBounds().closestPoint(uievent.mousepos)
            items = uievent.editor.networkItemsInBox(pos1,pos2,for_select=True)
            items = self.getItemsInBox(items)
            uievent.editor.setPreSelectedItems(())
            self.handleBoxPickComplete(items, uievent)
            if self.set_cursor:
                uievent.editor.setCursorMap(self.oldcursormap)
                uievent.editor.setDefaultCursor(self.olddefaultcursor)
            return None

        # Keep handling events until the mouse button is released.
        return self



def createEventHandler(uievent, pending_actions):
    if not isinstance(uievent.editor, hou.NetworkEditor):
        return None, False


    if uievent.eventtype == 'mousedown' and uievent.selected.item is None:
        hou.session.networkEditorVisibleBounds = uievent.editor.visibleBounds()
        hou.session.mouseDownEventTime = uievent.time
        return CustomBackgroundMouseHandler(uievent), True


    if isinstance(uievent, KeyboardEvent):
        key = utility_generic.getUnshiftedKey(uievent.key, uievent.modifierstate)
        
        hou.session.spaceKeyIsDown = uievent.editor.isVolatileKeyDown('Space')
        
        if uievent.eventtype == 'keyhit':
            return utility_hotkey_system.invokeActionFromKey(uievent)

    return None, False