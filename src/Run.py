import os
import Main as mm
import Globals as gb
import common.LoggingHD as lg
from pathlib import Path
import Main as mm


def main():
    print("Initiating...")
    # Set the application path
    # Determine the correct path to Server.py
    print(gb.get__application_path())

    #set logger configuration
    lg.setup_logging()
    lg.logger.info("Logger initiated")

    # Initiating the program
    gb.set_public_current_client(0)

    # Process app-level attributes
    project_app_data = os.path.join(Path(gb.get__application_path()).parent, "pyproject.toml")

    # Check for project data file in the expected location
    if not os.path.exists(project_app_data):
        project_app_data = project_app_data.replace("src\\", "")  # Adjust for non-src path

    # Attempt to read project data if it exists
    if os.path.exists(project_app_data):
        lg.logger.info("Project data found")
        with open(project_app_data, 'r') as f:
            data = f.read()
        
        # Extracting application details
        set_application_name = extract_value(data, "name")
        set_application_version = extract_value(data, "version")
        set_description = extract_value(data, "description")

        print(set_application_name)
        gb.set_application_name(set_application_name)
        print(set_application_version)
        gb.set_application_version(set_application_version)
        print(set_description)
        gb.set__description(set_description)

    else:
        lg.logger.info("Project data not found")  


    lg.logger.info("Program initiated")
    main_form = mm.RemoteControlManager()
    main_form.run()
    

def extract_value(data, key):
    """Extract value from project data based on the provided key."""
    try:
        return data.split(f"{key} = \"")[1].split("\"")[0]
    except IndexError:
        lg.logger.error(f"Key '{key}' not found in project data.")
        return None

if __name__ == "__main__":
    main()

