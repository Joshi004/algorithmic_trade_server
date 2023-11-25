from datetime import datetime
import pytz

def current_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return get_string_from_date(datetime.now(ist))


def str_to_ist(date_string, format):
    # Parse the date string into a datetime object
    dt = datetime.strptime(date_string, format)
    # Localize the datetime object to IST
    ist = pytz.timezone('Asia/Kolkata')
    dt = ist.localize(dt)
    return get_string_from_date(dt)

def localize_to_ist(naive_dt):
    # Create a timezone object for IST
    ist = pytz.timezone('Asia/Kolkata')

    # Localize the naive datetime object to IST
    dt_ist = ist.localize(naive_dt)
    return get_string_from_date(dt_ist)

def get_string_from_date(date_bj):
    date_str = str(date_bj)
    date_str = date_str.split(".")[0]
    return date_str

