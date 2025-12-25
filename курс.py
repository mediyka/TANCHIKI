import pygame
import random
import math
import os
import sys
import importlib.util

# Инициализация Pygame
pygame.init()

# Константы
SCREEN_WIDTH = 1200  # Увеличили ширину для второго игрока
SCREEN_HEIGHT = 700
GRID_SIZE = 12
CELL_SIZE = min((SCREEN_WIDTH - 600) // GRID_SIZE, SCREEN_HEIGHT // GRID_SIZE)  # Размер клетки
FPS = 30  # Уменьшили FPS для более медленной игры
VISION_RADIUS = 4  # Радиус зрения в клетках
TURN_DELAY = 1000  # Задержка между ходами в миллисекундах (1 секунда)

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)
BROWN = (139, 69, 19)
DARK_GRAY = (50, 50, 50)
LIGHT_BLUE = (100, 100, 255)
LIGHT_GREEN = (100, 255, 100)
ORANGE = (255, 165, 0)
PINK = (255, 182, 193)
DARK_RED = (139, 0, 0)

# Создание окна
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("1 vs 1 Tank Battle - Загрузи AI для боя!")
clock = pygame.time.Clock()


# Функция для преобразования координат сетки в пиксели
def grid_to_pixel(grid_x, grid_y):
    return (grid_x * CELL_SIZE + CELL_SIZE // 2, grid_y * CELL_SIZE + CELL_SIZE // 2)


# Функция для преобразования пикселей в координаты сетки
def pixel_to_grid(x, y):
    return (x // CELL_SIZE, y // CELL_SIZE)


# Функция проверки столкновений со стенами
def check_wall_collision(sprite, walls, new_rect=None):
    if new_rect is None:
        new_rect = sprite.rect
    return any(new_rect.colliderect(wall.rect) for wall in walls)


# Функция проверки столкновений с танками
def check_tank_collision(sprite, tanks, new_rect=None):
    if new_rect is None:
        new_rect = sprite.rect
    for tank in tanks:
        if tank != sprite and new_rect.colliderect(tank.rect):
            return True
    return False


# Функция проверки валидной позиции в сетке
def is_valid_grid_position(grid_x, grid_y, walls, other_tanks=None, medkits=None):
    """Проверяет, можно ли разместить объект в данной клетке сетки"""
    if grid_x < 0 or grid_x >= GRID_SIZE or grid_y < 0 or grid_y >= GRID_SIZE:
        return False

    pixel_x, pixel_y = grid_to_pixel(grid_x, grid_y)
    test_rect = pygame.Rect(pixel_x - CELL_SIZE // 2, pixel_y - CELL_SIZE // 2, CELL_SIZE, CELL_SIZE)

    # Проверяем столкновения со стенами
    if any(test_rect.colliderect(wall.rect) for wall in walls):
        return False

    # Проверяем столкновения с другими танками
    if other_tanks:
        for tank in other_tanks:
            if test_rect.colliderect(tank.rect):
                return False

    return True


# Функция поиска валидной позиции в сетке с минимальным расстоянием
def find_valid_grid_position(walls, existing_tanks=None, medkits=None, max_attempts=100, min_distance=5):
    """Находит валидную позицию для размещения танка в сетке с минимальным расстоянием от других"""
    if existing_tanks is None:
        existing_tanks = []
    if medkits is None:
        medkits = []

    for attempt in range(max_attempts):
        grid_x = random.randint(1, GRID_SIZE - 2)
        grid_y = random.randint(1, GRID_SIZE - 2)

        # Проверяем минимальное расстояние до других танков
        too_close = False
        for tank in existing_tanks:
            distance = abs(grid_x - tank.grid_x) + abs(grid_y - tank.grid_y)
            if distance < min_distance:
                too_close = True
                break

        if too_close:
            continue

        if is_valid_grid_position(grid_x, grid_y, walls, existing_tanks, medkits):
            return (grid_x, grid_y)

    # Если не нашли валидную позицию с минимальным расстоянием, пробуем без ограничения
    for attempt in range(max_attempts):
        grid_x = random.randint(1, GRID_SIZE - 2)
        grid_y = random.randint(1, GRID_SIZE - 2)

        if is_valid_grid_position(grid_x, grid_y, walls, existing_tanks, medkits):
            return (grid_x, grid_y)

    # Если не нашли валидную позицию, возвращаем позицию по умолчанию
    return (GRID_SIZE // 2, GRID_SIZE // 2)


# Функция проверки видимости между двумя клетками
def can_see_between(grid_x1, grid_y1, grid_x2, grid_y2, walls):
    """Проверяет, есть ли прямая видимость между двумя клетками"""
    # Если не на одной линии
    if grid_x1 != grid_x2 and grid_y1 != grid_y2:
        return False

    # Горизонтальная линия
    if grid_y1 == grid_y2:
        start_x = min(grid_x1, grid_x2)
        end_x = max(grid_x1, grid_x2)
        for x in range(start_x + 1, end_x):
            if any(wall.grid_x == x and wall.grid_y == grid_y1 for wall in walls):
                return False
        return True

    # Вертикальная линия
    if grid_x1 == grid_x2:
        start_y = min(grid_y1, grid_y2)
        end_y = max(grid_y1, grid_y2)
        for y in range(start_y + 1, end_y):
            if any(wall.grid_x == grid_x1 and wall.grid_y == y for wall in walls):
                return False
        return True

    return False


# Функция проверки видимости цели с учетом радиуса зрения
def can_see_target(viewer_x, viewer_y, target_x, target_y, walls):
    """Проверяет, видит ли танк цель с учетом радиуса зрения и стен"""
    # Проверяем расстояние
    distance = abs(viewer_x - target_x) + abs(viewer_y - target_y)
    if distance > VISION_RADIUS:
        return False

    # Проверяем видимость по прямой
    return can_see_between(viewer_x, viewer_y, target_x, target_y, walls)


# Класс для аптечки
class Medkit(pygame.sprite.Sprite):
    def __init__(self, grid_x, grid_y):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.image = pygame.Surface((CELL_SIZE - 8, CELL_SIZE - 8), pygame.SRCALPHA)
        # Рисуем аптечку - красный крест на белом фоне
        self.image.fill(WHITE)
        pygame.draw.rect(self.image, RED, (CELL_SIZE // 2 - 4, 2, 8, CELL_SIZE - 12))
        pygame.draw.rect(self.image, RED, (2, CELL_SIZE // 2 - 4, CELL_SIZE - 12, 8))
        pygame.draw.rect(self.image, BLACK, (0, 0, CELL_SIZE - 8, CELL_SIZE - 8), 2)
        pixel_x, pixel_y = grid_to_pixel(grid_x, grid_y)
        self.rect = self.image.get_rect(center=(pixel_x, pixel_y))
        self.active = True  # Активна ли аптечка

    def collect(self):
        """Собирает аптечку - полностью удаляет ее из игры"""
        self.active = False
        self.kill()


# Базовый класс для танка (общий для всех игроков)
class Tank(pygame.sprite.Sprite):
    def __init__(self, grid_x, grid_y, color, player_name, walls, medkits):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.color = color
        self.player_name = player_name
        self.original_image = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(self.original_image, color, (0, 0, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(self.original_image, BLACK, (0, 0, CELL_SIZE, CELL_SIZE), 2)
        pygame.draw.rect(self.original_image, BLACK, (CELL_SIZE // 2 - 2, 0, 4, CELL_SIZE // 2))
        self.image = self.original_image
        pixel_x, pixel_y = grid_to_pixel(grid_x, grid_y)
        self.rect = self.image.get_rect(center=(pixel_x, pixel_y))
        self.direction = pygame.math.Vector2(0, -1)
        self.bullets = pygame.sprite.Group()
        self.shoot_cooldown = 0
        self.health = 15
        self.max_health = 15
        self.score = 0
        self.commands = []
        self.current_command = 0
        self.actions_remaining = 1
        self.ai_module = None
        self.ai_instance = None
        self.execution_method = "commands"
        self.has_moved_this_turn = False
        self.visible_enemies = []
        self.opponent = None

        # ЗНАНИЕ КАРТЫ
        self.known_walls = [(wall.grid_x, wall.grid_y, wall.destructible) for wall in walls]
        self.known_medkits = [(medkit.grid_x, medkit.grid_y) for medkit in medkits]

    def update_position(self):
        """Обновляет пиксельную позицию на основе сеточной"""
        pixel_x, pixel_y = grid_to_pixel(self.grid_x, self.grid_y)
        self.rect.center = (pixel_x, pixel_y)

    def draw_health_bar(self, surface):
        """Отрисовывает полосу здоровья над танком"""
        bar_width = CELL_SIZE
        bar_height = 6
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 10

        # Фон полосы здоровья
        pygame.draw.rect(surface, DARK_RED, (bar_x, bar_y, bar_width, bar_height))

        # Зеленая часть - текущее здоровье
        health_width = int((self.health / self.max_health) * bar_width)
        if health_width > 0:
            pygame.draw.rect(surface, GREEN, (bar_x, bar_y, health_width, bar_height))

        # Обводка
        pygame.draw.rect(surface, BLACK, (bar_x, bar_y, bar_width, bar_height), 1)

    def start_turn(self):
        """Начинает новый ход игрока"""
        self.actions_remaining = 1
        self.has_moved_this_turn = False
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def execute_turn(self, walls, opponent, medkits):
        """Выполняет один ход игрока"""
        if self.actions_remaining <= 0:
            return False

        # Обновляем список видимых врагов
        self.update_visible_enemies([opponent], walls)

        # Обновляем знания о карте
        self.update_knowledge(medkits)

        if self.execution_method == "commands":
            if self.current_command < len(self.commands):
                command = self.commands[self.current_command]
                self.execute_command(command, walls, [opponent], medkits)
                self.current_command += 1
                self.actions_remaining -= 1
                return True

        elif self.execution_method == "ai_module" and self.ai_instance:
            try:
                # Подготовка данных для AI
                wall_coords = [(w.grid_x, w.grid_y, w.destructible) for w in walls]
                visible_enemy_coords = [(e.grid_x, e.grid_y) for e in self.visible_enemies]

                # Вызов AI
                if hasattr(self.ai_instance, 'update_with_full_knowledge'):
                    command = self.ai_instance.update_with_full_knowledge(
                        self.grid_x,
                        self.grid_y,
                        self.direction,
                        visible_enemy_coords,
                        [],
                        wall_coords,
                        self.known_medkits,
                        self.health,
                        self.max_health
                    )
                elif hasattr(self.ai_instance, 'update_with_health'):
                    command = self.ai_instance.update_with_health(
                        self.grid_x,
                        self.grid_y,
                        self.direction,
                        visible_enemy_coords,
                        wall_coords,
                        self.health,
                        self.max_health
                    )
                else:
                    command = self.ai_instance.update(
                        self.grid_x,
                        self.grid_y,
                        self.direction,
                        visible_enemy_coords,
                        wall_coords
                    )

                if command:
                    self.execute_ai_command(command, walls, [opponent], medkits)
                    self.actions_remaining -= 1
                    return True

            except Exception as e:
                print(f"AI execution error for {self.player_name}: {e}")
                import traceback
                traceback.print_exc()
                self.execution_method = "commands"

        return False

    def update_knowledge(self, medkits):
        """Обновляет знания о карте"""
        # Обновляем известные аптечки
        current_active_medkits = [(medkit.grid_x, medkit.grid_y) for medkit in medkits if medkit.active]
        self.known_medkits = current_active_medkits.copy()

    def update_visible_enemies(self, enemies, walls):
        """Обновляет список врагов, которых видит игрок"""
        self.visible_enemies = []
        for enemy in enemies:
            if can_see_target(self.grid_x, self.grid_y, enemy.grid_x, enemy.grid_y, walls):
                self.visible_enemies.append(enemy)

    def execute_command(self, command, walls, enemies, medkits):
        """Выполняет одну команду"""
        try:
            if command.startswith("move("):
                direction = command[5:-1].strip().strip('"').strip("'")
                self.move_tank(direction, walls, enemies, medkits)
            elif command.startswith("shoot("):
                self.shoot(walls, enemies)
        except Exception as e:
            print(f"Error executing command: {e}")

    def execute_ai_command(self, command, walls, enemies, medkits):
        """Выполнение команды от AI модуля"""
        try:
            if command.startswith("move_"):
                direction = command[5:]
                self.move_tank(direction, walls, enemies, medkits)
            elif command == "shoot":
                self.shoot(walls, enemies)
        except Exception as e:
            print(f"Error executing AI command: {e}")

    def move_tank(self, direction, walls, enemies, medkits):
        """Движение танка по сетке"""
        if self.has_moved_this_turn:
            return

        old_direction = self.direction.copy()

        # Устанавливаем направление
        if direction == "up" or direction == "north":
            self.direction = pygame.math.Vector2(0, -1)
            new_grid_x, new_grid_y = self.grid_x, self.grid_y - 1
        elif direction == "down" or direction == "south":
            self.direction = pygame.math.Vector2(0, 1)
            new_grid_x, new_grid_y = self.grid_x, self.grid_y + 1
        elif direction == "left" or direction == "west":
            self.direction = pygame.math.Vector2(-1, 0)
            new_grid_x, new_grid_y = self.grid_x - 1, self.grid_y
        elif direction == "right" or direction == "east":
            self.direction = pygame.math.Vector2(1, 0)
            new_grid_x, new_grid_y = self.grid_x + 1, self.grid_y
        else:
            return

        # Поворачиваем изображение если направление изменилось
        if old_direction != self.direction:
            angle = math.degrees(math.atan2(-self.direction.y, self.direction.x)) - 90
            self.image = pygame.transform.rotate(self.original_image, angle)

        # Проверяем возможность движения
        if is_valid_grid_position(new_grid_x, new_grid_y, walls, enemies, medkits):
            self.grid_x, self.grid_y = new_grid_x, new_grid_y
            self.update_position()
            self.has_moved_this_turn = True

            # Проверяем столкновение с аптечками после движения
            if self.health < self.max_health:
                self.check_medkit_collision(medkits)

    def check_medkit_collision(self, medkits):
        """Проверяет столкновение с аптечками после движения"""
        for medkit in medkits:
            if medkit.active and self.rect.colliderect(medkit.rect) and self.health < self.max_health:
                self.heal()
                # Удаляем аптечку из списка известных перед удалением
                self.known_medkits = [m for m in self.known_medkits if m != (medkit.grid_x, medkit.grid_y)]
                medkit.collect()
                break

    def heal(self, amount=None):
        """Восстанавливает здоровье танка"""
        if amount is None:
            self.health = self.max_health
        else:
            self.health = min(self.max_health, self.health + amount)

    def shoot(self, walls, enemies):
        """Стрельба с проверкой видимости"""
        if self.shoot_cooldown > 0:
            return

        # Проверяем всех видимых врагов на возможность выстрела
        for enemy in self.visible_enemies:
            if self.can_shoot_enemy(enemy, walls):
                pixel_x, pixel_y = grid_to_pixel(self.grid_x, self.grid_y)
                bullet_pos = (pixel_x, pixel_y) + self.direction * (CELL_SIZE // 2)
                bullet = Bullet(bullet_pos[0], bullet_pos[1], self.direction, self.color)
                self.bullets.add(bullet)
                self.shoot_cooldown = 2
                return

    def can_shoot_enemy(self, enemy, walls):
        """Проверяет, можно ли выстрелить во врага"""
        current_dir = self.vector_to_direction(self.direction)

        if current_dir == "right":
            if enemy.grid_y == self.grid_y and enemy.grid_x > self.grid_x:
                return can_see_between(self.grid_x, self.grid_y, enemy.grid_x, enemy.grid_y, walls)
        elif current_dir == "left":
            if enemy.grid_y == self.grid_y and enemy.grid_x < self.grid_x:
                return can_see_between(self.grid_x, self.grid_y, enemy.grid_x, enemy.grid_y, walls)
        elif current_dir == "down":
            if enemy.grid_x == self.grid_x and enemy.grid_y > self.grid_y:
                return can_see_between(self.grid_x, self.grid_y, enemy.grid_x, enemy.grid_y, walls)
        elif current_dir == "up":
            if enemy.grid_x == self.grid_x and enemy.grid_y < self.grid_y:
                return can_see_between(self.grid_x, self.grid_y, enemy.grid_x, enemy.grid_y, walls)

        return False

    def vector_to_direction(self, vector):
        """Преобразует вектор в строковое направление"""
        x, y = vector.x, vector.y
        if x > 0.5:
            return "right"
        elif x < -0.5:
            return "left"
        elif y > 0.5:
            return "down"
        elif y < -0.5:
            return "up"
        return "right"

    def load_commands(self, code):
        """Загрузка команд из текста"""
        self.commands = []
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                self.commands.append(line)
        self.current_command = 0
        self.execution_method = "commands"

    def load_ai_module(self, filepath):
        """Загрузка AI модуля из файла"""
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            ai_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ai_module)

            if hasattr(ai_module, 'TankAI'):
                self.ai_instance = ai_module.TankAI()
                self.execution_method = "ai_module"
                self.current_command = 0
                return True
            else:
                print(f"AI module must contain 'TankAI' class")
                return False

        except Exception as e:
            print(f"Error loading AI module for {self.player_name}: {e}")
            import traceback
            traceback.print_exc()
            return False


# Класс для стены
class Wall(pygame.sprite.Sprite):
    def __init__(self, grid_x, grid_y):
        super().__init__()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
        self.image.fill(GRAY)
        pixel_x, pixel_y = grid_to_pixel(grid_x, grid_y)
        self.rect = self.image.get_rect(center=(pixel_x, pixel_y))
        self.destructible = False


# Класс для пули
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, color):
        super().__init__()
        self.image = pygame.Surface((8, 8))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction
        self.speed = CELL_SIZE
        self.color = color
        self.distance_traveled = 0
        self.max_distance = 5 * CELL_SIZE

    def update(self, walls=None):
        self.rect.center += self.direction * self.speed
        self.distance_traveled += self.speed

        if walls:
            wall_hit = pygame.sprite.spritecollide(self, walls, False)
            if wall_hit:
                self.kill()
                return

        if (self.distance_traveled >= self.max_distance or
                self.rect.right < 0 or self.rect.left > SCREEN_WIDTH - 600 or
                self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT):
            self.kill()


# Класс для интерфейса загрузки файлов
class FileLoader:
    def __init__(self, x, y, width, height, player_name, player_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = pygame.font.SysFont("Arial", 20)
        self.small_font = pygame.font.SysFont("Arial", 16)
        self.loaded_file = None
        self.status_message = f"Выберите AI файл для {player_name}"
        self.status_color = WHITE
        self.player_name = player_name
        self.player_color = player_color

    def draw(self, surface):
        # Фон интерфейса с цветом игрока
        pygame.draw.rect(surface, (self.player_color[0] // 4, self.player_color[1] // 4, self.player_color[2] // 4),
                         self.rect)
        pygame.draw.rect(surface, self.player_color, self.rect, 3)

        title = self.font.render(f"{self.player_name}", True, self.player_color)
        surface.blit(title, (self.rect.x + 10, self.rect.y + 10))

        load_button = pygame.Rect(self.rect.x + 20, self.rect.y + 50, self.rect.width - 40, 40)
        pygame.draw.rect(surface, LIGHT_BLUE, load_button)
        load_text = self.font.render("Загрузить AI файл", True, BLACK)
        surface.blit(load_text, (load_button.centerx - load_text.get_width() // 2,
                                 load_button.centery - load_text.get_height() // 2))

        if self.loaded_file:
            file_text = self.small_font.render(f"Файл: {os.path.basename(self.loaded_file)}", True, LIGHT_GREEN)
        else:
            file_text = self.small_font.render("Файл не выбран", True, RED)

        surface.blit(file_text, (self.rect.x + 20, self.rect.y + 110))

        status_text = self.small_font.render(self.status_message, True, self.status_color)
        surface.blit(status_text, (self.rect.x + 20, self.rect.y + 140))

        return load_button

    def load_file_dialog(self):
        try:
            import tkinter as tk
            from tkinter import filedialog

            root = tk.Tk()
            root.withdraw()

            file_path = filedialog.askopenfilename(
                title=f"Выберите AI файл для {self.player_name}",
                filetypes=[("Python files", "*.py"), ("All files", "*.*")]
            )

            root.destroy()

            if file_path:
                self.loaded_file = file_path
                self.status_message = "Файл загружен успешно!"
                self.status_color = GREEN
                return file_path
            else:
                self.status_message = "Файл не выбран"
                self.status_color = RED
                return None

        except ImportError:
            # Альтернатива если tkinter недоступен
            print("Tkinter не доступен, используйте путь к файлу")
            self.status_message = "Введите путь к файлу вручную"
            self.status_color = ORANGE
            # Просим пользователя ввести путь вручную
            file_path = input(f"Введите путь к файлу AI для {self.player_name}: ")
            if file_path and os.path.exists(file_path):
                self.loaded_file = file_path
                self.status_message = "Файл загружен успешно!"
                self.status_color = GREEN
                return file_path
            return None

    def set_status(self, message, is_error=False):
        self.status_message = message
        self.status_color = RED if is_error else GREEN


# Создание уровня
def create_level():
    walls = pygame.sprite.Group()

    # Границы карты
    for x in range(GRID_SIZE):
        walls.add(Wall(x, 0))
        walls.add(Wall(x, GRID_SIZE - 1))

    for y in range(GRID_SIZE):
        walls.add(Wall(0, y))
        walls.add(Wall(GRID_SIZE - 1, y))


    wall_positions = [
        (3, 3), (3, 4), (3, 5),
        (6, 2), (6, 3), (6, 4),
        (2, 7),
        (3, 7),
        (7, 6), (7, 7),
        (4, 5),
        (5, 4),
        (8, 2), (8, 3),
        (2, 8), (3, 8)
    ]

    for pos in wall_positions:
        if 0 <= pos[0] < GRID_SIZE and 0 <= pos[1] < GRID_SIZE:
            # Проверяем, не является ли позиция одной из тех, что нужно убрать
            if pos not in [(2, 7), (3, 7), (4, 5)]:
                walls.add(Wall(pos[0], pos[1]))

    return walls


# Создание аптечек
def create_medkits(walls, tanks, count=4, min_distance_between_medkits=2):
    medkits = pygame.sprite.Group()
    medkit_positions = []

    for i in range(count):
        for attempt in range(100):
            pos = find_valid_grid_position(walls, tanks, medkits, max_attempts=50)

            if pos:
                too_close = False
                for existing_pos in medkit_positions:
                    distance = abs(pos[0] - existing_pos[0]) + abs(pos[1] - existing_pos[1])
                    if distance < min_distance_between_medkits:
                        too_close = True
                        break

                if not too_close:
                    medkit = Medkit(pos[0], pos[1])
                    medkits.add(medkit)
                    medkit_positions.append(pos)
                    break

    return medkits


# Основная игровая функция
def main():
    walls = create_level()
    medkits = create_medkits(walls, [])

    # Создаем двух игроков в противоположных углах
    # Синий танк - левый верхний угол (1,1)
    player1_pos = (1, 1)
    # Красный танк - правый нижний угол (GRID_SIZE-2, GRID_SIZE-2)
    player2_pos = (GRID_SIZE - 2, GRID_SIZE - 2)

    # Проверяем, что позиции валидны
    if not is_valid_grid_position(player1_pos[0], player1_pos[1], walls):
        # Если позиция занята, ищем другую в левом верхнем квадранте
        for x in range(1, GRID_SIZE // 2):
            for y in range(1, GRID_SIZE // 2):
                if is_valid_grid_position(x, y, walls):
                    player1_pos = (x, y)
                    break
            if player1_pos != (1, 1):
                break

    if not is_valid_grid_position(player2_pos[0], player2_pos[1], walls):
        # Если позиция занята, ищем другую в правом нижнем квадранте
        for x in range(GRID_SIZE - 2, GRID_SIZE // 2, -1):
            for y in range(GRID_SIZE - 2, GRID_SIZE // 2, -1):
                if is_valid_grid_position(x, y, walls):
                    player2_pos = (x, y)
                    break
            if player2_pos != (GRID_SIZE - 2, GRID_SIZE - 2):
                break

    player1 = Tank(player1_pos[0], player1_pos[1], BLUE, "Игрок 1 (Синий)", walls, medkits)
    player2 = Tank(player2_pos[0], player2_pos[1], RED, "Игрок 2 (Красный)", walls, medkits)

    # Устанавливаем оппонентов
    player1.opponent = player2
    player2.opponent = player1

    all_sprites = pygame.sprite.Group()
    all_sprites.add(player1)
    all_sprites.add(player2)
    all_sprites.add(walls)
    all_sprites.add(medkits)

    # Создаем два загрузчика файлов
    file_loader1 = FileLoader(SCREEN_WIDTH - 580, 20, 280, 180, "Игрок 1 (Синий)", BLUE)
    file_loader2 = FileLoader(SCREEN_WIDTH - 280, 20, 280, 180, "Игрок 2 (Красный)", RED)

    run_button = pygame.Rect(SCREEN_WIDTH - 580, 220, 560, 40)
    reset_button = pygame.Rect(SCREEN_WIDTH - 580, 270, 560, 40)
    speed_up_button = pygame.Rect(SCREEN_WIDTH - 580, 320, 180, 40)
    speed_down_button = pygame.Rect(SCREEN_WIDTH - 390, 320, 180, 40)
    pause_button = pygame.Rect(SCREEN_WIDTH - 200, 320, 180, 40)

    all_bullets = pygame.sprite.Group()

    running = True
    game_over = False
    winner = None
    game_started = False
    current_turn = "player1"
    turn_number = 1
    waiting_for_next_turn = False
    turn_timer = 0  # Таймер для автоматических ходов
    game_paused = False  # Флаг паузы
    current_turn_delay = TURN_DELAY  # Текущая задержка между ходами

    while running:
        # Получаем время с последнего кадра
        dt = clock.tick(FPS)

        # Обработка событий
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game_over and event.key == pygame.K_r:
                    return main()
                if event.key == pygame.K_SPACE and game_started and not game_over:
                    game_paused = not game_paused  # Пауза/продолжение по пробелу
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    current_turn_delay = max(100, current_turn_delay - 100)  # Ускорить
                if event.key == pygame.K_MINUS:
                    current_turn_delay += 100  # Замедлить

            if event.type == pygame.MOUSEBUTTONDOWN:
                load_button1 = file_loader1.draw(screen)
                load_button2 = file_loader2.draw(screen)

                if load_button1.collidepoint(event.pos):
                    file_path = file_loader1.load_file_dialog()
                    if file_path:
                        success = player1.load_ai_module(file_path)
                        if success:
                            file_loader1.set_status("AI загружен успешно!")
                        else:
                            file_loader1.set_status("Ошибка загрузки AI", True)

                elif load_button2.collidepoint(event.pos):
                    file_path = file_loader2.load_file_dialog()
                    if file_path:
                        success = player2.load_ai_module(file_path)
                        if success:
                            file_loader2.set_status("AI загружен успешно!")
                        else:
                            file_loader2.set_status("Ошибка загрузки AI", True)

                elif run_button.collidepoint(event.pos) and not game_started:
                    if player1.execution_method == "ai_module" and player1.ai_instance and \
                            player2.execution_method == "ai_module" and player2.ai_instance:
                        game_started = True
                        file_loader1.set_status("Игра запущена!")
                        file_loader2.set_status("Игра запущена!")
                        player1.start_turn()
                        player2.start_turn()
                    else:
                        file_loader1.set_status("Оба игрока должны загрузить AI!", True)
                        file_loader2.set_status("Оба игрока должны загрузить AI!", True)

                elif speed_up_button.collidepoint(event.pos) and game_started:
                    current_turn_delay = max(100, current_turn_delay - 100)  # Ускорить минимум до 100 мс

                elif speed_down_button.collidepoint(event.pos) and game_started:
                    current_turn_delay += 100  # Замедлить

                elif pause_button.collidepoint(event.pos) and game_started and not game_over:
                    game_paused = not game_paused  # Пауза/продолжение

                elif reset_button.collidepoint(event.pos):
                    return main()

        # Игровая логика (только если игра запущена и не на паузе)
        if not game_over and game_started and not game_paused:
            # Обновляем таймер
            turn_timer += dt

            # Если прошло достаточно времени, выполняем ход
            if turn_timer >= current_turn_delay:
                turn_timer = 0  # Сбрасываем таймер

                if current_turn == "player1":
                    action_taken = player1.execute_turn(walls, player2, medkits)
                    if not action_taken or player1.actions_remaining <= 0:
                        # Переход хода к следующему игроку
                        current_turn = "player2"
                        player2.start_turn()
                else:
                    action_taken = player2.execute_turn(walls, player1, medkits)
                    if not action_taken or player2.actions_remaining <= 0:
                        # Переход хода к следующему игроку
                        current_turn = "player1"
                        player1.start_turn()
                        turn_number += 1

            # Обновляем пули каждый кадр (независимо от ходов)
            for bullet in all_bullets:
                bullet.update(walls)

            # Проверяем столкновения пуль игрока 1 с игроком 2
            for bullet in player1.bullets:
                if bullet.rect.colliderect(player2.rect):
                    player2.health -= 1
                    bullet.kill()

                    if player2.health <= 0:
                        game_over = True
                        winner = player1

            # Проверяем столкновения пуль игрока 2 с игроком 1
            for bullet in player2.bullets:
                if bullet.rect.colliderect(player1.rect):
                    player1.health -= 1
                    bullet.kill()

                    if player1.health <= 0:
                        game_over = True
                        winner = player2

            # Очищаем группы пуль после обработки
            player1.bullets = pygame.sprite.Group()
            player2.bullets = pygame.sprite.Group()

            # Собираем все пули в одну группу для отрисовки
            all_bullets.empty()
            all_bullets.add(player1.bullets)
            all_bullets.add(player2.bullets)

        # Отрисовка
        screen.fill(BLACK)

        # Рисуем сетку
        for x in range(GRID_SIZE):
            for y in range(GRID_SIZE):
                rect = pygame.Rect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, DARK_GRAY, rect, 1)

        # Рисуем спрайты
        for sprite in all_sprites:
            if isinstance(sprite, Medkit) and not sprite.active:
                continue
            screen.blit(sprite.image, sprite.rect)

        # Рисуем пули
        all_bullets.draw(screen)

        # Рисуем здоровье
        player1.draw_health_bar(screen)
        player2.draw_health_bar(screen)

        # Рисуем интерфейсы
        pygame.draw.rect(screen, (20, 20, 20), (SCREEN_WIDTH - 600, 0, 600, SCREEN_HEIGHT))
        load_button1 = file_loader1.draw(screen)
        load_button2 = file_loader2.draw(screen)

        # Кнопки управления
        pygame.draw.rect(screen, GREEN, run_button)
        pygame.draw.rect(screen, RED, reset_button)
        pygame.draw.rect(screen, ORANGE, speed_up_button)
        pygame.draw.rect(screen, YELLOW, speed_down_button)
        pause_color = DARK_RED if game_paused else BLUE
        pygame.draw.rect(screen, pause_color, pause_button)

        font = pygame.font.SysFont(None, 28)
        run_text = font.render("ЗАПУСТИТЬ БОЙ AI vs AI", True, BLACK)
        reset_text = font.render("СБРОС ИГРЫ", True, BLACK)
        speed_up_text = font.render("+ УСКОРИТЬ", True, BLACK)
        speed_down_text = font.render("- ЗАМЕДЛИТЬ", True, BLACK)
        pause_text = font.render("ПАУЗА/ПРОДОЛЖ." if game_paused else "ПАУЗА/ПРОДОЛЖ.", True, BLACK)

        screen.blit(run_text,
                    (run_button.centerx - run_text.get_width() // 2, run_button.centery - run_text.get_height() // 2))
        screen.blit(reset_text, (reset_button.centerx - reset_text.get_width() // 2,
                                 reset_button.centery - reset_text.get_height() // 2))
        screen.blit(speed_up_text, (speed_up_button.centerx - speed_up_text.get_width() // 2,
                                    speed_up_button.centery - speed_up_text.get_height() // 2))
        screen.blit(speed_down_text, (speed_down_button.centerx - speed_down_text.get_width() // 2,
                                      speed_down_button.centery - speed_down_text.get_height() // 2))
        screen.blit(pause_text, (pause_button.centerx - pause_text.get_width() // 2,
                                 pause_button.centery - pause_text.get_height() // 2))

        # Информация о текущем состоянии
        info_font = pygame.font.SysFont(None, 22)

        # Информация об игроке 1
        player1_health = info_font.render(f"Игрок 1: {player1.health}/{player1.max_health} HP", True, BLUE)
        player1_pos_text = info_font.render(f"Позиция: ({player1.grid_x}, {player1.grid_y})", True, BLUE)
        player1_ai = info_font.render(f"AI: {'Загружен' if player1.ai_instance else 'Нет'}", True, BLUE)

        # Информация об игроке 2
        player2_health = info_font.render(f"Игрок 2: {player2.health}/{player2.max_health} HP", True, RED)
        player2_pos_text = info_font.render(f"Позиция: ({player2.grid_x}, {player2.grid_y})", True, RED)
        player2_ai = info_font.render(f"AI: {'Загружен' if player2.ai_instance else 'Нет'}", True, RED)

        # Общая информация
        turn_info = info_font.render(f"Ход №{turn_number}", True, WHITE)
        turn_speed = info_font.render(f"Скорость: {current_turn_delay}мс/ход", True, WHITE)
        current_player = info_font.render(
            f"Сейчас ходит: {'Игрок 1 (Синий)' if current_turn == 'player1' else 'Игрок 2 (Красный)'}",
            True, BLUE if current_turn == 'player1' else RED)
        medkits_text = info_font.render(f"Аптечек: {len([m for m in medkits if m.active])}", True, PINK)

        # Индикатор паузы
        if game_paused:
            pause_indicator = info_font.render("ИГРА НА ПАУЗЕ", True, ORANGE)
        else:
            time_to_next_turn = max(0, current_turn_delay - turn_timer)
            next_turn = info_font.render(f"След. ход через: {time_to_next_turn}мс", True, GREEN)

        y_start = 380
        screen.blit(player1_health, (SCREEN_WIDTH - 580, y_start))
        screen.blit(player1_pos_text, (SCREEN_WIDTH - 580, y_start + 25))
        screen.blit(player1_ai, (SCREEN_WIDTH - 580, y_start + 50))

        screen.blit(player2_health, (SCREEN_WIDTH - 580, y_start + 90))
        screen.blit(player2_pos_text, (SCREEN_WIDTH - 580, y_start + 115))
        screen.blit(player2_ai, (SCREEN_WIDTH - 580, y_start + 140))

        screen.blit(turn_info, (SCREEN_WIDTH - 580, y_start + 190))
        screen.blit(turn_speed, (SCREEN_WIDTH - 580, y_start + 215))
        screen.blit(current_player, (SCREEN_WIDTH - 580, y_start + 240))
        screen.blit(medkits_text, (SCREEN_WIDTH - 580, y_start + 265))

        if game_paused:
            screen.blit(pause_indicator, (SCREEN_WIDTH - 580, y_start + 290))
        elif game_started and not game_over:
            screen.blit(next_turn, (SCREEN_WIDTH - 580, y_start + 290))

        if game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))

            game_over_font = pygame.font.SysFont(None, 72)
            if winner:
                winner_text = f"ПОБЕДИЛ {winner.player_name}!"
                game_over_text = game_over_font.render(winner_text, True, winner.color)
            else:
                game_over_text = game_over_font.render("НИЧЬЯ!", True, WHITE)

            restart_text = font.render("Нажмите R для новой игры", True, WHITE)

            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2,
                                         SCREEN_HEIGHT // 2 - game_over_text.get_height() // 2))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()