# tank_ai.py
import random


class TankAI:
    def __init__(self):
        self.visited = set()
        self.last_action = None
        self.action_repeat = 0
        self.shoot_attempts = 0
        self.health_threshold = 0.6  # 60%

    def update_with_full_knowledge(self, my_x, my_y, my_direction,
                                   visible_enemies, visible_medkits,
                                   walls, known_medkits, health, max_health):
        """
        Простой и надежный AI
        """

        # Сохраняем текущую позицию
        current_pos = (my_x, my_y)
        self.visited.add(current_pos)

        # 1. ВСЕГДА стреляем если видим врага и можем
        if visible_enemies and self.shoot_attempts < 2:
            enemy_x, enemy_y = visible_enemies[0]

            # Проверяем, можем ли стрелять прямо сейчас
            if self.can_shoot_now(my_x, my_y, my_direction, enemy_x, enemy_y, walls):
                self.shoot_attempts += 1
                self.last_action = "shoot"
                self.action_repeat = 0
                return "shoot"

            # Если не можем стрелять, поворачиваемся к врагу
            self.shoot_attempts = 0
            turn_action = self.turn_to_enemy(my_x, my_y, enemy_x, enemy_y, my_direction)
            if turn_action:
                self.last_action = turn_action
                self.action_repeat = 0
                return turn_action

        self.shoot_attempts = 0

        # 2. Проверяем здоровье
        health_ratio = health / max_health
        if health_ratio < self.health_threshold and known_medkits:
            # Идем к ближайшей аптечке
            action = self.go_to_nearest_medkit(my_x, my_y, known_medkits, walls)
            if action and action != self.last_action:
                self.last_action = action
                self.action_repeat = 0
                return action

        # 3. Движение - ВСЕГДА делаем ход
        action = self.get_movement_action(my_x, my_y, walls)

        # Избегаем повторения одного действия слишком много раз
        if action == self.last_action:
            self.action_repeat += 1
            if self.action_repeat > 2:
                # Меняем действие если зациклились
                action = self.get_alternative_action(my_x, my_y, walls, action)
                self.action_repeat = 0
        else:
            self.action_repeat = 0

        self.last_action = action
        return action

    def can_shoot_now(self, my_x, my_y, my_direction, enemy_x, enemy_y, walls):
        """Проверяет, можно ли выстрелить прямо сейчас"""
        # Получаем текущее направление
        current_dir = self.get_direction_name(my_direction)

        # Проверяем, что враг на той же линии
        if current_dir == "right" and enemy_y == my_y and enemy_x > my_x:
            return self.has_line_of_sight(my_x, my_y, enemy_x, enemy_y, walls)
        elif current_dir == "left" and enemy_y == my_y and enemy_x < my_x:
            return self.has_line_of_sight(my_x, my_y, enemy_x, enemy_y, walls)
        elif current_dir == "down" and enemy_x == my_x and enemy_y > my_y:
            return self.has_line_of_sight(my_x, my_y, enemy_x, enemy_y, walls)
        elif current_dir == "up" and enemy_x == my_x and enemy_y < my_y:
            return self.has_line_of_sight(my_x, my_y, enemy_x, enemy_y, walls)

        return False

    def turn_to_enemy(self, my_x, my_y, enemy_x, enemy_y, current_direction):
        """Поворачивается к врагу"""
        dx = enemy_x - my_x
        dy = enemy_y - my_y

        current_dir = self.get_direction_name(current_direction)

        # Определяем нужное направление
        if abs(dx) > abs(dy):
            if dx > 0 and current_dir != "right":
                return "move_right"
            elif dx < 0 and current_dir != "left":
                return "move_left"
        else:
            if dy > 0 and current_dir != "down":
                return "move_down"
            elif dy < 0 and current_dir != "up":
                return "move_up"

        # Если уже смотрим в нужную сторону, но не можем стрелять
        # (есть препятствие), двигаемся для лучшей позиции
        return self.get_safe_move(my_x, my_y, walls=None)  # walls передаются позже

    def go_to_nearest_medkit(self, my_x, my_y, known_medkits, walls):
        """Двигается к ближайшей аптечке"""
        if not known_medkits:
            return None

        # Находим ближайшую аптечку
        closest = None
        min_dist = float('inf')

        for medkit_x, medkit_y in known_medkits:
            dist = abs(my_x - medkit_x) + abs(my_y - medkit_y)
            if dist < min_dist:
                min_dist = dist
                closest = (medkit_x, medkit_y)

        if closest:
            # Простое движение к цели
            target_x, target_y = closest
            return self.move_towards(my_x, my_y, target_x, target_y, walls)

        return None

    def get_movement_action(self, my_x, my_y, walls):
        """Получает действие для движения"""
        # Пробуем найти непосещенную клетку
        unvisited = self.get_unvisited_directions(my_x, my_y, walls)

        if unvisited:
            return random.choice(unvisited)

        # Все соседние клетки посещены - двигаемся в случайном направлении
        possible = self.get_possible_directions(my_x, my_y, walls)

        if possible:
            return random.choice(possible)

        # Не можем двигаться - стреляем (может разрушить стену)
        return "shoot"

    def get_unvisited_directions(self, my_x, my_y, walls):
        """Возвращает направления к непосещенным клеткам"""
        directions = []

        # Вверх
        if self.can_move_to(my_x, my_y - 1, walls) and (my_x, my_y - 1) not in self.visited:
            directions.append("move_up")
        # Вниз
        if self.can_move_to(my_x, my_y + 1, walls) and (my_x, my_y + 1) not in self.visited:
            directions.append("move_down")
        # Влево
        if self.can_move_to(my_x - 1, my_y, walls) and (my_x - 1, my_y) not in self.visited:
            directions.append("move_left")
        # Вправо
        if self.can_move_to(my_x + 1, my_y, walls) and (my_x + 1, my_y) not in self.visited:
            directions.append("move_right")

        return directions

    def get_possible_directions(self, my_x, my_y, walls):
        """Возвращает все возможные направления для движения"""
        directions = []

        if self.can_move_to(my_x, my_y - 1, walls):
            directions.append("move_up")
        if self.can_move_to(my_x, my_y + 1, walls):
            directions.append("move_down")
        if self.can_move_to(my_x - 1, my_y, walls):
            directions.append("move_left")
        if self.can_move_to(my_x + 1, my_y, walls):
            directions.append("move_right")

        return directions

    def get_alternative_action(self, my_x, my_y, walls, current_action):
        """Получает альтернативное действие"""
        possible = self.get_possible_directions(my_x, my_y, walls)

        if not possible:
            return "shoot"

        # Убираем текущее действие из возможных
        if current_action in possible:
            possible.remove(current_action)

        if possible:
            return random.choice(possible)

        # Если нет альтернатив, оставляем текущее
        return current_action

    def get_safe_move(self, my_x, my_y, walls):
        """Безопасное движение (заглушка)"""
        possible = self.get_possible_directions(my_x, my_y, walls)
        if possible:
            return random.choice(possible)
        return "shoot"

    def move_towards(self, my_x, my_y, target_x, target_y, walls):
        """Движение к цели"""
        dx = target_x - my_x
        dy = target_y - my_y

        # Приоритет по большей оси
        if abs(dx) > abs(dy):
            if dx > 0 and self.can_move_to(my_x + 1, my_y, walls):
                return "move_right"
            elif dx < 0 and self.can_move_to(my_x - 1, my_y, walls):
                return "move_left"
            # Если горизонталь недоступна, пробуем вертикаль
            if dy > 0 and self.can_move_to(my_x, my_y + 1, walls):
                return "move_down"
            elif dy < 0 and self.can_move_to(my_x, my_y - 1, walls):
                return "move_up"
        else:
            if dy > 0 and self.can_move_to(my_x, my_y + 1, walls):
                return "move_down"
            elif dy < 0 and self.can_move_to(my_x, my_y - 1, walls):
                return "move_up"
            # Если вертикаль недоступна, пробуем горизонталь
            if dx > 0 and self.can_move_to(my_x + 1, my_y, walls):
                return "move_right"
            elif dx < 0 and self.can_move_to(my_x - 1, my_y, walls):
                return "move_left"

        # Если не можем двигаться к цели, ищем любое движение
        possible = self.get_possible_directions(my_x, my_y, walls)
        if possible:
            return random.choice(possible)

        return "shoot"

    def can_move_to(self, x, y, walls):
        """Проверяет, можно ли двигаться в клетку"""
        # Границы карты
        if x < 0 or x >= 12 or y < 0 or y >= 12:
            return False

        # Стены
        for wall in walls:
            if len(wall) >= 2 and wall[0] == x and wall[1] == y:
                return False

        return True

    def has_line_of_sight(self, x1, y1, x2, y2, walls):
        """Проверяет прямую видимость"""
        # Горизонтально
        if y1 == y2:
            start = min(x1, x2) + 1
            end = max(x1, x2)
            for x in range(start, end):
                if any(w[0] == x and w[1] == y1 for w in walls):
                    return False
            return True

        # Вертикально
        if x1 == x2:
            start = min(y1, y2) + 1
            end = max(y1, y2)
            for y in range(start, end):
                if any(w[0] == x1 and w[1] == y for w in walls):
                    return False
            return True

        return False

    def get_direction_name(self, direction):
        """Преобразует направление в строку"""
        if hasattr(direction, 'x'):
            x, y = direction.x, direction.y
        elif isinstance(direction, tuple) or isinstance(direction, list):
            x, y = direction[0], direction[1]
        else:
            return "right"  # По умолчанию

        if x > 0.5:
            return "right"
        elif x < -0.5:
            return "left"
        elif y > 0.5:
            return "down"
        elif y < -0.5:
            return "up"

        return "right"