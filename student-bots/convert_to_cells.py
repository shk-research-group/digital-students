import pandas as pd

# Specify input and output file names
input_csv = 'student_vars_2.csv'
output_csv = 'student_vars_2_cells_output.csv'

# Read the input CSV file into a DataFrame.
# Assumes the first row is the header.
df = pd.read_csv(input_csv)

# Check that we have at least two columns (A plus at least one other)
if df.shape[1] < 2:
    raise ValueError("Input CSV must have at least two columns.")

# The first column (column A) is used as the row label.
row_label_col = df.columns[0]

# Optionally, if you want to ensure you only process columns B to CE,
# you can limit the columns to process. For example, if you know that 'CE'
# is the 83rd column (Excel columns: A=1, B=2, ..., CE=83), then:
# Uncomment the following two lines if needed.
# expected_cols = df.columns[1:83]  # columns B to CE (assuming they exist)
# df = df[[row_label_col] + list(expected_cols)]

# Use pandas.melt to unpivot the DataFrame.
# - id_vars: columns to keep intact (the row label from column A).
# - value_vars: all columns to be unpivoted (columns B to end).
df_melt = df.melt(
    id_vars=row_label_col,
    value_vars=df.columns[1:], 
    var_name='Column Header',
    value_name='Cell Value'
)

# Rename the row label column to "Ax Value"
df_melt.rename(columns={row_label_col: 'Ax Value'}, inplace=True)

# Write the transformed data to the output CSV file.
df_melt.to_csv(output_csv, index=False)

print(f"Transformation complete! Output written to '{output_csv}'.")
