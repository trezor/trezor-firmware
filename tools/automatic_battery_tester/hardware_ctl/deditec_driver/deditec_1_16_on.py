from __future__ import annotations

import signal
import socket
import sys
from typing import Any
import logging

from typing_extensions import Self # Potřebuje pip install typing-extensions


# !!! ZKONTROLUJ A PŘÍPADNĚ UPRAV VÝCHOZÍ IP !!!
# Tato IP se použije, pokud RelayController nedostane jinou,
# a hlavně se použije v test_deditec_control.py
IP = "192.168.1.10"  # <--- VÝCHOZÍ IP PRO TESTY Z TERMINÁLU
PORT = 9912


class Deditec_1_16_on:
    def __init__(self, ip: str = IP, port: int = PORT, timeout_seconds: int = 3):
        # Použije předanou IP/port, nebo výchozí hodnoty
        self.ip = ip
        self.port = port
        self.timeout_seconds = max(1, timeout_seconds) # Min 1s timeout
        self.socket: socket.socket | None = None # Inicializace na None
        logging.debug(f"Deditec communication object created for {self.ip}:{self.port}")

    def connect(self) -> bool: # Vrací bool pro úspěch/neúspěch
        if self.socket is not None:
             logging.warning("Deditec:: connect called, but socket already exists. Closing first.")
             self.close_connection()

        logging.debug(f"Deditec:: connecting to device at {self.ip}:{self.port}...")
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Nastavení timeoutu pro operace socketu (connect, send, recv)
            self.socket.settimeout(self.timeout_seconds)
            self.socket.connect((self.ip, self.port))
            logging.debug("Deditec:: connection established")
            return True
        except socket.timeout:
            logging.error(f"Deditec:: connection timed out ({self.timeout_seconds}s)")
            self.socket = None # Zajistit, že socket je None při chybě
            return False
        except Exception as e:
            logging.exception(f"Deditec:: error when connecting: {e}")
            self.socket = None
            return False

    def send_command(self, command: bytes) -> int: # Vrací 0 pro úspěch, >0 pro chybu
        if self.socket is None:
            logging.error("Deditec:: send_command called but not connected.")
            return 1 # Chyba - není připojeno

        logging.debug(f"Deditec:: sending command: {command!r}")
        try:
            self.socket.sendall(command)
            # Čekání na odpověď (očekává se nějaká?)
            # Původní kód četl data, i když je nepoužíval. Zkusíme to také.
            # Velikost bufferu může být malá, pokud neočekáváme velkou odpověď.
            data = self.socket.recv(64) # Přečíst malou odpověď
            logging.debug(f"Deditec:: received confirmation data (len={len(data)}): {data!r}")
            return 0 # Předpokládáme úspěch, pokud sendall a recv nehodily výjimku
        except socket.timeout:
             logging.error(f"Deditec:: socket timeout during send/recv ({self.timeout_seconds}s)")
             return 2 # Chyba - timeout
        except Exception as e:
            logging.exception(f"Deditec:: error sending command or receiving confirmation: {e}")
            return 3 # Jiná chyba

    def close_connection(self) -> None:
        if self.socket:
            logging.debug("Deditec:: closing connection")
            try:
                self.socket.close()
            except Exception as e:
                 logging.error(f"Deditec:: error closing socket: {e}")
            finally:
                 self.socket = None # Vždy nastavit na None
        else:
             logging.debug("Deditec:: close_connection called but already closed.")


    def __enter__(self) -> Self:
        # Nastavení SIGALRM pro celkový timeout operace (funguje jen v hlavním vlákně na Unixu)
        # V jiných případech spoléháme na socket timeout
        try:
            signal.alarm(self.timeout_seconds + 1) # Dáme o 1s víc než socket timeout
        except ValueError: # Stává se ve Windows nebo mimo hlavní vlákno
             logging.warning("Cannot set SIGALRM handler (not on Unix main thread?), relying on socket timeout.")
             pass # Pokračujeme bez alarmu

        if not self.connect():
            signal.alarm(0) # Zrušit alarm, pokud byl nastaven
            # Vyvolat specifickou výjimku pro připojení
            raise ConnectionError(f"Failed to connect to Deditec device at {self.ip}:{self.port}")
        # Nepotřebujeme rušit alarm zde, udělá se v __exit__
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        # Vždy zrušit alarm a zavřít spojení
        try:
             signal.alarm(0)
        except ValueError:
             pass
        self.close_connection()

        if exc_type: # Pokud došlo k výjimce uvnitř 'with' bloku
            logging.error(f"Deditec:: An error occurred during 'with' block: {exc_type.__name__}: {exc_val}")
            # return False # Předáme výjimku dál (standardní chování)
        return False # Vždy předat výjimku dál, pokud nastala


# --- Kód pro přímé spuštění (test připojení) ---
if __name__ == "__main__":
    # Tento test se spustí jen při `python libs/backend/deditec_driver/deditec_1_16_on.py`
    print("Running direct connection test...")
    # Použijeme try-except místo __enter__/__exit__ pro jednodušší test
    tester = Deditec_1_16_on(timeout_seconds=2) # Krátký timeout pro test
    if tester.connect():
        print(f"SUCCESS: Connected to Deditec device at {tester.ip}:{tester.port}")
        print("Closing connection.")
        tester.close_connection()
        sys.exit(0) # Úspěch
    else:
        print(f"ERROR: Failed to connect to Deditec device at {tester.ip}:{tester.port}")
        sys.exit(1) # Neúspěch
