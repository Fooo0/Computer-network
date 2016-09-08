# -*- coding: utf-8 -*-
"""
Created on Thu May 12 20:19:19 2016

@author: 宋佳飞
"""

import socket
import sys
import time
import random

class GBNClient:
    def __init__(self, addr):
        self.bufsize = 1028
        self.client = None
        self.ser_addr = addr
        self.seq_size = 20
        self.packetLossRatio = 0.2
        self.ackLossRatio = 0.2
        self.waitSEQ = None
        self.recvSEQ = None

    def printTips(self):    # 打印说明
        print 'Instruction:'
        print '\t -time: get current time.'
        print '\t -quit: exit.'
        print '\t -testgbn[X][Y]: test gbn.'
        print ' '
    
    def Preparation(self):
        try:    # 套接字创建
            self.client = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        except socket.error, err_msg:
            print 'Failed to create socket: ' + err_msg
            sys.exit(1)
        print 'Socket created successfully!'
    
    def loss(self, lossratio):    # 丢与否
        boundary = 100 * lossratio
        dice = random.randint(1,101)    # 随机数
        if dice <= boundary:    # 丢
            return True
        return False
        
    def GBNTest(self):
        print 'Begin to test GBN Protocal, please don\'t abort the process'
        print 'The loss ratio of packet is {0:.2},\
            \n The loss ratio of ack is {1:.2}'.format(self.packetLossRatio, self.ackLossRatio)
        stage = 0
        command = '-testgbn'
        self.client.sendto(command, self.ser_addr)
        while True:
            ser_data, _ = self.client.recvfrom(self.bufsize)
            if stage == 0:    # 等待握手
                if ser_data == '205':
                    print 'Ready for file transmission.'
                    clin_data = '200'
                    self.client.sendto(clin_data, self.ser_addr)
                    stage = 1
                    self.recvSEQ = 0
                    self.waitSEQ = 1
            elif stage == 1:    # 数据传输开始
                smark = ser_data.index('@',0, 3)
                seqc = ser_data[:smark]    # 取序列号
                if seqc == '0':    # 发送完毕
                    print 'Transfer over'
                    break
                if self.loss(self.packetLossRatio):    # 丢包
                    print 'The packet with a seq of ' + seqc + ' loss.'
                    continue
                print 'Receive a packet with seq of ' + seqc
                seq = int(seqc)
                if seq == self.waitSEQ:    # 是期望的seq
                    self.waitSEQ += 1
                    if self.waitSEQ == 21:
                        self.waitSEQ = 1    # 循环seq
                    print 'ser_data:'
                    print ser_data
                    clin_data = seqc    # ack
                    self.recvSEQ = seq
                else:    # 不是期望的seq
                    if self.recvSEQ == 0:    # 第一个包都未收到
                        continue
                    clin_data = str(self.recvSEQ)    # 重复 ack：最近一次的
                if self.loss(self.ackLossRatio):    # 丢ack
                    print 'The ack of ' + clin_data + ' loss.'
                    continue
                self.client.sendto(clin_data, self.ser_addr)    # 发送ack
                print 'Send an ack of ' + clin_data
            time.sleep(0.5)

    def work(self):
        while(True):
            self.printTips()
            command = raw_input('Your command:')
            if command == '-time' or command == '-quit':    # -time 或者 -quit
                self.client.sendto(command, self.ser_addr)
                ser_data, _ = self.client.recvfrom(self.bufsize)
                print ser_data
                if ser_data == 'Good bye!':
                    break
                continue
            elif command[:8] == '-testgbn':    # gbntest
                tmpc = command.split('[')
                parl1 = len(tmpc[1])    # 处理参数一
                if parl1 > 1:
                    plr = float(tmpc[1][:parl1 - 1])
                    self.packetLossRatio = plr
                parl2 = len(tmpc[2])    # 处理参数二
                if parl2 > 1:
                    alr = float(tmpc[2][:parl2 - 1])
                    self.ackLossRatio = alr
                self.GBNTest()
            else:
                print 'Wrong command'
                sys.exit(0)
        self.client.close()    # 关闭
        
        
        
ser_host = '127.0.0.1'    # 服务器地址
ser_port = 8080    # 服务器端口
# 建立GBNClient
gclient = GBNClient((ser_host, ser_port))
gclient.Preparation()
# 开始工作
gclient.work()
