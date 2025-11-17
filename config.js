"use strict";

require('dotenv').config();

const {
  SERIAL_PORT,
  SERIAL_BAUD_RATE,
  SERIAL_TIMEOUT,
  SERIAL_RECONNECT_INTERVAL,
  SERIAL_RECONNECT_ATTEMPTS,
  SERIAL_SEND_RETRY_INTERVAL,
} = process.env;

const serialConfig = {
  port: SERIAL_PORT,
  baudRate: parseInt(SERIAL_BAUD_RATE, 10) || 115200,
  portTimeout: parseInt(SERIAL_TIMEOUT, 10) || 2000,
  reconnectOnFailure: true,
  reconnectInterval: parseInt(SERIAL_RECONNECT_INTERVAL, 10) || 3000,
  reconnectAttempts: parseInt(SERIAL_RECONNECT_ATTEMPTS, 10) || 5,
  sendRetryInterval: parseInt(SERIAL_SEND_RETRY_INTERVAL, 10) || 500,
};

module.exports = { serialConfig };
