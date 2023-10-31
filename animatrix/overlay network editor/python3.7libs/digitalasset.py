import hou
import json
from datetime import datetime
from utility_generic import *



class DigitalAsset:
    def __init__(self, hdadef, company="N/A"):
        self.name = hdadef.description()
        self.company = company
        self.context = getOperatorContextFromHDA(hdadef)
        self.category = hdadef.nodeTypeCategory().name()
        self.path = hdadef.libraryFilePath()
        self.modtime = hdadef.modificationTime()
        dt = datetime.fromtimestamp(self.modtime)
        self.moddate = "{0}-{1}-{2}".format(dt.year, dt.month, dt.day)
        self.mininputs = hdadef.minNumInputs()
        self.maxinputs = hdadef.maxNumInputs()
        components = hou.hda.componentsFromFullNodeTypeName(hdadef.nodeTypeName())
        self.namespace = components[1]
        self.typename = components[2]
        self.fulltypename = hdadef.nodeTypeName()
        self.fulltypenameWithoutVersion = components[1] + components[2]
        self.version = 0
        if components[3]:
            self.version = components[3]
    
    

    def getQtIcon(self):
        return getQtIcon(self.getDefinition())



    def getDefinition(self):
        hdas = hou.hda.definitionsInFile(self.path)
        for hda in hdas:
            if hda.nodeTypeName() == self.fulltypename:
                return hda
                
        return None
        
        
        
    def isCurrent(self):
        hdadef = self.getDefinition()
        if hdadef:
            return hdadef.isCurrent()
        else:
            return False