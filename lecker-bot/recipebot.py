# Simple Bot to reply to Telegram messages to recommend food recipes
# According to users' diet.

from telegram import (ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardHide)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
from pinterest_api_client import Pinterest
import logging
import requests
import time
import json

from random import randint

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

preferences = {}
DIET, MEAL, NEXT = range(3)
pinterest = Pinterest()
limit_of_recipes = 3
sent_recipes = []

# Load conversations texts.
with open('conversations.json') as data_file:
    conversations = json.load(data_file)



def start(bot, update):
 
    reply_keyboard = [ ['Normal'], ['Glutenfree'],['Vegetarian'], ['Vegan']]
    user = update.message.from_user

    bot.sendMessage(update.message.chat_id,
                    text=conversations['start'][randint(0,2)] % user.first_name,
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
    reply_keyboard = [['Yes', 'One more !']]
    user = update.message.from_user
    logger.info("Meal that %s wants is %s" % (user.first_name, update.message.text))
    preferences['meal'] = update.message.text
    bot.sendMessage(update.message.chat_id,
                    text=conversations['think'][randint(0,2)] % user.first_name)

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

        bot.sendMessage(update.message.chat_id,
                        text=conversations['enjoy'][randint(0,2)] % user.first_name,
                        reply_markup=ReplyKeyboardHide())

        bot.sendMessage(update.message.chat_id,
                        conversations['gifs'][(randint(0,2))])

        return ConversationHandler.END

    if  len(sent_recipes) > limit_of_recipes-1:

        bot.sendMessage(update.message.chat_id,
                        conversations['notMore'][(randint(0,2))])
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
    query = str(preferences['diet'] + " " + preferences['meal'] + " Food Recipe")
    recipes = pinterest.search(query)
    return recipes[randint(0, len(recipes) - 1)]['link']


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

