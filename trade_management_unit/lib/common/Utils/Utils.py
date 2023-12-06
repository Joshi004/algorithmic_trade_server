from datetime import datetime
import pytz

def current_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return get_date_without_time_zone(datetime.now(ist))


def str_to_ist(date_string, format):
    # Parse the date string into a datetime object
    dt = datetime.strptime(date_string, format)
    # Localize the datetime object to IST
    ist = pytz.timezone('Asia/Kolkata')
    dt = ist.localize(dt)
    return get_date_without_time_zone(dt)

def localize_to_ist(naive_dt):
    # Create a timezone object for IST
    ist = pytz.timezone('Asia/Kolkata')

    # Localize the naive datetime object to IST
    dt_ist = ist.localize(naive_dt)
    return get_date_without_time_zone(dt_ist)

def get_date_without_time_zone(date_bj):
    date_str = str(date_bj)
    date_str = date_str.split(".")[0]
    return get_date_obj(date_str)

def get_date_obj(date_string):
    date_str = date_string.split("+")[0].split(".")[0]
    date_format = "%Y-%m-%d %H:%M:%S"
    date_object = datetime.strptime(date_str, date_format)
    return date_object
