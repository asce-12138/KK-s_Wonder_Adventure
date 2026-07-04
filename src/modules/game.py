import pygame
from .player import Player
from .enemies.enemy_manager import EnemyManager
from .items.item_manager import ItemManager
from .ui import UI
from .menu import PauseMenu, GameOverMenu, UpgradeMenu
from .menus.main_menu import MainMenu
from .menus.save_menu import SaveMenu
from .save_system import SaveSystem
from .resource_manager import resource_manager
from .upgrade_system import UpgradeManager, WeaponUpgradeLevel, PassiveUpgradeLevel
from .utils import apply_mask_collision
from .map_manager import MapManager
from .menus.map_hero_select_menu import MapHeroSelectMenu
from .network_client import get_network_client
from .remote_player import RemotePlayer
from .utils import FontManager

class Game:
    def __init__(self, screen, network_mode=False, is_host=False, local_player_id=1, on_return_to_lobby=None):
        self.screen = screen
        self.running = True
        self.paused = False
        self.game_over = False
        self.in_main_menu = True
        self.in_map_hero_select = False
        
        self.network_mode = network_mode
        self.is_host = is_host
        self.local_player_id = local_player_id
        self.on_return_to_lobby = on_return_to_lobby
        self.disconnect_message = None
        self.network_sync_timer = 0
        self.network_sync_interval = 0.05
        
        self.remote_player = None
        self.remote_player_data = None
        self.show_disconnect_popup = False
        self.disconnect_popup_timer = 0
        
        resource_manager._init_resources()
        
        self.screen_center_x = self.screen.get_width() // 2
        self.screen_center_y = self.screen.get_height() // 2
        
        self.player = None
        
        self.camera_x = 0
        self.camera_y = 0
        
        self.grid_size = 50
        self.grid_color = (50, 50, 50)
        
        self.enemy_manager = None
        self.item_manager = None
        self.save_system = SaveSystem()
        self.upgrade_manager = UpgradeManager()
        self.map_manager = MapManager(screen)
        
        self.ui = UI(screen)
        
        if self.network_mode:
            self.main_menu = None
            self.in_main_menu = False
            self.in_map_hero_select = True
        else:
            extra_options = [{'text': '联机模式', 'action': 'multiplayer'}]
            self.main_menu = MainMenu(screen, extra_options=extra_options)
        
        self.pause_menu = PauseMenu(screen)
        self.game_over_menu = GameOverMenu(screen)
        self.upgrade_menu = UpgradeMenu(screen)
        self.save_menu = SaveMenu(screen, True)
        self.load_menu = SaveMenu(screen, False)
        
        self.map_hero_select_menu = MapHeroSelectMenu(
            screen,
            on_start_game=self._start_game_with_selection,
            on_back=self._back_to_main_menu
        )
        
        self.game_time = 0
        self.kill_num = 0
        self.level = 1
        
        self.current_map = None
        
        self.popup_font = FontManager.get_font(28)
        
        if self.network_mode:
            self._setup_network()
            self.map_hero_select_menu.show()
        else:
            self._play_menu_music()
        
    def _setup_network(self):
        """设置网络回调"""
        net_client = get_network_client()
        net_client.on_disconnected = self._on_network_disconnected
        self.remote_player = RemotePlayer(hero_type="ninja_frog")
        self.remote_player.player_name = f"玩家{2 if self.local_player_id == 1 else 1}"
        if self.local_player_id == 1:
            self.remote_player.name_color = (0, 255, 255)
        else:
            self.remote_player.name_color = (255, 200, 0)
        
        self._play_game_music()
    
    def _on_network_disconnected(self):
        """网络断开回调"""
        self.disconnect_message = "连接已断开，正在返回联机大厅..."
        self.show_disconnect_popup = True
        self.disconnect_popup_timer = 2.0
    
    def _return_to_lobby(self):
        """返回联机大厅"""
        if self.on_return_to_lobby:
            msg = self.disconnect_message if self.disconnect_message else None
            self.on_return_to_lobby(msg)
        
    def _set_map_boundaries(self):
        if not self.current_map:
            return
            
        map_width, map_height = self.map_manager.get_map_size()
        
        fence_width = 2 * 32
        
        min_x = fence_width
        min_y = fence_width
        max_x = map_width - fence_width
        max_y = map_height - fence_width
        
        if self.player:
            self.player.movement.set_boundaries(min_x, min_y, max_x, max_y)
            
        if self.enemy_manager:
            self.enemy_manager.set_map_boundaries(min_x, min_y, max_x, max_y)
            self.enemy_manager.set_current_map(self.current_map)
            
    def _set_player_boundaries(self):
        self._set_map_boundaries()
        
    def _start_game_with_selection(self, map_id, hero_id):
        self.in_map_hero_select = False
        self.game_over = False
        self.paused = False
        
        self.load_map(map_id)
        
        map_width, map_height = self.map_manager.get_map_size()
        
        self.player = Player(self.screen_center_x, self.screen_center_y, hero_id)
        
        self.player.world_x = map_width // 2
        self.player.world_y = map_height // 2
        
        if self.network_mode and self.local_player_id == 2:
            self.player.world_x = map_width // 2 + 100
            self.player.world_y = map_height // 2 + 100
        
        self.enemy_manager = EnemyManager()
        self.enemy_manager.set_difficulty("normal")
        self.item_manager = ItemManager()
        
        self._set_map_boundaries()
        
        self.game_time = 0
        self.kill_num = 0
        self.level = 1
        
        self.camera_x = self.player.world_x
        self.camera_y = self.player.world_y
        
        resource_manager.play_map_music(map_id, loops=-1)
        
        if self.network_mode and self.remote_player:
            self.remote_player.world_x = self.player.world_x + 80
            self.remote_player.world_y = self.player.world_y
        
    def _back_to_main_menu(self):
        if self.network_mode:
            self._return_to_lobby()
            return
        self.in_map_hero_select = False
        self.in_main_menu = True
        self._play_menu_music()
        
    def _play_menu_music(self):
        resource_manager.play_music("menu", loops=-1)
        
    def _play_game_music(self):
        resource_manager.play_music("background", loops=-1)
        
    def start_new_game(self):
        self.in_main_menu = False
        self.in_map_hero_select = True
        self.map_hero_select_menu.show()
            
    def load_map(self, map_name):
        success = self.map_manager.load_map(map_name)
        if success:
            self.current_map = map_name
            
            map_width, map_height = self.map_manager.get_map_size()
            
            if self.player:
                self.player.world_x = map_width // 2
                self.player.world_y = map_height // 2
                
                self.camera_x = self.player.world_x
                self.camera_y = self.player.world_y
                
                self._set_map_boundaries()
            
        else:
            print(f"加载地图 '{map_name}' 失败")
            
        return success

    def load_game_state(self, save_data):
        try:
            self.in_main_menu = False
            self.game_over = False
            self.paused = False
            
            player_data = save_data.get('player_data', {})
            if not player_data:
                print("存档数据损坏：缺少玩家数据")
                return False
                
            hero_type = player_data.get('hero_type', 'ninja_frog')
            self.player = Player(self.screen_center_x, self.screen_center_y, hero_type)
            
            self.player.health = player_data.get('health', self.player.health)
            self.player.health_component.max_health = player_data.get('max_health', self.player.health_component.max_health)
            self.player.progression.level = player_data.get('level', self.player.progression.level)
            self.player.progression.experience = player_data.get('experience', 0)
            self.player.progression.coins = player_data.get('coins', 0)
            self.player.world_x = player_data.get('world_x', self.screen_center_x)
            self.player.world_y = player_data.get('world_y', self.screen_center_y)
            
            component_states = player_data.get('component_states', {})
            if component_states:
                movement_states = component_states.get('movement', {})
                if movement_states:
                    self.player.movement.speed = movement_states.get('speed', self.player.movement.speed)
                    self.player.movement.direction = pygame.math.Vector2(0, 0)
                    self.player.movement.velocity = pygame.math.Vector2(0, 0)
                    self.player.movement.moving = {
                        'up': False, 
                        'down': False, 
                        'left': False, 
                        'right': False
                    }
                    if 'facing_right' in movement_states:
                        self.player.movement.facing_right = movement_states.get('facing_right')
                    if 'last_direction_x' in movement_states and 'last_direction_y' in movement_states:
                        self.player.movement.last_movement_direction.x = movement_states.get('last_direction_x', 1)
                        self.player.movement.last_movement_direction.y = movement_states.get('last_direction_y', 0)
                
                health_states = component_states.get('health', {})
                if health_states:
                    self.player.health_component.defense = health_states.get('defense', self.player.health_component.defense)
                    self.player.health_component.health_regen = health_states.get('health_regen', self.player.health_component.health_regen)
                
                progression_states = component_states.get('progression', {})
                if progression_states:
                    self.player.progression.exp_multiplier = progression_states.get('exp_multiplier', self.player.progression.exp_multiplier)
                    self.player.progression.luck = progression_states.get('luck', self.player.progression.luck)
                
                passive_states = component_states.get('passive', {})
                if passive_states and 'passive_levels' in passive_states:
                    passive_levels = passive_states['passive_levels']
                    for passive_type, level in passive_levels.items():
                        if passive_type in self.upgrade_manager.passive_upgrades:
                            upgrade = self.upgrade_manager.passive_upgrades[passive_type]
                            effect = None
                            for lvl in upgrade.levels:
                                if lvl.level == level:
                                    effect = lvl.effects
                                    break
                            if effect:
                                self.player.apply_passive_upgrade(passive_type, level, effect)
                            else:
                                self.player.passive_manager.passive_levels[passive_type] = level
                        else:
                            self.player.passive_manager.passive_levels[passive_type] = level
                    self.player._update_stats()
            
            weapons_data = player_data.get('weapons', [])
            if weapons_data:
                for weapon in list(self.player.weapons):
                    self.player.weapon_manager.remove_weapon(weapon.type)
                
                for weapon_type, level in weapons_data:
                    weapon = self.player.add_weapon(weapon_type)
                    if weapon:
                        weapon.level = level
            
            self.enemy_manager = EnemyManager()
            self.item_manager = ItemManager()
            
            game_data = save_data.get('game_data', {})
            self.game_time = game_data.get('game_time', 0)
            self.kill_num = game_data.get('kill_num', 0)
            self.level = game_data.get('level', 1)
            
            self.enemy_manager.difficulty_level = self.level
            self.enemy_manager.set_difficulty(game_data.get('difficulty', 'normal'))
            self.enemy_manager.game_time = self.game_time
            self.enemy_manager.recalculate_difficulty()
            
            enemies_data = save_data.get('enemies_data', [])
            for enemy_data in enemies_data:
                try:
                    self.enemy_manager.spawn_enemy(
                        enemy_data.get('type', 'normal'),
                        enemy_data.get('x', 0),
                        enemy_data.get('y', 0),
                        enemy_data.get('health', 50)
                    )
                except Exception as e:
                    print(f"加载敌人时出错: {e}")
                    continue
            
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
            
            self._set_map_boundaries()
            
            resource_manager.play_music("background", loops=-1)
            
            return True
            
        except Exception as e:
            print(f"加载存档时出错: {e}")
            self.start_new_game()
            return False
        
    def handle_event(self, event):
        if self.show_disconnect_popup:
            return
        
        if self.in_map_hero_select:
            result = self.map_hero_select_menu.handle_event(event)
            return
            
        if self.in_main_menu:
            if self.load_menu.is_active:
                action = self.load_menu.handle_event(event)
                if action == "back":
                    self.load_menu.hide()
                elif isinstance(action, dict):
                    if self.load_game_state(action):
                        self.in_main_menu = False
                        self.load_menu.hide()
                    else:
                        print("加载存档失败")
                return
            
            action = self.main_menu.handle_event(event)
            if action == "start":
                self.start_new_game()
            elif action == "load":
                print("显示读取菜单")
                self.load_menu.show()
            elif action == "multiplayer":
                self._return_to_lobby()
            elif action == "quit":
                self.running = False
            return
            
        if self.load_menu.is_active:
            action = self.load_menu.handle_event(event)
            if action == "back":
                self.load_menu.hide()
            elif isinstance(action, dict):
                if self.load_game_state(action):
                    self.load_menu.hide()
                    self.paused = False
                else:
                    print("加载存档失败")
            return
            
        if self.save_menu.is_active:
            action = self.save_menu.handle_event(event)
            if action and action.startswith("slot_"):
                slot_id = int(action.split("_")[1])
                self.save_system.save_game(slot_id, self, self.screen)
                self.save_menu.hide()
                self.paused = False
            elif action == "back":
                self.save_menu.hide()
            return
            
        if self.game_over:
            action = self.game_over_menu.handle_event(event)
            if action == "restart":
                self.start_new_game()
            elif action == "main_menu":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.in_main_menu = True
                    self.game_over = False
                    self._play_menu_music()
            elif action == "exit":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.running = False
            return
            
        if self.paused:
            action = self.pause_menu.handle_event(event)
            if action == "continue":
                self.toggle_pause()
            elif action == "save":
                self.save_menu.show()
            elif action == "restart":
                self.start_new_game()
            elif action == "main_menu":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.in_main_menu = True
                    self.paused = False
                    self._play_menu_music()
            elif action == "exit":
                if self.network_mode:
                    self._return_to_lobby()
                else:
                    self.running = False
            return
               
        if self.upgrade_menu.is_active:
            selected_upgrade = self.upgrade_menu.handle_event(event)
            if selected_upgrade:
                self._apply_upgrade(selected_upgrade)
                self.upgrade_menu.hide()
            return True
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.toggle_pause()
                return True
            elif event.key == pygame.K_F2:
                if self.player:
                    self.player.toggle_outline()
                    for enemy in self.enemy_manager.enemies:
                        enemy.toggle_outline()
                return True
            
        if self.player:
            self.player.handle_event(event)
            
        return True
        
    def _apply_upgrade(self, upgrade_level):
        if isinstance(upgrade_level, WeaponUpgradeLevel):
            weapon_type = None
            for type_, upgrade in self.upgrade_manager.weapon_upgrades.items():
                if upgrade_level in upgrade.levels:
                    weapon_type = type_
                    break
                    
            if weapon_type:
                if self.player.apply_weapon_upgrade(weapon_type, upgrade_level.level, upgrade_level.effects):
                    if len([w for w in self.player.weapons if w.type == weapon_type]) == 0:
                        self.player.add_weapon(weapon_type)
                        
        elif isinstance(upgrade_level, PassiveUpgradeLevel):
            passive_type = None
            for type_, upgrade in self.upgrade_manager.passive_upgrades.items():
                if upgrade_level in upgrade.levels:
                    passive_type = type_
                    break
                    
            if passive_type:
                self.player.apply_passive_upgrade(passive_type, upgrade_level.level, upgrade_level.effects)
                
    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_menu.show()
            resource_manager.pause_music()
        else:
            self.pause_menu.hide()
            resource_manager.unpause_music()
        
    def update(self, dt):
        if self.show_disconnect_popup:
            self.disconnect_popup_timer -= dt
            if self.disconnect_popup_timer <= 0:
                self._return_to_lobby()
            return
        
        if self.in_main_menu:
            return
            
        if self.in_map_hero_select:
            return
            
        if self.network_mode:
            net_client = get_network_client()
            if not net_client.is_connected():
                if not self.show_disconnect_popup:
                    self.disconnect_message = "网络连接已中断"
                    self.show_disconnect_popup = True
                    self.disconnect_popup_timer = 2.0
                return
            
            remote_data = net_client.get_remote_player_data()
            if remote_data:
                self.remote_player_data = remote_data
                if self.remote_player:
                    self.remote_player.update_from_network(remote_data)
            
            self.network_sync_timer += dt
            if self.network_sync_timer >= self.network_sync_interval and self.player:
                self.network_sync_timer = 0
                is_moving = self.player.movement.is_moving()
                facing_right = self.player.movement.facing_right
                is_hurt = self.player.health_component.is_hurt()
                
                net_client.send_player_data(
                    self.player.world_x,
                    self.player.world_y,
                    self.player.health,
                    self.player.max_health,
                    self.player.hero_type,
                    is_moving,
                    facing_right,
                    is_hurt
                )
            
        if self.player and self.player.health <= 0 and not self.game_over:
            self.game_over = True
            self.game_over_menu.show()
            resource_manager.play_sound("player_death")
            return
            
        if self.game_over:
            self.game_over_menu.update(pygame.mouse.get_pos())
            return
            
        if self.paused or self.upgrade_menu.is_active or self.save_menu.is_active:
            return
            
        self.game_time += dt
        
        if self.player:
            self.player.update(dt)
            
            self.camera_x = self.player.world_x
            self.camera_y = self.player.world_y
        
        if self.network_mode and self.remote_player:
            self.remote_player.update(dt)
        
        if self.enemy_manager and self.player:
            for enemy in list(self.enemy_manager.enemies):
                if enemy in self.enemy_manager.enemies and not enemy.alive():
                    self.kill_num += 1
                    if self.item_manager:
                        self.item_manager.spawn_item(enemy.rect.x, enemy.rect.y, enemy.type, self.player)
            
            self.enemy_manager.update(dt, self.player)
            self.player.update_weapons(dt, self.enemy_manager.enemies)
            
            if self.item_manager:
                self.item_manager.update(dt, self.player)
            
            self._check_collisions()
            
            if self.player.add_experience(0):
                self.player.level_up()
                self.upgrade_menu.show(self.player, self)
        
    def render(self):
        self.screen.fill((0, 0, 0))
        
        if self.in_main_menu:
            if self.load_menu.is_active:
                self.load_menu.render()
            else:
                self.main_menu.render()
            pygame.display.flip()
            return
            
        if self.in_map_hero_select:
            self.map_hero_select_menu.render()
            pygame.display.flip()
            return
            
        if self.save_menu.is_active:
            self.save_menu.render()
            return
            
        if self.current_map:
            self.map_manager.render(self.camera_x, self.camera_y)
        else:
            self._draw_grid()
        
        if self.enemy_manager:
            self.enemy_manager.render(self.screen, self.camera_x, self.camera_y, 
                                   self.screen_center_x, self.screen_center_y)
        
        if self.item_manager:
            self.item_manager.render(self.screen, self.camera_x, self.camera_y, 
                                  self.screen_center_x, self.screen_center_y)
        
        if self.network_mode and self.remote_player:
            self.remote_player.render(self.screen, self.camera_x, self.camera_y,
                                     self.screen_center_x, self.screen_center_y)
        
        if self.player:
            self.player.render(self.screen)
            self.player.render_weapons(self.screen, self.camera_x, self.camera_y)
            
            self.ui.render(self.player, self.game_time, self.kill_num)
            
        if self.paused:
            self.pause_menu.render()
            
        if self.save_menu.is_active:
            self.save_menu.render()
            
        if self.upgrade_menu.is_active:
            self.upgrade_menu.render()
            
        if self.game_over:
            self.game_over_menu.render()
        
        if self.show_disconnect_popup:
            self._render_disconnect_popup()
            
        pygame.display.flip()
    
    def _render_disconnect_popup(self):
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        popup_width = 500
        popup_height = 150
        popup_x = (self.screen.get_width() - popup_width) // 2
        popup_y = (self.screen.get_height() - popup_height) // 2
        
        pygame.draw.rect(self.screen, (60, 30, 30), (popup_x, popup_y, popup_width, popup_height), border_radius=15)
        pygame.draw.rect(self.screen, (200, 80, 80), (popup_x, popup_y, popup_width, popup_height), 3, border_radius=15)
        
        if self.disconnect_message:
            text = self.popup_font.render(self.disconnect_message, True, (255, 100, 100))
        else:
            text = self.popup_font.render("连接已断开，正在返回大厅...", True, (255, 100, 100))
        text_rect = text.get_rect(center=(self.screen.get_width() // 2, popup_y + popup_height // 2))
        self.screen.blit(text, text_rect)
        
    def _draw_grid(self):
        offset_x = (self.camera_x % self.grid_size)
        offset_y = (self.camera_y % self.grid_size)
        
        for i in range(int(self.screen.get_width() / self.grid_size) + 2):
            x = i * self.grid_size - offset_x
            pygame.draw.line(self.screen, self.grid_color, (x, 0), (x, self.screen.get_height()))
            
        for i in range(int(self.screen.get_height() / self.grid_size) + 2):
            y = i * self.grid_size - offset_y
            pygame.draw.line(self.screen, self.grid_color, (0, y), (self.screen.get_width(), y))
        
    def _check_collisions(self):
        if not self.player or not self.enemy_manager:
            return
            
        for weapon in self.player.weapons:
            for projectile in weapon.get_projectiles():
                for enemy in self.enemy_manager.enemies:
                    dx = enemy.rect.x - projectile.world_x
                    dy = enemy.rect.y - projectile.world_y
                    distance = (dx**2 + dy**2)**0.5
                    
                    if distance < enemy.rect.width / 2 + projectile.rect.width / 2:
                        projectile_rect = projectile.rect.copy()
                        projectile_rect.centerx = projectile.world_x
                        projectile_rect.centery = projectile.world_y
                        
                        if apply_mask_collision(enemy, projectile):
                            should_destroy = weapon.handle_collision(projectile, enemy, self.enemy_manager.enemies)
                            resource_manager.play_sound("hit")
                            
                            if enemy.health <= 0:
                                self.kill_num += 1
                                if self.item_manager:
                                    self.item_manager.spawn_item(enemy.rect.x, enemy.rect.y, enemy.type, self.player)
                                self.enemy_manager.remove_enemy(enemy)
                                resource_manager.play_sound("enemy_death")
                                
                            if should_destroy:
                                projectile.kill()
        
        for enemy in self.enemy_manager.enemies:
            if not self.player.invincible:
                player_rect = self.player.rect.copy()
                player_rect.centerx = self.player.world_x
                player_rect.centery = self.player.world_y
                
                if hasattr(enemy, 'projectiles'):
                    enemy.attack_player(self.player)
                
                if player_rect.colliderect(enemy.rect):
                    if enemy.type == 'skt' and getattr(enemy, 'current_form', 1) == 1:
                        continue
                    
                    if enemy.type == 'plant':
                        continue
                    
                    saved_rect = self.player.rect
                    self.player.rect = player_rect
                    collided = apply_mask_collision(self.player, enemy)
                    self.player.rect = saved_rect
                    if collided:
                        damage_amount = enemy.damage * 0.5
                        if self.player.take_damage(damage_amount):
                            resource_manager.play_sound("player_hurt")
                            self._knockback_player(enemy)
                            break
        
    def _update_game_state(self):
        current_level = int(self.game_time // 60) + 1
        
        if current_level > self.level:
            resource_manager.play_sound("level_up")
            
        self.level = current_level
        
        if self.enemy_manager:
            self.enemy_manager.difficulty_level = self.level
    
    def _knockback_player(self, enemy):
        if not self.player or not enemy:
            return
        
        dx = self.player.world_x - enemy.rect.centerx
        dy = self.player.world_y - enemy.rect.centery
        distance = (dx**2 + dy**2)**0.5
        
        if distance == 0:
            return
        
        dx = dx / distance
        dy = dy / distance
        
        knockback_distance = 50
        self.player.world_x += dx * knockback_distance
        self.player.world_y += dy * knockback_distance
