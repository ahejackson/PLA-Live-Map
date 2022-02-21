"""Flask application to display live memory information from
   PLA onto a map"""
import json
import struct
import requests
from flask import Flask, render_template, request
import nxreader
from pa8 import Pa8
import pla
from xoroshiro import XOROSHIRO

with open("./static/resources/text_natures.txt",encoding="utf-8") as text_natures:
    NATURES = text_natures.read().split("\n")
with open("./static/resources/text_species.txt",encoding="utf-8") as text_species:
    SPECIES = text_species.read().split("\n")
PLAYER_LOCATION_PTR = "[[[[[[main+42B3558]+88]+90]+1F0]+18]+80]+90"
SPAWNER_PTR = "[[main+4268ee0]+330]"
PARTY_PTR = "[[[main+4269000]+d0]+58]"
WILD_PTR = "[[[[main+4268f00]+b0]+e0]+d0]"
OUTBREAK_PTR = "[[[[main+427C470]+2B0]+58]+18]"
CUSTOM_MARKERS = {
    "obsidianfieldlands": {
        "camp": {
            "coords": [
            365.36,
            52,
            136.1
            ],
            "faIcon": "campground",
        }
    },
    "crimsonmirelands": {
        "camp": {
            "coords": [
            242.45,
            55.64,
            435.84
            ],
            "faIcon": "campground",
        }
    },
    "cobaltcoastlands": {
        "camp": {
            "coords": [
            71.06,
            45.16,
            625.38
            ],
            "faIcon": "campground",
        }
    },
    "coronethighlands": {
        "camp": {
            "coords": [
            892.75,
            36.45,
            922.92
            ],
            "faIcon": "campground",
        }
    },
    "alabastericelands": {
        "camp": {
            "coords": [
            533.77,
            31.13,
            912.42
            ],
            "faIcon": "campground",
        }
    }
}

with open("config.json","r",encoding="utf-8") as config:
    IP_ADDRESS = json.load(config)["IP"]

app = Flask(__name__)
reader = nxreader.NXReader(IP_ADDRESS)

@app.route("/")
def root():
    """Display index.html at the root of the application"""
    return render_template('index.html')

@app.route("/map/<name>")
def load_map(name):
    """Read markers and generate map based on location"""
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{name}.json"
    markers = json.loads(requests.get(url).text)
    with open(f"./static/resources/{name}.json",encoding="utf-8") as slot_file:
        slots = json.load(slot_file)
    return render_template('map.html',
                           markers=markers.values(),
                           map_name=name,
                           custom_markers=json.dumps(CUSTOM_MARKERS[name]),
                           slots=slots)

def next_filtered(group_id, rolls, guaranteed_ivs, init_spawn, poke_filter, stopping_point=50000):
    """Find the next advance that matches poke_filter for a spawner"""
    # pylint: disable=too-many-locals,too-many-arguments
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}"\
                                             f"+{0x70+group_id*0x440+0x20:X}",8)
    return pla.next_filtered(generator_seed, rolls, guaranteed_ivs, init_spawn, poke_filter, stopping_point)

def show_outbreak(outbreak):
    return "<br>".join(show_outbreak_pokemon(*pokemon) for pokemon in outbreak)

def show_outbreak_pokemon(spawn, encryption_constant, pid, ivs, ability, gender, nature, shiny, alpha):
    return f"<b>{spawn}</b> <b>Shiny: " \
            f"<font color=\"{'green' if shiny else 'red'}\">{shiny}</font></b><br>" \
            f"<b>Alpha: <font color=\"{'green' if alpha else 'red'}\">" \
            f"{alpha}</font></b><br>" \
            f"EC: {encryption_constant:08X} PID: {pid:08X}<br>" \
            f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
            f"{'/'.join(str(iv) for iv in ivs)}<br>"

def show_path(paths):
    return '<br>'.join('|'.join(str(step) for step in path) for path in paths)

def show_mass_outbreak(main_rng, rolls, spawns, poke_filter):
    """Show the current set of a mass outbreak"""
    results, filtered_present = pla.generate_mass_outbreak(main_rng, rolls, spawns, poke_filter)
    return show_outbreak(results)

def show_next_filtered_mass_outbreak(main_rng, rolls, spawns, poke_filter):
    """Show the next pokemon of a mass outbreak that passes poke_filter
       and return a string representing it"""
    results, advance = pla.next_filtered_mass_outbreak(main_rng, rolls, spawns, poke_filter)
    return f"<b>Advance: {advance}</b><br>{show_outbreak(results)}"

def show_mass_outbreak_search_passive(group_seed, rolls, spawns, move_limit, poke_filter):
    """Show all the pokemon of an outbreak based on a provided passive path"""
    # pylint: disable=too-many-locals, too-many-arguments
    # the generation is unique to each path, no use in splitting this function

    results = pla.passive_outbreak_pathfind(group_seed, rolls, spawns, move_limit, poke_filter)
        
    if len(results["info"]) == 0:
        return "<b>No paths found</b>"
    
    return '<br>'.join(f"<b>Paths:<br>{show_path(results['paths'][seed])}<br></b>{show_outbreak_pokemon(*pokemon)}<br>" for seed, pokemon in results["info"].items())

def show_mass_outbreak_search_aggressive(group_seed, rolls, spawns, poke_filter):
    """Generate all the pokemon of an outbreak based on a provided aggressive path"""
    # pylint: disable=too-many-locals, too-many-arguments
    # the generation is unique to each path, no use in splitting this function
    results, advance = pla.next_filtered_aggressive_outbreak_pathfind(group_seed, rolls, spawns, poke_filter)
    return f"<br>Advance: {advance}</b><br>{show_outbreak(results)}"

@app.route('/read-battle', methods=['GET'])
def read_battle():
    """Read all battle pokemon and return the information as an html formatted string"""
    display = ""
    party_count = reader.read_pointer_int(f"{PARTY_PTR}+88",1)
    wild_count = reader.read_pointer_int(f"{WILD_PTR}+1a0",1) \
               - party_count
    if wild_count > 30:
        wild_count = 0
    for i in range(wild_count):
        pkm = Pa8(reader.read_pointer(f"{WILD_PTR}+{0xb0+8*(i+party_count):X}"\
                                       "]+70]+60]+98]+10]",Pa8.STOREDSIZE))
        pokemon_name = f"{SPECIES[pkm.species]}" \
                       f"{('-' + str(pkm.form_index)) if pkm.form_index > 0 else ''} " \
                       f"{'' if pkm.shiny_type == 0 else '⋆' if pkm.shiny_type == 1 else '◇'}"
        pokemon_info = f"EC: {pkm.encryption_constant:08X}<br>" \
                       f"PID: {pkm.pid:08X}<br>" \
                       f"Nature: {NATURES[pkm.nature]}<br>" \
                       f"Ability: {pkm.ability_string}<br>" \
                       f"IVs: {'/'.join(str(iv) for iv in pkm.ivs)}"
        if pkm.is_valid:
            display += f"<button type=\"button\" class=\"collapsible\" " \
                       f"data-for=\"battle{i}\" onclick=collapsibleOnClick()>{i+1} " \
                       f"{pokemon_name}</button>" \
                       f"<div class=\"info\" id=\"battle{i}\">{pokemon_info}</div><br>"
    return display

@app.route('/read-mass-outbreak', methods=['POST'])
def read_mass_outbreak():
    """Read current mass outbreak information and predict next pokemon that passes filter"""
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{request.json['name']}.json"
    minimum = int(list(json.loads(requests.get(url).text).keys())[-1])-15
    group_id = minimum+30
    group_seed = 0
    while group_seed == 0 and group_id != minimum:
        group_id -= 1
        print(f"Finding group_id {minimum-group_id+30}/30")
        group_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70+group_id*0x440+0x408:X}",8)
    if group_id == minimum:
        print("No mass outbreak found")
        return json.dumps(["No mass outbreak found","No mass outbreak found"])
    print(f"Found group_id {group_id}")

    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x70+group_id*0x440+0x20:X}",8)
    group_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF

    if request.json['spawns'] == -1:
        for i in range(4):
            spawns = reader.read_pointer_int(f"{OUTBREAK_PTR}+{0x60+i*0x50:X}",1)
            if 10 <= spawns <= 15:
                request.json['spawns'] = spawns
                break
        print(f"Spawns: {request.json['spawns']}")

    if request.json['aggressivePath']:
        # should display multiple aggressive paths like whats done with passive
        search_results = show_mass_outbreak_search_aggressive(group_seed, request.json['rolls'], request.json['spawns'], request.json['filter'])
        display = ["", f"Group Seed: {group_seed:X}<br>" + search_results]

    elif request.json['passivePath']:
        print(group_seed,request.json['rolls'], request.json['spawns'], request.json['passiveMoveLimit'], request.json['filter'])
        search_results = show_mass_outbreak_search_passive(group_seed,  request.json['rolls'], request.json['spawns'], request.json['passiveMoveLimit'], request.json['filter'])
        display = ["", f"Group Seed: {group_seed:X}<br>" + search_results]

    else:
        main_rng = XOROSHIRO(group_seed)
        mass_outbreak = show_mass_outbreak(main_rng,  request.json['rolls'], request.json['spawns'], request.json['filter'])
        next_filtered = show_next_filtered_mass_outbreak(main_rng, request.json['rolls'], request.json['spawns'], request.json['filter'])
        display = [f"Group Seed: {group_seed:X}<br>{mass_outbreak}", next_filtered]

    return json.dumps(display)

@app.route('/check-possible', methods=['POST'])
def check_possible():
    """Check spawners that can spawn a given species"""
    print(request.json)
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{request.json['name']}.json"
    markers = json.loads(requests.get(url).text)
    possible = {}
    for group_id, marker in markers.items():
        with open(f"./static/resources/{request.json['name']}.json",encoding="utf-8") as slot_file:
            sp_slots = \
                json.load(slot_file)[marker['name']]
        minimum, maximum, total \
            = pla.find_slot_range(request.json["filter"]["timeSelect"],
                              request.json["filter"]["weatherSelect"],
                              request.json["filter"]["speciesSelect"],
                              sp_slots)
        if total:
            possible[group_id] = (maximum-minimum)/total*100
    return json.dumps(possible)

@app.route('/read-seed', methods=['POST'])
def read_seed():
    """Read current information and next advance that passes filter for a spawner"""
    # pylint: disable=too-many-locals
    group_id = request.json['groupID']
    thresh = request.json['thresh']
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
            f"pla_spawners/jsons/{request.json['map']}.json"
    with open(f"./static/resources/{request.json['map']}.json",encoding="utf-8") as slot_file:
        sp_slots = \
            json.load(slot_file)[json.loads(requests.get(url).text)[str(group_id)]['name']]
    generator_seed = reader.read_pointer_int(f"{SPAWNER_PTR}"\
                                             f"+{0x70+group_id*0x440+0x20:X}",8)
    group_seed = (generator_seed - 0x82A2B175229D6A5B) & 0xFFFFFFFFFFFFFFFF
    rng = XOROSHIRO(group_seed)
    if not request.json['initSpawn']:
        # advance once
        rng.next() # spawner 0
        rng.next() # spawner 1
        rng.reseed(rng.next()) # reseed group rng
    rng.reseed(rng.next()) # use spawner 0 to reseed
    slot = rng.next() / (2**64) * request.json['filter']['slotTotal']
    fixed_seed = rng.next()
    encryption_constant,pid,ivs,ability,gender,nature,shiny = pla.generate_from_seed(fixed_seed, request.json['rolls'], request.json['ivs'])
    species = pla.slot_to_pokemon(pla.find_slots(request.json["filter"]["timeSelect"],
                                         request.json["filter"]["weatherSelect"],
                                         sp_slots),slot)

    display = f"Generator Seed: {generator_seed:X}<br>" \
              f"Species: {species}<br>" \
              f"Shiny: <font color=\"{'green' if shiny else 'red'}\"><b>{shiny}</b></font><br>" \
              f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
              f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
              f"{'/'.join(str(iv) for iv in ivs)}<br>"

    if request.json['filter']['filterSpeciesCheck']:
        request.json['filter']['minSlotFilter'], \
        request.json['filter']['maxSlotFilter'], \
        request.json['filter']['slotTotal'] \
            = pla.find_slot_range(request.json["filter"]["timeSelect"],
                              request.json["filter"]["weatherSelect"],
                              request.json["filter"]["speciesSelect"],
                              sp_slots)
        request.json['filter']['slotFilterCheck'] = True

    adv,slot,encryption_constant,pid,ivs,ability,gender,nature,shiny \
        = next_filtered(group_id,
                        request.json['rolls'],
                        request.json['ivs'],
                        request.json['initSpawn'],
                        request.json['filter'])
    if adv == -1:
        return "Impossible slot filters for this spawner"
    if adv == -2:
        return "No results before limit (50000)"
    if adv <= thresh:
        display += f"Next Filtered: <font color=\"green\"><b>{adv}</b></font><br>"
    else:
        display += f"Next Filtered: {adv} <br>"

    species = pla.slot_to_pokemon(pla.find_slots(request.json["filter"]["timeSelect"],
                                         request.json["filter"]["weatherSelect"],
                                         sp_slots),slot)
    display += f"Species: {species}<br>" \
               f"Shiny: <font color=\"{'green' if shiny else 'red'}\"><b>{shiny}</b></font><br>" \
               f"EC: {encryption_constant:X} PID: {pid:X}<br>" \
               f"Nature: {NATURES[nature]} Ability: {ability} Gender: {gender}<br>" \
               f"{'/'.join(str(iv) for iv in ivs)}<br>"
    return display

@app.route('/teleport', methods=['POST'])
def teleport():
    """Teleport the player to provided coordinates"""
    coordinates = request.json['coords']
    print(f"Teleporting to {coordinates}")
    position_bytes = struct.pack('fff', *coordinates)
    reader.write_pointer(PLAYER_LOCATION_PTR,f"{int.from_bytes(position_bytes,'big'):024X}")
    return ""

@app.route('/read-coords', methods=['GET'])
def read_coords():
    """Read the players current position"""
    pos = struct.unpack('fff', reader.read_pointer(PLAYER_LOCATION_PTR,12))
    coords = {
        "x":pos[0],
        "y":pos[1],
        "z":pos[2]
    }
    return json.dumps(coords)

@app.route('/update-positions', methods=['GET'])
def update_positions():
    """Scan all active spawns"""
    spawns = {}
    size = reader.read_pointer_int(f"{SPAWNER_PTR}+18",4)
    size = int(size//0x40 - 1)
    print(f"Checking up to index {size}")
    for index in range(0,size):
        if index % int(size//100) == 0:
            print(f"{index/size*100}% done scanning")
        position_bytes = reader.read_pointer(f"{SPAWNER_PTR}+{0x70+index*0x40:X}",12)
        seed = reader.read_pointer_int(f"{SPAWNER_PTR}+{0x90+index*0x40:X}",12)
        pos = struct.unpack('fff', position_bytes)
        if not (seed == 0 or pos[0] < 1 or pos[1] < 1 or pos[2] < 1):
            print(f"Active: spawner_id {index} {pos[0]},{pos[1]},{pos[2]} {seed:X}")
            spawns[str(index)] = {"x":pos[0],
                                  "y":pos[1],
                                  "z":pos[2],
                                  "seed":seed}
    return json.dumps(spawns)

@app.route('/check-near', methods=['POST'])
def check_near():
    """Check all spawners' nearest advance that passes filters to update icons"""
    # pylint: disable=too-many-locals
    # store these locals before the loop to avoid accessing dictionary items repeatedly
    thresh = request.json['thresh']
    name = request.json['name']
    url = "https://raw.githubusercontent.com/Lincoln-LM/JS-Finder/main/Resources/" \
         f"pla_spawners/jsons/{name}.json"
    markers = json.loads(requests.get(url).text)
    maximum = list(markers.keys())[-1]
    near = []
    poke_filter = request.json['filter']
    time = request.json["filter"]["timeSelect"]
    weather = request.json["filter"]["weatherSelect"]
    species = request.json["filter"]["speciesSelect"]
    with open(f"./static/resources/{name}.json",encoding="utf-8") as slot_file:
        slots = json.load(slot_file)
    for group_id, marker in markers.items():
        if poke_filter['filterSpeciesCheck']:
            sp_slots = slots[markers[str(group_id)]['name']]
            poke_filter['minSlotFilter'], \
            poke_filter['maxSlotFilter'], \
            poke_filter['slotTotal'] \
                = pla.find_slot_range(time,
                                weather,
                                species,
                                sp_slots)
            poke_filter['slotFilterCheck'] = True
        print(f"Checking group_id {group_id}/{maximum}")
        adv,_,_,_,_,_,_,_,_ = \
            next_filtered(int(group_id),
                                request.json['rolls'],
                                marker["ivs"],
                                request.json['initSpawn'],
                                poke_filter,
                                stopping_point=thresh)
        if 0 <= adv <= thresh:
            near.append(group_id)
    return json.dumps(near)

if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
