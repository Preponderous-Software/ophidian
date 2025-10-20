# UI/Gameplay Abstraction Architecture

## Overview

This document describes the architectural improvements made to decouple UI from gameplay logic, making it easy to support multiple UI implementations with minimal changes to core gameplay.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Ophidian                              │
│                   (Main Application)                         │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
            │                                 │
   ┌────────▼────────┐               ┌───────▼────────┐
   │   GUI Components │               │ Text UI Components│
   │   - Renderer     │               │ - TextRenderer  │
   │   - Menus        │               │ - Menu          │
   │   - Audio        │               │                 │
   └────────┬────────┘               └───────┬────────┘
            │                                 │
            │                                 │
   ┌────────▼────────┐               ┌───────▼────────┐
   │ GUIInputHandler │               │TextUIInputHandler│
   └────────┬────────┘               └───────┬────────┘
            │                                 │
            └─────────────┬───────────────────┘
                          │
                 ┌────────▼────────┐
                 │  InputHandler   │
                 │  (Abstract)     │
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │  GameEngine     │
                 │  (Core Logic)   │
                 └─────────────────┘
```

## Key Components

### 1. GameEngine (`src/game_engine.py`)

**Purpose**: Contains all core gameplay logic independent of UI.

**Responsibilities**:
- Game state management (level, score, tick)
- Snake movement and collision detection
- Level progression
- Game save/load
- Pure gameplay update loop

**Key Methods**:
- `initialize_game()` - Set up new game
- `update()` - Update game state for one tick
- `handle_direction_input(direction)` - Process movement input
- `get_game_state()` - Return current state for rendering
- `save_game_state()` / load game state

**Benefits**:
- Testable without UI
- Reusable across different UIs
- Clear separation of concerns
- Easy to modify gameplay without touching UI

### 2. InputHandler Abstraction (`src/input/input_handler.py`)

**Purpose**: Abstract interface for input handling.

**Components**:
- `InputHandler` (ABC) - Abstract base class
- `InputAction` - Enumeration of game actions
- `DirectionMapper` - Maps actions to game directions

**Implementations**:
- `TextUIInputHandler` - Handles terminal keyboard input
- `GUIInputHandler` - Handles pygame keyboard input

**Benefits**:
- UI-agnostic input processing
- Easy to add new input methods (gamepad, network, etc.)
- Consistent action mapping across UIs

### 3. GameRenderer Abstraction (`src/graphics/game_renderer.py`)

**Purpose**: Abstract interface for rendering.

**Key Method**:
- `render_game(game_state)` - Render current game state

**Implementations**:
- `TextUIRenderer` - Renders to terminal
- GUI uses existing `Renderer` class (could be adapted later)

**Benefits**:
- Rendering logic separate from game logic
- Easy to add new renderers (web, mobile, etc.)
- Game engine doesn't know how it's being displayed

## Data Flow

### Gameplay Loop (Simplified)

```
User Input → InputHandler → InputAction → GameEngine → Game State
                                                            ↓
Renderer ← GameRenderer ← Get Game State ← GameEngine
```

### Detailed Flow

1. **Input Phase**:
   ```python
   action = input_handler.get_input()
   if action == InputAction.MOVE_UP:
       direction = DirectionMapper.action_to_direction(action)
       game_engine.handle_direction_input(direction)
   ```

2. **Update Phase**:
   ```python
   game_engine.update()  # Pure game logic, no UI
   ```

3. **Render Phase**:
   ```python
   game_state = game_engine.get_game_state()
   renderer.render_game(game_state)
   ```

## Benefits of This Architecture

### 1. **Separation of Concerns**
- Game logic in `GameEngine`
- Input handling in `InputHandler` implementations
- Rendering in `GameRenderer` implementations
- UI-specific code in UI modules

### 2. **Easy to Support New UIs**
To add a new UI (e.g., web-based):

1. Create new `WebInputHandler(InputHandler)`
2. Create new `WebRenderer(GameRenderer)`
3. Initialize in `Ophidian.__init__()` with `use_web_ui` flag
4. **No changes to GameEngine needed!**

### 3. **Maintainability**
- Gameplay changes don't require UI updates
- UI changes don't risk breaking gameplay
- Each component can be tested independently
- Clear interfaces between components

### 4. **Testability**
```python
# Test gameplay without any UI
engine = GameEngine(config)
engine.initialize_game()
engine.handle_direction_input(DirectionMapper.UP)
engine.update()
assert engine.level == 1
```

### 5. **Code Reuse**
- Same `GameEngine` for all UIs
- Same input action definitions
- Shared game state structure

## Backward Compatibility

The refactored `Ophidian` class maintains backward compatibility through:

1. **Property Delegates**: Old attributes delegate to `GameEngine`
   ```python
   @property
   def level(self):
       return self.game_engine.level
   ```

2. **Existing Method Signatures**: Public methods maintain same signatures
3. **Gradual Migration**: Old code paths still work during transition

## Future Enhancements

With this architecture, these additions become trivial:

1. **Network Multiplayer**: Add `NetworkInputHandler`
2. **AI Player**: Add `AIInputHandler`
3. **Replay System**: Record/playback `InputAction` sequences
4. **Mobile UI**: Add `TouchInputHandler` and `MobileRenderer`
5. **Web UI**: Add `WebSocketInputHandler` and `CanvasRenderer`
6. **Testing**: Mock `InputHandler` for automated gameplay testing

## Example: Adding a New UI

```python
# 1. Create input handler
class CustomInputHandler(InputHandler):
    def get_input(self, timeout=None):
        # Custom input logic
        return action
    
    def cleanup(self):
        # Cleanup logic
        pass

# 2. Create renderer
class CustomRenderer(GameRenderer):
    def render_game(self, game_state):
        # Custom rendering logic
        pass
    
    def cleanup(self):
        pass

# 3. Use in Ophidian
def _initialize_custom_ui(self):
    self.custom_input = CustomInputHandler(...)
    self.custom_renderer = CustomRenderer(...)

# 4. Add game loop
def run_custom_game_loop(self):
    game_state = self.game_engine.get_game_state()
    self.custom_renderer.render_game(game_state)
    
    action = self.custom_input.get_input()
    if action in movement_actions:
        direction = DirectionMapper.action_to_direction(action)
        self.game_engine.handle_direction_input(direction)
    
    self.game_engine.update()
```

## Conclusion

This architecture successfully decouples UI from gameplay, making the codebase more maintainable, testable, and extensible. Adding new UI implementations or modifying gameplay logic are now independent operations that don't affect each other.
