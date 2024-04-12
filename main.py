import multiprocessing
import subprocess

# 本机部署配置
checkpoint_path = r"F:\auditmodel_4"  # 模型的路径
server_port = 8000  # 本机服务器的端口号
server_name = "127.0.0.1"  # 服务器的名称

# CPU 部署配置
cpu_only = False  # 是否只使用 CPU

# 局域网部署配置
web_server = True  # 是否使用 Web 服务器
port_number = 8000  # Web 服务器的端口号


def start_web_server(port):
    """
    启动Web服务器
    """
    subprocess.call(["python", "./src/web.py", str(port)])


def start_user_page():
    """
    启动SQL、用户页面
    """
    subprocess.call(["python", "./src/user.py"])


def start_api_server(checkpoint_path, server_port, server_name, cpu_only):
    """
    启动API服务器
    """
    if cpu_only:
        subprocess.call(["python", "./src/api.py",
                         "-c", checkpoint_path,
                         "--server-port", str(server_port),
                         "--server-name", server_name,
                         "--cpu-only"])
    else:
        subprocess.call(["python", "./src/api.py",
                         "-c", checkpoint_path,
                         "--server-port", str(server_port),
                         "--server-name", server_name])


if __name__ == "__main__":
    processes = []

    user_process = multiprocessing.Process(target=start_user_page)
    user_process.start()
    processes.append(user_process)

    if web_server:
        # 启动Web服务器
        web_process = multiprocessing.Process(target=start_web_server, args=(port_number,))
        web_process.start()
        processes.append(web_process)

    # 启动API服务器
    api_process = multiprocessing.Process(target=start_api_server,
                                          args=(checkpoint_path, server_port, server_name, cpu_only))
    api_process.start()
    processes.append(api_process)

    # 等待所有进程结束
    for process in processes:
        process.join()
