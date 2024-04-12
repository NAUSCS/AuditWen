


#插入数据

# 导入 pyodbc 模块用于与 SQL Server 数据库交互
import pyodbc
import datetime

# 假设您的数据库连接信息如下：
server = 'localhost'
database = '审计知识智能问答'
username = 'sa'
password = '123456'
conn = pyodbc.connect(
    'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
cursor = conn.cursor()
sq11="""
        select * from QuestionSets
        """
read_sql = pd.read_sql(sq11,conn)
try :
    set_id = max(read_sql["SetID"])
except :
    set_id = 0  # 初始化setID为零
question_id = 0  # 初始化QuestionID为零
group_id = 0  # 初始化QuestionGroupID为零
global groupId
groupId=1


@app.post("/add_message")
async def add_message(message: ChatMessage):
    global set_id, question_id, group_id
    if message.role == "user" or message.role == "assistant":
        if message.role == "user":
            cursor.execute("SELECT COUNT(*) FROM QuestionGroups WHERE GroupID = ?", (group_id,))
            count = cursor.fetchone()[0]
            question_id += 1
            set_id += 1
            if count == 0:
                cursor.execute("INSERT INTO QuestionGroups (GroupID,UserID, Time) "
                               "VALUES (?, ?, ?)", (group_id, "2003", datetime.datetime.now()))
                conn.commit()
            cursor.execute("INSERT INTO QuestionSets (SetID, GroupID, QuestionID, Question, Answer)"
                           " VALUES (?, ?, ?, ?, NULL)", (set_id, group_id, question_id, message.content,))

        else:
            cursor.execute("UPDATE QuestionSets SET Answer = ? WHERE Answer IS NULL", (message.content,))
        conn.commit()

        return {"message": "Message added successfully."}
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: Unsupported message role {message.role}.",
        )

@app.post("/new_chat")
async def new_chat():
    global set_id, question_id, group_id
    # set_id += 1
    group_id += 1
    question_id = 0
    cursor.execute("SELECT COUNT(*) FROM QuestionGroups WHERE GroupID = ?", (group_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO QuestionGroups (GroupID,UserID,  Time) VALUES (?, ?, ?)",
                       (group_id, "2003", datetime.datetime.now()))
        conn.commit()
    return {"message": "新的问答已开始"}

####################################################################################################################
#####################################################################################################################
#####################################################################################################################
#####################################################################################################################

@app.post("/retrieve_content")
async def retrieve_content(content):
    received_content = content
    print('接收到的 content:', received_content)
    return {"received_content": received_content}


#生成以最新的group_id的按钮
@app.get("/latest_group_id")
async def get_latest_group_id():
    global group_id
    # 查询数据库以获取最新的 GroupID
    cursor.execute("SELECT MAX(GroupID) FROM QuestionGroups")
    latest_group_id = cursor.fetchone()[0]
    if latest_group_id is not None:
        group_id = latest_group_id
    return {"latest_group_id": group_id}

#查询数据库以获得与之匹对的question和answer
@app.get("/question_answer")
async def get_question_answer():
    sql2 = """
            select * from QuestionSets
            """
    read_sql = pd.read_sql(sql2, conn)
    count1 = len(read_sql)
    # 选择 GroupID 为 1 的所有记录
    group_1_records = read_sql[read_sql['GroupID'] == groupId]
    # 将记录转换为元组并放入列表中
    question_answer = [tuple(record[-2:]) for record in group_1_records.values]
    count2 = len(question_answer)
    return {"question_answer":question_answer}


##################################################################################################
####################################################################################################################
#####################################################################################################################
#####################################################################################################################
#####################################################################################################################
#根据点击的按钮名查询数据
@app.get("/get_data_by_button_name")
async def get_data_by_button_name(button_name: str):
    groupId=button_name
    data_list = []
    # 查询数据库以获取与按钮名字相同的数据
    cursor.execute("SELECT * FROM QuestionSets WHERE ButtonName = ?", (button_name,))
    rows = cursor.fetchall()
    for row in rows:
        data_list.append({
            "SetID": row.SetID,
            "GroupID": row.GroupID,
            "QuestionID": row.QuestionID,
            "Question": row.Question,
            "Answer": row.Answer
        })
    print(rows)
    return data_list
##############可用
@app.get("/query_question_sets")
async def query_question_sets(groupId: str):
    # 查询数据库以获取与 GroupID 匹配的数据
    cursor.execute("SELECT Question,Answer FROM QuestionSets WHERE GroupID = ?", (groupId,))
    query_result = cursor.fetchall()  # 假设查询结果是一个列表
    # 返回查询结果（这里假设将查询结果转换为字符串返回）
    return {"query_result": str(query_result)}

#####################################################################################################################
#####################################################################################################################
#####################################################################################################################
############################################################################
# #开始新的聊天，清空聊天栏
history = []


@app.post("/add_message")
async def add_message(message: ChatMessage):
    if message.role == "user":
        question = message.content
        answer = ""
        if len(history) > 0 and history[-1][1] == "":
            # 将问题添加到上一个对话中的用户消息中
            history[-1][0] += f"\nQuestion: {question}"
        else:
            # 创建一个新的对话记录
            history.append([question, answer])
    elif message.role == "assistant":
        if len(history) > 0 and history[-1][1] == "":
            # 将回答添加到上一个对话中的助手消息中
            history[-1][1] = message.content
        else:
            # 创建一个新的对话记录（无用户问题）
            history.append(["", message.content])
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: Unsupported message role {message.role}.",
        )
    return {"message": "Message added successfully."}


@app.get("/history")
async def get_history():
    return json.dumps({"history": history})


@app.post("/new_chat")
async def new_chat():
    # 清除当前问答历史
    history.clear()
    return {"message": "新的问答已开始"}



#############################################################################################
###########################################################################################
#####################################################################################################################
