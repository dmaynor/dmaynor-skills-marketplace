#!/usr/bin/env python3
"""
Godot Project Scaffolder

Creates a new Godot 4.x project with recommended directory structure
and starter files.

Usage:
    python scaffold_project.py <project_name> [--path <output_dir>]

Examples:
    python scaffold_project.py my_platformer
    python scaffold_project.py space_shooter --path ~/Projects
"""

import argparse
import os
from pathlib import Path
from typing import Optional


def create_project_godot(project_name: str) -> str:
    """Generate project.godot content."""
    return f'''config_version=5

[application]
config/name="{project_name}"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.2", "Forward Plus")
config/icon="res://icon.svg"

[autoload]
GameManager="*res://scripts/autoload/game_manager.gd"
AudioManager="*res://scripts/autoload/audio_manager.gd"

[display]
window/size/viewport_width=1920
window/size/viewport_height=1080
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"

[input]
move_left={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":65,"key_label":0,"unicode":97,"echo":false,"script":null)
]
}}
move_right={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":68,"key_label":0,"unicode":100,"echo":false,"script":null)
]
}}
move_up={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":87,"key_label":0,"unicode":119,"echo":false,"script":null)
]
}}
move_down={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":83,"key_label":0,"unicode":115,"echo":false,"script":null)
]
}}
jump={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":32,"key_label":0,"unicode":32,"echo":false,"script":null)
]
}}
pause={{
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":4194305,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}}

[rendering]
textures/canvas_textures/default_texture_filter=0
'''


def create_main_scene() -> str:
    """Generate main.tscn content."""
    return '''[gd_scene format=3 uid="uid://main"]

[node name="Main" type="Node2D"]
'''


def create_game_manager() -> str:
    """Generate game_manager.gd content."""
    return '''extends Node
## Global game state manager.

signal score_changed(new_score: int)
signal game_paused(is_paused: bool)
signal game_over

var score: int = 0:
    set(value):
        score = value
        score_changed.emit(score)

var is_paused: bool = false:
    set(value):
        is_paused = value
        get_tree().paused = value
        game_paused.emit(is_paused)


func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS


func _input(event: InputEvent) -> void:
    if event.is_action_pressed("pause"):
        is_paused = not is_paused


func add_score(amount: int) -> void:
    score += amount


func reset() -> void:
    score = 0
    is_paused = false


func trigger_game_over() -> void:
    game_over.emit()
'''


def create_audio_manager() -> str:
    """Generate audio_manager.gd content."""
    return '''extends Node
## Global audio manager for SFX and music.

const MAX_CONCURRENT_SOUNDS: int = 8

var _sfx_players: Array[AudioStreamPlayer] = []
var _music_player: AudioStreamPlayer


func _ready() -> void:
    for i in MAX_CONCURRENT_SOUNDS:
        var player := AudioStreamPlayer.new()
        player.bus = "SFX"
        add_child(player)
        _sfx_players.append(player)
    
    _music_player = AudioStreamPlayer.new()
    _music_player.bus = "Music"
    add_child(_music_player)


func play_sfx(stream: AudioStream, volume_db: float = 0.0) -> void:
    for player in _sfx_players:
        if not player.playing:
            player.stream = stream
            player.volume_db = volume_db
            player.play()
            return
    
    _sfx_players[0].stream = stream
    _sfx_players[0].volume_db = volume_db
    _sfx_players[0].play()


func play_music(stream: AudioStream, volume_db: float = 0.0, fade_duration: float = 0.5) -> void:
    if _music_player.playing:
        var tween := create_tween()
        tween.tween_property(_music_player, "volume_db", -40.0, fade_duration)
        await tween.finished
    
    _music_player.stream = stream
    _music_player.volume_db = -40.0
    _music_player.play()
    
    var tween := create_tween()
    tween.tween_property(_music_player, "volume_db", volume_db, fade_duration)


func stop_music(fade_duration: float = 0.5) -> void:
    if _music_player.playing:
        var tween := create_tween()
        tween.tween_property(_music_player, "volume_db", -40.0, fade_duration)
        await tween.finished
        _music_player.stop()
'''


def create_gitignore() -> str:
    """Generate .gitignore content."""
    return '''# Godot 4+ specific ignores
.godot/

# Godot-specific ignores
*.translation

# Imported textures and samples
.import/

# Mono-specific ignores
.mono/
data_*/
mono_crash.*.json

# Export
export/
*.exe
*.x86_64
*.pck

# IDE
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
'''


def create_default_bus_layout() -> str:
    """Generate default_bus_layout.tres content."""
    return '''[gd_resource type="AudioBusLayout" format=3 uid="uid://audio_bus"]

[resource]
bus/1/name = &"Music"
bus/1/solo = false
bus/1/mute = false
bus/1/bypass_fx = false
bus/1/volume_db = 0.0
bus/1/send = &"Master"
bus/2/name = &"SFX"
bus/2/solo = false
bus/2/mute = false
bus/2/bypass_fx = false
bus/2/volume_db = 0.0
bus/2/send = &"Master"
'''


def create_icon_svg() -> str:
    """Generate simple placeholder icon."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">
  <rect width="128" height="128" fill="#478cbf"/>
  <text x="64" y="80" font-size="48" text-anchor="middle" fill="white">G</text>
</svg>
'''


def scaffold_project(project_name: str, output_path: Optional[str] = None) -> Path:
    """
    Create a complete Godot project structure.
    
    Args:
        project_name: Name of the project
        output_path: Directory to create project in (default: current directory)
    
    Returns:
        Path to created project directory
    """
    base_path = Path(output_path) if output_path else Path.cwd()
    project_dir = base_path / project_name
    
    if project_dir.exists():
        raise FileExistsError(f"Directory already exists: {project_dir}")
    
    directories = [
        "scenes",
        "scenes/player",
        "scenes/enemies",
        "scenes/ui",
        "scenes/levels",
        "scripts/autoload",
        "scripts/components",
        "scripts/resources",
        "resources/themes",
        "assets/sprites",
        "assets/audio/sfx",
        "assets/audio/music",
        "assets/fonts",
        "assets/shaders",
    ]
    
    for dir_path in directories:
        (project_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    files = {
        "project.godot": create_project_godot(project_name),
        "scenes/main.tscn": create_main_scene(),
        "scripts/autoload/game_manager.gd": create_game_manager(),
        "scripts/autoload/audio_manager.gd": create_audio_manager(),
        "default_bus_layout.tres": create_default_bus_layout(),
        "icon.svg": create_icon_svg(),
        ".gitignore": create_gitignore(),
    }
    
    for file_path, content in files.items():
        (project_dir / file_path).write_text(content)
    
    print(f"Created Godot project: {project_dir}")
    print(f"\nOpen in Godot: godot --path {project_dir}")
    
    return project_dir


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create a new Godot 4.x project with recommended structure"
    )
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument(
        "--path",
        help="Output directory (default: current directory)",
        default=None
    )
    
    args = parser.parse_args()
    
    try:
        scaffold_project(args.project_name, args.path)
    except FileExistsError as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
