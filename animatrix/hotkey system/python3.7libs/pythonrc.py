"""
Context-Sensitive Rule-Based Hotkey System Settings
"""
UseMMBToSelectNearestNode = False
UseLMBToSelectNearestNode = True
MMBSelectNearestNodeTimeLimit = 0.1 #seconds



def initializeHotkeySystem():
    hou.session.UseMMBToSelectNearestNode = UseMMBToSelectNearestNode
    hou.session.UseLMBToSelectNearestNode = UseLMBToSelectNearestNode
    hou.session.MMBSelectNearestNodeTimeLimit = MMBSelectNearestNodeTimeLimit



try:
    if hou.isUIAvailable():
        import hdefereval
        hdefereval.execute_deferred(initializeHotkeySystem)
except:
    pass