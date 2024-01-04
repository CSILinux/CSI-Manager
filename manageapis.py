import functools
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox, QLabel, QVBoxLayout, QDialog, QPushButton, QHBoxLayout, QSpinBox, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

import json, sys
import os, subprocess

# libs for encrypting APIKeys
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from csilibs.auth import encrypt, decrypt, gen_key
from csilibs.utils import pathme
from csilibs.data import  apiKeys
from csilibs.gui import percentSize
import qdarktheme

# Global var and function ###########
enc_pass=''
title_icon=pathme("assets/icons/csi_black.ico")
# You can add new tools_support and write their implementation in the Ui_MainWindow.save_api_data &  Ui_MainWindow.wipe_data 
tools_support=["OSINT-Search", "Recon-NG", "Spiderfoot", "theHarvester", "CSI UserSearch"]


def show_message_box(title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
    
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setWindowIcon(QtGui.QIcon(title_icon))
    msg_box.setText(message)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(buttons)
    result = msg_box.exec_()
    return result
    

###################################### 
# Setting up Table with API Data
class TableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(TableModel, self).__init__()
        self._data = data
        self.header_labels = ["Name", "API Keys", "Tools Supported"]  # New header names

    def data(self, index, role):
        if role == Qt.DisplayRole:
            try:
                if type(self._data[index.row()][index.column()]) == list:
                    return ", ".join(self._data[index.row()][index.column()])
                else:
                    return self._data[index.row()][index.column()]
            except IndexError:
                return ''
        
    
    def setData(self, index, value, role):
        if role == QtCore.Qt.EditRole:
            row = index.row()
            column = index.column()
            
            # Preserve the existing data for other columns
            if column != 1:
                return False
            if not value:
                return False
            
            self._data[row][column] = value
            self.dataChanged.emit(index, index)  # Emit signal for data change
            return True
        
    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self._data[0])
    
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            if section < len(self.header_labels):
                return self.header_labels[section]
        return super(TableModel, self).headerData(section, orientation, role)

    def flags(self, index):
        if index.column() == 1:  # Column 2
            return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        return super(TableModel, self).flags(index)

# Dialog box for editing/removing API entry
class newAPIDialog(QDialog):
    def __init__(self, mainObj, opt="remove"):
        super().__init__()
        self.mainObj = mainObj
        self.setWindowIcon(QtGui.QIcon(title_icon))
        if opt == 'add':            
            self.setWindowTitle("Add New API")
            self.addAPILabel = QLabel("Enter API Name(e.g name_api): ")
            self.addAPIInput = QLineEdit()
            self.addAPIBtn = QPushButton("Add New Entry")
            self.addAPIBtn.clicked.connect(self.create_new_entry)
        
            layout = QHBoxLayout()
            layout.addWidget(self.addAPILabel)
            layout.addWidget(self.addAPIInput)
            layout.addWidget(self.addAPIBtn)
            
            tool_layout = QVBoxLayout()
            toolLabel = QLabel("SUPPORTED BY: ")
            tool_layout.addWidget(toolLabel)
        
            self.chkbx_list = [QCheckBox() for i in range(0,len(tools_support))]
            for i, tool in enumerate(tools_support):
                self.chkbx_list[i].setText(tool)
                tool_layout.addWidget(self.chkbx_list[i])
        
        elif opt == 'remove':
            self.setWindowTitle("Remove Current API")
            self.rmAPILabel = QLabel("Enter the Entry Number:")
            self.rmAPIInput = QSpinBox()
            self.rmAPIInput.setRange(0,9999)
            self.rmAPIBtn = QPushButton("REMOVE ENTRY")
            
            self.rmAPIBtn.clicked.connect(self.remove_entry)

        
            layout = QHBoxLayout()
            layout.addWidget(self.rmAPILabel)
            layout.addWidget(self.rmAPIInput)
            layout.addWidget(self.rmAPIBtn)        
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        if opt == 'add':            
            main_layout.addLayout(tool_layout)
        self.setLayout(main_layout)

    def create_new_entry(self):
        # getting list of supported tools
        tools_sup = []
        for chkbx in self.chkbx_list:
            if chkbx.isChecked():
                tools_sup.append(chkbx.text())

        self.mainObj.api_keys_list.append([self.addAPIInput.text(),'',tools_sup])
        self.mainObj.save_api_data(f"Added {self.addAPIInput.text()} API Successfully!, Restart the program to see Changes.")
        self.close()
    
    def remove_entry(self):
        try:
            result = show_message_box("Confirmation", f"Do you want to Remove \"{self.mainObj.api_keys_list[self.rmAPIInput.value()-1][0]}\" API Entry?", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
            if result == QMessageBox.Yes:
                del self.mainObj.api_keys_list[self.rmAPIInput.value()-1]
                self.mainObj.save_api_data(f"Removed API Successfully!")
                self.close()
        except IndexError:
            show_message_box("Error",f"You have total {len(self.mainObj.api_keys_list)} entries", QMessageBox.Warning)

# MAIN Windows
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        self.changed_values = []  # to store the changes into the file
        api_keys = {}

        MainWindow.setObjectName("MainWindow")
        MainWindow.setWindowIcon(QtGui.QIcon(title_icon))

        MainWindow.setGeometry(0,0,*percentSize(app,44,90))    
        self.center(MainWindow)        
        
        MainWindow.resizeEvent = lambda event: self.adjust_size(MainWindow)

        #--------------- Setting up GUI elements ---------------
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.verticalLayoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.verticalLayoutWidget.setGeometry(0,0,*percentSize(MainWindow,100,95))
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)

        self.Heading = QtWidgets.QLabel(self.verticalLayoutWidget)
        self.Heading.setMaximumHeight(percentSize(MainWindow,0,5)[1])
        font = QtGui.QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.Heading.setAlignment(QtCore.Qt.AlignCenter)
        self.Heading.setObjectName("Heading")

        self.btns_layoutwidget = QtWidgets.QWidget(self.verticalLayoutWidget)
        self.btns_layoutwidget.setMaximumHeight(percentSize(MainWindow,0,10)[1])
        self.btns_layout  = QHBoxLayout(self.btns_layoutwidget)

        self.exitBtn = QtWidgets.QPushButton()
        self.exitBtn.setAutoDefault(False)
        self.exitBtn.setObjectName("exitBtn")
        self.exitBtn.clicked.connect(MainWindow.close)

        self.saveBtn = QtWidgets.QPushButton()
        self.saveBtn.setAutoDefault(False)
        self.saveBtn.setObjectName("saveBtn")
        self.saveBtn.clicked.connect(functools.partial(self.save_api_data,"Your API Keys saved successfully!"))

        self.wipeBtn = QtWidgets.QPushButton()
        self.wipeBtn.setAutoDefault(False)
        self.wipeBtn.setObjectName("wipeBtn")
        self.wipeBtn.clicked.connect(self.wipe_data)

        self.btns_layout.addWidget(self.wipeBtn)
        self.btns_layout.addWidget(self.saveBtn)
        self.btns_layout.addWidget(self.exitBtn)


        # Table View setup
        self.APIData = QtWidgets.QTableView(self.verticalLayoutWidget)
        self.APIData.setObjectName("APIData")
        self.APIData.setMaximumHeight(percentSize(MainWindow,0,80)[1])

        _, api_keys = apiKeys(enc_pass)

        self.api_keys_list = [[key, value["key"],value["inTools"]] for key, value in api_keys.items()]

        self.model = TableModel(self.api_keys_list)
        self.APIData.setModel(self.model)
        self.APIData.setColumnWidth(0,percentSize(MainWindow,20,0)[0])
        self.APIData.setColumnWidth(1,percentSize(MainWindow,43,0)[0])
        self.APIData.setColumnWidth(2,percentSize(MainWindow,25,0)[0])
        self.APIData.horizontalHeader().setStretchLastSection(True)

        self.model.dataChanged.connect(self.on_data_changed)  # Connect dataChanged signal to slot

        self.verticalLayout.addWidget(self.Heading)
        self.verticalLayout.addWidget(self.APIData)
        self.verticalLayout.addWidget(self.btns_layoutwidget)

        MainWindow.setCentralWidget(self.centralwidget)

        #------------ MENU BAR ------------
        
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, *percentSize(MainWindow,100,10)))
        self.menubar.setObjectName("menubar")
        
        self.menuEdit_API_Data = QtWidgets.QMenu(self.menubar)
        self.menuEdit_API_Data.setObjectName("menuEdit_API_Data")
        self.menuThemes = QtWidgets.QMenu(self.menubar)
        self.menuThemes.setObjectName("menuThemes")

        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionAdd_New_Entry = QtGui.QAction(MainWindow)
        self.actionAdd_New_Entry.setObjectName("actionAdd_New_Entry")
        self.actionRemove_Entry = QtGui.QAction(MainWindow)
        self.actionRemove_Entry.setObjectName("actionRemove_Entry")
        self.menuEdit_API_Data.addAction(self.actionAdd_New_Entry)
        self.menuEdit_API_Data.addAction(self.actionRemove_Entry)

        self.actionDark_Theme = QtGui.QAction(MainWindow)
        self.actionDark_Theme.setObjectName("actionDark_Theme")
        self.actionLight_Theme = QtGui.QAction(MainWindow)
        self.actionLight_Theme.setObjectName("actionLight_Theme")
        self.menuThemes.addAction(self.actionDark_Theme)
        self.menuThemes.addAction(self.actionLight_Theme)

        self.menubar.addAction(self.menuEdit_API_Data.menuAction())
        self.menubar.addAction(self.menuThemes.menuAction())

        self.actionAdd_New_Entry.triggered.connect(self.add_APIentry)
        self.actionRemove_Entry.triggered.connect(self.rm_APIentry)

        self.actionLight_Theme.triggered.connect(functools.partial(self.change_theme,"light"))
        self.actionDark_Theme.triggered.connect(functools.partial(self.change_theme,"dark"))

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "CSI Linux API Keys Management tool"))
        self.Heading.setText(_translate("MainWindow", "CSI Linux API Manager"))
        self.exitBtn.setText(_translate("MainWindow", "EXIT"))
        self.saveBtn.setText(_translate("MainWindow", "SAVE"))
        self.wipeBtn.setText(_translate("MainWindow", "WIPE DATA"))

        self.menuEdit_API_Data.setTitle(_translate("MainWindow", "Edit API Data"))
        self.actionAdd_New_Entry.setText(_translate("MainWindow", "Add New Entry"))
        self.actionAdd_New_Entry.setStatusTip(_translate("MainWindow", "Adds new entry in the API Data"))
        self.actionAdd_New_Entry.setShortcut(_translate("MainWindow", "Ctrl+A"))
        self.actionRemove_Entry.setText(_translate("MainWindow", "Remove Entry"))
        self.actionRemove_Entry.setStatusTip(_translate("MainWindow", "Removes by entry number from table."))
        self.actionRemove_Entry.setShortcut(_translate("MainWindow", "Ctrl+R"))

        self.menuThemes.setTitle(_translate("MainWindow", "Themes"))
        self.actionDark_Theme.setText(_translate("MainWindow", "Dark Theme"))
        self.actionLight_Theme.setText(_translate("MainWindow", "Light Theme"))

    #----------- ACTIONS  -----------
    def adjust_size(self, MainWindow):
        self.verticalLayoutWidget.setGeometry(0,0,*percentSize(MainWindow,100,95))
        self.Heading.setMaximumHeight(percentSize(MainWindow,0,5)[1])
        self.btns_layoutwidget.setMaximumHeight(percentSize(MainWindow,0,10)[1])
        self.APIData.setMaximumHeight(percentSize(MainWindow,0,80)[1])
        self.APIData.setColumnWidth(0,percentSize(MainWindow,20,0)[0])
        self.APIData.setColumnWidth(1,percentSize(MainWindow,43,0)[0])
        self.APIData.setColumnWidth(2,percentSize(MainWindow,25,0)[0])


        

    def on_data_changed(self, top_left, bottom_right):
        for row in range(top_left.row(), bottom_right.row() + 1):
            for column in range(top_left.column(), bottom_right.column() + 1):
                index = self.model.index(row, column)
                value = self.model.data(index, QtCore.Qt.DisplayRole)
                self.changed_values.append((row, column, value))

    def save_api_data(self, text):
        for i,j,keys in self.changed_values:
            self.api_keys_list[i][j] = keys

        update_api_keys = {item[0]: {"key":item[1],"inTools":item[2]} for item in self.api_keys_list}

        apiKeys(enc_pass, update_api_keys)
        
        #-------- Adding API keys in supported tools ----------------
        try:
            for api in self.api_keys_list:
                # api[0]=name, api[1]=key, api[2]=inTools

                if 'Recon-NG' in api[2]:    
                    subprocess.run(["sqlite3", "/home/csi/.recon-ng/keys.db", f'UPDATE keys SET Value = "{api[1]}" WHERE name="{api[0]}";'])
                if 'hades' in api[0]:  
                    subprocess.run(["sed", "-i", "s/atiikey=''/atiikey='$key'/g", "/opt/csitools/ProjectHades"])
                if 'Spiderfoot' in api[2]:
                    #improve it more
                    search_term = api[0]    # e.g. shodan_api = [shodan,api]  to search into spiderfoot config
                    # Using regex for finding the api name dynamically.
                    subprocess.run(["sed", "-i", "-E", f"s/(^sfp.*{search_term[0]}.*{search_term[1]}.*=)(key value)?/\\1{api[1]}/", "/opt/csitools/SpiderFoot.cfg"])
        
        except Exception as e:
            print("Got error during adding API data to supported tools!")
            print(e)
                
        
        show_message_box("Success",text)

    def wipe_data(self):
        result = show_message_box("Confirmation", "Do you want to proceed?", QMessageBox.Question, QMessageBox.Yes | QMessageBox.No)
        if result == QMessageBox.Yes:
            empty_api_keys = {item[0]: {"key":'',"inTools":item[2]} for item in self.api_keys_list}
            
            apiKeys(enc_pass, empty_api_keys)
            
            try:
                # Wiping data from supported tools using bash commands for better readability
                subprocess.run(["cp", "/opt/theHarvester/api-backup","/opt/theHarvester/api-keys.yaml"])
                subprocess.run(["cp", "/opt/OSINT-Search/osintSearch.config.back", "/opt/OSINT-Search/osintSearch.config.ini"])
                subprocess.run(["cp", "/opt/csitools/SpiderFoot.empty", "/opt/csitools/SpiderFoot.cfg"])
                for api in self.api_keys_list:  # api[0], first entry is name
                    if 'Recon-NG' in api[2]:
                        subprocess.run(["sqlite3", "/home/csi/.recon-ng/keys.db", f'UPDATE keys SET Value = "" WHERE name="{api[0]}";'])
            except Exception as e:
                print("Got error during wiping API data from supported tools!")
                print(e)

            show_message_box("Success","Data Removed From APIKeys, Recon-NG, theHarvester, OSINT-Search and SpiderFoot Successfully!",QMessageBox.Information)

            self.setupUi(MainWindow)
        
    
    def add_APIentry(self):
        dialog = newAPIDialog(self,"add")
        dialog.exec_()
        dialog.finished.connect(self.dialog_finished)
    
    def rm_APIentry(self):
        dialog = newAPIDialog(self,"remove")
        dialog.exec_()
        dialog.finished.connect(self.dialog_finished)

    def dialog_finished(self, result):
        print("reached here")
        self.setupUi(MainWindow)
    
    def change_theme(self, mode):
        if mode == 'dark':
            os.environ['CSI_DARK'] = 'enable'
            qdarktheme.setup_theme()
        else:
            os.environ['CSI_DARK'] = 'disable'
            qdarktheme.setup_theme("light")
    @staticmethod
    def center(window):
        qRect = window.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        window.move(qRect.topLeft())

if __name__ == "__main__":
    global app
    app = QtWidgets.QApplication(sys.argv)
    if os.environ.get("CSI_DARK") == 'enable':
        qdarktheme.setup_theme()
    else:
        qdarktheme.setup_theme("light")

    # Just to set the Icon on the password input
    MainWindow = QtWidgets.QMainWindow()
    MainWindow.setWindowIcon(QtGui.QIcon(title_icon))
    Ui_MainWindow.center(window=MainWindow)

    is_enc_file_avaiable, _ = apiKeys()
    # Creating encrypted APIKeys by setting up new password
    if not is_enc_file_avaiable:
        new_password, ok = QInputDialog.getText(MainWindow, "Set New Password", "Enter a New Password:", QLineEdit.Password)
        if ok:
            confirm_password, ok = QInputDialog.getText(MainWindow, "Set New Password", "ReEnter the Password:", QLineEdit.Password)
            if ok:
                if new_password != '' and new_password == confirm_password :
                    apiKeys(new_password)
                    show_message_box("Success","Password Set Successfully!",QMessageBox.Information)
                    enc_pass=new_password
                else:
                    msg_box = QMessageBox()
                    show_message_box("Error","Password Confirmation Failed!",QMessageBox.Warning)
                    exit()
            else:
                exit()
        else:
            exit()
    # Decrypting the APIKeys encrypted file, if it is present
    else:
        decrypt_password, ok = QInputDialog.getText(MainWindow, "Password to Decrypt", "Enter Password to decrypt the API Keys File:", QLineEdit.Password)
        if ok:
            try:
                # to check if password is correct
                apiKeys(decrypt_password)
                
                enc_pass=decrypt_password
            except ValueError:
                show_message_box("Error","Failed to Decrypt With this Password!",QMessageBox.Warning)
                exit()
            
    # Again declaring to set the location to center
    MainWindow = QtWidgets.QMainWindow()

    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()

    sys.exit(app.exec_())
