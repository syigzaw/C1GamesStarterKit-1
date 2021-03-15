import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from collections import Counter, defaultdict
import math
import random

"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.destroyed_locations = []
        self.attack_path = []
        self.attacking_from_left = True

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)
        self.attack_path = []
        self.attacking_from_left = True

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        self.attack(game_state)
        self.build_formation(game_state)

    def build_formation(self, game_state):
        stuff_to_destroy = []
        turret_spacing = 4
        if game_state.SP <= 30:
            turret_spacing = 8
        elif game_state.SP <= 50:
            turret_spacing = 6

        game_state.attempt_spawn(SUPPORT, [13,9])
        game_state.attempt_upgrade([13,9])

        # Corner stoppers
        for i in range(3):
            for j in range(3-i):
                if [2-j,13-i] in self.destroyed_locations:
                    game_state.attempt_spawn(WALL, [2-j,13-i])
                    game_state.attempt_upgrade([2-j,13-i])
                elif [2-j,13-i] not in self.attack_path:
                    game_state.attempt_spawn(WALL, [2-j,13-i])
                if [25+j,13-i] in self.destroyed_locations:
                    game_state.attempt_spawn(WALL, [25+j,13-i])
                    game_state.attempt_upgrade([25+j,13-i])
                elif [25+j,13-i] not in self.attack_path:
                    game_state.attempt_spawn(WALL, [25+j,13-i])
                stuff_to_destroy.append([2-j,13-i])
                stuff_to_destroy.append([25+j,13-i])

        x_pos = range(23, 3, -1)
        if self.attacking_from_left:
            x_pos = range(4, 24)

        # Second wall
        for x in x_pos:
            if [x, 11] in self.destroyed_locations or x % turret_spacing == 0:
                game_state.attempt_spawn(TURRET, [x, 11])
                if turret_spacing == 4:
                    game_state.attempt_upgrade([x, 11])
            else:
                game_state.attempt_spawn(WALL, [x, 11])
            stuff_to_destroy.append([x, 11])

        x_pos = range(2, 26)
        if self.attacking_from_left:
            x_pos = range(25, 1, -1)

        # First wall
        for x in x_pos:
            if [x, 13] not in self.attack_path:
                if [x, 13] in self.destroyed_locations or x % turret_spacing == 0:
                    game_state.attempt_spawn(TURRET, [x, 13])
                    if turret_spacing == 4:
                        game_state.attempt_upgrade([x, 13])
                else:
                    game_state.attempt_spawn(WALL, [x, 13])
                stuff_to_destroy.append([x, 13])

        # V
        for i in range(8):
            if [13-i,2+i] in self.destroyed_locations:
                game_state.attempt_spawn(TURRET, [13-i,2+i])
                game_state.attempt_upgrade([13-i,2+i])
            else:
                game_state.attempt_spawn(WALL, [13-i,2+i])
            stuff_to_destroy.append([13-i,2+i])
            if [14+i,2+i] in self.destroyed_locations:
                game_state.attempt_spawn(TURRET, [14+i,2+i])
                game_state.attempt_upgrade([14+i,2+i])
            else:
                game_state.attempt_spawn(WALL, [14+i,2+i])
            stuff_to_destroy.append([14+i,2+i])

        game_state.attempt_remove(stuff_to_destroy)

    def check_enemy_removes(self, game_state):
        """
        This function will return the list of where to put turrets to defend from enemy removes,
        from most important to least important
        """
        if len(self.removes)==0:
            return []
        lst = []
        for rem in self.removes:
            temp = game_state.game_map.get_locations_in_range([rem[0],rem[1]], 2.5)
            for i in temp:
                lst += (i[0],i[1])
        cntd = Counter(lst)
        return  sorted(cntd, key=cntd.get, reverse=True)
        
    def attack(self, game_state):
        friendly_edges = [list(i) for i in list(
            (set(tuple(i) for i in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)) | 
            set(tuple(i) for i in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT))) - 
            set([(0,13),(1,12),(2,11),(27,13),(26,12),(25,11)])
            )]
        damage_locations = self.least_damage_spawn_location(game_state, friendly_edges)
        attack_locations = self.largest_attack_spawn_location(game_state, friendly_edges)

        sorted_damage_locations = sorted(zip(damage_locations,friendly_edges))
        location = sorted_damage_locations[0][1]
        gamelib.debug_write(location)
        gamelib.debug_write(game_state.find_path_to_edge(location))
        if not game_state.find_path_to_edge(location):
            gamelib.debug_write(game_state.contains_stationary_unit(location))
        self.attack_path.extend(game_state.find_path_to_edge(location))
        self.attacking_from_left = location in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT)
        if self.attacking_from_left:
            game_state.attempt_spawn(WALL, [3, 11])
            game_state.attempt_remove([3, 11])
            if sorted_damage_locations[0][0] == 0:
                while game_state.get_resource(MP) >= 3:
                    game_state.attempt_spawn(DEMOLISHER, [3, 10])
            else:
                game_state.attempt_spawn(WALL, [5, 9])
                game_state.attempt_remove([5, 9])
                for i in range(3):
                    game_state.attempt_spawn(DEMOLISHER, [3, 10])
                while game_state.get_resource(MP) >= 1:
                    game_state.attempt_spawn(SCOUT, [5, 8])
        else:
            game_state.attempt_spawn(WALL, [24, 11])
            game_state.attempt_remove([24, 11])
            if sorted_damage_locations[0][0] == 0:
                while game_state.get_resource(MP) >= 3:
                    game_state.attempt_spawn(DEMOLISHER, [24, 10])
            else:
                game_state.attempt_spawn(WALL, [22, 9])
                game_state.attempt_remove([22, 9])
                for i in range(3):
                    game_state.attempt_spawn(DEMOLISHER, [24, 10])
                while game_state.get_resource(MP) >= 1:
                    game_state.attempt_spawn(SCOUT, [22, 8])

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            if path:
                for path_location in path:
                    # Get number of enemy turrets that can attack each location and multiply by turret damage
                    damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)
        
        # Now just return the location that takes the least damage
        return damages

    def largest_attack_spawn_location(self, game_state, location_options):
        attacks = [[], []]
        # Get the damage estimate each path will take
        for i, attacker in enumerate([SCOUT, DEMOLISHER]):
            for location in location_options:
                path = game_state.find_path_to_edge(location)
                attack = 0
                if path:
                    for path_location in path:
                        enemy_structure_in_range = False
                        for attack_loc in game_state.game_map.get_locations_in_range(path_location, gamelib.GameUnit(attacker, game_state.config).attackRange):
                            if game_state.contains_stationary_unit(attack_loc) and game_state.contains_stationary_unit(attack_loc).player_index == 1:
                                enemy_structure_in_range = True
                        if enemy_structure_in_range:
                            attack += gamelib.GameUnit(attacker, game_state.config).damage_f * (3 if attacker == SCOUT else 8)
                attacks[i].append(attack)
        
        return attacks

    def enemy_least_damage_location(self, game_state):
        damages = []
        enemy_edges = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + \
                      game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        
        all_paths = []
        for location in enemy_edges:
            path = game_state.find_path_to_edge(location)
            all_paths.append(path)
            damage = 0
            if path:
                for path_location in path:
                    # Get number of enemy turrets that can attack each location and multiply by turret damage
                    damage += len(game_state.get_attackers(path_location, 1)) * gamelib.GameUnit(TURRET,
                                                                                                 game_state.config).damage_i
            damages.append(damage)
        if not damages:
            return []

        probable_attack_path = all_paths[damages.index(min(damages))]
        filtered_attack_path = []
        if probable_attack_path:
            filtered_attack_path = list(filter(lambda x: True if x[1] <= 13 else False, probable_attack_path))

        return filtered_attack_path


    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        spawns = events["spawn"]
        damages = events["damage"]
        deaths = events["death"]
        game_state = gamelib.GameState(self.config, turn_string)
        for death in deaths:
            if death[1] in [0, 1, 2] and death[3] == 1 and not death[4]:
                self.destroyed_locations.append(death[0])


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
