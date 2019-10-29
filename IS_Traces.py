# Используемые библиотеки
from pyModbusTCP.client import ModbusClient

from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtWidgets import *
import pyqtgraph as pg
import time

import numpy as np
import os

# Класс, отвечающий за отображение оси времени (чтобы были не миллисекунды а время в формате hh:mm), сделано по гайду из интернета
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
            t.setTime_t(value / 1000)
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
    def __init__(self, Min, Max, RGB, Name=""):
        self.min = Min  # минмимальное значение на оси y
        self.max = Max  # максимальное
        self.rgb = RGB  # цвет - массив(list) из трез значение [r,g,b]
        self.value = 0  # текущее значение
        self.name = Name  # имя для отображения в легенде

    def setValue(self, val):  # функция чтобы задать значение
        self.value = val


# преобразования байтового значения которое выдает АЦП (по сути целочисленное) в значение напряжения
def toV(b, Min, Max):
    # обрабатывается вусего 2 случая - минимум нулевой
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


class ICP_DAS_ET7000:
    # Класс канала, представляет канал АЦП
    class Channel:
        def __init__(self, addr, min, max, convert=Channel.toV):
            self.addr = addr  # номер канала на АЦП
            self.min = min  # минимальное значение в вольтах
            self.max = max  # максимальное
            self.convert = convert

        # преобразования байтового значения которое выдает АЦП (по сути целочисленное) в значение напряжения
        def toV(self, b):
            # обрабатывается вусего 2 случая - минимум нулевой
            if self.min == 0 and self.max > 0:
                return self.max * b / 0xffff
                # и минимум по модулю равен максимуму
            if self.min == -self.max and self.max > 0:
                one = 0xffff / 2
                if b <= one:
                    return self.max * b / one
                else:
                    return -self.max * (0xffff - b) / one
            # в других случаях ошибка
            return float('nan')

    def __init__(self, host, port, timeout=0.15):
        self._host = host
        self._port = port
        self._client = ModbusClient(host=self._host, port=self._port, auto_open=True, auto_close=True, timeout=timeout)
        self.channels = []

    def read(self):
        pass

    # Создаем три клиента по протоколу модбас - библиотека pyModbusTCP, смотри интернет как пользоваться


# вот первый клиент для первого АЦП, указывается айпи, порт
client1 = ModbusClient(host='192.168.0.46', port=502, auto_open=True, auto_close=True, timeout=0.15)
# а вот массив его каналов, всего пять
chan1 = [Channel(0, -10, 10), Channel(1, -10, 10), Channel(2, -10, 10), Channel(3, -10, 10), Channel(4, -10, 10),
         Channel(5, -10, 10)]

# аналогично для второго ацп, термопары
client2 = ModbusClient(host='192.168.0.45', port=502, auto_open=True, auto_close=True, timeout=0.15)
chan2 = [Channel(0, -600, 600), Channel(1, -600, 600), Channel(2, -600, 600), Channel(3, -600, 600),
         Channel(4, -600, 600), Channel(5, -600, 600), Channel(6, -600, 600)]

# третьего
client3 = ModbusClient(host='192.168.0.47', port=502, auto_open=True, auto_close=True, timeout=0.15)
chan3 = [Channel(0, -10, 10), Channel(1, -10, 10), Channel(2, -10, 10), Channel(3, -10, 10), Channel(4, -10, 10),
         Channel(5, -10, 10)]

# создаем массив кривых которые будут отображатся на графике
curves = [Curve(0, 20, [255, 0, 0], "beam current"), Curve(0, 2e-4, [200, 200, 200], "vacuum high"),
          Curve(0, 150, [200, 200, 0], "T yarmo"), Curve(0, 300, [200, 100, 0], "T plastik"),
          Curve(0, 20, [250, 100, 100], "current 2"), Curve(0, 125, [100, 100, 250], "gas flow"),
          Curve(0, 2e-4, [150, 150, 150], "vacuum tube"),
          Curve(0, 1e-1, [0, 150, 130], "vacuum low")]  # , Curve(0,1e-2,[100,100,100])


# основной класс окна, используется библиотека PyQt
class MainWindow(QMainWindow):
    def __init__(self):
        # окно
        super(MainWindow, self).__init__()
        self.setWindowTitle("ICP DAS Measurements")
        self.setGeometry(0, 690, 1110, 350)

        # создаем элементы для графика: сам график pyqtgraph и слайдер чтобы перемещатся по шкале времени
        self.graph = pg.GraphicsLayoutWidget(parent=self)
        self.plt = self.graph.addPlot(axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.graph.resize(900, 330)
        self.plt.showGrid(x=True, y=True, alpha=1)
        # слайдер, что знаят методы можно найти в гугле по запросу PyQt QSlider, аналогично с другими Q-элементами
        self.slider = QSlider(QtCore.Qt.Horizontal, self)
        self.slider.resize(800, 20)
        self.slider.move(100, 330)
        self.slider.setMinimum(0)
        self.slider.setMaximum(10000)
        self.slider.setValue(10000)

        # легенда для графика
        self.legend = QComboBox(self)
        self.legend.move(0, 330)
        self.legend.resize(100, 20)
        n = 0
        # для каждой кривой добавляем элемент в легенде
        # также создаем картнку 10х10 нужного цвета и делаем ее иконкой для элемента
        for curve in curves:
            p = QtGui.QPixmap(10, 10)
            p.fill(QtGui.QColor(curve.rgb[0], curve.rgb[1], curve.rgb[2]))
            i = QtGui.QIcon(p)
            self.legend.addItem(curve.name)
            self.legend.setItemIcon(n, i)
            n += 1

        # создаем пустой массив в котором будут храниться все точки графиков
        self.data = []
        for i in range(len(curves)): self.data.append([])  # на каждую кривую добавляем по элементу

        # массив в котром будет хранится история всех значений, которая будет зааписыватся в файл
        self.hist = []

        # стандартный таймер - функция cycle будет вызыватся каждую секунду
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.cycle)
        self.timer.start(1000)
        self.time = []  # массив времени - по сути сюда записывается время в миллисекундах каждую секунду (ниже). Использвется для построения графика и записи в файл истории

        # вроде что-то ненужное, оставил на всякий случай
        self.t = QtCore.QTime()
        self.t.start()

        # Для АЦП 1 создаем спинбоксы с значениями все напряжений
        self.vols = []  # массив всех значений(спинбоксов) с напряжениями чтобы потом их использовать
        for i in range(6):
            s = QDoubleSpinBox(self)  # число
            l = QLabel("V" + str(i), self)  # надпись перед ним
            s.value = 0
            s.move(1130, 10 + 30 * i)
            l.move(1110, 10 + 30 * i)
            s.resize(70, 20)
            s.setMaximum(666)
            s.setMinimum(-666)
            s.setDecimals(3)  # отображать три знака
            l.resize(120, 20)
            self.vols.append(s)  # добавляем значение в массив со спинбоксами

        # аналогично для второго ацп
        self.vols2 = []
        for i in range(6):
            s = QDoubleSpinBox(self)
            l = QLabel("V" + str(i), self)
            s.value = 0
            s.move(1130, 190 + 30 * i)
            l.move(1110, 190 + 30 * i)
            s.resize(70, 20)
            s.setMaximum(666)
            s.setMinimum(-666)
            s.setDecimals(3)
            l.resize(120, 20)
            self.vols2.append(s)

        # большой шрифт для основных значений
        bigFont = QtGui.QFont("Times", 11, QtGui.QFont.Bold)

        # основные значения (ток, давление и т.п)
        self.vals = []  # массив всех значений(тут это текстовые окна лайн едит) чтобы потом их использовать
        self.labels = []  # массив всех подписей чтобы ниже заполнить каждую из них

        # цикл создает 5 значений выстроеных вертикально
        for i in range(5):
            s = QLineEdit(self)
            l = QLabel("channel " + str(i), self)  # изначально они подписаны как channel N, ниже названия меняются
            s.setText("0")  # изначально значение 0
            s.move(1020, 10 + 30 * i)
            l.move(910, 10 + 30 * i)
            s.resize(85, 25)
            l.resize(110, 25)
            l.setFont(bigFont)
            s.setFont(bigFont)
            # добавляем значения и подписи в массив
            self.vals.append(s)
            self.labels.append(l)

        # меняем названия (подписи) на те что надо
        self.labels[0].setText("Beam current")
        self.labels[1].setText("Vacuum High")
        self.labels[2].setText("Vacuum Tube")
        self.labels[3].setText("Vacuum Low")
        self.labels[4].setText("Gas flow")

        # добавляем кнопку разворачивания основного окна чтобы показывались значения напряжений ацп
        self.big = False  # развернуто ли окно
        self.bigbut = QPushButton('volt', self)  # кнопка
        self.bigbut.move(1050, 187)
        self.bigbut.resize(40, 20)
        self.bigbut.clicked.connect(self.bigPress)  # при нажатии срабатывает метод bigPress

        # надпись
        l = QLabel("Diaphragm Temp", self)
        l.resize(120, 20)
        l.move(967, 240)

        self.Td = [0, 0, 0, 0, 0]  # массив значений температуры диафрагмы, нулевой элемент не использвется
        for i in range(1, 5):  # 1,2,3,4 - по часовой, начало из левого верхнего угла
            self.Td[i] = QDoubleSpinBox(self)
            self.Td[i].resize(50, 20)
            self.Td[i].setMaximum(7000)
            self.Td[i].setReadOnly(True)
            self.Td[i].setDecimals(0)
            # располагаются по кругу
            if i < 3:
                self.Td[i].move(800 + i * 120, 210)
            else:
                self.Td[i].move(1040 - (i - 3) * 120, 270)

        self.Tds = [0, 0, 0, 0, 0]  # массив средних значений между соседними термопарами
        for i in range(1, 5):  # 1,2,3,4 - по часовой, начало из левого верхнего угла
            self.Tds[i] = QDoubleSpinBox(self)
            self.Tds[i].resize(50, 20)
            self.Tds[i].setMaximum(7000)
            self.Tds[i].setReadOnly(True)
            self.Tds[i].setDecimals(0)
            if i == 1 or i == 3:
                self.Tds[i].move(980, 200 + (i - 1) * 38)
            else:
                self.Tds[i].move(1050 - (i - 2) * 70, 240)
        # значение температур ярма с подписью
        self.T1 = QDoubleSpinBox(self)
        self.T1.resize(50, 20)
        self.T1.move(920, 320)
        self.T1.setMaximum(7000)
        self.T1.setReadOnly(True)
        self.T1.setDecimals(0)
        l = QLabel("Temp Yarmo", self)
        l.resize(120, 20)
        l.move(920, 298)

        # температура пластика
        self.T2 = QDoubleSpinBox(self)
        self.T2.resize(50, 20)
        self.T2.move(1040, 320)
        self.T2.setMaximum(7000)
        self.T2.setReadOnly(True)
        self.T2.setDecimals(0)
        l = QLabel("Temp Plastik", self)
        l.resize(120, 20)
        l.move(1040, 298)

        self.writeN = 0  # счетчик для записи в файл каждые 10 секунд, использвется ниже

        # генерация имени фалй для записи истории
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
        if self.big:
            self.resize(1110, 350)
        else:
            self.resize(1210, 350)
        self.big = not self.big

    # функция - основной цикл. вызвается раз в секунду
    def cycle(self):

        # СЧИТЫВАНИЕ И ВЫВОД ЗНАЧЕНИЙ

        # считываем значения напряжения с первого ацп в массив volt
        volt = []
        # проходим по всем каналам которые мы добавили в самом верху
        for chan in chan1:
            b = client1.read_input_registers(chan.addr,
                                             1)  # функция считывания байтового значения из ацп по протоколу модбас
            if b is None:  # если вернула None то есть какая-то ошибка - скорее всего нет подключения - тогда задаем значение 666
                volt.append(666)
                print("chan error")
            else:
                if len(b) > 0:  # функция вернула массив данных, мы запрашивали один канал так что массив размера один если он меньлше чем один задаем значение 666 - ошибка
                    volt.append(toV(b[0], chan.min,
                                    chan.max))  # если нет ошибки, то задаем значение функции toV от первого элемента массива (по идее единственного). toV как раз преобразует байтовое значение в вольты, минимальное и максимальное значение берем из канала
                else:
                    print("chan error")
                    volt.append(666)

        # считываем значения напряжения со второго ацп (третий клиент так как второй это термопары) в массив volt2
        volt2 = []
        for chan in chan3:
            b = client3.read_input_registers(chan.addr, 1)
            if b is None:
                volt2.append(666)
                print("chan error")
            else:
                if len(b) > 0:
                    volt2.append(toV(b[0], chan.min, chan.max))
                else:
                    print("chan error")
                    volt2.append(666)

        # Заполняем значения напряжений АЦП тем что считали чтобы их увидел пользователь
        for i in range(6):
            self.vols[i].setValue(volt[i])
            if volt[i] == 666: volt[i] = 0
        for i in range(6):
            self.vols2[i].setValue(volt2[i])
            if volt2[i] == 666: volt2[i] = 0

        # Из напряжений расчитываем основные значения
        curr = -volt2[2] * 1000 / 400  # ток пучка mA
        vacH = pow(10, 1.667 * volt[3] - 11.46)  # вакуум в бочке
        vacL = pow(10, volt[4] - 5.625)  # форвакуум
        vacT = pow(10, -1.667 * volt2[1] / 2 * 20.66 / 20. - 11.46)  # вакуум в трубке
        curr2 = -volt2[5] * 10  # ток 2 mA - хз что это
        flow = ((-volt2[0] * 1000 / 402) - 4) * 100 / 16  # поток газа

        # Теперь записываем основные значения чтобы их увидел пользователь
        self.setChannelEng(self.vals[0], curr, 3)
        self.setChannelSci(self.vals[1], vacH)
        self.setChannelSci(self.vals[2], vacT)
        self.setChannelSci(self.vals[3], vacL)
        self.setChannelEng(self.vals[4], flow, 1)

        # считываем температуру аналогично напряжению
        temp = []
        for chan in chan2:
            b = client2.read_input_registers(chan.addr, 1)
            if b is None:
                temp.append(6666)
                print("chan error")
            else:
                if len(b) > 0:
                    temp.append(toV(b[0], chan.min, chan.max))
                else:
                    temp.append(6666)
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
        self.T1.setStyleSheet("background-color:white")
        self.T2.setStyleSheet("background-color:white")
        # если больше некоторых значений то значение краснеет
        if self.T1.value() > 120: self.T1.setStyleSheet("background-color:red")
        if self.T2.value() > 250: self.T2.setStyleSheet("background-color:red")

        # ГРАФИК И ИСТОРИЯ

        # Шкала времени
        dt = QtCore.QDateTime.currentDateTime()
        self.time.append(
            dt.currentMSecsSinceEpoch())  # каждый цикл добавляем в этот массив значение времени в миллисекундах

        # рассчитываем значение отступа по времени в зависимости от положения слайдера чтобы можно было перемещатся по графику
        offset = (dt.currentMSecsSinceEpoch() - self.time[0]) * (10000 - self.slider.value()) / 10000

        # self.T1.setStyleSheet("background-color:red")

        # Предупреждение, если слайдер сдвига графика не в конце то делаем его красным
        if self.slider.value() != self.slider.maximum():
            self.slider.setStyleSheet("background-color:red")
        else:
            self.slider.setStyleSheet("background-color:white")

        # задаем границы оси Х графика (время) с учетом отступа. Ширина 15 минут
        self.plt.setXRange(dt.currentMSecsSinceEpoch() - 15 * 60 * 1000 - offset, dt.currentMSecsSinceEpoch() - offset)
        # print(self.plt.getXRange)
        # ax = self.plt.getAxis('bottom')
        # strt = int( (dt.currentMSecsSinceEpoch()-15*60*1000-offset)/60000 )
        # tx = [(value*60000,str(value*60000)) for value in range(strt,strt+16) ]
        # ax.setTicks([tx, [])

        # Задаем желаемое значение для каждой кривой, которую мы добавили в самом верху
        curves[0].setValue(curr)
        curves[1].setValue(vacH)
        curves[2].setValue(Tyarmo)
        curves[3].setValue(Tplastik)
        curves[4].setValue(curr2)
        curves[5].setValue(flow)
        curves[6].setValue(vacT)
        curves[7].setValue(vacL)

        # находим текущую кривую - ту которая выбрана в легенде
        curr_curve = curves[self.legend.currentIndex()]
        # задаем Y диапозон на графике в соответсвие с этим диапозоном у текущей кривой
        self.plt.setYRange(curr_curve.min, curr_curve.max)
        # self.plt.setXWidth(60*1000)
        # self.plt.AxisItem
        self.plt.clear()  # очистка графика

        # цикл отрисовки всех кривых
        n = 0
        for curve in curves:
            # добавляем к массиву всех значений данной кривой нормализованное (минимум - 0, максимум - 1) значение даной кривой
            self.data[n].append((curve.value - curve.min) / (curve.max - curve.min))

            new_data = []  # массив для отрисовки в соотвествие с текущими осями
            for i in range(len(self.data[n])):
                new_data.append((curr_curve.max - curr_curve.min) * self.data[n][
                    i] + curr_curve.min)  # новый массив это старый (нормализованный) но у которго максимум и минимум не 1 и о а максимум и минимум curr_curve

            # отрисовываем данную кривую
            self.plt.plot(self.time, new_data, pen=(curve.rgb[0], curve.rgb[1], curve.rgb[2]))
            n += 1

        # запись истории в файл
        # массив заголовков - названия всех записываемых значений, первое всегда время
        headers = ['time', 'beam current', 'vacuum high', 'T yarmo', 'T plastik', 'current 2', 'gas flow',
                   'vacuum tube', 'vacuum low', 'Tup', 'Tright', 'Tdown', 'Tleft', ]
        if len(self.hist) == 0:
            # если история еще пустая, добавляем в нее пустой массив для каждого заголовка
            for i in range(len(headers) - 1): self.hist.append([])

        # добавляем очередное значение, значения должны соотвествовать заголовкам
        self.hist[0].append(curr)
        self.hist[1].append(vacH)
        self.hist[2].append(Tyarmo)
        self.hist[3].append(Tplastik)
        self.hist[4].append(curr2)
        self.hist[5].append(flow)
        self.hist[6].append(vacT)
        self.hist[7].append(vacL)
        self.hist[8].append(temp[1])
        self.hist[9].append(temp[6])
        self.hist[10].append(temp[3])
        self.hist[11].append(temp[2])

        # Каждые 10 цилов записываем историю в файл с именем fname которое мы определили выше
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


# Стандартный код для  PyQt приложения - создание Qt приложения, окна и запуск
app = QApplication([])
window = MainWindow()
window.show()
code = app.exec_()
client1.close()
client2.close()
exit(code)