import telebot
from telebot import types
import emoji
import random
import emoji
from PIL import Image
import os
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


class InputType:
    input_type = InputTypes.other

    def get_input_type(self):
        return self.input_type

    def set_input_type(self, type):
        self.input_type = type


class Cell(object):
    empty_cell = emoji.emojize(':water_wave:')
    ship_cell = emoji.emojize(':passenger_ship:')
    destroyed_ship = emoji.emojize(':skull:')
    damaged_ship = emoji.emojize(':fire:')
    miss_cell = emoji.emojize(':sweat_droplets:')


# поле игры. состоит из трех частей: карта где расставлены корабли игрока.
# радар на котором игрок отмечает свои ходы и результаты
# поле с весом клеток. используется для ходов ИИ
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
        reply = ''
        field = self.get_field_part(element)
        field_message = emoji.emojize(':triangular_flag:') + " 🄰  🄱  🄲  🄳  🄴  🄵  🄶  🄷  🄸  🄹" + '\n'
        for x in range(0, self.size):
            field_message += emoji.emojize(':keycap_' + str(x + 1) + ':')
            for y in range(0, self.size):
                field_message += " " + str(field[x][y])
            field_message += '\n'
        field_message += '\n'
        return field_message

    # Функция проверяет помещается ли корабль на конкретную позицию конкретного поля.
    # будем использовать при расстановке кораблей, а так же при вычислении веса клеток
    # возвращает False если не помещается и True если корабль помещается
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

    # добавление корабля: пробегаемся от позиции х у корабля по его высоте и ширине и помечаем на поле эти клетки
    # параметр element - сюда мы передаем к какой части поля мы обращаемся: основная, радар или вес
    def add_ship_to_field(self, ship, element):

        field = self.get_field_part(element)

        x, y = ship.x, ship.y
        width, height = ship.width, ship.height

        for p_x in range(x, x + height):
            for p_y in range(y, y + width):
                # заметьте в клетку мы записываем ссылку на корабль.
                # таким образом обращаясь к клетке мы всегда можем получить текущее HP корабля
                field[p_x][p_y] = ship

    # функция возвращает список координат с самым большим коэффициентом шанса попадения
    def get_max_weight_cells(self):
        weights = {}
        max_weight = 0
        # просто пробегаем по всем клеткам и заносим их в словарь с ключом который является значением в клетке
        # заодно запоминаем максимальное значение. Далее просто берём из словаря список координат с этим
        # максимальным значением weights[max_weight]
        for x in range(self.size):
            for y in range(self.size):
                if self.weight[x][y] > max_weight:
                    max_weight = self.weight[x][y]
                weights.setdefault(self.weight[x][y], []).append((x, y))

        return weights[max_weight]

    # пересчет веса клеток
    def recalculate_weight_map(self, available_ships):
        # Для начала мы выставляем всем клеткам 1.
        # нам необязательно знать какой вес был у клетки в предыдущий раз:
        # эффект веса не накапливается от хода к ходу.
        self.weight = [[1 for _ in range(self.size)] for _ in range(self.size)]

        # Пробегаем по всем полю.
        # Если находим раненый корабль - ставим клеткам выше ниже и по бокам
        # коэффициенты умноженые на 50 т.к. логично что корабль имеет продолжение в одну из сторон.
        # По диагоналям от раненой клетки ничего не может быть - туда вписываем нули
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
        # Это открытая инафа исходя из правил игры.  Проходим по каждой клетке поля.
        # Если там уничтоженый корабль, задамаженый или клетка с промахом -
        # ставим туда коэффициент 0. Больше делать нечего - переходим следующей клетке.
        # Иначе прикидываем может ли этот корабль с этой клетки начинаться в какую-либо сторону
        # и если он помещается прбавляем клетке коэф 1.

        for ship_size in available_ships:

            ship = Ship(ship_size, 1, 1, 0)
            # вот тут бегаем по всем клеткам поля
            for x in range(self.size):
                for y in range(self.size):
                    if self.radar[x][y] in (Cell.destroyed_ship, Cell.damaged_ship, Cell.miss_cell) \
                            or self.weight[x][y] == 0:
                        self.weight[x][y] = 0
                        continue
                    # вот здесь ворочаем корабль и проверяем помещается ли он
                    for rotation in range(0, 4):
                        ship.set_position(x, y, rotation)
                        if self.check_ship_fits(ship, FieldPart.radar):
                            self.weight[x][y] += 1


class Game(object):
    letters = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J")
    ships_rules = [1, 1, 1, 1, 2, 2, 2, 3, 3, 4]
    field_size = len(letters)

    def __init__(self):

        self.players = []
        self.current_player = None
        self.next_player = None

        self.status = 'prepare'

    # при старте игры назначаем текущего и следующего игрока
    def start_game(self):

        self.current_player = self.players[0]
        self.next_player = self.players[1]

    # функция переключения статусов
    def status_check(self):
        # Переключаем с prepare на in game если в игру добавлено два игрока.
        # Далее стартуем игру
        if self.status == 'prepare' and len(self.players) >= 2:
            self.status = 'in game'
            self.start_game()
            return True
        # переключаем в статус game over если у следующего игрока осталось 0 кораблей.
        if self.status == 'in game' and len(self.next_player.ships) == 0:
            self.status = 'game over'
            return True

    def add_player(self, player):
        # при добавлении игрока создаем для него поле
        player.field = Field(Game.field_size)
        player.enemy_ships = list(Game.ships_rules)
        # расставляем корабли
        self.ships_setup(player)
        # высчитываем вес для клеток поля (это нужно только для ИИ, но в целом при расширении возможностей
        # игры можно будет например на основе этого давать подсказки игроку).
        player.field.recalculate_weight_map(player.enemy_ships)
        self.players.append(player)

    def ships_setup(self, player):
        # делаем расстановку кораблей по правилам заданным в классе Game
        for ship_size in Game.ships_rules:
            # задаем количество попыток при выставлении кораблей случайным образом
            # нужно для того чтобы не попасть в бесконечный цикл когда для последнего корабля остаётся очень мало места
            retry_count = 30

            # создаем предварительно корабль-балванку просто нужного размера
            # дальше будет видно что мы присваиваем ему координаты которые ввел пользователь
            ship = Ship(ship_size, 0, 0, 0)

            while True:

                if player.auto_ship_setup is not True:
                    player.field.draw_field(FieldPart.main)
                    player.message.append('Куда поставить {} корабль: '.format(ship_size))
                    for _ in player.message:
                        print(_)
                else:
                    pass

                player.message.clear()

                x, y, r = player.get_input('ship_setup')
                # если пользователь ввёл какую-то ерунду функция возвратит нули, значит без вопросов делаем continue
                # фактически просто просим еще раз ввести координаты
                if x + y + r == 0:
                    continue

                ship.set_position(x, y, r)

                # если корабль помещается на заданной позиции - отлично. добавляем игроку на поле корабль
                # также добавляем корабль в список кораблей игрока. и переходим к следующему кораблю для расстановки
                if player.field.check_ship_fits(ship, FieldPart.main):
                    player.field.add_ship_to_field(ship, FieldPart.main)
                    player.ships.append(ship)
                    break

                # сюда мы добираемся только если корабль не поместился. пишем юзеру что позиция неправильная
                # и отнимаем попытку на расстановку
                player.message.append('Неправильная позиция!')
                retry_count -= 1
                if retry_count < 0:
                    # после заданного количества неудачных попыток - обнуляем карту игрока
                    # убираем у него все корабли и начинаем расстановку по новой
                    player.field.map = [[Cell.empty_cell for _ in range(Game.field_size)] for _ in
                                        range(Game.field_size)]
                    player.ships = []
                    self.ships_setup(player)
                    return True

    def draw(self):
        field = self.current_player.field.draw_field(FieldPart.main)
        radar = self.current_player.field.draw_field(FieldPart.radar)
        return field, radar

    # игроки меняются вот так вот просто.
    def switch_players(self):
        self.current_player, self.next_player = self.next_player, self.current_player


class Player(object):

    def __init__(self, name, is_ai, skill, auto_ship):
        self.name = name
        self.is_ai = is_ai
        self.auto_ship_setup = auto_ship
        self.skill = skill
        self.message = []
        self.ships = []
        self.enemy_ships = []
        self.field = None

    # Ход игрока. Это либо расстановка кораблей (input_type == "ship_setup")
    # Либо совершения выстрела (input_type == "shot")
    def get_input(self, input_type):

        if input_type == "ship_setup":

            if self.is_ai or self.auto_ship_setup:
                user_input = str(choice(Game.letters)) + str(randrange(0, self.field.size)) + choice(["H", "V"])
            else:
                user_input = input().upper().replace(" ", "")

            if len(user_input) < 3:
                return 0, 0, 0

            x, y, r = user_input[0], user_input[1:-1], user_input[-1]

            if x not in Game.letters or not y.isdigit() or int(y) not in range(1, Game.field_size + 1) or \
                    r not in ("H", "V"):
                self.message.append('Приказ непонятен, повторите')
                return 0, 0, 0

            return Game.letters.index(x), int(y) - 1, 0 if r == 'H' else 1

        if input_type == "shot":

            if self.is_ai:
                if self.skill == 1:
                    x, y = choice(self.field.get_max_weight_cells())
                if self.skill == 0:
                    x, y = randrange(0, self.field.size), randrange(0, self.field.size)
            else:
                user_input = input().upper().replace(" ", "")
                x, y = user_input[0].upper(), user_input[1:]
                if x not in Game.letters or not y.isdigit() or int(y) not in range(1, Game.field_size + 1):
                    self.message.append('Приказ непонятен, ошибка формата данных')
                    return 500, 0
                x = Game.letters.index(x)
                y = int(y) - 1
            return x, y

    # при совершении выстрела мы будем запрашивать ввод данных с типом shot
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

        # после совершения выстрела пересчитаем карту весов
        self.field.recalculate_weight_map(self.enemy_ships)

        return shot_res

    # здесь игрок будет принимать выстрел
    # как и в жизни игрок должен отвечать (возвращать) результат выстрела
    # попал (return "get") промазал (return "miss") или убил корабль (тогда возвращаем целиком корабль)
    # так проще т.к. сразу знаем и координаты корабля и его длину
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

    def __init__(self, size, x, y, rotation):

        self.size = size
        self.hp = size
        self.x = x
        self.y = y
        self.rotation = rotation
        self.set_rotation(rotation)

    def __str__(self):
        return Cell.ship_cell

    def set_position(self, x, y, r):
        self.x = x
        self.y = y
        self.set_rotation(r)

    def set_rotation(self, r):

        self.rotation = r

        if self.rotation == 0:
            self.width = self.size
            self.height = 1
        elif self.rotation == 1:
            self.width = 1
            self.height = self.size
        elif self.rotation == 2:
            self.y = self.y - self.size + 1
            self.width = self.size
            self.height = 1
        elif self.rotation == 3:
            self.x = self.x - self.size + 1
            self.width = 1
            self.height = self.size


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
    markup.add(Start)
    bot.send_message(message.chat.id, 'Для начала игры нажми "Начать"', parse_mode='html',
                     reply_markup=markup)


@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.chat.id not in chatVariables.keys():
        bot.send_message(message.chat.id, "Вас нет в базе данных!\nНажмите /start чтобы исправить")
        return
    current_game = chatVariables[message.chat.id]
    if InputType.input_type == InputTypes.other:
        if message.text == 'Автоматически':
            pass
        elif message.text == 'Вручную':
            pass
        elif message.text == 'Завершить':
            pass
        elif message.text == 'Начать':
            current_game.add_player(Player(name=message.from_user.first_name, is_ai=False, auto_ship=True, skill=1))
            current_game.add_player(Player(name='SkyNet', is_ai=True, auto_ship=True, skill=1))
            current_game.start_game()
            field, radar = current_game.draw()
            markup = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, 'Ваш флот\n' + field, parse_mode='html', reply_markup=markup)
            bot.send_message(message.chat.id, 'Радар\n' + radar)
            InputType.input_type = InputTypes.shot

    elif InputType.input_type == InputTypes.shot:
        user_input = message.text.upper().replace(" ", "")
        x, y = user_input[0].upper(), user_input[1:]
        reply = ''
        if x not in Game.letters or not y.isdigit() or int(y) not in range(1, Game.field_size + 1):
            bot.send_message(message.chat.id, 'Приказ непонятен, ошибка формата данных')
        else:
            y, x = Game.letters.index(x), int(y) - 1
            shot_result = current_game.current_player.make_shot(current_game.next_player, x, y)
            if shot_result == 'miss':
                reply += 'Промах!\n'
                bot.send_message(message.chat.id, reply)
                current_game.switch_players()
                shot_result = ''
                while shot_result != 'miss':
                    bot.send_message(message.chat.id, 'Ход вашего соперника...')
                    shot_result = current_game.current_player.make_shot(current_game.next_player, 1, 1)
                    if shot_result == 'miss':
                        reply = current_game.current_player.name + ' промахнулся!\n'
                    elif shot_result == 'get':
                        reply = 'Наш корабль попал под обстрел!'
                    elif shot_result == 'kill':
                        reply = 'Наш корабль был уничтожен!'
                        if current_game.status == 'game over':
                            reply = 'Наш последний корабль уничтожен!\n' + current_game.current_player.name + ' победил'
                            bot.send_message(message.chat.id, reply)
                            InputType.input_type = InputTypes.other
                            break
                    bot.send_message(message.chat.id, reply)

                current_game.switch_players()
                reply = ''
            elif shot_result == 'get':
                reply = 'Отличный выстрел, продолжайте!'
            elif shot_result == 'kill':
                reply = 'Корабль противника уничтожен!'
                current_game.status_check()
                if current_game.status == 'game over':
                    reply = 'Это был последний\nОтличная работа, капитан!\n'+ current_game.next_player.name + ' повержен'
                    InputType.input_type = InputTypes.other
        field, radar = current_game.draw()
        bot.send_message(message.chat.id, 'Ваш флот\n' + field)
        bot.send_message(message.chat.id, 'Радар\n' + radar)
        if reply != '':
            bot.send_message(message.chat.id, reply)

    elif InputType.input_type == InputTypes.ship_setup:
        pass

    elif InputType.input_type == InputTypes.waiting:
        reply = "Ожидайте своей очереди"
        bot.send_message(message.chat.id, reply)


bot.polling(none_stop=True)
