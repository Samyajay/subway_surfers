from ursina import *
from ursina.shaders import lit_with_shadows_shader
import random
import math

app = Ursina()

# =========================================================
# 1. WINDOW & CAMERA SETUP
# =========================================================
window.title = "SUBWAY STYLE RUNNER - 3D EDITION"
window.borderless = False
window.exit_button.visible = False
window.fps_counter.enabled = True

# Atmosphere & Fog (Blends the horizon)
window.color = color.hex('#5cb3ff') 
scene.fog_density = 0.015           
scene.fog_color = window.color      

camera.position = (0, 6, -20)
camera.rotation_x = 15
camera.fov = 92
camera.clip_plane_far = 400

# =========================================================
# 2. LIGHTING & SHADOWS
# =========================================================
sun = DirectionalLight(y=10, rotation=(45, -45, 45))
sun.shadows = True                  
sun.shadow_map_resolution = Vec2(2048, 2048) 

AmbientLight(color=color.rgba(140, 140, 150, 0.6)) 

# =========================================================
# 3. GAME VARIABLES
# =========================================================
LANES = [-3, 0, 3]
speed = 18
score = 0
game_over = False

obstacles = []
coins = []
city_parts = []
sleepers = []
side_trains = []

# =========================================================
# 4. ENVIRONMENT GENERATION
# =========================================================
# Dirt Ground (Expanded and pulled back to fix the blue gap)
ground = Entity(
    model='plane', 
    scale=(100, 1, 400),       
    position=(0, 0, 100),      
    color=color.hex('#8c6b4a'), 
    texture='noise', 
    texture_scale=(50, 200),
    shader=lit_with_shadows_shader
)

# Rails
for lane in LANES:
    Entity(model='cube', scale=(0.13, 0.08, 300), position=(lane - 0.4, 0.06, 140), color=color.gray, shader=lit_with_shadows_shader)
    Entity(model='cube', scale=(0.13, 0.08, 300), position=(lane + 0.4, 0.06, 140), color=color.gray, shader=lit_with_shadows_shader)

# Wooden Sleepers under rails
for z in range(-20, 200, 4):
    for lane in LANES:
        s = Entity(
            model='cube', scale=(1.25, 0.06, 0.22), position=(lane, 0.02, z), 
            color=color.hex('#3b2313'), shader=lit_with_shadows_shader
        )
        sleepers.append(s)

# Side Decor Trains
for z in range(-20, 200, 45):
    t1 = Entity(model='cube', scale=(2.8, 2.8, 18), position=(-9, 1.4, z), color=color.blue, texture='white_cube', shader=lit_with_shadows_shader)
    t2 = Entity(model='cube', scale=(2.8, 2.8, 18), position=(9, 1.4, z + 22), color=color.blue, texture='white_cube', shader=lit_with_shadows_shader)
    side_trains.extend([t1, t2])

# City Buildings
for z in range(-20, 220, 16):
    for side in [-1, 1]:
        h = random.uniform(12, 40)
        c = random.choice([color.hex('#d4d4d4'), color.hex('#a3a3a3'), color.hex('#738291')])
        building = Entity(
            model='cube', scale=(6, h, 6), position=(side * 18, h / 2, z),
            color=c, texture='white_cube', texture_scale=(2, int(h/3)),
            shader=lit_with_shadows_shader
        )
        city_parts.append(building)
        
        # Glowing Windows
        for wy in range(2, int(h), 4):
            for wz in [-2, 0, 2]:
                Entity(
                    parent=building, model='cube', scale=(0.25, 0.35, 0.02),
                    x=-3.02 if side == -1 else 3.02, y=wy - (h / 2), z=wz, 
                    color=color.yellow, unlit=True 
                )

# =========================================================
# 5. PLAYER CLASS (Leg positioning fixed here!)
# =========================================================
class Player(Entity):
    def __init__(self):
        super().__init__(model='cube', scale=(1, 2, 1), position=(0, 1.3, -8), color=color.clear)
        self.current_lane = 1
        self.vertical_speed = 0
        self.gravity = 28
        self.grounded = True

        # Scaled parts correctly to fit inside the parent transform context
        self.body = Entity(parent=self, model='cube', scale=(0.9, 0.5, 0.6), y=0.1, color=color.azure, shader=lit_with_shadows_shader)
        self.head = Entity(parent=self, model='sphere', scale=0.35, y=0.55, color=color.peach, shader=lit_with_shadows_shader)
        self.left_arm = Entity(parent=self, model='cube', scale=(0.15, 0.4, 0.15), x=-0.55, y=0.1, color=color.red, shader=lit_with_shadows_shader)
        self.right_arm = Entity(parent=self, model='cube', scale=(0.15, 0.4, 0.15), x=0.55, y=0.1, color=color.red, shader=lit_with_shadows_shader)
        self.left_leg = Entity(parent=self, model='cube', scale=(0.2, 0.4, 0.2), x=-0.22, y=-0.35, color=color.black, shader=lit_with_shadows_shader)
        self.right_leg = Entity(parent=self, model='cube', scale=(0.2, 0.4, 0.2), x=0.22, y=-0.35, color=color.black, shader=lit_with_shadows_shader)

    def jump(self):
        if self.grounded:
            self.vertical_speed = 11
            self.grounded = False

    def update(self):
        target_x = LANES[self.current_lane]
        self.x += (target_x - self.x) * 10 * time.dt
        
        self.y += self.vertical_speed * time.dt
        self.vertical_speed -= self.gravity * time.dt

        # Ground level adjustment for updated legs
        if self.y <= 1.3:
            self.y = 1.3
            self.vertical_speed = 0
            self.grounded = True

        t = time.time() * 14
        run_power = min(speed / 18, 2)
        
        self.left_leg.rotation_x = math.sin(t) * 45 * run_power
        self.right_leg.rotation_x = -math.sin(t) * 45 * run_power
        self.left_arm.rotation_x = -math.sin(t) * 45 * run_power
        self.right_arm.rotation_x = math.sin(t) * 45 * run_power
        
        self.body.y = 0.1 + abs(math.sin(t)) * 0.08
        self.z = -8 + abs(math.sin(t * 0.5)) * 0.08
        self.rotation_z = (self.x - target_x) * -10

player = Player()

# =========================================================
# 6. ENEMY TRAINS & COINS
# =========================================================
class Train(Entity):
    def __init__(self, lane_index):
        super().__init__()
        self.lane_index = lane_index
        self.position = (LANES[lane_index], 1.2, 120)

        Entity(parent=self, model='cube', scale=(2.4, 2.5, 8), color=color.magenta, texture='white_cube', shader=lit_with_shadows_shader)
        Entity(parent=self, model='cube', scale=(2.2, 0.3, 7.8), y=1.3, color=color.yellow, shader=lit_with_shadows_shader)
        Entity(parent=self, model='cube', scale=(2.1, 2, 1.5), z=-4.7, color=color.dark_gray, shader=lit_with_shadows_shader)

    def update(self):
        global game_over
        if game_over: return
        self.z -= speed * time.dt
        
        if self.z < -30:
            if self in obstacles: obstacles.remove(self)
            destroy(self)
            return

        same_lane = (self.lane_index == player.current_lane)
        close_z = abs(self.z - player.z) < 1.2
        player_low = player.y < 2.2
        
        if same_lane and close_z and player_low:
            game_over = True

class Coin(Entity):
    def __init__(self, lane_index, z):
        super().__init__(
            model='sphere', scale=0.45, color=color.yellow, position=(LANES[lane_index], 1.5, z),
            shader=lit_with_shadows_shader
        )

    def update(self):
        global score
        if game_over: return
        self.z -= speed * time.dt
        self.rotation_y += 220 * time.dt

        if self.z < -20:
            if self in coins: coins.remove(self)
            destroy(self)
            return

        if distance(self.position, player.position) < 0.8:
            score += 10
            score_text.text = f"Score : {int(score)}"
            if self in coins: coins.remove(self)
            destroy(self)

# =========================================================
# 7. UI & MAIN GAME LOOP
# =========================================================
score_text = Text(text="Score : 0", scale=2, position=(-0.85, 0.45))
game_over_text = Text(text="GAME OVER\nPress R to Restart", origin=(0, 0), scale=2.5, color=color.red, enabled=False)

spawn_timer = 0
coin_timer = 0

def update():
    global spawn_timer, coin_timer, speed, game_over

    if game_over:
        game_over_text.enabled = True
        return

    speed += 0.03 * time.dt
    
    # Scroll ground texture to simulate high speed
    ground.texture_offset = (0, time.time() * speed * 0.02)

    # Recycle scenery
    for b in city_parts:
        b.z -= speed * time.dt
        if b.z < -40: b.z += 260

    for s in sleepers:
        s.z -= speed * time.dt
        if s.z < -30: s.z += 220

    for t in side_trains:
        t.z -= speed * time.dt
        if t.z < -40: t.z += 240

    # Spawners
    spawn_timer -= time.dt
    if spawn_timer <= 0:
        lane_index = random.randint(0, 2)
        obstacles.append(Train(lane_index))
        spawn_timer = random.uniform(1.1, 1.8)

    coin_timer -= time.dt
    if coin_timer <= 0:
        lane_index = random.randint(0, 2)
        for i in range(5):
            coins.append(Coin(lane_index, 80 + i * 2))
        coin_timer = 2

    # Camera Action
    camera.x += ((player.x * 0.3) - camera.x) * 2 * time.dt
    camera.y = (6 + abs(math.sin(time.time() * 6)) * 0.05)
    camera.fov = lerp(camera.fov, 92 + speed * 0.15, time.dt * 2)

def input(key):
    global game_over
    if game_over and key == 'r':
        application.restart()

    if key in ['a', 'left arrow']:
        player.current_lane = max(0, player.current_lane - 1)
    if key in ['d', 'right arrow']:
        player.current_lane = min(2, player.current_lane + 1)
    if key in ['space', 'up arrow', 'w']:
        player.jump()

app.run()