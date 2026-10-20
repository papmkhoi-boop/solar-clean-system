import AsyncStorage from '@react-native-async-storage/async-storage';
import React, { ReactNode, createContext, useContext, useEffect, useRef, useState } from 'react';
import { ApiService, normalizeServerUrl } from '../services/api';
import { ensureNotificationPermissions, notifyCrackDetected } from '../services/notifications';
import {
  ApiResponse,
  SystemSettings,
  SystemStatus,
  defaultSettings,
  defaultStatus,
} from '../types/models';

const DEFAULT_SERVER_URL = 'https://ctut.clean.id.vn';
const STORAGE_KEYS = {
  session: 'session_cookie',
};

type AuthScreen = 'login' | 'register';

interface AppContextValue {
  api: ApiService;
  authChecked: boolean;
  busy: boolean;
  isLoggedIn: boolean;
  activeAuthScreen: AuthScreen;
  status: SystemStatus;
  settings: SystemSettings;
  connected: boolean;
  wsConnected: boolean;
  lastError: string | null;
  openLogin: () => void;
  openRegister: () => void;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, password: string, fullname?: string) => Promise<ApiResponse>;
  logout: () => Promise<void>;
  refreshAll: () => Promise<void>;
  refreshStatus: () => Promise<SystemStatus | null>;
  systemStart: () => Promise<ApiResponse>;
  systemStop: () => Promise<ApiResponse>;
  manualClean: () => Promise<ApiResponse>;
  plcReconnect: (plcIp: string) => Promise<ApiResponse>;
  setSnapshotInterval: (minutes: number) => Promise<ApiResponse>;
  setDirtThreshold: (threshold: number) => Promise<ApiResponse>;
  powerData: { voltage: number; current: number; power: number; energy: number; efficiency: any } | null;
  powerHistory: any[];
  powerHourly: any[];
  powerDaily: any[];
  powerMonthly: any[];
  cleaningEfficiency: any[];
  fetchPowerData: () => Promise<void>;
  fetchPowerHistory: (hours?: number) => Promise<void>;
  fetchPowerHourly: () => Promise<void>;
  fetchPowerDaily: (days?: number) => Promise<void>;
  fetchPowerMonthly: () => Promise<void>;
  fetchCleaningEfficiency: (limit?: number) => Promise<void>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const apiRef = useRef(new ApiService(DEFAULT_SERVER_URL));
  const wsCleanupRef = useRef<null | (() => void)>(null);
  const pollRef = useRef<null | ReturnType<typeof setInterval>>(null);
  const wsConnectedRef = useRef(false);
  const crackActiveRef = useRef(false);
  const lastCrackAlertKeyRef = useRef<string | null>(null);

  const [authChecked, setAuthChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [activeAuthScreen, setActiveAuthScreen] = useState<AuthScreen>('login');
  const [session, setSession] = useState<string | null>(null);
  const [status, setStatus] = useState(defaultStatus);
  const [settings, setSettings] = useState(defaultSettings);
  const [wsConnected, setWsConnected] = useState(false);
  const [connected, setConnected] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [powerData, setPowerData] = useState<{ voltage: number; current: number; power: number; energy: number; efficiency: any } | null>(null);
  const [powerHistory, setPowerHistory] = useState<any[]>([]);
  const [powerHourly, setPowerHourly] = useState<any[]>([]);
  const [powerDaily, setPowerDaily] = useState<any[]>([]);
  const [powerMonthly, setPowerMonthly] = useState<any[]>([]);
  const [cleaningEfficiency, setCleaningEfficiency] = useState<any[]>([]);

  const isLoggedIn = Boolean(session);

  function setRealtimeState(nextState: boolean) {
    wsConnectedRef.current = nextState;
    setWsConnected(nextState);
  }

  function stopRealtime() {
    wsCleanupRef.current?.();
    wsCleanupRef.current = null;

    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    setRealtimeState(false);
  }

  async function resetSessionState() {
    stopRealtime();
    apiRef.current.setSession(null);
    setSession(null);
    setConnected(false);
    setStatus(defaultStatus);
    setSettings(defaultSettings);
    setLastError(null);
    setActiveAuthScreen('login');
    await AsyncStorage.removeItem(STORAGE_KEYS.session);
  }

  function getCrackAlertKey(nextStatus: SystemStatus) {
    return (
      nextStatus.lastSnapshotPath ??
      nextStatus.lastSnapshotTime ??
      nextStatus.yoloCrackFaults.join('|') ??
      'crack'
    );
  }

  function applyStatus(nextStatus: SystemStatus) {
    setStatus(nextStatus);

    const hasCrack = nextStatus.yoloCrackFaults.length > 0;
    if (!hasCrack) {
      crackActiveRef.current = false;
      return;
    }

    const alertKey = getCrackAlertKey(nextStatus);
    const shouldNotify = !crackActiveRef.current || alertKey !== lastCrackAlertKeyRef.current;
    crackActiveRef.current = true;

    if (!shouldNotify) {
      return;
    }

    lastCrackAlertKeyRef.current = alertKey;
    notifyCrackDetected(nextStatus.yoloCrackFaults).catch(() => undefined);
  }

  async function fetchSettings() {
    const result = await apiRef.current.getSettings();
    if (result.ok && result.data) {
      setSettings(result.data);
    }
  }

  async function refreshStatus() {
    const result = await apiRef.current.getStatus();
    if (result.ok && result.data) {
      applyStatus(result.data);
      setConnected(true);
      return result.data;
    }

    if (result.unauthorized) {
      await resetSessionState();
      return null;
    }

    setConnected(false);
    return null;
  }

  function startRealtime() {
    stopRealtime();

    wsCleanupRef.current = apiRef.current.connectWebSocket(
      (nextStatus) => {
        applyStatus(nextStatus);
        setConnected(true);
        setRealtimeState(true);
      },
      (nextState) => {
        setRealtimeState(nextState);
      },
    );

    pollRef.current = setInterval(() => {
      if (wsConnectedRef.current) {
        return;
      }

      refreshStatus().catch(() => {
        setConnected(false);
      });
    }, 2000);
  }

  async function fetchPowerData() {
    const res = await apiRef.current.getPowerData();
    if (res.ok && res.data) {
      setPowerData(res.data as any);
    }
  }

  async function fetchPowerHistory(hours = 1) {
    const res = await apiRef.current.getPowerHistory(hours);
    if (res.ok && res.data && Array.isArray(res.data.readings)) {
      setPowerHistory(res.data.readings);
    }
  }

  async function fetchPowerHourly() {
    const res = await apiRef.current.getPowerHourly();
    if (res.ok && res.data && Array.isArray(res.data.hourly)) {
      setPowerHourly(res.data.hourly);
    }
  }

  async function fetchPowerDaily(days = 7) {
    const res = await apiRef.current.getPowerDaily(days);
    if (res.ok && res.data && Array.isArray(res.data.daily)) {
      setPowerDaily(res.data.daily);
    }
  }

  async function fetchPowerMonthly() {
    const res = await apiRef.current.getPowerMonthly();
    if (res.ok && res.data && Array.isArray(res.data.monthly)) {
      setPowerMonthly(res.data.monthly);
    }
  }

  async function fetchCleaningEfficiency(limit = 20) {
    const res = await apiRef.current.getCleaningEfficiency(limit);
    if (res.ok && res.data && Array.isArray(res.data.events)) {
      setCleaningEfficiency(res.data.events);
    }
  }

  async function refreshAll() {
    await Promise.all([
      refreshStatus(),
      fetchSettings(),
      fetchPowerData(),
      fetchCleaningEfficiency(),
    ]);
  }

  async function login(username: string, password: string) {
    setBusy(true);
    setLastError(null);

    const result = await apiRef.current.login(username.trim(), password);
    if (!result.ok || !result.data?.session) {
      setBusy(false);
      setLastError(result.error ?? 'Đăng nhập thất bại');
      return false;
    }

    apiRef.current.setSession(result.data.session);
    setSession(result.data.session);
    await AsyncStorage.setItem(STORAGE_KEYS.session, result.data.session);

    await refreshStatus();
    await fetchSettings();
    startRealtime();
    setBusy(false);
    return true;
  }

  async function register(username: string, password: string, fullname = '') {
    setBusy(true);
    setLastError(null);
    const response = await apiRef.current.register(username.trim(), password, fullname.trim());
    setBusy(false);
    if (!response.success) {
      setLastError(response.message);
    }
    return response;
  }

  async function logout() {
    await resetSessionState();
  }

  async function bootstrap() {
    const normalizedUrl = normalizeServerUrl(DEFAULT_SERVER_URL);
    apiRef.current.setBaseUrl(normalizedUrl);
    await AsyncStorage.removeItem('server_url');

    const storedSession = await AsyncStorage.getItem(STORAGE_KEYS.session);
    if (!storedSession) {
      setAuthChecked(true);
      return;
    }

    apiRef.current.setSession(storedSession);
    setSession(storedSession);

    const statusResult = await apiRef.current.getStatus();
    if (statusResult.unauthorized) {
      await resetSessionState();
      setAuthChecked(true);
      return;
    }

    if (statusResult.ok && statusResult.data) {
      applyStatus(statusResult.data);
      setConnected(true);
    }

    await fetchSettings();
    await Promise.all([fetchPowerData(), fetchCleaningEfficiency()]);
    startRealtime();
    setAuthChecked(true);
  }

  useEffect(() => {
    ensureNotificationPermissions().catch(() => undefined);
    bootstrap().catch(() => {
      setAuthChecked(true);
    });

    return () => {
      stopRealtime();
    };
  }, []);

  async function afterCommand(response: ApiResponse) {
    if (response.success) {
      await refreshAll();
    }
    return response;
  }

  async function systemStart() {
    return afterCommand(await apiRef.current.systemStart());
  }

  async function systemStop() {
    return afterCommand(await apiRef.current.systemStop());
  }

  async function manualClean() {
    return afterCommand(await apiRef.current.manualClean());
  }

  async function plcReconnect(plcIp: string) {
    return afterCommand(await apiRef.current.plcReconnect(plcIp));
  }

  async function saveSettings(payload: {
    cameraId?: number;
    plcIp?: string;
    dirtThreshold?: number;
  }) {
    return afterCommand(await apiRef.current.postSettings(payload));
  }

  async function setSnapshotInterval(minutes: number) {
    return afterCommand(await apiRef.current.setSnapshotInterval(minutes * 60));
  }

  async function setDirtThreshold(threshold: number) {
    return afterCommand(await apiRef.current.setDirtThreshold(threshold));
  }

  return (
    <AppContext.Provider
      value={{
        api: apiRef.current,
        authChecked,
        busy,
        isLoggedIn,
        activeAuthScreen,
        status,
        settings,
        connected,
        wsConnected,
        lastError,
        openLogin: () => {
          setLastError(null);
          setActiveAuthScreen('login');
        },
        openRegister: () => {
          setLastError(null);
          setActiveAuthScreen('register');
        },
        login,
        register,
        logout,
        refreshAll,
        refreshStatus,
        systemStart,
        systemStop,
        manualClean,
        plcReconnect,
        saveSettings,
        setSnapshotInterval,
        setDirtThreshold,
        powerData,
        powerHistory,
        powerHourly,
        powerDaily,
        powerMonthly,
        cleaningEfficiency,
        fetchPowerData,
        fetchPowerHistory,
        fetchPowerHourly,
        fetchPowerDaily,
        fetchPowerMonthly,
        fetchCleaningEfficiency,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used inside AppProvider');
  }
  return context;
}
