"""Curated list of fictional character names for Fight Club team naming.

Each round, pairs of characters are randomly combined to form team names
like "Дедпул & Росомаха" or "По & Вчитель Шіфу".
"""

import random

# Characters from various movies, cartoons, and pop culture (Ukrainian names)
CHARACTERS = [
    # Кунг-фу Панда
    "По",
    "Тигриця",
    "Шіфу",
    "Гадюка",
    "Журавель",
    "Богомол",
    "Мавпа",
    "Уґвей",
    # Marvel
    "Дедпул",
    "Росомаха",
    "Людина-Павук",
    "Залізна Людина",
    "Тор",
    "Галк",
    "Чорна Вдова",
    "Соколине Око",
    "Капітан Америка",
    "Локі",
    "Ґрут",
    "Ракета",
    "Гамора",
    "Зоряний Лорд",
    "Дракс",
    "Червона Відьма",
    "Віжн",
    "Людина-Мураха",
    "Оса",
    "Чорна Пантера",
    "Доктор Стрендж",
    "Танос",
    # DC
    "Бетмен",
    "Супермен",
    "Диво-Жінка",
    "Флеш",
    "Аквамен",
    "Джокер",
    "Гарлі Квін",
    "Жінка-Кішка",
    "Робін",
    "Альфред",
    # Studio Ghibli
    "Тоторо",
    "Тіхіро",
    "Гаул",
    "Софі",
    "Кікі",
    "Поньо",
    "Мононоке",
    "Ашітака",
    "Кальцифер",
    "Безликий",
    # Disney/Pixar
    "Базз",
    "Вуді",
    "Немо",
    "Дорі",
    "Сімба",
    "Муфаса",
    "Ельза",
    "Моана",
    "Мауї",
    "Ремі",
    "Волл-І",
    "Єва",
    "Беймакс",
    "Стіч",
    "Рапунцель",
    "Меріда",
    "Мулан",
    "Аладдін",
    "Джин",
    "Рафікі",
    "Жасмін",
    # Володар Перснів
    "Ґандальф",
    "Араґорн",
    "Леґолас",
    "Ґімлі",
    "Фродо",
    "Семвайз",
    "Ґолум",
    "Саруман",
    "Боромір",
    "Еовін",
    # Гаррі Поттер
    "Дамблдор",
    "Герміона",
    "Добі",
    "Геґрід",
    "Снейп",
    "Луна",
    "МакҐонеґел",
    "Сіріус",
    "Гедвіґа",
    "Невіл",
    # Зоряні Війни
    "Йода",
    "Чубака",
    "Ган Соло",
    "Лея",
    "Обі-Ван",
    "R2-D2",
    "C-3PO",
    "Вейдер",
    "Мандалорець",
    "Ґроґу",
    # Шрек
    "Шрек",
    "Віслюк",
    "Фіона",
    "Кіт у чоботях",
    "Пряниковий Чоловічок",
    # Час Пригод / Мультики
    "Фінн",
    "Джейк",
    "Пікачу",
    "Скубі",
    "Шеґґі",
    "Том",
    "Джеррі",
    "Губка Боб",
    "Патрік",
    "Ґарфілд",
    "Оді",
    # Аніме
    "Ґоку",
    "Веджита",
    "Наруто",
    "Саске",
    "Луффі",
    "Зоро",
    "Танджіро",
    "Незуко",
    "Сайтама",
    "Ґенос",
    # Людина-Бензопила (Chainsaw Man)
    "Денджі",
    "Почіта",
    "Макіма",
    "Акі",
    "Павер",
    "Кобені",
    # Коханий у Франксі (Darling in the Franxx)
    "Зеро Ту",
    "Хіро",
    "Ічіґо",
    "Ґоро",
    # Коносуба (KonoSuba)
    "Казума",
    "Аква",
    "Меґумін",
    "Даркнес",
    # Смаколики Підземелля (Dungeon Meshi)
    "Лайос",
    "Марсіль",
    "Чілчак",
    "Сенші",
    # Ну, постривай! / Мультики
    "Вовк",
    "Заєць",
    "Лелік",
    "Болік",
    "Карлсон",
    "Малюк",
    "Кіт Леопольд",
    # Принцеса-наречена / Різне
    "Ініґо Монтоя",
    "Вестлі",
    "Зорро",
    "Джек Горобець",
    "Шурі",
    "Нео",
    "Морфеус",
    "Тріниті",
    "Аґент Сміт",
    # Різне
    "Шерлок",
    "Ватсон",
    "Індіана Джонс",
    "Марті МакФлай",
    "Док Браун",
    "Кетніс",
    "Оптімус Прайм",
    "Бамблбі",
    "Сонік",
    "Тейлз",
]


def generate_team_names(num_teams, used_names=None):
    """Generate unique team names by pairing random characters.

    Args:
        num_teams: Number of team names needed.
        used_names: Optional set of previously used names to avoid repeats.

    Returns:
        List of team name strings, e.g. ["Deadpool & Wolverine", "Panda & Sensei"]
    """
    if used_names is None:
        used_names = set()

    available = list(CHARACTERS)
    random.shuffle(available)

    names = []
    idx = 0

    while len(names) < num_teams and idx + 1 < len(available):
        char1 = available[idx]
        char2 = available[idx + 1]
        name = f"{char1} i {char2}"

        if name not in used_names:
            names.append(name)
            used_names.add(name)
        idx += 2

    # Fallback if we run out of unique character pairs
    fallback_idx = 1
    while len(names) < num_teams:
        name = f"Team Shuffle {fallback_idx}"
        if name not in used_names:
            names.append(name)
            used_names.add(name)
        fallback_idx += 1

    return names
