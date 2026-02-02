# Godot Shader Reference

## Shader Types

| Type | Purpose | File |
|------|---------|------|
| `shader_type canvas_item` | 2D sprites, UI, CanvasItem nodes | `.gdshader` |
| `shader_type spatial` | 3D meshes, materials | `.gdshader` |
| `shader_type particles` | GPU particles | `.gdshader` |
| `shader_type sky` | Sky/environment backgrounds | `.gdshader` |
| `shader_type fog` | Volumetric fog | `.gdshader` |

## Canvas Item Shaders (2D)

### Basic Structure

```glsl
shader_type canvas_item;

// Uniforms (configurable from inspector/code)
uniform vec4 tint_color : source_color = vec4(1.0);
uniform float intensity : hint_range(0.0, 1.0) = 1.0;
uniform sampler2D noise_texture : filter_linear;

void vertex() {
    // Modify vertex position/UV
}

void fragment() {
    // Modify pixel color
    vec4 tex_color = texture(TEXTURE, UV);
    COLOR = tex_color * tint_color;
}

void light() {
    // Custom lighting (optional)
}
```

### Flash Effect (Hit Feedback)

```glsl
shader_type canvas_item;

uniform vec4 flash_color : source_color = vec4(1.0, 1.0, 1.0, 1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;

void fragment() {
    vec4 tex_color = texture(TEXTURE, UV);
    COLOR = mix(tex_color, flash_color, flash_amount);
    COLOR.a = tex_color.a;
}
```

GDScript control:

```gdscript
func flash(duration: float = 0.1) -> void:
    material.set_shader_parameter("flash_amount", 1.0)
    var tween := create_tween()
    tween.tween_property(material, "shader_parameter/flash_amount", 0.0, duration)
```

### Outline

```glsl
shader_type canvas_item;

uniform vec4 outline_color : source_color = vec4(0.0, 0.0, 0.0, 1.0);
uniform float outline_width : hint_range(0.0, 10.0) = 1.0;

void fragment() {
    vec2 size = TEXTURE_PIXEL_SIZE * outline_width;
    
    float outline = texture(TEXTURE, UV + vec2(-size.x, 0)).a;
    outline += texture(TEXTURE, UV + vec2(size.x, 0)).a;
    outline += texture(TEXTURE, UV + vec2(0, -size.y)).a;
    outline += texture(TEXTURE, UV + vec2(0, size.y)).a;
    outline += texture(TEXTURE, UV + vec2(-size.x, -size.y)).a;
    outline += texture(TEXTURE, UV + vec2(size.x, -size.y)).a;
    outline += texture(TEXTURE, UV + vec2(-size.x, size.y)).a;
    outline += texture(TEXTURE, UV + vec2(size.x, size.y)).a;
    outline = min(outline, 1.0);
    
    vec4 tex_color = texture(TEXTURE, UV);
    COLOR = mix(outline_color * outline, tex_color, tex_color.a);
}
```

### Dissolve

```glsl
shader_type canvas_item;

uniform sampler2D noise_texture : filter_linear;
uniform float dissolve_amount : hint_range(0.0, 1.0) = 0.0;
uniform float edge_width : hint_range(0.0, 0.2) = 0.05;
uniform vec4 edge_color : source_color = vec4(1.0, 0.5, 0.0, 1.0);

void fragment() {
    vec4 tex_color = texture(TEXTURE, UV);
    float noise = texture(noise_texture, UV).r;
    
    float dissolve_edge = dissolve_amount + edge_width;
    float edge = step(dissolve_amount, noise) - step(dissolve_edge, noise);
    
    COLOR = mix(tex_color, edge_color, edge);
    COLOR.a *= step(dissolve_amount, noise) * tex_color.a;
}
```

### Pixelate

```glsl
shader_type canvas_item;

uniform float pixel_size : hint_range(1.0, 64.0) = 4.0;

void fragment() {
    vec2 size = vec2(pixel_size) / vec2(textureSize(TEXTURE, 0));
    vec2 uv = floor(UV / size) * size + size * 0.5;
    COLOR = texture(TEXTURE, uv);
}
```

### Screen Wave/Distortion

```glsl
shader_type canvas_item;

uniform float wave_amplitude : hint_range(0.0, 0.1) = 0.02;
uniform float wave_frequency : hint_range(0.0, 50.0) = 10.0;
uniform float wave_speed : hint_range(0.0, 10.0) = 2.0;

void fragment() {
    vec2 uv = UV;
    uv.x += sin(uv.y * wave_frequency + TIME * wave_speed) * wave_amplitude;
    uv.y += cos(uv.x * wave_frequency + TIME * wave_speed) * wave_amplitude;
    COLOR = texture(TEXTURE, uv);
}
```

### Grayscale

```glsl
shader_type canvas_item;

uniform float amount : hint_range(0.0, 1.0) = 1.0;

void fragment() {
    vec4 tex_color = texture(TEXTURE, UV);
    float gray = dot(tex_color.rgb, vec3(0.299, 0.587, 0.114));
    COLOR.rgb = mix(tex_color.rgb, vec3(gray), amount);
    COLOR.a = tex_color.a;
}
```

### Chromatic Aberration

```glsl
shader_type canvas_item;

uniform float offset : hint_range(0.0, 0.02) = 0.005;

void fragment() {
    float r = texture(TEXTURE, UV + vec2(offset, 0.0)).r;
    float g = texture(TEXTURE, UV).g;
    float b = texture(TEXTURE, UV - vec2(offset, 0.0)).b;
    float a = texture(TEXTURE, UV).a;
    COLOR = vec4(r, g, b, a);
}
```

### CRT Effect

```glsl
shader_type canvas_item;

uniform float scanline_intensity : hint_range(0.0, 1.0) = 0.3;
uniform float scanline_count : hint_range(50.0, 500.0) = 200.0;
uniform float vignette_intensity : hint_range(0.0, 1.0) = 0.3;
uniform float curvature : hint_range(0.0, 0.1) = 0.02;

void fragment() {
    // Barrel distortion
    vec2 uv = UV - 0.5;
    float dist = length(uv);
    uv *= 1.0 + curvature * dist * dist;
    uv += 0.5;
    
    // Clamp and sample
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
        COLOR = vec4(0.0);
    } else {
        vec4 tex_color = texture(TEXTURE, uv);
        
        // Scanlines
        float scanline = sin(uv.y * scanline_count * PI) * 0.5 + 0.5;
        tex_color.rgb -= scanline_intensity * scanline;
        
        // Vignette
        float vignette = 1.0 - dist * 2.0 * vignette_intensity;
        tex_color.rgb *= vignette;
        
        COLOR = tex_color;
    }
}
```

## Spatial Shaders (3D)

### Basic Unlit

```glsl
shader_type spatial;
render_mode unshaded;

uniform vec4 albedo_color : source_color = vec4(1.0);
uniform sampler2D albedo_texture : source_color;

void fragment() {
    ALBEDO = texture(albedo_texture, UV).rgb * albedo_color.rgb;
}
```

### Toon Shader

```glsl
shader_type spatial;

uniform vec4 albedo_color : source_color = vec4(1.0);
uniform sampler2D albedo_texture : source_color;
uniform int bands : hint_range(2, 10) = 3;
uniform float rim_amount : hint_range(0.0, 1.0) = 0.5;
uniform vec4 rim_color : source_color = vec4(1.0);

void fragment() {
    ALBEDO = texture(albedo_texture, UV).rgb * albedo_color.rgb;
}

void light() {
    float ndotl = dot(NORMAL, LIGHT);
    float banded = floor(ndotl * float(bands)) / float(bands);
    
    // Rim lighting
    float rim = 1.0 - dot(NORMAL, VIEW);
    rim = smoothstep(1.0 - rim_amount, 1.0, rim);
    
    DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * banded * ALBEDO;
    DIFFUSE_LIGHT += rim * rim_color.rgb * LIGHT_COLOR;
}
```

### Hologram

```glsl
shader_type spatial;
render_mode cull_disabled;

uniform vec4 hologram_color : source_color = vec4(0.0, 1.0, 1.0, 1.0);
uniform float scan_speed : hint_range(0.0, 10.0) = 2.0;
uniform float scan_lines : hint_range(10.0, 200.0) = 50.0;
uniform float flicker_speed : hint_range(0.0, 50.0) = 20.0;
uniform float alpha : hint_range(0.0, 1.0) = 0.7;

void fragment() {
    // Fresnel effect
    float fresnel = pow(1.0 - dot(NORMAL, VIEW), 2.0);
    
    // Scanlines
    float scan = sin((UV.y + TIME * scan_speed) * scan_lines) * 0.5 + 0.5;
    
    // Flicker
    float flicker = sin(TIME * flicker_speed) * 0.1 + 0.9;
    
    ALBEDO = hologram_color.rgb;
    ALPHA = (fresnel + scan * 0.3) * alpha * flicker;
    EMISSION = hologram_color.rgb * fresnel;
}
```

## Particle Shaders

### Basic Custom Particle

```glsl
shader_type particles;

uniform float spread : hint_range(0.0, 180.0) = 45.0;
uniform float initial_velocity : hint_range(0.0, 100.0) = 10.0;
uniform float gravity : hint_range(-20.0, 20.0) = -9.8;

void start() {
    float angle = radians(spread) * (randf() - 0.5);
    VELOCITY = vec3(sin(angle), cos(angle), 0.0) * initial_velocity;
}

void process() {
    VELOCITY.y += gravity * DELTA;
    
    // Fade out
    COLOR.a = 1.0 - LIFETIME / LIFETIME;
    
    // Scale down
    float t = LIFETIME / LIFETIME;
    TRANSFORM[0].x = 1.0 - t;
    TRANSFORM[1].y = 1.0 - t;
}
```

## Uniform Hints

| Hint | Usage |
|------|-------|
| `:source_color` | Color picker in inspector |
| `:hint_range(min, max)` | Slider with range |
| `:hint_range(min, max, step)` | Slider with step |
| `sampler2D : filter_linear` | Linear texture filtering |
| `sampler2D : filter_nearest` | Nearest (pixelated) filtering |
| `sampler2D : repeat_enable` | Texture repeats |

## Built-in Variables

### Canvas Item (fragment)

| Variable | Type | Description |
|----------|------|-------------|
| `UV` | vec2 | Texture coordinates |
| `TEXTURE` | sampler2D | Main texture |
| `COLOR` | vec4 | Output color |
| `SCREEN_UV` | vec2 | Screen-space UV |
| `SCREEN_TEXTURE` | sampler2D | Screen contents |
| `TIME` | float | Shader time |
| `TEXTURE_PIXEL_SIZE` | vec2 | Pixel size in UV |

### Spatial (fragment)

| Variable | Type | Description |
|----------|------|-------------|
| `VERTEX` | vec3 | Vertex position |
| `NORMAL` | vec3 | Surface normal |
| `UV` | vec2 | Texture coordinates |
| `VIEW` | vec3 | View direction |
| `ALBEDO` | vec3 | Base color output |
| `EMISSION` | vec3 | Emissive color |
| `ALPHA` | float | Transparency |
| `METALLIC` | float | Metallic value |
| `ROUGHNESS` | float | Roughness value |

## Applying Shaders via GDScript

```gdscript
# Create material
var material := ShaderMaterial.new()
material.shader = preload("res://shaders/flash.gdshader")

# Apply to sprite
sprite.material = material

# Set uniform
material.set_shader_parameter("flash_color", Color.RED)
material.set_shader_parameter("flash_amount", 0.5)

# Get uniform
var current: float = material.get_shader_parameter("flash_amount")
```

## Screen-Reading Shaders

Enable in CanvasItem Material Next Pass material, or use:

```glsl
shader_type canvas_item;

uniform sampler2D screen_texture : hint_screen_texture, filter_linear_mipmap;

void fragment() {
    vec4 screen = texture(screen_texture, SCREEN_UV);
    COLOR = screen;
}
```
