import {
  ApiResponse,
  RequestResult,
  SystemSettings,
  SystemStatus,
  normalizeApiResponse,
  normalizeSettings,
  normalizeStatus,
} from '../types/models';

const JSON_HEADERS = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
};

type HeaderBag = Headers & {
  getSetCookie?: () => string[];
  map?: Record<string, string | string[]> | (() => Record<string, string | string[]>);
};

type ReactNativeWebSocketConstructor = new (
  url: string,
  protocols?: string | string[],
  options?: { headers?: Record<string, string> },
) => WebSocket;

export function normalizeServerUrl(url: string) {
  const trimmed = url.trim().replace(/\/+$/, '');
  if (!trimmed) {
    return '';
  }
  if (!/^https?:\/\//i.test(trimmed)) {
    return `http://${trimmed}`;
  }
  return trimmed;
}

function withTimeout<T>(promise: Promise<T>, timeoutMs = 10000) {
  return Promise.race<T>([
    promise,
    new Promise<T>((_, reject) => {
      setTimeout(() => reject(new Error('Hết thời gian chờ phản hồi')), timeoutMs);
    }),
  ]);
}

function getHeader(headers: Headers, name: string) {
  const key = name.toLowerCase();

  try {
    const directValue = headers.get(name) ?? headers.get(key);
    if (directValue) {
      return directValue;
    }
  } catch {
    // Continue to React Native-specific fallbacks.
  }

  const headerBag = headers as HeaderBag;
  if (key === 'set-cookie' && typeof headerBag.getSetCookie === 'function') {
    const cookies = headerBag.getSetCookie().filter(Boolean);
    if (cookies.length > 0) {
      return cookies.join('; ');
    }
  }

  const rawMap = typeof headerBag.map === 'function' ? headerBag.map() : headerBag.map;
  if (!rawMap) {
    return null;
  }

  const mappedValue = rawMap[key] ?? rawMap[name];
  if (Array.isArray(mappedValue)) {
    return mappedValue[0] ?? null;
  }

  return typeof mappedValue === 'string' ? mappedValue : null;
}

function extractSessionCookie(rawCookie: string | null) {
  if (!rawCookie || !rawCookie.includes('session=')) {
    return null;
  }

  const match = /session=([^;]+)/.exec(rawCookie);
  return match?.[1] ?? null;
}

function formEncode(payload: Record<string, string>) {
  return Object.entries(payload)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&');
}

function encodeBase64(value: string) {
  const bytes = Array.from(
    encodeURIComponent(value).replace(/%([0-9A-F]{2})/g, (_, hex: string) =>
      String.fromCharCode(parseInt(hex, 16)),
    ),
  ).map((char) => char.charCodeAt(0));

  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
  let output = '';

  for (let index = 0; index < bytes.length; index += 3) {
    const chunk =
      ((bytes[index] ?? 0) << 16) |
      ((bytes[index + 1] ?? 0) << 8) |
      (bytes[index + 2] ?? 0);

    output += alphabet[(chunk >> 18) & 63];
    output += alphabet[(chunk >> 12) & 63];
    output += index + 1 < bytes.length ? alphabet[(chunk >> 6) & 63] : '=';
    output += index + 2 < bytes.length ? alphabet[chunk & 63] : '=';
  }

  return output;
}

function bytesToBase64(bytes: Uint8Array) {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
  let output = '';

  for (let index = 0; index < bytes.length; index += 3) {
    const chunk =
      ((bytes[index] ?? 0) << 16) |
      ((bytes[index + 1] ?? 0) << 8) |
      (bytes[index + 2] ?? 0);

    output += alphabet[(chunk >> 18) & 63];
    output += alphabet[(chunk >> 12) & 63];
    output += index + 1 < bytes.length ? alphabet[(chunk >> 6) & 63] : '=';
    output += index + 2 < bytes.length ? alphabet[chunk & 63] : '=';
  }

  return output;
}

function requestFailure<T>(response: RequestResult<unknown>): RequestResult<T> {
  return {
    ok: false,
    error: response.error,
    status: response.status,
    unauthorized: response.unauthorized,
  };
}

export class ApiService {
  private baseUrl: string;
  private sessionCookie: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = normalizeServerUrl(baseUrl);
  }

  setBaseUrl(url: string) {
    this.baseUrl = normalizeServerUrl(url);
  }

  getBaseUrl() {
    return this.baseUrl;
  }

  setSession(sessionCookie: string | null) {
    this.sessionCookie = sessionCookie;
  }

  getSession() {
    return this.sessionCookie;
  }

  get isAuthenticated() {
    return Boolean(this.sessionCookie);
  }

  getAuthHeaders(extraHeaders?: Record<string, string>) {
    const headers: Record<string, string> = { ...(extraHeaders ?? {}) };
    if (!this.sessionCookie) {
      return headers;
    }

    if (this.sessionCookie.startsWith('__basic__:')) {
      headers.Authorization = `Basic ${this.sessionCookie.slice(10)}`;
      return headers;
    }

    headers.Cookie = `session=${this.sessionCookie}`;
    return headers;
  }

  private async requestJson<T>(
    path: string,
    options: RequestInit = {},
    timeoutMs = 10000,
  ): Promise<RequestResult<T>> {
    try {
      const response = await withTimeout(
        fetch(`${this.baseUrl}${path}`, {
          ...options,
          headers: this.getAuthHeaders(options.headers as Record<string, string> | undefined),
        }),
        timeoutMs,
      );

      if (response.status === 401) {
        this.sessionCookie = null;
        return { ok: false, unauthorized: true, status: 401, error: 'Chưa xác thực' };
      }

      const raw = await response.text();
      const payload = raw ? (JSON.parse(raw) as T) : undefined;

      if (!response.ok) {
        return {
          ok: false,
          error: `HTTP ${response.status}`,
          status: response.status,
          data: payload,
        };
      }

      return { ok: true, data: payload, status: response.status };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : 'Lỗi kết nối mạng',
      };
    }
  }

  async login(username: string, password: string): Promise<RequestResult<{ session: string }>> {
    const formBody = formEncode({
      username: username.trim(),
      password,
    });

    try {
      const response = await withTimeout(
        fetch(`${this.baseUrl}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'text/html',
          },
          body: formBody,
          redirect: 'manual',
        }),
        10000,
      );

      const setCookie = getHeader(response.headers, 'set-cookie');
      const sessionCookie = extractSessionCookie(setCookie);
      if (sessionCookie) {
        this.sessionCookie = sessionCookie;
        return { ok: true, data: { session: sessionCookie }, status: response.status };
      }
    } catch {
      // Ignore and continue to the fallback path.
    }

    try {
      const response = await withTimeout(
        fetch(`${this.baseUrl}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            Accept: 'text/html',
          },
          body: formBody,
        }),
        10000,
      );

      const setCookie = getHeader(response.headers, 'set-cookie');
      const sessionCookie = extractSessionCookie(setCookie);
      if (sessionCookie) {
        this.sessionCookie = sessionCookie;
        return { ok: true, data: { session: sessionCookie }, status: response.status };
      }
    } catch {
      // Ignore and continue to Basic auth fallback.
    }

    const basicAuth = encodeBase64(`${username}:${password}`);
    try {
      const probe = await withTimeout(
        fetch(`${this.baseUrl}/api/status`, {
          headers: {
            Authorization: `Basic ${basicAuth}`,
          },
        }),
        10000,
      );

      if (probe.ok) {
        const session = `__basic__:${basicAuth}`;
        this.sessionCookie = session;
        return { ok: true, data: { session }, status: probe.status };
      }
    } catch {
      // Ignore. Final error will be returned below.
    }

    return { ok: false, error: 'Sai tài khoản hoặc mật khẩu' };
  }

  async register(username: string, password: string, fullname = '') {
    const response = await this.requestJson<Record<string, unknown>>(
      '/api/register',
      {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify({
          username,
          password,
          fullname,
        }),
      },
      10000,
    );

    if (!response.ok || !response.data) {
      return {
        success: false,
        message: response.error ?? 'Đăng ký thất bại',
      } satisfies ApiResponse;
    }

    return normalizeApiResponse(response.data);
  }

  async getStatus() {
    const response = await this.requestJson<Record<string, unknown>>('/api/status', {}, 8000);
    if (!response.ok || !response.data) {
      return requestFailure<SystemStatus>(response);
    }
    return { ok: true, data: normalizeStatus(response.data), status: response.status };
  }

  async getSettings() {
    const response = await this.requestJson<Record<string, unknown>>('/api/settings', {}, 8000);
    if (!response.ok || !response.data) {
      return requestFailure<SystemSettings>(response);
    }
    return { ok: true, data: normalizeSettings(response.data), status: response.status };
  }

  async postSettings(payload: { cameraId?: number; plcIp?: string; dirtThreshold?: number }) {
    const body: Record<string, unknown> = {};
    if (payload.cameraId !== undefined) {
      body.CAMERA_ID = payload.cameraId;
    }
    if (payload.plcIp !== undefined) {
      body.PLC_IP = payload.plcIp;
    }
    if (payload.dirtThreshold !== undefined) {
      body.DIRT_THRESHOLD = payload.dirtThreshold;
    }
    return this.postApiResponse('/api/settings', body);
  }

  async setSnapshotInterval(seconds: number) {
    return this.postApiResponse('/api/snapshot_interval', { interval: seconds });
  }

  async plcReconnect(plcIp: string) {
    return this.postApiResponse('/api/plc/reconnect', { PLC_IP: plcIp });
  }

  async manualClean() {
    return this.postApiResponse('/api/plc/manual_clean', {});
  }

  async systemStart() {
    return this.postApiResponse('/api/system/start', {});
  }

  async systemStop() {
    return this.postApiResponse('/api/system/stop', {});
  }

  async setDirtThreshold(threshold: number) {
    return this.postApiResponse('/api/settings', { DIRT_THRESHOLD: threshold });
  }

  private async fetchImageDataUri(path: string, timeoutMs = 12000) {
    const response = await withTimeout(
      fetch(`${this.baseUrl}${path}`, {
        headers: this.getAuthHeaders(),
      }),
      timeoutMs,
    );

    if (response.status === 401) {
      this.sessionCookie = null;
      throw new Error('Chưa xác thực');
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const contentType = getHeader(response.headers, 'content-type') ?? 'image/jpeg';
    const buffer = await response.arrayBuffer();
    const base64 = bytesToBase64(new Uint8Array(buffer));
    return `data:${contentType};base64,${base64}`;
  }

  private async postApiResponse(path: string, body: Record<string, unknown>) {
    const response = await this.requestJson<Record<string, unknown>>(
      path,
      {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify(body),
      },
      10000,
    );

    if (!response.ok || !response.data) {
      return {
        success: false,
        message: response.error ?? 'Yêu cầu thất bại',
      } satisfies ApiResponse;
    }

    return normalizeApiResponse(response.data);
  }

  connectWebSocket(
    onMessage: (status: SystemStatus) => void,
    onStateChange?: (connected: boolean) => void,
  ) {
    if (!this.sessionCookie) {
      return () => undefined;
    }

    try {
      const uri = new URL(this.baseUrl);
      const scheme = uri.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${scheme}//${uri.host}/ws`;
      const headers = this.getAuthHeaders();
      const ReactNativeWebSocket = WebSocket as unknown as ReactNativeWebSocketConstructor;
      const socket = new ReactNativeWebSocket(wsUrl, [], { headers });

      socket.onopen = () => onStateChange?.(true);
      socket.onmessage = (event) => {
        if (typeof event.data !== 'string') {
          return;
        }

        try {
          onMessage(normalizeStatus(JSON.parse(event.data) as Record<string, unknown>));
        } catch {
          // Ignore malformed payloads.
        }
      };
      socket.onerror = () => onStateChange?.(false);
      socket.onclose = () => onStateChange?.(false);

      return () => {
        try {
          socket.close();
        } catch {
          // Ignore close errors.
        }
      };
    } catch {
      onStateChange?.(false);
      return () => undefined;
    }
  }

  buildCurrentFrameSource(cacheKey: number) {
    return {
      uri: `${this.baseUrl}/api/current_frame?ts=${cacheKey}`,
      headers: this.getAuthHeaders(),
    };
  }

  buildVideoFeedSource() {
    return {
      uri: `${this.baseUrl}/video_feed`,
      headers: this.getAuthHeaders(),
    };
  }

  async fetchCurrentFrameDataUri(cacheKey: number) {
    return this.fetchImageDataUri(`/api/current_frame?ts=${cacheKey}`);
  }

  async fetchCnnPatchFrameDataUri(cacheKey: string | number = 0) {
    return this.fetchImageDataUri(
      `/api/cnn_patch_frame?ts=${encodeURIComponent(String(cacheKey))}`,
    );
  }

  async fetchYoloPanelFrameDataUri(cacheKey: string | number = 0) {
    return this.fetchImageDataUri(
      `/api/yolo_panel_frame?ts=${encodeURIComponent(String(cacheKey))}`,
    );
  }

  async fetchSnapshotDataUri(filename: string, cacheKey: string | number = 0) {
    return this.fetchImageDataUri(
      `/snapshots/${encodeURIComponent(filename)}?ts=${encodeURIComponent(String(cacheKey))}`,
    );
  }

  buildSnapshotSource(filename: string, cacheKey: string | number = 0) {
    return {
      uri: `${this.baseUrl}/snapshots/${encodeURIComponent(filename)}?ts=${encodeURIComponent(String(cacheKey))}`,
      headers: this.getAuthHeaders(),
    };
  }

  async getPowerData() {
    return this.requestJson<Record<string, unknown>>('/api/power', {}, 6000);
  }

  async getPowerHistory(hours = 1) {
    return this.requestJson<Record<string, unknown>>(`/api/power/history?hours=${hours}`, {}, 8000);
  }

  async getPowerHourly() {
    return this.requestJson<Record<string, unknown>>('/api/power/hourly', {}, 8000);
  }

  async getPowerDaily(days = 7) {
    return this.requestJson<Record<string, unknown>>(`/api/power/daily?days=${days}`, {}, 8000);
  }

  async getPowerMonthly() {
    return this.requestJson<Record<string, unknown>>('/api/power/monthly', {}, 8000);
  }

  async getCleaningEfficiency(limit = 20) {
    return this.requestJson<Record<string, unknown>>(`/api/cleaning/efficiency?limit=${limit}`, {}, 8000);
  }
}
