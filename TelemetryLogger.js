"use strict";

const fs = require('fs');
const path = require('path');

const { mkdir } = fs.promises;

class TelemetryLogger {
  constructor(filePath, headers = []) {
    if (!filePath || typeof filePath !== 'string') {
      throw new Error('TelemetryLogger requires a file path');
    }

    this.filePath = filePath;
    this.headers = Array.isArray(headers) ? headers : [];
    this._stream = null;
    this._initialized = false;
    this._initPromise = null;
  }

  async _ensureStream() {
    if (this._initialized) return;
    if (this._initPromise) return this._initPromise;

    this._initPromise = (async () => {
      const dir = path.dirname(this.filePath);
      await mkdir(dir, { recursive: true });

      const shouldWriteHeader = this.headers.length > 0;

      this._stream = fs.createWriteStream(this.filePath, { flags: 'w' });

      if (shouldWriteHeader) {
        await this._writeLine(this.headers);
      }

      this._initialized = true;
    })();

    return this._initPromise;
  }

  async appendRow(values) {
    if (!Array.isArray(values)) {
      throw new Error('appendRow expects an array of values');
    }

    await this._ensureStream();
    return this._writeLine(values);
  }

  async _writeLine(values) {
    const serialized = values
      .map(TelemetryLogger._serializeValue)
      .join(',') + '\n';

    await new Promise((resolve, reject) => {
      this._stream.write(serialized, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  static _serializeValue(value) {
    if (value === undefined || value === null) return '';
    const str = String(value);
    if (str.includes('"') || str.includes(',') || str.includes('\n')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }
}

module.exports = { TelemetryLogger };
