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
from PySide2.QtCore import QThread, Signal, QUrl, Qt, QSize, QRect, QMetaObject, QCoreApplication, QEvent
from PySide2.QtGui import QIcon, QPixmap, QFont
from PySide2.QtWidgets import (
    QApplication, QDesktopWidget, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStatusBar, QLabel, QTextEdit, QPlainTextEdit, QLineEdit, QInputDialog,
     QScrollArea, QDialog, QTabWidget, QAction, QMenuBar, QMenu, QCompleter,
      QDockWidget, QRadioButton, QCheckBox, QFormLayout,QMessageBox, QGridLayout, QFileDialog
)

from csilibs.utils import pathme, auditme, get_current_timestamp, reportme
from csilibs.config import create_case_folder
from csilibs.assets import icons, ui
from csilibs.gui import percentSize
from csilibs.data import agencyData

import qdarktheme



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
        self.setGeometry(0,0, *percentSize("app",70,90))
        # self.setFixedSize(*percentSize("app",70,90))
        self.center()

        #-------------------------- MENU BAR --------------------------#
        self.menubar = QMenuBar(self)
        self.menubar.setGeometry(QRect(0, 0, *percentSize("app",95,10)))
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
        center_point = QDesktopWidget().availableGeometry().center()
        qRect.moveCenter(center_point)
        self.move(qRect.topLeft())

    def set_application(self, application):
        """Set the application instance."""
        self.application = application

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
            img.setStatusTip("Click to Open the File" if not self.del_btn.isChecked() else "Click to Delete the File")

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
        img.setStatusTip("Click to Open the File")
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
        img.setStatusTip("Click to Open the File")
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
    qdarktheme.setup_theme()

    # Create the main window
    main_window = CSIMainWindow()

    widget1 = AgencyInfoTab(main_window)
    widget2 = sysFileEditTab(main_window, "Keyword Lists", pathme("keywordlists"), ui.PAGE, ['txt'])     
    widget3 = sysFileEditTab(main_window, "Sites Lists", pathme("sites"), ui.LAPTOP, ['json'])    
    widget4 = templateTab(main_window, "Report Templates", pathme("Templates"), ['docx','odt']) 
    tabs = BaseCSITabs({"Agency Info":widget1, 'Keyword Lists':widget2, 'Sites List':widget3, 'Report Templates': widget4})
    
    main_window.setCentralWidget(tabs)
    main_window.set_application(app)
    
    # Show the main window
    main_window.show()
    # Start the application event loop
    sys.exit(app.exec_())
