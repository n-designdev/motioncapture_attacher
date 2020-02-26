# -*- coding: utf-8 -*-
import os, sys
import re
import pprint

# ------------------------------
env_key = 'ND_TOOL_PATH_PYTHON'

ND_TOOL_PATH = os.environ.get(env_key, 'Y:/tool/ND_Tools/python')

for path in ND_TOOL_PATH.split(';'):
    path = path.replace('\\', '/')
    if path in sys.path:
        continue
    sys.path.append(path)
# ------------------------------------

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2.QtUiTools import QUiLoader


class GUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(self.__class__, self).__init__(parent)
        self.ui_path = "Y:\\users\\env\\maya\\share\\nAnim\\motioncapture_attacher\\gui.ui"
        self.ui = QUiLoader().load(self.ui_path)
        self.table_list = []

        self.ui_connect()
        self.ui_setup()

        self.ui.show()


    def ui_connect(self):
        self.ui.exec_button.clicked.connect(self.exec_button_clicked)
        self.ui.refresh_button.clicked.connect(self.refresh_button_clicked)


    def ui_setup(self):
        from importlib import import_module
        import sys

        sys.path.append("Y:\\users\\env\\maya\\share\\nAnim\\motioncapture_attacher")
        self.setting_module = import_module("mc_setting")
        reload(self.setting_module)

        setting_dict = self.setting_module.setting
        self.table_list = setting_dict
        self.set_table()

    def set_table(self):
        self.ui.info_table.reset()
        for count, table_dict in enumerate(self.table_list):
            self.ui.info_table.setItem(count, 0, QtWidgets.QTableWidgetItem(table_dict["MC"]))
            self.ui.info_table.setItem(count, 1, QtWidgets.QTableWidgetItem(table_dict["const"]))
            self.ui.info_table.setItem(count, 2, QtWidgets.QTableWidgetItem(table_dict["RH"]))
            if self.ui.info_table.rowCount() < len(self.table_list)-1:
                self.ui.info_table.insertRow(self.ui.info_table.rowCount())


    def eventFilter(self, obj, event):
        pass


    def exec_button_clicked(self):
        self.constrain_body()


    def refresh_button_clicked(self):
        mc_ns = self.ui.mc_ns_line.text()
        rh_ns = self.ui.rh_ns_line.text()

        new_table_list = []
        for table_dict in self.table_list:
            _dict = {}
            if mc_ns != "":
                _dict["MC"] = mc_ns+":"+table_dict["MC"].split(":")[-1]
            else:
                _dict["MC"] = table_dict["MC"].split(":")[-1]
            if rh_ns != "":
                _dict["RH"] = rh_ns+":"+table_dict["RH"].split(":")[-1]
            else:
                _dict["RH"] = table_dict["RH"].split(":")[-1]
            _dict["const"] = table_dict["const"]
            new_table_list.append(_dict)

        self.table_list = new_table_list;
        self.set_table()


    def constrain_body(self):
        root_obj = self.setting_module.root
        nodes = []
        mc_namespace = self.ui.mc_ns_line.text() + ":"
        _nodes = self._get_nsObjs(mc_namespace)
        nodes.extend(cmds.ls(_nodes, type="transform"))
        nodes.extend(cmds.ls(_nodes, type="joint"))

        f_frame_set = set()
        l_frame_set = set()

        for _node in nodes:
            f_frame_set.add(cmds.findKeyframe(_node, w="first"))
            l_frame_set.add(cmds.findKeyframe(_node, w="last"))

        f_frame = min(f_frame_set)
        l_frame = max(l_frame_set)

        trans_list = ["translateX", "translateY", "translateZ"]
        rot_list = ["rotateX", "rotateY", "rotateZ"]

        for _node in reversed(nodes):
            for _attr in rot_list:
                cmds.setKeyframe(str(_node)+"."+_attr, v=0, t=(f_frame-5))
            if _node == root_obj:
                for _attr in trans_list:
                    cmds.setKeyframe(str(_node)+"."+_attr, v=0, t=(f_frame-5))

        # Constrainパート
        cmds.currentTime(f_frame-5)
        results = {}
        consts = []

        for table_dict in self.table_list:
            const = table_dict["const"]
            rh = table_dict["RH"]
            mc = table_dict["MC"]
            const_type, const = self.exec_const(const, rh, mc)
            consts.extend(const)
            results.setdefault(const_type, []).append(rh)

        cmds.currentTime(f_frame)

        # Bakeパート
        cmds.cycleCheck(e=False)
        bakelist = []
        # parent
        if "parent" in results:
            attrs = trans_list + rot_list
            bakelist.extend(self._cana_composer(results["parent"], attrs))
        # orient
        if "orient" in results:
            attrs = rot_list
            bakelist.extend(self._cana_composer(results["orient"], attrs))
        # point
        if "point" in results:
            attrs = trans_list
            bakelist.extend(self._cana_composer(results["point"], attrs))

        cmds.bakeResults(bakelist, t=(f_frame, l_frame), ral=True, sm=1)
        cmds.cycleCheck(e=True)
        cmds.delete(consts)

    def exec_const(self, const_type, rh, mc):
        if const_type == "parentConstraint":
            return 'parent', cmds.parentConstraint(mc, rh, mo=True)
        elif const_type == "orientConstraint":
            return 'orient', cmds.orientConstraint(mc, rh, mo=True)
        elif const_type == "pointConstraint":
            return 'point', cmds.pointConstraint(mc, rh, mo=True)

    def _cana_composer(self, objs, attrs):
        create_items = []
        for const in objs:
            for attr in attrs:
                create_items.append(const+"."+attr)
        print create_items
        return create_items

    def _get_nsObjs(self, NS):
        currentNS = cmds.namespaceInfo(cur=True)
        cmds.namespace(set=NS)
        nsObjs = cmds.namespaceInfo(lod=True)
        cmds.namespace(set=currentNS)
        return nsObjs

def main():
    x = GUI()
