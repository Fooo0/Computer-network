# -*- coding: utf-8 -*-
"""
Created on Sat May 07 13:50:11 2016

@author: 宋佳飞
"""

import socket
import select
import sys
import thread

class FProxy:
    def __init__(self, socketc):
        self.client, self.client_ad = socketc.accept()
        self.server = None
        self.bufsize = 4096
        self.method = None
        self.host = None
        self.cookie = None
    
    def connectClient(self):
        try:
            request = self.client.recv(self.bufsize)    # 来自用户的报文
        except socket.error, err_msg:  
            print "Error receiving data: %s" % err_msg 
            sys.exit(1) 
        if self.client_ad[0] == '127.0.0.1' or not request:
            return None
        return request
        
    def getPort(self, request):
        tmps = request.split('\r\n')
        firstline = tmps[0]
        #print 'First line from client ---->>>> ' + firstline
        seg = firstline.split()
        self.method = seg[0]    # 方法，get/post
        if self.method != 'POST' and self.method != 'GET':
            #print 'Unable to deal with request: %s' % self.method
            sys.exit(1)
            
        for line in tmps:
            if line:
                if line[0] == 'H':    # host
                    self.host = line[6:]
                    print 'Get host ---- >>>>'
                    print self.host
                    print '<<<< ---- over'
                if line[:6] == 'Cookie':    # cookie
                    self.cookie = line[8:]

        
        tar_url = seg[1]    # host
        chep = tar_url.replace('http:','')        
        if ':' in chep:
            tmps = tar_url.split(':')
            port = int(tmps[1])    # 指定端口
        else:
            port = 80    # 默认端口
            
        if self.host == 'www.baidu.com':    # 匹配被过滤的网站
            port = 0
        elif self.host == 'cn.bing.com':    # 匹配作为“钓鱼鱼饵”的网站
            port = 1
        return port
    
    def keepConnection(self):
        socs = [self.client, self.server]
        while True:
            rs,ws,ers = select.select(socs, [], socs, 3)    # 异步socket处理
            if ers:
                break
            for soc in rs:
                try:
                    data = soc.recv(self.bufsize)
                except socket.error, err_msg:  
                    print "Error receiving data: %s" % err_msg 
                    sys.exit(1)
                if data:
                    if soc is self.client:
                        try:
                            self.server.sendall(data)    # 向服务器发送用户的数据
                        except socket.error:
                            print 'Failed to send to server!'
                            sys.exit(1)
                    elif soc is self.server:
                        try:
                            self.client.sendall(data)    # 向用户发送服务器的数据
                        except socket.error:
                            print 'Failed to send to server!'
                            sys.exit(1)
                else:
                    break
    
        self.server.close()    # 关闭
        self.client.close()
                
                
    def connectServer(self, request):
        por = self.getPort(request)
        if self.host:
            if por == 0:    # 访问被过滤的网站的用户收到以下forbi报文
                forbi = '''HTTP/1.1 403 Forbidden\r\nDate: Mon, 09 May 2016 07:46:53 GMT\r\nServer: Apache\r\nContent-Type: text/html\r\n\r\n'''
                self.client.sendall(forbi)
            elif por == 1:    # 访问被作为“钓鱼鱼饵”的网站的用户收到以下fake报文，引导向钓鱼网站
                fake = '''HTTP/1.1 200 OK\r\nDate: Mon, 09 May 2016 07:46:53 GMT\r\nServer: Apache\r\nContent-Type: text/html\r\n\r\n<html><head><title>Wooo!!!</title></head><body>Bingo!!!!</body></html>'''
                self.client.sendall(fake)
            else:
                # 获取用于创建socket对象的信息
                fami, soctyp, proto, _, addr = socket.getaddrinfo(self.host, por)[0]    # 可能有很多，取第一个
                try:
                    self.server = socket.socket(fami, soctyp, proto)    # 创建到 用户目标服务器的套接字
                except socket.error, err_msg:
                    print 'Failed to creat server_socket: %s' % err_msg
                    sys.exit(1)
                    
                try:   
                    self.server.connect(addr)    # 连接服务器
                except socket.gaierror, err_msg:  
                    print "Address-related error connectiong to server: %s" % err_msg  
                    sys.exit(1)
                except socket.error, err_msg:  
                    print "Connection error: %s" % err_msg  
                    sys.exit(1)
        
                try:
                    self.server.sendall(request)    # 向服务器发送用户的数据
                except socket.error:
                    print 'Failed to send to server!'
                    sys.exit(1)
                self.keepConnection()     # 保持客户与服务器的通话
        else:
            print 'Failed to get host'
            sys.exit(1)
        
    def run(self):
        request = self.connectClient()
        if request:
            self.connectServer(request)
        else:    # 被过滤的用户收到 以下out报文
            out = '''HTTP/1.1 200 OK\r\nDate: Mon, 09 May 2016 07:46:53 GMT\r\nServer: Apache\r\nContent-Type: text/html\r\n\r\n<html><head><title>Warning</title></head><body>Your are not allowed to surf the Internet</body></html>'''
            self.client.sendall(out)
            

print 'Prepare socket ...'           
host = ''    # 任意地址
port = 8080
backlog = 5

try:    # 创建服务用户套接字
    fpserver = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
except socket.error, err_msg:
    print 'Failed to creat fpserver socket: %s' % err_msg
    sys.exit(1)
print 'Creat fpserver socket successful!'

try:    # 绑定
    fpserver.bind((host, port))
except socket.error, err_msg:
    print 'Failed to bind fpserver socket: %s' % err_msg
    sys.exit(1)
print 'Bind fpserver socket successful!'

fpserver.listen(backlog)

while True:
    thread.start_new_thread(FProxy(fpserver).run, ())    # 多线程