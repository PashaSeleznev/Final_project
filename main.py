import telebot
from telebot import types
import emoji
import random
import emoji
from PIL import Image

class random_field:
    def __init__(self):
        # Создание пустого поля боя
        self.empty_square = emoji.emojize(':black_square_button:')
        self.filled_square = emoji.emojize(':black_large_square:')
        self.field_1 = [[self.empty_square for _ in range(-1, 11)] for _ in range(-1, 11)]
        self.field = [[self.empty_square for _ in range(10)] for _ in range(10)]

        # Список кораблей с их размерами и количеством
        self.ships = {'Авианосец': 1,
                      'Линкор': 1,
                      'Крейсер': 1,
                      'Эсминец': 3,
                      'Катер': 4}

        # Размеры кораблей
        self.ship_sizes = {'Авианосец': 4,
                           'Линкор': 3,
                           'Крейсер': 3,
                           'Эсминец': 2,
                           'Катер': 1}

    # Функция для проверки доступности ячеек для размещения корабля
    def check_valid_position(self, field, row, col, size, direction):
        if direction == 'вертикальное':
            for i in range(size):
                if row + i >= len(field) \
                        or self.field_1[row + i][col] != self.empty_square or self.field_1[row + i - 1][col] != self.empty_square or self.field_1[row + i + 1][col] != self.empty_square \
                        or self.field_1[row + i][col+ 1] != self.empty_square or self.field_1[row + i - 1][col + 1] != self.empty_square or self.field_1[row + i + 1][col + 1] != self.empty_square\
                        or self.field_1[row + i + 1][col - 1] != self.empty_square or self.field_1[row + i - 1][col - 1] != self.empty_square\
                        or self.field_1[row + i][col - 1] != self.empty_square:
                    return False
        elif direction == 'горизонтальное':
            for i in range(size):
                if col + i >= len(field) or self.field[row][col + i] != self.empty_square or self.field_1[row][col + i -1] != self.empty_square \
                        or self.field_1[row][col + i + 1] != self.empty_square or self.field_1[row + 1][col+i] != self.empty_square \
                        or self.field_1[row + 1][col+i-1] != self.empty_square or self.field_1[row + 1][col+i+1] != self.empty_square \
                        or self.field_1[row - 1][col + i] != self.empty_square or self.field_1[row - 1][col + i + 1] != self.empty_square \
                        or self.field_1[row - 1][col + i - 1] != self.empty_square:
                    return False
        return True

    # Функция для размещения корабля на поле
    def place_ship(self, field, row, col, size, direction):
        if direction == 'вертикальное':
            for i in range(size):
                self.field[row + i][col] = self.filled_square
                self.field_1[row + i][col] = self.filled_square
        elif direction == 'горизонтальное':
            for i in range(size):
                self.field[row][col + i] = self.filled_square
                self.field_1[row][col + i] = self.filled_square
        return self.field

    # Размещение кораблей на поле
    def place_ships(self):
        for ship, count in self.ships.items():
            for i in range(count):
                size = self.ship_sizes[ship]
                while True:
                    row = random.randint(0, 9)
                    col = random.randint(0, 9)
                    direction = random.choice(['вертикальное', 'горизонтальное'])
                    if self.check_valid_position(self.field, row, col, size, direction):
                        self.field = self.place_ship(self.field, row, col, size, direction)
                        break
        # Вывод поля боя с размещенными кораблями
        for row in self.field:
            print(' '.join(row))

            img = Image.new('RGB', (500, 500), color='white')
            pixels = img.load()
            scale_factor = 50  # размер стороны клетки
            black_color = (0, 0, 0)  # цвет черной клетки
            for i in range(10):
                for j in range(10):
                    if self.field[i][j] == self.filled_square:
                        # координаты левого верхнего пикселя
                        x = j * scale_factor
                        y = i * scale_factor
                        # рисуем квадрат 4х4 пикселя
                        for k in range(32):
                            for l in range(32):
                                # проверяем, не выходим ли за границы изображения
                                if x + k < 500 and y + l < 500:
                                    pixels[x + k, y + l] = black_color

            # Сохранение изображения в файл
            img.save('battleship_board.png')


# Здесь мы начинаем создавать нашего телеграм бота

bot = telebot.TeleBot('6214557143:AAF9wrgPduSyDvYCJrmiaizbiahJwbDPem4')

@bot.message_handler(commands=['start'])
def start(message):
    hello_mess = f'Привет, <b>{message.from_user.username}</b>'
    enter_game_mess = f'Твоя жизнь крайне скучная и утомляющая? Никто из друзей не соглашается поиграть в настольные игры из-за сессии?' \
                      f'' \
                      f' Тогда ты попал по адресу! Наша команда предлагает тебе абстрагироваться от окружающей реальности и вернуться в детство.'
    enter_game_mess += emoji.emojize(':magic_wand:')
    next_point_mess = f'Для продолжения игры напиши GO'
    bot.send_message(message.chat.id, hello_mess, parse_mode='html')
    bot.send_message(message.chat.id, enter_game_mess)
    bot.send_message(message.chat.id, next_point_mess)



@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.text == 'GO':
        photo = open('Правила.jpg', 'rb')
        bot.send_message(message.chat.id, 'Правила игры:')
        bot.send_photo(message.chat.id, photo)

        markup = types.ReplyKeyboardMarkup()
        start = types.KeyboardButton('START')
        markup.add(start)
        bot.send_message(message.chat.id, 'Если прочитал правила, начинай игру', parse_mode='html', reply_markup=markup)

    if message.text == 'START':
        our_ship = random_field()
        our_ship.place_ships()
        photo_field = open('battleship_board.png', 'rb')
        bot.send_message(message.chat.id, 'Мы сгенерировали расстановку твоих кораблей')
        bot.send_photo(message.chat.id, photo_field)


bot.polling(none_stop=True)

