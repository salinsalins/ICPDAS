import datetime
import logging
import os
import sys
import time
import zipfile
from math import isnan

import numpy
from PyQt5.QtCore import QSize, QPoint
from pyModbusTCP.client import ModbusClient
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import *
import pyqtgraph as pg

import numpy as np

from ET7000 import *

sys.path.append('../TangoUtils')
from TangoUtils import config_logger, restore_settings, save_settings, log_exception, Configuration, \
    LOG_FORMAT_STRING_SHORT


# Класс, отвечающий за отображение оси времени (чтобы были не миллисекунды, а время в формате hh:mm),
# сделано по гайду из интернета
class TimeAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def tickValues(self, minVal, maxVal, size):
        tx = [value * 60000 for value in range(int((minVal) / 60000), int((maxVal) / 60000) + 1)]
        return [(60000, tx)]

    def tickStrings(self, values, scale, spacing):
        sign = []
        for value in values:
            t = QtCore.QDateTime()
            t.setTime_t(int(value / 1000))
            sign.append(t.toString('hh:mm'))
        return sign


# класс кривой, представляет кривую на общем графике
class Curve:
    def __init__(self, _min, _max, color=(255,255,255), name="", plot=True):
        self.min = _min  # минимальное значение на оси y
        self.max = _max  # максимальное
        self.rgb = color  # цвет - массив(list) из трех значений [r,g,b]
        self.value = 0  # текущее значение
        self.name = name  # имя для отображения в легенде
        self.plot = plot

    def set_value(self, val):  # функция, чтобы задать значение
        self.value = val


ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'H_minus_trace'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '0.1'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

LOGGER = config_logger(format_string=LOG_FORMAT_STRING_SHORT)

# создаем массив кривых которые будут отображаться на графике
curves = [Curve(0, 20, [255, 0, 0], "beam current"),
          Curve(0, 8e-5, [255, 255, 0], "vacuum high"),
          Curve(0, 150, [200, 200, 0], "T yarmo"),
          Curve(0, 300, [200, 100, 0], "T plastik"),
          Curve(0, 20, [250, 100, 100], "current 2"),
          Curve(0, 125, [100, 100, 250], "gas flow"),
          Curve(0, 8e-5, [0, 255, 255], "vacuum tube"),
          Curve(0, 1e-1, [0, 150, 130], "vacuum low")]
headers = ['time', 'beam_current', 'vacuum_high', 'T_yarmo', 'T_plastik', 'current_2', 'gas_flow',
           'vacuum_tube', 'vacuum_low']


# основной класс окна, используется библиотека PyQt
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.logger = LOGGER
        #
        self.out_root = '.\\data\\'
        self.ip1 = '192.168.0.44'
        self.ip2 = '192.168.0.45'
        self.ip3 = '192.168.0.46'
        self.pet1 = None
        self.pet2 = None
        self.pet3 = None
        self.data_folder = None
        self.data_file_name = None
        self.data_file = None
        self.curves = []
        #
        self.config = Configuration()
        uic.loadUi(UI_FILE, self)
        self.resize(QSize(480, 640))  # size
        self.move(QPoint(50, 50))  # position
        self.setWindowTitle(APPLICATION_NAME)  # title
        self.setWindowIcon(QtGui.QIcon('icon.png'))  # icon
        self.setWindowTitle("ICP DAS Measurements")
        #
        self.restore_settings()
        # welcome message
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')
        if self.data_file is None:
            self.logger.error('Output file can not be created')
            sys.exit(-12)
        # график pyqtgraph и слайдер
        self.graph = self.graphicsView
        self.plt = self.graph.addPlot(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plt.showGrid(x=True, y=True, alpha=1)
        self.slider = self.horizontalScrollBar
        # легенда для графика
        self.legend = self.comboBox
        n = 0
        # для каждой кривой добавляем элемент в легенде
        # также создаем картинку 10х10 нужного цвета и делаем ее иконкой для элемента
        for curve in curves:
            p = QtGui.QPixmap(10, 10)
            p.fill(QtGui.QColor(curve.rgb[0], curve.rgb[1], curve.rgb[2]))
            i = QtGui.QIcon(p)
            self.legend.addItem(curve.name)
            self.legend.setItemIcon(n, i)
            n += 1
        self.legend.setCurrentIndex(1)
        # создаем массив для графиков
        self.data = []
        self.data_index = -1
        data_array_length = 12 * 3600
        for i in range(len(curves)):
            # self.data.append([])  # на каждую кривую добавляем по элементу
            self.data.append(numpy.zeros(data_array_length))
        # массив времени в миллисекундах раз в секунду
        self.time = numpy.zeros(data_array_length)
        # массив, в котором будет храниться история всех значений для записи в файл
        self.hist = []
        # стандартный таймер - функция cycle будет вызываться каждую секунду
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.cycle)
        # основные значения (ток, давление и т.п)
        self.vals = [self.lineEdit_1, self.lineEdit_2, self.lineEdit_3, self.lineEdit_4, self.lineEdit_5]
        # добавляем кнопку разворачивания окна со значениями напряжений ацп
        # self.bigbut = self.pushButton
        self.pushButton.clicked.connect(self.toggle_list)  # при нажатии срабатывает метод bigPress
        self.listWidget.hide()
        # массив значений температуры диафрагмы, нулевой элемент не используется
        # 1,2,3,4 - по часовой, начало из левого верхнего угла
        self.Td = [0, self.doubleSpinBox, self.doubleSpinBox_3, self.doubleSpinBox_9, self.doubleSpinBox_7]
        # массив средних значений между соседними термопарами
        # 1,2,3,4 - по часовой, начало из левого верхнего угла
        self.Tds = [0, self.doubleSpinBox_2, self.doubleSpinBox_6, self.doubleSpinBox_8, self.doubleSpinBox_4]
        # температура ярма
        self.T1 = self.doubleSpinBox_10
        # температура пластика
        self.T2 = self.doubleSpinBox_11
        #
        self.writeN = 0  # счетчик для записи в файл каждые 10 секунд
        self.timer.start(1000)

    def restore_settings(self, file_name=CONFIG_FILE):
        try:
            self.config = Configuration(file_name=file_name)
            self.logger.setLevel(self.config.get('log_level', logging.DEBUG))
            wsp = self.config.get('main_window', {'size': [800, 400], 'position': [0, 0]})
            self.resize(QSize(wsp['size'][0], wsp['size'][1]))
            self.move(QPoint(wsp['position'][0], wsp['position'][1]))
            self.ip1 = self.config.get('ip1', '192.168.0.44')
            self.ip2 = self.config.get('ip2', '192.168.0.46')
            self.ip3 = self.config.get('ip3', '192.168.0.45')
            self.pet1 = FakeET7000(self.ip1, logger=LOGGER, timeout=0.15, type='7026')
            self.pet2 = FakeET7000(self.ip2, logger=LOGGER, timeout=0.15, type='7015')
            self.pet3 = FakeET7000(self.ip3, logger=LOGGER, timeout=0.15, type='7026', sin=1.0)
            self.out_root = self.config.get('out_root', '.\\data\\')
            self.checkBox.setChecked(self.config.get('autoscale', False))
            self.curves = self.config.get('curves', [])
            for i, curve in enumerate(self.curves):
                if i < len(curves):
                    curves[i] = Curve(curve[0], curve[1], curve[2], curve[3])
                if i >= len(curves):
                    curves.append(Curve(curve[0], curve[1], curve[2], curve[3]))
            self.make_data_folder()
            self.open_data_file()
            self.logger.info('Configuration restored from %s', CONFIG_FILE)
        except:
            log_exception(self, 'Error configuration restore from %s', CONFIG_FILE, level=logging.INFO)
        return self.config

    # функция устанавливает значение канала(LineEdit) в виде числа со степенью
    def setChannelSci(self, chan, val):
        chan.setText("{:.2E}".format(val))

    # функция устанавливает значение канала(LineEdit) в виде числа с N цифр после запятой
    def setChannelEng(self, chan, val, N=3):
        chan.setText(("{:." + str(N) + "f}").format(val))

    # функция вызывается при нажатии на кнопку развернуть окно и увеличивает или уменьшает его размер
    def toggle_list(self):
        if self.pushButton.isChecked():
            self.listWidget.show()
        else:
            self.listWidget.hide()

    # Функция - основной цикл. Вызывается раз в секунду
    def cycle(self):
        # СЧИТЫВАНИЕ И ВЫВОД ЗНАЧЕНИЙ
        try:
            # считываем значения напряжения с первого ацп в массив volt
            if self.pet1.type == 0x7026:
                volt = self.pet1.ai_read()
            else:
                volt = [999.] * 6
            for i in range(len(volt)):
                if isnan(volt[i]):
                    volt[i] = 999.
            # считываем значения напряжения со второго ацп (третий клиент так как второй это термопары) в массив volt2
            if self.pet3.type == 0x7026:
                volt2 = self.pet3.ai_read()
            else:
                volt2 = [999.] * 6
            # считываем температуру аналогично напряжению
            if self.pet2.type == 0x7015:
                temp = self.pet2.ai_read()
            else:
                temp = [999.] * 7
            # fill list widget with raw data
            self.listWidget.clear()
            self.listWidget.addItem(self.ip1)
            for _v in volt:
                self.listWidget.addItem(str(_v))
            self.listWidget.addItem(' ')
            self.listWidget.addItem(self.ip3)
            for _v in volt2:
                self.listWidget.addItem(str(_v))
            self.listWidget.addItem(' ')
            self.listWidget.addItem(self.ip2)
            for _v in temp:
                self.listWidget.addItem(str(_v))

            # Из напряжений рассчитываем основные значения
            beam_current = -volt2[5] * 1000 / 92.93  # ток пучка mA
            intercepted_current = -volt2[5] * 10  # ток 2 mA - хз что это
            flow = ((-volt2[3] * 1000 / 102) - 4) * 100 / 16  # поток газа
            # vacuum
            if volt2[1] >= 666:
                vac_chamber = 0.0  # вакуум в бочке
            else:
                vac_chamber = pow(10, 1.667 * volt2[1] - 11.46)  # вакуум в бочке
            if volt[5] >= 666:
                vac_fore = 0.0  # форвакуум
            else:
                vac_fore = pow(10, volt[5] - 5.625)
            if volt2[0] >= 666:
                vac_tube = 0.0  # вакуум в канале транспортировки
            else:
                vac_tube = pow(10, 1.667 * volt2[0] - 11.46)  # вакуум в трубке

            # записываем основные значения чтобы их увидел пользователь
            self.setChannelEng(self.vals[0], beam_current, 3)
            self.setChannelSci(self.vals[1], vac_chamber)
            self.setChannelSci(self.vals[2], vac_tube)
            self.setChannelSci(self.vals[3], vac_fore)
            self.setChannelEng(self.vals[4], flow, 1)

            # выводим значения температуры диафрагмы
            self.Td[1].setValue(temp[1])
            self.Td[2].setValue(temp[6])
            self.Td[3].setValue(temp[3])
            self.Td[4].setValue(temp[2])
            # считаем и выводим средние значения температур
            for i in range(1, 5):
                j = i + 1
                if j > 4:
                    j = 1
                self.Tds[i].setValue((self.Td[i].value() + self.Td[j].value()) / 2)
            # задаем температуры ярма и пластика
            Tyarmo = temp[5]
            Tplastik = temp[0]
            # выводим их для пользователя
            self.T1.setValue(Tyarmo)
            self.T2.setValue(Tplastik)
            # если больше некоторых значений, то значение краснеет
            if self.T1.value() > 120:
                self.T1.setStyleSheet('background-color:red; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            else:
                self.T1.setStyleSheet('background-color:white; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            if self.T2.value() > 250:
                self.T2.setStyleSheet('background-color:red; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            else:
                self.T2.setStyleSheet('background-color:white; font: 75 12pt "MS Shell Dlg 2"; font: bold;')

            # ГРАФИК И ИСТОРИЯ
            # new point index
            self.data_index += 1
            # check for data array overflow - switch for new file
            if self.data_index >= len(self.data[0]):
                self.logger.warning('Data array is full, index reset to zero')
                self.data_index = 0
                self.close_data_file()
                self.make_data_folder()
                self.open_data_file()
                #self.time = []
                self.hist = []
            # check for date change - switch for new file
            cfn = self.get_data_file_name()
            if cfn[:9] != self.data_file_shot[:9]:
                self.logger.warning('Date changed, switch for new file')
                self.data_index = 0
                self.close_data_file()
                self.make_data_folder()
                self.open_data_file()
                #self.time = []
                self.hist = []

            # Шкала времени
            dt = QtCore.QDateTime.currentDateTime()
            dt_ms = dt.currentMSecsSinceEpoch()
            # каждый цикл добавляем значение времени в миллисекундах
            #self.time.append(dt_ms)
            self.time[self.data_index] = dt_ms
            # рассчитываем отступ по времени в зависимости от положения слайдера
            slider_relative = 1.0 - (self.slider.maximum() - self.slider.value()) / self.slider.maximum()
            offset = (dt_ms - self.time[0]) * (self.slider.maximum() - self.slider.value()) / self.slider.maximum()
            # Задаем границы оси Х графика (время) с учетом отступа. Ширина 15 минут
            #self.plt.setXRange(dt_ms - 15 * 60 * 1000 - offset, dt_ms - offset)
            last_index = int(slider_relative * self.data_index)
            first_index = max(last_index - (15 * 60), 0)

            # Задаем желаемое значение для каждой кривой
            curves[0].set_value(beam_current)
            curves[1].set_value(vac_chamber)
            curves[2].set_value(Tyarmo)
            curves[3].set_value(Tplastik)
            curves[4].set_value(intercepted_current)
            curves[5].set_value(flow)
            curves[6].set_value(vac_tube)
            curves[7].set_value(vac_fore)

            # находим текущую кривую - ту которая выбрана в легенде
            curr_curve = curves[self.legend.currentIndex()]
            # self.LOGGER.debug('Base plot "%s" max: %s min: %s', curr_curve.name, curr_curve.max, curr_curve.min)
            # задаем Y диапазон на графике в соответствие с диапазоном у текущей кривой
            self.plt.clear()  # очистка графика
            if not self.checkBox.isChecked():
                self.plt.setYRange(curr_curve.min, curr_curve.max)
            # цикл отрисовки всех кривых
            n = 0
            for curve in curves:
                # добавляем к массиву нормализованное (минимум - 0, максимум - 1) значение
                # self.data[n].append((curve.value - curve.min) / (curve.max - curve.min))
                self.data[n][self.data_index] = curve.value
                if last_index > 0:
                    scale = 1.0 / (curve.max - curve.min) * (curr_curve.max - curr_curve.min)
                    plot_data = (self.data[n][first_index:last_index] - curve.min) * scale + curr_curve.min
                    plot_time = self.time[first_index:last_index]
                    # рисуем кривую
                    # c_max = curve.max / (curve.max - curve.min) * (curr_curve.max - curr_curve.min)
                    # c_min = curve.min / (curve.max - curve.min) * (curr_curve.max - curr_curve.min)
                    # c_val = (curve.value - curve.min) / (curve.max - curve.min) * (curr_curve.max - curr_curve.min)  + curr_curve.min
                    # self.LOGGER.debug('Plotting "%s" max: %s min: %s val: %s', curve.name, c_max, c_min, c_val)
                    self.plt.plot(plot_time, plot_data, pen=(curve.rgb[0], curve.rgb[1], curve.rgb[2]))
                n += 1

            # запись истории в файл
            # добавляем очередное значение, значения должны соответствовать заголовкам
            self.hist[0] = beam_current
            self.hist[1] = vac_chamber
            self.hist[2] = Tyarmo
            self.hist[3] = Tplastik
            self.hist[4] = intercepted_current
            self.hist[5] = flow
            self.hist[6] = vac_tube
            self.hist[7] = vac_fore

            # запись в файл
            if self.data_file is not None:
                # print("write to file")
                t = QtCore.QDateTime()
                # преобразуем миллисекунды в час:минута:секунда и записываем в файл
                self.data_file.setTime_t(int(self.time[i - 10] / 1000))
                self.data_file.write(t.toString('hh:mm:ss') + '\t')
                for j in range(len(self.hist)):  # следом записываем все соответсвующий значения истории
                    v = self.hist[j]
                    if v >= 666 or v >= 6666:
                        self.data_file.write(str('0\t'))
                    else:
                        self.data_file.write(str(v) + '\t')
                self.data_file.write('\n')
                self.data_file.flush()
        except:
            log_exception(self)

    def on_quit(self):
        # save_settings(self, file_name=CONFIG_FILE)
        p = self.pos()
        s = self.size()
        # self.config['curves'] = curves
        self.config['main_window'] = {'size': (s.width(), s.height()), 'position': (p.x(), p.y())}
        self.config['autoscale'] = self.checkBox.isChecked()
        self.config.write()
        self.logger.info('Configuration saved to %s', CONFIG_FILE)
        self.close_data_file()

    def make_data_folder(self):
        of = os.path.join(self.out_root, self.get_data_folder())
        try:
            if not os.path.exists(of):
                os.makedirs(of)
            if os.path.exists(of):
                self.data_folder = of
                self.logger.debug("Output folder %s has been created", self.data_folder)
                return True
            else:
                raise FileNotFoundError('Can not create output folder %s' % of)
        except:
            self.data_folder = None
            self.logger.error("Can not create output folder %s", self.data_folder)
            return False

    def get_data_folder(self):
        ydf = datetime.datetime.today().strftime('%Y')
        mdf = datetime.datetime.today().strftime('%Y-%m')
        ddf = datetime.datetime.today().strftime('%Y-%m-%d')
        folder = os.path.join(ydf, mdf, ddf)
        return folder

    def open_data_file(self, flags='a'):
        try:
            self.data_file_shot = self.get_data_file_name()
            self.data_file_name = os.path.join(self.data_folder, self.get_data_file_name())
            write_headers = not (os.path.exists(self.data_file_name) and flags == 'a')
            self.close_data_file()
            self.data_file = open(self.data_file_name, flags)
            if write_headers:
                self.write_headers(self.data_file)
            self.logger.debug("Output file %s has been opened", self.data_file_name)
        except:
            self.data_file = None
            log_exception(self, 'Output file open error')
        return self.data_file

    def close_data_file(self):
        if self.data_file is None:
            return
        try:
            if not self.data_file.closed:
                self.data_file.close()
            self.data_file = None
        except:
            self.data_file = None

    def get_data_file_name(self):
        data_file_name = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S.txt')
        return data_file_name

    def date_time_stamp(self):
        return datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    def time_stamp(self):
        return datetime.datetime.today().strftime('%H:%M:%S')

    def open_zip_file(self, folder):
        fn = datetime.datetime.today().strftime('%Y-%m-%d_%H%M%S.zip')
        zip_file_name = os.path.join(folder, fn)
        zip_file = zipfile.ZipFile(zip_file_name, 'a', compression=zipfile.ZIP_DEFLATED)
        return zip_file

    def write_headers(self, f):
        # запись заголовков
        for h in headers:
            f.write(h + "\t")
        f.write("\n")
        f.flush()


# Стандартный код для  PyQt приложения - создание Qt приложения, окна и запуск
app = QApplication([])
window = MainWindow()
app.aboutToQuit.connect(window.on_quit)
window.show()
code = app.exec_()
# client1.close()
# client2.close()
exit(code)
