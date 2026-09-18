import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'https://localhost:8443';
const REQUESTS_PER_SECOND = Number(__ENV.RPS || 50000);
const DURATION = __ENV.DURATION || '2m';

export const options = {
  scenarios: {
    ingest: {
      executor: 'constant-arrival-rate',
      rate: REQUESTS_PER_SECOND,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 4000,
      maxVUs: 25000,
    },
  },
  thresholds: {
    http_req_duration: ['p(99) < 5'],
    http_req_failed: ['rate < 0.01'],
  },
  tlsAuth: [
    {
      domains: [new URL(BASE_URL).hostname],
      cert: open(__ENV.CLIENT_CERT || './certs/client.crt'),
      key: open(__ENV.CLIENT_KEY || './certs/client.key'),
    },
  ],
};

export default function () {
  const payload = JSON.stringify({
    tenant_id: `tenant-${__VU % 64}`,
    sequence: __VU * 1000000 + __ITER,
    timestamp: new Date().toISOString(),
    source: 'document-pipeline',
    event_type: 'document.ingested',
    payload: {
      document_id: `doc-${__VU}-${__ITER}`,
      actor: 'ingest-worker',
      status: 'accepted',
    },
  });

  const res = http.post(`${BASE_URL}/v1/audit-events`, payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-Trace-ID': `trace-${__VU}-${__ITER}`,
    },
    timeout: '1500ms',
  });

  check(res, {
    'accepted': (r) => r.status === 202 || r.status === 503,
    'latency_under_threshold': (r) => r.timings.duration < 5,
  });
}
