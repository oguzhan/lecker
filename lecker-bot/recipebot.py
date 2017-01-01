#!/usr/bin/env python
# encoding=utf8
# Simple Bot to reply to Telegram messages to recommend food recipes
# According to users' diet.

from telegram import (ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardHide)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
from pinterest_api_client import Pinterest
import csv
import logging
import requests
import time
import json
import random
from emoji import emojize
from random import randint

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Definition of each steps.
NEED, DIET, MEAL, NEXT = range(4)

pinterest = Pinterest()
preferences = {}
stats = {}
limit_of_recipes = 3
sent_recipes = []

# Load conversations texts.
with open('conversations.json') as data_file:
    conversations = json.load(data_file)


def start(bot, update):

    reply_keyboard = [ ['Recipes'], ['Inspirations']] 
    user = update.message.from_user
    bot.sendMessage(update.message.chat_id,
                    text="Hi %s! Are you looking for a specific recipe or some inspiration ?" % user.first_name,
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return NEED

def need(bot, update):
    reply_markup = ReplyKeyboardHide()
    user = update.message.from_user
    if update.message.text == 'Recipes':
        bot.sendMessage(update.message.chat_id,
                        text="What'd you like to cook my dear %s ? (i.e Glutenfree Pizza)" % user.first_name, use_aliases=True)
        preferences['diet'] = ''
        return MEAL
    else:
        reply_keyboard = [ ['Normal'], ['Glutenfree'],['Vegetarian'], ['Vegan']]
        bot.sendMessage(update.message.chat_id,
                        text=emojize(conversations['start'][randint(0,2)] % user.first_name, use_aliases=True),
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return DIET


def diet(bot, update):
    user = update.message.from_user
    logger.info("Diet of %s: %s" % (user.first_name, update.message.text))
    preferences['diet'] = update.message.text

    if update.message.text == 'Normal':
        preferences['diet'] = ''

    bot.sendMessage(update.message.chat_id,
                    text=conversations['diet'][randint(0,2)]  % user.first_name)

    return MEAL


def skip_diet(bot, update):
    user = update.message.from_user
    logger.info("User %s did not specify diet." % user.first_name)
    bot.sendMessage(update.message.chat_id, text='So I assume all is fine for you !')
    return MEAL


def meal(bot, update):
    reply_markup = ReplyKeyboardHide()
    reply_keyboard = [['Yes', 'One more !']]
    user = update.message.from_user
    logger.info("Meal that %s wants is %s" % (user.first_name, update.message.text))
    preferences['meal'] = update.message.text
    bot.sendMessage(update.message.chat_id,
                    text=conversations['think'][randint(0,2)] % user.first_name,
                    reply_markup=reply_markup)

    # Retrieve recipe from Pinterest.
    try:
        recipe = get_recipe(preferences)
    except Exception, e:
        bot.sendMessage(update.message.chat_id,
                        text=conversations['problem'][randint(0,2)])
        return ConversationHandler.END

    bot.sendMessage(update.message.chat_id, text=recipe)
    sent_recipes.append(recipe)

    time.sleep(1)
    bot.sendMessage(update.message.chat_id, text='Did you like this or one more ?',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return NEXT


def skip_meal(bot, update):
    user = update.message.from_user
    logger.info("User %s didn't specify a meal" % user.first_name)
    bot.sendMessage(update.message.chat_id, text='Then I will have to decide for you !')

    return NEXT


def next_recipe(bot, update):
    user = update.message.from_user
    reply_keyboard = [['Yes', 'One more !']]

    if update.message.text == 'Yes':
        reply_markup = ReplyKeyboardHide()
        bot.sendMessage(update.message.chat_id,
                        text=conversations['enjoy'][randint(0,2)] % user.first_name,
                        reply_markup=reply_markup)

        bot.sendMessage(update.message.chat_id,
                        text='To start the conversation again, simply click on /start.')
        log_to_csv(update.message.chat_id, user, sent_recipes[0], preferences)
        gif = str(conversations['gifs'][(randint(0,2))])
        bot.sendDocument(chat_id=update.message.chat_id, document=gif)


        return ConversationHandler.END


    if len(sent_recipes) > limit_of_recipes-1:
        reply_markup = ReplyKeyboardHide()
        bot.sendMessage(update.message.chat_id,
                        conversations['notMore'][(randint(0,2))], reply_markup=reply_markup)
        del sent_recipes[:]
        return ConversationHandler.END


    # Code duplication here, change this!
    try:
        recipe = get_recipe(preferences)
    except Exception, e:
        bot.sendMessage(update.message.chat_id,
                        text=conversations['problem'][randint(0,2)])
        return ConversationHandler.END

    bot.sendMessage(update.message.chat_id, text=conversations['excuse'][randint(0,2)])
    bot.sendMessage(update.message.chat_id, text=recipe)
    sent_recipes.append(recipe)


    time.sleep(2)
    bot.sendMessage(update.message.chat_id, text=conversations['yesNo'][randint(0,2)],
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return NEXT


def get_recipe(preferences):
    query = str(preferences['diet'] + " " + preferences['meal'] + " Recipe")
    recipes = pinterest.search(query)
    recipe = random.choice(recipes)['link']
    return recipe

def log_to_csv(chat_id, user, sent_recipe, preferences):
    log_dict = {'id': chat_id, 'user': user.first_name,
                'meal': preferences['meal'], 'diet': preferences['diet'],
                'recipe': sent_recipe}

    with open('logs.csv', 'w') as csv_logger:
        fieldnames = ['id', 'user', 'meal', 'diet', 'recipe']
        writer = csv.DictWriter(csv_logger, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(log_dict)


def cancel(bot, update):
    user = update.message.from_user
    logger.info("User %s canceled the conversation." % user.first_name)
    bot.sendMessage(update.message.chat_id,
                    text='Bye %s! Let me know while if you fancy anything!' % user.first_name)

    return ConversationHandler.END


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("XXXX")

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states = {
            NEED : [RegexHandler('^(Recipes|Inspirations)', need)],
            DIET : [RegexHandler('^(Glutenfree|Vegan|Vegetarian|Normal)', diet), CommandHandler('skip', skip_diet)],
            MEAL : [MessageHandler([Filters.text], meal), CommandHandler('skip', skip_meal)],
            NEXT : [RegexHandler('^(Yes|One more !)', next_recipe)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conversation_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()

