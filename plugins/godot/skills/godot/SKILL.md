---
name: godot
description: "Godot Engine 4.x game development skill for GDScript, scene architecture, physics, UI, shaders, and project structure. Use when creating games, prototypes, or interactive applications in Godot. Triggers on requests involving GDScript code, .tscn/.tres files, node hierarchies, signals, tweens, animations, tilemaps, collision layers, export variables, autoloads, or any Godot-specific development task."
author: dmaynor
version: 1.0.0
date: 2026-03-29
---

# Godot Engine Development

Comprehensive skill for Godot 4.x game development. Covers GDScript, scene/node architecture, physics, UI, shaders, and deployment.

## Problem

Building Godot 4.x games requires juggling scattered documentation across GDScript syntax, node architecture, physics, UI, shaders, and deployment. Developers waste time hunting through docs, forums, and examples instead of building their game. The GDScript 2.0 syntax changes from Godot 3.x add further confusion.

## Version

Target: **Godot 4.2+** (GDScript 2.0 syntax). For Godot 3.x, adapt syntax (e.g., `@export` -> `export`, `@onready` -> `onready`).

## Core Workflow

1. **Scene architecture first**: Design your node tree before writing code. Everything is a Node; scenes are trees saved as `.tscn`.
2. **Composition over inheritance**: Build reusable component scenes and instance them (e.g., `HealthComponent.tscn`).
3. **Signals for decoupling**: Nodes communicate upward via signals, downward via method calls.
4. **Type everything**: Use explicit type hints on all variables, parameters, and return types.
5. **Export for tuning**: Use `@export` for inspector-editable values; `@onready` for node refs resolved after `_ready()`.
6. **Test in-engine**: Run with `godot --path . --debug` to catch errors early.

### Node Architecture Overview

```
Node (base class)
+-- Node2D (2D positioning: Sprite2D, CharacterBody2D, TileMap, Camera2D...)
+-- Node3D (3D positioning: MeshInstance3D, Camera3D, CharacterBody3D...)
+-- Control (UI: Button, Label, Container, Panel...)
+-- CanvasLayer (overlay layers for UI/HUD)
```

### Scene Composition Pattern

```
Player.tscn
+-- CharacterBody2D (root)
    +-- Sprite2D
    +-- CollisionShape2D
    +-- AnimationPlayer
    +-- HealthComponent.tscn (instanced)
```

## Common Patterns

### Script Template

```gdscript
class_name Player
extends CharacterBody2D
## Player controller handling movement and combat.

signal health_changed(new_health: int)
signal died

@export var move_speed: float = 200.0
@export var jump_force: float = -400.0
@export_range(0, 100) var max_health: int = 100

@onready var sprite: Sprite2D = $Sprite2D
@onready var anim_player: AnimationPlayer = $AnimationPlayer

var _health: int = max_health
var _gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")


func _ready() -> void:
    _health = max_health


func _physics_process(delta: float) -> void:
    _apply_gravity(delta)
    _handle_movement()
    move_and_slide()


func take_damage(amount: int) -> void:
    _health = max(_health - amount, 0)
    health_changed.emit(_health)
    if _health == 0:
        died.emit()
```

### State Machine

```gdscript
enum State { IDLE, RUN, JUMP, FALL, ATTACK }
var _state: State = State.IDLE

func _physics_process(delta: float) -> void:
    match _state:
        State.IDLE: _state_idle(delta)
        State.RUN: _state_run(delta)
        State.JUMP: _state_jump(delta)

func _change_state(new_state: State) -> void:
    if _state == new_state: return
    _exit_state(_state)
    _state = new_state
    _enter_state(new_state)
```

### Resource-based Data

```gdscript
class_name WeaponData
extends Resource

@export var name: String
@export var damage: int
@export var attack_speed: float
@export var icon: Texture2D
```

Save as `.tres`, load with: `var sword: WeaponData = preload("res://resources/weapons/sword.tres")`

### Signals

```gdscript
signal item_collected(item_name: String, quantity: int)
item_collected.emit("coin", 5)
player.item_collected.connect(_on_item_collected)
enemy.died.connect(_on_enemy_died, CONNECT_ONE_SHOT)
```

### Autoloads (Singletons)

Register in Project Settings -> Autoload. Access globally: `GameManager.add_score(100)`

```gdscript
extends Node
signal score_changed(new_score: int)

var score: int = 0:
    set(value):
        score = value
        score_changed.emit(score)
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

## Verification

1. Project runs without errors: launch with `godot --path . --debug` and confirm no GDScript errors in the output console
2. Main scene loads and renders correctly (no missing nodes, no null reference errors)
3. All `@export` variables appear in the Inspector with correct types and ranges
4. Signal connections fire as expected: test each `signal.emit()` path and verify connected handlers execute
5. No orphaned nodes: check `Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)` returns 0 during gameplay

## References

See `reference.md` for complete GDScript reference including detailed node types, physics, UI, input handling, animation, save/load, scene management, debugging, and project structure.

- **GDScript Patterns**: See `references/gdscript_patterns.md` for advanced patterns
- **Shader Reference**: See `references/shaders.md` for shader examples
- **Export Guide**: See `references/export.md` for platform deployment
