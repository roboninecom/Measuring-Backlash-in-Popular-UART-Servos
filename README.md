# Backlash Test

Small Node.js utility that sweeps a set of STS servos and logs position/current/temperature telemetry to `logs/motor_telemetry.csv`.

## Setup
- Install dependencies from this directory: `npm install`.
- Create a `.env` file (or export env vars) with serial connection options: `SERIAL_PORT`, `SERIAL_BAUD_RATE`, `SERIAL_TIMEOUT`, `SERIAL_RECONNECT_INTERVAL`, `SERIAL_RECONNECT_ATTEMPTS`, `SERIAL_SEND_RETRY_INTERVAL`.

## Usage
- Start the sweeps and telemetry logging with `node app.js`.
- Motor sweep behavior (IDs, positions, intervals) and logging cadence are configured in `sweepConfig.js`.
- Recorded CSV logs will appear under `logs/`.
