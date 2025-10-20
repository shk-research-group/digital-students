#!/usr/bin/env python3
"""
PPTX to PDF Converter

This script converts PowerPoint (PPTX) files to PDF format.
It supports both Windows (using comtypes) and other platforms (using LibreOffice).

Usage:
    python pptx-to-pdf.py <input_pptx_file> [output_pdf_file]
    python pptx-to-pdf.py --folder <input_folder> [output_folder]
    
    If output_pdf_file is not specified, it will use the same name as the input file with .pdf extension.
    If output_folder is not specified, PDFs will be saved in the same folder as the input files.
"""

import os
import sys
import platform
import subprocess
import glob
from pathlib import Path


def convert_with_comtypes(input_file, output_file):
    """Convert PPTX to PDF using comtypes (Windows only)"""
    import comtypes.client
    
    # Get absolute paths
    input_file_abs = os.path.abspath(input_file)
    output_file_abs = os.path.abspath(output_file)
    
    # Create PowerPoint application
    powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
    powerpoint.Visible = True
    
    try:
        # Open the presentation
        presentation = powerpoint.Presentations.Open(input_file_abs)
        
        # Save as PDF
        presentation.SaveAs(output_file_abs, 32)  # 32 is the PDF format code
        presentation.Close()
        
        print(f"Successfully converted {input_file} to {output_file}")
        return True
    except Exception as e:
        print(f"Error converting file: {e}")
        return False
    finally:
        # Close PowerPoint
        powerpoint.Quit()


def convert_with_libreoffice(input_file, output_file):
    """Convert PPTX to PDF using LibreOffice (cross-platform)"""
    # Check if LibreOffice is installed
    libreoffice_commands = ["libreoffice", "soffice"]
    libreoffice_path = None
    
    for cmd in libreoffice_commands:
        try:
            subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            libreoffice_path = cmd
            break
        except FileNotFoundError:
            continue
    
    if not libreoffice_path:
        print("Error: LibreOffice not found. Please install LibreOffice.")
        return False
    
    # Get absolute paths
    input_file_abs = os.path.abspath(input_file)
    output_dir = os.path.dirname(os.path.abspath(output_file))
    
    # Convert using LibreOffice
    try:
        subprocess.run([
            libreoffice_path,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            input_file_abs
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # LibreOffice creates the PDF with the same name as the input file
        # If the desired output name is different, rename the file
        default_output = os.path.join(output_dir, os.path.splitext(os.path.basename(input_file))[0] + ".pdf")
        if default_output != output_file:
            os.rename(default_output, output_file)
        
        print(f"Successfully converted {input_file} to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting file: {e}")
        return False


def process_folder(input_folder, output_folder=None):
    """Process all PPTX files in the input folder"""
    # Validate input folder
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder '{input_folder}' does not exist or is not a directory.")
        return False
    
    # If output folder is specified, create it if it doesn't exist
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Find all PPTX files in the input folder
    pptx_files = glob.glob(os.path.join(input_folder, "*.pptx"))
    
    if not pptx_files:
        print(f"No PPTX files found in '{input_folder}'.")
        return False
    
    print(f"Found {len(pptx_files)} PPTX files to convert.")
    
    # Process each file
    success_count = 0
    for pptx_file in pptx_files:
        # Determine output file path
        if output_folder:
            output_file = os.path.join(output_folder, os.path.splitext(os.path.basename(pptx_file))[0] + ".pdf")
        else:
            output_file = os.path.splitext(pptx_file)[0] + ".pdf"
        
        print(f"Converting: {pptx_file} -> {output_file}")
        
        # Convert based on platform
        system = platform.system()
        success = False
        
        if system == "Windows":
            try:
                success = convert_with_comtypes(pptx_file, output_file)
            except ImportError:
                print("Could not use Windows COM objects. Falling back to LibreOffice...")
                success = convert_with_libreoffice(pptx_file, output_file)
        else:
            success = convert_with_libreoffice(pptx_file, output_file)
        
        if success:
            success_count += 1
    
    print(f"Conversion complete: {success_count} of {len(pptx_files)} files converted successfully.")
    return success_count > 0


def main():
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python pptx-to-pdf.py <input_pptx_file> [output_pdf_file]")
        print("       python pptx-to-pdf.py --folder <input_folder> [output_folder]")
        sys.exit(1)
    
    # Check if folder mode is requested
    if sys.argv[1] == "--folder":
        if len(sys.argv) < 3:
            print("Error: Input folder not specified.")
            print("Usage: python pptx-to-pdf.py --folder <input_folder> [output_folder]")
            sys.exit(1)
        
        input_folder = sys.argv[2]
        output_folder = sys.argv[3] if len(sys.argv) >= 4 else None
        
        if process_folder(input_folder, output_folder):
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Single file mode
    input_file = sys.argv[1]
    
    # Validate input file
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        sys.exit(1)
    
    if not input_file.lower().endswith('.pptx'):
        print(f"Warning: Input file '{input_file}' does not have a .pptx extension.")
    
    # Determine output file
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Use the same name as input but with .pdf extension
        output_file = os.path.splitext(input_file)[0] + ".pdf"
    
    # Convert based on platform
    system = platform.system()
    success = False
    
    if system == "Windows":
        try:
            success = convert_with_comtypes(input_file, output_file)
        except ImportError:
            print("Could not use Windows COM objects. Falling back to LibreOffice...")
            success = convert_with_libreoffice(input_file, output_file)
    else:
        success = convert_with_libreoffice(input_file, output_file)
    
    if success:
        print(f"Conversion complete: {output_file}")
    else:
        print("Conversion failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
