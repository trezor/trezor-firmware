import datetime

log_level = "None"
log_timestamps = False


def __get_timestamp():
    return str(datetime.datetime.now())


def __log_message(message):
    if log_timestamps == True:
        print(f"{__get_timestamp()}\t{message}")
    else:
        print(message)


def log_uhid_event(event_name, params=None):
    if log_level == "uhid-event":
        if params:
            __log_message(f"{event_name}\t{params}")
        else:
            __log_message(event_name)


def log_hid_packet(packet_name, payload):
    if log_level == "hid-packet":
        __log_message(f"{packet_name}\t{payload}")


def log_raw(direction, payload):
    if log_level == "raw":
        __log_message(f"{direction}\t{payload}")
