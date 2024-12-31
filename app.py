import os
import base64
import requests
from flask import Flask, jsonify, send_file
import yt_dlp
import logging

app = Flask(__name__)

# Установите уровень логирования
logging.basicConfig(level=logging.DEBUG)

# Получаем API-ключ из переменной окружения
YOAI_API_KEY = os.getenv('YOAI_API_KEY')

# URL для получения обновлений
GET_UPDATES_URL = 'https://yoai.yophone.com/api/pub/getUpdates'

# URL для отправки сообщений
SEND_MESSAGE_URL = 'https://yoai.yophone.com/api/pub/sendMessage'

# Проверка, что API-ключ установлен
if not YOAI_API_KEY:
    logging.error('API-ключ YoAI не найден. Установите переменную окружения YOAI_API_KEY.')
    exit(1)

@app.route('/')
def home():
    return 'Сервер работает! Бот готов к работе.', 200

def get_updates():
    headers = {
        'Content-Type': 'application/json',
        'X-YoAI-API-Key': YOAI_API_KEY
    }
    response = requests.post(GET_UPDATES_URL, headers=headers, json={})
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        logging.error(f'Ошибка при получении обновлений: {response.status_code}')
        return []

def send_message(chat_id, text, file_path=None):
    headers = {
        'Content-Type': 'application/json',
        'X-YoAI-API-Key': YOAI_API_KEY
    }
    data = {
        'chatId': chat_id,
        'text': base64.b64encode(text.encode()).decode()
    }
    if file_path:
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'audio/mpeg')
            }
            response = requests.post(SEND_MESSAGE_URL, headers=headers, data=data, files=files)
    else:
        response = requests.post(SEND_MESSAGE_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        logging.info(f'Сообщение отправлено в чат {chat_id}')
    else:
        logging.error(f'Ошибка при отправке сообщения: {response.status_code}')

def download_youtube_audio(url):
    try:
        output_dir = 'downloads'
        os.makedirs(output_dir, exist_ok=True)
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict).replace('.webm', '.mp3').replace('.m4a', '.mp3')
            logging.debug(f'Скачанный файл: {filename}')
            return filename
    except Exception as e:
        logging.exception('Ошибка при загрузке аудио:')
        return None

def process_messages():
    updates = get_updates()
    for update in updates:
        chat_id = update.get('chatId')
        text = base64.b64decode(update.get('text')).decode()
        if 'youtube.com' in text or 'youtu.be' in text:
            logging.info(f'Найдена YouTube ссылка в чате {chat_id}: {text}')
            mp3_file = download_youtube_audio(text)
            if mp3_file:
                send_message(chat_id, 'Вот ваш MP3 файл:', mp3_file)
            else:
                send_message(chat_id, 'Не удалось загрузить аудио. Пожалуйста, проверьте ссылку.')
        else:
            logging.info(f'Получено сообщение без YouTube ссылки в чате {chat_id}')

@app.route('/webhook', methods=['POST'])
def webhook():
    process_messages()
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
