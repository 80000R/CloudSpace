#!/usr/bin/python
# -*- coding: UTF-8 -*-
import  threading
#导入SQLite驱动：
import sqlite3
import json
import socket
import time

#连接到SQlite数据库
#数据库文件是test.db，不存在，则自动创建
#serverIP = '172.28.177.9'
serverIP = '127.0.0.1'
serverPort = 10086

def login(username, password, address, outerIP,transPort):
    """
    用于用户名和密码的验证
    :param username:用户名
    :param paaword:密码
    :return:1,用户验证成功;2,密码错误;3:用户不存在
    """
    try:
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            cur2 = dbcon.cursor()
            cur3 = dbcon.cursor()
            cursor =cur.execute('SELECT * from service')
            for row in cursor:
                if row[0] == username and row[1] == 1:
                    print('设备已登录')
                    return 4
            sql = '''SELECT devname, password from dev'''
            sql2 = '''update service set state=1,innerIP=?,outerIP=?, transPort = ? where servicename=?'''
            sql3 = '''update serversource set stat = 1 where servicename=?'''
            cursor =cur.execute(sql)
            for row in cursor:
                if row[0] == username and row[1] == password:
                    cur2.execute(sql2,(str(address[0]),outerIP,transPort,username))
                    cur3.execute(sql3,(username,))
                    dbcon.commit()
                    print("登录成功")
                    return 1
                elif row[0] == username and row[1] != password:
                    print("密码错误！！")
                    return 2        
            print("设备不存在")
            return 3
            cur.close()
            cur2.close()
            cur3.close()
    except IOError:        
        return 0

def register(username, password, address, outerIP,transPort):
    """
    注册用户
    1、打开文件
    2、用户名$密码
    :param username:用户名
    :param password:密码
    :return:True：注册成功；
    """
    print(outerIP)
    with sqlite3.connect("space.db") as dbcon:
        cur = dbcon.cursor()
        sql = ''' insert into dev values (:d_username, :d_password)'''
        cur.execute(sql,{'d_username':username, 'd_password':password})
        dbcon.commit()
        sql = ''' insert into service VALUES (:uuname, :ustate, :uconn, :uouterIP, :utransPort,:umessge)'''
        cur.execute(sql,{'uuname':username, 'ustate':0, 'uconn':str(address[0]), 'uouterIP':outerIP,'utransPort':transPort, 'umessge':None})
        dbcon.commit()
        cur.close()
        return True

def user_exist(username):
    """
    检测用户名是否存在
    :param username:要检测的用户名
    :return: True：用户名存在；False：用户名不存在
    """
    # 一行一行的去查找，如果用户名存在，return True：False
    try:
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            cursor = cur.execute("SELECT devname from dev")
            for row in cursor:
                if row[0] == username:
                    return True
            return False
            cur.close()
    except IOError:
        return False

def reslogout(conn):
    l = 'logout'
    data = str(conn.recv(1024),encoding='UTF-8')
    #data = conn.recv(1024*1024*100)#接收资源协议包
    if data!= None:
        data_loaded = json.loads(data)
        user = data_loaded['user']
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            #查询、更改设备登录状态
            try:
                sql = '''update service set state=0 where servicename=?'''
                sql2 = '''update serversource set stat = 0 where servicename=?'''
                cur.execute(sql,(user,))
                cur.execute(sql2,(user,))
                cur.close()
                #退出系统的协议
                data_to_client = {'user':user,
                                'tag':'1'}
                data_dumped = json.dumps(data_to_client)#用json格式发送协议
                conn.sendall(bytes(data_dumped.encode("utf-8")))
                print('设备%s退出' %user)
            except Exception as e:
                print(e)
                return False
    else:
        print('错误')

def ls(conn):
    print('client want to check resources')
    list = []
    #查询、更改设备登录状态
    try:
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            sql = '''select sourcename, servicename, stat, messege from serversource'''
            cursor = cur.execute(sql)
            for row in cursor:
                list.append(row[0]+'+'+row[1]+'+'+str(row[2])+'+'+str(row[3]))
            cur.close()
        if len(list) != 0:
            #协议
            data_to_client = {'statuscode':'200',
                            'list':list}
            data_dumped = json.dumps(data_to_client)#用json格式发送协议
        else:
            data_to_client = {'statuscode':'203',
                            'list':' '}
            data_dumped = json.dumps(data_to_client)
        conn.sendall(bytes(data_dumped.encode("utf-8")))
        while True:
            resrecv = str(conn.recv(1024),encoding='UTF-8')
            if resrecv != None:
                data_loaded = json.loads(resrecv)
                if data_loaded['statuscode'] == '1':
                    user = data_loaded['user']
                    print('资源列表已送达',user)
                    break
                elif data_loaded['statuscode'] == '0':
                    data_dumped = json.dumps(data_to_client)
                    conn.sendall(bytes(data_dumped.encode("utf-8")))
                    print('资源列表未送达',user,'重传')
                    continue
            else:
                print('接收响应消息出错')
                break
    except Exception as e:
        print(e)


def dealConn(conn,address):
    lasttime=time.time()

    #注册登录功能
    while True:
        #a表示选择注册还是登录
        a = conn.recv(1024)
        if a==bytes(1):
            reg_d = conn.recv(1024)#接收获取设备列表的协议
            reg=json.loads(reg_d)
            print('设备%s请求注册' % reg['name'])
            canreg = input("同意此设备注册请输入1，拒绝请输入2\n")
            if canreg == "2":
                conn.sendall(bytes(300))
                continue
            is_exist = user_exist(reg['name'])
            if is_exist:
                conn.sendall(bytes(400))
                #conn.send("用户名已经存在，注册失败".encode("utf-8"))
            else:
                name=reg['name']
                password=reg['password']
                outerIP=reg['outerIP']
                transPort=reg['transPort']
                if register(name, password,address,outerIP,transPort):
                    conn.sendall(bytes(200))
                    #conn.send("注册成功".encode("utf-8"))
                    continue
                else:
                    conn.sendall(bytes(401))
                    #conn.send("注册失败".encode("utf-8"))               
        elif a==bytes(2):
            login_d = conn.recv(1024)#接收获取设备列表的协议
            log=json.loads(login_d)

            print('Server received: %s' % log['name'])
            name2=log['name']
            password2=log['password']
            outerIP=log['outerIP']
            transPort=log['transPort']
            tag = login(name2, password2,address,outerIP,transPort)
            if tag == 1:
                conn.sendall(bytes(200))
                #将登陆时间记录，在心跳检测中更新
                lasttime=time.time()
                #修改设备表和资源表的状态信息
                with sqlite3.connect("space.db") as dbcon:
                        cur = dbcon.cursor()
                        sql1 = ''' update service set state=1 where servicename=? '''
                        sql2 = ''' update serversource set stat=1 where servicename=? '''
                        try:
                            cur.execute(sql1,(name2,))
                            cur.execute(sql2,(name2,))
                            dbcon.commit()
                            cur.close()
                        except Exception as e:
                            print(e)
                break#登录完毕
            elif tag == 2:
                conn.sendall(bytes(401))
                #print('密码错误')
            elif tag == 3:
                conn.sendall(bytes(402))
                #print('用户不存在')
            else:
                conn.sendall(bytes(400))
                print('登录失败')
    status=1
    while status:#接收此设备的操作请求并调用相应的函数
        conn.settimeout(60)
        try:
            data =str(conn.recv(1024),encoding='UTF-8')
        except Exception:
            tag=checkHeart(lasttime,name2)#超过60s没有接收到任何消息，将检测该连接是否有效
            print(tag)
            if tag:
                continue
            else:
                conn.close()
                break
        if data == 'heartBeats':#接收此设备的心跳，并更新连接的时间
            heartBeats_d = str(conn.recv(1024),encoding='UTF-8')
            heartBeats = json.loads(heartBeats_d)
            #print('%s is alive '%heartBeats['user'])
            lasttime=time.time()
            conn.sendall(bytes(200))
            continue

        elif data=='declare':#声明资源请求
            acceptDeclare(conn)
            continue
        elif data=='getlist':#获取资源所在设备列表
            getList(conn)
            continue
                
        elif data == 'logout':
            reslogout(conn)
            conn.close()
            status=0
            break
        elif data == 'ls':
            ls(conn)
            continue


# 心跳监听
def checkHeart(lasttime,name): 
    #print(lasttime)
    print(time.time()-lasttime) 
    if time.time()-lasttime > 120.0:#上一次连接和此次连接时间差大于等于30秒视为断开
        #更新设备表和资源信息表
        with sqlite3.connect("space.db") as dbcon:
                cur = dbcon.cursor()
                sql1 = ''' update service set state=0 where servicename=? '''
                sql2 = ''' update serversource set stat=0 where servicename=? '''
                try:
                    cur.execute(sql1,(name,))
                    cur.execute(sql2,(name,))
                    dbcon.commit()
                    cur.close()
                except Exception as e:
                    print(e)   
        print('ip: %s diconnect!' %name)
        return 0
    else:
        return 1

#处理资源声明
def acceptDeclare(conn):

    data = conn.recv(1024*1024*100)#接收资源协议包
    flag=0
    if data!= None:
        declaremessege = json.loads(data)
        if declaremessege['filename']== 'error':
            print("client has unknow error in declaration")
        else:
            with sqlite3.connect("space.db") as dbcon:
                cur = dbcon.cursor()
                #查询该设备是否声明过此资源
                #print("select uniquecode from serversource where servicename='%s'"%declaremessege['servicename'])
                try:
                    cur.execute("select uniquecode from serversource where servicename='%s'"%declaremessege['servicename'])
                except Exception as e:
                    print(e)
                allfile=cur.fetchall()
                #print(allfile)
                for file in allfile:
                    if file[0]==declaremessege['MD5']:
                        #已声明过此资源，返回状态码203
                        conn.sendall(bytes(203))
                        flag=1
                        #print('%s was declareed !'%declaremessege['filename'])
                        break
                
                if flag==0:#没有声明过此资源，将其插入资源表并返回状态码200
                    cur = dbcon.cursor()
                    sql = ''' insert into serversource VALUES (:filename, :servicename, :statu, :uniquecode, :messge)'''
                    try:
                        cur.execute(sql,{'filename':declaremessege['filename'],'servicename':declaremessege['servicename'],'statu':1,'uniquecode':declaremessege['MD5'],'messge':None})
                        cur.close()
                    except Exception as e:
                        print("line 208")
                        print(e)
                    conn.sendall(bytes(200))
            
    else:#数据包丢失
        conn.sendall(bytes(205))
        print("did not recv any bytes")

#获取申请资源
def getList(conn):
    data = conn.recv(1024*1024*100)#接收获取设备列表的协议
    filename=json.loads(data)
    tag=0
    global uniquecode
    if data!= None:
        reqmessege = json.loads(data)
        
        with sqlite3.connect("space.db") as dbcon:
            cur = dbcon.cursor()
            try:
                cur.execute("select servicename,uniquecode from serversource where sourcename='%s' and stat=1"%reqmessege['filename'])
                alluser=cur.fetchall()
                dbcon.commit()

            except Exception as e:
                print("yes")
                conn.sendall(bytes(202))
            l=len(alluser)
            serviceList = [([0] * 5) for i in range(l)]
            print(len(alluser))
            if len(alluser)==0:
                tag=1
                print("201")
                conn.sendall(bytes(202))
            else:
                i=0
                for user in alluser:
                    serviceList[i][0]=user[0]
                    serviceList[i][1]=user[1]
                    i=i+1
                #print(serviceList)
            cur.close()
                
        if tag==0:
            for index in range(l):
                z=0
                
                with sqlite3.connect("space.db") as dbcon:
                    cur = dbcon.cursor()
                    try:
                        cur.execute("select * from service where servicename='%s'"%serviceList[index][0])
                        dbcon.commit()
                    except Exception as e:
                        #print("1")
                        print("yes")
                    result=cur.fetchone()
                    serviceList[index][2]=result[2]   
                    serviceList[index][3]=result[3]   
                    serviceList[index][4]=result[4] 
                    cur.close()

            conn.sendall(bytes(200))#返回成功
            servicemessege={
            'filename':reqmessege['filename'],
            'serviceList':serviceList
            }
             #以json格式发送
            serverSocket= json.dumps(servicemessege)
            conn.sendall(bytes(serverSocket.encode("utf-8")))  
        else:
            pass
            



def main():
    # 创建TCP套接字，使用IPv4协议
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    # 将TCP套接字绑定到指定端口
    serverSocket.bind((serverIP,serverPort)) 
    # 最大连接数为5
    serverSocket.listen(5) 
    print("The server is ready to receive")
    while True:
        #接收到客户连接请求后，建立新的TCP连接套接字
        conn, addr = serverSocket.accept()
        print('Accept new connection from %s:%s...' % addr)
        
        #使用另一个线程去收发数据,这样服务端就可以继续接受其他客户端连接 非阻塞
        #最多接收5个连接
        thread = threading.Thread(target=dealConn, args=(conn, addr,))
        thread.start()

        
#执行 如果入口是main函数
if __name__ == '__main__':
    main()