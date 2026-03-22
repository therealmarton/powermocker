import pandas as pd
import numpy as np
import os
from WS import WeatherSimulator
from HP import HouseProfile
import requests
import json

# --- KONFIGURÁCIÓ ---
WEBHOOK_URL = "https://webhook.site/80ceec4e-52ca-4670-9dd5-93664542a88c"  # Cseréld ki a saját URL-edre
OUTPUT_DIR = "haz_adatok"

def trigger_webhook(payload):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers)
        return response.status_code
    except Exception as e:
        print(f"Webhook hiba: {e}")
        return None
    
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
        HouseProfile("Haz_1_Idos", "elderly", has_solar=False, solar_kwp=0, base_load_kwh=0.03),
        HouseProfile("Haz_2_Csalad", "family",  has_solar=False, solar_kwp=0, base_load_kwh=0.05),
        HouseProfile("Haz_3_Egyedul", "single",  has_solar=False, solar_kwp=0, base_load_kwh=0.02),
        HouseProfile("Haz_4_Solar_Idos", "elderly", has_solar=True,  solar_kwp=3.5, base_load_kwh=0.03),
        HouseProfile("Haz_5_Solar_Csalad", "family",  has_solar=True,  solar_kwp=6.0, base_load_kwh=0.05),
        HouseProfile("Haz_6_Solar_Egyedul", "single",  has_solar=True,  solar_kwp=4.0, base_load_kwh=0.03),
    ]
    all_houses_list = [] # Összes ház adatait gyűjtő lista a webhook payload-hoz

    for house in houses:
        df = pd.DataFrame({'timestamp': timestamps})
        df['house_id'] = house.name
        df['profile'] = house.profile_type
        
        # --- VÁLTOZÓK DEFINIÁLÁSA (A hiányzó rész) ---
        
        # Hónap és óra kinyerése
        months = df['timestamp'].dt.month.to_numpy()
        hours = df['timestamp'].dt.hour.to_numpy()
        
        # 1. Szezonalitás (Télen több fogyasztás: Januárban max, Júliusban min)
        seasonal_demand = 1.0 + 0.25 * np.cos(np.pi * (months - 1) / 6)
        
        # 2. Időbeli eltolás (Jitter minden napra)
        days = len(df) // 96
        time_shift = np.random.randint(-1, 2, size=days+1)
        shifts = np.repeat(time_shift, 96)[:len(df)]
        shifted_hours = (hours + shifts) % 24
        
        # 3. Profil súlyok lekérése a HP-ból
        profile_weights = np.array([house.get_consumption_weight(h) for h in shifted_hours], dtype=float)
        
        # 4. Zaj és váratlan fogyasztási tüskék (Spikes)
        base_noise = np.random.uniform(0.7, 1.3, len(df))
        spikes = np.random.choice([0, 0.15, 0.4], size=len(df), p=[0.96, 0.03, 0.01])
        
        # --- SZÁMÍTÁSOK ---

        # FOGYASZTÁS
        df['consumption_kwh'] = (house.base_load + (profile_weights * base_noise * seasonal_demand) + spikes)
        
        # TERMELÉS
        if house.has_solar:
            df['generation_kwh'] = (house.solar_kwp * solar_factors) / 4
        else:
            df['generation_kwh'] = 0.0
            
        # NETTÓ FORGALOM (+ vétel, - betáplálás)
        df['net_grid_flow'] = df['consumption_kwh'] - df['generation_kwh']
        
        # --- VILLANYÓRA ÁLLÁSOK (KUMULÁLT) ---
        
        # 1. Vételezés mérője (Import): Csak a pozitív flow-t gyűjti
        import_flow = np.where(df['net_grid_flow'] > 0, df['net_grid_flow'], 0)
        df['meter_import_kwh'] = np.cumsum(import_flow)
        
        # 2. Betáplálás mérője (Export): Csak a negatív flow abszolút értékét gyűjti
        export_flow = np.where(df['net_grid_flow'] < 0, abs(df['net_grid_flow']), 0)
        df['meter_export_kwh'] = np.cumsum(export_flow)
        
        # KEREKÍTÉS 6 tizedesre
        cols = ['consumption_kwh', 'generation_kwh', 'net_grid_flow', 'meter_import_kwh', 'meter_export_kwh']
        df[cols] = df[cols].round(6)
        
        # Adatok hozzáadása az összes ház listájához a webhook-hoz
        all_houses_list.append(df.copy())

        # Fájl mentése
        file_path = os.path.join(output_dir, f"{house.name}.csv")
        df.to_csv(file_path, index=False)
        print(f"Kész (mérőórákkal és szezonalitással): {house.name}")
    # --- ÖSSZEFÉSÜLÉS (OLLÓZÁS) ---
    
    master_df = pd.concat(all_houses_list)
    master_df = master_df.sort_values(by=['timestamp', 'house_id'])
    
    # Mentés egy nagy fájlba
    master_file = os.path.join(OUTPUT_DIR, "osszes_haz_adat.csv")
    master_df.to_csv(master_file, index=False)
    print(f"\nMaster CSV elmentve: {master_file}")

    # --- WEBHOOK KÜLDÉS ---
    print("Webhook küldése folyamatban...")
    master_df['timestamp'] = master_df['timestamp'].apply(lambda x: x.isoformat() if hasattr(x, 'isoformat') else str(x))
    records = master_df.to_dict('records')
    
    # 6 ház * 96 negyedóra = 576 sor naponta
    chunk_size = 576 
    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        payload = {
            "type": "batch_update",
            "data": chunk
        }
        status = trigger_webhook(payload)
        if i % (chunk_size * 10) == 0: # Csak minden 10. napnál írjunk ki státuszt
            print(f"  Feltöltés: {i}/{len(records)} sor... Status: {status}")
if __name__ == "__main__":
    run_simulation()