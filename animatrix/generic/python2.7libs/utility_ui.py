import hou
import types
import os, sys, platform, subprocess, time
import math
import socket
import ctypes
import shiboken2
from PySide2 import QtCore, QtWidgets, QtGui
from canvaseventtypes import *
from utility_generic import *



debug = False

def getWidgetByName(name):
    if not hasattr(hou.session, "mainQtWindow"):
        hou.session.mainQtWindow = hou.qt.mainWindow()

    hasHandle = hasattr(hou.session, name)
    if not hasHandle or (hasHandle and getattr(hou.session, name) and not shiboken2.isValid(getattr(hou.session, name))):
        allWidgets = QtWidgets.QApplication.allWidgets()
        for w in allWidgets:
            if name in w.windowTitle():
                i = int(shiboken2.getCppPointer(w)[0])
                qw = shiboken2.wrapInstance(i, QtWidgets.QWidget)

                setattr(hou.session, name, qw)
                w.setParent(hou.session.mainQtWindow, QtCore.Qt.Tool)
                break

    if not hasattr(hou.session, name):
        return None

    return getattr(hou.session, name)



def diagonalFromWidthHeight(width, height):
    return math.sqrt(width * width + height * height)



def getViewportPosSize(width=None, height=None):
    viewportWidgets = []

    qtWindow = hou.qt.mainWindow()
    for widget in qtWindow.findChildren(QtWidgets.QWidget, "RE_Window"):
        if widget.windowTitle() == "DM_ViewLayout":
            for l in widget.findChildren(QtWidgets.QVBoxLayout):
                if l.count()==1:
                    w = l.itemAt(0).widget()
                    if w.objectName() == "RE_GLDrawable":
                        i = long(shiboken2.getCppPointer(w)[0])
                        mouse_widget = shiboken2.wrapInstance(i, QtWidgets.QWidget)
                        viewportWidgets.append(mouse_widget)

    if viewportWidgets:
        pos = [w.pos() for w in viewportWidgets]
        size = [w.size() for w in viewportWidgets]

        #if len(viewportWidgets) > 1 and width and height:
            #diagonal = diagonalFromWidthHeight(width, height)
            #diagonals = [diagonalFromWidthHeight(s.width(), s.height()) - diagonal for s in size]

            #pos = [x for _,x in sorted(zip(diagonals, pos))]
            #size = [x for _,x in sorted(zip(diagonals, size))]

        return w.mapToGlobal(pos[-1]), size[-1], True

    return QtCore.QPoint(0, 0), QtCore.QSize(400, 400), False



def getSessionVariable(name):
    val = None
    if hasattr(hou.session, name):
        try:
            val = getattr(hou.session, name)
        except:
            pass
        
    return val



def setSessionVariable(name, value):
    return setattr(hou.session, name, value)



def findFloatingPanelByName(name):
    desktop = hou.ui.curDesktop()
    panels = desktop.floatingPanels()
    for p in panels:
        if p.name() == name:
            return p

    return None



def togglePanel(paneTabName, paneTabType, splitFraction):
    desktop = hou.ui.curDesktop()
    paneTab = desktop.findPaneTab(paneTabName)
    if not paneTab:
        paneTab = desktop.paneTabOfType(paneTabType)

    if paneTab:
        pane = paneTab.pane()
        if pane:
            pane.setIsSplitMaximized(pane.isSplitMinimized())
            pane.setSplitFraction(splitFraction)



def resetViewportPosSize():
    name = "animatrix_viewport"
    viewport = getSessionVariable(name)
    if not viewport:
        desktop = hou.ui.curDesktop()
        viewport = desktop.findPaneTab(name)

    size = viewport.contentSize()
    pos = hou.session.mainQtWindow.pos()

    setSessionVariable("viewportSize", size)
    setSessionVariable("applicationPos", pos)

    if debug:
        print ("pos size reset")



def toggleSceneRenderView():
    desktop = hou.ui.curDesktop()
    viewport = desktop.findPaneTab("animatrix_viewport")
    if not viewport:
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)

    if viewport:
        pane = viewport.pane()
        if pane:
            if pane.isSplitMinimized():
                pane.setIsSplitMaximized(True)

            if not viewport.isCurrentTab():
                viewport.setIsCurrentTab()
            else:
                panename = "animatrix_renderview_redshift"
                if socket.gethostname().startswith("las"):
                    panename = "animatrix_renderview_mantra"

                renderview = desktop.findPaneTab(panename)
                if not renderview:
                    renderview = desktop.paneTabOfType(hou.paneTabType.IPRViewer)

                if renderview:
                    renderview.setIsCurrentTab()



def toggleParameterEditorMaterialPalette():
    desktop = hou.ui.curDesktop()
    parameterEditor = desktop.findPaneTab("animatrix_parameter_editor")
    if not parameterEditor:
        parameterEditor = desktop.paneTabOfType(hou.paneTabType.Parm)

    if parameterEditor:
        pane = parameterEditor.pane()
        if pane:
            if pane.isSplitMinimized():
                pane.setIsSplitMaximized(True)

            if not parameterEditor.isCurrentTab():
                parameterEditor.setIsCurrentTab()
            else:
                materialPalette = desktop.findPaneTab("animatrix_material_palette")
                if not materialPalette:
                    materialPalette = desktop.paneTabOfType(hou.paneTabType.MaterialPalette)

                if materialPalette:
                    materialPalette.setIsCurrentTab()



def resetNetworkEditorZoomLevelFromEditorCenter(editor=None, targetzoom=125):
    if not editor:
        editor = hou.ui.paneTabUnderCursor()
        if editor.type() != hou.paneTabType.NetworkEditor:
            desktop = hou.ui.curDesktop()
            editor = desktop.paneTabOfType(hou.paneTabType.NetworkEditor)

    if editor:
        screenbounds = editor.screenBounds()
        # Figure out how much we need to scale the current bounds to get to
        # a zoom level of 100 pixels per network editor unit.
        bounds = editor.visibleBounds()
        currentzoom = editor.screenBounds().size().x() / bounds.size().x()
        scale = currentzoom / targetzoom

        zoomcenter = editor.posFromScreen(screenbounds.center())
        bounds.translate(-zoomcenter)
        bounds.scale((scale, scale))
        bounds.translate(zoomcenter)

        editor.setVisibleBounds(bounds)

        bounds = editor.visibleBounds()
        currentzoom = editor.screenBounds().size().x() / bounds.size().x()



def resetNetworkEditorZoomLevelFromMousePos(editor=None, targetzoom=125):
    if not editor:
        editor = hou.ui.paneTabUnderCursor()
        if editor.type() != hou.paneTabType.NetworkEditor:
            desktop = hou.ui.curDesktop()
            editor = desktop.paneTabOfType(hou.paneTabType.NetworkEditor)

    if editor:
        screenbounds = editor.screenBounds()
        # Figure out how much we need to scale the current bounds to get to
        # a zoom level of 100 pixels per network editor unit.
        bounds = editor.visibleBounds()
        currentzoom = editor.screenBounds().size().x() / bounds.size().x()
        scale = currentzoom / targetzoom

        zoomcenter = editor.cursorPosition()
        bounds.translate(-zoomcenter)
        bounds.scale((scale, scale))
        bounds.translate(zoomcenter)

        editor.setVisibleBounds(bounds)

        bounds = editor.visibleBounds()
        currentzoom = editor.screenBounds().size().x() / bounds.size().x()



def resetNetworkEditorZoomLevel(uievent, targetzoom=125):
    editor = uievent.editor
    screenbounds = editor.screenBounds()
    # Figure out how much we need to scale the current bounds to get to
    # a zoom level of 100 pixels per network editor unit.
    bounds = editor.visibleBounds()
    currentzoom = editor.screenBounds().size().x() / bounds.size().x()
    scale = currentzoom / targetzoom

    zoomcenter = editor.posFromScreen(uievent.mousepos)
    bounds.translate(-zoomcenter)
    bounds.scale((scale, scale))
    bounds.translate(zoomcenter)
    
    editor.setVisibleBounds(bounds)



def toggleNetworkEditor():
    desktop = hou.ui.curDesktop()
    networkEditor = desktop.findPaneTab("animatrix_network_editor")
    if not networkEditor:
        networkEditor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
    if networkEditor:
        pane = networkEditor.pane()
        isMinimized = pane.isSplitMinimized()
        
        pane.setIsSplitMaximized(isMinimized)
        pane.setSplitFraction(0.5)



class VerticalLineDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        super(VerticalLineDelegate, self).paint(painter, option, index)
        line = QtCore.QLine(option.rect.topRight(), option.rect.bottomRight())
        painter.save()
        color = QtGui.QColor(50, 50, 50)
        painter.setPen(QtGui.QPen(color, 1))
        painter.drawLine(line)
        painter.restore()



class FileTableWidget(QtWidgets.QTableWidget):
    allFiles = []
    
    def __init__(self, parent=None):
        super(FileTableWidget, self).__init__(parent)
        self.installEventFilter(self)

        self.setColumnCount(2)
        self.setMinimumHeight(5)
        self.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows);
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        delegate = VerticalLineDelegate(self)
        self.setItemDelegate(delegate)
        
        hh = self.horizontalHeader()
        hh.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        hh.hide()
        
        vh = self.verticalHeader()
        vh.setDefaultSectionSize(hou.ui.scaledSize(10))
        vh.setMinimumSectionSize(hou.ui.scaledSize(20))
        vh.setMaximumWidth(hou.ui.scaledSize(28))
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)

        files = getRecentHipFiles()
        filedates = [time.ctime(os.path.getmtime(file)) for file in files]

        for i in range(1, 16):
            if i > len(files):
                files.append("")
                filedates.append("")
                
        self.allFiles = files
        for index, file in enumerate(files):
            self.insertRow(index)
            self.setRowHeight(index, hou.ui.scaledSize(10))

            filename = QtWidgets.QTableWidgetItem(file)
            filename.setFlags(filename.flags() & ~QtCore.Qt.ItemIsEditable)
            date = QtWidgets.QTableWidgetItem(filedates[index])
            date.setFlags(date.flags() & ~QtCore.Qt.ItemIsEditable)
            self.setItem(index, 0, filename)
            self.setItem(index, 1, date)
            
            

    def getSelectedFile(self):
        row = self.currentRow()
        return self.allFiles[row]
        
        

    def askLoadingFile(self, file):
        return hou.ui.displayMessage("Do you want to load?\n" + file, buttons=("Yes", "No")) == 0
        

        
    def loadSelectedFile(self):
        file = self.getSelectedFile()
        confirmed = self.askLoadingFile(file)
        if confirmed:
            hou.hipFile.load(file)
            self.parent().close()
        

        
    def loadFileByIndex(self, index):
        file = self.getSelectedFile()
        confirmed = self.askLoadingFile(file)
        if confirmed:
            hou.hipFile.load(file)        
            self.parent().close()
            
            

    def keyPressEvent(self, event):
         key = event.key()
         
         index = -1
         if key == QtCore.Qt.Key_0:
            index = 9
         elif key == QtCore.Qt.Key_1:
            index = 0
         elif key == QtCore.Qt.Key_2:
            index = 1
         elif key == QtCore.Qt.Key_3:
            index = 2
         elif key == QtCore.Qt.Key_4:
            index = 3
         elif key == QtCore.Qt.Key_5:
            index = 4
         elif key == QtCore.Qt.Key_6:
            index = 5
         elif key == QtCore.Qt.Key_7:
            index = 6
         elif key == QtCore.Qt.Key_8:
            index = 7
         elif key == QtCore.Qt.Key_9:
            index = 8
            
         if index != -1:
            self.selectRow(index)
            self.loadFileByIndex(index)
         else:
             if key == QtCore.Qt.Key_Enter:
                 self.loadSelectedFile()
             elif key == QtCore.Qt.Key_Return:
                 self.loadSelectedFile()
             elif key == QtCore.Qt.Key_Escape:
                 self.parent().close()
             else:
                 super(FileTableWidget, self).keyPressEvent(event)
                 
             

    def mousePressEvent(self, event):
        handled = False
        if event.type() == QtCore.QEvent.MouseButtonPress:
            if event.button() == QtCore.Qt.RightButton:
                file = self.getSelectedFile()
                if file:
                    openfile(file)
                    handled = True
                                
        if not handled:
            super(FileTableWidget, self).mousePressEvent(event)
                

            
    def mouseDoubleClickEvent(self, event):
        widget = self.childAt(event.pos())
        if widget is not None and widget.objectName():
            self.loadSelectedFile()
            
            

class FileBrowser(QtWidgets.QWidget):
    def __init__(self):
        super(FileBrowser, self).__init__()
        self.setWindowTitle("Recently Opened Files")
        self.setParent(hou.qt.mainWindow(), QtCore.Qt.Tool)
        #self.setParent(hou.qt.mainWindow(), QtCore.Qt.CustomizeWindowHint)
        
        layout = QtWidgets.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(FileTableWidget())
        self.setLayout(layout)
        
        self.show()
        
        

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
        #elif event.key() == QtCore.Qt.Key_Enter:
        #    self.loadSelectedFile()
            
        event.accept()



def showRecentlyOpenedFiles():
    window = FileBrowser()

    size = window.size()
    width = size.width()
    height = size.height()
    window.setFixedSize(width, height)

    desktop = QtWidgets.QDesktopWidget()
    sw = desktop.screen().width()
    sh = desktop.screen().height()

    window.move((sw - width)/2, (sh - height)/2)



def togglePointNumbers():
    import toolutils
    pt = None

    try:
        # cycle
        pts = hou.session.pt[:]
        pts = pts[1:]+pts[:1]
        pt = pts[0]
        hou.session.pt = pts
    except:
        # set up default vars
        hou.session.pt = ['on', 'off']
        pt = hou.session.pt[0]

    pts = { 'on':'on', 'off':'off'}
    hou.hscript("viewdispset -c %s on display *" % pts[pt].lower())



def togglePointMarkers():
    import toolutils
    pt = None

    try:
        # cycle
        pts = hou.session.ptm[:]
        pts = pts[1:]+pts[:1]
        pt = pts[0]
        hou.session.ptm = pts
    except:
        # set up default vars
        hou.session.ptm = ['on', 'off']
        pt = hou.session.ptm[0]

    pts = { 'on':'on', 'off':'off'}
    hou.hscript("viewdispset -m %s on display *" % pts[pt].lower())



def togglePointNormals():
    import toolutils
    pt = None

    try:
        # cycle
        pts = hou.session.ptn[:]
        pts = pts[1:]+pts[:1]
        pt = pts[0]
        hou.session.ptn = pts
    except:
        # set up default vars
        hou.session.ptn = ['on', 'off']
        pt = hou.session.ptn[0]

    pts = { 'on':'on', 'off':'off'}
    hou.hscript("viewdispset -n %s on display *" % pts[pt].lower())



def togglePrimitiveNormals():
    import toolutils
    pt = None

    try:
        # cycle
        pts = hou.session.prn[:]
        pts = pts[1:]+pts[:1]
        pt = pts[0]
        hou.session.prn = pts
    except:
        # set up default vars
        hou.session.prn = ['on', 'off']
        pt = hou.session.prn[0]

    pts = { 'on':'on', 'off':'off'}
    hou.hscript("viewdispset -N %s on display *" % pts[pt].lower())



def toggleHiddenLineShaded():
    hou.hscript("viewdisplay -M all hidden_invis VFX.FloatingPanel.world")



def createNotesFromComments():
    import textwrap

    with hou.undos.group("Create Notes From Comments"):
        selectedNodes = hou.selectedNodes()
        networkEditor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
        currentPath = networkEditor.pwd().path()

        for node in selectedNodes:
            if len ( node.comment ( ) ) != 0:

                lines = node.comment ( ).split ( "\n\n" )
                numLines = 0
                for line in lines:
                    numLines += len ( textwrap.wrap ( line, 50 ) )
                numLines += node.comment ( ).count ( "\n\n" )

                height = 0.22 * numLines

                comment = hou.node ( currentPath ).createStickyNote ( node.name ( ) + "_" )
                comment.setText ( node.comment ( ) )
                comment.setColor ( hou.Color ( ) )
                comment.setSize ( hou.Vector2 ( 0.5, 0.5 ) )
                comment.setPosition ( node.position ( ) + hou.Vector2 ( 5, -0.5 ) )
                comment.setSize ( hou.Vector2 ( 5, 0.4 + height ) )
                comment.move ( hou.Vector2 ( 0, -height / 1 ) )



def createVolumeLights():
    with hou.undos.group("Create Volume Lights"):
        editor = kwargs['pane']
        currentPath = editor.pwd().path()
        pos = editor.cursorPosition ( ) 

        newNode = hou.node ( currentPath ).createNode ( "hlight" )
        size = newNode.size ( )
        pos [ 0 ] -= size [ 0 ] / 2
        pos [ 1 ] -= size [ 1 ] / 2
        newNode.setPosition ( pos )

        hou.hscript("oppresetload " + newNode.path() + " 'Volume Light 1'")

        newNode = hou.node ( currentPath ).createNode ( "hlight" )
        size = newNode.size ( )
        pos [ 0 ] -= size [ 0 ] / 2
        pos [ 1 ] -= size [ 1 ] / 2
        newNode.setPosition ( pos - size )

        hou.hscript("oppresetload " + newNode.path() + " 'Volume Light 2'")



def toggleUpdateMode():
    with hou.undos.disabler():
        mode = hou.updateModeSetting()
        if mode != hou.updateMode.AutoUpdate:
            hou.setUpdateMode(hou.updateMode.AutoUpdate)
        else:
            hou.setUpdateMode(hou.updateMode.Manual)



def currentViewportFrameSelected():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            viewport.curViewport().frameSelected()
    


def currentViewportFrameAll():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            viewport.curViewport().frameAll()



def currentViewportSwitchToPerspective():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            view.changeType(hou.geometryViewportType.Perspective)



def currentViewportSwitchToTop():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            if view.type() == hou.geometryViewportType.Top:
                view.changeType(hou.geometryViewportType.Bottom)
            else:
                view.changeType(hou.geometryViewportType.Top)



def currentViewportSwitchToFront():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            if view.type() == hou.geometryViewportType.Front:
                view.changeType(hou.geometryViewportType.Back)
            else:
                view.changeType(hou.geometryViewportType.Front)



def currentViewportSwitchToRight():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            if view.type() == hou.geometryViewportType.Right:
                view.changeType(hou.geometryViewportType.Left)
            else:
                view.changeType(hou.geometryViewportType.Right)



def currentViewportSwitchToUV():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            view.changeType(hou.geometryViewportType.UV)



def currentViewportSetToWireframe():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.WireGhost)



def currentViewportSetToHiddenLineInvisible():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.HiddenLineInvisible)



def currentViewportSetToFlatShaded():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.Flat)



def currentViewportSetToFlatWireShaded():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.FlatWire)



def currentViewportSetToSmoothShaded():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.Smooth)



def currentViewportSetToSmoothWireShaded():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            displaySet.setShadedMode(hou.glShadingType.SmoothWire)



def currentViewportToggleWireframe():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            shadingMode = displaySet.shadedMode()

            if shadingMode != hou.glShadingType.WireGhost:
                setSessionVariable("lastViewportShadingMode", shadingMode)
                displaySet.setShadedMode(hou.glShadingType.WireGhost)
            else:
                displaySet.setShadedMode(getSessionVariable("lastViewportShadingMode"))



def currentViewportToggleHiddenLineInvisible():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            view = viewport.curViewport()
            displaySet = view.settings().displaySet(hou.displaySetType.DisplayModel)
            shadingMode = displaySet.shadedMode()

            if shadingMode != hou.glShadingType.HiddenLineInvisible:
                setSessionVariable("lastViewportShadingMode", shadingMode)
                displaySet.setShadedMode(hou.glShadingType.HiddenLineInvisible)
            else:
                displaySet.setShadedMode(getSessionVariable("lastViewportShadingMode"))



def currentViewportEnterViewState():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            viewport.enterViewState()



def currentViewportToggleViewState():
    with hou.undos.disabler():
        desktop = hou.ui.curDesktop()
        viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
        if viewport.isCurrentTab():
            viewstates = ["sopview", "objview", "chopview", "dopview", "imgview", "shopview", "topview", "ropview", "matview"]
            
            if viewport.currentState() in viewstates:
                viewport.enterCurrentNodeState()
            else:
                viewport.enterViewState()



def clearStatusBarMessage():
    with hou.undos.disabler():
        hou.ui.setStatusMessage("")



def diveInsideNearestNode():
    with hou.undos.group("Dive Inside Nearest Node"):
        currentPaneTab = hou.ui.paneTabUnderCursor()
        if currentPaneTab:
            nearestNode = findNearestNode(currentPaneTab)
            if nearestNode:
                hdadef = nearestNode.type().definition()
                if hdadef:
                    sections = hdadef.sections()
                    if "DiveTarget" in sections:
                        diveTarget = sections["DiveTarget"].contents()
                        nearestNode = nearestNode.node(diveTarget)

                currentPaneTab.setPwd(nearestNode)



def toggleNetworkEditorGrid():
    networkEditor = hou.ui.paneTabUnderCursor()
    if networkEditor.type() == hou.paneTabType.NetworkEditor:
        networkEditor.setPref("gridmode", "2" if networkEditor.getPref("gridmode") != "2" else "0")



def jumpUpOneLevel():
    with hou.undos.group("Jump Up"):
        currentPaneTab = hou.ui.paneTabUnderCursor()
        if currentPaneTab:
            pwd = currentPaneTab.pwd()
            parentNode = pwd
            if pwd.isInsideLockedHDA():
                parent = pwd
                hdadef = None
                while hdadef is None and parent:
                    hdadef = parent.type().definition()
                    if hdadef is None:
                        parent = parent.parent()

                if hdadef:
                    sections = hdadef.sections()
                    if "DiveTarget" in sections:
                        diveTarget = sections["DiveTarget"].contents()
                        parentNode = parent

            parentNode = parentNode.parent()
            if parentNode:
                currentPaneTab.setPwd(parentNode)



def fullscreenSession():
    window = hou.qt.mainWindow()
    #hou.ui.setHideAllMinimizedStowbars(not window.isFullScreen())
    # HOUDINI BUG
    if window.isFullScreen():
    #window.showMaximized()
    #print ("maximized: ", window.isMaximized())
    #if window.isMaximized():
        window.showNormal()
        #print ("normal")
        #window.showMaximized()
    else:
        #window.showNormal()
        #print ("full screen")
        window.showFullScreen()

    hou.ui.setHideAllMinimizedStowbars(window.isFullScreen())



def syncAdvancedCodeEditorToSelection(selectedNode):
    if hasattr(hou.session, "animatrixcodeeditor"):
            hou.session.animatrixcodeeditor.syncSelection(selectedNode)



def syncHDAManagerToSelectedNode(selectedNode):
    panetabs = hou.ui.paneTabs()
    for panetab in panetabs:
        if panetab.name() == "animatrix_hdamanager" and panetab.isCurrentTab():
            panetab.activeInterfaceRootWidget().syncSelectedNode(selectedNode)



def refreshHDAManager():
    panetabs = hou.ui.paneTabs()
    for panetab in panetabs:
        if panetab.name() == "animatrix_hdamanager" and panetab.isCurrentTab():
            panetab.activeInterfaceRootWidget().refresh()



def hideObsoleteOperators ( ):
    hou.hscript("ophide Object auto_rig_biped_arm")
    hou.hscript("ophide Object auto_rig_biped_hand_4f_2s")
    hou.hscript("ophide Object auto_rig_biped_hand_4f_3s")
    hou.hscript("ophide Object auto_rig_biped_hand_5f_3s")
    hou.hscript("ophide Object auto_rig_biped_head_and_neck")
    hou.hscript("ophide Object auto_rig_biped_leg")
    hou.hscript("ophide Object auto_rig_biped_spine_3pc")
    hou.hscript("ophide Object auto_rig_biped_spine_5pc")
    hou.hscript("ophide Object auto_rig_character_placer")
    hou.hscript("ophide Object auto_rig_quadruped_back_leg")
    hou.hscript("ophide Object auto_rig_quadruped_front_leg")
    hou.hscript("ophide Object auto_rig_quadruped_head_and_neck")
    hou.hscript("ophide Object auto_rig_quadruped_ik_spine")
    hou.hscript("ophide Object auto_rig_quadruped_tail")
    hou.hscript("ophide Object auto_rig_quadruped_toes_4f")
    hou.hscript("ophide Object auto_rig_quadruped_toes_5f")
    hou.hscript("ophide Object biped_auto_rig")
    hou.hscript("ophide Object fourpointmuscle")
    hou.hscript("ophide Object muscle")
    hou.hscript("ophide Object quadruped_auto_rig_4f")
    hou.hscript("ophide Object quadruped_auto_rig_5f")
    hou.hscript("ophide Object toon_character")
    hou.hscript("ophide Object threepointmuscle")
    hou.hscript("ophide Object twopointmuscle")
    hou.hscript("ophide Shop rsl_vopvolume")
    hou.hscript("ophide Shop rsl_vopsurfacetype")
    hou.hscript("ophide Shop rsl_vopstruct")
    hou.hscript("ophide Shop rsl_vopdisplacetype")
    hou.hscript("ophide Shop rsl_vopsurface")
    hou.hscript("ophide Shop rsl_voplight")
    hou.hscript("ophide Shop rsl_voplighttype")
    hou.hscript("ophide Shop rsl_vopshaderclass")
    hou.hscript("ophide Shop rsl_vopdisplace")
    hou.hscript("ophide Shop rsl_vopmaterial")
    hou.hscript("ophide Shop rsl_vopvolumetype")
    hou.hscript("ophide Shop rsl_vopimager")
    hou.hscript("ophide Object pxrspherelight")
    hou.hscript("ophide Object pxrgobolightfilter")
    hou.hscript("ophide Object pxraovlight")
    hou.hscript("ophide Object pxrintmultlightfilter")
    hou.hscript("ophide Object pxrstdarealight")
    hou.hscript("ophide Object pxrcookielightfilter")
    hou.hscript("ophide Object pxrportallight")
    hou.hscript("ophide Object pxrdisklight")
    hou.hscript("ophide Object pxrblockerlightfilter")
    hou.hscript("ophide Object pxrdistantlight")
    hou.hscript("ophide Object pxrrodlightfilter")
    hou.hscript("ophide Object pxrenvdaylight")
    hou.hscript("ophide Object pxrdomelight")
    hou.hscript("ophide Object pxrrectlight")
    hou.hscript("ophide Object pxrstdenvmaplight")
    hou.hscript("ophide Object pxrramplightfilter")
    hou.hscript("ophide Object pxrstdenvdaylight")
    hou.hscript("ophide Object pxrbarnlightfilter")
    hou.hscript("ophide Vop rsl_surfacecolor")
    hou.hscript("ophide Vop rsl_calculatenormal")
    hou.hscript("ophide Vop pxrmarschnerhair::2.0")
    hou.hscript("ophide Vop pxrlmmixer")
    hou.hscript("ophide Vop pxrfilmictonemappersamplefilter")
    hou.hscript("ophide Vop pxrintmultlightfilter")
    hou.hscript("ophide Vop pxrcolorcorrect")
    hou.hscript("ophide Vop pxrvisualizer")
    hou.hscript("ophide Vop pxrcookielightfilter")
    hou.hscript("ophide Vop pxrexposure")
    hou.hscript("ophide Vop rsl_environment")
    hou.hscript("ophide Vop pxrdisklight")
    hou.hscript("ophide Vop pxrdisplace")
    hou.hscript("ophide Vop pxrcopyaovdisplayfilter")
    hou.hscript("ophide Vop pxrmanifold3d")
    hou.hscript("ophide Vop pxrocclusion")
    hou.hscript("ophide Vop pxrenvdaylight")
    hou.hscript("ophide Vop pxrlmdiffuse")
    hou.hscript("ophide Vop pxrdisplayfiltercombiner")
    hou.hscript("ophide Vop pxrseexpr")
    hou.hscript("ophide Vop pxrthreshold")
    hou.hscript("ophide Vop pxrvolume")
    hou.hscript("ophide Vop pxrprojectionstack")
    hou.hscript("ophide Vop rsl_import")
    hou.hscript("ophide Vop rsl_log")
    hou.hscript("ophide Vop pxrvcm")
    hou.hscript("ophide Vop pxrgradedisplayfilter")
    hou.hscript("ophide Vop pxrstdarealight")
    hou.hscript("ophide Vop rsl_transform")
    hou.hscript("ophide Vop pxrtofloat")
    hou.hscript("ophide Vop pxrconstant")
    hou.hscript("ophide Vop pxrblackbody")
    hou.hscript("ophide Vop pxrmultitexture")
    hou.hscript("ophide Vop pxrlayer")
    hou.hscript("ophide Vop rsl_illuminate")
    hou.hscript("ophide Vop pxrtee")
    hou.hscript("ophide Vop pxrbakepointcloud")
    hou.hscript("ophide Vop pxrprimvar")
    hou.hscript("ophide Vop pxrfractalize")
    hou.hscript("ophide Vop pxrdisplacement")
    hou.hscript("ophide Vop rsl_indirectdiffuse")
    hou.hscript("ophide Vop pxrsurface")
    hou.hscript("ophide Vop pxrbarnlightfilter")
    hou.hscript("ophide Vop pxrworley")
    hou.hscript("ophide Vop pxrprojectionlayer")
    hou.hscript("ophide Vop pxrdot")
    hou.hscript("ophide Vop pxrdirectlighting")
    hou.hscript("ophide Vop pxraovlight")
    hou.hscript("ophide Vop pxrhalfbuffererrorfilter")
    hou.hscript("ophide Vop pxrgradesamplefilter")
    hou.hscript("ophide Vop pxrtangentfield")
    hou.hscript("ophide Vop rsl_illuminance")
    hou.hscript("ophide Vop pxrgobo")
    hou.hscript("ophide Vop pxrglass")
    hou.hscript("ophide Vop pxrmarschnerhair")
    hou.hscript("ophide Vop pxrgeometricaovs")
    hou.hscript("ophide Vop rsl_shadow")
    hou.hscript("ophide Vop rsl_step")
    hou.hscript("ophide Vop pxrmatteid")
    hou.hscript("ophide Vop pxrstdenvmaplight")
    hou.hscript("ophide Vop pxrhsl")
    hou.hscript("ophide Vop pxrrectlight")
    hou.hscript("ophide Vop pxrlmlayer")
    hou.hscript("ophide Vop pxrmeshlight")
    hou.hscript("ophide Vop pxrinvert")
    hou.hscript("ophide Vop rsl_rayinfo")
    hou.hscript("ophide Vop rsl_depth")
    hou.hscript("ophide Vop pxrrandomtexturemanifold")
    hou.hscript("ophide Vop pxrblocker")
    hou.hscript("ophide Vop pxrmanifold3dn")
    hou.hscript("ophide Vop pxrbackgroundsamplefilter")
    hou.hscript("ophide Vop pxrlmplastic")
    hou.hscript("ophide Vop pxrtexture")
    hou.hscript("ophide Vop rsl_textureinfo")
    hou.hscript("ophide Vop pxradjustnormal")
    hou.hscript("ophide Vop pxrlmmetal")
    hou.hscript("ophide Vop rsl_deriv")
    hou.hscript("ophide Vop pxrlayermixer")
    hou.hscript("ophide Vop pxrramp")
    hou.hscript("ophide Vop pxrspherelight")
    hou.hscript("ophide Vop pxrcombinerlightfilter")
    hou.hscript("ophide Vop pxrvoronoise")
    hou.hscript("ophide Vop pxrblack")
    hou.hscript("ophide Vop pxrlayeredtexture")
    hou.hscript("ophide Vop pxrvalidatebxdf")
    hou.hscript("ophide Vop pxrportallight")
    hou.hscript("ophide Vop pxrnormalmap")
    hou.hscript("ophide Vop pxrskin")
    hou.hscript("ophide Vop pxrblockerlightfilter")
    hou.hscript("ophide Vop pxrrodlightfilter")
    hou.hscript("ophide Vop pxrarealight")
    hou.hscript("ophide Vop pxrblend")
    hou.hscript("ophide Vop pxrcopyaovsamplefilter")
    hou.hscript("ophide Vop pxrdomelight")
    hou.hscript("ophide Vop pxrbaketexture")
    hou.hscript("ophide Vop pxrpathtracer")
    hou.hscript("ophide Vop pxrtofloat3")
    hou.hscript("ophide Vop pxrshadedside")
    hou.hscript("ophide Vop rsl_texture")
    hou.hscript("ophide Vop pxrosl")
    hou.hscript("ophide Vop pxrupbp")
    hou.hscript("ophide Vop pxrramplightfilter")
    hou.hscript("ophide Vop pxrwhitepointdisplayfilter")
    hou.hscript("ophide Vop pxrlightprobe")
    hou.hscript("ophide Vop rsl_ctransform")
    hou.hscript("ophide Vop rsl_bias")
    hou.hscript("ophide Vop pxrimageplanefilter")
    hou.hscript("ophide Vop pxrgrid")
    hou.hscript("ophide Vop pxrlightemission")
    hou.hscript("ophide Vop pxrcamera")
    hou.hscript("ophide Vop pxrremap")
    hou.hscript("ophide Vop rsl_oglass")
    hou.hscript("ophide Vop pxrshadowfilter")
    hou.hscript("ophide Vop pxrwhitepointsamplefilter")
    hou.hscript("ophide Vop pxrstdenvdaylight")
    hou.hscript("ophide Vop pxrimagedisplayfilter")
    hou.hscript("ophide Vop pxrfractal")
    hou.hscript("ophide Vop pxrattribute")
    hou.hscript("ophide Vop pxrgobolightfilter")
    hou.hscript("ophide Vop pxrlayeredblend")
    hou.hscript("ophide Vop pxrvariable")
    hou.hscript("ophide Vop pxrsamplefiltercombiner")
    hou.hscript("ophide Vop pxrmanifold2d")
    hou.hscript("ophide Vop pxrptexture")
    hou.hscript("ophide Vop pxrshadowdisplayfilter")
    hou.hscript("ophide Vop rsl_gain")
    hou.hscript("ophide Vop pxrfacingratio")
    hou.hscript("ophide Vop rsl_occlusion")
    hou.hscript("ophide Vop pxrmix")
    hou.hscript("ophide Vop pxrdispvectorlayer")
    hou.hscript("ophide Vop pxrdisptransform")
    hou.hscript("ophide Vop pxrdirt")
    hou.hscript("ophide Vop pxrclamp")
    hou.hscript("ophide Vop pxrroundcube::2.0")
    hou.hscript("ophide Vop pxrfilmictonemapperdisplayfilter")
    hou.hscript("ophide Vop pxrdiffuse")
    hou.hscript("ophide Vop pxrroundcube")
    hou.hscript("ophide Vop pxrvary")
    hou.hscript("ophide Vop pxrflakes")
    hou.hscript("ophide Vop pxrthinfilm")
    hou.hscript("ophide Vop rsl_random")
    hou.hscript("ophide Vop pxrbumpmanifold2d")
    hou.hscript("ophide Vop pxrlmglass")
    hou.hscript("ophide Vop pxrdispscalarlayer")
    hou.hscript("ophide Vop pxrchecker")
    hou.hscript("ophide Vop pxrtilemanifold")
    hou.hscript("ophide Vop pxrdebugshadingcontext")
    hou.hscript("ophide Vop rsl_renderstate")
    hou.hscript("ophide Vop pxrhaircolor")
    hou.hscript("ophide Vop pxrbump")
    hou.hscript("ophide Vop pxrlmsubsurface")
    hou.hscript("ophide Vop pxrdistantlight")
    hou.hscript("ophide Vop pxrrollingshutter")
    hou.hscript("ophide Vop pxrdisney")
    hou.hscript("ophide Vop pxrprojector")
    hou.hscript("ophide Vop pxrgamma")
    hou.hscript("ophide Vop pxrcross")
    hou.hscript("ophide Vop pxrbackgrounddisplayfilter")
    hou.hscript("ophide Vop pxrdefaultintegrator")
    hou.hscript("ophide Vop rsl_dudv")
    hou.hscript("ophide VopNet rsl_surface")
    hou.hscript("ophide VopNet rsl_light")
    hou.hscript("ophide VopNet rsl_displace")
    hou.hscript("ophide VopNet rsl_volume")
    hou.hscript("ophide VopNet rsl_imager")
    hou.hscript("ophide Sop bakeode")
    hou.hscript("ophide Sop duplicate")
    hou.hscript("ophide Sop starburst")
    hou.hscript("ophide Sop pointmap")
    hou.hscript("ophide Sop vex")