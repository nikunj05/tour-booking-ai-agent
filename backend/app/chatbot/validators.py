from datetime import datetime

def valid_date(text):
    try:
        datetime.strptime(text, "%d/%m/%Y")
        return True
    except ValueError:
        return False

def valid_int(text):
    return text.isdigit() and int(text) > 0
