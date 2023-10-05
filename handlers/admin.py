from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import types
from aiogram.dispatcher.filters import Text

from create_bot import bot, logging
from data_base import sqlite_db
from handlers import other

from datetime import time


async def check_if_admin(user_id, chat_id):
    """Функция проверяет, является ли заданный id администратором в заданной группе"""
    try:
        admins_info = await bot.get_chat_administrators(chat_id)
        admins = [i['user']['id'] for i in admins_info]
    except Exception as e:
        logging.error(f'Ошибка: {e}')
        return False
    if user_id in admins:
        return True
    return False


async def start(message: types.Message):
    """
    При срабатывании первый раз, определяет пользователя как старшего администратора (в дальнейшем-СА)
    В следующий раз распознакоет СА как СА.
    Если вводит не СА-проверяет, есть ли пользователь в списке других администраторов (ДА),
    которые управляют ботом, которых назначил СА.
    Если ни в каком списке нет-прощается
    """
    main_admin_from_db = await sqlite_db.main_id()
    if main_admin_from_db:
        """Если в таблице с СА уже есть айди"""
        if message.from_user.id == main_admin_from_db:
            """Если айди пишущего совпадает с СА из БД"""
            await bot.send_message(message.from_user.id, '''Бот распознал тебя, как главного администратора.
            \nЧтобы посмотреть доступные команды - /help''')

        else:
            """Не совпало со СА, проверяем других админов"""
            other_admin_from_db = await sqlite_db.check_if_exists_admin()
            if other_admin_from_db:
                """Если список не пустой"""
                other_admin_list = [int(i[0]) for i in other_admin_from_db]
                if message.from_user.id in other_admin_list:
                    """Если пищущий в этом списке"""
                    await bot.send_message(message.from_user.id,
                                           'Привет! Чтобы посмотреть доступные команды - /help')
                else:
                    """Если пишущего нет в этом списке"""
                    await bot.send_message(message.from_user.id,
                                           '''Привет! Ты не можешь изменять настройки бота. 
                                           \nПопроси главного администратора добавить тебя в список.''')
            else:
                """В списке с ДА никого нет"""
                await bot.send_message(message.from_user.id,
                                       '''Привет! Ты не можешь изменять настройки бота.
                                       \nПопроси главного администратора добавить тебя в список.''')
    else:
        """Если еще не назначен СА"""
        await sqlite_db.add_main_admin(message.from_user.id)
        await bot.send_message(message.from_user.id,
                               '''Привет! Твой id добавлен как главный администратор.
                               \nЧтобы посмотреть доступные команды - /help
                               \nНе забудь добавить id чата, в котором будем работать!''')


async def help(message: types.Message):
    """
    Функция выводит доступные команды СА или ДА. Другим пользователям не выводит
    """
    if message.from_user.id == await sqlite_db.main_id():
        await bot.send_message(message.from_user.id, '''Доступные команды старшего администратора:
        \n/chats - посмотреть список всех чатов, где работает бот.
        \n/add_chat - добавить чат и администратора.
        \n/del_chat - удалить чат. 
        \n/change_admin - изменить администратора в чате''')

    if message.from_user.id in await sqlite_db.other_admins():
        chat_id_from_db = sqlite_db.cur.execute('''SELECT chat 
                                                        FROM chat_admin_time
                                                        WHERE admin == ?''', (message.from_user.id,)).fetchall()
        chats_list = [i[0] for i in chat_id_from_db]
        await bot.send_message(message.from_user.id, f'''Вы управляете чатом/чатами с id {chats_list}''')
        await bot.send_message(message.from_user.id, '''Доступные команды для работы в чате:
        \n/time - изменить время отправки сообщений и включения чата.
        \n/morning - изменить утренние приветственные сообщения. 
        \n/night - изменить ночные приветственные сообщения.''')


async def chats(message: types.Message):
    """
    Функция доступна СА. Посмотреть список всех чатов, в которых сейчас работает бот.
    """
    if message.from_user.id == await sqlite_db.main_id():
        chats_from_db = sqlite_db.cur.execute('''SELECT chat, admin 
                                        FROM chat_admin_time''').fetchall()
        for i in chats_from_db:
            await bot.send_message(message.from_user.id, f'''Чатом с id {i[0]} управляет пользователь с id {i[1]}''')
        await bot.send_message(message.from_user.id, '''/add_chat - добавить чат и администратора.
                            \n/del_chat - удалить чат. 
                            \n/change_admin - изменить администратора в чате''')


class FSMAdmin_chat_admin_add(StatesGroup):
    add_chat = State()
    add_admin = State()


async def add_chat(message: types.Message):
    """
    Функция доступна СА. Добавить чат в БД для работы бота. Бот запрашивает id чата и пользователя,
    который будет управлять этим чатом.
    Проверяет, является ли СА администратором в этом чате, является ли введеный пользователь администратором в этом чате.
    """
    if message.from_user.id == await sqlite_db.main_id():
        await FSMAdmin_chat_admin_add.add_chat.set()
        await message.reply(f'''Введите id чата''')


async def receive_id_chat(message: types.Message, state: FSMContext):
    if message.from_user.id == await sqlite_db.main_id():
        async with state.proxy() as data:
            try:
                int(message.text)
                chat_from_db = await sqlite_db.check_if_exists_chat()
                if chat_from_db and int(message.text) in [int(i[0]) for i in chat_from_db]:
                    await message.reply('''Вы ввели id чата, который уже есть в списке.
                    \nВведите id снова или /cancel, чтобы выйти.''')
                else:
                    if await check_if_admin(user_id=message.from_user.id, chat_id=int(message.text)):
                        if await check_if_admin(user_id=bot.id, chat_id=int(message.text)):
                            data['chat'] = int(message.text)
                            await message.reply('''Введите id пользователя, который будет \
                            контролировать работу бота в этом чате.\
                            Пользователь должен быть администратором в этом чате.''')
                            await FSMAdmin_chat_admin_add.add_admin.set()
                        else:
                            await message.reply('''Бот не добавлен в группу или не является администратором этой группы.
                            \nДабавьте бота, сделайте его администратором, после попробуйте команду снова''')
                            await state.finish()
                            return None
                    else:
                        await message.reply('''Вы не являетесь администратором этой группы.
                        \nВведите корректный id или /cancel''')
            except ValueError as e:
                await message.reply('Введены некорректные данные. Введите id снова или /cancel, чтобы выйти.')
                logging.error(f'Ошибка:{e}')


async def receive_id_admin(message: types.Message, state: FSMContext):
    if message.from_user.id == await sqlite_db.main_id():
        async with state.proxy() as data:
            try:
                int(message.text)
                if await check_if_admin(user_id=int(message.text), chat_id=data['chat']):
                    data['admin'] = int(message.text)
                    await sqlite_db.insert_new_chat(data)
                    await sqlite_db.insert_messages(data['chat'])
                    await message.reply('Чат внесен в БД')
                    main_admin = await sqlite_db.main_id()
                    await other.add_jobs_for_chat(data['chat'], message.from_user.id, 6, 30, 22, 30, main_admin)
                    await state.finish()
                else:
                    await message.reply('''Этот пользователь не является администратором этой группы.
                    \nСделайте его администратором, или выберите другого модератораю Попробуйте команду снова''')
                    await state.finish()
                    return None
            except ValueError as e:
                await message.reply('Введены некорректные данные. Введите id снова или /cancel, чтобы выйти.')
                logging.error(f'Ошибка:{e}')


class FSMAdmin_del_chat(StatesGroup):
    del_chat = State()


async def del_chat(message: types.Message, state: FSMContext):
    """
    Удаление чатов. Доступно СА.
    Проверяет инфу на корректность данных, на наличие этого чата в списке.
    """
    if message.from_user.id == await sqlite_db.main_id():
        chat_from_db = await sqlite_db.check_if_exists_chat()
        if chat_from_db:
            await FSMAdmin_del_chat.del_chat.set()
            await message.reply('Введите id чата без лишних символов для удаления')
        else:
            await message.reply('Бот не работает ни с одним чатом. Удалять нечего')
            await state.finish()
            return None


async def receive_del_chat_id(message: types.Message, state: FSMContext):
    if message.from_user.id == await sqlite_db.main_id():
        async with state.proxy() as data:
            chat_from_db = await sqlite_db.check_if_exists_chat()
            try:
                int(message.text)
                chat_list = [int(i[0]) for i in chat_from_db]
                data['chat_id'] = int(message.text)
                if data['chat_id'] in chat_list:
                    await sqlite_db.del_chat(data['chat_id'])
                    await sqlite_db.delete_all_morning_messages_of_chat(data['chat_id'])
                    await sqlite_db.delete_all_night_messages_of_chat(data['chat_id'])
                    await other.del_job_from_scheduler(data['chat_id'])
                    await sqlite_db.del_permissions_from_db(data['chat_id'])
                    await message.reply('Чат удален')
                    await state.finish()
                else:
                    await message.reply('Такого чата нет в списке. Введите корректный id или /cancel, чтобы выйти')
            except ValueError as e:
                await message.reply('Введены некорректные данные. Введите снова или /cancel')
                logging.error(f'Ошибка:{e}')


class FSMAdmin_change_admin(StatesGroup):
    chat_id = State()
    change_admin = State()


async def change_chat(message: types.Message):
    """
    Доступно СА. Изменяет администратора в уже работающем чате.
    """
    if message.from_user.id == await sqlite_db.main_id():
        await FSMAdmin_change_admin.chat_id.set()
        await message.reply(f'''Введите id чата, в котором хотите изменить администратора''')


async def receive_id_chat_change(message: types.Message, state: FSMContext):
    if message.from_user.id == await sqlite_db.main_id():
        async with state.proxy() as data:
            try:
                int(message.text)
                chat_from_db = await sqlite_db.check_if_exists_chat()
                if chat_from_db and int(message.text) in [int(i[0]) for i in chat_from_db]:
                    data['chat'] = int(message.text)
                    await message.reply('Введите id нового администратора дл этого чата')
                    await FSMAdmin_change_admin.change_admin.set()
                else:
                    await message.reply('''Чата с таким id нет в базе данных. Бот в нем не работает.
                                        \nВведите id снова или /cancel, чтобы выйти.''')
            except ValueError as e:
                await message.reply('Введены некорректные данные. Введите id снова или /cancel, чтобы выйти.')
                logging.error(f'Ошибка:{e}')


async def receive_admin_change(message: types.Message, state: FSMContext):
    if message.from_user.id == await sqlite_db.main_id():
        async with state.proxy() as data:
            try:
                int(message.text)
                if await check_if_admin(user_id=int(message.text), chat_id=data['chat']):
                    data['admin'] = int(message.text)
                    await sqlite_db.update_admin(data)
                    await message.reply('Администратор изменен.')
                    await state.finish()
                else:
                    await message.reply('''Этот пользователь не является администратором этой группы.
                    \nСделайте его администратором, или выберите другого модератора. Попробуйте команду снова''')
                    await state.finish()
                    return None
            except ValueError as e:
                await message.reply('''Введены некорректные данные.\
                                    Введите id администратора снова или /cancel, чтобы выйти.''')
                logging.error(f'Ошибка:{e}')


class FSMAdmin(StatesGroup):
    choose_chat_time = State()
    time_morning = State()
    time_night = State()


async def change_time(message: types.Message, state: FSMContext):
    """
    Изменение времени
    Доступно ДА.
    Сразу утро и вечер вместе.
    ДА, который управляет несколькими чатами, сначала вводит id чата, в котором собирается произвести изменения.
    ДА, который управляет одним чатом, сразу вносит изменения.
    """
    if message.from_user.id in await sqlite_db.other_admins():
        chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
        """Проверяем, сколькоми чатами управляет пользователь"""
        if len(chats_list) == 1:
            async with state.proxy() as data:
                data['chat'] = chats_list[0]
            time_from_db = await sqlite_db.get_info_chat(data['chat'])
            morning = time(time_from_db[2], time_from_db[3])
            night = time(time_from_db[4], time_from_db[5])
            await FSMAdmin.time_morning.set()
            await message.reply(f'''На данный момент в вашем чате установлено время: 
                                \nУтро - {morning}. Вечер - {night}.
                                \nВведи время включения чата. Через двоеточие. Например - 8:15.
                                \n/cancel, чтобы выйти''')
        else:
            await message.reply(f'''Вы управляете чатами с id {chats_list}. Введите номер чата, который хотите изменить
                                \n/cancel, чтобы выйти''')
            await FSMAdmin.choose_chat_time.set()


async def chat_for_change_time(message: types.Message, state: FSMContext):
    """Дополнительный этап, где пользователь, управляющий сразу несколькими группами,
    ввродит чат, который именно хочет изменить"""
    if message.from_user.id in await sqlite_db.other_admins():
        try:
            int(message.text)
            chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
            async with state.proxy() as data:
                if int(message.text) in chats_list:
                    data['chat'] = int(message.text)
                    time_from_db = await sqlite_db.get_info_chat(data['chat'])
                    morning = time(time_from_db[2], time_from_db[3])
                    night = time(time_from_db[4], time_from_db[5])
                    await message.reply(f'''На данный момент в этом чате установлено время: 
                                                    \nУтро - {morning}. Вечер - {night}.''')

                    await message.reply('Введи время включения чата. Через двоеточие. Например - 8:05')
                    await FSMAdmin.time_morning.set()
                else:
                    await message.reply('Чат введен неверно. Введи id снова или /cancel')
        except Exception as e:
            await message.reply('Введены некорректные данные. Введи id снова или /cancel')
            logging.error(f'Ошибка:{e}')


async def cancel_handler(message: types.Message, state: FSMContext):
    """
    функция отмены
    выходит из состония изменения. Вызывается командой /cancel или текстом - отмена
    """
    if message.from_user.id == await sqlite_db.main_id() or message.from_user.id in await sqlite_db.other_admins():
        current_state = await state.get_state()
        if current_state is None:
            return None
        await state.finish()
        await message.reply('Ок')


async def morning_time(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                data['morning_hour'] = int(message.text.split(':')[0])
                data['morning_minute'] = int(message.text.split(':')[1])
                await FSMAdmin.next()
                await message.reply('Введи время выключения чата. Через двоеточие. Например - 22:03')
            except (IndexError, ValueError) as e:
                await message.reply('Время введено неверно. Введи время снова или /cancel')
                logging.error(f'Ошибка:{e}')


async def night_time(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                data['night_hour'] = int(message.text.split(':')[0])
                data['night_minute'] = int(message.text.split(':')[1])
                new_time_morning = time(data['morning_hour'], data['morning_minute'], 0)
                new_time_night = time(data['night_hour'], data['night_minute'], 0)
                if new_time_morning <= new_time_night:
                    await other.check_time(data, message, data['chat'])
                    await sqlite_db.update_time(data)
                    await message.reply('Время изменено')
                    await other.modify(data['chat'], data['morning_hour'], data['morning_minute'], data['night_hour'], data['night_minute'])
                    await state.finish()
                else:
                    await message.reply('Утреннее время должно быть меньше вечернего! Попробуйте команду снова - /time')
                    await state.finish()
            except (IndexError, ValueError, KeyError) as e:
                await message.reply('Время введено неверно. Введите время снова или /cancel, чтобы выйти.')
                logging.error(f'Ошибка:{e}')


class FSMAdmin_mm(StatesGroup):
    choose_chat_morning = State()
    option = State()
    number_del = State()
    morning_message = State()
    number_update = State()
    add = State()


async def option_morning(message: types.Message, state: FSMContext):
    """
    Изменение утренних сообщений
    Доступно ДА
    Возможности: Удалить одно, Изменить одно, Добавить одно, Перезаписать сразу все
    ДА, который управляет несколькими чатами, сначала вводит id чата, в котором собирается произвести изменения.
    ДА, который управляет одним чатом, сразу вносит изменения.
    """
    if message.from_user.id in await sqlite_db.other_admins():
        chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
        """Проверяем, сколькими чатами управляет"""
        if len(chats_list) == 1:
            async with state.proxy() as data:
                chat_id = chats_list[0]
                data['chat'] = chat_id
            await FSMAdmin_mm.option.set()
            await bot.send_message(message.from_user.id, 'Доступные утренние сообщения:')
            info = await sqlite_db.get_messages_morning(data['chat'])
            for i in info:
                await bot.send_message(message.from_user.id, i)
            await message.reply('''Введите команду 
                                \n/del - удалить одно из сообщений. 
                                \n/one - изменить одно из сообщений. 
                                \n/add - добавить новое сообщение. 
                                \n/all - обновить все сообщения сразу.
                                \n/cancel - выйти.''')
        else:
            await message.reply(f'''Вы управляете чатами с id {chats_list}. Введите номер чата, который хотите изменить
                                \n/cancel, чтобы выйти''')
            await FSMAdmin_mm.choose_chat_morning.set()


async def choose_chat_morning(message: types.Message, state: FSMContext):
    """Дополнительный этап, где пользователь, управляющий сразу несколькими группами,
        ввродит чат, который именно хочет изменить"""
    if message.from_user.id in await sqlite_db.other_admins():
        try:
            int(message.text)
            chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
            async with state.proxy() as data:
                if int(message.text) in chats_list:
                    data['chat'] = int(message.text)
                    await bot.send_message(message.from_user.id, 'Доступные утренние сообщения:')
                    info = await sqlite_db.get_messages_morning(data['chat'])
                    for i in info:
                        await bot.send_message(message.from_user.id, i)
                    await message.reply('''Введите команду 
                                                    \n/del - удалить одно из сообщений. 
                                                    \n/one - изменить одно из сообщений. 
                                                    \n/add - добавить новое сообщение. 
                                                    \n/all - обновить все сообщения сразу.
                                                    \n/cancel - выйти.''')
                    await FSMAdmin_mm.option.set()
                else:
                    await message.reply('Чат введен неверно. Введи id снова или /cancel')
        except Exception as e:
            await message.reply('Введены некорректные данные. Введи id снова или /cancel')
            logging.error(f'Ошибка:{e}')


async def change_morning_all(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_mm.morning_message.set()
        await message.reply('''Введи новые утренние сообщения. 
                            \nМежду фразами поставь символ # и отправь за все вместе за один раз. 
                            \nНапример: Доброе утро#Hello#Buenas dias''')


async def receive_morning_all(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                messages = message.text.split('#')
                info_for_db = [[messages.index(i)+1, i] for i in messages]
                await sqlite_db.delete_all_morning_messages_of_chat(data['chat'])
                await sqlite_db.insert_many_morning(info_for_db, data['chat'])
                await message.reply('Сообщения обновлены')
            except (TypeError, ValueError) as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None
            await state.finish()


async def del_morning(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_mm.number_del.set()
        await message.reply('Введите номер сообщения, которое хотите удалить')


async def del_morning_number(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                number = int(message.text)
                index = await sqlite_db.check_number_morning_message(number, data['chat'])
                if index:

                    await sqlite_db.delete_one_morning_messages_of_chat(data['chat'], number)
                    await message.reply('Сообщение удалено.')
                    await state.finish()
                else:
                    await message.reply('''Сообщения с таким индексом нет в БД.\
                    Введи id верно или /cancel, чтобы выйти''')
            except Exception as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None


async def update_morning(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_mm.number_update.set()
        await message.reply('''Введите номер сообщения, которое хотите поменять, решетку, новое сообщение. 
                            \nНапример: 1#Доброе утро''')


async def update_morning_number(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                info_fo_db = message.text.split('#')
                number_user = info_fo_db[0]
                index = await sqlite_db.check_number_morning_message(number_user, data['chat'])
                if index:
                    await sqlite_db.update_one_morning(info_fo_db, data['chat'])
                    await message.reply('Сообщение изменено')
                    await state.finish()
                else:
                    await message.reply('''Сообщения с таким индексом нет в БД.\
                    Введи id верно или /cancel, чтобы выйти''')
            except Exception as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None


async def add_morning(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_mm.add.set()
        await message.reply('Введите сообщение, которое хотите добавить')


async def add_morning_new(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                new_message = message.text
                id = await sqlite_db.last_id_morning(data['chat'])
                await sqlite_db.add_one_morning(id, new_message, data['chat'])
                await message.reply('Сообщение добавлено')
            except (TypeError, ValueError) as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None
            await state.finish()


class FSMAdmin_nm(StatesGroup):
    choose_chat_night = State()
    option = State()
    number_del = State()
    night_message = State()
    number_update = State()
    add = State()


async def option_night(message: types.Message, state: FSMContext):
    """
    Изменение ночных сообщений
    Доступно ДА
    Возможности: Удалить одно, Изменить одно, Добавить одно, Перезаписать сразу все
    ДА, который управляет несколькими чатами, сначала вводит id чата, в котором собирается произвести изменения.
    ДА, который управляет одним чатом, сразу вносит изменения.
    """
    if message.from_user.id in await sqlite_db.other_admins():
        chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
        """Проверяем, сколькими чатами управляет пользователь"""
        if len(chats_list) == 1:
            async with state.proxy() as data:
                data['chat'] = chats_list[0]
            await FSMAdmin_nm.option.set()
            await bot.send_message(message.from_user.id, 'Доступные ночные сообщения:')
            info = await sqlite_db.get_messages_night(data['chat'])
            for i in info:
                await bot.send_message(message.from_user.id, i)
            await message.reply('''Введите команду 
                                \n/del - удалить одно из сообщений. 
                                \n/one - изменить одно из сообщений. 
                                \n/add - добавить новое сообщение. 
                                \n/all - обновить все сообщения сразу.
                                \n/cancel - выйти.''')
        else:
            await message.reply(f'''Вы управляете чатами с id {chats_list}. Введите номер чата, который хотите изменить
                                \n/cancel, чтобы выйти''')
            await FSMAdmin_nm.choose_chat_night.set()


async def choose_chat_night(message: types.Message, state: FSMContext):
    """Дополнительный этап, где пользователь, управляющий сразу несколькими группами,
        ввродит чат, который именно хочет изменить"""
    if message.from_user.id in await sqlite_db.other_admins():
        try:
            int(message.text)
            chats_list = await sqlite_db.get_chats_of_admin_from_db(message.from_user.id)
            async with state.proxy() as data:
                if int(message.text) in chats_list:
                    data['chat'] = int(message.text)
                    await bot.send_message(message.from_user.id, 'Доступные ночные сообщения:')
                    info = await sqlite_db.get_messages_night(data['chat'])
                    for i in info:
                        await bot.send_message(message.from_user.id, i)
                    await message.reply('''Введите команду 
                                                    \n/del - удалить одно из сообщений. 
                                                    \n/one - изменить одно из сообщений. 
                                                    \n/add - добавить новое сообщение. 
                                                    \n/all - обновить все сообщения сразу.
                                                    \n/cancel - выйти.''')
                    await FSMAdmin_nm.option.set()
                else:
                    await message.reply('Чат введен неверно. Введи id снова или /cancel')
        except ValueError as e:
            await message.reply('Введены некорректные данные. Введи id снова или /cancel')
            logging.error(f'Ошибка:{e}')


async def change_night_all(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_nm.night_message.set()
        await message.reply('''Введи новые ночные сообщения. 
                            \nМежду фразами поставь символ # и отправь за все вместе за один раз. 
                            \nНапример: Доброй ночи#CHAO#Buenas noches''')


async def receive_night_all(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                messages = message.text.split('#')
                info_for_db = [[messages.index(i)+1, i] for i in messages]
                await sqlite_db.delete_all_night_messages_of_chat(data['chat'])
                await sqlite_db.insert_many_night(info_for_db, data['chat'])
                await message.reply('Сообщения добавлены')
            except (TypeError, ValueError) as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None
            await state.finish()


async def del_night(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_nm.number_del.set()
        await message.reply('Введите номер сообщения, которое хотите удалить')


async def del_night_number(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                number = int(message.text)
                index = await sqlite_db.check_number_night_message(number, data['chat'])
                if index:
                    await sqlite_db.delete_one_night_messages_of_chat(data['chat'], number)
                    await message.reply('Сообщение удалено.')
                    await state.finish()
                else:
                    await message.reply('''Сообщения с таким индексом нет в БД.\
                    Введи id верно или /cancel, чтобы выйти''')
            except (TypeError, ValueError) as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None


async def update_night(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_nm.number_update.set()
        await message.reply('''Введите номер сообщения, которое хотите поменять, решетку, новое сообщение.
                            \nНапример: 1#Доброй ночи''')


async def update_night_number(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                info_for_db = message.text.split('#')
                number_user = info_for_db[0]
                index = await sqlite_db.check_number_night_message(number_user, data['chat'])
                if index:
                    await sqlite_db.update_one_night(info_for_db, data['chat'])
                    await message.reply('Сообщение изменено')
                    await state.finish()
                else:
                    await message.reply('''Сообщения с таким индексом нет в БД.\
                                    Введи id верно или /cancel, чтобы выйти''')
            except Exception as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None


async def add_night(message: types.Message):
    if message.from_user.id in await sqlite_db.other_admins():
        await FSMAdmin_nm.add.set()
        await message.reply('Введите сообщение, которое хотите добавить')


async def add_night_new(message: types.Message, state: FSMContext):
    if message.from_user.id in await sqlite_db.other_admins():
        async with state.proxy() as data:
            try:
                new_message = message.text
                id = await sqlite_db.last_id_night(data['chat'])
                await sqlite_db.add_one_night(id, new_message, data['chat'])
                await message.reply('Сообщение добавлено')
            except (TypeError, ValueError) as e:
                await message.reply('Что-то пошло не так. Попробуй команду еще раз и введи данные правильно!')
                logging.error(f'Ошибка:{e}')
                await state.finish()
                return None
            await state.finish()


async def bot_is_member(message: types.Message):
    """
    Отслеживаем добавление бота в чат, чтобы получать id чата от самого бота, не добавляя сторонних ботов
    """
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id

    for chat_member in message.new_chat_members:
        if chat_member.id == bot_id:
            chat_id = message.chat.id
            chat_title = message.chat.title
            main_id = await sqlite_db.main_id()
            if main_id:
                await bot.send_message(main_id, f'''Бот добавлен в чат {chat_title} с id {chat_id}.
                                                \nНе забудьте сделать бота администратором в данном чате\
                                                 и добавить сам чат в бота! /add_chat''')


async def bot_is_not_member(message: types.Message):
    """
    Отслеживаем удаление бота из чата, автоматически удаляем все данные по этому чату из БД.
    """
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    chat_id = message.chat.id

    if message.left_chat_member.id == bot_id:
        info = await sqlite_db.check_if_exists_chat()
        if info and chat_id in [int(i[0]) for i in info]:
            chat_title = message.chat.title
            # удаляем из бд чатов
            await sqlite_db.del_chat(chat_id)
            # удаляем из сообщений
            await sqlite_db.delete_all_morning_messages_of_chat(chat_id)
            await sqlite_db.delete_all_night_messages_of_chat(chat_id)
            # удаляем из шедулера
            await other.del_job_from_scheduler(chat_id)

            main_id = await sqlite_db.main_id()
            if main_id:
                await bot.send_message(main_id, f'''Бот удален из чата {chat_title} с id {chat_id}.
                                                \nБот не будет работать в этом чате''')


async def migrate_to_chat(message: types.Message):
    """
    Отслеживаем миграцию чата в другой статус и изменение его id.
    Старый и новый id находятся по отдельности.
    Поэтому обмен происходит поэтапно с созданием вспомогательной таблицы.
    Здесь находим новый id, создаем таблицу БД для последующего обмена и вносим новый id.
    """
    new_chat_id = message.migrate_to_chat_id
    name = message.chat.title
    await sqlite_db.table_for_exchange(new_chat_id, name)


async def migrate_from_chat(message: types.Message):
    """
    Отслеживаем миграцию чата в другой статус и изменение его id
    Здесь находим старый id. Вносим в БД.
    Если бот работал в этом чате, вызываем функцию, производящую изменения.
    """
    old_chat_id = message.migrate_from_chat_id
    info_chat_from_db = sqlite_db.cur.execute('''SELECT * 
                                                    FROM chat_admin_time 
                                                    WHERE chat == ?''', (old_chat_id,)).fetchone()
    if info_chat_from_db is None:
        """если бот и не работал в этом чате, просто состоял и словил апдейт"""
        sqlite_db.cur.execute('DELETE FROM exchange')
        sqlite_db.base.commit()
    else:
        sqlite_db.cur.execute('''UPDATE exchange 
                                SET old == ? 
                                WHERE id = ?''', (old_chat_id, 1))
        sqlite_db.base.commit()

        await change_after_migration()


async def change_after_migration():

    """Обмен во всей БД старого id на новый, меняем шедулере и удаляем вспомогательную таблицу."""

    info_for_exchange = sqlite_db.cur.execute('''SELECT * 
                                                FROM exchange''').fetchone()
    old_id = info_for_exchange[0]
    new_id = info_for_exchange[1]
    name = info_for_exchange[3]
    main_id = await sqlite_db.main_id()

    try:
        info_chat_from_db = await sqlite_db.get_info_chat(old_id)

        await other.add_jobs_for_chat(new_id, info_chat_from_db[1], info_chat_from_db[2],
                                      info_chat_from_db[3], info_chat_from_db[4], info_chat_from_db[5], main_id)
        await other.del_job_from_scheduler(old_id)
        await sqlite_db.update_chat(new_id, old_id)
        sqlite_db.cur.execute('DELETE FROM exchange')
        sqlite_db.base.commit()
        await bot.send_message(main_id, f'''Чат {name} поменял id. Старое id: {old_id}. Новое id: {new_id}.
                                        \nБот произвел изменения в базе данных, но скорее всего, \
                                        потерял свои администраторские права в этом чате.\
                                        Пожалуйста, проверьте, является ли бот до сих пор админом, \
                                        для продолжения его корректной работы.''')
    except Exception as e:
        logging.error(f'Ошибка: {e}')
        await bot.send_message(main_id, f'''Чат {name} поменял id, но что-то пошло не так и база данных не обновилась автоматически.
                                    \nПожалуйста, удалите самостоятельно из бота старый чат с id {old_id}.
                                    \nИ добавьте новый id {new_id} для успешного продолжения работы бота.''')


def register_handlers_admin(dp):
    """Регистрируем хэндлеры"""
    # общие команды
    dp.register_message_handler(start, commands='start')
    dp.register_message_handler(help, commands='help')
    dp.register_message_handler(cancel_handler, state="*", commands='cancel')
    dp.register_message_handler(cancel_handler, Text(equals='отмена', ignore_case=True), state="*")
    # команды СА/посмотреть чаты, где работает бот
    dp.register_message_handler(chats, commands='chats')
    # команды СА/добавить чат
    dp.register_message_handler(add_chat, commands='add_chat', state=None)
    dp.register_message_handler(receive_id_chat, state=FSMAdmin_chat_admin_add.add_chat)
    dp.register_message_handler(receive_id_admin, state=FSMAdmin_chat_admin_add.add_admin)
    # команды СА/удалить чат
    dp.register_message_handler(del_chat, commands='del_chat')
    dp.register_message_handler(receive_del_chat_id, state=FSMAdmin_del_chat.del_chat)
    # команды СА/изменить администратора в чате
    dp.register_message_handler(change_chat, commands='change_admin', state=None)
    dp.register_message_handler(receive_id_chat_change, state=FSMAdmin_change_admin.chat_id)
    dp.register_message_handler(receive_admin_change, state=FSMAdmin_change_admin.change_admin)
    # время
    dp.register_message_handler(change_time, commands='time', state=None)
    dp.register_message_handler(chat_for_change_time, state=FSMAdmin.choose_chat_time)
    dp.register_message_handler(morning_time, state=FSMAdmin.time_morning)
    dp.register_message_handler(night_time, state=FSMAdmin.time_night)
    # сообщения утренние
    dp.register_message_handler(option_morning, commands='morning', state=None)
    dp.register_message_handler(choose_chat_morning, state=FSMAdmin_mm.choose_chat_morning)
    dp.register_message_handler(change_morning_all, commands='all', state=FSMAdmin_mm.option)
    dp.register_message_handler(receive_morning_all, state=FSMAdmin_mm.morning_message)
    dp.register_message_handler(del_morning, commands='del', state=FSMAdmin_mm.option)
    dp.register_message_handler(del_morning_number, state=FSMAdmin_mm.number_del)
    dp.register_message_handler(update_morning, commands='one', state=FSMAdmin_mm.option)
    dp.register_message_handler(update_morning_number, state=FSMAdmin_mm.number_update)
    dp.register_message_handler(add_morning, commands='add', state=FSMAdmin_mm.option)
    dp.register_message_handler(add_morning_new, state=FSMAdmin_mm.add)
    # сообщения ночные
    dp.register_message_handler(option_night, commands='night', state=None)
    dp.register_message_handler(choose_chat_night, state=FSMAdmin_nm.choose_chat_night)
    dp.register_message_handler(change_night_all, commands='all', state=FSMAdmin_nm.option)
    dp.register_message_handler(receive_night_all, state=FSMAdmin_nm.night_message)
    dp.register_message_handler(del_night, commands='del', state=FSMAdmin_nm.option)
    dp.register_message_handler(del_night_number, state=FSMAdmin_nm.number_del)
    dp.register_message_handler(update_night, commands='one', state=FSMAdmin_nm.option)
    dp.register_message_handler(update_night_number, state=FSMAdmin_nm.number_update)
    dp.register_message_handler(add_night, commands='add', state=FSMAdmin_nm.option)
    dp.register_message_handler(add_night_new, state=FSMAdmin_nm.add)
    # добавление и удаление бота в чат
    dp.register_message_handler(bot_is_member, content_types=['new_chat_members'])
    dp.register_message_handler(bot_is_not_member, content_types=['left_chat_member'])
    # миграция группы в супергруппу и изменение id
    dp.register_message_handler(migrate_from_chat, content_types=['migrate_from_chat_id'])
    dp.register_message_handler(migrate_to_chat, content_types=['migrate_to_chat_id'])
