"use strict";

const path = require('path')
const { StsInstruction, StsRegisterSchemaKeys, StsManager, StsMotor } = require('StsServo');

const { serialConfig } = require('./config')
const { TelemetryLogger } = require('./TelemetryLogger');
const { motorSweepConfigs } = require('./sweepConfig');

const DEFAULT_LOG_FILE = path.join(__dirname, 'logs', 'motor_telemetry.csv');
const LOGGING_INTERVAL_MS = 100;

const {
  CURRENT_POSITION,
  CURRENT_SPEED,
  CURRENT_LOAD,
  CURRENT_CURRENT,
  CURRENT_TEMPERATURE,
  SERVO_STATUS,
  MOVING_STATUS
} = StsRegisterSchemaKeys;

const motors = [];
const motorsById = new Map();
let sweepStarted = false;
const motorStates = new Map();
const loggingGroups = new Map();
let telemetryLogTimer = null;


function resolveLogPath(logPath) {
  if (!logPath) return null;
  return path.isAbsolute(logPath) ? logPath : path.join(__dirname, logPath);
}

function buildHeaders(motorIds) {
  const headers = ['timestamp'];
  for (const id of motorIds) {
    headers.push(
      `target pos (${id})`,
      `pos (${id})`,
      `speed (${id})`,
      `load (${id})`,
      `current (${id})`,
      `temp (${id})`,
      `status (${id})`,
      `moving (${id})`
    );
  }
  return headers;
}

function registerLoggingTarget(motorId, logFile) {
  if (!motorId || !logFile) return;

  let group = loggingGroups.get(logFile);
  if (!group) {
    group = { motorIds: [], logger: null };
    loggingGroups.set(logFile, group);
  }

  if (!group.motorIds.includes(motorId)) {
    group.motorIds.push(motorId);
  }
}

function initializeLoggingGroups() {
  loggingGroups.forEach((group, filePath) => {
    if (!group.logger) {
      const headers = buildHeaders(group.motorIds);
      group.logger = new TelemetryLogger(filePath, headers);
    }
  });
}

function startTelemetryLogging() {
  if (telemetryLogTimer || loggingGroups.size === 0) return;

  const intervalMs = LOGGING_INTERVAL_MS || 500;

  telemetryLogTimer = setInterval(() => {
    loggingGroups.forEach((group, filePath) => {
      if (!group.logger || group.motorIds.length === 0) return;

      const timestamp = new Date().toISOString();

      const row = [timestamp];
      let hasData = false;

      for (const motorId of group.motorIds) {
        const state = motorStates.get(motorId);
        const motor = motorsById.get(motorId);
        const telemetry = motor?.lastTelemetry ?? {};
        const targetPosition = state?.lastCommanded ?? null;

        row.push(
          targetPosition ?? '',
          telemetry?.[CURRENT_POSITION] ?? '',
          telemetry?.[CURRENT_SPEED] ?? '',
          telemetry?.[CURRENT_LOAD] ?? '',
          telemetry?.[CURRENT_CURRENT] ?? '',
          telemetry?.[CURRENT_TEMPERATURE] ?? '',
          telemetry?.[SERVO_STATUS] ?? '',
          telemetry?.[MOVING_STATUS] ?? ''
        );

        if (
          targetPosition != null ||
          telemetry?.[CURRENT_POSITION] != null ||
          telemetry?.[CURRENT_SPEED] != null ||
          telemetry?.[CURRENT_LOAD] != null ||
          telemetry?.[CURRENT_CURRENT] != null ||
          telemetry?.[CURRENT_TEMPERATURE] != null ||
          telemetry?.[SERVO_STATUS] != null ||
          telemetry?.[MOVING_STATUS] != null
        ) {
          hasData = true;
        }
      }

      if (hasData) {
        group.logger.appendRow(row).catch((err) => {
          console.error(`Telemetry log write failed (${filePath}):`, err);
        });
      }
    });
  }, intervalMs);
}

function startSweepTest(stsManager) {
  if (motors.length < motorSweepConfigs.length) {
    console.warn(`Expected ${motorSweepConfigs.length} motors, got ${motors.length}. Sweep test skipped.`);
    return;
  }

  const missingIds = motorSweepConfigs
    .map(cfg => cfg.index)
    .filter(id => !motorsById.has(id));

  if (missingIds.length) {
    console.warn(`Missing motors for IDs: ${missingIds.join(', ')}. Sweep test skipped.`);
    return;
  }

  sweepStarted = true;
  console.log('Starting motor sweep test');

  motorSweepConfigs.forEach((cfg) => {
    const motor = motorsById.get(cfg.index);
    if (!motor) return;
    if (!Array.isArray(cfg.positions) || cfg.positions.length === 0) {
      console.warn(`No positions configured for motor ${cfg.index}. Sweep skipped.`);
      return;
    }

    const resolvedLogPath = resolveLogPath(DEFAULT_LOG_FILE);
    const targetIds = [cfg.index];
    let positionIndex = 0;
    let initialized = false;

    const state = motorStates.get(cfg.index) ?? {
      config: cfg,
      logFile: resolvedLogPath,
      lastCommanded: null,
      lastCommandedAt: null,
      timer: null
    };

    state.logFile = resolvedLogPath;
    motorStates.set(cfg.index, state);
    registerLoggingTarget(cfg.index, state.logFile);

    const sanitizeInterval = (value) => {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
    };

    const fallbackIntervalMs =
      sanitizeInterval(
        Array.isArray(cfg.intervalsMs) && cfg.intervalsMs.length ? cfg.intervalsMs[0] : cfg.intervalMs
      ) ?? 1000;

    const getIntervalForIndex = (index) => {
      const intervals = Array.isArray(cfg.intervalsMs) ? cfg.intervalsMs : null;
      if (intervals?.length) {
        const candidate = sanitizeInterval(intervals[index % intervals.length]);
        if (candidate != null) {
          return candidate;
        }
      }
      return fallbackIntervalMs;
    };

    const scheduleNextMove = (delayMs = fallbackIntervalMs) => {
      if (state.timer) {
        clearTimeout(state.timer);
        state.timer = null;
      }
      const safeDelay = sanitizeInterval(delayMs) ?? fallbackIntervalMs;
      state.timer = setTimeout(() => {
        void writePosition();
      }, safeDelay);
    };

    const writePosition = async () => {
      const currentIndex = positionIndex;
      const targetPosition = cfg.positions[currentIndex];
      const dwellMs = getIntervalForIndex(currentIndex);
      positionIndex = (positionIndex + 1) % cfg.positions.length;

      const payload = initialized
        ? {
            [StsRegisterSchemaKeys.TARGET_POSITION]: targetPosition
          }
        : {
            [StsRegisterSchemaKeys.TORQUE_SWITCH]: 1,
            [StsRegisterSchemaKeys.RUNNING_SPEED]: cfg.speed,
            [StsRegisterSchemaKeys.ACCELERATION]: cfg.accel,
            [StsRegisterSchemaKeys.TARGET_POSITION]: targetPosition
          };

      try {
        await stsManager.Write(payload, targetIds);
        initialized = true;
        state.lastCommanded = targetPosition;
        state.lastCommandedAt = Date.now();
      } catch (err) {
        console.error(`Failed to update motor ${cfg.index}:`, err);
      } finally {
        scheduleNextMove(dwellMs);
      }
    };

    scheduleNextMove(cfg.startDelayMs ?? 0);
  });

  initializeLoggingGroups();
  startTelemetryLogging(stsManager);
}

async function init() {
  try {
    const sts = new StsInstruction(serialConfig);
    sts.on('error', (err) => console.error(err));

    const stsManager = StsManager.getInstance(sts);
    stsManager.on('error', (err) => console.error('StsManager error:', err));
    stsManager.on('discovery', (ids) => {
      console.log(`Servos found: ${ids}`);
      for (const id of ids) {
        if (!motorsById.has(id)) {
          const motor = new StsMotor(id);
          motors.push(motor);
          motorsById.set(id, motor);
        }
      }
      const allConfiguredMotorsPresent = motorSweepConfigs.every(cfg => motorsById.has(cfg.index));
      if (!sweepStarted && allConfiguredMotorsPresent) {
        startSweepTest(stsManager);
      }
    });
    
    await sts.ConnectFailsafe();
    
  } catch (err) {
    console.error("Initialization failed:", err);
  }
}

init().catch(console.error);
