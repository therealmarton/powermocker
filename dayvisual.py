import pandas as pd
import matplotlib.pyplot as plt
import os
import random

def visualize_random_day(file_path, target_date=None):
    # Adatok beolvasása
    df = pd.read_csv(file_path, parse_dates=['timestamp'])
    
    # Ha nincs megadva dátum, választunk egy véletlenszerűt, ahol süt a nap (június-augusztus között érdemes)
    if target_date is None:
        random_row = random.randint(0, len(df) - 96)
        target_date = df.iloc[random_row]['timestamp'].strftime('%Y-%m-%d')
    
    # Szűrés az adott napra
    day_df = df[df['timestamp'].dt.strftime('%Y-%m-%d') == target_date].copy()
    
    if day_df.empty:
        print(f"Nincs adat ezen a napon: {target_date}")
        return

    house_name = os.path.basename(file_path).replace('.csv', '')

    # Grafikon készítése
    plt.figure(figsize=(12, 7))
    
    # 1. Fogyasztás (vörös terület)
    plt.fill_between(day_df['timestamp'], day_df['consumption_kwh'], 0, 
                     color='red', alpha=0.2, label='Fogyasztás (kWh)')
    plt.plot(day_df['timestamp'], day_df['consumption_kwh'], color='red', linewidth=1.5)

    # 2. Napelem termelés (zöld terület)
    if day_df['generation_kwh'].max() > 0:
        plt.fill_between(day_df['timestamp'], day_df['generation_kwh'], 0, 
                         color='green', alpha=0.3, label='Napelem termelés (kWh)')
        plt.plot(day_df['timestamp'], day_df['generation_kwh'], color='green', linewidth=1.5)

    # 3. Nettó egyenleg (szaggatott vonal)
    plt.plot(day_df['timestamp'], day_df['net_grid_flow'], color='black', 
             linestyle='--', linewidth=1, label='Nettó hálózati forgalom')

    # Dekoráció
    plt.title(f"{house_name} - Napi profil: {target_date}", fontsize=14)
    plt.xlabel("Idő (óra:perc)")
    plt.ylabel("Energia (kWh / 15 perc)")
    
    # X tengely formázása (hogy órákat mutasson)
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    
    plt.grid(True, which='both', linestyle=':', alpha=0.5)
    plt.legend()
    plt.tight_layout()

    output_name = f"{house_name}_{target_date}.png"
    plt.savefig(output_name)
    print(f"Napi grafikon elmentve: {output_name}")
    plt.show()

if __name__ == "__main__":
    # Itt válaszd ki, melyik házat akarod nézni
    test_file = "haz_adatok/Haz_4_Solar_Idos.csv"
    
    if os.path.exists(test_file):
        # Ha konkrét napot akarsz: visualize_random_day(test_file, "2026-06-15")
        visualize_random_day(test_file)
    else:
        print("A fájl nem található! Futtasd le a generátort előbb.")