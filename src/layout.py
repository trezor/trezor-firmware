from trezor import ui

def show_send(address, amount, currency='BTC'):
   ui.display.bar(0, 0, 240, 40, ui.GREEN)
   ui.display.bar(0, 40, 240, 200, ui.WHITE)
   ui.display.text(10, 28, 'Sending', ui.BOLD, ui.WHITE, ui.GREEN)
   ui.display.text(10, 80, '%f %s' % (amount, currency), ui.BOLD, ui.BLACK, ui.WHITE)
   ui.display.text(10, 110, 'to this address:', ui.NORMAL, ui.BLACK, ui.WHITE)
   ui.display.text(10, 140, address[:18], ui.MONO, ui.BLACK, ui.WHITE)
   ui.display.text(10, 160, address[18:], ui.MONO, ui.BLACK, ui.WHITE)
