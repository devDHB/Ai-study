document.addEventListener('DOMContentLoaded', () => {
    // --- 변수 정의 ---
    const chatForm = document.getElementById('input-form');
    const chatInput = document.getElementById('question-input');
    const messagesContainer = document.getElementById('messages');
    const chatApiUrl = 'http://127.0.0.1:8000/api/ask/';

    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const uploadApiUrl = 'http://127.0.0.1:8000/api/upload/';

    // 업로드된 파일의 고유 ID를 저장할 변수
    let currentSessionId = null;

    // --- 파일 업로드 로직 ---
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) {
            uploadStatus.textContent = '파일을 선택해주세요.';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        uploadStatus.textContent = `'${file.name}' 업로드 및 처리 중...`;
        uploadForm.querySelector('button').disabled = true;

        try {
            const response = await fetch(uploadApiUrl, {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '업로드에 실패했습니다.');
            }
            
            uploadStatus.textContent = data.message;
            addMessage('파일이 업로드되었습니다. 이제 이 파일의 내용에 대해 질문할 수 있습니다.', 'bot');
            fileInput.value = '';
            
            // 서버로부터 받은 세션 ID를 변수에 저장합니다.
            currentSessionId = data.session_id;
            console.log("New Session ID received:", currentSessionId);

        } catch (error) {
            console.error('Upload Error:', error);
            uploadStatus.textContent = `오류: ${error.message}`;
        } finally {
            uploadForm.querySelector('button').disabled = false;
        }
    });

    // --- 채팅 메시지 전송 로직 ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = chatInput.value.trim();
        if (!question) return;

        addMessage(question, 'user');
        chatInput.value = '';
        chatForm.querySelector('button').disabled = true;
        const botMessageDiv = addMessage('답변을 생성 중입니다...', 'bot');

        try {
            // body에 세션 ID를 포함하여 전송합니다.
            const payload = {
                question: question,
                session_id: currentSessionId // 저장해둔 세션 ID를 함께 보냅니다.
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
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            const answerTextNode = botMessageDiv.firstChild;
            answerTextNode.textContent = data.answer;

            if (!data.answer.includes("죄송합니다") && data.sources && data.sources.length > 0) {
                const sourcesContainer = document.createElement('div');
                sourcesContainer.className = 'sources-container';
                
                const sourcesHeader = document.createElement('h4');
                sourcesHeader.style.marginTop = '10px';
                sourcesHeader.style.marginBottom = '5px';
                sourcesHeader.textContent = '참고 자료:';
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
            botMessageDiv.firstChild.textContent = '오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
        } finally {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            chatForm.querySelector('button').disabled = false;
        }
    });

    // --- 메시지 화면에 추가하는 헬퍼 함수 ---
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