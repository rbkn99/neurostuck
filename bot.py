import logging
from subprocess import Popen, PIPE, STDOUT

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

network_process = Popen(['python3',
                         'network/generate_transformers.py',
                         '--model_type=gpt2',
                         '--model_name_or_path=network/comment_model',
                         '--k=5', '--p=0.95', '--length=350'],
                        stdout=PIPE, stdin=PIPE, stderr=STDOUT)

CHOOSE_GENERATE_OPTION, CREATE_PAIRING, SECOND_CHARACTER, GENERATE_BY_TEXT, GENERATE = range(5)

generation_options = {
    CREATE_PAIRING: 'Создать пейринг',
    GENERATE_BY_TEXT: 'Продолжить по началу',
    GENERATE: 'Полный рандом'
}

characters = ["Джон Эгберт",
              "Роуз Лалонд",
              "Дэйв Страйдер",
              "Джейд Харли",
              "Каркат Вантас",
              "Непета Лейон",
              "Вриска Серкет",
              "Соллукс Каптор",
              "Джейк Инглиш",
              "Джейн Крокер",
              "Дирк Страйдер",
              "Рокси Лалонд"]

cols = 3
characters_keyboard = [[characters[j] for j in range(i, i + cols)]
                       for i in range(0, len(characters), cols)]


def start(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [[opt] for opt in generation_options.values()]
    context.user_data.clear()
    update.message.reply_text(
        'Привет! Я могу генерировать фанфики по Хоумстаку. Начнём??\n'
        'Пришли /cancel если захочешь отменить текущую генерацию.',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSE_GENERATE_OPTION


def choose_gen_option(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    response = update.message.text
    logger.info("User %s chose \"%s\" option", user.first_name, response)
    if response == generation_options[CREATE_PAIRING]:
        update.message.reply_text(
            'Отлично! Теперь выбери первого персонажа или напиши его имя.',
            reply_markup=ReplyKeyboardMarkup(characters_keyboard, one_time_keyboard=True)
        )
        return CREATE_PAIRING
    if response == generation_options[GENERATE_BY_TEXT]:
        update.message.reply_text(
            'Хорошо! Отправь текст, а я попытаюсь его продолжить.'
        )
        return GENERATE_BY_TEXT
    if response == generation_options[GENERATE]:
        return generate(update, context)


def choose_first_pairing(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    first_character = update.message.text
    context.user_data['first_character'] = first_character
    logger.info("User %s chose %s as the first pairing character.", user.first_name, first_character)
    update.message.reply_text(
        'А теперь выбери второго персонажа, либо отправь /skip, '
        'если хочешь пропустить этот шаг.',
        reply_markup=ReplyKeyboardMarkup(characters_keyboard, one_time_keyboard=True)
    )
    return SECOND_CHARACTER


def choose_second_pairing(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    second_character = update.message.text
    context.user_data['second_character'] = second_character
    logger.info("User %s chose %s as the second pairing character.", user.first_name, second_character)
    pairing_text = context.user_data['first_character']
    if second_character:
        pairing_text += '/' + second_character
    update.message.reply_text(
        'Вы выбрали пейринг *{}/{}*. Запускаю генерацию!'.format(context.user_data['first_character'],
                                                                 second_character),
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN)
    return generate(update, context)


def skip_second_pairing(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s skipped second character choice.", user.first_name)
    update.message.reply_text(
        'Вы выбрали пейринг *{}*. Запускаю генерацию!'.format(context.user_data['first_character']),
        reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN
    )
    return generate(update, context)


def generate_by_text(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    text = update.message.text
    context.user_data['text_beginning'] = text
    logger.info("User %s send \"%s\" as the text beginning.", user.first_name, text)
    update.message.reply_text('Запускаю генерацию!', reply_markup=ReplyKeyboardRemove())
    return generate(update, context)


def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Текущая генерация отменена.', reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


def help_info(update: Update, context: CallbackContext):
    help_text = '''Доступные команды:
/start - Выбрать параметры генерации
/cancel - Отменить текущий выбор параметров'''
    update.message.reply_text(help_text, reply_markup=ReplyKeyboardRemove())


def generate(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Фанфик генерируется, это займет немного времени...', reply_markup=ReplyKeyboardRemove()
    )
    network_input = ''
    if 'first_character' in context.user_data:
        network_input += context.user_data['first_character']
    if 'second_character' in context.user_data:
        network_input += ' ' + context.user_data['second_character']
    if 'text_beginning' in context.user_data:
        network_input += ' ' + context.user_data['text_beginning']
    if len(network_input) == 0:
        network_input = '.'
    network_stdout = network_process.communicate(input=str.encode(network_input))[0]
    print(network_stdout)
    update.message.reply_text(network_stdout.decode('utf-8'))
    return ConversationHandler.END


def main() -> None:
    token = open('tg_bot_token.txt').read()
    updater = Updater(token)

    dispatcher = updater.dispatcher
    default_filter = (Filters.text & ~Filters.command)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_GENERATE_OPTION: [MessageHandler(
                Filters.regex('^({})$'.format('|'.join(generation_options.values()))),
                choose_gen_option)],
            CREATE_PAIRING: [MessageHandler(default_filter, choose_first_pairing)],
            SECOND_CHARACTER: [
                MessageHandler(default_filter, choose_second_pairing),
                CommandHandler('skip', skip_second_pairing)],
            GENERATE_BY_TEXT: [MessageHandler(default_filter, generate_by_text)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('help', help_info))
    dispatcher.add_handler(MessageHandler(default_filter, help_info))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
