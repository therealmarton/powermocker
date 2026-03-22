import numpy as np

class WeatherSimulator:
    def __init__(self, timestamps):
        self.timestamps = timestamps
        
    def get_solar_factor(self):
        # Adatok kinyerése
        hour = (self.timestamps.hour + self.timestamps.minute / 60).to_numpy()
        month = self.timestamps.month.to_numpy()
        
        # 1. Napi ciklus finomítása
        # day_length: télen kb. 8.5 óra, nyáron 15.5 óra (Magyarországra reálisabb)
        day_length = 12 + 3.5 * np.cos(np.pi * (month - 6) / 6)
        sunrise = 12 - day_length / 2
        sunset = 12 + day_length / 2
        
        # Inicializálunk egy nulla tömböt
        solar_day = np.zeros(len(self.timestamps))
        
        # Csak ott számolunk szinuszt, ahol nappal van (sunrise < hour < sunset)
        daytime_mask = (hour > sunrise) & (hour < sunset)
        
        # Itt már nincs nullával osztás, mert a day_length minimuma 8.5
        solar_day[daytime_mask] = np.sin(np.pi * (hour[daytime_mask] - sunrise[daytime_mask]) / day_length[daytime_mask])
        
        # Biztonsági clip (negatív értékek ellen, bár a maszk miatt elvileg nem kell)
        solar_day = np.clip(solar_day, 0, None)
        
        # 2. Szezonalitás (A Nap ereje)
        # Júniusban szorzó: 1.0, Decemberben: 0.25 (télen gyengébb a beesési szög)
        seasonal_mult = 0.625 + 0.375 * np.cos(np.pi * (month - 6) / 6)
        
        # 3. Felhősség (Random negyedórás ingadozás)
        clouds = np.random.uniform(0.3, 1.0, len(self.timestamps))
        
        # 4. Rossz idő faktor (egész napos borultság esélye)
        days = len(self.timestamps) // 96
        daily_weather = np.random.choice([0.15, 0.5, 1.0], size=days + 1, p=[0.1, 0.2, 0.7])
        bad_weather_factor = np.repeat(daily_weather, 96)[:len(self.timestamps)]
        
        return solar_day * seasonal_mult * clouds * bad_weather_factor