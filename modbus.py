# Используемые библиотеки
import os
import time
from math import isnan

from PyQt5.QtCore import QSize, QPoint
from pyModbusTCP.client import ModbusClient
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import *
import pyqtgraph as pg

import numpy as np

from ET7000 import *
from TangoUtils import config_logger, restore_settings, save_settings, log_exception


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


# Класс канала, представляет канал АЦП
class Channel:
    def __init__(self, Addr, Min, Max):
        self.addr = Addr  # номер канала на АЦП
        self.min = Min  # минимальное значение в вольтах
        self.max = Max  # максимальное


# класс кривой, представляет кривую на общем графике
class Curve:
    def __init__(self, _min, _max, color, name=""):
        self.min = _min  # минимальное значение на оси y
        self.max = _max  # максимальное
        self.rgb = color  # цвет - массив(list) из трех значений [r,g,b]
        self.value = 0  # текущее значение
        self.name = name  # имя для отображения в легенде

    def set_value(self, val):  # функция, чтобы задать значение
        self.value = val


# преобразования байтового значения которое выдает АЦП (по сути целочисленное) в значение напряжения
def toV(b, Min, Max):
    # обрабатывается всего 2 случая - минимум нулевой
    if Min == 0 and Max > 0:
        return Max * b / 0xffff
        # и минимум по модулю равен максимуму
    if Min == -Max and Max > 0:
        one = 0xffff / 2
        if b <= one:
            return Max * b / one
        else:
            return -Max * (0xffff - b) / one
    # в других случаях ошибка
    print('wrong borders')
    return 666


# ненужная функция, на всякий случай не стал удалять
def toT(b):
    return b / 10


ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'H_minus_trace'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '0.1'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

logger = config_logger()

IP1 = '192.168.0.44'
IP2 = '192.168.0.45'
IP3 = '192.168.0.46'

pet1 = FakeET7000(IP1, logger=logger, timeout=0.15, type='7026')
pet2 = FakeET7000(IP2, logger=logger, timeout=0.15, type='7015')
pet3 = FakeET7000(IP3, logger=logger, timeout=0.15, type='7026')

# Создаем три клиента по протоколу модбас - библиотека pyModbusTCP, смотри интернет как пользоваться

# первый клиент для первого АЦП, указывается айпи, порт
client1 = ModbusClient(host='192.168.0.44', port=502, auto_open=True, auto_close=True, timeout=0.15)
# массив его каналов, всего пять
chan1 = [Channel(0, -10, 10), Channel(1, -10, 10), Channel(2, -10, 10), Channel(3, -10, 10), Channel(4, -10, 10),
         Channel(5, -10, 10)]

# аналогично для второго ацп, термопары
client2 = ModbusClient(host='192.168.0.46', port=502, auto_open=True, auto_close=True, timeout=0.15)
chan2 = [Channel(0, -600, 600), Channel(1, -600, 600), Channel(2, -600, 600), Channel(3, -600, 600),
         Channel(4, -600, 600), Channel(5, -600, 600), Channel(6, -600, 600)]

# третьего
client3 = ModbusClient(host='192.168.0.45', port=502, auto_open=True, auto_close=True, timeout=0.15)
chan3 = [Channel(0, -10, 10), Channel(1, -10, 10), Channel(2, -10, 10), Channel(3, -10, 10), Channel(4, -10, 10),
         Channel(5, -10, 10)]

# создаем массив кривых которые будут отображаться на графике
curves = [Curve(0, 20, [255, 0, 0], "beam current"), Curve(0, 8e-5, [255, 255, 0], "vacuum high"),
          Curve(0, 150, [200, 200, 0], "T yarmo"), Curve(0, 300, [200, 100, 0], "T plastik"),
          Curve(0, 20, [250, 100, 100], "current 2"), Curve(0, 125, [100, 100, 250], "gas flow"),
          Curve(0, 8e-5, [0, 255, 255], "vacuum tube"),
          Curve(0, 1e-1, [0, 150, 130], "vacuum low")]  # , Curve(0,1e-2,[100,100,100])


# основной класс окна, используется библиотека PyQt
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.logger = logger
        uic.loadUi(UI_FILE, self)
        self.resize(QSize(480, 640))                 # size
        self.move(QPoint(50, 50))                    # position
        self.setWindowTitle(APPLICATION_NAME)        # title
        self.setWindowIcon(QtGui.QIcon('icon.png'))  # icon
        self.setWindowTitle("ICP DAS Measurements")
        #
        restore_settings(self, file_name=CONFIG_FILE)
        # save_settings(self, file_name=CONFIG_FILE)
        # welcome message
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')
        # график pyqtgraph и слайдер
        #self.graph = pg.GraphicsLayoutWidget(parent=self)
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

        # создаем пустой массив в котором будут храниться все точки графиков
        self.data = []
        for i in range(len(curves)):
            self.data.append([])  # на каждую кривую добавляем по элементу

        # массив, в котором будет храниться история всех значений для записи в файл
        self.hist = []
        # массив времени в миллисекундах раз в секунду
        self.time = []

        # стандартный таймер - функция cycle будет вызываться каждую секунду
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.cycle)
        self.timer.start(1000)

        # вроде что-то ненужное, оставил на всякий случай
        self.t = QtCore.QTime()
        self.t.start()

        # большой шрифт для основных значений
        big_font = QtGui.QFont("Times", 12, QtGui.QFont.Bold)

        # основные значения (ток, давление и т.п)
        self.vals = [self.lineEdit_1, self.lineEdit_2, self.lineEdit_3, self.lineEdit_4, self.lineEdit_5]

        # добавляем кнопку разворачивания окна со значениями напряжений ацп
        self.bigbut = self.pushButton
        self.bigbut.clicked.connect(self.bigPress)  # при нажатии срабатывает метод bigPress
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

        self.writeN = 0  # счетчик для записи в файл каждые 10 секунд

        # генерация имени файла для записи истории
        self.fname = "error"
        d = QtCore.QDate.currentDate()  # текущая дата
        # цикл поиска свободного имени файла
        for i in range(100):
            name = str(d.day()) + "-" + str(d.month()) + "-" + str(d.year())  # имя файла в виде день-месяц-год
            if i > 0: name += " " + str(i)  # если цикл не первый, прибавляем к имени файла цифру
            name += ".txt"  # добавляем формат
            if not os.path.isfile(
                    "logs\\" + name):  # если такого файла нет, то выходим из цикла и сохраняем имя, если нет то продолжаем (цифра увеличится на единицу)
                self.fname = name
                break

    # функция устанавливает значение канала(LineEdit) в виде числа со степенью
    def setChannelSci(self, chan, val):
        chan.setText("{:.2E}".format(val))

    # функция устанавливает значение канала(LineEdit) в виде числа с N цифр после запятой
    def setChannelEng(self, chan, val, N=3):
        chan.setText(("{:." + str(N) + "f}").format(val))

    # функция вызывается при нажатии на кнопку развернуть окно и увеличивает или уменьшает его размер
    def bigPress(self):
        if self.pushButton.isChecked():
            self.listWidget.show()
        else:
            self.listWidget.hide()

    # Функция - основной цикл. Вызвается раз в секунду
    def cycle(self):
        # СЧИТЫВАНИЕ И ВЫВОД ЗНАЧЕНИЙ
        try:
            # считываем значения напряжения с первого ацп в массив volt
            if pet1.type != 0:
                volt = pet1.ai_read()
            else:
                volt = [999.] * 5
            for i in range(len(volt)):
                if isnan(volt[i]):
                    volt[i] = 999.
            #volt = []
            # проходим по всем каналам которые мы добавили в самом верху
            # for chan in chan1:
            #     # ! b = client1.read_input_registers(chan.addr,1)#функция считывания байтового значения из ацп по протоколу модбас
            #     b = [0, 0]
            #     if b is None:  # если вернула None то есть какая-то ошибка - скорее всего нет подключения - тогда задаем значение 666
            #         volt.append(666)
            #         print("chan error1")
            #     else:
            #         if len(b) > 0:  # функция вернула массив данных, мы запрашивали один канал так что массив размера один если он меньлше чем один задаем значение 666 - ошибка
            #             volt.append(toV(b[0], chan.min,
            #                             chan.max))  # если нет ошибки, то задаем значение функции toV от первого элемента массива (по идее единственного). toV как раз преобразует байтовое значение в вольты, минимальное и максимальное значение берем из канала
            #         else:
            #             print("chan error2")
            #             volt.append(666)
            #
            # считываем значения напряжения со второго ацп (третий клиент так как второй это термопары) в массив volt2
            if pet3.type != 0:
                volt2 = pet3.ai_read()
            else:
                volt2 = [999.] * 5

            # volt2 = []
            # for chan in chan3:
            #     b = client3.read_input_registers(chan.addr, 1)
            #     if b is None:
            #         volt2.append(666)
            #         print("chan error3", chan.addr)
            #     else:
            #         if len(b) > 0:
            #             volt2.append(toV(b[0], chan.min, chan.max))
            #         else:
            #             print("chan error4", chan.addr)
            #             volt2.append(666)
            #
            # Заполняем значения напряжений АЦП тем что считали чтобы их увидел пользователь
            # for i in range(6):
            #     self.vols[i].setValue(volt[i])
            #     if volt[i] == 666: volt[i] = 0
            self.listWidget.clear()
            self.listWidget.addItem(IP1)
            for _v in volt:
                self.listWidget.addItem(str(_v))
            self.listWidget.addItem(' ')
            self.listWidget.addItem(IP3)
            for _v in volt2:
                self.listWidget.addItem(str(_v))

            # Из напряжений рассчитываем основные значения
            curr = -volt2[5] * 1000 / 92.93  # ток пучка mA
            if volt2[1] >= 666:
                vacH = 0.0  # вакуум в бочке
            else:
                vacH = pow(10, 1.667 * volt2[1] - 11.46)  # вакуум в бочке
            if volt[5] >= 666:
                vacL = 0.0  # вакуум в бочке
            else:
                vacL = pow(10, volt[5] - 5.625)  # форвакуум
            if volt2[0] >= 666:
                vacT = 0.0  # вакуум в бочке
            else:
                vacT = pow(10, 1.667 * volt2[0] - 11.46)  # вакуум в трубке
            curr2 = -volt2[5] * 10  # ток 2 mA - хз что это
            flow = ((-volt2[3] * 1000 / 102) - 4) * 100 / 16  # поток газа

            # Теперь записываем основные значения чтобы их увидел пользователь
            self.setChannelEng(self.vals[0], curr, 3)
            self.setChannelSci(self.vals[1], vacH)
            self.setChannelSci(self.vals[2], vacT)
            self.setChannelSci(self.vals[3], vacL)
            self.setChannelEng(self.vals[4], flow, 1)

            # считываем температуру аналогично напряжению
            if pet2.type != 0:
                temp = pet2.ai_read()
            else:
                temp = [999.] * 7
            self.listWidget.addItem(' ')
            self.listWidget.addItem(IP2)
            for _v in temp:
                self.listWidget.addItem(str(_v))

            # temp = []
            # for chan in chan2:
            #     # !            b = client2.read_input_registers(chan.addr,1)
            #     b = [0, 0]
            #     if b is None:
            #         temp.append(6666)
            #         print("chan error5")
            #     else:
            #         if len(b) > 0:
            #             temp.append(toV(b[0], chan.min, chan.max))
            #         else:
            #             temp.append(6666)
            # задаем значения температуры диафрагмы для пользователя
            self.Td[1].setValue(temp[1])
            self.Td[2].setValue(temp[6])
            self.Td[3].setValue(temp[3])
            self.Td[4].setValue(temp[2])
            # считаем средние значения и выводим их для пользователя
            for i in range(1, 5):
                j = i + 1
                if j > 4: j = 1
                self.Tds[i].setValue((self.Td[i].value() + self.Td[j].value()) / 2)
            # задаем температуры ярма и пластика
            Tyarmo = temp[5]
            Tplastik = temp[0]
            # выводим их для пользователя
            self.T1.setValue(Tyarmo)
            self.T2.setValue(Tplastik)
            self.T1.setStyleSheet('background-color:white; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            self.T2.setStyleSheet('background-color:white; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            # если больше некоторых значений то значение краснеет
            if self.T1.value() > 120: self.T1.setStyleSheet('background-color:red; font: 75 12pt "MS Shell Dlg 2"; font: bold;')
            if self.T2.value() > 250: self.T2.setStyleSheet('background-color:red; font: 75 12pt "MS Shell Dlg 2"; font: bold;')

            # ГРАФИК И ИСТОРИЯ

            # Шкала времени
            dt = QtCore.QDateTime.currentDateTime()
            self.time.append(
                dt.currentMSecsSinceEpoch())  # каждый цикл добавляем в этот массив значение времени в миллисекундах

            # рассчитываем значение отступа по времени в зависимости от положения слайдера чтобы можно было перемещатся по графику
            offset = (dt.currentMSecsSinceEpoch() - self.time[0]) * (10000 - self.slider.value()) / 10000

            # self.T1.setStyleSheet("background-color:red")

            # # Предупреждение, если слайдер сдвига графика не в конце то делаем его красным
            # if self.slider.value() != self.slider.maximum():
            #     self.slider.setStyleSheet("background-color:red")
            # else:
            #     self.slider.setStyleSheet("background-color:white")

            # задаем границы оси Х графика (время) с учетом отступа. Ширина 15 минут
            self.plt.setXRange(dt.currentMSecsSinceEpoch() - 15 * 60 * 1000 - offset, dt.currentMSecsSinceEpoch() - offset)
            # print(self.plt.getXRange)
            # ax = self.plt.getAxis('bottom')
            # strt = int( (dt.currentMSecsSinceEpoch()-15*60*1000-offset)/60000 )
            # tx = [(value*60000,str(value*60000)) for value in range(strt,strt+16) ]
            # ax.setTicks([tx, [])

            # Задаем желаемое значение для каждой кривой, которую мы добавили в самом верху
            curves[0].set_value(curr)
            curves[1].set_value(vacH)
            curves[2].set_value(Tyarmo)
            curves[3].set_value(Tplastik)
            curves[4].set_value(curr2)
            curves[5].set_value(flow)
            curves[6].set_value(vacT)
            curves[7].set_value(vacL)

            # находим текущую кривую - ту которая выбрана в легенде
            curr_curve = curves[self.legend.currentIndex()]
            # задаем Y диапазон на графике в соответствие с этим диапазоном у текущей кривой
            self.plt.setYRange(curr_curve.min, curr_curve.max)
            # self.plt.setXWidth(60*1000)
            # self.plt.AxisItem
            self.plt.clear()  # очистка графика

            # цикл отрисовки всех кривых
            n = 0
            for curve in curves:
                # добавляем к массиву всех значений данной кривой нормализованное (минимум - 0, максимум - 1) значение даной кривой
                self.data[n].append((curve.value - curve.min) / (curve.max - curve.min))

                new_data = []  # массив для отрисовки в соответствие с текущими осями
                for i in range(len(self.data[n])):
                    new_data.append((curr_curve.max - curr_curve.min) * self.data[n][
                        i] + curr_curve.min)  # новый массив это старый (нормализованный) но у которго максимум и минимум не 1 и о а максимум и минимум curr_curve

                # отрисовываем данную кривую
                self.plt.plot(self.time, new_data, pen=(curve.rgb[0], curve.rgb[1], curve.rgb[2]))
                n += 1

            # запись истории в файл
            # массив заголовков - названия всех записываемых значений, первое всегда время
            headers = ['time', 'beam current', 'vacuum high', 'T yarmo', 'T plastik', 'current 2', 'gas flow',
                       'vacuum tube', 'vacuum low']
            if len(self.hist) == 0:
                # если история еще пустая, добавляем в нее пустой массив для каждого заголовка
                for i in range(len(headers) - 1): self.hist.append([])

            # добавляем очередное значение, значения должны соответствовать заголовкам
            self.hist[0].append(curr)
            self.hist[1].append(vacH)
            self.hist[2].append(Tyarmo)
            self.hist[3].append(Tplastik)
            self.hist[4].append(curr2)
            self.hist[5].append(flow)
            self.hist[6].append(vacT)
            self.hist[7].append(vacL)

            # Каждые 10 циклов записываем историю в файл с именем fname которое мы определили выше
            self.writeN += 1
            if self.writeN > 10:
                print("write to file")
                f = open("logs\\" + self.fname, "w")
                for h in headers: f.write(h + "\t")  # запись заголовков
                f.write("\n")
                t = QtCore.QDateTime()
                for i in range(len(self.time)):  # цикл для каждого момента времени
                    # преобразуем миллисекунды в час:минута:секунда и записываем в файл
                    t.setTime_t(self.time[i] / 1000)
                    f.write(t.toString('hh:mm:ss') + '\t')
                    for j in range(len(self.hist)):  # следом записываем все соответсвующий значения истории
                        if self.hist[j][i] == 666 or self.hist[j][i] == 6666:
                            f.write(str('0\t'))
                        else:
                            f.write(str(self.hist[j][i]) + '\t')
                    f.write('\n')
                f.close()
                self.writeN = 0
        except:
            log_exception(self)

    def on_quit(self):
        save_settings(self, file_name=CONFIG_FILE)



# Стандартный код для  PyQt приложения - создание Qt приложения, окна и запуск
app = QApplication([])
window = MainWindow()
app.aboutToQuit.connect(window.on_quit)
window.show()
code = app.exec_()
client1.close()
client2.close()
exit(code)
