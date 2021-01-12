#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import msvcrt,sys
import requests
import re
import socket
import os
import json
import threading
import hashlib
import sqlite3
import tkinter.filedialog

_FILE_SLIM=100*1024*1024

serverIP = '127.0.0.1'
transIP ='127.0.0.1'
serverPort = 10086
transPort = 8000
#获取当前公网和内网IP
def getIP():
    #获取当前设备公网IP
    req=requests.get("http://txt.go.sohu.com/ip/soip")
    outerIP =re.findall(r'\d+.\d+.\d+.\d+',req.text)#匹配IP地址形式
    #print(outerIP[0])

    #获取当前设备内网IP
    hostname = socket.gethostname()#获取主机名
    innerIP = socket.gethostbyname(hostname)# 获取本机ip
    IP=[outerIP[0],innerIP]
    return IP 

def pwd_input():    
    chars = []   
    while True:  
        try:  
            newChar = msvcrt.getch().decode(encoding="utf-8")  
        except:  
            return input("你很可能不是在cmd命令行下运行，密码输入将不能隐藏:")  
        if newChar in '\r\n': # 如果是换行，则输入结束               
             break   
        elif newChar == '\b': # 如果是退格，则删除密码末尾一位并且删除一个星号   
             if chars:    
                 del chars[-1]   
                 msvcrt.putch('\b'.encode(encoding='utf-8')) # 光标回退一格  
                 msvcrt.putch( ' '.encode(encoding='utf-8')) # 输出一个空格覆盖原来的星号  
                 msvcrt.putch('\b'.encode(encoding='utf-8')) # 光标回退一格准备接受新的输入                   
        else:  
            chars.append(newChar)  
            msvcrt.putch('*'.encode(encoding='utf-8')) # 显示为星号  
    return (''.join(chars) ) 

#发送heartBeat给服务器，保持连接
def heartBeat(sk,usr):
    h='heartBeats'
    sk.sendall(bytes(h.encode("utf-8")))
    #心跳包的协议
    data_to_server = {'user':usr,
                    'status': 'alive', 
                    'pid': os.getpid()
                     }
    data_dumped = json.dumps(data_to_server)#用json格式发送协议
    try:
        sk.sendall(bytes(data_dumped.encode("utf-8")))
        #print ('I - ', os.getpid(), '- am alive.')
        tag=0
    except socket.error:
        print("Send failed!!the server is down")
        #sys.exit()
        tag=1
    try:
        response=sk.recv(1024)
    except: 
        tag=1 
        print("the server is down")
    return tag
#云盘客户端主界面：登录 注册
def mainpage(status):
    # 创建TCP套接字，使用IPv4协议
    while True:
        global usr
        global serviceList
        serviceList=[]
        sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        sk.connect((serverIP,serverPort))
        #获取当前公网内网IP
        IP=getIP()
        innerIP=IP[1]
        outerIP=IP[0]
        status=0
        while (status==0):
            
            print("欢迎登录个人云空间")
            arg = input("注册请输入1，登录请输入2\n")
            
            if arg == "1":
                while True:
                    sk.sendall(bytes(1))
                    name = input("请输入用户名\n")
                    print("请输入密码:")
                    password = pwd_input()
                    print("\n请再次输入密码:")
                    password2 = pwd_input()
                    print("\n")
                    if password != password2:
                        print("两次密码不一致")
                        continue
                    reg={
                            'name':name,
                            'password':password,
                            'outerIP':outerIP,
                            'transPort':transPort
                    }
                    reg_dump= json.dumps(reg)
                    sk.sendall(bytes(reg_dump.encode("utf-8")))
                    
                    reg_state = sk.recv(1024)
                    if reg_state == bytes(300): 
                        print("服务器拒绝设备%s注册\n" % name)
                        break
                    elif reg_state == bytes(200): 
                        print("恭喜你注册成功\n")
                        break
                    elif reg_state == bytes(400):
                        print("设备已经存在，请直接登录\n")                    
                        break
                    else:
                        print("注册失败\n")                    
                        break
            elif arg == "2":
                while True:
                    print("请登录")
                    sk.sendall(bytes(2))
                    name2 = input("请输入用户名\n")
                    print("请输入密码")
                    password3 = pwd_input()
                    print("\n")
                    login={
                            'name':name2,
                            'password':password3,
                            'outerIP':outerIP,
                            'transPort':transPort
                    }
                    login_dump= json.dumps(login)
                    sk.sendall(bytes(login_dump.encode("utf-8")))
                    log_state = sk.recv(1024)
                    if log_state==bytes(200):                
                        print("登录成功\n")
                        usr=name2
                        break
                    elif log_state==bytes(401):
                        print("密码错误！请重新输入")
                    elif log_state==bytes(402):
                        print("用户不存在！请重新输入")
                    else:
                        print("登录失败！请重新输入")
                    arg2 = input("重新登录请输入1，返回注册请输入2\n")
                    if arg2 == "1":
                        continue
                    else:
                        break                       
                if log_state==bytes(200):
                    status=1
                    #登录结束，继续后面操作
            else:
                print("输入错误，请重新输入")

            while status == 1:
                data = readInput(sk,name2)#超时35s没有输入 将发送心跳包
                com = data.split()
                #print(com[0])
                if com[0] == 'help':
                    usage()
                    continue
                elif com[0] == 'declare':
                    print('\n')
                    declare(sk,usr,IP)
                    continue
                elif com[0] == 'gsl':#获取有该资源的设备列表
                    print('\n')
                    serviceList=reqSource(sk,usr,IP,com)
                    with con:
                        con.notify()
                        con.wait()
                        con.release
                    continue
                elif com[0] == 'logout':
                    tag = logout(sk,name2)
                    if tag == '1':
                        print('退出登录')
                        status = 2 #退出
                        break
                    else:
                        print('操作失败')
                        continue
                elif com[0] == 'ls':
                    ls(sk,name2)
                    continue
                elif com[0] == 'disconnect':
                    print('断开连接')
                    status = 2 #退出连接
                    break
                elif com[0] == '/n':
                    continue
                else:
                    print( 'Error: Unknown command %s. Please input "help" to get some help' %com[0])
                    continue
                '''
                elif 
                elif
                elif
                
                '''
def readInput(sk,usr,timeout =35):

    start_time = time.time()
    default='/n'
    sys.stdout.flush()
    input = ''
    while True:

        if msvcrt.kbhit():
            byte_arr = msvcrt.getche()
            if ord(byte_arr) == 13: # enter_key
                break
            elif ord(byte_arr) ==8:
                if input:
                    input = input[:-1]
                    msvcrt.putch( ' '.encode(encoding='utf-8')) # 输出一个空格覆盖原来的星号  
                    msvcrt.putch('\b'.encode(encoding='utf-8')) # 光标回退一格准备接受新的输入 
            elif ord(byte_arr) >= 32: #空格键以上
                input += "".join(map(chr,byte_arr))
        if len(input) == 0 and (time.time() - start_time) > timeout:
            tag=heartBeat(sk,usr)
            #print(tag)
            break
    if len(input) > 0:
        return input
    elif tag==1:
        sta='disconnect'
        return sta
    else:
        return default    

#声明资源操作的函数
def declare(sk,username,IP):
    #发送包的类型
    d='declare'
    sk.sendall(bytes(d.encode("utf-8")))
    #调用操作系统filedialog，在图形界面选取要声明的文件


    default_dir = r"C:"  # 设置默认打开目录
    #选取需要上传的文件
    root = tkinter.Tk()    # 创建一个Tkinter.Tk()实例
    root.withdraw()       # 将Tkinter.Tk()实例隐藏
    filename = tkinter.filedialog.askopenfilename(title=u"选择文件",
                                     initialdir=(os.path.expanduser(default_dir)))
    print(filename)
    if len(filename)==0:
        error={
            'filename':'error'
        }
        error_dump= json.dumps(error)
        sk.sendall(bytes(error_dump.encode("utf-8"))) 
        print('declaration canceled !')
        #返回文件路径
    else:
        name = filename.split('/')[-1]


        #分片的个数,当文件大于100M时，分片转换防止内存不够用
        calltimes = 0     
        hmd5 = hashlib.md5()
        fp = open(filename, "rb")
        f_size = os.stat(filename).st_size #得到文件的大小
        #将文件用MD5加密
        #文件大于100M时进行分片处理
        if f_size > _FILE_SLIM:
            while (f_size > _FILE_SLIM):
                hmd5.update(fp.read(_FILE_SLIM))
                f_size /= _FILE_SLIM
                calltimes += 1  # delete    
            if (f_size > 0) and (f_size <= _FILE_SLIM):
                hmd5.update(fp.read())
        else:
            hmd5.update(fp.read())

        #声明操作的协议包
        decl={'filename':name,
            'MD5':hmd5.hexdigest(),
            'servicename':username,
            'outerIP':IP[0],
            'innerIP':IP[1],
            'desIP':serverIP,
            'desPort':serverPort
            }
        #以json格式发送
        decl_dump= json.dumps(decl)
        sk.sendall(bytes(decl_dump.encode("utf-8")))        

        time.sleep(0.3)#等待服务器返回信息
        response=sk.recv(1024)
        if response == bytes(200):#声明操作成功
            #在本地数据库保存此文件的路径和MD5编码
           #在本地数据库保存此文件的路径和MD5编码
            with sqlite3.connect("space.db") as dbcon:
                            cur = dbcon.cursor()
                            sql = ''' insert into localsource VALUES (?, ?, ?, ?)'''
                            try:
                                cur.execute(sql,(name,filename,hmd5.hexdigest(),None))
                                dbcon.commit()
                                cur.close()
                            except Exception as e:
                                print(e)
                            else:
                                print ('%s has been declared successfully!' %name)
        elif response==bytes(203):#该文件已经被声明过了
            print(' %s has been declared before! No need operate again.'%name)
        elif response== bytes(205):
            print('fail to declare %s!'%name)

#云盘操作指令的提示信息，模仿linux命令行
def usage():
    print ('''
        help        Show help.
        declare Declare our file to server
        ls      List all files and directories.
        gsl filename    get resource list.
        logout        logout Cloud!
        ''')
#根据不同操作命令 调用不同的函数 ,还没实现完  
 
def reqSource(sk,usr,IP,com):
    if len(com) == 1:
        print( 'len = %d' %len(com))
        filename = input ('Please input the file name: ')
    else:
        filename = com[1]
        d='getlist'
        sk.sendall(bytes(d.encode("utf-8")))

        #申请资源操作的协议包
        req={
            'servicename':usr,
            'desIP':serverIP,
            'desPort':serverPort,
            'filename':filename
            }
        #以json格式发送
        req_dump= json.dumps(req)
        sk.sendall(bytes(req_dump.encode("utf-8")))        
        response=sk.recv(1024)
        #print(bytes(response))
        if response == bytes(200):
            service_d=sk.recv(1024*1024*100)
            servicestr=json.loads(service_d)
            serviceList=servicestr['serviceList']
        elif response==bytes(201):
            print('Did not receive filename')
            serviceList=[]
        elif response==bytes(202):
            print('no available service')
            serviceList=[]
        #print(serviceList)
    return serviceList

def Download():
    if con.acquire():
        #print("download acquire Condition lock successfully")
        if len(serviceList) == 0:
            con.wait()
            for i in range(len(serviceList)):
                # 创建TCP套接字，使用IPv4协议
                print(serviceList[i][0])
                if serviceList[i][0] != usr:
                    try:
                        sk1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                        sk1.connect((str(serviceList[i][2]),serviceList[i][4]))
                        print("connecting with %s"%serviceList[i][0])
                    except Exception:
                        continue
                    downloadreq={
                                'servicename':usr,
                                'uniquecode':serviceList[i][1]
                    }
                    dl_dump= json.dumps(downloadreq)
                    sk1.sendall(bytes(dl_dump.encode("utf-8")))        
                    response=sk1.recv(1024)
                    if response==bytes(200):
                        file_d=sk1.recv(1024)
                        file=json.loads(file_d)
                        filename=file['filename']
                        if filename=='error':
                            print("file has been deleted")
                            pass
                        else:
                            default_dir = r"E:"  # 设置默认打开目录
                            root = tkinter.Tk()    # 创建一个Tkinter.Tk()实例
                            root.withdraw()       # 将Tkinter.Tk()实例隐藏
                            filepath=tkinter.filedialog.askdirectory(title=u"选择文件")#选择以什么文件保存，创建文件并返回文件流对象
                            filepath=filepath+'/'+filename
                            print("save path %s"%filepath)
                            print(file['size'])
                            with open(filepath, "wb") as f: 
                                string=sk1.recv(file['size'])      
                                sta=f.write(string)
                            if sta:
                                f.close()
                                sk1.sendall(bytes(202))
                                print("download file %s successfully"%filepath)
                            else:
                                print("error in writing files")
                        
                    elif response==bytes(201):
                           print("Unknown erro")

                    sk1.close()
            con.notify()
        con.release()

def transSocket(serverIP,transPort):
    
    # 创建TCP套接字，使用IPv4协议
    transSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    # 将TCP套接字绑定到指定端口
    transSocket.bind((transIP,transPort)) 
    # 最大连接数为1
    transSocket.listen(1)
    print("The client is ready to Upload")
    while True:
        conn, addr = transSocket.accept()
        #print('Accept new connection from %s:%s...' % addr)

        file_d=conn.recv(1024)
        file=json.loads(file_d)
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            try:
                cur.execute("select sourcename,path from localsource where uniquecode='%s'"%file['uniquecode'])
            except Exception as e:
                print(e)
            r=cur.fetchall()
            #print(r)
            for file in r:
                filepath=file[1]
                filename=file[0]
            if len(r)==0:
                conn.send(bytes(201))
                conn.close()
                continue
                #该资源不存在，返回状态码，并取消声明
                #print("Sorry,no such file!")
            else:
                #文件传输
                tag=0
                conn.send(bytes(200))
                
                try:
                    tag=0
                    buf = bytearray(os.path.getsize(filepath))                        
                except OSError as reason:
                    tag=1
                    print(str(reason)+'文件已被删除')
                    error={
                            'filename':'error'
                            }
                    error_dump= json.dumps(error)
                    conn.sendall(bytes(error_dump.encode("utf-8")))  
                if tag==0:
                    with open(filepath, 'rb') as f:
                        f.readinto(buf)
                        f_size = os.path.getsize(filepath) #得到文件的大小
                        first={
                            'filename':filename,
                            'size':f_size
                                }
                        first_d=json.dumps(first)      
                        conn.sendall(bytes(first_d.encode("utf-8")))
                        time.sleep(1)
                        conn.sendall(bytes(buf))
                        s=conn.recv(1024)
                        if s==bytes(202):
                            conn.close()
                        elif s==bytes(201):
                            conn.close()    
                continue
                    
                
        
#退出系统
def logout(sk,username):
    l = 'logout'
    tag = 0
    sk.sendall(bytes(l.encode("utf-8")))
    #退出系统的协议
    data_to_server = {'user':username}
    data_dumped = json.dumps(data_to_server)#用json格式发送协议
    sk.sendall(bytes(data_dumped.encode("utf-8")))
    time.sleep(0.3)#等待服务器返回信息
    response=str(sk.recv(1024),encoding='UTF-8')
    data_loaded = json.loads(response)#将json格式的文件解码
    tag = data_loaded['tag']
    #rep = data_loaded['rep']
    return tag
    
def ls(sk,username):
    while True:
        ls = 'ls'
        sk.sendall(bytes(ls.encode("utf-8")))
        response=str(sk.recv(1024),encoding='UTF-8')
        data_loaded = json.loads(response)#将json格式的文件解码
        tag = data_loaded['statuscode']
        list = data_loaded['list']
        if tag == '200':
            recvtag = '1'
            print('目前在线设备的已声明资源有：（资源名+设备+是否可用+备注）')
            for row in list:
                print(row)
            break
        elif tag == '203':
            recvtag = '1'
            print('云空间无资源')
            break
        else:
            recvtag = '0'
            res_to_server = {'user':username,
                    'statuscode':recvtag}
            data_dumped = json.dumps(res_to_server)#用json格式发送协议
            sk.sendall(bytes(data_dumped.encode("utf-8")))
    res_to_server = {'user':username,
                    'statuscode':recvtag}
    data_dumped = json.dumps(res_to_server)#用json格式发送协议
    sk.sendall(bytes(data_dumped.encode("utf-8")))
                
def main():
    status=0
    global con
    con = threading.Condition()
    global thread_isalive
    thread_isalive = True
    
    threadmain = threading.Thread(target=mainpage, args=(status,))
    threadmain.start()
    
    threaddownload = threading.Thread(target=Download,)
    threaddownload.start()
    
    threadtrans= threading.Thread(target=transSocket,args=(serverIP,transPort,))
    threadtrans.start()
    
    
#执行 如果入口是main函数
if __name__ == '__main__':
    main()
    


    
