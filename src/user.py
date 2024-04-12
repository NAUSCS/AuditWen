# encoding=utf8
import os
import sys

from flask import Flask, render_template, request, jsonify
import pymssql
import pandas as pd

app = Flask(__name__, template_folder='../web/pages', static_folder='../web/css')


# 首页路由
@app.route('/')
def index():
    return render_template('signup.html')


# 登录路由
@app.route('/login', methods=['POST'])
def login():
    # 获取登录表单数据
    username = request.form['Username']
    password = request.form['Password']

    # 在这里你可以根据需要进行验证，比如验证用户名密码是否正确
    # 这里简单地将数据打印出来
    print("Login Form Data:", username, password)
    conn = pymssql.connect(host='localhost', user='sa', password='123456', database='AuditWen', )  # 连接数据库
    db = conn.cursor()  # 获取游标
    sql = '''SELECT * FROM Users'''
    df = pd.read_sql(sql, conn)
    num = 0
    for row in df.values:
        num = num + 1
        if username == row[1] and password == row[2]:
            return render_template('/user.html')
    if num == len(df):
        return jsonify({'message': 'login error'})
    # 返回响应，你可以根据需要返回不同的响应，比如登录成功或失败


# 注册路由
@app.route('/register', methods=['POST'])
def register():
    # 获取注册表单数据
    email = request.form['email']
    username = request.form['Username']
    password = request.form['Password']
    repeat_password = request.form['Passwordrepeat']

    # 在这里你可以根据需要进行验证，比如验证密码是否一致等
    # 这里简单地将数据打印出来
    print("Register Form Data:", email, username, password, repeat_password)

    # 返回响应，你可以根据需要返回不同的响应，比如注册成功或失败

    conn = pymssql.connect(host='localhost', user='sa', password='123456', database='AuditWen')  # 连接数据库
    db = conn.cursor()  # 获取游标
    sql1 = '''create table Users(
                UserID INT PRIMARY KEY,
                Username VARCHAR(50),
                Password VARCHAR(50)
                );'''
    try:
        db.execute(sql1)
        conn.commit()  # 提交事务
    except:
        print("已有数据库Users")

    sql2 = '''select * from Users'''
    num1 = pd.read_sql(sql2, conn)

    num = len(num1)
    print(num)

    sql3 = '''insert into Users(UserID,Username,Password) values({},'{}','{}')'''.format(num, email, password)
    try:
        db.execute(sql3)
        conn.commit()  # 提交事务
        print("插入成功")
    except Exception as e:
        print(e)
    db.close()
    conn.close()  # 关闭数据库
    return jsonify({'message': 'register successfully!'})


@app.route('/answer')
def answer():
    return render_template('/index.html')


if __name__ == '__main__':
    app.run(debug=True)
