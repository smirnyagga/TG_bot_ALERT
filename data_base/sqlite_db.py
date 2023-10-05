import sqlite3 as sq

from create_bot import logging
from messages import morning_list, night_list


base = sq.connect('greeting.db')
cur = base.cursor()


async def sql_start():
    global base, cur
    base = sq.connect('greeting.db')
    cur = base.cursor()
    if base:
        logging.info('database connected ok!')

    base.execute('''CREATE TABLE IF NOT EXISTS main_admin
                    (main_admin INTEGER UNIQUE)''')
    base.execute('''CREATE TABLE IF NOT EXISTS chat_admin_time
                    (chat INTEGER UNIQUE, 
                    admin INTEGER, 
                    morning_hour INTEGER, 
                    morning_minute INTEGER, 
                    night_hour INTEGER, 
                    night_minute INTEGER
                    )''')
    base.execute('''CREATE TABLE IF NOT EXISTS morning_greeting
                                                    (id INTEGER, 
                                                    morning_message TEXT,
                                                    chat INTEGER)''')
    base.execute('''CREATE TABLE IF NOT EXISTS night_greeting
                                                    (id INTEGER, 
                                                    night_message TEXT,
                                                    chat INTEGER)''')
    base.execute('''CREATE TABLE IF NOT EXISTS permissions
                                                            (chat INTEGER, 
                                                            permissions TEXT)''')
    base.commit()


"""Функции общие"""


async def check_if_exists_admin():
    if cur.execute(f'''SELECT admin 
                        FROM chat_admin_time''').fetchall():
        return cur.execute(f'''SELECT admin 
                                FROM chat_admin_time''').fetchall()
    return None


async def check_if_exists_chat():
    if cur.execute(f'''SELECT chat 
                        FROM chat_admin_time''').fetchall():
        return cur.execute(f'''SELECT chat 
                                FROM chat_admin_time''').fetchall()
    else:
        return None


async def add_main_admin(data):
    cur.execute('''INSERT INTO main_admin(main_admin) 
                    VALUES(?)''', (data,))
    base.commit()


async def main_id():
    if cur.execute('SELECT main_admin '
                   'FROM main_admin').fetchone():
        return cur.execute('SELECT main_admin '
                           'FROM main_admin').fetchone()[0]
    else:
        return None


async def other_admins():
    admins_from_db = cur.execute('''SELECT admin 
                                 FROM chat_admin_time''').fetchall()
    other_admins_list = [i[0] for i in admins_from_db]
    return other_admins_list


async def get_chats_of_admin_from_db(admin):
    chat_id_from_db = cur.execute('''SELECT chat 
                                    FROM chat_admin_time
                                    WHERE admin == ?''', (admin,)).fetchall()
    chats_list = [i[0] for i in chat_id_from_db]
    return chats_list


async def get_info_chat(chat):
    full_info_about_chat = cur.execute('''SELECT *
                                        FROM chat_admin_time
                                        WHERE chat == ?''', (chat,)).fetchone()
    return full_info_about_chat


async def del_permissions_from_db(chat_id):
    cur.execute('''DELETE FROM permissions 
                                            WHERE chat == ?''', (chat_id,))
    base.commit()


"""Функции команд Старшего Администратора"""


async def insert_new_chat(data):
    cur.execute('''INSERT INTO chat_admin_time 
                VALUES(?, ?, ?, ?, ?, ?)''', (data['chat'], data['admin'], 6, 30, 22, 30))
    base.commit()


async def del_chat(chat):
    cur.execute('''DELETE FROM chat_admin_time 
                WHERE chat == ?''', (chat,))
    base.commit()


async def update_admin(data):
    cur.execute('''UPDATE chat_admin_time 
                SET admin == ? 
                WHERE chat == ?''', (data['admin'], data['chat']))
    base.commit()


"""Функции изменения времени"""


async def update_time(data):
    cur.execute('''UPDATE chat_admin_time 
                SET morning_hour == ? 
                WHERE chat == ?''', (data['morning_hour'], data['chat']))
    cur.execute('''UPDATE chat_admin_time 
                SET morning_minute == ? 
                WHERE chat == ?''', (data['morning_minute'], data['chat']))
    cur.execute('''UPDATE chat_admin_time 
                SET night_hour == ? 
                WHERE chat == ?''', (data['night_hour'], data['chat']))
    cur.execute('''UPDATE chat_admin_time 
                SET night_minute == ? 
                WHERE chat == ?''', (data['night_minute'], data['chat']))
    base.commit()


"""Функции для работы в БД при изменении сообщений"""


async def insert_messages(chat_id):
    for i in morning_list:
        cur.execute('''INSERT INTO morning_greeting VALUES(?, ?, ?)''', (i[0], i[1], chat_id))
    base.commit()

    for i in night_list:
        cur.execute('''INSERT INTO night_greeting VALUES(?, ?, ?)''', (i[0], i[1], chat_id))
    base.commit()


async def delete_all_morning_messages_of_chat(chat_id):
    cur.execute('''DELETE FROM morning_greeting 
                        WHERE chat == ?''', (chat_id,))
    base.commit()


async def delete_one_morning_messages_of_chat(chat_id, message_id):
    cur.execute('''DELETE FROM morning_greeting 
                        WHERE chat == ? AND id == ?''', (chat_id, message_id))
    base.commit()


async def delete_all_night_messages_of_chat(chat_id):
    cur.execute('''DELETE FROM night_greeting 
                        WHERE chat == ?''', (chat_id,))
    base.commit()


async def delete_one_night_messages_of_chat(chat_id, message_id):
    cur.execute('''DELETE FROM night_greeting 
                        WHERE chat == ? AND id == ?''', (chat_id, message_id))
    base.commit()


async def check_number_morning_message(number, chat_id):
    index = cur.execute('''SELECT morning_message
                            FROM morning_greeting 
                            WHERE chat == ? AND id == ?''', (chat_id, number)).fetchone()
    return index


async def check_number_night_message(number, chat_id):
    index = cur.execute('''SELECT night_message
                            FROM night_greeting 
                            WHERE chat == ? AND id == ?''', (chat_id, number)).fetchone()
    return index


async def insert_many_morning(info, chat_id):
    for i in info:
        cur.execute('''INSERT INTO morning_greeting VALUES(?, ?, ?)''', (i[0], i[1], chat_id))
    base.commit()


async def insert_many_night(info, chat_id):
    for i in info:
        cur.execute('''INSERT INTO night_greeting VALUES(?, ?, ?)''', (i[0], i[1], chat_id))
    base.commit()


async def update_one_morning(data, chat_id):
    cur.execute('''UPDATE morning_greeting 
                        SET morning_message == ? 
                        WHERE id == ? AND chat = ?''', (data[1], data[0], chat_id))
    base.commit()


async def update_one_night(data, chat_id):
    cur.execute('''UPDATE night_greeting 
                        SET night_message == ? 
                        WHERE id == ? AND chat = ?''', (data[1], data[0], chat_id))
    base.commit()


async def add_one_morning(id, data, chat_id):
    cur.execute('''INSERT INTO morning_greeting 
                    VALUES(?, ?, ?)''', (id, data, chat_id))
    base.commit()


async def add_one_night(id, data, chat_id):
    cur.execute('''INSERT INTO night_greeting 
                    VALUES(?, ?, ?)''', (id, data, chat_id))
    base.commit()


async def get_messages_morning(chat):
    info = cur.execute(f'''SELECT id, morning_message 
                        FROM morning_greeting 
                        WHERE chat = ?''', (chat,)).fetchall()
    return info


async def last_id_morning(chat):
    last_id_db = cur.execute('''SELECT id 
                            FROM morning_greeting 
                            WHERE chat = ?
                            ORDER BY id DESC''', (chat,)).fetchone()
    id = last_id_db[0] + 1
    return id


async def get_messages_night(chat):
    info = cur.execute(f'''SELECT id, night_message 
                        FROM night_greeting 
                        WHERE chat = ?''', (chat,)).fetchall()
    return info


async def last_id_night(chat):
    last_id_db = cur.execute('''SELECT id 
                            FROM night_greeting 
                            WHERE chat = ?
                            ORDER BY id DESC''', (chat,)).fetchone()
    id = last_id_db[0] + 1
    return id


"""Функции миграции id чата"""


async def table_for_exchange(new_chat_id, name):
    base.execute('''CREATE TABLE IF NOT EXISTS exchange
                                (old INTEGER, 
                                new INTEGER,
                                id INTEGER,
                                name TEXT)''')
    base.commit()
    cur.execute('''INSERT INTO exchange(new, id, name) 
                                VALUES(?, ?, ?)''', (new_chat_id, 1, name))
    base.commit()


async def update_chat(new_id, old_id):
    cur.execute('''UPDATE chat_admin_time 
                SET chat == ? 
                WHERE chat = ?''', (new_id, old_id))

    cur.execute('''UPDATE morning_greeting 
                SET chat == ? 
                WHERE chat = ?''', (new_id, old_id))

    cur.execute('''UPDATE night_greeting 
                SET chat == ? 
                WHERE chat = ?''', (new_id, old_id))

    cur.execute('''UPDATE permissions 
                SET chat == ? 
                WHERE chat = ?''', (new_id, old_id))
    base.commit()
