import base64
import copy
import json
import time
import csv
import re
import pandas as pd
from datetime import datetime
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from pprint import pprint
from typing import Dict, List, Literal, Optional, Union

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.generation import GenerationConfig


class BasicAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, username: str, password: str):
        super().__init__(app)
        self.required_credentials = base64.b64encode(
            f'{username}:{password}'.encode()).decode()

    async def dispatch(self, request: Request, call_next):
        authorization: str = request.headers.get('Authorization')
        if authorization:
            try:
                schema, credentials = authorization.split()
                if credentials == self.required_credentials:
                    return await call_next(request)
            except ValueError:
                pass

        headers = {'WWW-Authenticate': 'Basic'}
        return Response(status_code=401, headers=headers)


def _gc(forced: bool = False):
    global args
    if args.disable_gc and not forced:
        return

    import gc

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


@asynccontextmanager
async def lifespan(app: FastAPI):  # collects GPU memory
    yield
    _gc(forced=True)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class ModelCard(BaseModel):
    id: str
    object: str = 'model'
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = 'owner'
    root: Optional[str] = None
    parent: Optional[str] = None
    permission: Optional[list] = None


class ModelList(BaseModel):
    object: str = 'list'
    data: List[ModelCard] = []


class Content(BaseModel):
    content: int
    function_call: Optional[Dict] = None


class ChatMessage(BaseModel):
    role: Literal['user', 'assistant', 'system', 'function']
    content: Optional[str]
    function_call: Optional[Dict] = None


class DeltaMessage(BaseModel):
    role: Optional[Literal['user', 'assistant', 'system']] = None
    content: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    functions: Optional[List[Dict]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_length: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str]] = None


class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Union[ChatMessage]
    finish_reason: Literal['stop', 'length', 'function_call']


class ChatCompletionResponseStreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[Literal['stop', 'length']]


class ChatCompletionResponse(BaseModel):
    model: str
    object: Literal['chat.completion', 'chat.completion.chunk']
    choices: List[Union[ChatCompletionResponseChoice,
    ChatCompletionResponseStreamChoice]]
    created: Optional[int] = Field(default_factory=lambda: int(time.time()))


@app.get('/v1/models', response_model=ModelList)
async def list_models():
    global model_args
    model_card = ModelCard(id='AuditWen')
    return ModelList(data=[model_card])


# 导入 pyodbc 模块用于与 SQL Server 数据库交互
import pyodbc
import datetime

# 连接数据库
server = 'localhost'
database = 'AuditWen'
username = 'sa'
password = '123456'
conn = pyodbc.connect(
    'DRIVER={SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
cursor = conn.cursor()
sq11 = """
        select * from QuestionSets
        """
read_sql = pd.read_sql(sq11, conn)
try:
    set_id = max(read_sql["SetID"])
except:
    set_id = 0  # 初始化setID为零
question_id = 0  # 初始化QuestionID为零
group_id = 0  # 初始化QuestionGroupID为零
global groupId
global time_now


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
                               "VALUES (?, ?, ?)", (group_id, "0", datetime.datetime.now()))
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
    global set_id, question_id, group_id, time_now
    # set_id += 1
    group_id += 1
    question_id = 0
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT COUNT(*) FROM QuestionGroups WHERE GroupID = ?", (group_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO QuestionGroups (GroupID,UserID,  Time) VALUES (?, ?, ?)",
                       (group_id, "0", time_now))
        conn.commit()
    return {"message": "新的问答已开始"}


@app.post("/retrieve_content")
async def retrieve_content(a: Content):
    received_content = a.content
    global groupId
    groupId = received_content
    global group_id
    group_id = received_content
    print('接收到的 content:', received_content)
    return {"received_content": received_content}


@app.get("/time_now")
async def time_now():
    global time_now
    time_now = str(time_now)
    time_now = time_now[0:-3]
    return {"time_now": time_now}


# 生成以最新的group_id的按钮
@app.get("/latest_group_id")
async def get_latest_group_id():
    global group_id
    # 查询数据库以获取最新的 GroupID
    cursor.execute("SELECT MAX(GroupID) FROM QuestionGroups")
    latest_group_id = cursor.fetchone()[0]
    if latest_group_id is not None:
        group_id = latest_group_id
    return {"latest_group_id": group_id}


# 查询数据库以获得与之匹对的question和answer
@app.get("/question_answer")
async def get_question_answer():
    sql2 = """
            select * from QuestionSets
            """
    read_sql = pd.read_sql(sql2, conn)
    count1 = len(read_sql)
    # 选择 GroupID 为 1 的所有记录
    global groupId
    group_1_records = read_sql[read_sql['GroupID'] == groupId]
    # 将记录转换为元组并放入列表中
    question_answer = [tuple(record[-2:]) for record in group_1_records.values]
    count2 = len(question_answer)
    global history
    history = [("你是谁？", "我是一个智能审计问答机器人，可以回答审计相关的问题。")] + question_answer
    return {"question_answer": question_answer}


# 根据点击的按钮名查询数据
@app.get("/get_data_by_button_name")
async def get_data_by_button_name(button_name: str):
    groupId = button_name
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


@app.get("/query_question_sets")
async def query_question_sets(groupId: str):
    # 查询数据库以获取与 GroupID 匹配的数据
    cursor.execute("SELECT Question,Answer FROM QuestionSets WHERE GroupID = ?", (groupId,))
    query_result = cursor.fetchall()  # 假设查询结果是一个列表
    # 返回查询结果（这里假设将查询结果转换为字符串返回）
    return {"query_result": str(query_result)}


# 开始新的聊天，清空聊天栏
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


@app.get("/time_history")
async def time_history():
    sql1 = """
            select * from QuestionGroups
            """
    a = pd.read_sql(sql1, conn)
    Group_Time = [tuple(record[:]) for record in a.values]
    b = []
    for i in Group_Time:
        a = []
        time = str(i[2])
        time = time[0:-3]
        a.append(i[0])
        a.append(i[1])
        a.append(time)
        b.append(a)
    Group_Time = [tuple(record[:]) for record in b]
    return {"Group_Time": Group_Time}


def add_extra_stop_words(stop_words):
    if stop_words:
        _stop_words = []
        _stop_words.extend(stop_words)
        for x in stop_words:
            s = x.lstrip('\n')
            if s and (s not in _stop_words):
                _stop_words.append(s)
        return _stop_words
    return stop_words


def trim_stop_words(response, stop_words):
    if stop_words:
        for stop in stop_words:
            idx = response.find(stop)
            if idx != -1:
                response = response[:idx]
    return response


TOOL_DESC = (
    '{name_for_model}: Call this tool to interact with the {name_for_human} API.'
    ' What is the {name_for_human} API useful for? {description_for_model} Parameters: {parameters}'
)

REACT_INSTRUCTION = """Answer the following questions as best you can. You have access to the following APIs:

{tools_text}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tools_name_text}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!"""

_TEXT_COMPLETION_CMD = object()


def parse_messages(messages, functions):
    if all(m.role != 'user' for m in messages):
        raise HTTPException(
            status_code=400,
            detail='Invalid request: Expecting at least one user message.',
        )

    messages = copy.deepcopy(messages)
    if messages[0].role == 'system':
        system = messages.pop(0).content.lstrip('\n').rstrip()
    else:
        system = 'You are a helpful assistant.'

    if functions:
        tools_text = []
        tools_name_text = []
        for func_info in functions:
            name = func_info.get('name', '')
            name_m = func_info.get('name_for_model', name)
            name_h = func_info.get('name_for_human', name)
            desc = func_info.get('description', '')
            desc_m = func_info.get('description_for_model', desc)
            tool = TOOL_DESC.format(
                name_for_model=name_m,
                name_for_human=name_h,
                # Hint: You can add the following format requirements in description:
                #   "Format the arguments as a JSON object."
                #   "Enclose the code within triple backticks (`) at the beginning and end of the code."
                description_for_model=desc_m,
                parameters=json.dumps(func_info['parameters'],
                                      ensure_ascii=False),
            )
            tools_text.append(tool)
            tools_name_text.append(name_m)
        tools_text = '\n\n'.join(tools_text)
        tools_name_text = ', '.join(tools_name_text)
        instruction = (REACT_INSTRUCTION.format(
            tools_text=tools_text,
            tools_name_text=tools_name_text,
        ).lstrip('\n').rstrip())
    else:
        instruction = ''

    messages_with_fncall = messages
    messages = []
    for m_idx, m in enumerate(messages_with_fncall):
        role, content, func_call = m.role, m.content, m.function_call
        content = content or ''
        content = content.lstrip('\n').rstrip()
        if role == 'function':
            if (len(messages) == 0) or (messages[-1].role != 'assistant'):
                raise HTTPException(
                    status_code=400,
                    detail=
                    'Invalid request: Expecting role assistant before role function.',
                )
            messages[-1].content += f'\nObservation: {content}'
            if m_idx == len(messages_with_fncall) - 1:
                # add a prefix for text completion
                messages[-1].content += '\nThought:'
        elif role == 'assistant':
            if len(messages) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=
                    'Invalid request: Expecting role user before role assistant.',
                )
            if func_call is None:
                if functions:
                    content = f'Thought: I now know the final answer.\nFinal Answer: {content}'
            else:
                f_name, f_args = func_call['name'], func_call['arguments']
                if not content.startswith('Thought:'):
                    content = f'Thought: {content}'
                content = f'{content}\nAction: {f_name}\nAction Input: {f_args}'
            if messages[-1].role == 'user':
                messages.append(
                    ChatMessage(role='assistant',
                                content=content.lstrip('\n').rstrip()))
            else:
                messages[-1].content += '\n' + content
        elif role == 'user':
            messages.append(
                ChatMessage(role='user',
                            content=content.lstrip('\n').rstrip()))
        else:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid request: Incorrect role {role}.')

    query = _TEXT_COMPLETION_CMD
    if messages[-1].role == 'user':
        query = messages[-1].content
        messages = messages[:-1]

    if len(messages) % 2 != 0:
        raise HTTPException(status_code=400, detail='Invalid request')

    return query, system


def parse_response(response):
    func_name, func_args = '', ''
    i = response.find('\nAction:')
    j = response.find('\nAction Input:')
    k = response.find('\nObservation:')
    if 0 <= i < j:  # If the text has `Action` and `Action input`,
        if k < j:  # but does not contain `Observation`,
            # then it is likely that `Observation` is omitted by the LLM,
            # because the output text may have discarded the stop word.
            response = response.rstrip() + '\nObservation:'  # Add it back.
        k = response.find('\nObservation:')
        func_name = response[i + len('\nAction:'):j].strip()
        func_args = response[j + len('\nAction Input:'):k].strip()

    if func_name:
        response = response[:i]
        t = response.find('Thought: ')
        if t >= 0:
            response = response[t + len('Thought: '):]
        response = response.strip()
        choice_data = ChatCompletionResponseChoice(
            index=0,
            message=ChatMessage(
                role='assistant',
                content=response,
                function_call={
                    'name': func_name,
                    'arguments': func_args
                },
            ),
            finish_reason='function_call',
        )
        return choice_data

    z = response.rfind('\nFinal Answer: ')
    if z >= 0:
        response = response[z + len('\nFinal Answer: '):]
    choice_data = ChatCompletionResponseChoice(
        index=0,
        message=ChatMessage(role='assistant', content=response),
        finish_reason='stop',
    )
    return choice_data


# completion mode, not chat mode
def text_complete_last_message(history, stop_words_ids, gen_kwargs, system):
    im_start = '<|im_start|>'
    im_end = '<|im_end|>'
    prompt = f'{im_start}system\n{system}{im_end}'
    for i, (query, response) in enumerate(history):
        query = query.lstrip('\n').rstrip()
        response = response.lstrip('\n').rstrip()
        prompt += f'\n{im_start}user\n{query}{im_end}'
        prompt += f'\n{im_start}assistant\n{response}{im_end}'
    prompt = prompt[:-len(im_end)]

    _stop_words_ids = [tokenizer.encode(im_end)]
    if stop_words_ids:
        for s in stop_words_ids:
            _stop_words_ids.append(s)
    stop_words_ids = _stop_words_ids

    input_ids = torch.tensor([tokenizer.encode(prompt)]).to(model.device)
    output = model.generate(input_ids,
                            stop_words_ids=stop_words_ids,
                            **gen_kwargs).tolist()[0]
    output = tokenizer.decode(output, errors='ignore')
    assert output.startswith(prompt)
    output = output[len(prompt):]
    output = trim_stop_words(output, ['<|endoftext|>', im_end])
    print(f'<completion>\n{prompt}\n<!-- *** -->\n{output}\n</completion>')
    return output


# 加载已知问题和答案到字典中
def load_known_questions(filename):
    known_questions = {}
    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='|')
        for i, row in enumerate(reader):
            if len(row) < 2:
                continue
            question = row[0]
            answer = row[1]
            known_questions[question] = answer
    return known_questions


history = [("你是谁？", "我是一个智能审计问答机器人，可以回答审计相关的问题。")]
count_history = 0
known_questions = load_known_questions(r'.\src\question.csv')


@app.post('/v1/chat/completions', response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    global model, tokenizer, known_questions, count_history

    # 检查用户提出的问题是否与已知问题匹配
    question = request.messages[0].content
    if '|' in question:
        error_msg = "问题中不能包含'|'字符"
        raise HTTPException(status_code=400, detail=error_msg)

    if question in known_questions:
        # 如果匹配到已知问题，则直接返回对应的答案
        response_text = known_questions[question]
        choice_data = ChatCompletionResponseChoice(
            index=0,
            message=ChatMessage(role="assistant", content=response_text),
            finish_reason="stop",
        )
        history.append((question, response_text))
        count_history += 2
        return ChatCompletionResponse(
            model=request.model, choices=[choice_data], object="chat.completion"
        )

    gen_kwargs = {}
    if request.top_k is not None:
        gen_kwargs['top_k'] = request.top_k
    if request.temperature is not None:
        if request.temperature < 0.01:
            gen_kwargs['top_k'] = 1  # greedy decoding
        else:
            # Not recommended. Please tune top_p instead.
            gen_kwargs['temperature'] = request.temperature
    if request.top_p is not None:
        gen_kwargs['top_p'] = request.top_p

    stop_words = add_extra_stop_words(request.stop)
    if request.functions:
        stop_words = stop_words or []
        if 'Observation:' not in stop_words:
            stop_words.append('Observation:')

    query, system = parse_messages(request.messages, request.functions)

    if count_history % 2 == 0:
        history.append((query, ''))  # 添加问题
        count_history += 1
    else:
        print("error")

    if request.stream:
        if request.functions:
            raise HTTPException(
                status_code=400,
                detail=
                'Invalid request: Function calling is not yet implemented for stream mode.',
            )
        generate = predict(query,
                           history,
                           request.model,
                           stop_words,
                           gen_kwargs,
                           system=system)
        return EventSourceResponse(generate, media_type='text/event-stream')

    stop_words_ids = [tokenizer.encode(s)
                      for s in stop_words] if stop_words else None
    if query is _TEXT_COMPLETION_CMD:
        response = text_complete_last_message(history,
                                              stop_words_ids=stop_words_ids,
                                              gen_kwargs=gen_kwargs,
                                              system=system)
    else:
        response, _ = model.chat(
            tokenizer,
            query,
            history=history,
            system=system,
            stop_words_ids=stop_words_ids,
            **gen_kwargs,
        )

        if count_history % 2 != 0:
            history[-1] = (history[-1][0], response)  # 更新上一个元组，添加答案
            count_history += 1
        else:
            print("error")

        print('<chat>')
        pprint(history, indent=2)
        print(f'{query}\n<!-- *** -->\n{response}\n</chat>')
    _gc()

    response = trim_stop_words(response, stop_words)
    if request.functions:
        choice_data = parse_response(response)
    else:
        choice_data = ChatCompletionResponseChoice(
            index=0,
            message=ChatMessage(role='assistant', content=response),
            finish_reason='stop',
        )
    return ChatCompletionResponse(model=request.model,
                                  choices=[choice_data],
                                  object='chat.completion')


def _dump_json(data: BaseModel, *args, **kwargs) -> str:
    try:
        return data.model_dump_json(*args, **kwargs)
    except AttributeError:  # pydantic<2.0.0
        return data.json(*args, **kwargs)  # noqa


async def predict(
        query: str,
        history: List[List[str]],
        model_id: str,
        stop_words: List[str],
        gen_kwargs: Dict,
        system: str,
):
    global model, tokenizer
    choice_data = ChatCompletionResponseStreamChoice(
        index=0, delta=DeltaMessage(role='assistant'), finish_reason=None)
    chunk = ChatCompletionResponse(model=model_id,
                                   choices=[choice_data],
                                   object='chat.completion.chunk')
    yield '{}'.format(_dump_json(chunk, exclude_unset=True))

    current_length = 0
    stop_words_ids = [tokenizer.encode(s)
                      for s in stop_words] if stop_words else None

    delay_token_num = max([len(x) for x in stop_words]) if stop_words_ids else 0
    response_generator = model.chat_stream(tokenizer,
                                           query,
                                           history=history,
                                           stop_words_ids=stop_words_ids,
                                           system=system,
                                           **gen_kwargs)
    for _new_response in response_generator:
        if len(_new_response) <= delay_token_num:
            continue
        new_response = _new_response[:-delay_token_num] if delay_token_num else _new_response

        if len(new_response) == current_length:
            continue

        new_text = new_response[current_length:]
        current_length = len(new_response)

        choice_data = ChatCompletionResponseStreamChoice(
            index=0, delta=DeltaMessage(content=new_text), finish_reason=None)
        chunk = ChatCompletionResponse(model=model_id,
                                       choices=[choice_data],
                                       object='chat.completion.chunk')
        yield '{}'.format(_dump_json(chunk, exclude_unset=True))

    if current_length != len(_new_response):
        # Determine whether to print the delay tokens
        delayed_text = _new_response[current_length:]
        new_text = trim_stop_words(delayed_text, stop_words)
        if len(new_text) > 0:
            choice_data = ChatCompletionResponseStreamChoice(
                index=0, delta=DeltaMessage(content=new_text), finish_reason=None)
            chunk = ChatCompletionResponse(model=model_id,
                                           choices=[choice_data],
                                           object='chat.completion.chunk')
            yield '{}'.format(_dump_json(chunk, exclude_unset=True))

    choice_data = ChatCompletionResponseStreamChoice(index=0,
                                                     delta=DeltaMessage(),
                                                     finish_reason='stop')
    chunk = ChatCompletionResponse(model=model_id,
                                   choices=[choice_data],
                                   object='chat.completion.chunk')
    yield '{}'.format(_dump_json(chunk, exclude_unset=True))
    yield '[DONE]'

    _gc()


def _get_args():
    parser = ArgumentParser()
    parser.add_argument(
        '-c',
        '--checkpoint-path',
        type=str,
        default='Qwen-Audit',
        help='Checkpoint name or path, default to %(default)r',
    )
    parser.add_argument('--api-auth', help='API authentication credentials')
    parser.add_argument('--cpu-only',
                        action='store_true',
                        help='Run demo with CPU only')
    parser.add_argument('--server-port',
                        type=int,
                        default=8000,
                        help='Demo server port.')
    parser.add_argument(
        '--server-name',
        type=str,
        default='127.0.0.1',
        help=
        'Demo server name. Default: 127.0.0.1, which is only visible from the local computer.'
        ' If you want other computers to access your server, use 0.0.0.0 instead.',
    )
    parser.add_argument(
        '--disable-gc',
        action='store_true',
        help='Disable GC after each response generated.',
    )
    parser.add_argument(
        '--sql',
        type=str,
        default='False',
        help='Use SQL database for storing chat history.',
    )

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = _get_args()

    tokenizer = AutoTokenizer.from_pretrained(
        args.checkpoint_path,
        trust_remote_code=True,
        resume_download=True,
    )

    if args.api_auth:
        app.add_middleware(BasicAuthMiddleware,
                           username=args.api_auth.split(':')[0],
                           password=args.api_auth.split(':')[1])

    if args.cpu_only:
        device_map = 'cpu'
    else:
        device_map = 'auto'

    # if args.sql=="True":
    #     start_sql_server()

    model = AutoModelForCausalLM.from_pretrained(
        args.checkpoint_path,
        device_map=device_map,
        trust_remote_code=True,
        resume_download=True,
    ).eval()

    model.generation_config = GenerationConfig.from_pretrained(
        args.checkpoint_path,
        trust_remote_code=True,
        resume_download=True,
    )

    uvicorn.run(app, host=args.server_name, port=args.server_port, workers=1)
