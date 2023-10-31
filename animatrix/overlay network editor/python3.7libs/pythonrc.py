import os, sys, shiboken2
from PySide2 import QtCore, QtWidgets, QtGui
from utility_ui import refreshHDAManager, hideObsoleteOperators, syncAdvancedCodeEditorToSelection, syncHDAManagerToSelectedNode, getWidgetByName



"""
Supercharged H19 Settings

useVolatileSpaceToToggleNetworkEditor
If it's True, Space as a volatile key will be reserved for toggling the overlay network editor.
If it's False, Space will be free to be used as a modifier key to define custom actions in hotkeys.csv.
"""
useVolatileSpaceToToggleNetworkEditor = True
overlayNetworkEditorOpacity = 0.75
finalizeUITimerInSeconds = 8
resetZoomLevelTimerInSeconds = 2
networkEditorXOffsetCorrection = 0
networkEditorTopMaskHeight = 0
hideMainMenuBarAtStartup = True
hideShelfDockAtStartup = True
lastStatusMessageTimeInMs = -1
lastStatusMessageTimeTimeout = 1000



def globalNetworkEditorNodeSelectionCallback(selection):
    if selection:
        syncAdvancedCodeEditorToSelection(selection[-1])
        if len(selection) == 1:
            syncHDAManagerToSelectedNode(selection[-1])



def updateOverlayNetworkEditor():
    from utility_overlay_network_editor import updateUIElements

    updateUIElements()
    


class ViewportEventFilter(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Resize:
            self.updateWidget()
 
        elif event.type() == QtCore.QEvent.Move:
            self.updateWidget()
        
        return False
 
 
    def updateWidget(self):
        viewportPos = hou.session.viewportWidget.mapToGlobal(QtCore.QPoint(0, 0))
        viewportSize = hou.session.viewportWidget.size()
        
        hou.session.overlayviewpos = viewportPos
        hou.session.overlayviewsize = viewportSize
        


def finalizeUI():
    from utility_ui import fullscreenSession

    fullscreenSession()



def resetZoomLevel():
    hou.ui.addEventLoopCallback(resetZoomLevelCallback)



def setTitleToFilename():
    filename = hou.hipFile.name()
    if "/" in filename:
        filepath = filename.split("/")
        title = filepath[-1]
        if hou.qt.mainWindow().windowTitle() != title:
            hou.qt.mainWindow().setWindowTitle(title)
        


def initializeOverlayNetworkEditor():
    import threading
    from utility_ui import findFloatingPanelByName
    from utility_overlay_network_editor import createNewFloatingNetworkEditor, updateUIElements, initializeNewFloatingNetworkEditor, ViewportOutlineWidget

    if hideMainMenuBarAtStartup:
        hou.setPreference('showmenu.val', '0')
    if hideShelfDockAtStartup:
        hou.ui.curDesktop().shelfDock().show(False)
    
    networkEditor = findFloatingPanelByName("animatrix_overlay_network_editor")
    if not networkEditor:
        createNewFloatingNetworkEditor()
        
    hou.session.isOverlayNetworkEditorInstalled = True
    hou.session.isOverlayNetworkEditorVisible = False
    hou.session.overlayNetworkEditorOpacity = overlayNetworkEditorOpacity
    hou.session.networkEditorXOffsetCorrection = networkEditorXOffsetCorrection
    hou.session.networkEditorTopMaskHeight = networkEditorTopMaskHeight
    hou.session.useVolatileSpaceToToggleNetworkEditor = useVolatileSpaceToToggleNetworkEditor
    hou.session.lastStatusMessageTimeInMs = 0
    hou.session.lastStatusMessageTimeTimeout = 2000

    hou.ui.addEventLoopCallback(setTitleToFilename)
    hou.ui.addEventLoopCallback(updateOverlayNetworkEditor)
    hou.ui.addSelectionCallback(globalNetworkEditorNodeSelectionCallback)
    

    desktop = hou.ui.curDesktop()
    viewport = desktop.paneTabOfType(hou.paneTabType.SceneViewer)
    hou.session.viewportWidget = viewport.qtWindow()


    hou.session.viewportOutlineWidget = ViewportOutlineWidget()

    timer = threading.Timer(finalizeUITimerInSeconds, finalizeUI)
    timer2 = threading.Timer(resetZoomLevelTimerInSeconds, initializeNewFloatingNetworkEditor)
    timer.start()
    timer2.start()



try:
    if hou.isUIAvailable():
        import hdefereval
        hdefereval.execute_deferred(initializeOverlayNetworkEditor)
        hdefereval.execute_deferred(refreshHDAManager)
except:
    pass