from random import randint
from telegram.ext import Updater, CommandHandler

def start(bot, update):
    update.message.reply_text('Hello World!')

def hello(bot, update):
    update.message.reply_text('Hello {}'.format(\
        update.message.from_user.first_name))
    
def dice(bot, update):
    message = update.message.text[6:]
    parsed = message.split('d')
    if len(parsed[0]) > 0:
        num = int(parsed[0])
    else:
        num = 1
    val = int(parsed[1])
    res = [randint(1, val) for i in range(num)]
    update.message.reply_text('{} rolled: {}, sum: {}'.format(update.message.from_user.username, res, sum(res)))

updater = Updater('379931845:AAH-3mrlthdNokUKRx21PZ6rmIiYZZGp5vY')

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(CommandHandler('dice', dice))

updater.start_polling()
updater.idle()
