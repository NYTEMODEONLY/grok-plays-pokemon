# Game State Tracking

This document provides information about the game state tracking in Grok Plays Pokémon, including how game data is extracted from the emulator and how it could be enhanced in the future.

## Current Implementation

The current implementation in `emulator.py` uses placeholder data for the game state. In a full implementation, you would read specific memory locations in the Game Boy emulator to extract actual game state.

### Game State Structure

The game state object has the following structure:

```json
{
  "pokemon_team": [
    {
      "name": "SQUIRTLE",
      "level": 5,
      "hp": 20,
      "max_hp": 20
    }
  ],
  "items": [
    {
      "name": "Potion",
      "count": 1
    },
    {
      "name": "Poké Ball",
      "count": 5
    }
  ],
  "location": "PALLET TOWN",
  "badges": 0,
  "money": 3000,
  "current_pokemon": "SQUIRTLE"
}
```

## Reading Memory in Pokémon Red

Pokémon Red stores game data in specific memory locations that can be read using PyBoy's memory access methods. Here's how you might implement real memory reading for different game states:

### Accessing Memory with PyBoy

```python
# Read a single byte from memory
value = self.pyboy.get_memory_value(address)

# Read multiple bytes
values = [self.pyboy.get_memory_value(address + i) for i in range(length)]
```

### Pokémon Team Data

In Pokémon Red, the player's Pokémon team data starts at address `0xD16B` and each Pokémon entry is 44 bytes long.

```python
def get_pokemon_team(self):
    pokemon_team = []
    team_size = self.pyboy.get_memory_value(0xD163)
    
    for i in range(team_size):
        # Calculate the starting address for this Pokémon
        pokemon_address = 0xD16B + (i * 44)
        
        # Read species, level, HP, etc.
        species_id = self.pyboy.get_memory_value(pokemon_address)
        level = self.pyboy.get_memory_value(pokemon_address + 8)
        current_hp = self.pyboy.get_memory_value(pokemon_address + 1) * 256 + self.pyboy.get_memory_value(pokemon_address + 2)
        max_hp = self.pyboy.get_memory_value(pokemon_address + 3) * 256 + self.pyboy.get_memory_value(pokemon_address + 4)
        
        # Get Pokémon name (stored in a different location, indexed by species_id)
        name = self.get_pokemon_name(species_id)
        
        pokemon_team.append({
            "name": name,
            "level": level,
            "hp": current_hp,
            "max_hp": max_hp
        })
    
    return pokemon_team
```

### Items Inventory

The item inventory in Pokémon Red is stored starting at address `0xD31D`.

```python
def get_items(self):
    items = []
    item_count = self.pyboy.get_memory_value(0xD31C)
    
    for i in range(item_count):
        # Each item entry is 2 bytes: item ID and quantity
        item_address = 0xD31D + (i * 2)
        item_id = self.pyboy.get_memory_value(item_address)
        item_quantity = self.pyboy.get_memory_value(item_address + 1)
        
        # Get item name from item ID (would need to implement a lookup table)
        item_name = self.get_item_name(item_id)
        
        items.append({
            "name": item_name,
            "count": item_quantity
        })
    
    return items
```

### Player Location

The player's location (map ID) is stored at address `0xD35E`.

```python
def get_location(self):
    map_id = self.pyboy.get_memory_value(0xD35E)
    return self.get_map_name(map_id)  # Would need to implement a map name lookup
```

### Badges

The player's badges are stored as a bitfield at address `0xD356`.

```python
def get_badges(self):
    badge_bits = self.pyboy.get_memory_value(0xD356)
    badge_count = bin(badge_bits).count('1')
    return badge_count
```

### Money

The player's money is stored as a 3-byte BCD (Binary-Coded Decimal) number starting at address `0xD347`.

```python
def get_money(self):
    # Money is stored as BCD, need to convert
    byte1 = self.pyboy.get_memory_value(0xD347)
    byte2 = self.pyboy.get_memory_value(0xD348)
    byte3 = self.pyboy.get_memory_value(0xD349)
    
    # Convert from BCD
    digit1 = (byte1 >> 4) & 0xF
    digit2 = byte1 & 0xF
    digit3 = (byte2 >> 4) & 0xF
    digit4 = byte2 & 0xF
    digit5 = (byte3 >> 4) & 0xF
    digit6 = byte3 & 0xF
    
    money = digit1 * 100000 + digit2 * 10000 + digit3 * 1000 + digit4 * 100 + digit5 * 10 + digit6
    return money
```

### Battle State

You can detect if the game is in a battle by checking address `0xD057`, which contains the battle type.

```python
def is_in_battle(self):
    battle_type = self.pyboy.get_memory_value(0xD057)
    return battle_type != 0
```

## Implementation Notes

### Memory Map Resources

For a full implementation, you would need a comprehensive memory map of Pokémon Red. Several resources are available online:

- [Pokémon Red/Blue Memory Map](https://datacrystal.romhacking.net/wiki/Pok%C3%A9mon_Red/Blue:RAM_map)
- [Bulbapedia - Pokémon data structure in Generation I](https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_in_Generation_I)
- [GitHub repositories with Pokémon memory hacking tools](https://github.com/topics/pokemon-red)

### Validation and Error Handling

When reading memory, it's important to validate the data and handle errors:

```python
def get_pokemon_team(self):
    try:
        team_size = self.pyboy.get_memory_value(0xD163)
        if team_size < 0 or team_size > 6:
            logger.warning(f"Invalid team size detected: {team_size}, using default")
            return self.current_state["pokemon_team"]  # Return previous state
        
        # Read team data...
        
    except Exception as e:
        logger.error(f"Error reading Pokémon team data: {e}")
        return self.current_state["pokemon_team"]  # Return previous state
```

### Performance Considerations

Reading memory on every tick can be performance-intensive. Consider reading only at key moments or at reduced frequency:

```python
# In the game loop
if self.frame_count % 30 == 0:  # Every 30 frames (0.5 seconds at 60 FPS)
    self.update_game_state()
```

## Future Enhancements

### Machine Learning for Screen Recognition

For screens or states that are difficult to extract from memory, you could implement machine learning image recognition:

```python
def detect_battle_screen(self):
    # Capture screenshot
    screen = self.get_screen_ndarray()
    
    # Use a pre-trained model to classify the screen
    prediction = self.screen_classifier.predict(screen)
    
    return prediction == "battle_screen"
```

### Custom Game Progress Tracking

You could implement custom tracking for game progress, such as:

- Main quest progression
- Pokédex completion
- Trainer battles won/lost
- Wild encounters statistics

### Event-Based Updates

Instead of polling memory, you could implement event detection to trigger updates:

```python
def check_for_events(self):
    # Check if player entered a new area
    current_map = self.pyboy.get_memory_value(0xD35E)
    if current_map != self.last_known_map:
        self.last_known_map = current_map
        self.trigger_event("area_changed", self.get_map_name(current_map))
    
    # Check if Pokémon team changed
    team_size = self.pyboy.get_memory_value(0xD163)
    if team_size != self.last_team_size:
        self.last_team_size = team_size
        self.trigger_event("team_changed", self.get_pokemon_team())
    
    # Other events...
```

## Conclusion

While the current implementation uses placeholder data, a full implementation would use memory reading to extract the actual game state. This document provides a starting point for implementing such functionality. 