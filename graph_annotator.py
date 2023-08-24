import sys

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QGridLayout, QVBoxLayout, QGroupBox, QPushButton, QDesktopWidget, QStyleFactory, \
    QWidget, QTabWidget, QFrame, QPlainTextEdit, QFileDialog, QLineEdit
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor

import matplotlib

matplotlib.use("Qt5Agg")

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure, Rectangle

from netgraph_class.interactive_variants import MutableGraph
from netgraph._artists import NodeArtist, EdgeArtist
from netgraph_class.file_manager import EventGraphData

import networkx as nx


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        super().__init__(parent)
        self._highlight_lines = {}

    def highlight_line(self, line_num, fmt):
        if isinstance(line_num, int) and line_num >= 0 and isinstance(fmt, QTextCharFormat):
            self._highlight_lines[line_num] = fmt
            block = self.document().findBlockByNumber(line_num)
            self.rehighlightBlock(block)

    def clear_highlight(self):
        self._highlight_lines = {}
        self.rehighlight()

    def highlightBlock(self, text):
        blockNumber = self.currentBlock().blockNumber()
        fmt = self._highlight_lines.get(blockNumber)
        if fmt is not None:
            self.setFormat(0, len(text), fmt)


class MplCanvas(FigureCanvasQTAgg, QtWidgets.QWidget):
    mySignal = QtCore.pyqtSignal(int)

    def __init__(self, parent=None, width=5, height=4, dpi=100, app_object=None, event_info=None, graph_info=None):
        super(MplCanvas, self).__init__(Figure(figsize=(width, height), dpi=dpi))
        self.setParent(parent)
        self.ax = self.figure.add_subplot(111)
        self.figure.tight_layout()
        # self.figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

        graph = nx.complete_graph(2)
        node_dict = True if event_info is None else {}
        if graph_info is not None and event_info is not None:
            node_dict = {}
            graph = nx.Graph()
            for idx, event in enumerate(event_info):
                node_dict[idx] = "{}: {}".format(idx, event["instance"])
                graph.add_node(idx)
                graph.add_edges_from(graph_info)
        self.plot_instance = MutableGraph(graph, edge_width=1.5, edge_color="blue", ax=self.ax,
                                          node_labels=node_dict, node_alpha=0.5, node_label_fontdict=dict(size=12),
                                          canvas_parent=self)

        self.mySignal.connect(app_object.text_highlight)

    def get_plot(self):
        return self.plot_instance

    def node_selection(self, node):
        self.mySignal.emit(node)


class MyTableWidget(QWidget):
    tab_names = ["Temporal", "Spatial", "Character", "Causal", "Intention"]

    def __init__(self, parent, app_object, event_info=None, graph_info=None):
        super(QWidget, self).__init__(parent)
        if graph_info is None:
            graph_info = [None, None, None, None, None]
        self.layout = QVBoxLayout(self)
        self.app_object = app_object

        # Initialize tab screen
        self.tabs = QTabWidget(self)
        self.tab_list = []
        self.canvas_list = []
        for idx, tab_name in enumerate(self.tab_names):
            tmp_tab = QWidget(self)
            tmp_tab.resize(300, 300)

            tmp_canvas = MplCanvas(tmp_tab, width=3, height=3, dpi=150,
                                   app_object=app_object,
                                   event_info=event_info, graph_info=graph_info[idx])
            tmp_canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
            tmp_canvas.setFocus()

            tmp_tab.layout = QVBoxLayout(self)
            tmp_tab.layout.addWidget(tmp_canvas)
            tmp_tab.setLayout(tmp_tab.layout)

            self.tabs.addTab(tmp_tab, tab_name)
            self.tab_list.append(tmp_tab)
            self.canvas_list.append(tmp_canvas)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def update_graph(self, event_info=None, graph_info=None):
        if graph_info is None:
            graph_info = [None, None, None, None, None]
        for idx, cur_tab in enumerate(self.tab_list):
            cur_tab.layout.removeWidget(self.canvas_list[idx])
            self.canvas_list[idx].deleteLater()
        self.canvas_list.clear()
        for idx, cur_tab in enumerate(self.tab_list):
            tmp_canvas = MplCanvas(cur_tab, width=3, height=3, dpi=150,
                                   app_object=self.app_object,
                                   event_info=event_info, graph_info=graph_info[idx])
            tmp_canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
            tmp_canvas.setFocus()

            cur_tab.layout.addWidget(tmp_canvas)
            cur_tab.setLayout(cur_tab.layout)
            self.canvas_list.append(tmp_canvas)

    def get_graph(self):
        graph_info = []
        for cur_canvas in self.canvas_list:
            graph_info.append(cur_canvas.get_plot().edges)
        return graph_info


class MainWindow(QtWidgets.QMainWindow):
    NumButtons = ['PreviousGraph', 'NextGraph']
    PrintBUttons = ['SaveGraph', 'ImportFile']

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        font = QFont()
        font.setPointSize(16)
        self.file_manager = None

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1600, 720)
        self.center()
        self.setWindowTitle('Graph Plot')

        # main widget
        self.main_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.main_widget)
        grid = QGridLayout(self.main_widget)
        self.setLayout(grid)

        # button group
        self.createVerticalGroupBox()
        self.buttonLayout = QVBoxLayout(self.main_widget)
        self.buttonLayout.addWidget(self.verticalGroupBox)
        grid.addLayout(self.buttonLayout, 0, 0)

        # canvas frame
        self.canvasFrame = QFrame(self.main_widget)
        self.canvasFrame.resize(300, 300)
        self.canvasFrame.setStyleSheet("background-color: rgb(200, 255, 255)")
        self.tabs = None
        self.canvas_box = QVBoxLayout(self.main_widget)
        grid.addWidget(self.canvasFrame, 0, 1, 9, 9)

        # sentences frame
        self.textFrame = QFrame(self.main_widget)
        self.textFrame.resize(100, 300)
        self.textFrame.setStyleSheet("background-color: rgb(100, 255, 255)")
        self.text_box = QVBoxLayout(self.main_widget)
        self.text_editor = QPlainTextEdit(self.main_widget)
        self.text_editor.setReadOnly(True)
        self.text_editor.setStyleSheet('font-size: 15px')
        self.text_box.addWidget(self.text_editor)
        self.textFrame.setLayout(self.text_box)
        grid.addWidget(self.textFrame, 0, 10, 9, 5)

        # tree frame
        self.treeFrame = QFrame(self.main_widget)
        self.treeFrame.resize(100, 300)
        self.treeFrame.setStyleSheet("background-color: rgb(50, 255, 255)")
        self.tree_box = QVBoxLayout(self.main_widget)
        self.tree_editor = QPlainTextEdit(self.main_widget)
        self.tree_editor.setReadOnly(True)
        self.tree_editor.setStyleSheet('font-size: 15px')
        self.tree_box.addWidget(self.tree_editor)
        self.treeFrame.setLayout(self.tree_box)
        grid.addWidget(self.treeFrame, 0, 15, 9, 3)


    def createVerticalGroupBox(self):
        self.verticalGroupBox = QGroupBox(self.main_widget)
        layout = QVBoxLayout(self.main_widget)

        button = QPushButton("Prev")
        button.setObjectName("Prev")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.prev_story)

        button = QPushButton("Next")
        button.setObjectName("Next")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.next_story)

        self.num_line = QLineEdit(self.main_widget)
        self.num_line.setStyleSheet('font-size: 14px')
        layout.addWidget(self.num_line)

        button = QPushButton("Jump")
        button.setObjectName("Jump")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.jump_story)

        layout.insertSpacing(100, 30)

        button = QPushButton("SaveGraph")
        button.setObjectName("SaveGraph")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.save_story)

        layout.insertSpacing(100, 30)

        button = QPushButton("SaveFile")
        button.setObjectName("SaveFile")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.save_file)

        button = QPushButton("ImportFile")
        button.setObjectName("ImportFile")
        button.setStyleSheet('font-size: 14px')
        layout.addWidget(button)
        button.clicked.connect(self.import_file)

        layout.setSpacing(10)
        self.verticalGroupBox.setLayout(layout)
        self.verticalGroupBox.setMaximumWidth(100)

    def load_story(self):
        self.cur_events = self.file_manager.get_event_info(self.cur_story_idx)

        # text editor
        self.tree_editor.clear()
        self.text_editor.clear()
        cur_sents = self.file_manager.get_story_text(self.cur_story_idx)
        for sent in cur_sents:
            self.text_editor.appendPlainText("> " + sent)
        self.text_editor.appendPlainText("")
        self.text_editor.appendPlainText(self.file_manager.get_story_moral(self.cur_story_idx))
        self.highlighter = SyntaxHighlighter(self.text_editor.document())

        # canvas
        if self.tabs is None:
            self.tabs = MyTableWidget(self.main_widget, self,
                                      event_info=self.cur_events,
                                      graph_info=self.file_manager.get_graph_info(self.cur_story_idx))
            self.canvas_box.addWidget(self.tabs)
            self.canvasFrame.setLayout(self.canvas_box)
        else:
            self.tabs.update_graph(event_info=self.cur_events,
                                   graph_info=self.file_manager.get_graph_info(self.cur_story_idx))

        self.num_line.setText(str(self.cur_story_idx))

    def jump_story(self):
        if self.file_manager is None:
            print("no file_manager yet.")
            return
        tmp_idx = int(self.num_line.text())
        self.num_line.clear()
        if isinstance(tmp_idx, int) and self.file_manager.check_idx(tmp_idx):
            self.save_story()
            self.cur_story_idx = tmp_idx
            self.load_story()

    def next_story(self):
        if self.file_manager is None:
            print("no file_manager yet.")
            return
        self.save_story()
        self.cur_story_idx = self.file_manager.get_next_idx(self.cur_story_idx)
        self.load_story()

    def prev_story(self):
        if self.file_manager is None:
            print("no file_manager yet.")
            return
        self.save_story()
        self.cur_story_idx = self.file_manager.get_prev_idx(self.cur_story_idx)
        self.load_story()

    def save_story(self):
        assert self.tabs, "no tab created"
        new_graph = self.tabs.get_graph()
        self.file_manager.set_graph_info(self.cur_story_idx, new_graph)

    def import_file(self):
        f_name = QFileDialog.getOpenFileName(self, 'Open file', "./Data", "JSON fils (*.json *.jsonl)")
        try:
            self.cur_story_idx = 0
            self.file_manager = EventGraphData(f_name[0])
            self.load_story()
        except Exception as e:
            print(e)
            self.file_manager = None
            self.cur_story_idx = None

    def save_file(self):
        if not self.file_manager:
            print("no file loaded yet.")
            return
        self.save_story()
        f_name = QFileDialog.getSaveFileName(self, 'Save file', "./Data/Full_Fables_Graph_New.json",
                                             "JSON fils (*.json *.jsonl)")
        try:
            self.file_manager.save_file(f_name[0])
        except Exception as e:
            print(e)

    def text_highlight(self, node_id):
        parsed_tree = self.cur_events[node_id]["parsed_tree"]
        self.tree_editor.clear()
        for tree_elem in parsed_tree:
            self.tree_editor.appendPlainText(tree_elem)
        line_num = self.cur_events[node_id]["sent_id"]
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("yellow"))
        self.highlighter.clear_highlight()
        try:
            self.highlighter.highlight_line(line_num, fmt)
        except Exception as e:
            pass

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.aboutToQuit.connect(app.deleteLater)

    w = MainWindow()
    w.show()
    app.exec_()


if __name__ == "__main__":
    main()
