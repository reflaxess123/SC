from PySide2 import QtCore, QtWidgets, QtGui
from utility_generic import connectSelectedNodesToNewNode



modifierKeys = QtWidgets.QApplication.queryKeyboardModifiers()
if (modifierKeys & QtCore.Qt.ShiftModifier):
    newNode = kwargs["node"]
    connectSelectedNodesToNewNode(newNode, hou.selectedNodes(), connectToNearestNodeIfNoSelection=True)