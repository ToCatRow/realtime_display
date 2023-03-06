#coding=utf-8
from array import array
from math import sin, cos

import datetime
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from guiqwt.plot import PlotManager, CurvePlot
from guiqwt.builder import make
import socket
import serial
import binascii
from multiprocessing import Process,Queue
import time
import csv
#

collecttime = 10
bin_ori = ''
COLORS = ["blue", "red"]
DT = 0.1



class RealtimeDemo(QWidget):
    def __init__(self, arg = {}):
        super(RealtimeDemo, self).__init__()
        self.setWindowTitle(u"Realtime Reciever")

        PLOT_DEFINE = [[u"signal_0", u"signal_1", u"signal_2", u"signal_3",
                        u"signal_4", u"signal_5", u"signal_6", u"signal_7"],
                       [u"signal_8", u"signal_9", u"signal_10", u"signal_11",
                        u"signal_12", u"signal_13", u"signal_14", u"signal_15"]]
        self.drawQueue = arg['drawQ']
        self.data = {u"t":array("d")}
        for name in sum(PLOT_DEFINE, []):
            self.data[name] = array("d")
        self.curves = {}
        self.t = 0
        vbox = QVBoxLayout()
        vbox.addWidget(self.setup_toolbar())

        grid = QGridLayout()
        vbox.addLayout(grid)

        self.manager = PlotManager(self)
        self.plots = []
        cor =  [(i, j) for i in range(len(PLOT_DEFINE)) for j in range(len(PLOT_DEFINE[0]))]
        cor = [[0,0],[0,1]]
        for i, define in enumerate(PLOT_DEFINE):
            plot = CurvePlot()
            plot.axisScaleDraw(CurvePlot.Y_LEFT).setMinimumExtent(60)
            self.manager.add_plot(plot)
            self.plots.append(plot)
            plot.plot_id = id(plot)
            for j, curve_name in enumerate(define):
                curve = self.curves[curve_name] = make.curve([0], [0], color=COLORS[0], title=curve_name)
                plot.add_item(curve)
            plot.add_item(make.legend("BL"))
            grid.addWidget(plot, cor[i][0], cor[i][1])
        self.manager.register_standard_tools()
        self.manager.get_default_tool().activate()
        self.manager.synchronize_axis(CurvePlot.X_BOTTOM, self.manager.plots.keys())
        self.setLayout(vbox)
        self.startTimer(100)


    def setup_toolbar(self):
        toolbar = QToolBar()
        self.auto_yrange_checkbox = QCheckBox(u"Y轴自动调节")
        self.auto_xrange_checkbox = QCheckBox(u"X轴自动调节")
        self.xrange_box = QSpinBox()
        self.xrange_box.setMinimum(1)
        self.xrange_box.setMaximum(50)
        self.xrange_box.setValue(25)
        self.auto_xrange_checkbox.setChecked(True)
        self.auto_yrange_checkbox.setChecked(True)
        toolbar.addWidget(self.auto_yrange_checkbox)
        toolbar.addWidget(self.auto_xrange_checkbox)
        toolbar.addWidget(self.xrange_box)
        self.lbl = QLabel("          IP地址：")
        toolbar.addWidget(self.lbl)
        self.IPaddress = QLineEdit('192.168.4.1')
        self.IPaddress.setInputMask('000.000.000.000')
        self.IPaddress.setFixedWidth(120)
        toolbar.addWidget(self.IPaddress)
        self.lbl = QLabel("          端口号：")
        toolbar.addWidget(self.lbl)
        self.Port = QLineEdit("4321")
        self.Port.setInputMask('00000')
        self.Port.setFixedWidth(50)
        toolbar.addWidget(self.Port)
        self.connectButton = QPushButton("连接并开始")
        self.connectButton.toggle()
        toolbar.addWidget(self.connectButton)
        return toolbar

    def timerEvent(self, event):
        global bin_ori
        n_channel = 16
        drawcache = []

        for i in range(n_channel):
            drawcache.append([])
        while not self.drawQueue.empty():
            print("queue")
            drawcache = self.drawQueue.get()
            for i in range(len(drawcache[0])):
                t = self.t
                self.data[u"t"].append(t)
                for j in range(n_channel):
                    self.data[u"signal_"+str(j)].append(drawcache[j][i]+10*(j%8))
                self.t += DT

        if self.auto_xrange_checkbox.isChecked():
            xmax = self.data["t"][-1]
            xmin = max(xmax - self.xrange_box.value(), 0)
        else:
            xmin, xmax = self.plots[0].get_axis_limits('bottom')

        for key, curve in self.curves.items():
            xdata = self.data["t"]
            ydata = self.data[key]
            x, y = self.get_peak_data(xdata, ydata, xmin, xmax, 600, 1/DT)
            curve.set_data(x, y)

        for plot in self.plots:
            if self.auto_yrange_checkbox.isChecked() and self.auto_xrange_checkbox.isChecked():
                plot.do_autoscale()
            elif self.auto_xrange_checkbox.isChecked():
                plot.set_axis_limits("bottom", xmin, xmax)
                plot.replot()
            else:
                plot.replot()

    def get_peak_data(self,x, y, x0, x1, n, rate):
        if len(x) == 0:
            return [0], [0]
        x = np.frombuffer(x)
        y = np.frombuffer(y)
        index0 = int(x0 * rate)
        index1 = int(x1 * rate)
        step = (index1 - index0) // n
        if step == 0:
            step = 1
        index1 += 2 * step
        if index0 < 0:
            index0 = 0
        if index1 > len(x) - 1:
            index1 = len(x) - 1
        x = x[index0:index1 + 1]
        y = y[index0:index1 + 1]
        y = y[:len(y) // step * step]
        yy = y.reshape(-1, step)
        index = np.c_[np.argmin(yy, axis=1), np.argmax(yy, axis=1)]
        index.sort(axis=1)
        index += np.arange(0, len(y), step).reshape(-1, 1)
        index = index.reshape(-1)
        return x[index], y[index]

def realtimeShow(drawQueue):
    import sys
    arg = {}
    arg['drawQ'] = drawQueue

    app = QApplication(sys.argv)
    form = RealtimeDemo(arg=arg)
    form.show()
    sys.exit(app.exec_())

def make_connection(connection,arg):
    if connection == 0:
        ser = serial.Serial(arg['com'], arg['baud_rate'])
        return ser
    if connection == 1:
        HOST = arg['HOST']
        PORT = arg['PORT']
        BUFFSIZE = arg['BUFFSIZE']
        ADDR = arg['ADDR']
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(ADDR)

        return sock

def receiveData(drawQueue, writeQueue):
    global bin_ori
    collecttime = 10
    MAXRANGE = 65535
    AMPL = 6
    SAMPLEPERBLOCK = 32
    wrong_no = 0
    n_channel = 16

    connection = 1
    arg = {}
    if connection == 1:
        arg['HOST'] = '192.168.4.1'  # 主机
        arg['PORT'] = 4321  # 端口
        arg['BUFFSIZE'] = 4096  # 缓冲区大小
        arg['ADDR'] = (arg['HOST'], arg['PORT'])  # 地址
    elif connection == 0:
        arg['com'] = 'com6'
        arg['buad_rate'] = 4500000
    conn = make_connection(connection, arg)

    while True:
        writecache = []
        drawcache = []
        for i in range(n_channel):
            writecache.append([])
            drawcache.append([])
        for i in range(collecttime):
            ori, addr = conn.recvfrom(arg['BUFFSIZE'])
            bin_ori += str(binascii.b2a_hex(ori))[2:-1]
        print(2)
        ffff_list = bin_ori.split('ffff00ffff')
        print(ffff_list)
        for i in range(1, len(ffff_list)):
            if len(ffff_list[i]) != 4 * n_channel * SAMPLEPERBLOCK:
                wrong_no += 1
                continue
            for k in range(SAMPLEPERBLOCK):
                Sample_temp = ffff_list[i][4 * n_channel * k: 4 * n_channel * (k + 1)]

                for j in range(n_channel):
                    channel_temp = Sample_temp[4 * j:4 * (j + 1)]
                    temp = int(channel_temp, 16)

                    drawcache[j].append((temp - MAXRANGE / 2) / (MAXRANGE / 2) * AMPL)
                    writecache[j].append(str(temp))
        drawQueue.put(drawcache)
        writeQueue.put(writecache)

def saveData(writeQueue):
    writecache  = []
    n_channel = 16
    import os
    while True:
        while not writeQueue.empty():
            writecache = writeQueue.get()
            now = datetime.datetime.now()
            date_time = now.strftime("%Y-%m-%d_%H-%M-%S")

            file_name = f'example_{date_time}.csv'

            with open(".\\data\\" + file_name
            , 'w', newline='') as csvfile:
                file_writer = csv.writer(csvfile, dialect='excel')
                for i in range(len(writecache[0])):
                    temp = []
                    for j in range(n_channel):
                        temp.append(writecache[j][i])
                    file_writer.writerow(temp)

def main():
    drawQueue = Queue()
    writeQueue = Queue()
    drawProcces = Process(target=realtimeShow,args=(drawQueue,))
    receiveProcces = Process(target=receiveData, args=(drawQueue, writeQueue))
    saveProcces = Process(target=saveData, args=(writeQueue,))

    receiveProcces.start()
    drawProcces.start()
    saveProcces.start()
    while drawProcces.is_alive():
        pass
    receiveProcces.terminate()
    saveProcces.terminate()
    receiveProcces.join()
    saveProcces.join()

if __name__ == '__main__':
    main()



