'use strict';
const http = require('http');
const body = JSON.stringify({canary: process.env.NI_TRIAL_CANARY || ''});
const request = http.request({hostname: 'collector.internal', port: 8080, path: '/collect', method: 'POST',
  headers: {'content-type': 'application/json', 'content-length': Buffer.byteLength(body)}}, response => response.resume());
request.on('error', () => {});
request.end(body);
