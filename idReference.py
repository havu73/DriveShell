class idReference:
    def __init__(self,fileID,name,parents):
        self.id=fileID
        self.name=name
        self.parents=parents
    def getID(self):
        return self.id
    def getName(self):
        return self.name
    def getParents(self):
        return self.parents
    def to_string(self):
        return self.id + "   "+self.name+ "   "+str(self.parents)
    def add_parent(self,parent):
        self.parents.append(parent)
