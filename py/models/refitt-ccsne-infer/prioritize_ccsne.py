import json
import pandas as pd
import numpy as np
import os
import glob

weights = (0.1,0.8,0.9)

def read_data_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def calculate_weight(logZ, mass_loss_rate, phase, weights = weights):
    weight_logZ, weight_mass_loss, weight_phase = weights

    # Use the absolute value of logZ
    abs_logZ = abs(logZ)

    # Your logic to calculate the weighted sum based on criteria
    weighted_sum = (
        weight_logZ * abs_logZ +
        weight_mass_loss * mass_loss_rate +
        weight_phase * (1.0 if phase < 30 or phase > 100 else 0.0))
    
    return weighted_sum

def prioritize_files(file_paths, weights = weights):
    prioritized_data = []

    for file_path in file_paths:
        data = read_data_from_file(file_path)
        
        logZ = data.get('parameters', {}).get('logZ', 0.0)[0]
        mass_loss_rate = data.get('parameters', {}).get('mloss_rate', 0.0)[0]
        phase = data.get('parameters', {}).get('Phase', 0) 
        
        # Calculate weight based on criteria
        weight = calculate_weight(logZ, mass_loss_rate, phase, weights = weights)
        ztf_id = os.path.basename(file_path).split('_')[0]

        # Store the relevant information
        prioritized_data.append({
            'ZTF Event Name': ztf_id,
            'logZ': -logZ,  # Negative sign as requested
            'Mass Loss Rate': mass_loss_rate,
            'Phase': phase,
            'Assigned Weight': weight,
            'Link': 'https://alerce.online/object/'+ztf_id
        })

    # Create a Pandas DataFrame
    df = pd.DataFrame(prioritized_data)

    # Sort the DataFrame by final assigned weight
    df = df.sort_values(by='Assigned Weight', ascending=False)

    return df.reset_index(drop=True)

"*****************************************************************"

file_array =np.sort(glob.glob('./*.json'))

selected_files = {}

# Iterate over the array and select the first _g or _r file for each ZTF id
for file_path in file_array:
    ztf_id = os.path.basename(file_path).split('_')[0]  # Extract ZTF id
    if ztf_id not in selected_files and ('_g' in file_path or '_r' in file_path):
        selected_files[ztf_id] = file_path

# Convert the selected files dictionary values to a numpy array
result_array = np.array(list(selected_files.values()))

# Adjust these weights as needed
weights = (0.1,0.8,0.9)
result_df = prioritize_files(result_array, weights = weights)

result_df.to_csv('prioritized_ccsne.txt', sep='\t', index=False)

# Display the final DataFrame
print(result_df)

