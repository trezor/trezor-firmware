# Every application is supposed to have two entry points:
#
# boot() is called during device boot time and it should prepare
# all global things necessary to run.
#
# dispatch() is called once event subscribed in boot() is received.

def dispatch():
    # Callback for HID messages
    print("Dispatch homescreen")

def boot():
    # Initilize app on boot time.
    # This should hookup HID message types dispatcher() wants to receive.
    print("Stickova appka")
