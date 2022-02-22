// Save and load user preferences
function loadPreferences() {
    let teleportHeight = readIntFromStorage("teleportHeight", 50);
    let rolls = readIntFromStorage("rolls", 1);
    let thresh = readIntFromStorage("thresh", 50);
    let initSpawn = readBoolFromStorage("initSpawn", false);
    let mapShinyFilter = readBoolFromStorage("mapShinyFilter", true);
    let mapAlphaFilter = readBoolFromStorage("mapAlphaFilter", true);
    let outbreakAlphaFilter = readBoolFromStorage("outbreakAlphaFilter", false);
    let outbreakShinyFilter = readBoolFromStorage("outbreakShinyFilter", false);
    let massOutbreakRolls = readIntFromStorage("massOutbreakRolls", 26);
    let passiveMoveLimit = readIntFromStorage("passiveMoveLimit", 10);

    document.getElementById("y").value = teleportHeight;
    document.getElementById("rolls").value = rolls;
    document.getElementById("thresh").value = thresh;
    document.getElementById("initSpawn").checked = initSpawn;
    document.getElementById("alphaFilterCheck").checked = mapAlphaFilter;
    document.getElementById("shinyFilterCheck").checked = mapShinyFilter;
    document.getElementById("outbreakAlphaFilter").checked = outbreakAlphaFilter;
    document.getElementById("outbreakShinyFilter").checked = outbreakShinyFilter;
    document.getElementById("massOutbreakRolls").value = massOutbreakRolls;
    document.getElementById("passiveMoveLimit").value = passiveMoveLimit;
}

function savePreferences() {
    document.getElementById("y").addEventListener("change", function(e) {
        saveIntToStorage("teleportHeight", e.target.value);
    });
    document.getElementById("rolls").addEventListener("change", function(e) {
        saveIntToStorage("rolls", e.target.value);
    });
    document.getElementById("thresh").addEventListener("change", function(e) {
        saveIntToStorage("thresh", e.target.value);
    });
    document.getElementById("initSpawn").addEventListener("change", function(e) {
        saveBoolToStorage("initSpawn", e.target.checked);
    });
    document.getElementById("alphaFilterCheck").addEventListener("change", function(e) {
        saveBoolToStorage("mapAlphaFilter", e.target.checked);
    });
    document.getElementById("shinyFilterCheck").addEventListener("change", function(e) {
        saveBoolToStorage("mapShinyFilter", e.target.checked);
    });
    document.getElementById("outbreakAlphaFilter").addEventListener("change", function(e) {
        saveBoolToStorage("outbreakAlphaFilter", e.target.checked);
    });
    document.getElementById("outbreakShinyFilter").addEventListener("change", function(e) {
        saveBoolToStorage("outbreakShinyFilter", e.target.checked);
    });
    document.getElementById("massOutbreakRolls").addEventListener("change", function(e) {
        saveIntToStorage("massOutbreakRolls", e.target.value);
    });
    document.getElementById("passiveMoveLimit").addEventListener("change", function(e) {
        saveIntToStorage("passiveMoveLimit", e.target.value);
    });
}

function saveIntToStorage(id, value) {
    localStorage.setItem(id, value);
}

function readIntFromStorage(id, defaultValue) {
    value = localStorage.getItem(id);
    return value ? parseInt(value) : defaultValue;
}

function saveBoolToStorage(id, value) {
    localStorage.setItem(id, value ? 1 : 0)
}

function readBoolFromStorage(id, defaultValue) {
    value = localStorage.getItem(id);
    return value ? (parseInt(value) == 1) : defaultValue;
}