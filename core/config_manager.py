from data.database import get_connection


class ConfigManager:
    @staticmethod
    def get(key, default=None):
        conn = get_connection()
        row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        conn.close()
        if row is None:
            return default
        return row['value']

    @staticmethod
    def set(key, value):
        conn = get_connection()
        conn.execute(
            'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
            (key, str(value))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_bool(key, default=False):
        val = ConfigManager.get(key)
        if val is None:
            return default
        return val == '1'

    @staticmethod
    def set_bool(key, value):
        ConfigManager.set(key, '1' if value else '0')