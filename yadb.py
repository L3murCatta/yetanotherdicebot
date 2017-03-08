from random import randint
from telegram.ext import Updater, CommandHandler
digits = {0,1,2,3,4,5,6,7,8,9}

def nextNonDigit(msg, i):
    for j in range(i+1, len(msg)):
        if msg[j] not in digits:
            return c
    else:
        return -1

def dice(bot, update):
    message = update.message.text[6:]
    d = message.find('d')
    plus = message.find('+')
    minus = message.find('-')
    excl = message.find('!')
    if excl > -1:
        message = message[:excl]+message[excl+1:]
        excl = True
    else:
        excl = False
    if d == 0:
        num = 1
    else:
        num = int(message[:d])
    sign = max(plus, minus)
    if sign == -1:
        val = message[d+1:]
        mod = 0
    else:
        val = message[d+1:sign]
        mod = message[sign+1:]
        if message[sign] == '-':
            mod = '-' + mod
    res = [randint(1, int(val)) for i in range(num)]
    if excl:
        resp = '{} rolled: {}'.format(update.message.from_user.username, res)
        temp = list(filter(lambda x : x == int(val), res))
        while len(temp) > 0:
            temp = [randint(1, int(val)) for i in temp]
            res.extend(temp)
            resp += '\nrerolls: {}'.format(temp)
            temp = list(filter(lambda x : x == int(val), temp))
        resp += '\ntotal: {}'.format(sum(res))
        update.message.reply_text(resp)
    else:
        update.message.reply_text('{} rolled: {}, total: {}'.format(update.message.from_user.username, res, sum(res)+int(mod)))

updater = Updater('379931845:AAH-3mrlthdNokUKRx21PZ6rmIiYZZGp5vY')

updater.dispatcher.add_handler(CommandHandler('dice', dice))

updater.start_polling()
updater.idle()
