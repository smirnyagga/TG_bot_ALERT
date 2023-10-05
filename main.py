from aiogram.utils import executor

from datetime import datetime
import pytz

from create_bot import dp, logging
from data_base import sqlite_db
from handlers import other, admin


async def on_startup(_):
    tz_moscow = pytz.timezone("Europe/Moscow")
    logging.info(datetime.now(tz_moscow))
    await sqlite_db.sql_start()
    await other.run_scheduler()


admin.register_handlers_admin(dp)


executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
