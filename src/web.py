import http.server
import socketserver
import os
import socket


def get_local_ip():
    try:
        # 创建一个socket对象
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 连接到一个临时的地址
        s.connect(("8.8.8.8", 80))

        # 获取本机IP地址
        local_ip = s.getsockname()[0]

        return local_ip
    except Exception as e:
        print("获取本机IP地址时出错:", e)
    finally:
        s.close()


# 设置服务器端口号
PORT = 8000

# 获取当前工作目录
web_dir = os.path.join(os.path.dirname(__file__), '../web')
os.chdir(web_dir)

# 指定服务器处理程序（这里使用简单的静态文件处理程序）
Handler = http.server.SimpleHTTPRequestHandler

# 启动HTTP服务器，使用局域网地址 0.0.0.0，这样其他设备就可以访问
with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print("服务器启动在端口:", PORT)
    print("您的网页可在 http://%s:%s/index.html 访问" % (get_local_ip(), PORT))
    # 这里将一直监听，直到手动停止服务器
    httpd.serve_forever()
