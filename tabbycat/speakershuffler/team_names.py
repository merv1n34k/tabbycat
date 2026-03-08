"""Curated list of fictional character names for Fight Club team naming.

Each round, pairs of characters are randomly combined to form team names
like "Deadpool & Wolverine" or "Panda & Sensei".
"""

import random

# Characters from various movies, cartoons, and pop culture
CHARACTERS = [
    # Kung Fu Panda
    "Po", "Tigress", "Shifu", "Viper", "Crane", "Mantis", "Monkey", "Oogway",
    # Marvel
    "Deadpool", "Wolverine", "Spider-Man", "Iron Man", "Thor", "Hulk",
    "Black Widow", "Hawkeye", "Captain America", "Loki", "Groot", "Rocket",
    "Gamora", "Star-Lord", "Drax", "Scarlet Witch", "Vision", "Ant-Man",
    "Wasp", "Black Panther", "Doctor Strange", "Thanos",
    # DC
    "Batman", "Superman", "Wonder Woman", "Flash", "Aquaman", "Joker",
    "Harley Quinn", "Catwoman", "Robin", "Alfred",
    # Studio Ghibli
    "Totoro", "Chihiro", "Howl", "Sophie", "Kiki", "Ponyo", "Mononoke",
    "Ashitaka", "Calcifer", "No-Face",
    # Disney/Pixar
    "Buzz", "Woody", "Nemo", "Dory", "Simba", "Mufasa", "Elsa", "Moana",
    "Maui", "Remy", "Wall-E", "Eve", "Baymax", "Stitch", "Rapunzel",
    "Merida", "Mulan", "Aladdin", "Genie", "Rafiki",
    # Lord of the Rings
    "Gandalf", "Aragorn", "Legolas", "Gimli", "Frodo", "Samwise", "Gollum",
    "Saruman", "Boromir", "Eowyn",
    # Harry Potter
    "Dumbledore", "Hermione", "Dobby", "Hagrid", "Snape", "Luna",
    "McGonagall", "Sirius", "Hedwig", "Neville",
    # Star Wars
    "Yoda", "Chewbacca", "Han Solo", "Leia", "Obi-Wan", "R2-D2",
    "C-3PO", "Vader", "Mandalorian", "Grogu",
    # Shrek
    "Shrek", "Donkey", "Fiona", "Puss in Boots", "Gingerbread Man",
    # Adventure Time / Cartoons
    "Finn", "Jake", "Pikachu", "Scooby", "Shaggy", "Tom", "Jerry",
    "SpongeBob", "Patrick", "Garfield", "Odie",
    # Anime
    "Goku", "Vegeta", "Naruto", "Sasuke", "Luffy", "Zoro", "Tanjiro",
    "Nezuko", "Saitama", "Genos",
    # The Princess Bride / Misc
    "Inigo Montoya", "Westley", "Zorro", "Jack Sparrow", "Shuri",
    "Neo", "Morpheus", "Trinity", "Agent Smith",
    # Miscellaneous
    "Sherlock", "Watson", "Indiana Jones", "Marty McFly", "Doc Brown",
    "Katniss", "Optimus Prime", "Bumblebee", "Sonic", "Tails",
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
        name = f"{char1} & {char2}"

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
