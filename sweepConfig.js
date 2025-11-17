"use strict";


const HOME_POSITION = 2047;

const SWEEP_POSITION_1_1 = 1747;
const SWEEP_POSITION_1_2 = 2247;
const SWEEP_POSITION_2_1 = 1847;
const SWEEP_POSITION_2_2 = 2347;

const motorSweepConfigs = [
  {
    index: 1,
    positions: [1947, HOME_POSITION, 2147, HOME_POSITION],
    intervalsMs: [1000, 5500, 1000, 5500],
    speed: 1000,
    accel: 20,
    startDelayMs: 0,
    logFile: DEFAULT_LOG_FILE
  },
  {
    index: 2,
    positions: [2147, HOME_POSITION, 1947, HOME_POSITION],
    intervalsMs: [1000, 5500, 1000, 5500],
    speed: 1000,
    accel: 20,
    startDelayMs: 0,
    logFile: DEFAULT_LOG_FILE
  },
  {
    index: 3,
    positions:   [SWEEP_POSITION_1_1, SWEEP_POSITION_1_2, SWEEP_POSITION_1_1, SWEEP_POSITION_1_2, SWEEP_POSITION_1_1, SWEEP_POSITION_1_2, SWEEP_POSITION_1_1],
    intervalsMs: [3500, 500,  4500, 500,  2500, 500,  1000],
    speed: 3000,
    accel: 120,
    startDelayMs: 0,
    logFile: DEFAULT_LOG_FILE
  },
  {
    index: 4,
    positions:   [SWEEP_POSITION_2_2, SWEEP_POSITION_2_1, SWEEP_POSITION_2_2, SWEEP_POSITION_2_1, SWEEP_POSITION_2_2, SWEEP_POSITION_2_1, SWEEP_POSITION_2_2],
    intervalsMs: [2000, 500,  2500, 500,  4500, 500,  2500],
    speed: 3000,
    accel: 120,
    startDelayMs: 0,
    logFile: DEFAULT_LOG_FILE
  }
];

module.exports = {
  HOME_POSITION,
  motorSweepConfigs
};
