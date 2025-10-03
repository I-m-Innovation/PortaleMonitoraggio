from django.db import connection
import pandas as pd



def datiTabella( table_suffix=None):
    impianti_mapping = {
        'BA': 'Partitore',
        'I1': 'Torrino Foresta', 
        'PE': 'San Teodoro',
        'PG': 'Ponte Giurino'
    }
    table_names = ["corrispettivi_energia_BA", "corrispettivi_energia_I1", "corrispettivi_energia_PE", "corrispettivi_energia_PG"]
    if table_suffix:
        table_names = [f"corrispettivi_energia_{table_suffix}"]

    all_data = []
    with connection.cursor() as cursor:
        for table_name in table_names:
            try:
                cursor.execute(f'SELECT * FROM "{table_name}"')
                rows = cursor.fetchall()
                col_names = [desc[0] for desc in cursor.description]
                
                if rows:
                    df = pd.DataFrame(rows, columns=col_names)
                    suffix = table_name.split('_')[-1]  # Estrae BA, I1, PE, PG
                    df['impianto_nickname'] = suffix
                    df['impianto_nome'] = impianti_mapping.get(suffix, suffix)
                    all_data.append(df)
            except Exception as e:
                print(f"Errore nel recuperare dati dalla tabella {table_name}: {e}")
                continue
   
    # Combina tutti i DataFrame in uno solo
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()



if __name__ == "__main__":
    print(datiTabella('BA'))