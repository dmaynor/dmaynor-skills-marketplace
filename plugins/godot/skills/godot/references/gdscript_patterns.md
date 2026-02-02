# GDScript Advanced Patterns

## Component System

Reusable logic modules attached to entities.

### Health Component

```gdscript
class_name HealthComponent
extends Node
## Manages health for any entity. Attach as child node.

signal health_changed(current: int, maximum: int)
signal damaged(amount: int, source: Node)
signal healed(amount: int)
signal died

@export var max_health: int = 100
@export var invincibility_duration: float = 0.0

var current_health: int:
    get:
        return _current_health

var _current_health: int
var _invincible: bool = false


func _ready() -> void:
    _current_health = max_health


func take_damage(amount: int, source: Node = null) -> void:
    if _invincible or _current_health <= 0:
        return
    
    _current_health = max(_current_health - amount, 0)
    damaged.emit(amount, source)
    health_changed.emit(_current_health, max_health)
    
    if _current_health == 0:
        died.emit()
    elif invincibility_duration > 0:
        _start_invincibility()


func heal(amount: int) -> void:
    if _current_health <= 0:
        return
    
    var old_health := _current_health
    _current_health = min(_current_health + amount, max_health)
    
    if _current_health > old_health:
        healed.emit(_current_health - old_health)
        health_changed.emit(_current_health, max_health)


func _start_invincibility() -> void:
    _invincible = true
    await get_tree().create_timer(invincibility_duration).timeout
    _invincible = false
```

### Hitbox/Hurtbox System

```gdscript
# hitbox.gd
class_name Hitbox
extends Area2D
## Deals damage on contact with Hurtbox.

@export var damage: int = 10
@export var knockback_force: float = 200.0

var source: Node


# hurtbox.gd
class_name Hurtbox
extends Area2D
## Receives damage from Hitbox.

signal hit(hitbox: Hitbox)

@export var health_component: HealthComponent

func _ready() -> void:
    area_entered.connect(_on_area_entered)


func _on_area_entered(area: Area2D) -> void:
    if area is Hitbox:
        hit.emit(area)
        if health_component:
            health_component.take_damage(area.damage, area.source)
```

## Dependency Injection

### Service Locator Pattern

```gdscript
# service_locator.gd (Autoload)
class_name ServiceLocator
extends Node

var _services: Dictionary = {}


func register(service_name: String, service: Object) -> void:
    _services[service_name] = service


func get_service(service_name: String) -> Object:
    return _services.get(service_name)


func has_service(service_name: String) -> bool:
    return _services.has(service_name)
```

Usage:

```gdscript
# Registration (in _ready of service)
ServiceLocator.register("audio", self)

# Retrieval
var audio: AudioManager = ServiceLocator.get_service("audio")
```

## Event Bus

```gdscript
# event_bus.gd (Autoload)
class_name EventBus
extends Node

# Game events
signal enemy_spawned(enemy: Node)
signal enemy_killed(enemy: Node, killer: Node)
signal player_died
signal level_completed(level_id: int)
signal checkpoint_reached(checkpoint_id: int)

# UI events  
signal score_updated(new_score: int)
signal health_updated(current: int, max_health: int)
signal dialog_started(dialog_id: String)
signal dialog_ended
```

Usage:

```gdscript
# Emit
EventBus.enemy_killed.emit(self, killer)

# Subscribe
EventBus.enemy_killed.connect(_on_enemy_killed)
```

## Coroutines and Async

### Sequential Animations

```gdscript
func play_combo() -> void:
    await _attack("slash")
    await get_tree().create_timer(0.1).timeout
    await _attack("thrust")
    await get_tree().create_timer(0.1).timeout
    await _attack("spin")


func _attack(anim_name: String) -> void:
    anim_player.play(anim_name)
    await anim_player.animation_finished
```

### Parallel Operations

```gdscript
func load_level_async() -> void:
    var tasks := [
        _load_tilemap(),
        _spawn_enemies(),
        _setup_audio()
    ]
    
    # Wait for all
    for task in tasks:
        await task
    
    level_ready.emit()
```

### Cancellable Operations

```gdscript
var _current_tween: Tween

func move_to(target: Vector2, duration: float) -> void:
    # Cancel existing
    if _current_tween and _current_tween.is_valid():
        _current_tween.kill()
    
    _current_tween = create_tween()
    _current_tween.tween_property(self, "global_position", target, duration)
    await _current_tween.finished
```

## Command Pattern

```gdscript
class_name Command
extends RefCounted

func execute() -> void:
    pass

func undo() -> void:
    pass


class MoveCommand extends Command:
    var _unit: Node2D
    var _direction: Vector2
    var _distance: float
    var _previous_position: Vector2
    
    func _init(unit: Node2D, direction: Vector2, distance: float) -> void:
        _unit = unit
        _direction = direction
        _distance = distance
    
    func execute() -> void:
        _previous_position = _unit.global_position
        _unit.global_position += _direction * _distance
    
    func undo() -> void:
        _unit.global_position = _previous_position


# Command invoker
class_name CommandHistory
extends Node

var _history: Array[Command] = []
var _redo_stack: Array[Command] = []

func execute(command: Command) -> void:
    command.execute()
    _history.append(command)
    _redo_stack.clear()

func undo() -> void:
    if _history.is_empty():
        return
    var command := _history.pop_back()
    command.undo()
    _redo_stack.append(command)

func redo() -> void:
    if _redo_stack.is_empty():
        return
    var command := _redo_stack.pop_back()
    command.execute()
    _history.append(command)
```

## Observer with Weak References

```gdscript
class_name Observable
extends RefCounted

var _observers: Array[WeakRef] = []

func add_observer(observer: Object) -> void:
    _observers.append(weakref(observer))

func remove_observer(observer: Object) -> void:
    for i in range(_observers.size() - 1, -1, -1):
        var ref := _observers[i].get_ref()
        if ref == null or ref == observer:
            _observers.remove_at(i)

func notify(method: String, args: Array = []) -> void:
    for i in range(_observers.size() - 1, -1, -1):
        var ref := _observers[i].get_ref()
        if ref == null:
            _observers.remove_at(i)
        elif ref.has_method(method):
            ref.callv(method, args)
```

## Hierarchical State Machine

```gdscript
class_name State
extends Node

signal transitioned(new_state_name: String)

func enter() -> void:
    pass

func exit() -> void:
    pass

func update(_delta: float) -> void:
    pass

func physics_update(_delta: float) -> void:
    pass

func handle_input(_event: InputEvent) -> void:
    pass


class_name StateMachine
extends Node

@export var initial_state: State

var current_state: State
var states: Dictionary = {}

func _ready() -> void:
    for child in get_children():
        if child is State:
            states[child.name.to_lower()] = child
            child.transitioned.connect(_on_state_transitioned)
    
    if initial_state:
        current_state = initial_state
        current_state.enter()

func _process(delta: float) -> void:
    if current_state:
        current_state.update(delta)

func _physics_process(delta: float) -> void:
    if current_state:
        current_state.physics_update(delta)

func _unhandled_input(event: InputEvent) -> void:
    if current_state:
        current_state.handle_input(event)

func _on_state_transitioned(new_state_name: String) -> void:
    var new_state := states.get(new_state_name.to_lower())
    if new_state == null or new_state == current_state:
        return
    
    current_state.exit()
    current_state = new_state
    current_state.enter()
```

## Behavior Trees (Simplified)

```gdscript
class_name BTNode
extends RefCounted

enum Status { SUCCESS, FAILURE, RUNNING }

func tick(_actor: Node, _blackboard: Dictionary) -> Status:
    return Status.FAILURE


class BTSequence extends BTNode:
    var children: Array[BTNode] = []
    
    func tick(actor: Node, blackboard: Dictionary) -> Status:
        for child in children:
            var status := child.tick(actor, blackboard)
            if status != Status.SUCCESS:
                return status
        return Status.SUCCESS


class BTSelector extends BTNode:
    var children: Array[BTNode] = []
    
    func tick(actor: Node, blackboard: Dictionary) -> Status:
        for child in children:
            var status := child.tick(actor, blackboard)
            if status != Status.FAILURE:
                return status
        return Status.FAILURE


class BTCondition extends BTNode:
    var condition: Callable
    
    func _init(cond: Callable) -> void:
        condition = cond
    
    func tick(actor: Node, blackboard: Dictionary) -> Status:
        if condition.call(actor, blackboard):
            return Status.SUCCESS
        return Status.FAILURE
```

## Generic Timer Pool

```gdscript
class_name TimerPool
extends Node

var _timers: Array[Timer] = []

func get_timer(duration: float, one_shot: bool = true) -> Timer:
    var timer: Timer
    
    # Find available timer
    for t in _timers:
        if t.is_stopped():
            timer = t
            break
    
    # Create new if none available
    if timer == null:
        timer = Timer.new()
        add_child(timer)
        _timers.append(timer)
    
    timer.wait_time = duration
    timer.one_shot = one_shot
    return timer


func start_timer(duration: float, callback: Callable) -> Timer:
    var timer := get_timer(duration)
    timer.timeout.connect(callback, CONNECT_ONE_SHOT)
    timer.start()
    return timer
```
