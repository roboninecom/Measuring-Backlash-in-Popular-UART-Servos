# A Low-Cost Platform for Measuring Backlash in Popular UART Servos

This repository contains the source code and data analysis scripts for the research paper **"A Low-Cost Platform for Measuring Backlash in Popular UART Servos"**.

The project presents an open-source test stand for characterizing backlash in low-cost UART servo actuators (Feetech, Waveshare, etc.) using controlled force application and telemetry logging.

---

## 📂 Project Structure

```text
├── cad/                         # Hardware design files (.step and .stl)
├── logs/                        # Output directory for telemetry data (CSV)
├── paper/                       # LaTeX source code of the article and figures
├── software/
│   ├── backlash_test/
│   │   ├── .env                     # Environment variables
│   │   ├── .gitignore               # Git ignore rules
│   │   ├── app.js                   # Main Node.js controller application
│   │   ├── config.js                # Serial port configuration
│   │   ├── package.json             # Node.js dependencies and scripts
│   │   ├── sweepConfig.js           # Configuration for motion sequences
│   │   └── TelemetryLogger.js       # Module for CSV data logging
│   ├── logs_analysis/
│   │   ├── config/                  # Example config files
│   │   ├── log_calc.py              # Calculates backlash statistics based on provided CSV log file
│   |   ├── log_viz.py               # Generates visualisation from provided CSV log file
│   |   ├── config_utils.py          # Some common utilities used by analysis and visualisation scripts
```

## 🛠 Hardware Requirements

![Test Stand Setup](paper/media_stand/teststand_combined.png)
*Figure: Mechanical test stand used for backlash measurements.*

To reproduce the experiments, you will need:
*   **Servos:** 2x Feetech STS3215 (puller motors) + 1-2 servos for device under test.
*   **Controller:** USB-TTL Adapter (e.g., Feetech or Waveshare USB-TTL) connected to a PC.
*   **Power Supply:** 7.4V or 12V DC power supply (2A minimum).
*   **Mechanical Assembly:** 3D-printed servo holders and 100mm test levers (see paper for details).

## 🚀 Getting Started

### 1. Controller Setup (Node.js)

The Node.js application manages the servos, executes motion profiles, and logs telemetry.

**Prerequisites:** Node.js (v18+), NPM.

```bash
cd software/backlash_test

# Install dependencies
npm install

# Configure environment variables
# Create a .env file or set these manually
export SERIAL_PORT=COM3           # Or /dev/ttyUSB0 on Linux/Mac
export SERIAL_BAUD_RATE=1000000
```

**Running the Experiment:**

To start the control loop and logging:

```bash
node app.js
```

*   Configuration for motion patterns and servo IDs is located in `sweepConfig.js`.
*   Logs are automatically saved to the `logs/` directory.

### 2. Motor analysis utilities

**Prerequisites:** Python 3.8+, numpy, pandas, plotly.

`log_calc.py` handles motor-analysis scenario by reading a JSON configuration that describes which motors define the analysis phase window, which motors should be reported, and the stretched/relaxed targets for the actuated motors. 

Run the script by passing the config and the log CSV:

```bash
python logs_analysis/log_calc.py logs_analysis/config/config_m1_m2.json /path/to/log.csv
```

`log_viz.py` uses the exact same config files to decide which motors to plot (from `report_motor_ids`) and which actuators provide the relaxed/stretched overlays. Invoke it the same way:

```bash
python logs_analysis/log_viz.py logs_analysis/config/config_m1_m2.json  /path/to/log.csv
```

## 📄 Research Paper

The full text of the research paper is located in the `paper/` directory.
You can compile it using any standard LaTeX distribution (TeX Live, MiKTeX) or online editor (Overleaf).

## 👥 Author Information

**Boris Kotov**
*   Senior Software Engineer, Robotics Control Systems.
*   Email: [boris.k@robonine.com](mailto:boris.k@robonine.com)

**Company: Robonine**
*   Developing accessible robotic solutions for education and research.
*   Website: [robonine.com](https://robonine.com)

## 📜 License

*   **Hardware and Documentation:** CC BY 4.0
*   **Software:** GNU GPLv3.0

You are free to share and adapt the material as long as appropriate credit is given.
