# -*- coding: utf-8 -*-
"""
Created on Tue May 10 18:30:05 2016

@author: 宋佳飞
"""

import socket
import sys
import time

class GBNServer:
    def __init__(self):
        self.bufsize = 1026
        self.win_size = 10
        self.seq_size = 20
        self.ack = [True for i in range(self.seq_size)]
        self.expACK = None    # 等待的ack
        self.curSEQ = None    # 当前（下一个可能可用seq）
        self.totalSEQ = None    # 总数
        self.server = None
        self.clin_addr = None

    def Preparation(self, address):
        try:    # 套接字创建
            self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        except socket.error, err_msg:
            print 'Failed to create socket: ' + err_msg
            sys.exit(1)
        print 'Socket created successfully!'
        
        self.server.setblocking(0)    # 非阻塞
        
        try:    # 绑定
            self.server.bind(address)
        except socket.error, err_msg:
            print 'Failed to bind GBNserver socket: ' + err_msg
            sys.exit(1)
        print 'Bind fpserver socket successful!'

    def getCurTime(self):    # 获取当前时间
        TIMEFORMAT = '%Y-%m-%d %X'    # 时间格式
        return time.strftime(TIMEFORMAT,time.localtime())

    def seqIsAvaliable(self):    # 判断下一个seq是否可用
        distant = self.curSEQ - self.expACK
        distant = distant if distant >= 0 else distant + self.seq_size
        if distant >= self.win_size:    # 窗口装不下
            return False
        if self.ack[self.curSEQ]:    # 没有等待ack
            return True
        return False

    def timeoutHandler(self):    # timeout处理
        print 'Timeout error'
        for i in range(0, self.win_size):    # 使序列号可用
            index = (self.expACK + i) % self.win_size
            self.ack[index] = True
        # 超时之后发送的包都当作没有发送
        lossamount = self.curSEQ - self.expACK
        # 序列号循环使 丢包数 可能为负，为得出真正的 丢包数，为负时需要加上seq_size
        lossamount = lossamount if lossamount >= 0 else lossamount + self.seq_size
        self.totalSEQ = self.totalSEQ - lossamount    # 处理计数
        self.curSEQ = self.expACK    # 下一个可用序列号置为期待的序列号
        

    def ackHandler(self, clin_data):    # ack处理
        ack_index = int(clin_data) - 1
        print 'Received an ack of %d' % (ack_index + 1)
        if self.expACK <= ack_index:
            for i in range(self.expACK, ack_index + 1):    # 累积确认
                self.ack[i] = True
            self.expACK = (ack_index + 1) % self.seq_size
        else:    # 可能是序列号循环导致，也可能是重复 ack
            if self.expACK - ack_index >= 12:    # 序列号循环导致
                for i in range(self.expACK, self.seq_size):    # 累积确认
                    self.ack[i] = True
                for i in range(0, ack_index + 1):    # 累积确认
                    self.ack[i] = True
                self.expACK = ack_index + 1
            # 不处理重复 ack
        time.sleep(0.5)

    def GBNTest(self):
        print 'Begin to test GBN Protocal, please don\'t abort the process'
        print 'Shake hands stage'
        stage = 0    # 阶段
        waitCount = 0    # 计时器
        runFlag = True
        while(runFlag):
            if stage == 0:    # 主动握手
                ser_data = '205'
                self.server.sendto(ser_data, self.clin_addr)
                time.sleep(0.1)
                stage = 1    # 进入等待用户回应阶段
            elif stage == 1:
                try:
                    clin_data, addr = self.server.recvfrom(self.bufsize)
                except socket.error:    # 没有收到数据
                    waitCount += 1
                    if(waitCount > 20):    # 超时
                        runFlag = False
                        print 'Timeout error!'
                        break    # 重新开始
                    time.sleep(0.5)
                    continue
                if addr == self.clin_addr:
                    if clin_data == '200':
                        print 'Begin a file transfer'
                        print 'File size is ' + str(len(data)) + \
                            ' each packet is 1024B and packet total num is ' + \
                            str(packetamout)
                        self.expACK = 0
                        self.curSEQ = 0
                        self.totalSEQ = 0
                        waitCount = 0
                        stage = 2
                else:
                    print 'Stranger'
            elif stage == 2:    # gbn测试正式开始
                if self.seqIsAvaliable():
                    if self.totalSEQ < packetamout:    # 还有数据包需要发送
                        ser_data1 = '%d@' % (self.curSEQ + 1)
                        ser_data2 = data[1024 * self.totalSEQ : \
                            1024 * (self.totalSEQ + 1)]
                        ser_data =  ser_data1 + ser_data2
                        print 'Send a packet with the seq of ',
                        print self.curSEQ + 1
                        print '\t',
                        print ser_data
                        self.server.sendto(ser_data, self.clin_addr)
                        self.curSEQ += 1
                        self.curSEQ = self.curSEQ % self.seq_size    # 循环
                        self.totalSEQ += 1
                        time.sleep(0.5)
                try:
                    clin_data, addr = self.server.recvfrom(self.bufsize)
                except socket.error:    # 没有收到数据
                    waitCount += 1
                    if(waitCount > 20):    # 超时
                        self.timeoutHandler()
                        if self.totalSEQ >= packetamout:    # 数据传输完毕
                            runFlag = False
                            ser_data = '0@'
                            self.server.sendto(ser_data, self.clin_addr)
                        waitCount = 0
                    time.sleep(0.5)
                    continue
                self.ackHandler(clin_data)    # 收到数据
        print 'One time transfer over'


    def work(self):
        while(True):
            try:
                clin_data, self.clin_addr = (self.server).recvfrom(self.bufsize)
            except socket.error:    # 没有收到数据
                time.sleep(0.2)
                continue
            print 'Data from client: ' + clin_data
            if clin_data == '-time':    # 报时
                ser_data = self.getCurTime()
                self.server.sendto(ser_data, self.clin_addr)
            elif clin_data == '-quit':    # 结束
                ser_data = 'Good bye!'
                self.server.sendto(ser_data, self.clin_addr)
            elif clin_data == '-testgbn':    # 测试开始
                self.GBNTest()
            time.sleep(0.4)
        self.server.close()    # 关闭


global data
global packetamout
host = ''    # 任意地址
port = 8080
# 读需要传输的数据
datafile = open('gbndata.txt')
data = datafile.read(1024 * 30)
packetamout = len(data) / 1024
datafile.close() 
# 建立GBNServer
gserver = GBNServer()
gserver.Preparation((host, port))
# 开始工作
gserver.work()