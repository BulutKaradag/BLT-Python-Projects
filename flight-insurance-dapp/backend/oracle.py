import random

def check_flight_status(flight_number: str) -> str:
    """
    FlightAware veya Aviation Edge gibi API'lerin sahte (mock) versiyonu.
    Uçuşun anlık durumunu döner. Prototip için rastgele veya hardcoded.
    """
    flight_num_upper = flight_number.upper()
    
    # "CANCEL" veya "DELAY" barındıran uçuş numaralarında her zaman ödeme yapsın.
    if "CANCEL" in flight_num_upper:
        return "CANCELLED"
    if "DELAY" in flight_num_upper:
        return "DELAYED"
        
    # Diğerleri %80 ihtimalle normal, %20 ihtimalle iptal/gecikmeli (Demo için simülasyon)
    statuses = ["ON_TIME", "ON_TIME", "ON_TIME", "ON_TIME", "CANCELLED", "DELAYED"]
    return random.choice(statuses)
