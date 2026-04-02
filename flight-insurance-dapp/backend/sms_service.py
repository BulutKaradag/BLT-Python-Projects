def send_sms(phone_number: str, message: str):
    """
    Simüle edilmiş SMS gönderme fonksiyonu.
    Gerçek senaryoda burada Twilio API (örn: client.messages.create) kullanılırdı.
    """
    print("\n========================================")
    print(f"[SMS GONDERILIYOR] -> {phone_number}")
    print(f"Mesaj: {message}")
    print("========================================\n")
    return True
