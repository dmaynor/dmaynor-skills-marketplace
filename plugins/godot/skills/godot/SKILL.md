---
name: godot
description: "Godot Engine 4.x game development skill for GDScript, scene architecture, physics, UI, shaders, and project structure. Use when creating games, prototypes, or interactive applications in Godot. Triggers on requests involving GDScript code, .tscn/.tres files, node hierarchies, signals, tweens, animations, tilemaps, collision layers, export variables, autoloads, or any Godot-specific development task."
---

# Godot Engine Development

Comprehensive skill for Godot 4.x game development. Covers GDScript, scene/node architecture, physics, UI, shaders, and deployment.

## Version

Target: **Godot 4.2+** (GDScript 2.0 syntax). For Godot 3.x, adapt syntax (e.g., `@export` → `export`, `@onready` → `onready`).

## Core Concepts

### Node Architecture

Everything in Godot is a **Node**. Scenes are trees of nodes saved as `.tscn` files.

```
Node (base class)
├── Node2D (2D positioning)
│   ├── Sprite2D, AnimatedSprite2D
│   ├── CharacterBody2D, RigidBody2D, StaticBody2D, Area2D
│   └── TileMap, Camera2D, ParallaxBackground
├── Node3D (3D positioning)
│   ├── MeshInstance3D, Camera3D
│   └── CharacterBody3D, RigidBody3D, Area3D
├── Control (UI elements)
│   ├── Button, Label, TextEdit, LineEdit
│   ├── Container, VBoxContainer, HBoxContainer
│   └── Panel, ScrollContainer, TabContainer
└── CanvasLayer (overlay layers for UI/HUD)
```

### Scene Composition Pattern

Prefer composition over inheritance. Create reusable scenes and instance them:

```
Player.tscn
├── CharacterBody2D (root)
│   ├── Sprite2D
│   ├── CollisionShape2D
│   ├── AnimationPlayer
│   └── HealthComponent.tscn (instanced)
```

## GDScript Fundamentals

### Script Template

```gdscript
class_name Player
extends CharacterBody2D
## Player controller handling movement and combat.

# Signals
signal health_changed(new_health: int)
signal died

# Exports (inspector-editable)
@export var move_speed: float = 200.0
@export var jump_force: float = -400.0
@export_range(0, 100) var max_health: int = 100

# Onready (resolved after _ready)
@onready var sprite: Sprite2D = $Sprite2D
@onready var anim_player: AnimationPlayer = $AnimationPlayer

# Private variables
var _health: int = max_health
var _gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")


func _ready() -> void:
    _health = max_health


func _physics_process(delta: float) -> void:
    _apply_gravity(delta)
    _handle_movement()
    move_and_slide()


func _apply_gravity(delta: float) -> void:
    if not is_on_floor():
        velocity.y += _gravity * delta


func _handle_movement() -> void:
    var direction := Input.get_axis("move_left", "move_right")
    velocity.x = direction * move_speed
    
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = jump_force


func take_damage(amount: int) -> void:
    _health = max(_health - amount, 0)
    health_changed.emit(_health)
    if _health == 0:
        died.emit()
```

### Type Hints

Always use explicit type hints:

```gdscript
var count: int = 0
var items: Array[String] = []
var data: Dictionary = {}

func calculate(value: float, multiplier: float = 1.0) -> float:
    return value * multiplier

func get_node_typed() -> Sprite2D:
    return $Sprite2D as Sprite2D
```

### Signals

```gdscript
# Declaration
signal item_collected(item_name: String, quantity: int)

# Emission
item_collected.emit("coin", 5)

# Connection (code)
player.item_collected.connect(_on_item_collected)

# Disconnection
player.item_collected.disconnect(_on_item_collected)

# One-shot connection
enemy.died.connect(_on_enemy_died, CONNECT_ONE_SHOT)

# Deferred connection (waits for idle frame)
button.pressed.connect(_on_pressed, CONNECT_DEFERRED)
```

### Common Patterns

#### State Machine

```gdscript
enum State { IDLE, RUN, JUMP, FALL, ATTACK }

var _state: State = State.IDLE

func _physics_process(delta: float) -> void:
    match _state:
        State.IDLE:
            _state_idle(delta)
        State.RUN:
            _state_run(delta)
        State.JUMP:
            _state_jump(delta)
        State.FALL:
            _state_fall(delta)
        State.ATTACK:
            _state_attack(delta)


func _change_state(new_state: State) -> void:
    if _state == new_state:
        return
    _exit_state(_state)
    _state = new_state
    _enter_state(new_state)
```

#### Object Pooling

```gdscript
class_name BulletPool
extends Node

@export var bullet_scene: PackedScene
@export var pool_size: int = 50

var _pool: Array[Node2D] = []

func _ready() -> void:
    for i in pool_size:
        var bullet := bullet_scene.instantiate() as Node2D
        bullet.set_process(false)
        bullet.visible = false
        add_child(bullet)
        _pool.append(bullet)


func get_bullet() -> Node2D:
    for bullet in _pool:
        if not bullet.visible:
            bullet.visible = true
            bullet.set_process(true)
            return bullet
    return null


func return_bullet(bullet: Node2D) -> void:
    bullet.set_process(false)
    bullet.visible = false
```

#### Resource-based Data

```gdscript
# weapon_data.gd
class_name WeaponData
extends Resource

@export var name: String
@export var damage: int
@export var attack_speed: float
@export var icon: Texture2D
```

Save as `.tres` file. Load with:

```gdscript
var sword: WeaponData = preload("res://resources/weapons/sword.tres")
```

## Physics

### Collision Layers

Configure in Project Settings → Physics → 2D/3D:
- Layer 1: Player
- Layer 2: Enemies  
- Layer 3: Environment
- Layer 4: Projectiles
- Layer 5: Pickups

```gdscript
# Set collision layer/mask in code
collision_layer = 1  # What this body IS
collision_mask = 6   # What this body DETECTS (binary: layers 2 + 4)

# Or use bit flags
set_collision_layer_value(1, true)
set_collision_mask_value(2, true)
```

### CharacterBody2D Movement

```gdscript
extends CharacterBody2D

@export var speed: float = 300.0
@export var acceleration: float = 1500.0
@export var friction: float = 1200.0

func _physics_process(delta: float) -> void:
    var input_dir := Input.get_vector("left", "right", "up", "down")
    
    if input_dir != Vector2.ZERO:
        velocity = velocity.move_toward(input_dir * speed, acceleration * delta)
    else:
        velocity = velocity.move_toward(Vector2.ZERO, friction * delta)
    
    move_and_slide()
```

### Area2D Detection

```gdscript
extends Area2D

func _ready() -> void:
    body_entered.connect(_on_body_entered)
    area_entered.connect(_on_area_entered)


func _on_body_entered(body: Node2D) -> void:
    if body.is_in_group("player"):
        body.take_damage(10)


func _on_area_entered(area: Area2D) -> void:
    if area.is_in_group("hitbox"):
        queue_free()
```

### Raycasting

```gdscript
func _physics_process(_delta: float) -> void:
    var space_state := get_world_2d().direct_space_state
    var query := PhysicsRayQueryParameters2D.create(
        global_position,
        global_position + Vector2(100, 0),
        collision_mask
    )
    query.exclude = [self]
    
    var result := space_state.intersect_ray(query)
    if result:
        print("Hit: ", result.collider.name, " at ", result.position)
```

## UI Development

### Control Node Anchors

```gdscript
# Full rect (fills parent)
anchor_left = 0.0
anchor_top = 0.0
anchor_right = 1.0
anchor_bottom = 1.0

# Center
anchor_left = 0.5
anchor_top = 0.5
anchor_right = 0.5
anchor_bottom = 0.5
```

### Theme Overrides

```gdscript
# In code
label.add_theme_color_override("font_color", Color.RED)
label.add_theme_font_size_override("font_size", 24)

# Remove override
label.remove_theme_color_override("font_color")
```

### Responsive UI Pattern

```gdscript
extends Control

func _ready() -> void:
    get_viewport().size_changed.connect(_on_viewport_resized)


func _on_viewport_resized() -> void:
    var viewport_size := get_viewport_rect().size
    # Adjust UI based on viewport_size
```

## Animation

### AnimationPlayer

```gdscript
@onready var anim: AnimationPlayer = $AnimationPlayer

func _ready() -> void:
    anim.animation_finished.connect(_on_animation_finished)


func play_attack() -> void:
    anim.play("attack")
    await anim.animation_finished
    anim.play("idle")
```

### Tweens

```gdscript
func fade_out(duration: float = 0.5) -> void:
    var tween := create_tween()
    tween.tween_property(self, "modulate:a", 0.0, duration)
    await tween.finished
    queue_free()


func shake(intensity: float = 10.0, duration: float = 0.2) -> void:
    var tween := create_tween()
    var original_pos := position
    
    for i in 10:
        var offset := Vector2(randf_range(-1, 1), randf_range(-1, 1)) * intensity
        tween.tween_property(self, "position", original_pos + offset, duration / 10)
    
    tween.tween_property(self, "position", original_pos, duration / 10)


func bounce_scale() -> void:
    var tween := create_tween()
    tween.set_trans(Tween.TRANS_ELASTIC)
    tween.set_ease(Tween.EASE_OUT)
    tween.tween_property(self, "scale", Vector2(1.2, 1.2), 0.1)
    tween.tween_property(self, "scale", Vector2.ONE, 0.3)
```

## Autoloads (Singletons)

Register in Project Settings → Autoload:

```gdscript
# game_manager.gd
extends Node

signal score_changed(new_score: int)
signal game_paused(is_paused: bool)

var score: int = 0:
    set(value):
        score = value
        score_changed.emit(score)

var is_paused: bool = false:
    set(value):
        is_paused = value
        get_tree().paused = value
        game_paused.emit(is_paused)


func add_score(amount: int) -> void:
    score += amount


func reset() -> void:
    score = 0
    is_paused = false
```

Access globally:

```gdscript
GameManager.add_score(100)
GameManager.is_paused = true
```

## Scene Management

```gdscript
# Change scene
get_tree().change_scene_to_file("res://scenes/level_2.tscn")

# Change scene (packed)
var next_scene: PackedScene = preload("res://scenes/level_2.tscn")
get_tree().change_scene_to_packed(next_scene)

# Reload current
get_tree().reload_current_scene()

# Quit
get_tree().quit()
```

### Scene Transitions

```gdscript
# transition_manager.gd (Autoload)
extends CanvasLayer

@onready var color_rect: ColorRect = $ColorRect

func change_scene(path: String) -> void:
    var tween := create_tween()
    tween.tween_property(color_rect, "color:a", 1.0, 0.3)
    await tween.finished
    get_tree().change_scene_to_file(path)
    tween = create_tween()
    tween.tween_property(color_rect, "color:a", 0.0, 0.3)
```

## Input Handling

### Input Map Actions

Define in Project Settings → Input Map, then use:

```gdscript
if Input.is_action_pressed("move_right"):
    velocity.x = speed

if Input.is_action_just_pressed("jump"):
    jump()

if Input.is_action_just_released("attack"):
    release_attack()

# Analog input (joystick/triggers)
var axis := Input.get_axis("move_left", "move_right")
var vector := Input.get_vector("left", "right", "up", "down")
```

### Input Events

```gdscript
func _input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        if event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
            shoot()
    
    if event is InputEventKey:
        if event.keycode == KEY_ESCAPE and event.pressed:
            toggle_pause()

func _unhandled_input(event: InputEvent) -> void:
    # Only receives events not handled by UI
    pass
```

## Saving/Loading

```gdscript
const SAVE_PATH := "user://save_game.json"

func save_game() -> void:
    var data := {
        "player_position": {
            "x": player.global_position.x,
            "y": player.global_position.y
        },
        "score": GameManager.score,
        "level": current_level
    }
    
    var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
    file.store_string(JSON.stringify(data))
    file.close()


func load_game() -> bool:
    if not FileAccess.file_exists(SAVE_PATH):
        return false
    
    var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
    var json := JSON.new()
    var error := json.parse(file.get_as_text())
    file.close()
    
    if error != OK:
        return false
    
    var data: Dictionary = json.data
    player.global_position = Vector2(
        data.player_position.x,
        data.player_position.y
    )
    GameManager.score = data.score
    return true
```

## Debugging

```gdscript
# Print
print("Value: ", value)
print_debug("Debug info")  # Includes stack trace
printerr("Error message")  # Prints to stderr

# Assertions (debug builds only)
assert(health > 0, "Health cannot be negative")

# Breakpoint
breakpoint  # Pauses execution in debugger

# Remote debugger
@tool  # Makes script run in editor
```

## Project Structure

```
project/
├── project.godot
├── scenes/
│   ├── main.tscn
│   ├── player/
│   │   ├── player.tscn
│   │   └── player.gd
│   ├── enemies/
│   ├── ui/
│   └── levels/
├── scripts/
│   ├── autoload/
│   │   ├── game_manager.gd
│   │   └── audio_manager.gd
│   ├── components/
│   │   ├── health_component.gd
│   │   └── hitbox_component.gd
│   └── resources/
│       └── weapon_data.gd
├── resources/
│   ├── weapons/
│   │   └── sword.tres
│   └── themes/
│       └── main_theme.tres
├── assets/
│   ├── sprites/
│   ├── audio/
│   ├── fonts/
│   └── shaders/
└── addons/
```

## Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Node not found | Use `@onready` or access in `_ready()`. Check node path. |
| Signal not connecting | Verify signal exists, check for typos, ensure node is in tree. |
| Physics not working | Check collision layers/masks. Verify collision shapes exist. |
| UI not receiving input | Check `mouse_filter` property. Ensure no blocking nodes above. |
| Exported variable not showing | Re-save script. Check `@export` syntax. |
| Animation not playing | Verify animation name. Check `AnimationPlayer` node path. |
| Scene change crashes | Use `call_deferred("change_scene_to_file", path)`. |

## References

- **GDScript Patterns**: See `references/gdscript_patterns.md` for advanced patterns
- **Shader Reference**: See `references/shaders.md` for shader examples
- **Export Guide**: See `references/export.md` for platform deployment
