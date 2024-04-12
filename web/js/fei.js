document.addEventListener('DOMContentLoaded', function () {
    // 在DOMContentLoaded事件触发后执行的代码
    var questionInput = document.getElementById('questionInput');
    var submitButton = document.getElementById('submitButton');

    // 添加事件监听器
    questionInput.addEventListener('keypress', function (event) {
        if (event.keyCode === 13 || event.which === 13) {
            event.preventDefault();
            submitButton.click();
        }
    });
});


function askQuestion() {
    var question = document.getElementById('questionInput').value;
    if (question.trim() === '') {
        return;
    }

    var historyContainer = document.getElementById('historyContainer');
    var historyItem = document.createElement('p');
    historyItem.innerHTML = '<strong>问题：</strong>' + question;
    historyContainer.appendChild(historyItem);
    // 滚动到历史记录的底部
    historyContainer.scrollTop = historyContainer.scrollHeight;
    // 获取当前历史记录
    var history = [];
    var historyItems = historyContainer.getElementsByTagName('p');
    for (var i = 0; i < historyItems.length; i++) {
        history.push(historyItems[i].textContent);
    }

    axios.post('http://localhost:8000/v1/chat/completions', {
        model: 'Qwen-Audit',
        messages: [{role: 'user', content: question}],
        temperature: 0.7,
        top_p: 0.9,
        max_length: 150,
        history: history // 将历史记录作为参数传递给后端
    })
        .then(function (response) {
            var answer = response.data.choices[0].message.content;
            var answerItem = document.createElement('p');
            answerItem.innerHTML = '<strong>回答：</strong>' + answer;
            historyContainer.appendChild(answerItem);

            // 滚动到历史记录的底部
            historyContainer.scrollTop = historyContainer.scrollHeight;
            // 向服务器发送用户问题和AI回答
            sendMessageToServer(question, answer);
        })
        .catch(function (error) {
            // 处理错误，将错误信息显示在历史记录框里
            var errorMessage = "错误：" + error.response.data.detail;
            var errorItem = document.createElement('p');
            errorItem.innerHTML = '<strong>' + errorMessage + '</strong>';
            historyContainer.appendChild(errorItem);

            // 滚动到历史记录的底部
            historyContainer.scrollTop = historyContainer.scrollHeight;

        });

    document.getElementById('questionInput').value = '';
}

function askRecommendedQuestion(question) {
    document.getElementById('questionInput').value = question; // 将点击的问题填入问答框

    // 获取当前历史记录
    var historyContainer = document.getElementById('historyContainer');
    var history = [];
    var historyItems = historyContainer.getElementsByTagName('p');
    for (var i = 0; i < historyItems.length; i++) {
        history.push(historyItems[i].textContent);
    }

    // 调用 askQuestion 函数时传递历史记录参数
    askQuestion(history);
}

function sendMessageToServer(question, answer) {
    axios.post('http://localhost:8000/add_message', {
        role: 'user',
        content: question
    })
        .then(function (response) {
            console.log('问题已保存');
            // 保存回答
            axios.post('http://localhost:8000/add_message', {
                role: 'assistant',
                content: answer
            })
                .then(function (response) {
                    console.log('回答已保存');
                })
                .catch(function (error) {
                    console.error('保存回答时出错：', error);
                });
        })
        .catch(function (error) {
            console.error('保存问题时出错：', error);
        });
}

function startNewChat() {
    axios.get('http://localhost:8000/latest_group_id')
        .then(function (response) {
            var latestGroupID = response.data.latest_group_id;

            // 创建新按钮
            var newButton = document.createElement('button');
            newButton.id = latestGroupID + 1;

            newButton.textContent = "新的对话" + newButton.id; // 设置按钮文本内容为最新的 ID
            // 添加点击事件处理程序

            // 添加点击事件处理程序
            newButton.onclick = function () {


                var groupId = newButton.id; // 获取按钮中的数字
                sendGroupId(groupId); // 将按钮中的数字发送到后端

                clearChatHistory();
                // 在前端页面上显示新的问答界面或提示信息
                displayNewChatMessage("开始新的问答！");

                axios.get('http://localhost:8000/question_answer')
                    .then(function (response) {
                        var question_answer = response.data.question_answer;
                        for (var i = 0; i < question_answer.length; i++) {
                            var historyContainer = document.getElementById('historyContainer');
                            var historyItem = document.createElement('p');
                            historyItem.textContent = '问题：' + question_answer[i][0];
                            historyContainer.appendChild(historyItem);

                            var answerItem = document.createElement('p');
                            answerItem.innerHTML = '<strong>回答：</strong>' + question_answer[i][1];
                            historyContainer.appendChild(answerItem);
                        }
                    })
                    .catch(function (error) {
                        console.error('请求问题和答案出错：', error);
                    });
            };


            // 向服务器发送请求，告知服务器清除当前问答历史
            axios.post('http://localhost:8000/new_chat')
                .then(function (response) {
                    // 清除前端页面上的问答历史
                    clearChatHistory();
                    // 在前端页面上显示新的问答界面或提示信息
                    displayNewChatMessage("开始新的问答！");
                })
                .catch(function (error) {
                    console.error('请求出错：', error);
                });

            axios.get('http://localhost:8000/time_now')
                .then(function (response) {
                    newButton.textContent = response.data.time_now
                })
            // 将新按钮添加到页面上
            var newButtonContainer = document.getElementById('newContainer');
            newButtonContainer.appendChild(newButton);
        })
        .catch(function (error) {
            console.error('请求出错：', error);
        });


}

function clearChatHistory() {
    // 清除前端页面上的问答历史信息
    var historyContainer = document.getElementById('historyContainer');
    historyContainer.innerHTML = '';
}

function displayNewChatMessage(message) {
    // 在前端页面上显示新的提示信息
    var historyContainer = document.getElementById('historyContainer');
    var messageItem = document.createElement('p');
    messageItem.textContent = message;
    historyContainer.appendChild(messageItem);

}

function displayTimeKeys() {
    var questionSetIDElement = document.getElementById('questionSetID');
    var questionIDElement = document.getElementById('questionID');
    var currentTimeElement = document.getElementById('currentTime');

    questionSetIDElement.textContent = question_set_id;
    questionIDElement.textContent = question_id;
    currentTimeElement.textContent = getCurrentTime();
}

function getCurrentTime() {
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;
    var day = now.getDate();
    var hour = now.getHours();
    var minute = now.getMinutes();
    var second = now.getSeconds();
    return year + '-' + month + '-' + day + ' ' + hour + ':' + minute + ':' + second;
}

function sendGroupId(groupId) {
    // 将字符串类型的 groupId 转换为整数类型
    var groupIdInt = parseInt(groupId);
    axios.post('http://localhost:8000/retrieve_content', {content: groupIdInt})
        .then(function (response) {
            console.log('成功检索内容：', response.data);
            // 这里可以根据返回的内容执行相应的操作，比如显示在页面上
        })
        .catch(function (error) {
            console.error('检索内容出错：', groupIdInt);
        });
}

function history_button_show() {
    axios.get('http://localhost:8000/time_history')
        .then(function (response) {
            var GroupID_Time = response.data.Group_Time;
            for (var i = 0; i < GroupID_Time.length; i++) {
                // 创建新按钮
                var newButton1 = document.createElement('button');
                newButton1.id = GroupID_Time[i][0];
                a = GroupID_Time[i][2];
                newButton1.textContent = a; // 设置按钮文本内容为最新的 ID
                newButton1.classList.add('userButton');
                // 将新按钮添加到页面上
                var newButtonContainer = document.getElementById('newContainer');
                newButtonContainer.appendChild(newButton1);
            }
            var buttons = document.querySelectorAll(".userButton");
            buttons.forEach(function (button) {
                button.addEventListener("click", function () {

                    // 获取按钮上存储的用户 ID
                    var userId = this.getAttribute("id");
                    sendGroupId(userId)

                    clearChatHistory();
                    // 在前端页面上显示新的问答界面或提示信息
                    displayNewChatMessage("开始新的问答！");

                    axios.get('http://localhost:8000/question_answer')
                        .then(function (response) {
                            var question_answer = response.data.question_answer;
                            for (var i = 0; i < question_answer.length; i++) {
                                var historyContainer = document.getElementById('historyContainer');
                                var historyItem = document.createElement('p');
                                historyItem.textContent = '问题：' + question_answer[i][0];
                                historyContainer.appendChild(historyItem);

                                var answerItem = document.createElement('p');
                                answerItem.innerHTML = '<strong>回答：</strong>' + question_answer[i][1];
                                historyContainer.appendChild(answerItem);
                            }
                        })
                        .catch(function (error) {
                            console.error('请求问题和答案出错：', error);
                        });
                })
            })
        })
}


function openAboutPage() {
    window.open('./pages/about.html', '_blank');
}

document.addEventListener("DOMContentLoaded", function () {
    // 在DOM加载完成后执行的代码
    history_button_show();
});