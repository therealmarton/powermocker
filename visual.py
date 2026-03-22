import pandas as pd
import matplotlib.pyplot as plt
import os

def visualize_house(file_path):
    # Beolvasás (indexnek a timestamp-et használjuk)
    df = pd.read_csv(file_path, parse_dates=['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    house_name = os.path.basename(file_path).replace('.csv', '')
    
    # Grafikon ablak létrehozása
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), sharex=True)
    plt.subplots_adjust(hspace=0.3)

    # --- 1. FOGYASZTÁS ÉS TERMELÉS ---
    ax1.plot(df.index, df['consumption_kwh'], label='Fogyasztás (kWh)', color='red', alpha=0.6, linewidth=0.5)
    if df['generation_kwh'].max() > 0:
        ax1.plot(df.index, df['generation_kwh'], label='Napelem termelés (kWh)', color='green', alpha=0.5, linewidth=0.5)
    
    ax1.set_title(f"{house_name} - Éves energiaforgalom")
    ax1.set_ylabel("Energia (kWh / 15min)")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # --- 2. NETTÓ FORGALOM (VÉTEL/ELADÁS) ---
    # Kiszámolunk egy 24 órás gördülő átlagot, hogy lássuk a trendet a zaj alatt
    rolling_net = df['net_grid_flow'].rolling(window=96).mean() 
    
    ax2.fill_between(df.index, df['net_grid_flow'], 0, where=(df['net_grid_flow'] > 0), 
                     facecolor='orange', alpha=0.3, label='Hálózati vétel')
    ax2.fill_between(df.index, df['net_grid_flow'], 0, where=(df['net_grid_flow'] < 0), 
                     facecolor='blue', alpha=0.3, label='Visszatáplálás')
    ax2.plot(df.index, rolling_net, color='black', linewidth=1, label='Napi trend (átlag)')

    ax2.set_title("Hálózati egyenleg (Net Grid Flow)")
    ax2.set_ylabel("kWh")
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    # Mentés képként
    output_image = f"{house_name}_summary.png"
    plt.savefig(output_image, dpi=300)
    print(f"Grafikon elmentve: {output_image}")
    plt.show()

if __name__ == "__main__":
    # Teszteljük az egyik napelemes házon
    file_to_plot = "haz_adatok/Haz_1_Idos.csv"
    if os.path.exists(file_to_plot):
        visualize_house(file_to_plot)
    else:
        print(f"Hiba: A {file_to_plot} fájl nem található. Előbb futtasd a generátort!")