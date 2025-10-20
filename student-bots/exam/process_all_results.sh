#!/bin/bash

# Array of input files to process
declare -a input_files=(
  # "exam_results_requests_111_batch_no_vark_v1_20250608_125146.json"
  # "exam_results_requests_111_batch_vark_v1_20250608_125933.json"
  # "exam_results_requests_121_batch_no_vark_v1_20250608_111604.json"
  # "exam_results_requests_121_batch_vark_v1_20250608_112028.json"
  # "exam_results_requests_ktqt_batch_no_vark_v3_20250608_110244.json"
  # "exam_results_requests_ktqt_batch_vark_v1_20250608_111106.json"
  # "exam_results_20250608_153952.json"
  # "exam_results_20250609_030300.json"
  # "exam_results_20250609_052649.json"
  # "exam_results_20250608_211921.json"
  # "exam_results_requests_ktqt_batch_vark_v2_20250611_093042.json"
  # "exam_results_requests_121_batch_no_vark_v2_20250611_094015.json"
  "exam_results_ktqt_individual_no_material_basic_prompt_v1_20250627_220712.json"
  "exam_results_121_individual_no_material_basic_prompt_v1_20250627_173956.json"
  "exam_results_121_individual_no_material_best_prompt_v1_20250627_153816.json"
  "exam_results_ktqt_individual_no_material_best_prompt_v1_20250627_200339.json"
)

echo "Starting to process all result files..."
echo "Total files to process: ${#input_files[@]}"
echo ""

# Process each file
for input_file in "${input_files[@]}"; do
  echo "Processing file: $input_file"
  
  # Check if the file exists
  if [ ! -f "$input_file" ]; then
    echo "Error: File $input_file not found. Skipping."
    continue
  fi
  
  # Run the Python script with the input file
  INPUT_FILE="$input_file" python3 process_students.py
  
  # Check if processing was successful
  if [ $? -ne 0 ]; then
    echo "Error processing $input_file"
  else
    echo "Successfully processed $input_file"
  fi
  
  echo ""
done

echo "All files have been processed."
echo "CSV files are available in the same directory." 