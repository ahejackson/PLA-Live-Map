from math import factorial
from xoroshiro import XOROSHIRO


def generate_from_seed(seed, rolls, guaranteed_ivs):
    """Generate pokemon information from a fixed seed (FixInitSpec)"""
    rng = XOROSHIRO(seed)
    encryption_constant = rng.rand(0xFFFFFFFF)
    sidtid = rng.rand(0xFFFFFFFF)

    for _ in range(rolls):
        pid = rng.rand(0xFFFFFFFF)
        shiny = ((pid >> 16) ^ (sidtid >> 16) ^ (pid & 0xFFFF) ^ (sidtid & 0xFFFF)) < 0x10
        if shiny:
            break

    ivs = [-1, -1, -1, -1, -1, -1]

    for i in range(guaranteed_ivs):
        index = rng.rand(6)
        while ivs[index] != -1:
            index = rng.rand(6)
        ivs[index] = 31

    for i in range(6):
        if ivs[i] == -1:
            ivs[i] = rng.rand(32)

    ability = rng.rand(2)
    gender = rng.rand(252) + 1
    nature = rng.rand(25)
    return encryption_constant, pid, ivs, ability, gender, nature, shiny


def next_filtered(generator_seed, rolls, guaranteed_ivs, init_spawn, poke_filter, stopping_point=50000):
    """Find the next advance that matches poke_filter for a spawner"""
    # pylint: disable=too-many-locals,too-many-arguments

    group_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
    main_rng = XOROSHIRO(group_seed)

    if not init_spawn:
        # advance once
        main_rng.next()  # spawner 0
        main_rng.next()  # spawner 1
        main_rng.reseed(main_rng.next())
    adv = -1

    if poke_filter["slotTotal"] == 0:
        return -1, -1, -1, -1, [], -1, -1, -1, False

    while True:
        adv += 1
        if adv > stopping_point:
            return -2, -1, -1, -1, [], -1, -1, -1, False
        generator_seed = main_rng.next()
        main_rng.next()  # spawner 1's seed, unused
        rng = XOROSHIRO(generator_seed)
        slot = poke_filter["slotTotal"] * rng.next() / 2**64

        (encryption_constant, pid, ivs, ability, gender, nature, shiny) = generate_from_seed(rng.next(), rolls, guaranteed_ivs)

        break_flag = (
            (poke_filter["shinyFilterCheck"] and not shiny)
            or poke_filter["slotFilterCheck"]
            and not (poke_filter["minSlotFilter"] <= slot < poke_filter["maxSlotFilter"])
            or poke_filter["outbreakAlphaFilter"]
            and not 100 <= slot < 101
        )

        if not break_flag:
            break
        main_rng.reseed(main_rng.next())

    return adv, slot, encryption_constant, pid, ivs, ability, gender, nature, shiny

def generate_mass_outbreak(main_rng, rolls, spawns, poke_filter):
    """Generate the current set of a mass outbreak and return a list of results along with
       a bool to show if a pokemon passing poke_filter is present"""
    # pylint: disable=too-many-locals
    # this many locals is appropriate to display all the information about
    # the mass outbreak that a user might want
    results = []
    filtered_present = False
    
    for init_spawn in range(1,5):
        generator_seed = main_rng.next()
        main_rng.next() # spawner 1's seed, unused
        fixed_rng = XOROSHIRO(generator_seed)
        slot = (fixed_rng.next() / (2**64) * 101)
        alpha = slot >= 100
        fixed_seed = fixed_rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = generate_from_seed(fixed_seed,rolls,3 if alpha else 0)
        results.append((f"Init Spawn {init_spawn}",encryption_constant,pid,ivs,ability,gender,nature,shiny,alpha))

        filtered = ((poke_filter['shinyFilterCheck'] and not shiny)
                  or poke_filter['outbreakAlphaFilter'] and not 100 <= slot < 101)
        filtered_present |= not filtered
    
    group_seed = main_rng.next()
    main_rng.reseed(group_seed)
    respawn_rng = XOROSHIRO(group_seed)

    for respawn in range(1,spawns-3):
        generator_seed = respawn_rng.next()
        respawn_rng.next() # spawner 1's seed, unused
        respawn_rng.reseed(respawn_rng.next())
        fixed_rng = XOROSHIRO(generator_seed)
        slot = (fixed_rng.next() / (2**64) * 101)
        alpha = slot >= 100
        fixed_seed = fixed_rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = generate_from_seed(fixed_seed,rolls,3 if alpha else 0)
        results.append((f"Respawn {respawn}",encryption_constant,pid,ivs,ability,gender,nature,shiny,alpha))

        filtered = ((poke_filter['shinyFilterCheck'] and not shiny)
                  or poke_filter['outbreakAlphaFilter'] and not 100 <= slot < 101)
        filtered_present |= not filtered
    
    return results, filtered_present

def next_filtered_mass_outbreak(main_rng, rolls, spawns, poke_filter):
    """Find the next pokemon of a mass outbreak that passes poke_filter
       and return a list of the results and the number of advances needed"""
    filtered_present = False
    advance = 0

    while not filtered_present:
        advance += 1
        results, filtered_present = generate_mass_outbreak(main_rng,rolls,spawns,poke_filter)
    
    return results, advance

def generate_mass_outbreak_passive_path(group_seed, rolls, steps, total_spawns, poke_filter, total_paths, storage):
    """Generate all the pokemon of an outbreak based on a provided passive path"""
    # pylint: disable=too-many-locals, too-many-arguments
    # the generation is unique to each path, no use in splitting this function
    storage['current'] += 1
    if storage['current'] & 0xF == 0 or storage['current'] == total_paths:
        print(f"Passive search {storage['current']}/{total_paths}")
    
    rng = XOROSHIRO(group_seed)
    for step_i,step in enumerate(steps):
        left = total_spawns - sum(steps[:step_i+1])
        final_in_init = (step_i == (len(steps) - 1)) and left + step <= 4
        all_in_init = (step_i != (len(steps) - 1)) and left <= 4
        down_to_init = final_in_init or all_in_init

        if final_in_init:
            add = 0
        else:
            add = min(4,left)
        
        for pokemon in range(step + add):
            spawner_seed = rng.next()
            spawner_rng = XOROSHIRO(spawner_seed)
            slot = spawner_rng.next() / (2**64) * 101
            alpha = slot >= 100
            fixed_seed = spawner_rng.next()
            encryption_constant,pid,ivs,ability,gender,nature,shiny = generate_from_seed(fixed_seed,rolls,3 if alpha else 0)
            filtered = ((poke_filter['shinyFilterCheck'] and not shiny)
                      or poke_filter['outbreakAlphaFilter'] and not alpha)
            effective_path = steps[:step_i] + [max(0,pokemon-3)]
            
            if not filtered:
                if fixed_seed in storage["info"] and effective_path not in storage["paths"][fixed_seed]:
                    storage["paths"][fixed_seed].append(effective_path)
                else:
                    storage["paths"][fixed_seed] = [effective_path]
                    storage["info"][fixed_seed] = (f"Spawn {pokemon}", encryption_constant, pid, ivs, ability, gender, nature, shiny, alpha)
            
            rng.next() # spawner 1 seed, unused
            if not down_to_init and pokemon >= 3:
                rng.reseed(rng.next())

def passive_outbreak_pathfind(group_seed, rolls, spawns, move_limit, poke_filter, total_paths=None, spawns_left=None, step=None, steps=None, storage=None):
    """Recursively pathfind to possible shinies for the current outbreak via variable
        Jubilife visits"""
    # pylint: disable=too-many-arguments
    # this could do with some optimization, there is a lot of overlap with passive paths
    if spawns_left is None or steps is None or storage is None:
        steps = []
        storage = {"info": {}, "paths": {}, "current": 0}
        spawns_left = spawns - 4
        total_paths = round(factorial(spawns_left + move_limit) / (factorial(spawns_left) * factorial(move_limit)))
        move_limit += 1
    move_limit -= 1
    _steps = steps.copy()
    if step is not None:
        spawns_left -= step
        _steps.append(step)
    if spawns_left <= 0 or move_limit == 0:
        generate_mass_outbreak_passive_path(group_seed, rolls, _steps, spawns, poke_filter, total_paths, storage)
        if _steps == [spawns-4]:
            return storage
        return None
    limit = spawns_left + 1
    for _move in range(limit):
        if passive_outbreak_pathfind(group_seed, rolls, spawns, move_limit, poke_filter, total_paths, spawns_left, _move, _steps, storage) is not None:
            return storage
    return None

def generate_mass_outbreak_aggressive_path(group_seed, rolls, steps, poke_filter, uniques, storage):
    """Generate all the pokemon of an outbreak based on a provided aggressive path"""
    # pylint: disable=too-many-locals, too-many-arguments
    # the generation is unique to each path, no use in splitting this function
    main_rng = XOROSHIRO(group_seed)
    for init_spawn in range(1,5):
        generator_seed = main_rng.next()
        main_rng.next() # spawner 1's seed, unused
        fixed_rng = XOROSHIRO(generator_seed)
        slot = (fixed_rng.next() / (2**64) * 101)
        alpha = slot >= 100
        fixed_seed = fixed_rng.next()
        encryption_constant,pid,ivs,ability,gender,nature,shiny = generate_from_seed(fixed_seed, rolls, 3 if alpha else 0)
        filtered = ((poke_filter['shinyFilterCheck'] and not shiny)
                  or poke_filter['outbreakAlphaFilter'] and not alpha)

        if not filtered and not fixed_seed in uniques:
            uniques.add(fixed_seed)
            storage.append((f"Init Spawn {init_spawn}", encryption_constant, pid, ivs, ability, gender, nature, shiny, alpha))

    group_seed = main_rng.next()
    respawn_rng = XOROSHIRO(group_seed)
    for step_i,step in enumerate(steps):
        for pokemon in range(1,step+1):
            generator_seed = respawn_rng.next()
            respawn_rng.next() # spawner 1's seed, unused
            fixed_rng = XOROSHIRO(generator_seed)
            slot = (fixed_rng.next() / (2**64) * 101)
            alpha = slot >= 100
            fixed_seed = fixed_rng.next()
            encryption_constant,pid,ivs,ability,gender,nature,shiny = generate_from_seed(fixed_seed, rolls, 3 if alpha else 0)
            filtered = ((poke_filter['shinyFilterCheck'] and not shiny)
                      or poke_filter['outbreakAlphaFilter'] and not alpha)
                      
            if not filtered and not fixed_seed in uniques:
                uniques.add(fixed_seed)
                path = f"Path: {'|'.join(str(s) for s in steps[:step_i]+[pokemon])} Spawns: {sum(steps[:step_i]) + pokemon + 4}"
                storage.append((path, encryption_constant, pid, ivs, ability, gender, nature, shiny, alpha))

        respawn_rng = XOROSHIRO(respawn_rng.next())

def get_final_path(spawns):
    """Get the final path that will be generated to know when to stop aggressive recursion"""
    spawns -= 4
    path = [4] * (spawns // 4)
    if spawns % 4 != 0:
        path.append(spawns % 4)
    return path

def aggressive_outbreak_pathfind(group_seed, rolls, spawns, poke_filter, step=0, steps=None, uniques=None, storage=None):
    """Recursively pathfind to possible shinies for the current outbreak via multi battles"""
    # pylint: disable=too-many-arguments
    # can this algo be improved?
    if steps is None or uniques is None or storage is None:
        steps = []
        uniques = set()
        storage = []
    _steps = steps.copy()
    if step != 0:
        _steps.append(step)
    if sum(_steps) + step < spawns - 4:
        for _step in range(1, min(5, (spawns - 4) - sum(_steps))):
            if aggressive_outbreak_pathfind(group_seed, rolls, spawns, poke_filter, _step, _steps, uniques, storage) is not None:
                return storage
    else:
        _steps.append(spawns - sum(_steps) - 4)
        generate_mass_outbreak_aggressive_path(group_seed, rolls, _steps, poke_filter, uniques, storage)
        if _steps == get_final_path(spawns):
            return storage
    return None

def next_filtered_aggressive_outbreak_pathfind(group_seed, rolls, spawns, poke_filter):
    """Check the next outbreak advances until an aggressive path to a pokemon that
       passes poke_filter exists - returns the pokemon and the number of advances"""
    main_rng = XOROSHIRO(group_seed)
    result = []
    advance = -1
    while len(result) == 0:
        if advance != -1:
            for _ in range(4*2):
                main_rng.next()
            group_seed = main_rng.next()
            main_rng.reseed(group_seed)
        advance += 1
        result = aggressive_outbreak_pathfind(group_seed, rolls, spawns, poke_filter)
    return result, advance