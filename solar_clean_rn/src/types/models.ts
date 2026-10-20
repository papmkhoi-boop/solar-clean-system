export interface SystemStatus {
  pDirty: number;
  areaRatio: number;
  predictedClass: number;
  labelName: string;
  predProbs: number[];
  classNames: string[];
  modelPipeline: string;
  status: string;
  statusColor: string;
  timestamp: number;
  fps: number;
  cleanCount: number;
  plcConnected: boolean;
  plcStatus: string;
  confidence: number;
  lastSnapshotPath: string | null;
  lastSnapshotTime: string | null;
  nextSnapshot: number;
  snapshotInterval: number;
  dirtThreshold: number;
  cameraId: number;
  isRunning: boolean;
  minConfidence: number;
  plcIp: string;
  cnnActive: boolean;
  panelDetected: boolean;
  yoloCleanFaults: string[];
  yoloCrackFaults: string[];
}

export interface SystemSettings {
  cameraId: number;
  plcIp: string;
  dirtThreshold: number;
  snapshotInterval: number;
  triggerClass: string;
  minConfidence: number;
  isRunning: boolean;
}

export interface ApiResponse {
  success: boolean;
  message: string;
}

export interface RequestResult<T> {
  ok: boolean;
  data?: T;
  error?: string;
  status?: number;
  unauthorized?: boolean;
}

export const defaultStatus: SystemStatus = {
  pDirty: 0,
  areaRatio: 0,
  predictedClass: 0,
  labelName: 'Chưa xác định',
  predProbs: [0, 0],
  classNames: ['sach', 'ban'],
  modelPipeline: 'CNN 2-class + YOLO/Panel-Seg auxiliaries',
  status: 'Đang kết nối...',
  statusColor: 'warning',
  timestamp: 0,
  fps: 0,
  cleanCount: 0,
  plcConnected: false,
  plcStatus: 'Chưa kết nối',
  confidence: 0,
  lastSnapshotPath: null,
  lastSnapshotTime: null,
  nextSnapshot: 0,
  snapshotInterval: 600,
  dirtThreshold: 0,
  cameraId: 0,
  isRunning: false,
  minConfidence: 0.6,
  plcIp: '192.168.1.1',
  cnnActive: false,
  panelDetected: false,
  yoloCleanFaults: [],
  yoloCrackFaults: [],
};

export const defaultSettings: SystemSettings = {
  cameraId: 0,
  plcIp: '192.168.1.1',
  dirtThreshold: 0,
  snapshotInterval: 600,
  triggerClass: 'ban',
  minConfidence: 0.6,
  isRunning: false,
};

function simplifyText(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9\s]/g, ' ')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function translateLabelName(value: unknown) {
  const raw = String(value ?? '').trim();
  const normalized = simplifyText(raw);

  if (!raw || normalized === 'unknown') {
    return 'Chưa xác định';
  }
  if (normalized.includes('nopanel') || normalized.includes('no panel')) {
    return 'CNN bỏ qua';
  }
  if (normalized === 'sach' || normalized.includes('clean')) {
    return 'Sạch';
  }
  if (normalized === 'ban' || normalized.includes('dirty')) {
    return 'Bẩn';
  }

  return raw;
}

function translateStatusText(value: unknown) {
  const raw = String(value ?? '').trim();
  const normalized = simplifyText(raw);

  if (!raw || normalized === 'unknown') {
    return 'Chưa xác định';
  }
  if (normalized.includes('can ve sinh') || normalized.includes('need clean')) {
    return 'Cần vệ sinh';
  }
  if (normalized.includes('no panel')) {
    return 'Panel-Seg: không thấy tấm pin';
  }
  if (normalized.includes('nut vo') || normalized.includes('crack')) {
    return 'Cảnh báo nứt vỡ';
  }
  if (normalized.includes('sach') || normalized.includes('clean')) {
    return 'Sạch';
  }

  return raw;
}

function translatePlcStatus(value: unknown, plcConnected: boolean, plcIp: string) {
  const raw = String(value ?? '').trim();
  const normalized = simplifyText(raw);

  if (plcConnected) {
    if (!raw || normalized === 'connected' || normalized === 'connected to') {
      return `Đã kết nối ${plcIp}`;
    }
    if (normalized.startsWith('connected to ')) {
      return `Đã kết nối ${raw.slice('Connected to '.length).trim()}`;
    }
    return raw;
  }

  if (!raw || normalized === 'not connected' || normalized === 'disconnected') {
    return 'Chưa kết nối';
  }

  return raw;
}

export function normalizeStatus(payload: Record<string, unknown>): SystemStatus {
  const plcConnected = Boolean(payload.plc_connected ?? false);
  const plcIp = String(payload.plc_ip ?? '192.168.1.1');
  const rawPredProbs = Array.isArray(payload.pred_probs)
    ? payload.pred_probs.map((value) => Number(value ?? 0)).slice(0, 2)
    : [0, 0];
  const predProbs = rawPredProbs.length === 1 ? [rawPredProbs[0], 0] : rawPredProbs;

  return {
    pDirty: Number(payload.p_dirty ?? 0),
    areaRatio: Number(payload.area_ratio ?? 0),
    predictedClass: Number(payload.predicted_class ?? 0),
    labelName: translateLabelName(payload.label_name),
    predProbs,
    classNames: Array.isArray(payload.class_names)
      ? payload.class_names.map((value) => String(value ?? '')).slice(0, 2)
      : ['sach', 'ban'],
    modelPipeline: String(payload.model_pipeline ?? 'CNN 2-class + YOLO/Panel-Seg auxiliaries'),
    status: translateStatusText(payload.status),
    statusColor: String(payload.status_color ?? 'warning'),
    timestamp: Number(payload.timestamp ?? 0),
    fps: Number(payload.fps ?? 0),
    cleanCount: Number(payload.clean_count ?? 0),
    plcConnected,
    plcStatus: translatePlcStatus(payload.plc_status, plcConnected, plcIp),
    confidence: Number(payload.confidence ?? 0),
    lastSnapshotPath:
      typeof payload.last_snapshot_path === 'string' ? payload.last_snapshot_path : null,
    lastSnapshotTime:
      typeof payload.last_snapshot_time === 'string' ? payload.last_snapshot_time : null,
    nextSnapshot: Number(payload.next_snapshot ?? 0),
    snapshotInterval: Number(payload.snapshot_interval ?? 600),
    dirtThreshold: Number(payload.dirt_threshold ?? 0),
    cameraId: Number(payload.camera_id ?? 0),
    isRunning: Boolean(payload.is_running ?? false),
    minConfidence: Number(payload.min_confidence ?? 0.6),
    plcIp,
    cnnActive: Boolean(payload.cnn_active ?? true),
    panelDetected: Boolean(payload.panel_detected ?? false),
    yoloCleanFaults: Array.isArray(payload.yolo_clean_faults)
      ? payload.yolo_clean_faults.map((value) => String(value ?? ''))
      : [],
    yoloCrackFaults: Array.isArray(payload.yolo_crack_faults)
      ? payload.yolo_crack_faults.map((value) => String(value ?? ''))
      : [],
  };
}

export function normalizeSettings(payload: Record<string, unknown>): SystemSettings {
  return {
    cameraId: Number(payload.CAMERA_ID ?? 0),
    plcIp: String(payload.PLC_IP ?? '192.168.1.1'),
    dirtThreshold: Number(payload.DIRT_THRESHOLD ?? 0),
    snapshotInterval: Number(payload.SNAPSHOT_INTERVAL ?? 600),
    triggerClass: String(payload.TRIGGER_CLASS ?? 'ban'),
    minConfidence: Number(payload.MIN_CONFIDENCE ?? 0.6),
    isRunning: Boolean(payload.IS_RUNNING ?? false),
  };
}

export function normalizeApiResponse(payload: Record<string, unknown>): ApiResponse {
  return {
    success: Boolean(payload.success ?? false),
    message: String(payload.message ?? ''),
  };
}

export function countdownText(nextSnapshot: number) {
  const mins = Math.floor(nextSnapshot / 60);
  const secs = nextSnapshot % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function formatPercent(value: number, fractionDigits = 1) {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function thresholdPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function intervalMinutes(value: number) {
  return Math.floor(value / 60);
}
