from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv, find_dotenv

import logging
import os

# !!!!!!!!!!
# import telebot
# checkbot = telebot.TeleBot('5396061392:AAFey3qztihNxidd8btHlfye24p4XmMffV8')

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()

load_dotenv(find_dotenv())
bot = Bot(os.getenv('TOKEN'))
dp = Dispatcher(bot, storage=storage)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
