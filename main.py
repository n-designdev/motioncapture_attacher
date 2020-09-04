# -*- coding: utf-8 -*-
import os, sys
import re
import pprint
import maya.cmds as cmds

# ------------------------------
env_key = 'ND_TOOL_PATH_PYTHON'

ND_TOOL_PATH = os.environ.get(env_key, 'Y:/tool/ND_Tools/python')

for path in ND_TOOL_PATH.split(';'):
    path = path.replace('\\', '/')
    if path in sys.path:
        continue
    sys.path.append(path)
# ------------------------------------
import PySide2
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
import PySide2.QtWidgets as QtWidgets

from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import *

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

# class GUI(QtWidgets.QDialog):
class GUI (MayaQWidgetBaseMixin, QMainWindow):

    def __init__(self, parent=None):
        super(GUI, self).__init__(parent)
        self.ui_path = "Y:\\users\\env\\maya\\share\\nAnim\\motioncapture_attacher\\gui.ui"
        self.ui = QUiLoader().load(self.ui_path)
        self.setCentralWidget(self.ui)

        self.table_list = []
        self.ui_connect()
        self.ui_setup()
        self.setWindowTitle("Bake Motion Capture")
        self.setGeometry(300,300, 1114, 600)
        self.sub = SubWindow(self.ui)
        self.errorDialog = ErrorDialog()



    def ui_connect(self):
        self.ui.exec_button.clicked.connect(self.exec_button_clicked)
        self.ui.refresh_button.clicked.connect(self.refresh_button_clicked)
        self.ui.mc_popup.clicked.connect(self.mc_popup_clicked)
        self.ui.rh_popup.clicked.connect(self.rh_popup_clicked)

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
        self.ui.info_table.setColumnWidth(1, 260)

    def eventFilter(self, obj, event):
        pass


    def exec_button_clicked(self):
        rh_ns = self.ui.rh_ns_line.text()
        if rh_ns != "":
            rh_ns = rh_ns+":"
        mc_ns = self.ui.mc_ns_line.text()
        if mc_ns != "":
            mc_ns = mc_ns+":"

        rev_l = cmds.getAttr("{}method_ctrl.reverseFoot_L".format(rh_ns))
        rev_r = cmds.getAttr("{}method_ctrl.reverseFoot_R".format(rh_ns))
        if rev_l == True and rev_r == True:
            self.constrain_body(reverse=True)
        elif rev_l == False and rev_r == False:
            self.constrain_body()
        else:
            self.errorDialog.show()


    def refresh_button_clicked(self):
        new_table_list = []
        mc_ns = self.ui.mc_ns_line.text()
        rh_ns = self.ui.rh_ns_line.text()

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

        self.table_list = new_table_list
        self.set_table()

    def mc_popup_clicked(self):
        self.sub.show("mc")
        return

    def rh_popup_clicked(self):
        self.sub.show("rh")
        return

    def constrain_body(self, reverse=False):
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

        mc_ns = self.ui.mc_ns_line.text()
        rh_ns = self.ui.rh_ns_line.text()
        if mc_ns !="":
            mc_ns = mc_ns+":"
        if rh_ns !="":
            rh_ns = rh_ns+":"
        for table_dict in self.table_list:
            const = table_dict["const"]
            rh = table_dict["RH"]
            mc = table_dict["MC"]
            cmds.setAttr("{}.rotate".format(mc), 0,0,0)
            if mc.split(":")[-1]=="root_MCJNT":
                cmds.setAttr("{}.translate".format(mc), 0,0,0)
            if reverse == True:
                if mc.split(":")[-1] in ["ankle_MCJNT_L", "ankle_MCJNT_R"]:
                    print "########################"
                    cmds.parentConstraint("{}ankle_MCJNT_R".format(mc_ns), "{}reverseFoot_ctrl_R".format(rh_ns), mo=True)
                    cmds.parentConstraint("{}ankle_MCJNT_L".format(mc_ns), "{}reverseFoot_ctrl_L".format(rh_ns), mo=True)
                    print "########################"
                    continue
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

        sampling = float(self.ui.sampling_line.text())

        cmds.bakeResults(bakelist, t=(f_frame, l_frame), ral=True, sm=1, sb=sampling)
        cmds.cycleCheck(e=True)
        cmds.delete(consts)

    def exec_const(self, const_type, rh, mc):
        if const_type[-4:]=="[mo]":
            mo=True
        else:
            mo=False
        const_type = const_type.split("[")[0]

        if const_type == "parentConstraint":
            return 'parent', cmds.parentConstraint(mc, rh, mo=mo)
        elif const_type == "orientConstraint":
            return 'orient', cmds.orientConstraint(mc, rh, mo=mo)
        elif const_type == "pointConstraint":
            return 'point', cmds.pointConstraint(mc, rh, mo=mo)

    def _cana_composer(self, objs, attrs):
        create_items = []
        for const in objs:
            for attr in attrs:
                create_items.append(const+"."+attr)
        return create_items

    def _get_nsObjs(self, NS):
        currentNS = cmds.namespaceInfo(cur=True)
        cmds.namespace(set=NS)
        nsObjs = cmds.namespaceInfo(lod=True)
        cmds.namespace(set=currentNS)
        return nsObjs

class SubWindow(QWidget):
    def __init__(self, parent=None):
        self.parent_ui = parent
        self.w = QDialog(parent)
        self.qlist = QListWidget()
        self.set_namespace()
        self.qlist.clicked.connect(self.close)
        layout = QHBoxLayout()
        layout.addWidget(self.qlist)
        self.w.setLayout(layout)

    def set_namespace(self):
        ignore_list = ["UI", "shared"]
        ns_list = []
        for ns in cmds.namespaceInfo(lon=True):
            if not ns in ignore_list:
                self.qlist.addItem(ns)
    def show(self, mcrh):
        self.mcrh=mcrh
        pos = QtGui.QCursor().pos()
        self.w.move(pos.x()-330, pos.y()+15)
        if self.mcrh == "rh":
            self.w.setWindowTitle("Rig Namespace")
        elif self.mcrh == "mc":
            self.w.setWindowTitle("Motion Caputure Namespace")
        self.w.exec_()

    def close(self):
        cur_txt = self.qlist.currentItem().text()
        if self.mcrh == "rh":
            self.parent_ui.rh_ns_line.setText(cur_txt)
        elif self.mcrh == "mc":
            self.parent_ui.mc_ns_line.setText(cur_txt)
        self.w.close()

class ErrorDialog(QDialog):
    def __init__(self, parent=None):
        super(ErrorDialog, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.text = QLabel("method_ctrlのReverseFootは必ず両足揃えてください")
        self.button = QPushButton("Agree")
        layout = QVBoxLayout()
        layout.addWidget(self.text)
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.button.clicked.connect(self.close_dialog)

    def close_dialog(self):
        self.close()



def main():
    # app = QApplication(sys.argv)
    gui = GUI()
    gui.show()