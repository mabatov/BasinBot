import sqlite3
import datetime
import telebot
from telebot import types
from config import CONFIG_VARS

bot = telebot.TeleBot(CONFIG_VARS.token_test)
conn = sqlite3.connect('db/BasinBot.db', check_same_thread=False)
cursor = conn.cursor()


def db_insert_user(user_id: int, username: str, user_firstname: str, user_lastname: str):
    cursor.execute('INSERT INTO user (user_id, username, user_firstname, user_lastname) VALUES (?, ?, ?, ?)',
                   (user_id, username, user_firstname, user_lastname))
    conn.commit()


def db_check_user(user_id: int):
    cursor.execute('select username from user where user_id =?', (user_id,))
    usr = cursor.fetchone()
    if usr is not None:
        return usr[0]
    else:
        return usr


def db_startBooking(user_id: int, username: str, user_firstname: str, user_lastname: str):
    cursor.execute('UPDATE user set isBooked = TRUE where user_id = ?', (user_id,))
    cursor.execute('INSERT INTO booking (user_id, startTime) VALUES (?, ?)', (user_id, datetime.datetime.now()))
    conn.commit()


def db_stopBooking(user_id: int, username: str, user_firstname: str, user_lastname: str):
    cursor.execute('UPDATE user set isBooked = FALSE where user_id = ?', (user_id,))
    cursor.execute('UPDATE booking set stopTime = ? where user_id = ? AND startTime is not NULL AND stopTime is NULL',
                   (datetime.datetime.now(), user_id))
    conn.commit()


def db_checkBooking():
    cursor.execute('select username from user where isBooked = 1')
    chkBooking = cursor.fetchone()
    return chkBooking


def db_selectAllUsers():
    cursor.execute('select * from user')
    chkBooking = cursor.fetchall()
    return chkBooking


def db_checkLastWasher():
    cursor.execute('select username from user where user_id = (select user_id from booking order by stopTime desc)')
    result = str(cursor.fetchone())[2:-3]
    return result

def db_stats():
    cursor.execute('select ROW_NUMBER() OVER(order by sum(minutes) desc) place, user_firstname, sum(minutes), count(1) numOfWashings from V_BOOKING group by username')
    return cursor.fetchall()

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    user_firstname = message.from_user.first_name
    user_lastname = message.from_user.last_name

    regState = db_check_user(user_id=user_id)
    if regState is None: regState = 'not registered'

    print(str(datetime.datetime.now()) + '[INFO] ' + 'The result of db_check_user: ' + str(regState))
    if regState is not None:
        print(str(datetime.datetime.now()) + '[INFO] ' + 'Пользователь ' + str(regState) + ' уже зарегистрирован.')
        bot.send_message(message.from_user.id, 'Пользователь ' + str(username) + ' уже зарегистрирован.')
    else:
        db_insert_user(user_id=user_id, username=username, user_firstname=user_firstname, user_lastname=user_lastname)
        bot.send_message(message.chat.id, 'Добро пожаловать, ' + message.from_user.first_name + '!')
        bot.send_message(message.from_user.id, 'Пользователь успешно зарегистрирован!')
        print(str(datetime.datetime.now()) + '[INFO] ' + 'Пользователь ' + str(username) + ' успешно зарегистрирован.')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Заступил на дежурство!')
    item2 = types.KeyboardButton('Тазик свободен!')
    item3 = types.KeyboardButton('У кого тазик?')
    markup.add(item1, item2, item3)
    bot.send_message(message.chat.id, 'Выбери нужный вариант:', reply_markup=markup)


@bot.message_handler(commands=['stats'])
def statistics_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    user_firstname = message.from_user.first_name
    user_lastname = message.from_user.last_name

    print(str(datetime.datetime.now()) + '[INFO] ' + username + ' запросил стастистику')
    print(db_stats())

    result = 'Статистика:\n'
    for i in db_stats():
        if (i[0]==1): result += '🥇 '
        elif (i[0]==2): result += '🥈 '
        elif (i[0]==3): result += '🥉 '
        result += 'Пользователь: ' + str(i[1]) + ', стирок: ' + str(i[3]) + ' (' + str(i[2]) + ' мин)\n'

    print(result)
    bot.send_message(message.chat.id, result)


@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    user_id = message.from_user.id
    username = message.from_user.username
    user_firstname = message.from_user.first_name
    user_lastname = message.from_user.last_name

    if message.text == 'Заступил на дежурство!':
        if db_checkBooking() is not None:
            bot.send_message(message.chat.id, '⛔ @' + str(db_checkBooking())[2:-3] + ' уже стирает')
            print(str(datetime.datetime.now()) + '[INFO] ' + username + ' пытался захватить тазик.')

        else:
            db_startBooking(user_id=user_id, username=username, user_firstname=user_firstname,
                            user_lastname=user_lastname)
            print(str(datetime.datetime.now()) + '[INFO] ' + username + ' приступил к стирке.')

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('Тазик свободен!')
            item3 = types.KeyboardButton('У кого тазик?')
            markup.add(item1, item3)
            bot.send_message(message.chat.id, '🧺 Вы приступили к стирке.', reply_markup=markup)

    elif message.text == 'Тазик свободен!':
        if db_checkBooking() is not None and (str(db_checkBooking())[2:-3] != username):
            print(str(datetime.datetime.now()) + '[INFO] ' + str(db_checkBooking())[2:-3])
            print(str(datetime.datetime.now()) + '[INFO] ' + user_firstname)
            bot.send_message(message.chat.id, '⛔ Не удалось. Тазик находится в руках @' + str(db_checkBooking())[2:-3])
        elif db_checkBooking() is None:
            bot.send_message(message.chat.id,
                             '⛔ Не удалось. Тазик не был занят. Последний раз стирался @' + db_checkLastWasher())

        else:
            db_stopBooking(user_id=user_id, username=username, user_firstname=user_firstname,
                           user_lastname=user_lastname)
            print(str(datetime.datetime.now()) + '[INFO] ' + str(username) + ' освободил тазик.')

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            item1 = types.KeyboardButton('Заступил на дежурство!')
            item3 = types.KeyboardButton('У кого тазик?')
            markup.add(item1, item3)
            bot.send_message(message.chat.id, '🆓 Вы освободили тазик.', reply_markup=markup)

    elif message.text == 'У кого тазик?':
        print(str(datetime.datetime.now()) + '[INFO] ' + username + ' запросил юзера с тазом.')

        if db_checkBooking() is not None:
            bot.send_message(message.chat.id, '🔴 Тазик сейчас у @' + str(db_checkBooking())[2:-3])
        else:
            bot.send_message(message.chat.id,
                             '🟢 Тазик сейчас свободен! Последний пользовался @' + db_checkLastWasher())

        result = 'Статистика:\n'
        for i in db_stats():
            if (i[0] == 1):
                result += '🥇 '
            elif (i[0] == 2):
                result += '🥈 '
            elif (i[0] == 3):
                result += '🥉 '
            result += 'Пользователь: ' + str(i[1]) + ', стирок: ' + str(i[3]) + ' (' + str(i[2]) + ' мин)\n'

        print(result)
        bot.send_message(message.chat.id, result)


bot.infinity_polling()
