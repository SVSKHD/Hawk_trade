import MetaTrader5 as mt5


def connect_mt5():
    if not mt5.initialize():
        print("Failed to initialize MetaTrader5")
        return False
    login = 213171528  # Login provided
    password = "AHe@Yps3"  # Password provided
    server = "OctaFX-Demo"  # Server provided

    authorized = mt5.login(login, password=password, server=server)
    if not authorized:
        print(f"Login failed for account {login}")
        return False
    print(f"Successfully logged into account {login} on server {server}")
    return True


