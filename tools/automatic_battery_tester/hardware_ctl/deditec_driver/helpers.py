import json
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import TypedDict, List, Dict

# --- Relativní a absolutní importy ---
try:
    # Relativní import v rámci stejného balíčku
    from .deditec_1_16_on import Deditec_1_16_on
    # Import z nadřazeného balíčku (backend)
    from backend.common import get_logger
    imports_ok = True
except ImportError as e:
     imports_ok = False
     # Fallback logger, pokud selže import common
     logging.basicConfig()
     logger = logging.getLogger(__name__)
     logger.error(f"Failed to import dependencies: {e}. Using fallback logger.")
     # Dummy třída, aby zbytek kódu mohl selhat později
     class Deditec_1_16_on: pass
else:
     # Pokud importy prošly, nastavíme logger
     logger = get_logger(__name__)
# ------------------------------------


class Cache(TypedDict):
    last_run: str
    pins_on: List[int]

# Cesta k cache souboru relativně k tomuto souboru
HERE = Path(__file__).parent
CACHE_FILE = HERE / "pin_cache.json"

PIN_COUNT = 16 # Počet relé na desce

def _ensure_cache_file_exists():
    """Zajistí existenci cache souboru s výchozí strukturou."""
    if not CACHE_FILE.exists():
        logger.warning(f"Cache file {CACHE_FILE} not found, creating default.")
        try:
            with open(CACHE_FILE, "w") as f:
                empty_cache: Cache = {"last_run": datetime.now().isoformat(), "pins_on": []}
                json.dump(empty_cache, f, indent=2) # Použít json.dump
        except IOError as e:
             logger.error(f"Failed to create cache file {CACHE_FILE}: {e}")

# Zajistíme existenci cache při načtení modulu
_ensure_cache_file_exists()

# Prefix příkazu pro nastavení všech výstupů najednou
# Zdroj: Dokumentace Deditec nebo reverzní inženýrství?
# DELIBOX-OPTO16-RELAIS16 - Protokollbeschreibung v1.0.pdf (pokud existuje)
# Tento prefix se zdá být specifický pro určitý příkaz.
PREFIX_CMD = b"\x63\x9a\x01\x01\x00\x0b\x57\x57\x00\x00"

# --- Funkce pro práci s cache a příkazy ---

def get_pins_on() -> List[int]:
    """Načte seznam aktuálně zapnutých pinů z cache souboru."""
    try:
        with open(CACHE_FILE) as f:
            data: Cache = json.load(f)
            # Validace načtených dat?
            if isinstance(data.get("pins_on"), List):
                 # Odstranit duplicity a zajistit čísla
                 pins = sorted(list(set(int(p) for p in data["pins_on"] if isinstance(p, (int, str)) and str(p).isdigit())))
                 # Omezit na platný rozsah
                 valid_pins = [p for p in pins if 1 <= p <= PIN_COUNT]
                 if len(valid_pins) != len(data["pins_on"]):
                      logger.warning(f"Invalid pins found in cache, cleaned up: {data['pins_on']} -> {valid_pins}")
                 return valid_pins
            else:
                 logger.error(f"Invalid format in cache file {CACHE_FILE}: 'pins_on' is not a List.")
                 return [] # Vrátit prázdný seznam při chybě formátu
    except FileNotFoundError:
         logger.error(f"Cache file {CACHE_FILE} not found during read. Returning empty state.")
         _ensure_cache_file_exists() # Zkusit znovu vytvořit
         return []
    except (json.JSONDecodeError, Exception) as e:
        logger.exception(f"Deditec:: failed reading/parsing cache file {CACHE_FILE}: {e}")
        return []


def save_new_pins_on(pins_on: List[int]) -> None:
    """Uloží nový seznam zapnutých pinů do cache souboru."""
    # Odstranit duplicity a seřadit pro konzistenci
    unique_sorted_pins = sorted(list(set(pins_on)))
    logger.debug(f"Saving new pins state to cache: {unique_sorted_pins}")
    try:
        with open(CACHE_FILE, "w") as f:
            cache: Cache = {"last_run": datetime.now().isoformat(), "pins_on": unique_sorted_pins}
            json.dump(cache, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to write cache file {CACHE_FILE}: {e}")


def get_new_pins_on(on: List[int], off: List[int], all_off: bool) -> List[int]:
    """Vypočítá nový seznam zapnutých pinů."""
    if all_off:
        return [] # Všechno vypnout

    # Získáme předchozí stav z cache
    previous_on_set = set(get_pins_on())
    logger.debug(f"Calculating new state: Previous ON={previous_on_set}, Requested ON={on}, Requested OFF={off}")

    # Aplikujeme změny
    current_on_set = (previous_on_set.union(set(on))) - set(off)

    # Vrátíme jako seřazený seznam
    new_pins = sorted(list(current_on_set))
    logger.debug(f"Resulting new ON state: {new_pins}")
    return new_pins

def turn_on_pins_command(pins: List[int]) -> bytes:
    """Vytvoří bajtový příkaz pro zapnutí daných pinů."""
    # Hodnota reprezentuje bitovou masku zapnutých pinů
    # Pin 1 = bit 0 (2^0), Pin 2 = bit 1 (2^1), ..., Pin 16 = bit 15 (2^15)
    pin_mask_value = 0
    valid_pins = set() # Sledujeme validní piny pro logování
    for pin in set(pins): # Zajistíme unikátnost
        if isinstance(pin, int) and 1 <= pin <= PIN_COUNT:
            pin_mask_value += 2 ** (pin - 1)
            valid_pins.add(pin)
        else:
             logger.warning(f"Invalid pin number provided to turn_on_pins_command: {pin}. Ignoring.")

    logger.debug(f"Generating command for pins: {sorted(list(valid_pins))}. Mask value: {pin_mask_value}")
    # Hodnota masky se přidá jako 2 bajty (big-endian) za prefix
    command = PREFIX_CMD + pin_mask_value.to_bytes(2, byteorder="big")
    return command


# --- Funkce pro přímé ovládání (použité v test_deditec_control) ---
# Tuto funkci náš RelayController nepoužívá, ale test ano
def run_pins_on_off_command_save(ip: str, port: int, pins_on: List[int], pins_off: List[int]) -> bool:
    """Kompletní sekvence: výpočet, připojení, odeslání, uložení."""
    logger.info(f"Executing direct command: ON={pins_on}, OFF={pins_off} to {ip}:{port}")
    if not imports_ok:
        logger.error("Cannot run direct command, imports failed.")
        return False

    try:
        with Deditec_1_16_on(ip=ip, port=port) as deditec_controller:
            new_pins_on = get_new_pins_on(pins_on, pins_off, False)
            command = turn_on_pins_command(new_pins_on)
            response = deditec_controller.send_command(command)
            success = response == 0
            if success:
                save_new_pins_on(new_pins_on)
                logger.info(f"Direct command successful. New state ON: {new_pins_on}")
            else:
                 logger.error(f"Direct command failed. Deditec response: {response}")
            return success
    except Exception as e:
         logger.exception(f"Error during direct command execution: {e}")
         return False

# --- Funkce pro čtení stavu (použité v test_deditec_control) ---
def get_pins_status_dict() -> Dict[str, bool]:
    """Vrátí slovník se stavem všech pinů na základě cache."""
    pins_on = get_pins_on()
    pin_status = {str(pin): (pin in pins_on) for pin in range(1, 1 + PIN_COUNT)}
    return pin_status


# --- Kód pro přímé spuštění (testování funkcí z helpers) ---
if __name__ == "__main__":
    print("Running helper tests...")
    # Test get_pins_on / save_new_pins_on
    print("Current pins ON (from cache):", get_pins_on())
    save_new_pins_on([1, 5, 15])
    print("Set pins [1, 5, 15]. New state from cache:", get_pins_on())
    save_new_pins_on([])
    print("Set pins []. New state from cache:", get_pins_on())

    # Test get_new_pins_on
    save_new_pins_on([2, 4])
    print("Cache state: [2, 4]")
    print("get_new_pins_on(on=[1], off=[2], all_off=False) ->", get_new_pins_on(on=[1], off=[2], all_off=False)) # Očekává [1, 4]
    print("get_new_pins_on(on=[6], off=[7], all_off=False) ->", get_new_pins_on(on=[6], off=[7], all_off=False)) # Očekává [2, 4, 6]
    print("get_new_pins_on(on=[], off=[], all_off=True) ->", get_new_pins_on(on=[], off=[], all_off=True))       # Očekává []

    # Test turn_on_pins_command
    res = turn_on_pins_command([1, 2])
    expected = b"\x63\x9a\x01\x01\x00\x0b\x57\x57\x00\x00\x00\x03"
    print(f"Cmd for [1, 2]: {res!r} (Expected: {expected!r}) -> {'OK' if res == expected else 'FAIL'}")
    res = turn_on_pins_command([1, 1, 2]) # Test duplicity
    print(f"Cmd for [1, 1, 2]: {res!r} (Expected: {expected!r}) -> {'OK' if res == expected else 'FAIL'}")
    res = turn_on_pins_command([11, 12]) # Piny 11 a 12
    expected = b"\x63\x9a\x01\x01\x00\x0b\x57\x57\x00\x00\x0c\x00" # 2^10 + 2^11 = 1024 + 2048 = 3072 = 0x0C00
    print(f"Cmd for [11, 12]: {res!r} (Expected: {expected!r}) -> {'OK' if res == expected else 'FAIL'}")
    res = turn_on_pins_command([]) # Vše vypnuto
    expected = b"\x63\x9a\x01\x01\x00\x0b\x57\x57\x00\x00\x00\x00"
    print(f"Cmd for []: {res!r} (Expected: {expected!r}) -> {'OK' if res == expected else 'FAIL'}")
    res = turn_on_pins_command([1, 16]) # První a poslední
    expected_val = 1 + 2**15 # 1 + 32768 = 32769 = 0x8001
    expected = PREFIX_CMD + expected_val.to_bytes(2, 'big')
    print(f"Cmd for [1, 16]: {res!r} (Expected: {expected!r}) -> {'OK' if res == expected else 'FAIL'}")

    # Test get_pins_status_dict
    save_new_pins_on([3, 8, 10])
    status = get_pins_status_dict()
    print("Status dict for [3, 8, 10]:", status)
    print("  Pin 3 status:", status.get('3'))
    print("  Pin 4 status:", status.get('4'))
    print("  Pin 8 status:", status.get('8'))
    print("  Pin 10 status:", status.get('10'))
