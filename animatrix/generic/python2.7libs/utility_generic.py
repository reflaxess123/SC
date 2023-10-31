import hou
import os, sys, fnmatch, pickle
import importlib
from shutil import copyfile
from PySide2 import QtCore, QtWidgets, QtGui
import utility_ui
import numpy as np



this = sys.modules[__name__]
currentdir = os.path.dirname(os.path.realpath(__file__))

def __reload_pythonlibs(showstatus=True):
    if showstatus:
        print ("Reloading generic libraries...")
    importlib.reload(this)
    importlib.reload(utility_ui)

fs_watcher = QtCore.QFileSystemWatcher()
fs_watcher.addPath(os.path.join(currentdir, "utility_generic.py"))
fs_watcher.addPath(os.path.join(currentdir, "utility_ui.py"))


fs_watcher.fileChanged.connect(__reload_pythonlibs)



def localizeHDAs():
    hipdir = hou.expandString("$HIP")
    otlsdir = os.path.join(hipdir, "otls")
    nsNodes, embeddedNodes = getNonStandardNodes()
    
    if nsNodes:
        sourceHDAs = []
        targetHDAs = []
        for node in nsNodes:
            nodetype = node.type()
            if "animatrix" not in nodetype.name():
                nodetypedef = nodetype.definition()
                if nodetypedef:
                    sourcefile = nodetypedef.libraryFilePath()
                    if sourcefile != "Embedded":
                        filename = os.path.basename(sourcefile)
                        targetfile = os.path.join(otlsdir, filename)
                        sourcefile = sourcefile.replace(os.sep, '/')
                        targetfile = targetfile.replace(os.sep, '/')
                        if sourcefile != targetfile and sourcefile not in sourceHDAs:
                            sourceHDAs.append(sourcefile)
                            targetHDAs.append(targetfile)
                        
        if sourceHDAs:
            if not os.path.exists(otlsdir):
                os.makedirs(otlsdir)
                
            for index, sourcefile in enumerate(sourceHDAs):
                targetfile = targetHDAs[index]
                print ("source: ", sourcefile)
                print ("target: ", targetfile)
                copyfile(sourcefile, targetfile)
                hou.hda.installFile(targetfile, oplibraries_file=None, force_use_assets=True)



def convertCategoryToOpCode(category):
    opcode = category
    if category == "DRIVER":
        opcode = "ROP"
    elif category == "OBJECT":
        opcode = "OBJ"
    elif category == "MANAGER":
        opcode = "NET"
    elif category == "COPNET":
        opcode = "COP"
    elif category == "DIRECTOR":
        opcode = "ROOT"
    elif category == "TOPNET":
        opcode = "TOP"
    elif category == "COP2":
        opcode = "COP"
        
    return opcode



def isStandardHDANode(node):
    hfs = hou.expandString("$HFS")
    
    hdadef = node.type().definition()
    if hdadef:
        hdapath = hdadef.libraryFilePath()
        if os.path.exists(hdapath):
            if hdapath.startswith(hfs):
                return True
    else:
        return True
            
    return False



def isEmbeddedNode(node):
    hdadef = node.type().definition()
    if hdadef:
        hdapath = hdadef.libraryFilePath()
        if hdapath == "Embedded":
            return True
            
    return False



def getNonStandardNodes():
    nsNodes = []
    embdeddedNodes = []
    
    nodes = hou.node("/").allNodes()
    for node in nodes:
        if not isStandardHDANode(node):
            nsNodes.append(node)
            
            if isEmbeddedNode(node):
                embdeddedNodes.append(node)
                
    return nsNodes, embdeddedNodes



def openfile(path):
    dirname = os.path.dirname(path)
    if platform.system() == "Windows":
        subprocess.Popen(r'explorer /select,' + os.path.abspath(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", dirname])
    else:
        subprocess.Popen(["xdg-open", dirname])



def getOperatorContextFromHDA(hdadef):
    context = hdadef.nodeTypeCategory().name().upper()
    return convertCategoryToOpCode(context)



def getOperatorContextFromNode(node):
    context = node.type().category().name().upper()
    return convertCategoryToOpCode(context)



def getRecentHipFiles():
    userdir = hou.getenv('HOUDINI_USER_PREF_DIR')
    file = os.path.join(userdir, "file.history")
    
    validfiles = []
    with open(file) as f:
        lines = f.readlines()
        for line in lines:
            newline = line.strip()
            if newline == "}":
                break;
                
            if newline != "{" and newline != "HIP":
                if os.path.exists(newline):
                    validfiles.append(newline)
            
        
    validfiles.reverse()
    return validfiles



#   For QWERTY keyboards only, this is a limitation of Qt
def getUnshiftedKey(shiftedKey, modifierstate):
    key = shiftedKey.replace('Ctrl+', '').replace('Alt+', '')
    shiftKey = 'Shift+'
    unshiftedKey = key.replace(shiftKey, '')
    if modifierstate.shift:
        if (shiftKey not in key):
            shiftedValues = ['~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '{', '}', ':', '"', '<', '>', '?', '|', 'Insert', 'Del', 'End', 'DownArrow', 'PageDown', 'LeftArrow', 'Clear', 'RightArrow', 'Home', 'UpArrow', 'PageUp']
            unshiftedValues = ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "[", "]", ";", "'", ",", ".", "/", "\\", "Pad0", "PadDot", "Pad1", "Pad2", "Pad3", "Pad4", "Pad5", "Pad6", "Pad7", "Pad8", "Pad9"]
            
            if key in shiftedValues:
                index = shiftedValues.index(key)
                unshiftedKey = unshiftedValues[index]

    return unshiftedKey



def findNearestNode(editor):
    pos = editor.cursorPosition()
    currentPath = editor.pwd().path()

    nodes = hou.node(currentPath).children()
    nearestNode = None
    dist = 999999999.0
    for node in nodes:
        d = (node.position() + (node.size() * 0.5)).distanceTo(pos)
        if d < dist:
            nearestNode = node
            dist = d

    return nearestNode



def selectNearestNodeFromEditor(editor):
    with hou.undos.group("Select Nearest Node"):
        nearestNode = findNearestNode(editor)
        if nearestNode and hou.selectedNodes()[0] != nearestNode:
            nearestNode.setSelected(True, clear_all_selected=True)



def selectNearestNode(uievent):
    with hou.undos.group("Select Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            selectedNodes = hou.selectedNodes()
            if (len(selectedNodes) == 1 and selectedNodes[0] != nearestNode) or len(selectedNodes) != 1:
                nearestNode.setSelected(True, clear_all_selected=True)



def displayNearestNode():
    with hou.undos.group("Display Nearest Node"):
        nearestNode = findNearestNode()
        if nearestNode:
            nearestNode.setDisplayFlag(not nearestNode.isDisplayFlagSet())
            nearestNode.setRenderFlag(not nearestNode.isRenderFlagSet())



def displayNearestNode(uievent, context):
    with hou.undos.group("Display Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            if context != "Driver" and context != "Shop" and context != "Chop" and context != "Vop":
                nearestNode.setDisplayFlag(not nearestNode.isDisplayFlagSet())
            if context != "Object" and context != "Driver" and context != "Dop" and context != "Shop" and context != "Chop" and context != "Vop" and context != "Lop":
                nearestNode.setRenderFlag(not nearestNode.isRenderFlagSet())



def displaySelectNearestNode():
    with hou.undos.group("Display & Select Nearest Node"):
        nearestNode = findNearestNode()
        if nearestNode:
            nearestNode.setSelected(True, clear_all_selected=True)
            nearestNode.setDisplayFlag(not nearestNode.isDisplayFlagSet())
            nearestNode.setRenderFlag(not nearestNode.isRenderFlagSet())



def displaySelectNearestNode(uievent, context):
    with hou.undos.group("Display & Select Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            nearestNode.setSelected(True, clear_all_selected=True)
            if context != "Driver" and context != "Shop" and context != "Chop" and context != "Vop":
                if hasattr(nearestNode, "setDisplayFlag"):
                    nearestNode.setDisplayFlag(not nearestNode.isDisplayFlagSet())
            if context != "Object" and context != "Driver" and context != "Dop" and context != "Shop" and context != "Chop" and context != "Vop" and context != "Lop":
                 if hasattr(nearestNode, "setDisplayFlag"):
                    nearestNode.setRenderFlag(not nearestNode.isRenderFlagSet())



def templateNearestNode(uievent):
    with hou.undos.group("Template Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            nearestNode.setGenericFlag(hou.nodeFlag.Template, not nearestNode.isGenericFlagSet(hou.nodeFlag.Template))



def selectableTemplateNearestNode(uievent):
    with hou.undos.group("Selectable Template Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            nearestNode.setGenericFlag(hou.nodeFlag.Footprint, not nearestNode.isGenericFlagSet(hou.nodeFlag.Footprint))



def bypassNearestNode(uievent):
    with hou.undos.group("Bypass Nearest Node"):
        editor = uievent.editor
        nearestNode = findNearestNode(editor)
        if nearestNode:
            nearestNode.setGenericFlag(hou.nodeFlag.Bypass, not nearestNode.isGenericFlagSet(hou.nodeFlag.Bypass))



def templateSelectedNodes():
    with hou.undos.group("Template Selected Nodes"):
        selNodes = hou.selectedNodes()
        for n in selNodes:
            n.setGenericFlag(hou.nodeFlag.Template, not n.isGenericFlagSet(hou.nodeFlag.Template))



def selectableTemplateSelectedNodes():
    with hou.undos.group("Selectable Template Selected Nodes"):
        selNodes = hou.selectedNodes()
        for n in selNodes:
            n.setGenericFlag(hou.nodeFlag.Footprint, not n.isGenericFlagSet(hou.nodeFlag.Footprint))



def bypassSelectedNodes(uievent):
    with hou.undos.group("Bypass Selected Nodes"):
        editor = uievent.editor
        selNodes = hou.selectedNodes()
        for n in selNodes:
            n.setGenericFlag(hou.nodeFlag.Bypass, not n.isGenericFlagSet(hou.nodeFlag.Bypass))



def objectMergeFromSelection(uievent):
    with hou.undos.group("Object Merge From Selection"):
        editor = uievent.editor
        pos = editor.cursorPosition()
        currentPath = editor.pwd().path()
        currentNode = hou.node(currentPath)
        selNodes = hou.selectedNodes()
        for node in selNodes:
            mergeNode = currentNode.createNode("object_merge")
            mergeNode.setName("IN_" + node.name(), unique_name=True)
            mergeNode.parm("objpath1").set("../" + node.name())

            if len(selNodes) > 1:
                pos = node.position()
                pos[1] -= 1
                mergeNode.setPosition(pos)
            else:
                size = mergeNode.size ( )
                pos [ 0 ] -= size [ 0 ] / 2
                pos [ 1 ] -= size [ 1 ] / 2
                mergeNode.setPosition ( pos )



def objectMergeOutputConnections(uievent):
    import math, re
    import toolutils as tutils

    with hou.undos.group("Object Merge Output Connections"):
        editor = uievent.editor
        currentPath = editor.pwd().path()
        currentNode = hou.node(currentPath)
        selNodes = hou.selectedNodes()
        sourceNodes = selNodes
        for node in selNodes:
            connectedNodes = tutils.findConnectedNodes(node, 'output', None)

            outputsReplaced = []
            newNullNodes = []
            newOutputNodes = []
            outputIndices = []

            childrenNames = []
            childrenNodes = []
            
            outputs = node.outputConnections()
            for o in outputs:
                outputIndex = o.outputIndex()
                outputNode = o.outputNode()
                if outputIndex not in outputsReplaced:
                    outputsReplaced.append(outputIndex)

                    outputIndices.append(outputIndex)

                    outputName = o.inputLabel().replace(' ', '_').upper()
                    re.sub(r'\W+', '', outputName)
                    
                    newNullNode = currentNode.createNode("null", outputName)
                    newNullNode.setInput(0, node, outputIndex)
                    
                    mergeNodeName = newNullNode.name()
                    mergeNode = currentNode.createNode("object_merge")
                    mergeNode.setName("IN_" + mergeNodeName, unique_name=True)
                    mergeNode.parm("objpath1").set("../" + mergeNodeName)
                    
                    newNullNodes.append(newNullNode)
                    newOutputNodes.append(mergeNode)
                    

                outputNodeName = outputNode.name()
                if outputNodeName not in childrenNames:
                    childrenNames.append(outputNodeName)
                    childrenNodes.append(outputNode)
            

            lowestPosY = 0
            outputCount = len(outputsReplaced)
            for index, newNode in enumerate(newNullNodes):
                outputIndex = outputIndices[index]
                
                xoffset = math.ceil((outputCount - 0) / 2) - outputIndex
                yoffset = outputIndex + 1
                pos = node.position()
                pos[0] -= xoffset
                pos[1] -= yoffset

                newNode.setPosition(pos)
                pos[1] -= min(3, outputCount)
                lowestPosY = pos[1]

                newOutputNodes[index].setPosition(pos)


            for o in outputs:
                outputNode = o.outputNode()
                outputIndex = o.outputIndex()
                inputIndex = o.inputIndex()
                
                outputNode.setInput(inputIndex, newOutputNodes[outputIndex])
            

            maxPosY = -999999999
            for connectedNode in connectedNodes:
                maxPosY = max(maxPosY, connectedNode.position().y())

            dist = lowestPosY - maxPosY
            minOffset = 2
            if dist < minOffset:
                diff = minOffset - dist
                for connectedNode in connectedNodes:
                    pos = connectedNode.position()
                    pos[1] -= diff
                    connectedNode.setPosition(pos)



def objectMergeInputConnections(uievent):
    import math, re
    import toolutils as tutils

    with hou.undos.group("Object Merge Output Connections"):
        editor = uievent.editor
        currentPath = editor.pwd().path()
        currentNode = hou.node(currentPath)
        selNodes = hou.selectedNodes()
        sourceNodes = []
        for node in selNodes:
            inputNodes = node.inputs()
            for n in inputNodes:
                if n not in sourceNodes:
                    sourceNodes.append(n)

        for node in sourceNodes:
            connectedNodes = tutils.findConnectedNodes(node, 'output', None)

            outputsReplaced = []
            newNullNodes = []
            newOutputNodes = []
            outputIndices = []

            childrenNames = []
            childrenNodes = []
            
            outputs = node.outputConnections()
            outputs = [output for output in outputs if output.outputNode() in selNodes]

            for o in outputs:
                outputIndex = o.outputIndex()
                outputNode = o.outputNode()
                if outputIndex not in outputsReplaced:
                    outputsReplaced.append(outputIndex)

                    outputIndices.append(outputIndex)

                    outputName = o.inputLabel().replace(' ', '_').upper()
                    re.sub(r'\W+', '', outputName)
                    
                    newNullNode = currentNode.createNode("null", outputName)
                    newNullNode.setInput(0, node, outputIndex)
                    
                    mergeNodeName = newNullNode.name()
                    mergeNode = currentNode.createNode("object_merge")
                    mergeNode.setName("IN_" + mergeNodeName, unique_name=True)
                    mergeNode.parm("objpath1").set("../" + mergeNodeName)
                    
                    newNullNodes.append(newNullNode)
                    newOutputNodes.append(mergeNode)
                    

                outputNodeName = outputNode.name()
                if outputNodeName not in childrenNames:
                    childrenNames.append(outputNodeName)
                    childrenNodes.append(outputNode)
            

            lowestPosY = 0
            outputCount = len(outputsReplaced)
            for index, newNode in enumerate(newNullNodes):
                outputIndex = outputIndices[index]
                
                xoffset = math.ceil((outputCount - 0) / 2) - outputIndex
                yoffset = outputIndex + 1
                pos = node.position()
                pos[0] -= xoffset
                pos[1] -= yoffset

                newNode.setPosition(pos)
                pos[1] -= min(3, outputCount)
                lowestPosY = pos[1]

                newOutputNodes[index].setPosition(pos)


            for o in outputs:
                outputNode = o.outputNode()
                outputIndex = o.outputIndex()
                inputIndex = o.inputIndex()

                outputNode.setInput(inputIndex, newOutputNodes[outputIndex])
            

            maxPosY = -999999999
            for connectedNode in connectedNodes:
                maxPosY = max(maxPosY, connectedNode.position().y())

            dist = lowestPosY - maxPosY
            minOffset = 2
            if dist < minOffset:
                diff = minOffset - dist
                for connectedNode in connectedNodes:
                    pos = connectedNode.position()
                    pos[1] -= diff
                    connectedNode.setPosition(pos)



def randomConstantColor(uievent):
    with hou.undos.group("Random Constant Color"):
        import random

        newNode = createNewNode(uievent, "color")
        if newNode:
            newNode.parm("colortype").set(0)
            colors = ((1,0,0), (0,1,0), (0,0,1), (1,0.35,0), (1,1,0), (0,1,1), (1,0,1), (0.45,0,1), (0.45,1,0), (0,0.45,1))
            newNode.parmTuple("color").set(random.choice(colors))



def toFloatOrVector(uievent):
    selectedNodes = hou.selectedNodes()
    if selectedNodes:
        selectedNode = selectedNodes[-1]
        outputDataTypes = selectedNode.outputDataTypes()
        if outputDataTypes:
            firstOutputType = outputDataTypes[0]
            isDestinationType = firstOutputType == 'float'
            undoname = 'To Vector' if isDestinationType else 'To Float'
            
            outputtypes = ['int', 'float', 'vector2', 'vector', 'vector4', 'matrix2', 'matrix3', 'matrix']
            nodetypes = ['inttofloat', 'floattovec', 'vec2tofloat', 'vectofloat', 'hvectofloat', 'matx2tofloat', 'matxtofloat', 'hmatxtofloat']
            index = outputtypes.index(firstOutputType) if firstOutputType in outputtypes else None
            if index != None:
                with hou.undos.group(undoname):
                    editor = uievent.editor
                    newNode = createNewNode(editor, nodetypes[index])



def toVectorOrFloat(uievent):
    selectedNodes = hou.selectedNodes()
    if selectedNodes:
        selectedNode = selectedNodes[-1]
        outputDataTypes = selectedNode.outputDataTypes()
        if outputDataTypes:
            firstOutputType = outputDataTypes[0]
            isDestinationType = firstOutputType == 'int'
            undoname = 'To Float' if isDestinationType else 'To Vector'
            
            outputtypes = ['int', 'float', 'vector2', 'vector', 'vector4', 'matrix3']
            nodetypes = ['inttovec', 'floattovec', 'vec2tovec', 'vectofloat', 'hvectovec', 'matxtovec']
            index = outputtypes.index(firstOutputType) if firstOutputType in outputtypes else None
            if index != None:
                with hou.undos.group(undoname):
                    editor = uievent.editor
                    newNode = createNewNode(editor, nodetypes[index])



def toVector4OrFloat(uievent):
    selectedNodes = hou.selectedNodes()
    if selectedNodes:
        selectedNode = selectedNodes[-1]
        outputDataTypes = selectedNode.outputDataTypes()
        if outputDataTypes:
            firstOutputType = outputDataTypes[0]
            isDestinationType = firstOutputType == 'int'
            undoname = 'To Float' if isDestinationType else 'To Vector4'
            
            outputtypes = ['float', 'vector2', 'vector', 'vector4', 'matrix3', 'matrix']
            nodetypes = ['floattohvec', 'vec2tohvec', 'vectohvec', 'hvectofloat', 'matxtoquat', 'hmatxtohvec']
            index = outputtypes.index(firstOutputType) if firstOutputType in outputtypes else None
            if index != None:
                with hou.undos.group(undoname):
                    editor = uievent.editor
                    newNode = createNewNode(editor, nodetypes[index])



def toMatrix3OrFloat(uievent):
    selectedNodes = hou.selectedNodes()
    if selectedNodes:
        selectedNode = selectedNodes[-1]
        outputDataTypes = selectedNode.outputDataTypes()
        if outputDataTypes:
            firstOutputType = outputDataTypes[0]
            isDestinationType = firstOutputType == 'int'
            undoname = 'To Float' if isDestinationType else 'To Integer'
            
            outputtypes = ['float', 'vector2', 'vector', 'vector4', 'matrix2', 'matrix3', 'matrix']
            nodetypes = ['floattomatx', 'vec2tomatx2', 'vectomatx', 'quattomatx', 'm2tom3', 'matxtofloat', 'm4tom3']
            index = outputtypes.index(firstOutputType) if firstOutputType in outputtypes else None
            if index != None:
                with hou.undos.group(undoname):
                    editor = uievent.editor
                    newNode = createNewNode(editor, nodetypes[index])


def toMatrixOrFloat(uievent):
    selectedNodes = hou.selectedNodes()
    if selectedNodes:
        selectedNode = selectedNodes[-1]
        outputDataTypes = selectedNode.outputDataTypes()
        if outputDataTypes:
            firstOutputType = outputDataTypes[0]
            isDestinationType = firstOutputType == 'int'
            undoname = 'To Float' if isDestinationType else 'To Integer'
            
            outputtypes = ['float', 'vector4', 'matrix2', 'matrix3', 'matrix']
            nodetypes = ['floattohmatx', 'hvectohmatx', 'm2tom4', 'm3tom4', 'hmatxtofloat']
            index = outputtypes.index(firstOutputType) if firstOutputType in outputtypes else None
            if index != None:
                with hou.undos.group(undoname):
                    editor = uievent.editor
                    newNode = createNewNode(editor, nodetypes[index])



def findNodeByType(context, pattern):
    import fnmatch

    nodeTypeCategories = {}
    nodeTypeCategories['Object'] = hou.objNodeTypeCategory()
    nodeTypeCategories['Sop'] = hou.sopNodeTypeCategory()
    nodeTypeCategories['Vop'] = hou.vopNodeTypeCategory()
    nodeTypeCategories['Dop'] = hou.dopNodeTypeCategory()
    nodeTypeCategories['Cop2'] = hou.cop2NodeTypeCategory()
    nodeTypeCategories['Chop'] = hou.chopNodeTypeCategory()
    nodeTypeCategories['Shop'] = hou.shopNodeTypeCategory()
    nodeTypeCategories['Driver'] = hou.ropNodeTypeCategory()
    nodeTypeCategories['Top'] = hou.topNodeTypeCategory()
    nodeTypeCategories['Lop'] = hou.lopNodeTypeCategory()

    category = nodeTypeCategories[context]

    nodes = [nodetype
        for nodetypename, nodetype in category.nodeTypes().items()
        if fnmatch.fnmatch(nodetypename, pattern)]

    if nodes:
        return nodes[0]
    else:
        return None



def doesNodeTypeExist(context, nodetypename):
    return findNodeByType(context, nodetypename) != None



def isCapsLockOn():
    if os.name == 'nt':
        hllDll = ctypes.WinDLL ("User32.dll")
        VK_CAPITAL = 0x14
        
        return hllDll.GetKeyState(VK_CAPITAL) == 1
    else:
        return False



def restartPlayback():
    with hou.undos.disabler():
        hou.playbar.stop()
        hou.setFrame(hou.playbar.playbackRange()[0])
        hou.playbar.play()



def goToFirstFrame():
    with hou.undos.disabler():
        hou.playbar.stop()
        frame = hou.playbar.playbackRange()[0]
        while hou.frame() != frame:
            hou.setFrame(frame)



def sortNodeInputs(nodes=None):
    with hou.undos.group("Sort Node Inputs"):
        if not nodes:
            nodes = hou.selectedNodes()

        for node in nodes:
            inputs = node.inputs()
            sortedInputs = sorted(inputs, key=lambda n: n.position().x())
            
            for index, input in enumerate(inputs):
                node.setInput(index, sortedInputs[index])



def dropNodeOnWire(newNode, nodeConnections):
    newNodeType = newNode.type()
    ninputs = newNodeType.maxNumInputs()
    noutputs = newNodeType.maxNumOutputs()
    

    sortedwires = sorted(nodeConnections, key=lambda c: c.inputNode().position().x())
    sortedwires = sorted(sortedwires, key=lambda c: c.inputIndex())
    uniquewires = []
    uniquenames = []

    for w in sortedwires:
        uniquename = w.inputNode().name() + ":" + str(w.inputIndex())
        if uniquename not in uniquenames:
            uniquenames.append(uniquename)
            uniquewires.append(w)

    nwires = len(uniquewires)
    #print "first", uniquewires
    #print "-----------------------------------------"
    for i in range(min(ninputs, nwires)):
        c = uniquewires[i]
        #print c.inputNode().name(), c.outputIndex(), newNode.name()
        newNode.setInput(i, c.inputNode(), c.outputIndex())

    sortedwires = sorted(nodeConnections, key=lambda c: c.outputNode().position().x())
    sortedwires = sorted(sortedwires, key=lambda c: c.outputIndex())

    #print "second", sortedwires
    for i in range(nwires):
        outputIndex = i
        if i >= noutputs - 1:
            outputIndex = noutputs - 1

        c = sortedwires[i]
        #print c.outputNode().name(), c.inputIndex(), newNode.name(), outputIndex
        c.outputNode().setInput(c.inputIndex(), newNode, outputIndex)



def connectSelectedNodesToNewNode(newNode, selNodes, connectToNearestNodeIfNoSelection=False):
    category = newNode.type().category()
    isSop = category == hou.sopNodeTypeCategory()
    isVop = category == hou.vopNodeTypeCategory()

    selectedNodes = selNodes
    nodecount = len(selectedNodes)
    if nodecount == 0 and connectToNearestNodeIfNoSelection:
        editor = hou.ui.paneTabUnderCursor()
        if editor:
            nearestNode = findNearestNode(editor)
            if nearestNode:
                selectedNodes = [nearestNode]
                nodecount = 1

    if nodecount > 0:
        newNodeType = newNode.type()
        ninputs = newNodeType.maxNumInputs()
        if ninputs > 1:
            #sort nodes from left to right and connect by position
            selectedNodes = sorted(selectedNodes, key=lambda n: n.position().x())

        if len(selectedNodes) == 1 and (isSop or isVop):
            selectedNode = selectedNodes[0]
            outputConnectors = selectedNode.outputConnectors()
            inputConnectors = newNode.inputConnectors()

            if selectedNode.type().name() == 'subnet' or (isSop and newNodeType.name() == "merge"):
                outputConnectors = [outputConnectors[0]]

            if isSop:
                for i in range(min(len(outputConnectors), len(inputConnectors))):
                    newNode.setInput(i, selectedNode, i)
            if isVop:
                outputIndex = 0
                outputDataTypes = selectedNode.outputDataTypes()
                inputDataTypes = newNode.inputDataTypes()
                numOutputDataTypes = len(outputDataTypes)
                numInputDataTypes = len(inputDataTypes)
                for i in range(numInputDataTypes):
                    if outputIndex == numOutputDataTypes:
                        break
                    if outputDataTypes[outputIndex] == inputDataTypes[i]:
                        newNode.setInput(i, selectedNode, outputIndex)
                        outputIndex += 1
        else:
            index = 0
            for i in range(nodecount):
                if selectedNodes[i].type().maxNumOutputs() > 0 and index < ninputs:
                    newNode.setInput(index, selectedNodes[i])
                    index += 1



def createNewNode(uievent, nodetypename, parms=None):
    import nodegraphutils as utils
    
    pwd = uievent.editor.pwd()
    path = pwd.path()
    context = pwd.childTypeCategory().name()
    if pwd and path and context:
        nodetype = hou.nodeType(pwd.childTypeCategory(), nodetypename)
        if nodetype:
            selectedNodes = hou.selectedNodes()
            with hou.undos.group("Create New Node: " + nodetype.description()):
                pos = uievent.editor.cursorPosition()
                
                newNode = hou.node(path).createNode(nodetypename)

                if parms:
                    if isinstance(parms, dict):
                        for i, (key, value) in enumerate(parms.items()):
                            newNode.parm(key).set(value)
                    elif isinstance(parms, types.StringTypes):
                        hou.hscript("oppresetload " + newNode.path() + " '{0}'".format(parms))


                radius = utils.getConnectorSnapRadius(uievent.editor)
                targets = utils.getPossibleDropTargets(uievent, radius)
                nodewires = [target.item for target in targets if target.name == "wire"]

                setdisplayflag = False
                if nodewires:
                    dropNodeOnWire(newNode, nodewires)
                else:
                    connectSelectedNodesToNewNode(newNode, selectedNodes)
                    setdisplayflag = True
                
                size = utils.getNewNodeHalfSize()
                pos[0] -= size.x()
                pos[1] -= size.y()

                newNode.setPosition(pos)
                newNode.setSelected(True, clear_all_selected=True)

                nodecount = len(selectedNodes)
                if setdisplayflag and nodecount != 0:
                    if context != "Driver" and context != "Dop" and context != "Shop" and context != "Chop" and context != "Vop":
                        if hasattr(newNode, "setDisplayFlag"):
                            newNode.setDisplayFlag(True)
                    if context != "Object" and context != "Driver" and context != "Dop" and context != "Shop" and context != "Chop" and context != "Vop" and context != "Lop":
                        if hasattr(newNode, "setDisplayFlag"):
                            newNode.setRenderFlag(True)

                return newNode



def pushNodes(kwargs, inside=True):
    import toolutils

    with hou.undos.group("Push Nodes"):
        pane = kwargs["pane"]
        center = pane.cursorPosition()
        nodes = pane.pwd().children()

        for node in nodes:
            p = node.position()
            n = (p - center).normalized()
            amount = -8.0 if inside else 8.0
            node.setPosition(p + n * amount)



def showCurrentHipFilename():
    with hou.undos.disabler():
        hou.ui.setStatusMessage(hou.hipFile.name())



def pasteRandomNumber(digits=4, decimals=4):
    rnd = np.random.uniform(0, pow(10, digits), 1)[0].round(decimals=decimals)
    hou.ui.copyTextToClipboard(str(rnd))
    key = QtGui.QKeyEvent(QtGui.QKeyEvent.KeyPress, QtGui.Qt.Key_V, QtGui.Qt.ControlModifier, "V")
    QtWidgets.QApplication.sendEvent(QtWidgets.QApplication.focusWidget(), key)



def getFiles(directory, pattern):
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename



def loadSerializedHDADatabase():
    files = getFiles(".", "*.hdadb")

    hdas = []
    for hdafile in files:
        with open(hdafile, 'rb') as f:
            hdas.extend(pickle.load(f))

    return hdas



def getQtIcon(hdaDefOrNode, size=16, defaultIcon="Sop/box"):
    iconsize = hou.ui.scaledSize(size)
    isHDADef = type(hdaDefOrNode) == hou.HDADefinition
    if isHDADef:
        try:
            icon = hdaDefOrNode.icon() if isHDADef else hdaDefOrNode.type().icon()
            qtIcon = hou.qt.Icon(icon, width=iconsize, height=iconsize)
        except:
            defaultIconPath = defaultIcon.split("/")
            default = findNodeByType(defaultIconPath[0], defaultIconPath[1]).icon()
            qtIcon = hou.qt.Icon(default, width=iconsize, height=iconsize)
    else:
        iconPath = hdaDefOrNode.split("/")
        default = findNodeByType(iconPath[0], iconPath[1]).icon()
        qtIcon = hou.qt.Icon(default, width=iconsize, height=iconsize)

    return qtIcon