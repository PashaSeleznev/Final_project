import telebot
from telebot import types
import emoji
from random import randrange
from random import choice


class FieldPart(object):
    main = 'map'
    radar = 'radar'
    weight = 'weight'


class InputTypes(object):
    ship_setup = 0
    shot = 1
    other = 2
    waiting = 3


class Cell(object):
    empty_cell = emoji.emojize(':water_wave:')
    ship_cell = emoji.emojize(':passenger_ship:')
    destroyed_ship = emoji.emojize(':skull:')
    damaged_ship = emoji.emojize(':fire:')
    miss_cell = emoji.emojize(':sweat_droplets:')


# Поле игры состоит из трех частей: карта, где расставлены корабли игрока;
# радар, на котором игрок отмечает свои ходы и результаты выстрелов;
# поле с весом клеток (используется для ходов ИИ)
class Field(object):

    def __init__(self, size):
        self.size = size
        self.map = [[Cell.empty_cell for _ in range(size)] for _ in range(size)]
        self.radar = [[Cell.empty_cell for _ in range(size)] for _ in range(size)]
        self.weight = [[1 for _ in range(size)] for _ in range(size)]

    def get_field_part(self, element):
        if element == FieldPart.main:
            return self.map
        if element == FieldPart.radar:
            return self.radar
        if element == FieldPart.weight:
            return self.weight

    # Рисуем поле. Здесь отрисовка делитcя на две части. т.к. отрисовка весов клеток идёт по другому
    def draw_field(self, element):
        field = self.get_field_part(element)
        # Выбор варианта отображения букв
        #letters = "  🄰  🄱  🄲  🄳  🄴  🄵  🄶  🄷  🄸  🄹"
        letters = '\U0001f1e6 ' + '\U0001f1e7 ' + '\U0001f1e8 ' + '\U0001f1e9 ' + '\U0001f1eA ' + \
                  '\U0001f1eB ' + '\U0001f1eC ' + '\U0001f1eD ' + '\U0001f1eE ' + '\U0001f1eF '

        field_message = emoji.emojize(':triangular_flag:') + letters[0:self.size * 2] + '\n'
        for x in range(0, self.size):
            field_message += emoji.emojize(':keycap_' + str(x + 1) + ':')
            for y in range(0, self.size):
                field_message += " " + str(field[x][y])
            field_message += '\n'
        field_message += '\n'
        return field_message

    # Функция проверяет, помещается ли корабль на конкретную позицию конкретного поля.
    # Возвращает False если не помещается и True если корабль помещается
    def check_ship_fits(self, ship, element):

        field = self.get_field_part(element)

        if ship.x + ship.height - 1 >= self.size or ship.x < 0 or \
                ship.y + ship.width - 1 >= self.size or ship.y < 0:
            return False

        x = ship.x
        y = ship.y
        width = ship.width
        height = ship.height

        for p_x in range(x, x + height):
            for p_y in range(y, y + width):
                if str(field[p_x][p_y]) == Cell.miss_cell:
                    return False

        for p_x in range(x - 1, x + height + 1):
            for p_y in range(y - 1, y + width + 1):
                if p_x < 0 or p_x >= len(field) or p_y < 0 or p_y >= len(field):
                    continue
                if str(field[p_x][p_y]) in (Cell.ship_cell, Cell.destroyed_ship):
                    return False

        return True

    # Когда корабль уничтожен необходимо пометить все клетки вокруг него сыгранными (Cell.miss_cell)
    # а все клетки корабля - уничтоженными (Cell.destroyed_ship). Так и делаем, только в два подхода.
    def mark_destroyed_ship(self, ship, element):

        field = self.get_field_part(element)

        x, y = ship.x, ship.y
        width, height = ship.width, ship.height

        for p_x in range(x - 1, x + height + 1):
            for p_y in range(y - 1, y + width + 1):
                if p_x < 0 or p_x >= len(field) or p_y < 0 or p_y >= len(field):
                    continue
                field[p_x][p_y] = Cell.miss_cell

        for p_x in range(x, x + height):
            for p_y in range(y, y + width):
                field[p_x][p_y] = Cell.destroyed_ship

    # Добавление корабля: пробегаемся от позиции х у корабля по его высоте и ширине и помечаем на поле эти клетки
    # параметр element - сюда мы передаем к какой части поля мы обращаемся: основная, радар или вес
    def add_ship_to_field(self, ship, element):

        field = self.get_field_part(element)

        x, y = ship.x, ship.y
        width, height = ship.width, ship.height

        for p_x in range(x, x + height):
            for p_y in range(y, y + width):
                # В клетку записывается ссылка на корабль (чтобы можно было получить его HP)
                field[p_x][p_y] = ship

    # Функция возвращает список координат с самым большим коэффициентом шанса попадания
    def get_max_weight_cells(self):
        weights = {}
        max_weight = 0
        # Пробегаем по всем клеткам и заносим их в словарь с ключом который является значением
        # Далее берём из словаря список координат с этим максимальным значением weights[max_weight]
        for x in range(self.size):
            for y in range(self.size):
                if self.weight[x][y] > max_weight:
                    max_weight = self.weight[x][y]
                weights.setdefault(self.weight[x][y], []).append((x, y))

        return weights[max_weight]

    # пересчет веса клеток
    def recalculate_weight_map(self, available_ships):
        # Для начала мы выставляем всем клеткам 1 (предыдущий вес не используется)
        self.weight = [[1 for _ in range(self.size)] for _ in range(self.size)]

        # Если находим раненый корабль - ставим клеткам выше ниже и по бокам
        # коэффициенты умноженные на 50. По диагоналям от раненой клетки вписываем нули
        for x in range(self.size):
            for y in range(self.size):
                if self.radar[x][y] == Cell.damaged_ship:

                    self.weight[x][y] = 0

                    if x - 1 >= 0:
                        if y - 1 >= 0:
                            self.weight[x - 1][y - 1] = 0
                        self.weight[x - 1][y] *= 50
                        if y + 1 < self.size:
                            self.weight[x - 1][y + 1] = 0

                    if y - 1 >= 0:
                        self.weight[x][y - 1] *= 50
                    if y + 1 < self.size:
                        self.weight[x][y + 1] *= 50

                    if x + 1 < self.size:
                        if y - 1 >= 0:
                            self.weight[x + 1][y - 1] = 0
                        self.weight[x + 1][y] *= 50
                        if y + 1 < self.size:
                            self.weight[x + 1][y + 1] = 0

        # Перебираем все корабли оставшиеся у противника.
        # Если он может находиться в какой-то клетке поля, увеличиваем ее вес на 1

        for ship_size in available_ships:
            # Рассматриваем оба возможных положения корабля
            ship_vert = Ship(ship_size, 1, 1, True)
            ship_hor = Ship(ship_size, 1, 1, False)
            for x in range(self.size):
                for y in range(self.size):
                    if self.radar[x][y] in (Cell.destroyed_ship, Cell.damaged_ship, Cell.miss_cell) \
                            or self.weight[x][y] == 0:
                        self.weight[x][y] = 0
                        continue
                    # Подставляем корабль в текущую клетку
                    ship_vert.set_position(x, y, True)
                    ship_hor.set_position(x, y, False)
                    # По всей площади корабля увеличиваем вес
                    if self.check_ship_fits(ship_vert, FieldPart.radar):
                        for i in range(ship_size):
                            self.weight[x + i][y] += 1
                    if self.check_ship_fits(ship_hor, FieldPart.radar):
                        for i in range(ship_size):
                            self.weight[x][y + i] += 1


class Game(object):
    letters = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")
    # letters = ("A", "B", "C", "D")
    ships_rules = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
    # ships_rules = [1,2]
    field_size = len(letters)
    input_type = InputTypes.other

    def __init__(self):

        self.players = []
        self.current_player = None
        self.next_player = None
        self.input_type = InputTypes.other
        self.status = 'prepare'

    # при старте игры назначаем текущего и следующего игрока
    def start_game(self):
        self.current_player = self.players[0]
        self.next_player = self.players[1]

    # функция переключения статусов
    def status_check(self):
        # Переключаем с prepare на in game если в игру добавлено два игрока.
        if self.status == 'prepare' and len(self.players) >= 2:
            self.status = 'in game'
            self.start_game()
            return True
        # Переключаем в статус в "game over" если у следующего игрока осталось 0 кораблей.
        if self.status == 'in game' and len(self.next_player.ships) == 0:
            self.status = 'game over'
            return True

    def add_player(self, player):
        # При добавлении игрока создаем для него поле
        player.field = Field(Game.field_size)
        player.enemy_ships = list(Game.ships_rules)
        # Расставляем его корабли
        self.ships_setup(player)
        # Высчитываем вес для клеток поля (это нужно только для ИИ)
        player.field.recalculate_weight_map(player.enemy_ships)
        self.players.append(player)

    def ships_setup(self, player):
        # Делаем расстановку кораблей по правилам заданным в классе Game
        for ship_size in Game.ships_rules:
            # Задаем количество попыток, чтобы не попасть в бесконечный цикл когда для корабля остается очень мало места
            retry_count = 30
            # Создаем предварительно корабль-болванку просто нужного размера
            ship = Ship(ship_size, 0, 0, True)

            while True:
                x, y, r = player.get_input('ship_setup')
                ship.set_position(x, y, r)

                # если корабль помещается на заданной позиции - добавляем игроку на поле и в список корабль
                if player.field.check_ship_fits(ship, FieldPart.main):
                    player.field.add_ship_to_field(ship, FieldPart.main)
                    player.ships.append(ship)
                    break

                # Если корабль не поместился. пишем, отнимаем попытку на расстановку
                retry_count -= 1
                if retry_count < 0:
                    # после заданного количества неудачных попыток - обнуляем карту игрока
                    player.field.map = [[Cell.empty_cell for _ in range(Game.field_size)] for _ in
                                        range(Game.field_size)]
                    player.ships = []
                    self.ships_setup(player)
                    return True

    def draw(self):
        field = self.current_player.field.draw_field(FieldPart.main)
        radar = self.current_player.field.draw_field(FieldPart.radar)
        return field, radar

    def switch_players(self):
        self.current_player, self.next_player = self.next_player, self.current_player


class Player(object):

    def __init__(self, name, is_ai, skill, auto_ship):
        self.name = name
        self.is_ai = is_ai
        self.auto_ship_setup = auto_ship
        self.skill = skill
        self.ships = []
        self.enemy_ships = []
        self.field = None

    # Получение ответа от ИИ
    def get_input(self, input_type):

        if input_type == "ship_setup":

            user_input = str(choice(Game.letters)) + str(randrange(0, self.field.size)) + choice(["H", "V"])
            x, y, r = user_input[0], user_input[1:-1], user_input[-1]

            return Game.letters.index(x), int(y) - 1, False if r == 'H' else True

        if input_type == "shot":
            if self.is_ai:
                if self.skill == 1:
                    x, y = choice(self.field.get_max_weight_cells())
                if self.skill == 0:
                    x, y = randrange(0, self.field.size), randrange(0, self.field.size)
            else:
                pass
            return x, y

    # При совершении выстрела мы будем запрашивать ввод данных с типом shot
    def make_shot(self, target_player, x, y):

        if self.is_ai:
            x, y = choice(self.field.get_max_weight_cells())
        sx, sy = x, y

        shot_res = target_player.receive_shot((sx, sy))

        if shot_res == 'miss':
            self.field.radar[sx][sy] = Cell.miss_cell

        if shot_res == 'get':
            self.field.radar[sx][sy] = Cell.damaged_ship

        if type(shot_res) == Ship:
            destroyed_ship = shot_res
            self.field.mark_destroyed_ship(destroyed_ship, FieldPart.radar)
            self.enemy_ships.remove(destroyed_ship.size)
            shot_res = 'kill'

        # После совершения выстрела пересчитаем карту весов
        self.field.recalculate_weight_map(self.enemy_ships)

        return shot_res

    # Игрок принимает выстрел, возвращает результат:
    # попал (return "get") промазал (return "miss") или убил корабль (тогда возвращаем корабль)
    def receive_shot(self, shot):

        sx, sy = shot

        if type(self.field.map[sx][sy]) == Ship:
            ship = self.field.map[sx][sy]
            ship.hp -= 1

            if ship.hp <= 0:
                self.field.mark_destroyed_ship(ship, FieldPart.main)
                self.ships.remove(ship)
                return ship

            self.field.map[sx][sy] = Cell.damaged_ship
            return 'get'

        else:
            self.field.map[sx][sy] = Cell.miss_cell
            return 'miss'


class Ship:

    def __init__(self, size, x, y, is_vert):
        self.size = size
        self.hp = size
        self.x = x
        self.y = y
        self.is_vert = is_vert
        self.set_rotation(is_vert)

    def __str__(self):
        return Cell.ship_cell

    def set_position(self, x, y, is_vert):
        self.x = x
        self.y = y
        self.set_rotation(is_vert)

    def set_rotation(self, is_vert):
        if is_vert:
            self.height, self.width = self.size, 1
        else:
            self.height, self.width = 1, self.size


# Здесь мы начинаем создавать нашего телеграм бота

chatVariables = {}
bot = telebot.TeleBot('6214557143:AAF9wrgPduSyDvYCJrmiaizbiahJwbDPem4')
players = []


@bot.message_handler(commands=['start'])
def start(message):
    game = Game()
    chatVariables[message.chat.id] = game
    hello_mess = f'Привет, <b>{message.from_user.username}</b>'
    enter_game_mess = f'Никто из друзей не соглашается поиграть в настольные игры из-за сессии?' \
                      f'' \
                      f' Тогда ты попал по адресу! Наша команда предлагает тебе вернуться в детство.'
    enter_game_mess += emoji.emojize(':magic_wand:')

    bot.send_message(message.chat.id, hello_mess, parse_mode='html')
    bot.send_message(message.chat.id, enter_game_mess)

    markup = types.ReplyKeyboardMarkup()
    Start = types.KeyboardButton('Начать')
    Help = types.KeyboardButton('Помощь')
    markup.add(Start, Help)
    bot.send_message(message.chat.id, 'Для начала игры нажми "Начать", а для ознакомления с правилами ввода - "Помощь"\n'
                                      'Для выхода из игры введи "Завершить"',
                     parse_mode='html',
                     reply_markup=markup)


@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.chat.id not in chatVariables.keys():
        bot.send_message(message.chat.id, "Вас нет в базе данных!\nНажмите /start чтобы исправить")
        return
    elif message.text == 'Помощь':
        help_mes = 'Цель игры - "потопить" все вражеские корабли\n' \
                   'Игровое поле представляет собой квадрат 10x10, столбцы обозначены латинскими заглавными буквами, а строки - числами.\n' \
                   'На игровом поле хаотично расположены корабли: 4 однопалубных, 3 двухпалубных, 2 трехпалубных и 1 четырехпалубный ' \
                   '(расстановка происходит автоматически). Корабли не могут поворачивать.\n' \
                   'Когда собираешься ввести координату выстрела, используй следующий формат: [A-J,1-10] (Заглавная латинская буква от A до J + число от 1 до 10).'
        bot.send_message(message.chat.id, help_mes)
    current_game = chatVariables[message.chat.id]
    if current_game.input_type == InputTypes.other:
        if message.text == 'Начать':
            current_game = Game()
            chatVariables[message.chat.id] = current_game
            current_game.add_player(Player(name=message.from_user.first_name, is_ai=False, auto_ship=True, skill=1))
            current_game.add_player(Player(name='SkyNet', is_ai=True, auto_ship=True, skill=1))
            current_game.status_check()
            field, radar = current_game.draw()
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, 'Ваш флот\n' + field, parse_mode='html', reply_markup=markup)
            bot.send_message(message.chat.id, 'Радар\n' + radar)
            current_game.input_type = InputTypes.shot

    elif current_game.input_type == InputTypes.shot:
        current_game.input_type = InputTypes.waiting
        if message.text == 'Завершить':
            current_game.input_type = InputTypes.other
            current_game.status = 'game over'
        else:
            user_input = message.text.upper().replace(" ", "")
            x, y = user_input[0].upper(), user_input[1:]
            current_game.input_type = InputTypes.waiting
            if x not in Game.letters or not y.isdigit() or int(y) not in range(1, Game.field_size + 1):
                bot.send_message(message.chat.id, 'Приказ непонятен, повторите')
            else:
                y, x = Game.letters.index(x), int(y) - 1
                shot_result = current_game.current_player.make_shot(current_game.next_player, x, y)
                if shot_result == 'miss':
                    bot.send_message(message.chat.id, 'Промах!')
                    current_game.switch_players()
                    shot_result = ''
                    while shot_result != 'miss':
                        bot.send_message(message.chat.id, 'Ход вашего соперника...')
                        shot_result = current_game.current_player.make_shot(current_game.next_player, 1, 1)
                        if shot_result == 'miss':
                            bot.send_message(message.chat.id, current_game.current_player.name + ' промахнулся!')
                        elif shot_result == 'get':
                            bot.send_message(message.chat.id, 'Наш корабль попал под обстрел!')
                        elif shot_result == 'kill':
                            bot.send_message(message.chat.id, 'Наш корабль был уничтожен!')
                            current_game.status_check()
                            if current_game.status == 'game over':
                                reply = 'Это был наш последний корабль!\n' + current_game.current_player.name + ' победил'
                                bot.send_message(message.chat.id, reply)
                                shot_result = 'miss'
                    current_game.switch_players()
                elif shot_result == 'get':
                    bot.send_message(message.chat.id, 'Отличный выстрел, продолжайте!')
                elif shot_result == 'kill':
                    bot.send_message(message.chat.id, 'Корабль противника уничтожен!')
                    current_game.status_check()
                    if current_game.status == 'game over':
                        bot.send_message(message.chat.id, 'Это был последний\nОтличная работа, капитан!\n' + current_game.next_player.name + ' повержен')
            field, radar = current_game.draw()
            bot.send_message(message.chat.id, 'Ваш флот\n' + field)
            bot.send_message(message.chat.id, 'Радар\n' + radar)
        if current_game.status == 'game over':
            current_game.input_type = InputTypes.other
            markup = types.ReplyKeyboardMarkup()
            retry = types.KeyboardButton('Начать')
            markup.add(retry)
            bot.send_message(message.chat.id, 'Спасибо за игру!\nЕсли хотите продолжить, нажмите "Начать"' , parse_mode='html', reply_markup=markup)
        else:
            current_game.input_type = InputTypes.shot
    elif current_game.input_type == InputTypes.ship_setup:
        pass

    elif current_game.input_type == InputTypes.waiting:
        reply = "Ожидайте своей очереди"
        bot.send_message(message.chat.id, reply)


bot.polling(none_stop=True)
