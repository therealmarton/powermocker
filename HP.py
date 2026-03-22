import numpy as np

class HouseProfile:
    def __init__(self, name, profile_type, has_solar, solar_kwp, base_load_kwh):
        self.name = name
        self.profile_type = profile_type
        self.has_solar = has_solar
        self.solar_kwp = solar_kwp
        self.base_load = base_load_kwh

    def get_consumption_weight(self, hour):
        if self.profile_type == 'elderly':
            # Idős: Korai kelés, déli főzés, délután szieszta, korai fekvés
            weights = {
                0: 0.01, 5: 0.01, 7: 0.3, 10: 0.15, 
                12: 0.8, 15: 0.1, 18: 0.4, 21: 0.2, 23: 0.01
            }
        elif self.profile_type == 'family':
            # Család: Reggeli káosz, napközben üres ház, este nagyüzem (mosás, főzés, TV)
            weights = {
                0: 0.01, 6: 0.05, 7: 0.9, 9: 0.1, 
                15: 0.1, 17: 0.6, 19: 1.3, 22: 0.4, 23: 0.02
            }
        else: # single
            # Egyedülálló: Reggel kávé, egész nap munka, késő este aktív
            weights = {
                0: 0.01, 7: 0.2, 9: 0.05, 17: 0.1, 
                19: 0.8, 21: 1.1, 23: 0.3, 24: 0.01
            }
            
        sorted_hours = sorted(weights.keys())
        sorted_values = [weights[h] for h in sorted_hours]
        return float(np.interp(hour, sorted_hours, sorted_values))