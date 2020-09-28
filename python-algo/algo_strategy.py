import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from collections import defaultdict
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
        global WALL, FACTORY, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        FACTORY = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        self.spawned = [0, 0, 0]
        self.possible_brake_through_locations = []
        self.scored_on_locations = []
        self.damaged_areas = []
        self.spawn_locations = []
        self.spawn_id_locations = {}

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
        self.spawned = [0, 0, 0]
        self.possible_brake_through_locations = []
        self.scored_on_locations = []
        self.damaged_areas = []
        self.spawn_locations = []

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        if game_state.turn_number == 0:
            game_state.attempt_spawn(INTERCEPTOR, [
                [1, 12],
                [1, 12],
                [4, 9],
                [23, 9],
                [26, 12]
                ])
        else:
            self.build_reactive_defense(game_state)
        self.build_defences(game_state)
        self.build_factories(game_state)
        self.attack(game_state)

    def build_factories(self, game_state):
        switch = 1
        x = 13
        hit_limit = False
        retry = False
        while True:
            for y in range(8):
                if game_state.get_resource(SP) < game_state.type_cost(FACTORY)[SP]:
                    return
                game_state.attempt_spawn(FACTORY, [x, y])
                if (x > 12 and x < 15) or hit_limit:
                    game_state.attempt_upgrade([x, y])
            game_state.attempt_spawn(WALL, [[13, 8], [13, 9], [13, 10]])
            game_state.attempt_spawn(TURRET, [[x, 11]])
            game_state.attempt_spawn(WALL, [x, 12])
            game_state.attempt_upgrade([[x, 11], [x, 12]])
            x += switch
            switch = -(switch+switch//abs(switch))
            if x < 5 or x > 22:
                if retry:
                    return
                retry = True
                hit_limit = True
                x = 11

    def build_defences(self, game_state):
        """
        Build basic defenses using hardcoded locations.
        Remember to defend corners and avoid placing units in the front where enemy demolishers can attack them.
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets that attack enemy units
        turret_locations = [[9, 6], [18, 6]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        game_state.attempt_spawn(TURRET, turret_locations)
        game_state.attempt_upgrade(turret_locations)

        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[9, 7], [18, 7]]
        game_state.attempt_spawn(WALL, wall_locations)
        # upgrade walls so they soak more damage
        game_state.attempt_upgrade(wall_locations)
        damaged_area_set = {tuple(i[0]) for i in self.damaged_areas}
        for damaged_area in damaged_area_set:
            damaged_unit = game_state.contains_stationary_unit(damaged_area)
            if damaged_unit and damaged_unit.health/damaged_unit.max_health < 0.5:
                if game_state.can_spawn(TURRET, [damaged_area[0]-1, damaged_area[1]]):
                    turret_locations = [damaged_area[0]-1, damaged_area[1]]
                    wall_locations = [damaged_area[0]-1, damaged_area[1]+1]
                else:
                    turret_locations = [damaged_area[0]+1, damaged_area[1]]
                    wall_locations = [damaged_area[0]+1, damaged_area[1]+1]
                game_state.attempt_spawn(TURRET, turret_locations)
                game_state.attempt_upgrade(turret_locations)
                game_state.attempt_spawn(WALL, wall_locations)
                game_state.attempt_upgrade(wall_locations)
            elif not damaged_unit:
                turret_locations = [damaged_area[0], damaged_area[1]]
                wall_locations = [damaged_area[0], damaged_area[1]+1]
                game_state.attempt_spawn(TURRET, turret_locations)
                game_state.attempt_upgrade(turret_locations)
                game_state.attempt_spawn(WALL, wall_locations)
                game_state.attempt_upgrade(wall_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for scored_on_location in self.scored_on_locations:
            path = game_state.find_path_to_edge(scored_on_location)
            if path:
                location = [i for i in path if i[1] == 13]
                if location:
                    location = location[0]
                if type(location) == list and len(location) == 2:
                    if location[0] == 0:
                        game_state.attempt_spawn(WALL, [location[0], location[1]])
                        game_state.attempt_upgrade([location[0], location[1]])
                        location[0] += 1
                    elif location[0] == 27:
                        game_state.attempt_spawn(WALL, [location[0], location[1]])
                        game_state.attempt_upgrade([location[0], location[1]])
                        location[0] -= 1
                    game_state.attempt_spawn(TURRET, [location[0], location[1]-1])
                    game_state.attempt_spawn(WALL, [location[0], location[1]])
                    game_state.attempt_upgrade([
                        [location[0], location[1]-1], 
                        [location[0], location[1]]
                        ])

        location_scored_counts = defaultdict(int)
        for location in self.scored_on_locations:
            location_scored_counts[tuple(location)] += 1

        for spawn_location in self.spawn_locations:
            path = game_state.find_path_to_edge(spawn_location)
            if path:
                gamelib.debug_write("spawn_locations", spawn_location)
                breach_location = path[0]
                location_scored_counts[tuple(breach_location)] += 1

        for possible_brake_through_location in self.possible_brake_through_locations:
            gamelib.debug_write("possible_brake_through_location", possible_brake_through_location)
            location_scored_counts[tuple(possible_brake_through_location)] += 1

        location_scored_counts_sum = sum(location_scored_counts.values())
        location_scored_counts_list = []
        mp = game_state.get_resource(MP)
        for scored_count, location in enumerate(location_scored_counts):
            location_scored_counts_list.append([scored_count, location])
        location_scored_counts_list.sort()
        location_scored_counts_list.reverse()
        gamelib.debug_write("location_scored_counts_list", location_scored_counts_list)
        for scored_count, location in location_scored_counts_list:
            can_spawn = False
            for i in [0, 1, -1, 2, -2]:
                if location in game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT):
                    location = [location[0]+i, location[1]-i]
                else:
                    location = [location[0]-i, location[1]+i]
                for num_spawns in range(math.ceil(location[0]/location_scored_counts_sum*mp)):
                    if game_state.can_spawn(INTERCEPTOR, location):
                        can_spawn = True
                        game_state.attempt_spawn(INTERCEPTOR, location)
                if can_spawn:
                    break

    def attack(self, game_state):
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        damage_locations = self.least_damage_spawn_location(game_state, friendly_edges)
        attack_locations = self.largest_attack_spawn_location(game_state, friendly_edges)

        demolisher_damage_locations = sorted(zip(damage_locations[1],friendly_edges))
        if demolisher_damage_locations[0][0] == 0:
            location = demolisher_damage_locations[0][1]
            if game_state.can_spawn(DEMOLISHER, location):
                while game_state.get_resource(MP) >= 3:
                    game_state.attempt_spawn(DEMOLISHER, location)
        else:
            scout_damage_minus_wall_attack = [damage - attack*0.25 for damage, attack in zip(damage_locations[0], [i[0] for i in attack_locations[0]])]
            scout_damage_minus_factory_attack = [damage - attack*0.25 for damage, attack in zip(damage_locations[0], [i[1] for i in attack_locations[0]])]
            min_scout_damage_minus_attack = [min(i, j) for i, j in zip(scout_damage_minus_wall_attack, scout_damage_minus_factory_attack)]
            locations = [x for _,x in sorted(zip(min_scout_damage_minus_attack,friendly_edges))]
            location = random.choice(self.filter_blocked_locations(friendly_edges, game_state))
            for i in locations:
                if game_state.can_spawn(SCOUT, i) and len(game_state.find_path_to_edge(i)) > 4:
                    location = i
                    break
            if game_state.can_spawn(SCOUT, location):
                while game_state.get_resource(MP) >= 1:
                    game_state.attempt_spawn(SCOUT, location)

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = [[], []]
        # Get the damage estimate each path will take
        for i, attacker in enumerate([SCOUT, DEMOLISHER]):
            for location in location_options:
                path = game_state.find_path_to_edge(location)
                damage = 0
                if path:
                    for path_location in path:
                        # Get number of enemy turrets that can attack each location and multiply by turret damage
                        damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i * (i+1)
                damage += self.spawned[2] * gamelib.GameUnit(INTERCEPTOR, game_state.config).damage_i
                damages[i].append(damage)
            
        # Now just return the location that takes the least damage
        return damages

    def largest_attack_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        attacks = [[], []]
        # Get the damage estimate each path will take
        for i, attacker in enumerate([SCOUT, DEMOLISHER]):
            for location in location_options:
                path = game_state.find_path_to_edge(location)
                attack = [0, 0]
                if path:
                    for path_location in path:
                        for attack_loc in game_state.game_map.get_locations_in_range(path_location, gamelib.GameUnit(attacker, game_state.config).attackRange):
                            if game_state.contains_stationary_unit(attack_loc):
                                if game_state.contains_stationary_unit(attack_loc).unit_type == WALL:
                                    attack[0] += gamelib.GameUnit(attacker, game_state.config).damage_f * (i+1)
                                elif game_state.contains_stationary_unit(attack_loc).unit_type == FACTORY:
                                    attack[1] += gamelib.GameUnit(attacker, game_state.config).damage_f * (i+1) * 2
                attacks[i].append(attack)
        
        # Now just return the location that takes the least damage
        return attacks

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        spawns = events["spawn"]
        damages = events["damage"]
        units = []
        if state["turnInfo"][2] == 0:
            for spawn in spawns:
                if spawn[3] == 2 and spawn[1] in [3, 4, 5]:
                    self.spawned[spawn[1]-3] += 1
                    self.spawn_id_locations[spawn[2]] = spawn[0]
                    self.spawn_locations.append(spawn[0])
            units = [j for i in [3, 4, 5] for j in state["p2Units"][i]]
        game_state = gamelib.GameState(self.config, turn_string)
        for unit in units:
            if unit[1] == 11:
                if self.spawn_id_locations[unit[3]] in game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT):
                    path = game_state.find_path_to_edge([unit[0], unit[1]], game_state.game_map.BOTTOM_RIGHT)
                else:
                    path = game_state.find_path_to_edge([unit[0], unit[1]], game_state.game_map.BOTTOM_LEFT)
                if path:
                    self.possible_brake_through_locations.append(path[-1])
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                self.scored_on_locations.append(location)
        for damage in damages:
            if damage[2] in [0, 1, 2]:
                self.damaged_areas.append(damage)


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
