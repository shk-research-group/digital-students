#!/bin/bash

# Define all configurations to run
declare -a configs=(
  # Format: "script_file|exam_name|exam_file|root_prompt|endpoint_url"
  
  # Configurations for taking_exam_requests.py (all questions in one request)
  #"taking_exam_requests.py|ktqt_batch_no_vark_v3|exam_ktqt.json|DoingExamNoVARKAllTests"
  # "taking_exam_requests.py|ktqt_batch_vark_v2|exam_ktqt.json|DoingExamAllTests"
  # "taking_exam_requests.py|121_batch_no_vark_v2|exam_121.json|DoingExamNoVARKAllTests"
  #"taking_exam_requests.py|121_batch_vark_v1|exam_121.json|DoingExamAllTests"
  # "taking_exam_requests.py|111_batch_no_vark_v1|exam_111.json|DoingExamNoVARKAllTests"
  # "taking_exam_requests.py|111_batch_vark_v1|exam_111.json|DoingExamAllTests"
  
  # Configurations for taking_exam_requests.py (individual requests)
  "taking_exam.py|121_individual_no_material_best_prompt_v1|exam_121.json|DoingExamWrongAndCorrect|https://n8n.khiemfle.com/webhook/139644a9-2fd6-4c59-ba4a-ecf406da70bb"
  "taking_exam.py|121_individual_no_material_basic_prompt_v1|exam_121.json|DoingExamBasic|https://n8n.khiemfle.com/webhook/29b96adf-2182-4365-a5c1-8247e58809b7"
  "taking_exam.py|ktqt_individual_no_material_best_prompt_v1|exam_ktqt.json|DoingExamWrongAndCorrect|https://n8n.khiemfle.com/webhook/139644a9-2fd6-4c59-ba4a-ecf406da70bb"
  "taking_exam.py|ktqt_individual_no_material_basic_prompt_v1|exam_ktqt.json|DoingExamBasic|https://n8n.khiemfle.com/webhook/29b96adf-2182-4365-a5c1-8247e58809b7"
  # "taking_exam.py|121_individual_v4|exam_121.json|DoingExamNoVARK"
  # "taking_exam.py|ktqt_individual_v1|exam_ktqt.json|DoingExamNoVARK"
  # "taking_exam.py|111_individual_v2|exam_111.json|DoingExamNoVARK"
)

# Function to run a specific configuration
run_config() {
  script_file=$1
  exam_name=$2
  exam_file=$3
  root_prompt=$4
  endpoint_url=$5
  
  echo "========================================================"
  echo "Running test with configuration:"
  echo "  Script: $script_file"
  echo "  Exam Name: $exam_name"
  echo "  Exam File: $exam_file"
  echo "  Root Prompt: $root_prompt"
  echo "  Endpoint URL: $endpoint_url"
  echo "========================================================"
  
  # Run the Python script with the specified configuration
  EXAM_ROOT_PROMPT=$root_prompt \
  EXAM_NAME=$exam_name \
  EXAM_QUESTIONS_FILE=$exam_file \
  EXAM_ENDPOINT_URL=$endpoint_url \
  python3 $script_file
  
  echo "Completed $exam_name using $script_file"
  echo ""
  
  # Sleep to avoid potential rate limiting
  sleep 5
}

# Check if a specific configuration was requested
if [ $# -eq 1 ]; then
  config_index=$1
  if [ $config_index -ge 0 ] && [ $config_index -lt ${#configs[@]} ]; then
    # Split the selected configuration by pipe
    IFS='|' read -ra config_parts <<< "${configs[$config_index]}"
    run_config "${config_parts[0]}" "${config_parts[1]}" "${config_parts[2]}" "${config_parts[3]}" "${config_parts[4]}"
    exit 0
  else
    echo "Invalid configuration index. Please specify a number between 0 and $((${#configs[@]} - 1))"
    exit 1
  fi
fi

# Run all configurations if no specific one was requested
echo "Starting all exam configurations..."
echo "Total configurations to run: ${#configs[@]}"
echo ""

for i in "${!configs[@]}"; do
  # Split the configuration by pipe
  IFS='|' read -ra config_parts <<< "${configs[$i]}"
  
  echo "Running configuration $i of ${#configs[@]}"
  run_config "${config_parts[0]}" "${config_parts[1]}" "${config_parts[2]}" "${config_parts[3]}" "${config_parts[4]}"
done

echo "All exam configurations completed!"
echo "Results are saved in the exam_results_*.json files." 
