from datetime import datetime, timedelta, time
import json
import random
import pytz

from create_bot import bot, scheduler, Bot, logging
from data_base import sqlite_db
from handlers import admin


async def check_time(data, message, chat_id):
    """
    Функция, которая проверяет, нужно ли включать или выключать ночной режим
    сразу после изменения времени администраторами.
    Есть определенные периоды времени, например: в БД указано время 8:00 для включения чата.
    На данный момент: 7:00. и Чат еще закрыт. Администратор меняет время на 6:00, то есть
    чат должен открыться. Но этого не происходит, так как модифицированный scheduler будет ждать
    следующие сутки, пока не наступит 6:00, чтобы открыть чат. Все это время чат будет закрыт.
    """

    main_admin = await sqlite_db.main_id()

    tz_moscow = pytz.timezone("Europe/Moscow")
    current_date_time = datetime.now(tz_moscow)
    current_time = current_date_time.time()

    full_info_about_chat = await sqlite_db.get_info_chat(chat_id)
    mh = full_info_about_chat[2]
    mm = full_info_about_chat[3]
    nh = full_info_about_chat[4]
    nm = full_info_about_chat[5]

    old_time_morning = time(hour=mh, minute=mm, second=0)
    old_time_night = time(hour=nh, minute=nm, second=0)

    new_time_morning = time(data['morning_hour'], data['morning_minute'], 0)
    new_time_night = time(data['night_hour'], data['night_minute'], 0)

    """ситуация, возникающая чаще при проверке работы бота админом.
    когда настоящее время попадает во временные отрезки и утреннего времени и вечернего сразу.
    например: сейчас 4:25. 
    старое время 4:30 - 4:39. стоит ночной режим.
    новое время 4:20-4:22. 
    Бот будет менять сначала на дневной режим, потом на ночной. а на самом деле нужно оставить чат в покое."""

    if current_time > old_time_morning and current_time < new_time_morning and\
            current_time > old_time_night and current_time < new_time_night or\
            current_time < old_time_night and current_time > new_time_night and\
            current_time < old_time_morning and current_time > new_time_morning:
        return None

    """следующие варианты отслеживают варианты, когда необходимо поменять режим в настоящий момент"""

    if current_time > old_time_morning and current_time < new_time_morning or \
            current_time < old_time_night and current_time > new_time_night:
        try:
            await night_mode(chat_id, message.from_user.id, main_admin)
            await message.reply('В чатe нельзя писать.')
        except Exception as e:
            logging.error(f'Ошибка: {e}')
    if current_time < old_time_morning and current_time > new_time_morning or \
            current_time > old_time_night and current_time < new_time_night:
        try:
            await day_mode(chat_id, message.from_user.id, main_admin)
            await message.reply('В чатe можно писать.')
        except Exception as e:
            logging.error(f'Ошибка: {e}')


async def night_mode(chat_id, admin_id, main_admin):
    """
    Функции включения ночного режима, когда нельзя писать сообщения в группу.
    Используются в Scheduler
    """

    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    permissions_of_chat = await bot.get_chat(chat_id=chat_id)

    """заносим в таблицу данные о пермишенс, до следующего утра, 
    чтобы включить в чате именно те разрешения, что были до ночи"""

    sqlite_db.cur.execute('''INSERT INTO permissions 
                        VALUES(?, ?)''', (chat_id, str(permissions_of_chat['permissions'])))
    sqlite_db.base.commit()

    new_permissions = permissions_of_chat['permissions']

    new_permissions['can_send_messages'] = False
    new_permissions['can_send_media_messages'] = False
    new_permissions['can_send_audios'] = False
    new_permissions['can_send_documents'] = False
    new_permissions['can_send_photos'] = False
    new_permissions['can_send_videos'] = False
    new_permissions['can_send_video_notes'] = False
    new_permissions['can_send_voice_notes'] = False
    new_permissions['can_send_polls'] = False
    new_permissions['can_send_other_messages'] = False
    new_permissions['can_add_web_page_previews'] = False

    if await admin.check_if_admin(bot_id, chat_id):
        try:
            await bot.set_chat_permissions(chat_id=chat_id, permissions=new_permissions)
        except Exception as e:
            logging.error(f'Ошибка: {e}')
            await bot.send_message(admin_id, f'''В чате {chat_id} не удалось включить ночной режим. \'
            Cкорее всего, у бота недостаточно прав, для ограничения пользователей. Проверьте права бота в чате.''')
    else:
        await bot.send_message(admin_id, f'''В чате {chat_id} не удалось включить ночной режим, \
        так как бота удалили из администраторов. Запрос на удаление чата из базы данных \
        или возвращения бота в администраторы отправлен старшему администратору.''')
        await bot.send_message(main_admin, f'''В чате {chat_id} бота удалили из администраторов. \
        Пожалуйста, удалите этот чат из бота /del_chat. Либо верните боту статус администратора \
        для продолжения его работы в этом чате.''')


async def day_mode(chat_id, admin_id, main_admin):
    """
    Функции отключения ночного режима
    Используются в Scheduler
    """
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id

    """проверяем, есть ли в БД данные о разрешениях по этому чату
    если есть-используем их. если нет_просто открываем отправку сообщений"""

    if sqlite_db.cur.execute('''SELECT permissions
                                        FROM permissions
                                        WHERE chat == ?''', (chat_id,)).fetchone():
        perm = sqlite_db.cur.execute('''SELECT permissions
                                        FROM permissions
                                        WHERE chat == ?''', (chat_id,)).fetchone()[0]
        new_permissions = json.loads(perm)

        await sqlite_db.del_permissions_from_db(chat_id)
    else:
        new_permissions = {}
        new_permissions['can_send_messages'] = True
        new_permissions['can_send_media_messages'] = True
        new_permissions['can_send_audios'] = True
        new_permissions['can_send_documents'] = True
        new_permissions['can_send_photos'] = True
        new_permissions['can_send_videos'] = True
        new_permissions['can_send_video_notes'] = True
        new_permissions['can_send_voice_notes'] = True
        new_permissions['can_send_polls'] = True
        new_permissions['can_send_other_messages'] = True
        new_permissions['can_add_web_page_previews'] = True

    if await admin.check_if_admin(bot_id, chat_id):
        try:
            await bot.set_chat_permissions(chat_id=chat_id, use_independent_chat_permissions=True, permissions=new_permissions)
        except Exception as e:
            logging.error(f'Ошибка: {e}')
            await bot.send_message(admin_id, f'''В чате {chat_id} не удалось выключить ночной режим.\
            Cкорее всего, у бота недостаточно прав, для ограничения пользователей. Проверьте права бота в чате.''')
    else:
        await bot.send_message(admin_id, f'''В чате {chat_id} не удалось включить ночной режим, \
        так как бота удалили из администраторов. Запрос на удаление чата из базы данных \
        или возвращения бота в администраторы отправлен старшему администратору.''')
        await bot.send_message(main_admin, f'''В чате {chat_id} бота удалили из администраторов. \
        Пожалуйста, удалите этот чат из бота /del_chat. Либо верните боту статус администратора \
        для продолжения его работы в этом чате.''')


async def function():
    """Пустая функция, чтобы запустить Sheduler при запуске бота"""
    pass


async def greeting_morning(bot: Bot, chat_id, admin_id):
    """Отправка утренних сообщений, используется в Scheduler"""
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    if await admin.check_if_admin(bot_id, chat_id):
        message_from_db = sqlite_db.cur.execute('''SELECT morning_message
                                                FROM morning_greeting
                                                WHERE chat = ?''', (chat_id,)).fetchall()
        if message_from_db:
            list_messages = [str(i[0]) for i in message_from_db]
        else:
            await bot.send_message(admin_id,
                                   f'''Утреннее сообщение в ваш чат с id {chat_id} не отправлено,\
                                   так как вы удалили все сообщения из базы данных.
                                   \nДобавьте сообщения, чтобы бот начал работу - /morning''')
            return None
        try:
            await bot.send_message(chat_id, text=random.choice(list_messages))
        except Exception as e:
            await bot.send_message(admin_id,
                                   f'''Не удалось отправить сообщение в ваш чат с id {chat_id}.
                                   \nПроверьте, добавлен ли бот в эту группу. И id этой группы''')
            logging.error(f'Ошибка: {e}')


async def greeting_night(bot: Bot, chat_id, admin_id):
    """Отправка ночных сообщений, используется в Scheduler"""
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    if await admin.check_if_admin(bot_id, chat_id):
        message_from_db = sqlite_db.cur.execute('''SELECT night_message
                                                FROM night_greeting
                                                WHERE chat = ?''', (chat_id,)).fetchall()
        if message_from_db:
            list_messages = [str(i[0]) for i in message_from_db]
        else:
            await bot.send_message(admin_id,
                                   f'''Вечернее сообщение в ваш чат с id {chat_id} не отправлено,\
                                   так как вы удалили все сообщения из базы данных. 
                                   \nДобавьте сообщения, чтобы бот начал работу - /night''')
            return None
        try:
            await bot.send_message(chat_id, text=random.choice(list_messages))
        except Exception as e:
            await bot.send_message(admin_id,
                                   f'''Не удалось отправить сообщение в ваш чат с id {chat_id}.
                                   \nПроверьте, добавлен ли бот в эту группу. И id этой группы''')
            logging.error(f'Ошибка: {e}')


async def add_jobs_for_chat(chat_id, admin_id, mh, mm, nh, nm, main_admin):
    """
    При добавлении старшим администратором чата в БД, добавляет в Scheduler новые задачи.
    """
    scheduler.add_job(greeting_morning,
                      id=f'''morning_message_{str(chat_id)}''',
                      trigger='cron',
                      hour=mh,
                      minute=mm,
                      start_date=datetime.now()+timedelta(seconds=10),
                      misfire_grace_time=1000,
                      kwargs={'bot': bot, 'chat_id': chat_id, 'admin_id': admin_id})
    scheduler.add_job(greeting_night,
                      id=f'''night_message_{str(chat_id)}''',
                      trigger='cron',
                      hour=nh,
                      minute=nm,
                      start_date=datetime.now() + timedelta(seconds=10),
                      misfire_grace_time=1000,
                      kwargs={'bot': bot, 'chat_id': chat_id, 'admin_id': admin_id})
    scheduler.add_job(night_mode,
                      id=f'''night_mode_{str(chat_id)}''',
                      trigger='cron',
                      hour=nh,
                      minute=nm,
                      start_date=datetime.now() + timedelta(seconds=10),
                      misfire_grace_time=1000,
                      kwargs={'admin_id': admin_id, 'chat_id': chat_id, 'main_admin': main_admin})
    scheduler.add_job(day_mode,
                      id=f'''day_mode_{str(chat_id)}''',
                      trigger='cron',
                      hour=mh,
                      minute=mm,
                      start_date=datetime.now() + timedelta(seconds=10),
                      misfire_grace_time=1000,
                      kwargs={'admin_id': admin_id, 'chat_id': chat_id, 'main_admin': main_admin})


async def run_scheduler():
    """
    Запуск при старте. При отсутствии чатов в БД, выполняет пустую функцию,
    при наличии чатов-добавляет все задачи по этим чатам.
    """
    main_admin = await sqlite_db.main_id()
    info_for_scheduler = sqlite_db.cur.execute('''SELECT *
                        FROM chat_admin_time''').fetchall()
    if info_for_scheduler:
        for i in info_for_scheduler:
            await add_jobs_for_chat(i[0], i[1], i[2], i[3], i[4], i[5], main_admin)
        scheduler.start()
    else:
        scheduler.add_job(function,
                          id=0,
                          trigger='date',
                          run_date=datetime.now()+timedelta(seconds=10))
        scheduler.start()


async def modify(chat_id, new_mh, new_mm, new_nh, new_nm):
    """Модификация задач Sheduler при изменении времени"""
    scheduler.reschedule_job(job_id=f'''morning_message_{str(chat_id)}''',
                             trigger='cron',
                             hour=new_mh,
                             minute=new_mm)
    scheduler.reschedule_job(job_id=f'''night_message_{str(chat_id)}''',
                             trigger='cron',
                             hour=new_nh,
                             minute=new_nm)
    scheduler.reschedule_job(job_id=f'''night_mode_{str(chat_id)}''',
                             trigger='cron',
                             hour=new_nh,
                             minute=new_nm)
    scheduler.reschedule_job(job_id=f'''day_mode_{str(chat_id)}''',
                             trigger='cron',
                             hour=new_mh,
                             minute=new_mm)


async def del_job_from_scheduler(chat_id):
    """Удаляет задачи при удалени чата из БД"""
    scheduler.remove_job(f'''morning_message_{str(chat_id)}''')
    scheduler.remove_job(f'''night_message_{str(chat_id)}''')
    scheduler.remove_job(f'''night_mode_{str(chat_id)}''')
    scheduler.remove_job(f'''day_mode_{str(chat_id)}''')
