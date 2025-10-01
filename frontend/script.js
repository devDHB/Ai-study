document.addEventListener('DOMContentLoaded', () => {
    // --- 変数定義 ---
    const chatForm = document.getElementById('input-form');
    const chatInput = document.getElementById('question-input');
    const messagesContainer = document.getElementById('messages');
    const chatApiUrl = 'http://127.0.0.1:8000/api/ask/';

    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const uploadApiUrl = 'http://127.0.0.1:8000/api/upload/';

    // アップロードされたファイルのセッションIDを保存する変数
    let currentSessionId = null;

    // --- ファイルアップロード ---
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) {
            uploadStatus.textContent = 'ファイルを選択してください。';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        uploadStatus.textContent = `'${file.name}' をアップロードして処理中...`;
        uploadForm.querySelector('button').disabled = true;

        try {
            const response = await fetch(uploadApiUrl, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'アップロードに失敗しました。');
            }

            uploadStatus.textContent = data.message;
            addMessage('ファイルがアップロードされました。このファイルの内容について質問できます。', 'bot');
            fileInput.value = '';

            // サーバーから受け取ったセッションIDを保存
            currentSessionId = data.session_id;
            console.log("New Session ID received:", currentSessionId);

        } catch (error) {
            console.error('Upload Error:', error);
            uploadStatus.textContent = `エラー: ${error.message}`;
        } finally {
            uploadForm.querySelector('button').disabled = false;
        }
    });

    // --- チャット送信ロジック ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = chatInput.value.trim();
        if (!question) return;

        addMessage(question, 'user');
        chatInput.value = '';
        chatForm.querySelector('button').disabled = true;
        const botMessageDiv = addMessage('回答を生成しています...', 'bot');

        try {
            // セッションIDを一緒に送信
            const payload = {
                question: question,
                session_id: currentSessionId
            };

            const response = await fetch(chatApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTPエラー! status: ${response.status}`);
            }

            const data = await response.json();

            const answerTextNode = botMessageDiv.firstChild;
            answerTextNode.textContent = data.answer;

            if (!data.answer.includes("申し訳ありません") && data.sources && data.sources.length > 0) {
                const sourcesContainer = document.createElement('div');
                sourcesContainer.className = 'sources-container';

                const sourcesHeader = document.createElement('h4');
                sourcesHeader.style.marginTop = '10px';
                sourcesHeader.style.marginBottom = '5px';
                sourcesHeader.textContent = '参考資料:';
                sourcesContainer.appendChild(sourcesHeader);

                data.sources.forEach(sourceText => {
                    const sourceDiv = document.createElement('div');
                    sourceDiv.className = 'source';
                    sourceDiv.textContent = sourceText;
                    sourcesContainer.appendChild(sourceDiv);
                });
                botMessageDiv.appendChild(sourcesContainer);
            }

        } catch (error) {
            console.error('API Error:', error);
            botMessageDiv.firstChild.textContent = 'エラーが発生しました。しばらくしてから再度お試しください。';
        } finally {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            chatForm.querySelector('button').disabled = false;
        }
    });

    // --- メッセージ画面に追加するヘルパー関数 ---
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        const textNode = document.createElement('span'); 
        textNode.textContent = text;
        messageDiv.appendChild(textNode);

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageDiv;
    }
});
