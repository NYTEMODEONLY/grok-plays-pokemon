import os
import time
import logging
from pyboy import PyBoy
from pyboy.utils import WindowEvent
import numpy as np
from PIL import Image
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pokemon Red/Blue/Yellow Memory Addresses (RAM)
# These are well-documented addresses for Gen 1 Pokemon games
MEMORY_ADDRESSES = {
    # Party Pokemon (6 Pokemon max, each entry is 44 bytes)
    "party_count": 0xD163,  # Number of Pokemon in party (0-6)
    "party_species": 0xD164,  # Species IDs of party Pokemon (6 bytes)
    "party_data": 0xD16B,  # Start of party Pokemon data

    # Individual Pokemon data offsets (within each 44-byte Pokemon struct)
    "pokemon_species": 0,
    "pokemon_hp": 1,  # 2 bytes (current HP)
    "pokemon_level": 33,
    "pokemon_max_hp": 34,  # 2 bytes

    # Player info
    "player_name": 0xD158,  # 11 bytes
    "money": 0xD347,  # 3 bytes (BCD encoded)
    "badges": 0xD356,  # 1 byte (bit flags)

    # Location
    "map_id": 0xD35E,  # Current map ID
    "player_x": 0xD362,  # Player X position
    "player_y": 0xD361,  # Player Y position

    # Battle state
    "battle_type": 0xD057,  # 0 = no battle, 1 = wild, 2 = trainer
    "enemy_pokemon_species": 0xCFE5,
    "enemy_pokemon_level": 0xCFF3,
    "enemy_pokemon_hp": 0xCFE6,  # 2 bytes

    # Items
    "bag_items_count": 0xD31D,
    "bag_items": 0xD31E,  # Item ID, quantity pairs
}

# Pokemon species names (index 0 is unused, species start at 1)
POKEMON_NAMES = {
    0: "???", 1: "RHYDON", 2: "KANGASKHAN", 3: "NIDORAN♂", 4: "CLEFAIRY",
    5: "SPEAROW", 6: "VOLTORB", 7: "NIDOKING", 8: "SLOWBRO", 9: "IVYSAUR",
    10: "EXEGGUTOR", 11: "LICKITUNG", 12: "EXEGGCUTE", 13: "GRIMER", 14: "GENGAR",
    15: "NIDORAN♀", 16: "NIDOQUEEN", 17: "CUBONE", 18: "RHYHORN", 19: "LAPRAS",
    20: "ARCANINE", 21: "MEW", 22: "GYARADOS", 23: "SHELLDER", 24: "TENTACOOL",
    25: "GASTLY", 26: "SCYTHER", 27: "STARYU", 28: "BLASTOISE", 29: "PINSIR",
    30: "TANGELA", 33: "GROWLITHE", 34: "ONIX", 35: "FEAROW", 36: "PIDGEY",
    37: "SLOWPOKE", 38: "KADABRA", 39: "GRAVELER", 40: "CHANSEY", 41: "MACHOKE",
    42: "MR.MIME", 43: "HITMONLEE", 44: "HITMONCHAN", 45: "ARBOK", 46: "PARASECT",
    47: "PSYDUCK", 48: "DROWZEE", 49: "GOLEM", 51: "MAGMAR", 52: "ELECTABUZZ",
    53: "MAGNETON", 54: "KOFFING", 56: "MANKEY", 57: "SEEL", 58: "DIGLETT",
    59: "TAUROS", 61: "FARFETCH'D", 62: "VENONAT", 63: "DRAGONITE", 65: "DODUO",
    66: "POLIWAG", 67: "JYNX", 68: "MOLTRES", 69: "ARTICUNO", 70: "ZAPDOS",
    71: "DITTO", 72: "MEOWTH", 73: "KRABBY", 75: "VULPIX", 76: "NINETALES",
    77: "PIKACHU", 78: "RAICHU", 80: "DRATINI", 81: "DRAGONAIR", 82: "KABUTO",
    83: "KABUTOPS", 84: "HORSEA", 85: "SEADRA", 88: "SANDSHREW", 89: "SANDSLASH",
    90: "OMANYTE", 91: "OMASTAR", 92: "JIGGLYPUFF", 93: "WIGGLYTUFF",
    94: "EEVEE", 95: "FLAREON", 96: "JOLTEON", 97: "VAPOREON", 98: "MACHOP",
    99: "ZUBAT", 100: "EKANS", 101: "PARAS", 102: "POLIWHIRL", 103: "POLIWRATH",
    104: "WEEDLE", 105: "KAKUNA", 106: "BEEDRILL", 108: "DODRIO", 109: "PRIMEAPE",
    110: "DUGTRIO", 111: "VENOMOTH", 112: "DEWGONG", 115: "CATERPIE",
    116: "METAPOD", 117: "BUTTERFREE", 118: "MACHAMP", 120: "GOLDUCK",
    121: "HYPNO", 122: "GOLBAT", 123: "MEWTWO", 124: "SNORLAX", 125: "MAGIKARP",
    127: "MUK", 128: "KINGLER", 129: "CLOYSTER", 131: "ELECTRODE", 132: "CLEFABLE",
    133: "WEEZING", 134: "PERSIAN", 135: "MAROWAK", 137: "HAUNTER", 138: "ABRA",
    139: "ALAKAZAM", 140: "PIDGEOTTO", 141: "PIDGEOT", 142: "STARMIE",
    143: "BULBASAUR", 144: "VENUSAUR", 145: "TENTACRUEL", 147: "GOLDEEN",
    148: "SEAKING", 152: "PONYTA", 153: "RAPIDASH", 154: "RATTATA", 155: "RATICATE",
    156: "NIDORINO", 157: "NIDORINA", 158: "GEODUDE", 159: "PORYGON", 160: "AERODACTYL",
    162: "MAGNEMITE", 165: "CHARMANDER", 166: "SQUIRTLE", 167: "CHARMELEON",
    168: "WARTORTLE", 169: "CHARIZARD", 171: "ODDISH", 172: "GLOOM",
    173: "VILEPLUME", 174: "BELLSPROUT", 175: "WEEPINBELL", 176: "VICTREEBEL",
}

# Map IDs to location names
MAP_NAMES = {
    0: "PALLET TOWN", 1: "VIRIDIAN CITY", 2: "PEWTER CITY", 3: "CERULEAN CITY",
    4: "LAVENDER TOWN", 5: "VERMILION CITY", 6: "CELADON CITY", 7: "FUCHSIA CITY",
    8: "CINNABAR ISLAND", 9: "INDIGO PLATEAU", 10: "SAFFRON CITY",
    12: "ROUTE 1", 13: "ROUTE 2", 14: "ROUTE 3", 15: "ROUTE 4",
    16: "ROUTE 5", 17: "ROUTE 6", 18: "ROUTE 7", 19: "ROUTE 8",
    20: "ROUTE 9", 21: "ROUTE 10", 22: "ROUTE 11", 23: "ROUTE 12",
    24: "ROUTE 13", 25: "ROUTE 14", 26: "ROUTE 15", 27: "ROUTE 16",
    28: "ROUTE 17", 29: "ROUTE 18", 30: "ROUTE 19", 31: "ROUTE 20",
    32: "ROUTE 21", 33: "ROUTE 22", 34: "ROUTE 23", 35: "ROUTE 24",
    36: "ROUTE 25", 37: "PLAYER'S HOUSE 1F", 38: "PLAYER'S HOUSE 2F",
    39: "RIVAL'S HOUSE", 40: "OAK'S LAB", 41: "POKEMON CENTER",
    42: "POKEMART", 43: "VIRIDIAN SCHOOL", 44: "VIRIDIAN HOUSE",
    51: "PEWTER MUSEUM 1F", 52: "PEWTER MUSEUM 2F", 53: "PEWTER GYM",
    54: "CERULEAN GYM", 55: "VERMILION GYM", 56: "CELADON GYM",
    57: "FUCHSIA GYM", 58: "SAFFRON GYM", 59: "CINNABAR GYM",
    65: "MT. MOON", 66: "MT. MOON", 82: "ROCK TUNNEL",
    83: "POWER PLANT", 88: "POKEMON TOWER 1F", 89: "POKEMON TOWER 2F",
    108: "SEAFOAM ISLANDS", 141: "POKEMON MANSION", 174: "VICTORY ROAD",
    194: "CERULEAN CAVE",
}

# Item names
ITEM_NAMES = {
    1: "MASTER BALL", 2: "ULTRA BALL", 3: "GREAT BALL", 4: "POKE BALL",
    5: "TOWN MAP", 6: "BICYCLE", 7: "?????", 8: "SAFARI BALL",
    9: "POKEDEX", 10: "MOON STONE", 11: "ANTIDOTE", 12: "BURN HEAL",
    13: "ICE HEAL", 14: "AWAKENING", 15: "PARLYZ HEAL", 16: "FULL RESTORE",
    17: "MAX POTION", 18: "HYPER POTION", 19: "SUPER POTION", 20: "POTION",
    21: "BOULDERBADGE", 22: "CASCADEBADGE", 23: "THUNDERBADGE", 24: "RAINBOWBADGE",
    25: "SOULBADGE", 26: "MARSHBADGE", 27: "VOLCANOBADGE", 28: "EARTHBADGE",
    29: "ESCAPE ROPE", 30: "REPEL", 31: "OLD AMBER", 32: "FIRE STONE",
    33: "THUNDER STONE", 34: "WATER STONE", 35: "HP UP", 36: "PROTEIN",
    37: "IRON", 38: "CARBOS", 39: "CALCIUM", 40: "RARE CANDY",
    41: "DOME FOSSIL", 42: "HELIX FOSSIL", 43: "SECRET KEY", 44: "?????",
    45: "BIKE VOUCHER", 46: "X ACCURACY", 47: "LEAF STONE", 48: "CARD KEY",
    49: "NUGGET", 50: "PP UP", 51: "POKE DOLL", 52: "FULL HEAL",
    53: "REVIVE", 54: "MAX REVIVE", 55: "GUARD SPEC.", 56: "SUPER REPEL",
    57: "MAX REPEL", 58: "DIRE HIT", 59: "COIN", 60: "FRESH WATER",
    61: "SODA POP", 62: "LEMONADE", 63: "S.S. TICKET", 64: "GOLD TEETH",
    65: "X ATTACK", 66: "X DEFEND", 67: "X SPEED", 68: "X SPECIAL",
    69: "COIN CASE", 70: "OAK'S PARCEL", 71: "ITEMFINDER", 72: "SILPH SCOPE",
    73: "POKE FLUTE", 74: "LIFT KEY", 75: "EXP. ALL", 76: "OLD ROD",
    77: "GOOD ROD", 78: "SUPER ROD", 79: "PP UP", 80: "ETHER",
    81: "MAX ETHER", 82: "ELIXER", 83: "MAX ELIXER",
}

# Define button mapping
BUTTON_MAP = {
    "a": WindowEvent.PRESS_BUTTON_A,
    "b": WindowEvent.PRESS_BUTTON_B,
    "start": WindowEvent.PRESS_BUTTON_START,
    "select": WindowEvent.PRESS_BUTTON_SELECT,
    "up": WindowEvent.PRESS_ARROW_UP,
    "down": WindowEvent.PRESS_ARROW_DOWN,
    "left": WindowEvent.PRESS_ARROW_LEFT,
    "right": WindowEvent.PRESS_ARROW_RIGHT
}

BUTTON_RELEASE_MAP = {
    "a": WindowEvent.RELEASE_BUTTON_A,
    "b": WindowEvent.RELEASE_BUTTON_B,
    "start": WindowEvent.RELEASE_BUTTON_START,
    "select": WindowEvent.RELEASE_BUTTON_SELECT,
    "up": WindowEvent.RELEASE_ARROW_UP,
    "down": WindowEvent.RELEASE_ARROW_DOWN,
    "left": WindowEvent.RELEASE_ARROW_LEFT,
    "right": WindowEvent.RELEASE_ARROW_RIGHT
}

class PokemonEmulator:
    def __init__(self, rom_path, rom_name=None):
        """Initialize the Pokemon emulator with the specified ROM."""
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM file not found: {rom_path}")

        logger.info(f"Initializing emulator with ROM: {rom_path}")
        self.rom_path = rom_path
        self.rom_name = rom_name or "Unknown"
        self.pyboy = PyBoy(rom_path, game_wrapper=True)
        self.game = self.pyboy.game_wrapper()
        self.screen_buffer = []
        self.last_screenshot = None
        self.frame_count = 0
        self.is_running = False

        # Game state tracking
        self.current_state = {
            "pokemon_team": [],
            "items": [],
            "location": "Unknown",
            "badges": 0,
            "money": 0,
            "current_pokemon": None,
            "rom_version": self.rom_name
        }

        logger.info(f"Emulator initialized successfully with {self.rom_name}")

    def start(self):
        """Start the emulator."""
        if not self.is_running:
            logger.info("Starting emulator")
            self.is_running = True
    
    def stop(self):
        """Stop the emulator."""
        if self.is_running:
            logger.info("Stopping emulator")
            self.is_running = False
            self.pyboy.stop()
    
    def get_screenshot(self):
        """Get the current screenshot of the game."""
        screen_image = self.pyboy.screen_image()
        self.last_screenshot = screen_image
        return screen_image
    
    def get_screen_ndarray(self):
        """Get the current screen as a numpy array."""
        return np.array(self.get_screenshot())
    
    def save_screenshot(self, path):
        """Save the current screenshot to a file."""
        self.get_screenshot().save(path)
        logger.info(f"Screenshot saved to {path}")
    
    def execute_action(self, action):
        """Execute a game action (button press)."""
        if action not in BUTTON_MAP:
            logger.warning(f"Unknown action: {action}")
            return False
        
        logger.info(f"Executing action: {action}")
        self.pyboy.send_input(BUTTON_MAP[action])
        self.tick(5)  # Small delay after button press
        self.pyboy.send_input(BUTTON_RELEASE_MAP[action])
        self.tick(5)  # Small delay after button release
        return True
    
    def execute_sequence(self, actions, delay=10):
        """Execute a sequence of actions with delays between them."""
        logger.info(f"Executing sequence: {actions}")
        results = []
        for action in actions:
            result = self.execute_action(action)
            results.append(result)
            self.tick(delay)
        return results
    
    def tick(self, frames=1):
        """Advance the emulator by a number of frames."""
        for _ in range(frames):
            self.pyboy.tick()
            self.frame_count += 1

    def run_for_seconds(self, seconds):
        """Run the emulator for a specified number of seconds."""
        fps = 60
        frames = int(seconds * fps)
        logger.info(f"Running for {seconds} seconds ({frames} frames)")
        self.tick(frames)
    
    def _read_memory(self, address):
        """Read a single byte from game memory."""
        try:
            return self.pyboy.memory[address]
        except Exception as e:
            logger.warning(f"Failed to read memory at {hex(address)}: {e}")
            return 0

    def _read_memory_word(self, address):
        """Read a 16-bit word from game memory (little-endian)."""
        try:
            low = self.pyboy.memory[address]
            high = self.pyboy.memory[address + 1]
            return (high << 8) | low
        except Exception as e:
            logger.warning(f"Failed to read word at {hex(address)}: {e}")
            return 0

    def _read_bcd_money(self, address):
        """Read BCD-encoded money value (3 bytes)."""
        try:
            b1 = self.pyboy.memory[address]
            b2 = self.pyboy.memory[address + 1]
            b3 = self.pyboy.memory[address + 2]
            # BCD decoding
            money = ((b1 >> 4) * 100000 + (b1 & 0xF) * 10000 +
                     (b2 >> 4) * 1000 + (b2 & 0xF) * 100 +
                     (b3 >> 4) * 10 + (b3 & 0xF))
            return money
        except Exception as e:
            logger.warning(f"Failed to read BCD money: {e}")
            return 0

    def _get_pokemon_name(self, species_id):
        """Get Pokemon name from species ID."""
        return POKEMON_NAMES.get(species_id, f"Pokemon #{species_id}")

    def _get_location_name(self, map_id):
        """Get location name from map ID."""
        return MAP_NAMES.get(map_id, f"Map #{map_id}")

    def _get_item_name(self, item_id):
        """Get item name from item ID."""
        return ITEM_NAMES.get(item_id, f"Item #{item_id}")

    def _count_badges(self, badge_byte):
        """Count number of badges from badge bit flags."""
        count = 0
        for i in range(8):
            if badge_byte & (1 << i):
                count += 1
        return count

    def update_game_state(self):
        """Update the game state by reading from game memory."""
        try:
            # Read party Pokemon
            party_count = self._read_memory(MEMORY_ADDRESSES["party_count"])
            party_count = min(party_count, 6)  # Max 6 Pokemon

            pokemon_team = []
            if party_count > 0:
                for i in range(party_count):
                    # Read species from party species list
                    species_id = self._read_memory(MEMORY_ADDRESSES["party_species"] + i)

                    # Read Pokemon data (44 bytes per Pokemon)
                    base_addr = MEMORY_ADDRESSES["party_data"] + (i * 44)

                    # Read HP (2 bytes at offset 1)
                    current_hp = self._read_memory_word(base_addr + 1)
                    # Read level (1 byte at offset 33)
                    level = self._read_memory(base_addr + 33)
                    # Read max HP (2 bytes at offset 34)
                    max_hp = self._read_memory_word(base_addr + 34)

                    # Sanity check values
                    if level == 0:
                        level = 1
                    if max_hp == 0:
                        max_hp = 1
                    if current_hp > max_hp:
                        current_hp = max_hp

                    pokemon_name = self._get_pokemon_name(species_id)

                    pokemon_team.append({
                        "name": pokemon_name,
                        "level": level,
                        "hp": current_hp,
                        "max_hp": max_hp,
                        "species_id": species_id
                    })

            # Read location
            map_id = self._read_memory(MEMORY_ADDRESSES["map_id"])
            location = self._get_location_name(map_id)

            # Read badges
            badge_byte = self._read_memory(MEMORY_ADDRESSES["badges"])
            badges = self._count_badges(badge_byte)

            # Read money
            money = self._read_bcd_money(MEMORY_ADDRESSES["money"])

            # Read items
            items = []
            item_count = self._read_memory(MEMORY_ADDRESSES["bag_items_count"])
            item_count = min(item_count, 20)  # Reasonable limit

            for i in range(item_count):
                item_addr = MEMORY_ADDRESSES["bag_items"] + (i * 2)
                item_id = self._read_memory(item_addr)
                item_qty = self._read_memory(item_addr + 1)

                if item_id > 0 and item_id != 0xFF:
                    items.append({
                        "name": self._get_item_name(item_id),
                        "count": item_qty,
                        "id": item_id
                    })

            # Check battle state
            battle_type = self._read_memory(MEMORY_ADDRESSES["battle_type"])
            in_battle = battle_type > 0

            # Build enemy info if in battle
            enemy_info = None
            if in_battle:
                enemy_species = self._read_memory(MEMORY_ADDRESSES["enemy_pokemon_species"])
                enemy_level = self._read_memory(MEMORY_ADDRESSES["enemy_pokemon_level"])
                enemy_hp = self._read_memory_word(MEMORY_ADDRESSES["enemy_pokemon_hp"])
                enemy_info = {
                    "name": self._get_pokemon_name(enemy_species),
                    "level": enemy_level,
                    "hp": enemy_hp,
                    "battle_type": "wild" if battle_type == 1 else "trainer"
                }

            # Update state
            self.current_state = {
                "pokemon_team": pokemon_team,
                "items": items,
                "location": location,
                "badges": badges,
                "money": money,
                "current_pokemon": pokemon_team[0]["name"] if pokemon_team else None,
                "rom_version": self.rom_name,
                "in_battle": in_battle,
                "enemy": enemy_info,
                "map_id": map_id,
                "party_count": party_count
            }

            logger.debug(f"Game state updated: {location}, {party_count} Pokemon, {badges} badges")

        except Exception as e:
            logger.error(f"Error updating game state: {e}")
            # Return minimal fallback state
            self.current_state = {
                "pokemon_team": [],
                "items": [],
                "location": "Unknown",
                "badges": 0,
                "money": 0,
                "current_pokemon": None,
                "rom_version": self.rom_name,
                "in_battle": False,
                "enemy": None
            }

        return self.current_state
    
    def get_state(self):
        """Get the current game state."""
        self.update_game_state()
        return self.current_state
    
    def detect_game_screen(self):
        """Detect what screen we're currently on (battle, overworld, menu, etc.)."""
        try:
            # Check battle state
            battle_type = self._read_memory(MEMORY_ADDRESSES["battle_type"])
            if battle_type > 0:
                return "battle"

            # Check if in menu (there are various menu states we could check)
            # For now, default to overworld if not in battle
            return "overworld"

        except Exception as e:
            logger.warning(f"Error detecting screen: {e}")
            return "unknown"

    def is_in_battle(self):
        """Check if the game is currently in a battle."""
        try:
            battle_type = self._read_memory(MEMORY_ADDRESSES["battle_type"])
            return battle_type > 0
        except:
            return False

    def get_game_loop_frequency(self):
        """Return the target frequency for the game loop."""
        return 30  # 30 FPS 