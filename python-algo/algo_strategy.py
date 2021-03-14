import gamelib
import random
import math
import warnings
from sys import maxsize
import json

# Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
# More community tools available at: https://terminal.c1games.com/rules#Download

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
        self.scored_on_locs = []
        self.score_locs = []
        self.damaged_locs = []
        self.friendly_edges = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], [11, 2], [12, 1], [13, 0],
                              [14, 0], [15, 1], [16, 2], [17, 3], [18, 4], [19, 5], [20, 6], [21, 7], [22, 8], [23, 9], [24, 10], [25, 11], [26, 12], [27, 13]]

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        game_state.attempt_spawn(DEMOLISHER, [24, 10], 3)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        # clear arrays
        self.scored_on_locs = []
        self.score_locs = []
        self.enemy_turrets = []
        self.damaged_locs = []

        game_state.submit_turn()


    """
    NOTE: All the methods after this point are part of the sample starter-algo
    strategy and can safely be replaced for your custom algo.
    """

    def starter_strategy(self, game_state):
        """
        For defense we will use a spread out layout and some interceptors early on.
        We will place turrets near locations the opponent managed to score on.
        For offense we will use long range demolishers if they place stationary units near the enemy's front.
        If there are no stationary units to attack in the front, we will send Scouts to try and score quickly.
        """

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number == 0:
            # Place basic defenses
            turret_locs = [[3, 12], [10, 12], [12, 12], [15, 12], [17, 12], [24, 12]]
            wall_locs = [[2, 13], [3, 13], [4, 13], [5, 13], [9, 13], [10, 13], [11, 13], [12, 13], [13, 13],
                         [14,13], [15, 13], [16, 13], [17, 13], [18, 13], [22, 13], [23, 13], [24, 13], [25, 13]]
            game_state.attempt_spawn(TURRET, turret_locs)
            game_state.attempt_spawn(WALL, wall_locs)

            deploy_locations = self.filter_blocked_locations(self.friendly_edges, game_state)

            # While we have remaining MP to spend lets send out interceptors randomly.
            while game_state.get_resource(MP) >= game_state.type_cost(TURRET)[MP] and len(deploy_locations) > 0:
                # Choose a random deploy location.
                deploy_index = random.randint(0, len(deploy_locations) - 1)
                deploy_location = deploy_locations[deploy_index]

                game_state.attempt_spawn(TURRET, deploy_location)

        else:
            # Build reactive defenses based on where the enemy scored
            self.he_reactiv_protec(game_state)
            self.he_attac(game_state)

            # If we have spare SP, randomly build some Support near the middle of our field
            support_locations = [[14, 9], [4, 11], [13, 3], [23, 11]]
            while game_state.get_resource(SP) >= game_state.type_cost(SUPPORT)[SP]:
                game_state.attempt_spawn(SUPPORT, support_locations)

    def he_reactiv_protec(self, game_state):
        #? put turrets where enemies break through, replace units with health < 50%, upgrade with leftover points
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locs:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1]+1]
            game_state.attempt_spawn(TURRET, build_location)

        damaged_area_set = {tuple(i[0]) for i in self.damaged_locs}
        replaced_units = []
        for elem in self.damaged_locs:
            if damaged_area_set.issuperset(set(elem[0])):
                damaged_area = elem[0]
                damaged_area_set.remove(elem[0])
                damaged_unit = game_state.contains_stationary_unit(damaged_area)

                # replace unit if damaged
                if damaged_unit and (damaged_unit.health/damaged_unit.max_health) < 0.5:
                    game_state.attempt_remove([damaged_area[0], damaged_area[1]])

                # go in order of importance
                if elem[2] == 2:
                    game_state.attempt_spawn(TURRET, [damaged_area[0], damaged_area[1]])
                elif elem[2] == 0:
                    game_state.attempt_spawn(WALL, [damaged_area[0], damaged_area[1]])
                elif elem[2] == 1:
                    game_state.attempt_spawn(SUPPORT, [damaged_area[0], damaged_area[1]])

                replaced_units.append(elem)

        # upgrade Turrets & Walls if we have remaining SP
        for unit in replaced_units:
            game_state.attempt_upgrade([damaged_area[0], damaged_area[1]])

        # add Turrets & Walls around breached areas if we have remaining SP
        breached_area_set = {tuple(i[0]) for i in self.scored_on_locs}
        for breached_area in self.scored_on_locs:
            if breached_area_set.issuperset(set(elem[0])):
                breached_area_set.remove(breached_area)

                # check for available space
                offsets = [[-2, 2], [-3, 2], [-1, 2], [-2, 1], [-3, 1], [-3, 3], [-2, 3], [-1, 3]]
                for offset in offsets:
                    if breached_area[0] > 14:
                        if game_state.attempt_spawn([breached_area[0] + offset[0], breached_area[1]] + offset[1]) is not None:
                            game_state.attempt_spawn([breached_area[0] + offset[0], breached_area[1]] + offset[1] + 1)
                            break
                    else:
                        if game_state.attempt_spawn([breached_area[0] - offset[0], breached_area[1]] + offset[1]) is not None:
                            game_state.attempt_spawn([breached_area[0] - offset[0], breached_area[1]] + offset[1] + 1)
                            break

    def he_attac(self, game_state):
        #? code taken from my teammate yiggy z
        friendly_edges = game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.BOTTOM_RIGHT)
        damage_locations = self.least_damage_spawn_location(game_state, friendly_edges)
        attack_locations = self.largest_attack_spawn_location(game_state, friendly_edges)

        demolisher_damage_locations = sorted(zip(damage_locations[1], friendly_edges))
        if demolisher_damage_locations[0][0] == 0:
            location = demolisher_damage_locations[0][1]
            if game_state.can_spawn(DEMOLISHER, location):
                while game_state.get_resource(MP) >= 3:
                    game_state.attempt_spawn(DEMOLISHER, location)
        else:
            scout_damage_minus_wall_attack = [damage - attack*0.25 for damage, attack in zip(damage_locations[0], [i[0] for i in attack_locations[0]])]
            scout_damage_minus_factory_attack = [damage - attack*0.25 for damage, attack in zip(damage_locations[0], [i[1] for i in attack_locations[0]])]
            min_scout_damage_minus_attack = [min(i, j) for i, j in zip(scout_damage_minus_wall_attack, scout_damage_minus_factory_attack)]
            locations = [x for _,x in sorted(zip(min_scout_damage_minus_attack, friendly_edges))]
            location = random.choice(self.filter_blocked_locations(friendly_edges, game_state))
            for i in locations:
                if game_state.can_spawn(SCOUT, i) and len(game_state.find_path_to_edge(i)) > 4:
                    location = i
                    break
            if game_state.can_spawn(SCOUT, location):
                while game_state.get_resource(MP) >= 1:
                    game_state.attempt_spawn(SCOUT, location)

    def safe_non_blocked_path(self, game_state, location):
        path = game_state.find_path_to_edge(location)
        enemy_edge = game_state.game_map.get_edge_locations(game_state.game_map.TOP_LEFT) + game_state.game_map.get_edge_locations(game_state.game_map.TOP_RIGHT)
        #gamelib.debug_write('Path: {}\nLocation: {}'.format(path, location))
        if location is not None and path is not None:
            return path[-1] in enemy_edge
        else:
            return False

    def valuable_spawn_locations(self, game_state):
        """
        returns list of locations that it actually makes sense to spawn from
        """
        possible_edges = filter(lambda loc: not game_state.contains_stationary_unit(loc), self.friendly_edges)
        out = filter(lambda loc: self.safe_non_blocked_path(game_state, loc), possible_edges)

        return list(out)

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
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(TURRET, game_state.config).damage_i
            damages.append(damage)

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
                attack = 0
                if path:
                    for path_location in path:
                        for attack_loc in game_state.game_map.get_locations_in_range(path_location, gamelib.GameUnit(attacker, game_state.config).attackRange):
                            if game_state.contains_stationary_unit(attack_loc):
                                attack += gamelib.GameUnit(attacker, game_state.config).damage_f * game_state.contains_stationary_unit(attack_loc).cost[0]
                attacks[i].append(attack)

        return attacks

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x = None, valid_y = None):
        total_units = 0

        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and \
                    (unit_type is None or unit.unit_type == unit_type) and \
                    (valid_x is None or location[0] in valid_x) and \
                    (valid_y is None or location[1] in valid_y):
                        total_units += 1

        return total_units

    def filter_blocked_locations(self, locations, game_state):
        filtered = []

        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)

        return filtered

    def on_action_frame(self, turn_string):
        #? also store where enemy turrets are & where we get attacked by what kind of unit
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
        damages = events["damage"]

        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                self.scored_on_locs.append(location)
                # gamelib.debug_write("Got scored on at: {}".format(location))
                # gamelib.debug_write("All locations: {}".format(self.scored_on_locs))

        for damage in damages:
            if damage[2] in [0, 1, 2]:
                self.damaged_locs.append(damage)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
