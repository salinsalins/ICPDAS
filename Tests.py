# -*- coding: utf-8 -*-

import threading
import time

flag = True


def loop():
    mydata = threading.local()
    mydata.t0 = time.time()
    for i in range(10000):
        time.sleep(0.002)
        # a = i ** i
        # if not flag:
        #     break
    print('loop', threading.get_ident(), time.time() - mydata.t0)


def proc(n):
    mydata = threading.local()
    mydata.t0 = time.time()
    for i in range(n):
        a = i**i
    print('proc', threading.get_ident(), time.time() - mydata.t0)

loop()
proc(10000)

t0 = time.time()

#th1 = threading.Thread(target=proc, args=(5000,))
th1 = threading.Thread(target=loop)
th2 = threading.Thread(target=proc, args=(10000,))

th2.start()
th1.start()

#flag = False
th2.join()
# flag = False
th1.join()

print('End', time.time() - t0)

