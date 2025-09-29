// frontend/script.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('input-form');
    const input = document.getElementById('question-input');
    const messagesContainer = document.getElementById('messages');
    const apiUrl = 'http://127.0.0.1:8000/api/ask/';

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = input.value.trim();
        if (!question) return;

        addMessage(question, 'user');
        input.value = '';

        const botMessageDiv = addMessage('답변을 생성 중입니다...', 'bot');

        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: question }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // --- 이 부분이 수정되었습니다 ---
            // 1. 기존 로딩 메시지를 실제 답변으로 교체
            //    답변 텍스트만 표시하도록 botMessageDiv의 첫 번째 자식 노드를 찾습니다.
            const answerTextNode = botMessageDiv.firstChild;
            answerTextNode.textContent = data.answer;

            // 2. 출처(sources)가 있다면 화면에 추가
            // AI가 "죄송합니다"라고 답변하지 않은, 유용한 답변일 경우에만 출처를 표시합니다.
            if (!data.answer.includes("죄송합니다") && data.sources && data.sources.length > 0) {
                const sourcesContainer = document.createElement('div');
                sourcesContainer.className = 'sources-container';
                
                const sourcesHeader = document.createElement('h4');
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
        }
    });

    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const textNode = document.createElement('span'); // 답변과 출처를 분리하기 위해 span으로 감쌉니다.
        textNode.textContent = text;
        messageDiv.appendChild(textNode);
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return messageDiv; // div 전체를 반환
    }
});