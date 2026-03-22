import pandas as pd
import numpy as np
import os
from WS import WeatherSimulator
from HP import HouseProfile 

def run_simulation():
    # Mappa létrehozása a fájloknak
    output_dir = "haz_adatok"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Időkeret (DatetimeIndex)
    timestamps = pd.date_range(start='2026-01-01', end='2026-12-31 23:45:00', freq='15min')
    
    # Időjárás adatok lekérése
    weather = WeatherSimulator(timestamps)
    solar_factors = weather.get_solar_factor()
    
    # 6 Ház definiálása
    houses = [
        HouseProfile("Haz_1_Idos", "elderly", has_solar=False, solar_kwp=0, base_load_kwh=0.04),
        HouseProfile("Haz_2_Csalad", "family",  has_solar=False, solar_kwp=0, base_load_kwh=0.08),
        HouseProfile("Haz_3_Egyedul", "single",  has_solar=False, solar_kwp=0, base_load_kwh=0.03),
        HouseProfile("Haz_4_Solar_Idos", "elderly", has_solar=True,  solar_kwp=3.5, base_load_kwh=0.05),
        HouseProfile("Haz_5_Solar_Csalad", "family",  has_solar=True,  solar_kwp=6.0, base_load_kwh=0.09),
        HouseProfile("Haz_6_Solar_Egyedul", "single",  has_solar=True,  solar_kwp=4.0, base_load_kwh=0.04),
    ]
    
    for house in houses:
        df = pd.DataFrame({'timestamp': timestamps})
        df['house_id'] = house.name
        df['profile'] = house.profile_type
        
        # 1. RANDOM: Időbeli eltolás
        days = len(df) // 96
        time_shift = np.random.randint(-1, 2, size=days+1)
        shifts = np.repeat(time_shift, 96)[:len(df)]
        
        # A shifted_hours kiszámítása és a súlyok lekérése (biztosítva a float típust)
        shifted_hours = (df['timestamp'].dt.hour + shifts) % 24
        profile_weights = np.array([house.get_consumption_weight(h) for h in shifted_hours], dtype=float)
        
        # 2. RANDOM: Alapzaj + "Spike-ok"
        base_noise = np.random.uniform(0.8, 1.2, len(df)) 
        spikes = np.random.choice([0, 0.15, 0.4], size=len(df), p=[0.96, 0.03, 0.01])
        
        # Fogyasztás számítása
        df['consumption_kwh'] = (house.base_load + (profile_weights * base_noise) + spikes)
        
        # 3. Termelés szimulálása (Fixálva: Mindig létrejön az oszlop)
        if house.has_solar:
            df['generation_kwh'] = (house.solar_kwp * solar_factors) / 4
        else:
            df['generation_kwh'] = 0.0
            
        # 4. Nettó forgalom számítása (Most már létezik a generation_kwh!)
        df['net_grid_flow'] = df['consumption_kwh'] - df['generation_kwh']
        
        # 5. KEREKÍTÉS 6 tizedesre
        cols_to_round = ['consumption_kwh', 'generation_kwh', 'net_grid_flow']
        df[cols_to_round] = df[cols_to_round].round(6)
        
        # Fájl mentése
        file_path = os.path.join(output_dir, f"{house.name}.csv")
        df.to_csv(file_path, index=False)
            
        print(f"Elmentve: {file_path}")

if __name__ == "__main__":
    run_simulation()