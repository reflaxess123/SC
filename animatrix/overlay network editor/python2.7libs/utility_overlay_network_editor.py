import hou
import hdefereval
import types
import os
import time
import threading
import ctypes
import importlib
import shiboken2
from PySide2 import QtCore, QtWidgets, QtGui
from utility_ui import *



currentdir = os.path.dirname(os.path.realpath('__file__'))

def __reload_pythonlibs(showstatus=True):
    if showstatus:
        print ("Reloading overlay network editor...")
    importlib.reload(utility_overlay_network_editor)
    importlib.reload(DigitalAsset)

fs_watcher = QtCore.QFileSystemWatcher()
fs_watcher.addPath(os.path.join(currentdir, "utility_overlay_network_editor.py"))
fs_watcher.addPath(os.path.join(currentdir, "digitalasset.py"))


fs_watcher.fileChanged.connect(__reload_pythonlibs)



class ViewportOutlineWidget(QtWidgets.QWidget):

    thickness = 0
    def __init__(self, thicknessValue=2):
        QtWidgets.QWidget.__init__(self, hou.qt.mainWindow(), QtGui.Qt.WindowStaysOnTopHint)
        

        self.thickness = thicknessValue
        self.setParent(hou.qt.floatingPanelWindow(None), QtGui.Qt.Window)
        self.update()

        p = self.palette()
        p.setColor(QtGui.QPalette.Window, QtGui.Qt.red)
        self.setPalette(p)


    def update(self):
        viewport = getSessionVariable("viewportWidget")
        s = viewport.size()
        p = viewport.mapToGlobal(QtCore.QPoint(0, 0))
        w = s.width()
        h = s.height()

        self.setGeometry(p.x(), p.y(), w, h)

        all = QtGui.QRegion(0, 0, w, h)
        inside = QtGui.QRegion(self.thickness, self.thickness, w - 2 * self.thickness, h - 2 * self.thickness)
        self.setMask(all.subtracted(inside))



def updateUIElements():
    # Clear specific status bar messages with a delay
    if hou.session.lastStatusMessageTimeInMs == -1:
        statusMessage = hou.ui.statusMessage()[0].strip()
        if statusMessage.startswith("Hold down Ctrl to snap to rounded values") or \
        statusMessage.startswith("Hold down Shift to allow moving between ladders") or \
        statusMessage.startswith("Not enough sources specified"):
            hou.ui.setStatusMessage("")

        if statusMessage.endswith(" copied") or statusMessage.endswith(" pasted"):
            hou.session.lastStatusMessageTimeInMs = int(round(time.time() * 1000))
    else:
        currentTimeInMs = int(round(time.time() * 1000))
        if currentTimeInMs > hou.session.lastStatusMessageTimeInMs + hou.session.lastStatusMessageTimeTimeout:
            hou.ui.setStatusMessage("")
            hou.session.lastStatusMessageTimeInMs = -1



    # Draw red outline if viewport is camera-locked
    if hasattr(hou.session, "viewportOutlineWidget"):
        sceneviewer = hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        currentViewport = sceneviewer.curViewport()
        if sceneviewer.isCurrentTab() and currentViewport.isCameraLockedToView() and currentViewport.camera():
            if not hou.session.viewportOutlineWidget.isVisible():
                hou.session.viewportOutlineWidget.show()
            else:
                hou.session.viewportOutlineWidget.update()
        else:
            if hou.session.viewportOutlineWidget.isVisible():
                hou.session.viewportOutlineWidget.hide()



    moveResizeOverlayNetworkEditor()



def createNewFloatingNetworkEditor():
    panel = hou.ui.curDesktop().createFloatingPanel(hou.paneTabType.NetworkEditor)
    panel.setName("animatrix_overlay_network_editor")
    panel.setSize((100,100))
    panel.attachToDesktop(True)

    editor = panel.paneTabs()[0]
    editor.setPin(False)
    editor.setShowNetworkControls(False)
    editor.setPref('gridxstep', '1')
    editor.setPref('gridystep', '1')
    editor.setPref('showmenu', '0')
    editor.pane().setShowPaneTabs(False)



def moveResizeOverlayNetworkEditor():
    if getSessionVariable("overlayNetworkEditorCallbackSuspended") == False:
        viewport = getSessionVariable("viewportWidget")

        if viewport.isVisible() and hasattr(hou.session, "animatrix_overlay_network_editor"):
            size = viewport.size()
            pos = viewport.mapToGlobal(QtCore.QPoint(0, 0))

            if getSessionVariable("useVolatileSpaceToToggleNetworkEditor") and getSessionVariable("spaceKeyIsDown"):
                size = QtCore.QSize(1, 1)

            #print(size)

            topMaskHeight = getSessionVariable("networkEditorTopMaskHeight")
            xOffsetCorrection = getSessionVariable("networkEditorXOffsetCorrection")

            overlayNE = hou.session.animatrix_overlay_network_editor
            if shiboken2.isValid(overlayNE) and overlayNE and overlayNE.toolTip() == "visible":
                overlayNE.resize(size.width(), size.height() + topMaskHeight)
                overlayNE.move(pos.x() + xOffsetCorrection, pos.y() - topMaskHeight)



def setOverlayNetworkEditorVisible(visible):
    overlayNE = hou.session.animatrix_overlay_network_editor
    if overlayNE:
        if visible:
            overlayNE.show()
            overlayNE.setToolTip("visible")
        else:
            overlayNE.hide()
            overlayNE.setToolTip("hidden")



def initializeNewFloatingNetworkEditorCallback():
    name = "animatrix_overlay_network_editor"
    networkEditor = findFloatingPanelByName(name)
    if networkEditor:
        panes = networkEditor.paneTabs()
        if panes:
            resetNetworkEditorZoomLevelFromEditorCenter(editor=panes[0])

    overlayNE = getWidgetByName(name)
    hou.session.animatrix_overlay_network_editor = overlayNE
    toggleOverlayNetworkEditor(ignoreIntegratedNetworkEditor=True)

    hou.ui.removeEventLoopCallback(initializeNewFloatingNetworkEditorCallback)



def initializeNewFloatingNetworkEditor():
    hou.ui.addEventLoopCallback(initializeNewFloatingNetworkEditorCallback)



def toggleOverlayNetworkEditor(ignoreIntegratedNetworkEditor=False):
    desktop = hou.ui.curDesktop()
    if not ignoreIntegratedNetworkEditor:
        paneTab = desktop.findPaneTab("animatrix_network_editor")
        if not paneTab:
            paneTab2 = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if paneTab2.name() != "animatrix_overlay_network_editor":
                paneTab = paneTab2

        if paneTab:
            pane = paneTab.pane()
            if not pane.isSplitMinimized():
                pane.setIsSplitMaximized(False)


    overlayNE = hou.session.animatrix_overlay_network_editor
    if shiboken2.isValid(overlayNE):
        if overlayNE:
            if overlayNE.toolTip() == "":
                overlayNE.setWindowOpacity(getSessionVariable("overlayNetworkEditorOpacity"))
                #overlayNE.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
                overlayNE.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
                overlayNE.setToolTip("hidden")

            if overlayNE.toolTip() == "visible":
                overlayNE.setToolTip("hidden")
                overlayNE.hide()
            else:
                overlayNE.setToolTip("visible")
                overlayNE.show()

            setSessionVariable("overlayNetworkEditorCallbackSuspended", False)
    else:
        createNewFloatingNetworkEditor()
        timer = threading.Timer(2, initializeNewFloatingNetworkEditor)
        timer.start()



def toggleNetworkEditor():
    if getSessionVariable("isOverlayNetworkEditorInstalled"):
        setSessionVariable("overlayNetworkEditorCallbackSuspended", True)

    overlayNE = hou.session.animatrix_overlay_network_editor

    networkEditor = hou.ui.curDesktop().findPaneTab("animatrix_network_editor")
    if not networkEditor:
        networkEditor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)

    if networkEditor:
        pane = networkEditor.pane()
        isMinimized = pane.isSplitMinimized()
        
        pane.setIsSplitMaximized(isMinimized)
        pane.setSplitFraction(0.5)

        if getSessionVariable("isOverlayNetworkEditorInstalled"):
            if isMinimized:
                if overlayNE.toolTip() == "visible":
                    setOverlayNetworkEditorVisible(False)
                    setSessionVariable("wasOverlayNetworkEditorVisible", True)
            else:
                if getSessionVariable("wasOverlayNetworkEditorVisible"):
                    setOverlayNetworkEditorVisible(True)
                    setSessionVariable("wasOverlayNetworkEditorVisible", False)



def setOverlayNetworkEditorOpacity(opacity):
    overlayNE = hou.session.animatrix_overlay_network_editor
    if overlayNE:
        setSessionVariable("overlayNetworkEditorOpacity", opacity)
        overlayNE.setWindowOpacity(opacity)