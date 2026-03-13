from API_iSolarCloud import refresh_plants_snapshot


def main(): 
    print(refresh_plants_snapshot(year=2026, json_path="plants_data.json"))
    
if __name__ == "__main__":
    main()