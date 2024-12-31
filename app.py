import os
import random
import base64
import json
import requests
from flask import Flask, jsonify
from datetime import datetime, timedelta
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

# Загружаем пожелания из wishes.json
with open('wishes.json', 'r', encoding='utf-8') as f:
    wishes = json.load(f)

# Словарь для отслеживания отправленных пожеланий
user_last_sent = {}

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

def send_message(chat_id, text):
    headers = {
        'Content-Type': 'application/json',
        'X-YoAI-API-Key': YOAI_API_KEY
    }
    data = {
        'chatId': chat_id,
        'text': base64.b64encode(text.encode()).decode()
    }
    response = requests.post(SEND_MESSAGE_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        logging.info(f'Сообщение отправлено в чат {chat_id}')
    else:
        logging.error(f'Ошибка при отправке сообщения: {response.status_code}')

def get_random_wishes():
    # Получаем текущую дату для отслеживания
    today = datetime.now().date()
    
    # Отслеживаем, когда пользователю в последний раз отправлялись пожелания
    sent_today = user_last_sent.get('date') == today
    
    if sent_today:
        # Если пожелания уже были отправлены сегодня, то берем не более 3 случайных
        return random.sample(wishes, 3)  # Берем 3 случайных пожелания
    else:
        # Если пожелания еще не отправлялись, выбираем 1-3 случайных пожелания
        selected_wishes = random.sample(wishes, random.randint(1, 3))  # 1-3 пожелания
        user_last_sent['date'] = today  # Обновляем дату отправки
        user_last_sent['sent_wishes'] = selected_wishes  # Обновляем отправленные пожелания
        return selected_wishes

def process_messages():
    updates = get_updates()
    for update in updates:
        chat_id = update.get('chatId')
        text = base64.b64decode(update.get('text')).decode()
        if 'youtube.com' in text or 'youtu.be' in text:
            logging.info(f'Найдена YouTube ссылка в чате {chat_id}: {text}')
            wishes_to_send = get_random_wishes()
            message = '\n'.join(wishes_to_send)
            send_message(chat_id, message)
        else:
            logging.info(f'Получено сообщение без YouTube ссылки в чате {chat_id}')

@app.route('/webhook', methods=['POST'])
def webhook():
    process_messages()
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
