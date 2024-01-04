#! /usr/bin/python3
# ----------------------------------------------------------------------------
# CSI Linux (https://www.csilinux.com)
# Author: Author
# Copyright (C) CSI Linux. All rights reserved.
#
# This software is proprietary and NOT open source. Redistribution,
# modification, or any other use of this code is strictly prohibited without
# the express written consent of CSI Linux.
#
# This software is provided "AS IS" without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose, and non-infringement. In no event shall
# the authors or copyright holders be liable for any claim, damages, or other
# liability, whether in an action of contract, tort or otherwise, arising from,
# out of or in connection with the software or the use or other dealings in
# the software.
#
# Paid support can be contracted through support@csilinux.com
# ----------------------------------------------------------------------------
import os, sys, shutil
import json
import logging
import functools, subprocess
import tempfile, zipfile, re
from PySide6.QtCore import QThread, Signal, QUrl, Qt, QSize, QRect, QMetaObject, QCoreApplication, QEvent
from PySide6.QtGui import QIcon, QPixmap, QFont, QGuiApplication,QAction
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStatusBar, QLabel, QTextEdit, QPlainTextEdit, QLineEdit, QInputDialog,
     QScrollArea, QDialog, QTabWidget, QMenuBar, QMenu, QCompleter, QTableView,
      QDockWidget, QRadioButton, QCheckBox, QFormLayout,QMessageBox, QGridLayout, QFileDialog,
      QStackedWidget
)

from csilibs.utils import pathme, auditme, get_current_timestamp, reportme
from csilibs.config import create_case_folder
from csilibs.assets import icons, ui
from csilibs.gui import percentSize
from csilibs.data import agencyData, apiKeys, Templates, KeywordLists

import qdarktheme

from manageapis import Ui_MainWindow, TableModel, show_message_box, newAPIDialog


enc_pass = ''
#---------------------------------------------- MainWindow ------------------------------------------------#
class CSIMainWindow(QMainWindow):
    """The main window class for the CSI application."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle(f"CSI Manager")
        self.setWindowIcon(QIcon(icons.CSI_BLACK))
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.application = None
        # self.setFixedSize(*percentSize("app",70,90))

        #-------------------------- MENU BAR --------------------------#
        self.menubar = QMenuBar(self)
        self.menubar.setObjectName("menubar")
        self.setMenuBar(self.menubar)
        
        # menu list
        self.menuList = QMenu(self.menubar)
        self.menuList.setTitle("Menu List")
        
        self.themeMenu = QMenu(self.menubar)
        self.themeMenu.setTitle("Themes")
        
        # menu options within menu list
        self.menuOption = QAction(self)
        self.menuOption.setText("Menu Option")
        self.menuOption.setStatusTip("Template status Tip")
        self.menuOption.setShortcut("Ctrl+S")
        self.menuList.addAction(self.menuOption)

        self.fullscreenOption = QAction(self)
        self.fullscreenOption.setShortcut("Ctrl+F")
        self.fullscreenOption.setText("FullScreen Toggle")
        self.fullscreenOption.setStatusTip("Click to move to and from FullScreen")
    
        self.menuList.addAction(self.fullscreenOption)

        self.menubar.addAction(self.menuList.menuAction())

        self.darkTheme = QAction(self)
        self.darkTheme.setText("Dark Theme")
        self.darkTheme.setStatusTip("Enable Dark theme")
        self.themeMenu.addAction(self.darkTheme)
        self.lightTheme = QAction(self)
        self.lightTheme.setText("Light Theme")
        self.lightTheme.setStatusTip("Enable Light theme")
        self.themeMenu.addAction(self.lightTheme)

        self.menubar.addAction(self.themeMenu.menuAction())

        self.darkTheme.triggered.connect(lambda: self.theme_change("dark"))
        self.lightTheme.triggered.connect(lambda: self.theme_change("light"))
        print("fullscreen",self.isFullScreen())
        self.fullscreenOption.triggered.connect(lambda: self.showFullScreen() if not self.isFullScreen() else self.showNormal())

    def theme_change(self, theme_color):
        qdarktheme.setup_theme(theme_color)

    def center(self):
        qRect = self.frameGeometry()
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())

    def set_application(self, application):
        """Set the application instance."""
        self.application = application
        # set size
        self.setGeometry(0,0, *percentSize(self.application,70,90))
        self.menubar.setGeometry(QRect(0, 0, *percentSize(self.application,95,10)))
        self.center()
        

    def update_status(self, message):
        """Update the status bar with the given message."""
        self.status_bar.showMessage(message)  


#---------------------------------------------- TabWidget ------------------------------------------------#
# give dict of tabname: WidgetObject as an argument
class BaseCSITabs(QDialog):
    def __init__(self, widgets_dict):
        super().__init__()
        tabwidget = QTabWidget()
    
        # Create tabs
        for tab_name, widget in widgets_dict.items():
            tabwidget.addTab(widget, tab_name)        

        vbox = QVBoxLayout()
        vbox.addWidget(tabwidget)
        
        self.setLayout(vbox)

#---------------------------------------------- Widgets ------------------------------------------------#

class AgencyInfoTab(QWidget):
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window = main_window
        self.main_layout = QVBoxLayout()
        print("this is agency tab mainwindow",dir(self.main_window))
        self.Heading = QLabel("Agency Info")
        self.Heading.setMaximumHeight(percentSize(self.main_window,0,5)[1])
        font = QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(Qt.LeftToRight)
        self.Heading.setAlignment(Qt.AlignCenter)


        # Form 
        with open(agencyData.file_path, 'r') as f:
            self.agency_info = json.load(f)

        self.labelArray = [QLabel() for i in self.agency_info]
        self.inputArray = [QLineEdit() for i in self.agency_info]

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(20,20,20,20)
        self.form_layout.setHorizontalSpacing(percentSize(self.main_window,0,5)[1])
        self.form_layout.setVerticalSpacing(percentSize(self.main_window,0,2)[1])

        for i, (label, data) in enumerate(self.agency_info.items()):
            if label != 'cases_folder':
                self.labelArray[i].setText(f"<b>{label.replace('_', ' ').title()}</b>")
                self.inputArray[i].setText(data)
                
                # After pressing enter move focus to next text box except on last text box
                if i != len(self.inputArray) - 1: 
                    self.inputArray[i].editingFinished.connect(self.inputArray[i+1].setFocus)

                self.form_layout.setWidget(i, QFormLayout.LabelRole, self.labelArray[i])
                self.form_layout.setWidget(i, QFormLayout.FieldRole, self.inputArray[i])


        # Buttons 
        self.btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.save_btn.clicked.connect(self.saveAgencyData)

        self.undo_btn = QPushButton("Undo Changes")
        self.undo_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.undo_btn.clicked.connect(self.populateAgain)
        
        self.btn_layout.addWidget(self.save_btn)
        self.btn_layout.addWidget(self.undo_btn)

        
        self.main_layout.addWidget(self.Heading)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.btn_layout)
        self.setLayout(self.main_layout)

    def saveAgencyData(self):
        result = QMessageBox(QMessageBox.Information,"Confirmation", "Do you want to Save your Changes?",QMessageBox.Yes|QMessageBox.No, self.main_window).exec_()
        if result == QMessageBox.Yes:
            for label, input in zip(self.agency_info.keys(), self.inputArray):
                self.agency_info[label] = input.text()  
            
            with open(agencyData.file_path, 'w') as f:
                json.dump(self.agency_info, f)
    
    def populateAgain(self):
        result = QMessageBox(QMessageBox.Information,"Confirmation", "Do you want to Undo all your Changes?",QMessageBox.Yes|QMessageBox.No, self.main_window).exec_()
        if result == QMessageBox.Yes:
            for label, input in zip(self.agency_info.keys(), self.inputArray):
                input.setText(self.agency_info[label])
                
# Used for 2 tabs: Keywordlists & Sites files
class sysFileEditTab(QWidget):
    def __init__(self, main_window, heading, file_dir, files_icon, file_exts, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.main_window = main_window
        self.file_dir = file_dir
        self.files_icon = files_icon
        self.file_exts = file_exts
        self.main_layout = QVBoxLayout()

        self.Heading = QLabel(heading)
        self.Heading.setMaximumHeight(percentSize(self.main_window,0,5)[1])
        font = QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(Qt.LeftToRight)
        self.Heading.setAlignment(Qt.AlignCenter)
        
        self.img_grid = QGridLayout()
        self.createGrid()    
        
        self.btn_layout = QHBoxLayout()

        self.del_btn = QPushButton()
        self.del_btn.setText(
            "Start Deleting" if not self.del_btn.isChecked() else "Stop Deleting"
        )
        self.del_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.del_btn.setCheckable(True)
        self.del_btn.toggled.connect(self.deleteFiles)

        self.create_btn = QPushButton("Create New File")
        self.create_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.create_btn.clicked.connect(self.createFile)

        self.export_btn = QPushButton("Export File")
        self.export_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.export_btn.clicked.connect(functools.partial(self.exportFile, self.file_exts))
        
        self.btn_layout.addWidget(self.del_btn)
        self.btn_layout.addWidget(self.create_btn)
        self.btn_layout.addWidget(self.export_btn)


        self.main_layout.addWidget(self.Heading)
        self.main_layout.addLayout(self.img_grid)
        self.main_layout.addLayout(self.btn_layout)
        self.setLayout(self.main_layout)

    def deleteFiles(self):
        if self.del_btn.isChecked() == True:
            self.del_btn.setText("Stop Deleting")
            self.del_mode = True

        else:
            self.del_btn.setText("Start Deleting")
            self.del_mode = False
        
        for img in self.img_btns:
            img.setStatusTip("Double Click to Open the File" if not self.del_btn.isChecked() else "Click to Delete the File")

    def createFile(self):
        while True:
            file_name, ok = QInputDialog.getText(self.main_window, "File Name", "Enter Name for the new File:")
            if ok:
                file_path = os.path.join(self.file_dir,file_name)
                if os.path.exists(file_path):
                    QMessageBox(QMessageBox.Critical,"Error", f"{file_name} already exists!", QMessageBox.Ok, self.main_window).exec_()
                else:
                    break
            else:
                return 0
        file_content, ok = QInputDialog.getMultiLineText(self.main_window, "File Content", "Enter the list of keywords to be written in the file:")
        if ok:
            with open(file_path, 'w') as f:
                f.write(file_content)

            self.img_btns.append(QPushButton())
            self.img_labels.append(QLabel(file_name))
            self.img_blocks.append(QVBoxLayout())
            index = len(self.img_blocks) - 1
            self.addItemToGrid(index , self.img_btns[index])

            QMessageBox(QMessageBox.Information,"Success", f"{file_name} created Successfully!", QMessageBox.Ok, self.main_window).exec_()


    def exportFile(self, file_extensions):
        file_string = ' '.join(['*.' + ext for ext in file_extensions])
        files_path, _ = QFileDialog.getOpenFileNames(self.main_window, "Export File", "", f"Data Files ({file_string})")

        for src_file in files_path:
            file_name = os.path.basename(src_file)
            dest_file = os.path.join(self.file_dir, file_name)
            if os.path.exists(dest_file):
                QMessageBox(QMessageBox.Critical,"Error", f"{file_name} already exists!", QMessageBox.Ok, self.main_window).exec_()
                files_path.remove(src_file)
                continue
            shutil.copy(src_file, dest_file)

            self.img_btns.append(QPushButton())
            self.img_labels.append(QLabel(file_name))
            self.img_blocks.append(QVBoxLayout())
            index = len(self.img_blocks) - 1
            self.addItemToGrid(index , self.img_btns[index])
        
        if files_path: 
            QMessageBox(QMessageBox.Information,"Success", f"Files Exported Successfully", QMessageBox.Ok, self.main_window).exec_()
            print("Files Exported Successfully")

    def imgAction(self, obj_index):
        file_name = self.img_labels[obj_index].text()
        file_path = os.path.join(self.file_dir,file_name)
        print(f"File: {file_path}")

        if self.del_btn.isChecked() == True:
            result = QMessageBox(QMessageBox.Warning,"Confirmation", f"Do you want to Delete {file_name}?",QMessageBox.Yes|QMessageBox.No, self.main_window).exec_()
            if result == QMessageBox.Yes:
                os.remove(file_path)
                self.img_btns[obj_index].deleteLater()
                self.img_labels[obj_index].deleteLater()
                self.img_grid.removeItem(self.img_blocks[obj_index])
                self.img_blocks[obj_index].setParent(None)
                self.img_blocks[obj_index].deleteLater()

                del self.img_btns[obj_index]
                del self.img_labels[obj_index]
                del self.img_blocks[obj_index]
                self.clearGridLayout()
                self.createGrid()
                print('File Deleted!')
        
        else:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS or Linux
                opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
                subprocess.run([opener, file_path])
            else:
                print('Error: Unsupported operating system.')

    def addItemToGrid(self, i, img):
        img.setIcon(QIcon(QPixmap(self.files_icon)))
        img.setObjectName(self.img_labels[i].text())
        icon_width = percentSize(main_window,10,0)[0]
        img.setIconSize(QSize(icon_width, icon_width))
        img.setStatusTip("Double Click to Open the File")
        img.setFlat(True)

        self.img_blocks[i].addWidget(img)
        self.img_blocks[i].setObjectName(self.img_labels[i].text())
        self.img_labels[i].setMaximumHeight(percentSize(self.main_window,0,3)[1])
        self.img_labels[i].setAlignment(Qt.AlignCenter)
        self.img_blocks[i].addWidget(self.img_labels[i])
        img.clicked.connect(functools.partial(self.imgAction, i))

        # dynamic grid assign
        row = int( i / self.img_per_row )
        col = i % self.img_per_row
        self.img_grid.addLayout(self.img_blocks[i],row,col)
    
    def clearGridLayout(self):
        while self.img_grid.count() > 0:
            item = self.img_grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
            elif item.layout():
                layout = item.layout()
                self.clearLayout(layout)

    def clearLayout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
            elif item.layout():
                self.clearLayout(item.layout())

    def createGrid(self):
        # Files in Grid
        keyword_files = os.listdir(self.file_dir)

        self.img_btns = [QPushButton() for i in keyword_files]
        self.img_labels = [QLabel(name) for name in keyword_files]
        self.img_blocks = [QVBoxLayout() for i in keyword_files]

        self.img_per_row = 6
        for i, img in enumerate(self.img_btns):
            self.addItemToGrid(i, img)


# dialog box used by templateTab()

class varValTemplDialog(QDialog):
    def __init__(self,main_window, file_dir, file_name, *args, **kwargs):
        super().__init__()
        self.setWindowTitle("Fill the template")
        self.main_window = main_window
        self.main_layout = QVBoxLayout()
        self.setMaximumHeight(percentSize(main_window,0,100)[1])

        self.Heading = QLabel(file_name)
        self.Heading.setMaximumHeight(percentSize(main_window,0,5)[1])
        font = QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(Qt.LeftToRight)
        self.Heading.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.Heading)
        
        self.file_path = os.path.join(file_dir,file_name)
        
        self.var_names, self.imgs_loc = self.getVarNamesImgDir(self.file_path)
        
        self.input_layout = QHBoxLayout()
        # var val form

        self.labelArray = [QLabel(names) for names in self.var_names]
        self.inputArray = [QLineEdit() for i in self.var_names]

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.form_layout = QFormLayout(self.scroll_widget)
        self.form_layout.setContentsMargins(20,20,20,20)
        self.form_layout.setHorizontalSpacing(10)
        self.form_layout.setVerticalSpacing(10)
        self.scroll_area.setWidget(self.scroll_widget)

        for i, label in enumerate(self.var_names):
            if label != 'cases_folder':          
                if label.endswith('list'):
                    self.inputArray[i] = QTextEdit()      
                # After pressing enter move focus to next text box except on last text box
                elif i != len(self.inputArray) - 1: 
                    self.inputArray[i].editingFinished.connect(self.inputArray[i+1].setFocus)

                self.form_layout.setWidget(i, QFormLayout.LabelRole, self.labelArray[i])
                self.form_layout.setWidget(i, QFormLayout.FieldRole, self.inputArray[i])
        
        self.input_layout.addWidget(self.scroll_area)

        # images to replace
        self.scroll_area2 = QScrollArea()
        self.scroll_area2.setWidgetResizable(True)
        self.scroll_widget2 = QWidget()
        self.img_layout = QVBoxLayout(self.scroll_widget2)
        self.scroll_area2.setWidget(self.scroll_widget2)
        
        self.img_btns = [QPushButton() for i in self.imgs_loc]

        self.img_dict = {}
        for i, img in enumerate(self.img_btns):
            print(self.imgs_loc[i])
            img.setIcon(QIcon(QPixmap(self.imgs_loc[i])))
            img.setObjectName(self.imgs_loc[i])
            icon_width = percentSize(main_window,10,0)[0]
            img.setIconSize(QSize(icon_width, icon_width))
            img.setStatusTip("Click to Replace the File")
            img.setFlat(True)
            img.clicked.connect(functools.partial(self.addNewImg, i))

            self.img_layout.addWidget(img)

        self.input_layout.addWidget(self.scroll_area2)

        self.main_layout.addLayout(self.input_layout)
        

        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.setMinimumHeight(percentSize(self.main_window,0,5)[1])
        self.generate_btn.clicked.connect(self.saveReport)
        self.main_layout.addWidget(self.generate_btn)

        self.setLayout(self.main_layout)

    def saveReport(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_dialog = QFileDialog()
        file_dialog.setOptions(options)

        file_ext = os.path.splitext(self.file_path)[1]
        dest_path, _ = file_dialog.getSaveFileName(self, "Save File", "", f"Text Files (*{file_ext})")

        if dest_path:
            # Perform saving operation with the chosen dest_path
            print("File saved:", dest_path)

        var_val_dict = {}
        for i, val in enumerate(self.inputArray):
            if not isinstance(val, QTextEdit):
                if not val.text() == '':
                    var = self.labelArray[i].text()
                    var_val_dict[var] = val.text()
            else:
                if not val.toPlainText() == '':
                    var = self.labelArray[i].text()
                    var_val_dict[var] = val.toPlainText()
                print(var_val_dict)
        reportme(self.file_path,dest_path,var_val_dict, self.img_dict)
        QMessageBox(QMessageBox.Information,"Success", f"Successfully Generated your Report at {dest_path}",QMessageBox.Ok, self.main_window).exec_()
        if os.name == 'nt':  # Windows
            os.startfile(dest_path)
        elif os.name == 'posix':  # macOS or Linux
            opener = 'open' if sys.platform == 'darwin' else 'xdg-open'
            subprocess.run([opener, dest_path])
        else:
            print('Error: Unsupported operating system.')
    
    def addNewImg(self, index):
        file_path, _ = QFileDialog.getOpenFileName(self.main_window, "Add an Image", "", f"Image Files (*.jpg *.jpeg *.png)")
        if file_path:
            self.img_btns[index].setIcon(QIcon(QPixmap(file_path)))
            self.img_dict[index] = file_path
    
    
    def getVarNamesImgDir(self, file_path):
        # for odt files
        if file_path.lower().endswith(".odt"):
            file_loc = ['styles.xml', 'content.xml']
            img_dir = 'Pictures'
        # for docx files            
        elif file_path.lower().endswith(".docx"):
            file_loc = ['word/header1.xml', 'word/footer1.xml', 'word/document.xml']
            img_dir = 'word/media'
        
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(file_path, 'r') as templ_file:
            templ_file.extractall(self.temp_dir)
        
        var_names = []
        for file in file_loc:
            file_path = os.path.join(self.temp_dir, file)
            with open(file_path, 'r',encoding='utf-8') as content_file:
                content = content_file.read()
                content_file.close()
            
            pattern = r'&lt;(.*?)&gt;'
            print(re.findall(pattern, content))
            var_names.extend(re.findall(pattern, content))

        imgs_loc = []
        img_path = os.path.join(self.temp_dir, img_dir)
        if os.path.exists(img_path):
            for img in os.listdir(img_path):
                imgs_loc.append(os.path.join(img_path, img))
        
        return self.remove_duplicates(var_names), imgs_loc

    def closeEvent(self, event):
        super(varValTemplDialog, self).closeEvent(event)
        shutil.rmtree(self.temp_dir)
    
    @staticmethod
    def remove_duplicates(lst):
        new_list = []
        seen = set()  

        for item in lst:
            if item not in seen:
                new_list.append(item)
                seen.add(item)

        return new_list



class templateTab(sysFileEditTab):
    def __init__(self, main_window, heading, file_dir, file_exts, *args, **kwargs):
        super().__init__(main_window, heading, file_dir, None, file_exts, *args, **kwargs)
        
        # Removes extra items from super class
        del self.files_icon
        self.btn_layout.removeWidget(self.create_btn)  # Remove the button from the layout
        self.create_btn.deleteLater()  # Destroy the button widget

        # adding context menu to buttons
        self.context_menus = [QMenu(self) for i in self.img_btns]

        for i, img in enumerate(self.img_btns):
            img.setContextMenuPolicy(Qt.CustomContextMenu)
            img.customContextMenuRequested.connect(functools.partial(self.on_context_menu,i,img))
            self.context_menus[i].addAction(QAction("Fill Template", self, triggered=functools.partial(self.fillTemplDialogue,i)))
        # self.img_btns[0].installEventFilter(self)

    def on_context_menu(self,index,img, point):
        # show context menu
        self.context_menus[index].exec_(img.mapToGlobal(point))

    def fillTemplDialogue(self, index):
        file_name = self.img_labels[index].text()

        dialog = varValTemplDialog(self.main_window,self.file_dir,file_name)
        dialog.exec_()

    def addItemToGrid(self, i, img):
        file_name = self.img_labels[i].text()
        if file_name.lower().endswith(".docx"):
            img.setIcon(QIcon(QPixmap(ui.FILE_DOCX)))
        elif file_name.lower().endswith(".odt"):
            img.setIcon(QIcon(QPixmap(ui.FILE_ODT)))

        img.setObjectName(file_name)
        icon_width = percentSize(main_window,10,0)[0]
        img.setIconSize(QSize(icon_width, icon_width))
        img.setStatusTip("Double Click to Open the File")
        img.setFlat(True)

        self.img_blocks[i].addWidget(img)
        self.img_blocks[i].setObjectName(file_name)
        self.img_labels[i].setMaximumHeight(percentSize(self.main_window,0,3)[1])
        self.img_labels[i].setAlignment(Qt.AlignCenter)
        self.img_blocks[i].addWidget(self.img_labels[i])

        img.clicked.connect(functools.partial(self.imgAction, i))

        # dynamic grid assign
        row = int( i / self.img_per_row )
        col = i % self.img_per_row
        self.img_grid.addLayout(self.img_blocks[i],row,col)

class APIKeys(QWidget):
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window = main_window
        self.main_layout = QVBoxLayout()
        self.enc_pass = ''
        self.changed_values = []  # to store the changes into the file
        api_keys = {}
        self.Heading = QLabel("CSI Linux API Manager")
        self.Heading.setMaximumHeight(percentSize(main_window,0,5)[1])
        font = QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(Qt.LeftToRight)
        self.Heading.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.Heading)

        self.setLayout(self.main_layout)
        
        self.btns_layout  = QHBoxLayout()

        self.exitBtn = QPushButton('EXIT')
        self.exitBtn.setAutoDefault(False)
        self.exitBtn.setObjectName("exitBtn")
        self.exitBtn.clicked.connect(self.main_window.close)

        self.saveBtn = QPushButton("SAVE")
        self.saveBtn.setAutoDefault(False)
        self.saveBtn.setObjectName("saveBtn")
        self.saveBtn.clicked.connect(functools.partial(self.save_api_data,"Your API Keys saved successfully!"))

        self.wipeBtn = QPushButton("WIPE DATA")
        self.wipeBtn.setAutoDefault(False)
        self.wipeBtn.setObjectName("wipeBtn")
        self.wipeBtn.clicked.connect(self.wipe_data)

        self.btns_layout.addWidget(self.wipeBtn)
        self.btns_layout.addWidget(self.saveBtn)
        self.btns_layout.addWidget(self.exitBtn)
        
        # Table View setup
        self.APIData = QTableView()
        self.APIData.setObjectName("APIData")
        self.APIData.setMaximumHeight(percentSize(self.main_window,0,80)[1])

    
        self.main_layout.addWidget(self.Heading)
    
        is_enc_file, api_keys = apiKeys(self.enc_pass)

        self.stacked_widget = QStackedWidget()

        ## New password form
        self.newpass_form_widget = QWidget()
        self.newpass_form_layout = QVBoxLayout()

        # Label and input field for the new password
        self.label_new_password = QLabel("New Password:")
        self.input_new_password = QLineEdit()
        self.input_new_password.setEchoMode(QLineEdit.Password)  # Hide password input
        self.newpass_form_layout.addWidget(self.label_new_password)
        self.newpass_form_layout.addWidget(self.input_new_password)

        # Label and input field for repeating the password
        self.label_repeat_password = QLabel("Repeat Password:")
        self.input_repeat_password = QLineEdit()
        self.input_repeat_password.setEchoMode(QLineEdit.Password)  # Hide password input
        self.newpass_form_layout.addWidget(self.label_repeat_password)
        self.newpass_form_layout.addWidget(self.input_repeat_password)

        # Button to submit the form
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.validate_passwords)
        self.newpass_form_layout.addWidget(self.submit_button)
        self.newpass_form_widget.setLayout(self.newpass_form_layout)
        # self.main_layout.addLayout(self.newpass_form_layout)
        
        # Password to decrypt
        self.pass_form_widget = QWidget()
        self.pass_form_layout = QVBoxLayout()

        self.label_password = QLabel("Enter Password to Decrypt API Keys file:")
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)  # Hide password input
        self.pass_form_layout.addWidget(self.label_password)
        self.pass_form_layout.addWidget(self.input_password)

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.decrypt_apikeys)
        self.pass_form_layout.addWidget(self.submit_button)
        # self.main_layout.addLayout(self.pass_form_layout)
        self.pass_form_widget.setLayout(self.pass_form_layout)


        # API Keys table 
        self.data_widget = None        
        
        if is_enc_file:
            self.stacked_widget.addWidget(self.pass_form_widget)
            self.stacked_widget.addWidget(self.newpass_form_widget)
        else:
            self.stacked_widget.addWidget(self.newpass_form_widget)
            self.stacked_widget.addWidget(self.pass_form_widget)
        # elif enc_pass == '':
            
        # else: 

    
        self.main_layout.addWidget(self.stacked_widget)
        # self.main_layout.addLayout(self.btns_layout)

        self.setLayout(self.main_layout)
    
    def decrypt_apikeys(self):
        password = self.input_password.text()
        
        try:
            apiKeys(password)
            show_message_box("Success","Decrypted API Keys with Successfully.",QMessageBox.Information)
            self.enc_pass = password
            # self.__init__(self.main_window, password)
            if self.data_widget is None:

                self.data_widget = QWidget()
                self.data_layout = QVBoxLayout()
                is_enc_file, api_keys = apiKeys(password)
                print('tester data', api_keys)
                self.api_keys_list = [[key, value["key"],value["inTools"]] for key, value in api_keys.items()]

                self.model = TableModel(self.api_keys_list)
                self.APIData.setModel(self.model)
                self.APIData.setColumnWidth(0,percentSize(self.main_window,20,0)[0])
                self.APIData.setColumnWidth(1,percentSize(self.main_window,43,0)[0])
                self.APIData.setColumnWidth(2,percentSize(self.main_window,25,0)[0])
                self.APIData.horizontalHeader().setStretchLastSection(True)

                self.model.dataChanged.connect(self.on_data_changed)  # Connect dataChanged signal to slot
                self.data_layout.addWidget(self.APIData)
                self.data_layout.addLayout(self.btns_layout)
                self.data_widget.setLayout(self.data_layout)
                self.stacked_widget.addWidget(self.data_widget)
                
                self.stacked_widget.setCurrentWidget(self.data_widget)
                
        except ValueError:
            show_message_box("Error","Failed to Decrypt the API keys, Invalid Password",QMessageBox.Critical)
            

    def validate_passwords(self):
        new_password = self.input_new_password.text()
        repeat_password = self.input_repeat_password.text()

        if new_password == repeat_password:
            apiKeys(new_password)
            show_message_box("Success","Encrypted API Keys with new Password",QMessageBox.Information)
            print("Passwords match!")
            # self.__init__(self.main_window)
            self.stacked_widget.setCurrentWidget(self.pass_form_widget)
            
        else:
            print("Passwords do not match. Please try again.")

    def on_data_changed(self, top_left, bottom_right):
        for row in range(top_left.row(), bottom_right.row() + 1):
            for column in range(top_left.column(), bottom_right.column() + 1):
                index = self.model.index(row, column)
                value = self.model.data(index, Qt.DisplayRole)
                self.changed_values.append((row, column, value))
                print('test changes:',self.changed_values)

    def save_api_data(self, text):
        for i,j,keys in self.changed_values:
            self.api_keys_list[i][j] = keys

        update_api_keys = {item[0]: {"key":item[1],"inTools":item[2]} for item in self.api_keys_list}

        apiKeys(self.enc_pass, update_api_keys)
        
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

            self.setupUi(self.main_window)
        
    
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
        self.__init__(self.main_window)
    
    def change_theme(self, mode):
        if mode == 'dark':
            os.environ['CSI_DARK'] = 'enable'
            qdarktheme.setup_theme()
        else:
            os.environ['CSI_DARK'] = 'disable'
            qdarktheme.setup_theme("light")

class BaseCSIWidget(QWidget):
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.main_window = main_window
        self.main_layout = QVBoxLayout()

        self.Heading = QLabel("Agency Info")
        self.Heading.setMaximumHeight(percentSize(main_window,0,5)[1])
        font = QFont()
        font.setFamily("Bahnschrift")
        font.setPointSize(14)
        self.Heading.setFont(font)
        self.Heading.setLayoutDirection(Qt.LeftToRight)
        self.Heading.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.Heading)

        self.setLayout(self.main_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Create the main window
    main_window = CSIMainWindow()

    widget1 = AgencyInfoTab(main_window)
    widget2 = sysFileEditTab(main_window, "Keyword Lists", KeywordLists.dir_path, ui.PAGE, ['txt'])     
    
    # Siteslists, conveted into sqlitedb
    # widget3 = sysFileEditTab(main_window, "Sites Lists", pathme("sites"), ui.LAPTOP, ['json'])    
    
    widget4 = templateTab(main_window, "Report Templates", Templates.dir_path , ['docx','odt']) 
    widget5 = APIKeys(main_window) 
    
    tabs = BaseCSITabs({"Agency Info":widget1, 'Keyword Lists':widget2, 'Report Templates': widget4, 'API Keys': widget5})
    
    main_window.setCentralWidget(tabs)
    main_window.set_application(app)
    
    qdarktheme.setup_theme()
    
    # Show the main window
    main_window.show()
    # Start the applicaStion event loop
    sys.exit(app.exec_())
