python -m venv venv

(Windows)
.\venv\Scripts\activate

pip install -r requirements.txt

.env作成
APIKEY追加
PERPLEXITY_API_KEY="pplx-..."

python manage.py migrate

サーバー実行
** Backend
python manage.py runserver

** Frontend
cd frontend
python -m http.server 8080
