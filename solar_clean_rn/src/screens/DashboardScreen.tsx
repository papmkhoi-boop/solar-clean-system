import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  Image,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Feather } from '@expo/vector-icons';
import { WebView } from 'react-native-webview';
import { BrandMark } from '../components/BrandMark';
import { KpiCard } from '../components/KpiCard';
import { ProbBar } from '../components/ProbBar';
import { SectionCard } from '../components/SectionCard';
import { useApp } from '../context/AppContext';
import { colors, toneFromStatus } from '../theme';
import {
  ApiResponse,
  SystemStatus,
  countdownText,
  formatPercent,
  intervalMinutes,
  thresholdPercent,
} from '../types/models';

type TabKey = 'monitor' | 'control' | 'power';

export function DashboardScreen() {
  const { width } = useWindowDimensions();
  const { logout, refreshAll, status, wsConnected } = useApp();
  const [tab, setTab] = useState<TabKey>('monitor');
  const [refreshing, setRefreshing] = useState(false);
  const statusTone = toneFromStatus(status.statusColor);
  const compactHeader = width < 430;
  const connectionLabel = compactHeader
    ? wsConnected
      ? 'WS'
      : 'REST'
    : wsConnected
      ? 'WebSocket'
      : 'REST dự phòng';

  async function handleRefresh() {
    setRefreshing(true);
    await refreshAll();
    setRefreshing(false);
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <View style={[styles.header, compactHeader ? styles.headerCompact : null]}>
        <View style={[styles.headerBrand, compactHeader ? styles.headerBrandCompact : null]}>
          <BrandMark size={34} />
          <View>
            <Text style={styles.headerTitle}>Solar Clean</Text>
            <Text style={styles.headerSubtitle}>Giám sát và điều khiển SCADA</Text>
          </View>
        </View>

        <View style={[styles.headerActions, compactHeader ? styles.headerActionsCompact : null]}>
          <View style={styles.liveBadge}>
            <View
              style={[
                styles.liveDot,
                { backgroundColor: wsConnected ? colors.green : colors.red },
              ]}
            />
            <Text style={styles.liveText}>{connectionLabel}</Text>
          </View>

          <View
            style={[
              styles.runBadge,
              {
                backgroundColor: `${statusTone}20`,
                borderColor: `${statusTone}50`,
              },
            ]}
          >
            <Text style={[styles.runBadgeText, { color: statusTone }]}>
              {status.isRunning ? 'Đang chạy' : 'Dừng'}
            </Text>
          </View>

          <TouchableOpacity style={styles.iconButton} onPress={logout}>
            <Feather name="log-out" size={18} color={colors.red} />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.tabBar}>
        <TabButton
          label="Giám sát"
          icon="grid"
          active={tab === 'monitor'}
          onPress={() => setTab('monitor')}
        />
        <TabButton
          label="Điều khiển"
          icon="sliders"
          active={tab === 'control'}
          onPress={() => setTab('control')}
        />
        <TabButton
          label="Hiệu năng"
          icon="bar-chart-2"
          active={tab === 'power'}
          onPress={() => setTab('power')}
        />
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={colors.blue}
          />
        }
      >
        {tab === 'monitor' ? <MonitorTab /> : tab === 'control' ? <ControlTab /> : <PowerTab />}
      </ScrollView>
    </SafeAreaView>
  );
}

function MonitorTab() {
  const { status } = useApp();
  const statusTone = toneFromStatus(status.statusColor);
  const aiLabel = status.cnnActive ? status.labelName : 'CNN bỏ qua';
  const yoloObjects =
    status.yoloCleanFaults.length > 0 ? status.yoloCleanFaults.join(', ') : 'Không có';
  const yoloCracks =
    status.yoloCrackFaults.length > 0 ? status.yoloCrackFaults.join(', ') : 'Không có';

  return (
    <View style={styles.stack}>
      <View
        style={[
          styles.statusBanner,
          {
            borderColor: `${statusTone}55`,
            backgroundColor: `${statusTone}1A`,
          },
        ]}
      >
        <Feather
          name={
            status.statusColor === 'danger'
              ? 'alert-triangle'
              : status.statusColor === 'success'
                ? 'check-circle'
                : 'info'
          }
          size={18}
          color={statusTone}
        />
        <View style={styles.statusBannerBody}>
          <Text style={[styles.statusBannerText, { color: statusTone }]}>{status.status}</Text>
          <Text style={styles.statusBannerSub}>Lần quét kế tiếp {countdownText(status.nextSnapshot)}</Text>
        </View>
      </View>

      <View style={styles.kpiGrid}>
        <KpiCard icon="tag" label="CNN" value={aiLabel} color={colors.blue} />
        <KpiCard
          icon="cpu"
          label="PLC"
          value={status.plcConnected ? 'Trực tuyến' : 'Ngoại tuyến'}
          color={status.plcConnected ? colors.green : colors.red}
        />
        <KpiCard icon="activity" label="FPS" value={status.fps.toFixed(0)} color={colors.cyan} />
        <KpiCard
          icon="wind"
          label="VỆ SINH"
          value={String(status.cleanCount)}
          color={colors.yellow}
        />
      </View>

      <SectionCard icon="info" title="Cấu hình hiện tại">
        <ConfigRow label="Chu kỳ AI" value={`${intervalMinutes(status.snapshotInterval)} phút`} />
        <Divider />
        <ConfigRow label="Ngưỡng bẩn" value={thresholdPercent(status.dirtThreshold)} />
        <Divider />
        <ConfigRow label="Camera" value={String(status.cameraId)} />
        <Divider />
        <ConfigRow label="IP PLC" value={status.plcIp} />
      </SectionCard>

      <SectionCard icon="bar-chart-2" title="Phân tích AI">
        <InfoRow label="Pipeline" value={status.modelPipeline} />
        <InfoRow label="Phân loại CNN" value={aiLabel} />
        <InfoRow label="Độ tin cậy" value={status.cnnActive ? formatPercent(status.confidence) : '—'} />
        <InfoRow label="Tỷ lệ bẩn" value={formatPercent(status.areaRatio)} />
        {status.predProbs.length >= 2 ? (
          <View style={styles.probStack}>
            <ProbBar label="Sạch" value={status.predProbs[0]} color={colors.green} />
            <ProbBar label="Bẩn" value={status.predProbs[1]} color={colors.red} />
          </View>
        ) : null}
      </SectionCard>

      <SectionCard icon="box" title="YOLO / Panel-Seg">
        <InfoRow
          label="Tấm pin"
          value={status.panelDetected ? 'Đã nhận diện' : status.cnnActive ? 'Dùng full frame' : 'Không tìm thấy'}
          color={status.panelDetected ? colors.green : status.cnnActive ? colors.txt2 : colors.yellow}
        />
        <InfoRow label="Vật cản" value={yoloObjects} color={status.yoloCleanFaults.length ? colors.orange : colors.txt2} />
        <InfoRow label="Nứt vỡ" value={yoloCracks} color={status.yoloCrackFaults.length ? colors.red : colors.txt2} />
      </SectionCard>

      <SectionCard icon="video" title="Khung hình trực tiếp">
        <LiveFrame />
        <View style={styles.feedMeta}>
          <Text style={styles.mutedText}>{status.fps.toFixed(0)} fps</Text>
          <View
            style={[
              styles.smallPill,
              {
                backgroundColor: status.isRunning ? colors.greenDim : colors.redDim,
              },
            ]}
          >
            <Text
              style={[
                styles.smallPillText,
                { color: status.isRunning ? colors.green : colors.red },
              ]}
            >
              {status.isRunning ? 'Đang chạy' : 'Đã dừng'}
            </Text>
          </View>
        </View>
      </SectionCard>

      <SectionCard icon="image" title="Ảnh chụp gần nhất">
        <SnapshotPanel status={status} />
      </SectionCard>

      <SectionCard icon="grid" title="CNN 32 patch">
        <AnalysisFramePanel
          type="cnn"
          cacheKey={status.lastSnapshotPath ?? status.lastSnapshotTime ?? status.timestamp}
          emptyText="Chưa có ảnh lưới 32 patch CNN"
          loadingText="Đang tải ảnh 32 patch..."
        />
      </SectionCard>

      <SectionCard icon="box" title="YOLO nhận diện tấm pin">
        <AnalysisFramePanel
          type="yolo"
          cacheKey={status.lastSnapshotPath ?? status.lastSnapshotTime ?? status.timestamp}
          emptyText="Chưa có ảnh YOLO / Panel-Seg"
          loadingText="Đang tải ảnh YOLO..."
        />
      </SectionCard>
    </View>
  );
}

function LiveFrame() {
  const [streamFailed, setStreamFailed] = useState(false);
  const { api, isLoggedIn } = useApp();

  if (!isLoggedIn) {
    return <Placeholder text="Chưa kết nối tới máy chủ" icon="wifi-off" />;
  }

  if (streamFailed) {
    return <PolledLiveFrame />;
  }

  return (
    <View style={styles.frameWrap}>
      <WebView
        source={api.buildVideoFeedSource()}
        style={styles.webviewFrame}
        originWhitelist={['*']}
        scrollEnabled={false}
        bounces={false}
        overScrollMode="never"
        javaScriptEnabled={false}
        domStorageEnabled={false}
        setSupportMultipleWindows={false}
        onError={() => setStreamFailed(true)}
        onHttpError={() => setStreamFailed(true)}
      />
    </View>
  );
}

function PolledLiveFrame() {
  const { api, isLoggedIn, status } = useApp();
  const [refreshKey, setRefreshKey] = useState(Date.now());
  const [primaryFrameUri, setPrimaryFrameUri] = useState<string | null>(null);
  const [secondaryFrameUri, setSecondaryFrameUri] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const showingPrimaryRef = useRef(true);
  const pendingSlotRef = useRef<'primary' | 'secondary' | null>(null);
  const primaryOpacity = useRef(new Animated.Value(1)).current;
  const secondaryOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshKey(Date.now());
    }, status.isRunning ? 1200 : 2200);

    return () => clearInterval(interval);
  }, [status.isRunning]);

  useEffect(() => {
    let active = true;

    if (!isLoggedIn) {
      setPrimaryFrameUri(null);
      setSecondaryFrameUri(null);
      setFailed(false);
      showingPrimaryRef.current = true;
      pendingSlotRef.current = null;
      primaryOpacity.setValue(1);
      secondaryOpacity.setValue(0);
      return () => {
        active = false;
      };
    }

    setFailed(false);

    api
      .fetchCurrentFrameDataUri(refreshKey)
      .then((uri) => {
        if (!active) {
          return;
        }

        if (!primaryFrameUri) {
          setPrimaryFrameUri(uri);
          showingPrimaryRef.current = true;
          pendingSlotRef.current = null;
          primaryOpacity.setValue(1);
          secondaryOpacity.setValue(0);
          setFailed(false);
          return;
        }

        const targetSlot = showingPrimaryRef.current ? 'secondary' : 'primary';
        pendingSlotRef.current = targetSlot;
        if (targetSlot === 'primary') {
          setPrimaryFrameUri(uri);
        } else {
          setSecondaryFrameUri(uri);
        }
        setFailed(false);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        if (!primaryFrameUri && !secondaryFrameUri) {
          setFailed(true);
        }
      });

    return () => {
      active = false;
    };
  }, [api, isLoggedIn, refreshKey]);

  if (!isLoggedIn) {
    return <Placeholder text="Chưa kết nối tới máy chủ" icon="wifi-off" />;
  }

  if (failed && !primaryFrameUri && !secondaryFrameUri) {
    return <Placeholder text="Không lấy được khung hình hiện tại" icon="video-off" />;
  }

  if (!primaryFrameUri && !secondaryFrameUri) {
    return <Placeholder text="Đang tải khung hình..." icon="camera" />;
  }

  function revealFrame(slot: 'primary' | 'secondary') {
    if (pendingSlotRef.current !== slot) {
      return;
    }

    pendingSlotRef.current = null;
    showingPrimaryRef.current = slot === 'primary';

    Animated.parallel([
      Animated.timing(primaryOpacity, {
        toValue: slot === 'primary' ? 1 : 0,
        duration: 140,
        useNativeDriver: true,
      }),
      Animated.timing(secondaryOpacity, {
        toValue: slot === 'secondary' ? 1 : 0,
        duration: 140,
        useNativeDriver: true,
      }),
    ]).start();
  }

  return (
    <View style={styles.frameWrap}>
      {primaryFrameUri ? (
        <Animated.Image
          source={{ uri: primaryFrameUri }}
          style={[styles.frameImage, styles.frameLayer, { opacity: primaryOpacity }]}
          resizeMode="contain"
          onLoadEnd={() => revealFrame('primary')}
        />
      ) : null}
      {secondaryFrameUri ? (
        <Animated.Image
          source={{ uri: secondaryFrameUri }}
          style={[styles.frameImage, styles.frameLayer, { opacity: secondaryOpacity }]}
          resizeMode="contain"
          onLoadEnd={() => revealFrame('secondary')}
        />
      ) : null}
    </View>
  );
}

function SnapshotPanel({ status }: { status: SystemStatus }) {
  const { api } = useApp();
  const [snapshotUri, setSnapshotUri] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;

    if (!status.lastSnapshotPath) {
      setSnapshotUri(null);
      setFailed(false);
      return () => {
        active = false;
      };
    }

    setFailed(false);

    api
      .fetchSnapshotDataUri(status.lastSnapshotPath, status.lastSnapshotPath)
      .then((uri) => {
        if (!active) {
          return;
        }
        setSnapshotUri(uri);
        setFailed(false);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        if (!snapshotUri) {
          setFailed(true);
        }
      });

    return () => {
      active = false;
    };
  }, [api, status.lastSnapshotPath]);

  if (!status.lastSnapshotPath || failed) {
    return <Placeholder text="Chưa có ảnh chụp" icon="image" compact />;
  }

  if (!snapshotUri) {
    return <Placeholder text="Đang tải ảnh chụp..." icon="image" compact />;
  }

  return (
    <View style={styles.snapshotWrap}>
      <View style={styles.snapshotImageWrap}>
        <Image
          source={{ uri: snapshotUri }}
          style={styles.snapshotImage}
          resizeMode="contain"
          onError={() => {
            if (!snapshotUri) {
              setFailed(true);
            }
          }}
        />
      </View>
      <View style={styles.snapshotMeta}>
        <Text style={styles.mutedText}>{status.lastSnapshotTime || 'Chưa có thời gian'}</Text>
        <Text style={styles.snapshotResult}>
          {status.labelName} · {formatPercent(status.confidence)}
        </Text>
      </View>
    </View>
  );
}

function AnalysisFramePanel({
  type,
  cacheKey,
  emptyText,
  loadingText,
}: {
  type: 'cnn' | 'yolo';
  cacheKey: string | number;
  emptyText: string;
  loadingText: string;
}) {
  const { api, isLoggedIn } = useApp();
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;

    if (!isLoggedIn || !cacheKey) {
      setImageUri(null);
      setFailed(false);
      return () => {
        active = false;
      };
    }

    setFailed(false);

    const request =
      type === 'cnn'
        ? api.fetchCnnPatchFrameDataUri(cacheKey)
        : api.fetchYoloPanelFrameDataUri(cacheKey);

    request
      .then((uri) => {
        if (!active) {
          return;
        }
        setImageUri(uri);
        setFailed(false);
      })
      .catch(() => {
        if (!active) {
          return;
        }
        if (!imageUri) {
          setFailed(true);
        }
      });

    return () => {
      active = false;
    };
  }, [api, cacheKey, isLoggedIn, type]);

  if (!isLoggedIn || failed) {
    return <Placeholder text={emptyText} icon={type === 'cnn' ? 'grid' : 'box'} compact />;
  }

  if (!imageUri) {
    return <Placeholder text={loadingText} icon={type === 'cnn' ? 'grid' : 'box'} compact />;
  }

  return (
    <View style={styles.analysisImageWrap}>
      <Image source={{ uri: imageUri }} style={styles.analysisImage} resizeMode="contain" />
    </View>
  );
}

function ControlTab() {
  const {
    status,
    systemStart,
    systemStop,
    manualClean,
    plcReconnect,
    saveSettings,
    setSnapshotInterval,
    setDirtThreshold,
  } = useApp();

  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [plcIp, setPlcIp] = useState(status.plcIp);
  const [cameraId, setCameraId] = useState(String(status.cameraId));
  const [interval, setIntervalValue] = useState(String(intervalMinutes(status.snapshotInterval)));
  const [threshold, setThreshold] = useState(String(Math.round(status.dirtThreshold * 100)));

  useEffect(() => {
    if (!editing && !busy) {
      setPlcIp(status.plcIp);
      setCameraId(String(status.cameraId));
      setIntervalValue(String(intervalMinutes(status.snapshotInterval)));
      setThreshold(String(Math.round(status.dirtThreshold * 100)));
    }
  }, [busy, editing, status]);

  async function runCommand(action: () => Promise<ApiResponse>) {
    setBusy(true);
    const result = await action();
    setBusy(false);
    Alert.alert(
      result.success ? 'Thành công' : 'Lỗi',
      result.message || (result.success ? 'Hoàn tất' : 'Yêu cầu thất bại'),
    );
  }

  return (
    <View style={styles.stack}>
      <SectionCard icon="power" title="Điều khiển hệ thống">
        <InfoRow
          label="Trạng thái"
          value={status.isRunning ? 'Đang chạy' : 'Dừng'}
          color={status.isRunning ? colors.green : colors.red}
        />
        <View style={styles.actionRow}>
          <ActionButton
            icon="play"
            label="Khởi động"
            color={colors.green}
            disabled={busy || status.isRunning}
            onPress={() => runCommand(systemStart)}
          />
          <ActionButton
            icon="square"
            label="Dừng"
            color={colors.red}
            disabled={busy || !status.isRunning}
            onPress={() => runCommand(systemStop)}
          />
        </View>
      </SectionCard>

      <SectionCard icon="cpu" title="Điều khiển PLC">
        <InfoRow
          label="Kết nối"
          value={status.plcConnected ? 'Trực tuyến' : 'Ngoại tuyến'}
          color={status.plcConnected ? colors.green : colors.red}
        />
        <InfoRow label="IP" value={status.plcIp} />
        <View style={styles.actionRow}>
          <ActionButton
            icon="refresh-cw"
            label="Kết nối lại"
            color={colors.blue}
            disabled={busy}
            onPress={() => runCommand(() => plcReconnect(plcIp))}
          />
          <ActionButton
            icon="wind"
            label="Vệ sinh"
            color={colors.green}
            disabled={busy}
            onPress={() => runCommand(manualClean)}
          />
        </View>
      </SectionCard>

      <SectionCard icon="clock" title="Chu kỳ chụp ảnh">
        <InputBlock
          value={interval}
          onChangeText={(value) => {
            setEditing(true);
            setIntervalValue(value);
          }}
          keyboardType="number-pad"
          suffix="phút"
        />
        <ActionButton
          icon="check"
          label="Lưu chu kỳ"
          color={colors.blue}
          disabled={busy}
          onPress={() => {
            const minutes = Number(interval);
            if (!Number.isFinite(minutes) || minutes < 1 || minutes > 1440) {
              Alert.alert('Giá trị không hợp lệ', 'Chu kỳ phải trong khoảng 1-1440 phút.');
              return;
            }
            setEditing(false);
            runCommand(() => setSnapshotInterval(minutes));
          }}
        />
      </SectionCard>

      <SectionCard icon="percent" title="Ngưỡng độ bẩn">
        <InputBlock
          value={threshold}
          onChangeText={(value) => {
            setEditing(true);
            setThreshold(value);
          }}
          keyboardType="number-pad"
          suffix="%"
        />
        <ThresholdBar value={Number(threshold) || 0} />
        <ActionButton
          icon="check"
          label="Lưu ngưỡng"
          color={colors.blue}
          disabled={busy}
          onPress={() => {
            const value = Number(threshold);
            if (!Number.isFinite(value) || value < 0 || value > 100) {
              Alert.alert('Giá trị không hợp lệ', 'Ngưỡng phải trong khoảng 0-100%.');
              return;
            }
            setEditing(false);
            runCommand(() => setDirtThreshold(value / 100));
          }}
        />
      </SectionCard>

      <SectionCard icon="settings" title="Cấu hình thiết bị">
        <Text style={styles.fieldHeading}>PLC IP</Text>
        <TextInput
          value={plcIp}
          onChangeText={(value) => {
            setEditing(true);
            setPlcIp(value);
          }}
          style={styles.panelInput}
          placeholder="192.168.1.11"
          placeholderTextColor={colors.txtMuted}
          autoCapitalize="none"
        />

        <Text style={styles.fieldHeading}>ID camera</Text>
        <TextInput
          value={cameraId}
          onChangeText={(value) => {
            setEditing(true);
            setCameraId(value);
          }}
          style={styles.panelInput}
          placeholder="0"
          placeholderTextColor={colors.txtMuted}
          keyboardType="number-pad"
        />

        <ActionButton
          icon="save"
          label="Lưu cấu hình"
          color={colors.blue}
          disabled={busy}
          onPress={() => {
            const parsedCamera = Number(cameraId);
            if (!Number.isFinite(parsedCamera) || parsedCamera < 0) {
              Alert.alert('Giá trị không hợp lệ', 'ID camera phải là số nguyên >= 0.');
              return;
            }
            setEditing(false);
            runCommand(() =>
              saveSettings({
                cameraId: parsedCamera,
                plcIp,
              }),
            );
          }}
        />
      </SectionCard>
    </View>
  );
}

function TabButton({
  label,
  icon,
  active,
  onPress,
}: {
  label: string;
  icon: keyof typeof Feather.glyphMap;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity style={[styles.tabButton, active ? styles.tabButtonActive : null]} onPress={onPress}>
      <Feather name={icon} size={16} color={active ? colors.blue : colors.txt3} />
      <Text style={[styles.tabText, active ? styles.tabTextActive : null]}>{label}</Text>
    </TouchableOpacity>
  );
}

function Divider() {
  return <View style={styles.divider} />;
}

function ConfigRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <View style={styles.valueChip}>
        <Text style={styles.valueChipText}>{value}</Text>
      </View>
    </View>
  );
}

function InfoRow({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={[styles.infoValue, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

function Placeholder({
  text,
  icon,
  compact = false,
}: {
  text: string;
  icon: keyof typeof Feather.glyphMap;
  compact?: boolean;
}) {
  return (
    <View style={[styles.placeholder, compact ? styles.placeholderCompact : null]}>
      <Feather name={icon} size={compact ? 26 : 34} color={colors.txt3} />
      <Text style={styles.placeholderText}>{text}</Text>
    </View>
  );
}

function InputBlock({
  value,
  onChangeText,
  keyboardType,
  suffix,
}: {
  value: string;
  onChangeText: (value: string) => void;
  keyboardType: 'default' | 'number-pad';
  suffix: string;
}) {
  return (
    <View style={styles.inputRow}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        style={[styles.panelInput, styles.flexInput]}
        placeholderTextColor={colors.txtMuted}
        keyboardType={keyboardType}
      />
      <Text style={styles.inputSuffix}>{suffix}</Text>
    </View>
  );
}

function ThresholdBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  const color = clamped > 60 ? colors.red : clamped > 30 ? colors.yellow : colors.green;

  return (
    <View style={styles.thresholdWrap}>
      <View style={styles.thresholdRow}>
        <Text style={styles.mutedText}>0%</Text>
        <Text style={[styles.thresholdValue, { color }]}>{Math.round(clamped)}%</Text>
        <Text style={styles.mutedText}>100%</Text>
      </View>
      <View style={styles.thresholdTrack}>
        <View style={[styles.thresholdFill, { width: `${clamped}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
}

function ActionButton({
  icon,
  label,
  color,
  disabled,
  onPress,
}: {
  icon: keyof typeof Feather.glyphMap;
  label: string;
  color: string;
  disabled?: boolean;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      style={[
        styles.actionButton,
        {
          backgroundColor: `${color}20`,
          borderColor: `${color}35`,
          opacity: disabled ? 0.45 : 1,
        },
      ]}
      onPress={onPress}
      disabled={disabled}
    >
      <Feather name={icon} size={16} color={color} />
      <Text style={[styles.actionButtonText, { color }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function CustomBarChart({
  data,
  valueKey,
  labelKey,
  unit,
  barColor = colors.blue,
  labelFormatter = (l: string) => l,
}: {
  data: any[];
  valueKey: string;
  labelKey: string;
  unit: string;
  barColor?: string;
  labelFormatter?: (label: string) => string;
}) {
  if (!data || data.length === 0) {
    return <Placeholder text="Không có dữ liệu thống kê" icon="bar-chart-2" compact />;
  }

  const values = data.map(item => Number(item[valueKey] ?? 0));
  const maxVal = Math.max(...values, 0.1);

  return (
    <View style={styles.chartContainer}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chartScroll}>
        <View style={styles.chartBarsWrap}>
          {data.map((item, index) => {
            const val = Number(item[valueKey] ?? 0);
            const rawLabel = String(item[labelKey] ?? '');
            const label = labelFormatter(rawLabel);
            const barHeightPct = `${Math.max(5, Math.min(100, (val / maxVal) * 100))}%`;

            return (
              <View key={index} style={styles.chartColumn}>
                <View style={styles.chartBarTrack}>
                  <View
                    style={[
                      styles.chartBarFill,
                      { height: barHeightPct, backgroundColor: barColor },
                    ]}
                  />
                  <Text style={styles.chartBarValue}>{val.toFixed(val < 10 ? 2 : 1)}{unit}</Text>
                </View>
                <Text style={styles.chartBarLabel} numberOfLines={1}>{label}</Text>
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

function PowerTab() {
  const {
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
  } = useApp();

  const [resolution, setResolution] = useState<'realtime' | 'hourly' | 'daily' | 'monthly'>('realtime');

  useEffect(() => {
    fetchPowerData().catch(() => undefined);
    fetchCleaningEfficiency(20).catch(() => undefined);

    const interval = setInterval(() => {
      fetchPowerData().catch(() => undefined);
    }, 4000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (resolution === 'realtime') {
      fetchPowerHistory(1).catch(() => undefined);
    } else if (resolution === 'hourly') {
      fetchPowerHourly().catch(() => undefined);
    } else if (resolution === 'daily') {
      fetchPowerDaily(7).catch(() => undefined);
    } else if (resolution === 'monthly') {
      fetchPowerMonthly().catch(() => undefined);
    }
  }, [resolution]);

  // Format real-time metrics
  const v = powerData?.voltage ?? 0;
  const a = powerData?.current ?? 0;
  const w = powerData?.power ?? 0;
  const kwh = powerData?.energy ?? 0;

  // Select chart configuration based on resolution
  let chartData: any[] = [];
  let valueKey = 'power';
  let labelKey = 'timestamp';
  let unit = 'W';
  let barColor = colors.yellow;
  let labelFormatter = (val: string) => val;

  if (resolution === 'realtime') {
    // Keep last 18 readings for better visibility
    chartData = powerHistory.slice(-18);
    valueKey = 'power';
    labelKey = 'timestamp';
    unit = 'W';
    barColor = colors.yellow;
    labelFormatter = (t) => t.split(' ')[1]?.slice(0, 5) ?? t;
  } else if (resolution === 'hourly') {
    chartData = powerHourly;
    valueKey = 'avg_power';
    labelKey = 'hour';
    unit = 'W';
    barColor = colors.blue;
    labelFormatter = (h) => `${h}h`;
  } else if (resolution === 'daily') {
    chartData = powerDaily;
    valueKey = 'total_energy';
    labelKey = 'date';
    unit = 'kWh';
    barColor = colors.green;
    labelFormatter = (d) => d.slice(5).replace('-', '/');
  } else if (resolution === 'monthly') {
    chartData = powerMonthly;
    valueKey = 'total_energy';
    labelKey = 'month';
    unit = 'kWh';
    barColor = colors.cyan;
    labelFormatter = (m) => `T${m}`;
  }

  return (
    <View style={styles.stack}>
      <View style={styles.kpiGrid}>
        <KpiCard icon="zap" label="CÔNG SUẤT" value={`${w.toFixed(1)} W`} color={colors.yellow} />
        <KpiCard icon="activity" label="ĐIỆN ÁP" value={`${v.toFixed(1)} V`} color={colors.blue} />
        <KpiCard icon="trending-up" label="DÒNG ĐIỆN" value={`${a.toFixed(2)} A`} color={colors.cyan} />
        <KpiCard icon="sun" label="SẢN LƯỢNG" value={`${kwh.toFixed(2)} kWh`} color={colors.green} />
      </View>

      <SectionCard icon="bar-chart-2" title="Biểu đồ công suất & năng lượng">
        <View style={styles.resSelector}>
          <TouchableOpacity
            style={[styles.resBtn, resolution === 'realtime' ? styles.resBtnActive : null]}
            onPress={() => setResolution('realtime')}
          >
            <Text style={[styles.resBtnText, resolution === 'realtime' ? styles.resBtnTextActive : null]}>T.Thời</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.resBtn, resolution === 'hourly' ? styles.resBtnActive : null]}
            onPress={() => setResolution('hourly')}
          >
            <Text style={[styles.resBtnText, resolution === 'hourly' ? styles.resBtnTextActive : null]}>Giờ</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.resBtn, resolution === 'daily' ? styles.resBtnActive : null]}
            onPress={() => setResolution('daily')}
          >
            <Text style={[styles.resBtnText, resolution === 'daily' ? styles.resBtnTextActive : null]}>Ngày</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.resBtn, resolution === 'monthly' ? styles.resBtnActive : null]}
            onPress={() => setResolution('monthly')}
          >
            <Text style={[styles.resBtnText, resolution === 'monthly' ? styles.resBtnTextActive : null]}>Tháng</Text>
          </TouchableOpacity>
        </View>

        <CustomBarChart
          data={chartData}
          valueKey={valueKey}
          labelKey={labelKey}
          unit={unit}
          barColor={barColor}
          labelFormatter={labelFormatter}
        />
      </SectionCard>

      <SectionCard icon="wind" title="Hiệu suất vệ sinh">
        {cleaningEfficiency.length === 0 ? (
          <Placeholder text="Chưa có dữ liệu lịch sử vệ sinh" icon="wind" compact />
        ) : (
          <View style={styles.efficiencyList}>
            {cleaningEfficiency.map((item, idx) => {
              const gain = item.power_gain ?? 0;
              const imp = item.improvement_pct ?? 0;
              const isPositive = gain > 0;
              return (
                <View key={item.id ?? idx} style={styles.efficiencyItem}>
                  <View style={styles.efficiencyHeader}>
                    <Text style={styles.efficiencyTime}>{item.start_time ?? 'Không có ngày'}</Text>
                    <View
                      style={[
                        styles.efficiencyBadge,
                        {
                          backgroundColor: isPositive ? colors.greenDim : colors.redDim,
                          borderColor: isPositive ? colors.green : colors.red,
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.efficiencyBadgeText,
                          { color: isPositive ? colors.green : colors.red },
                        ]}
                      >
                        {isPositive ? `+${imp.toFixed(1)}%` : `${imp.toFixed(1)}%`}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.efficiencyBody}>
                    <View style={styles.effDetail}>
                      <Text style={styles.effDetailLabel}>Trước quét</Text>
                      <Text style={styles.effDetailValue}>{(item.pre_clean_power ?? 0).toFixed(1)}W</Text>
                    </View>
                    <View style={styles.effDetail}>
                      <Text style={styles.effDetailLabel}>Sau quét</Text>
                      <Text style={styles.effDetailValue}>{(item.post_clean_power ?? 0).toFixed(1)}W</Text>
                    </View>
                    <View style={styles.effDetail}>
                      <Text style={styles.effDetailLabel}>Tăng trưởng</Text>
                      <Text
                        style={[
                          styles.effDetailValue,
                          { color: isPositive ? colors.green : colors.red, fontWeight: '800' },
                        ]}
                      >
                        {isPositive ? `+${gain.toFixed(1)}W` : `${gain.toFixed(1)}W`}
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        )}
      </SectionCard>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.bg0,
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    backgroundColor: colors.bg1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  headerCompact: {
    alignItems: 'flex-start',
  },
  headerBrand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
    minWidth: 0,
  },
  headerBrandCompact: {
    paddingTop: 2,
  },
  headerTitle: {
    color: colors.txt1,
    fontSize: 16,
    fontWeight: '800',
  },
  headerSubtitle: {
    color: colors.txt3,
    fontSize: 11,
    fontWeight: '600',
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    flexWrap: 'wrap',
    gap: 8,
  },
  headerActionsCompact: {
    maxWidth: 164,
  },
  liveBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor: colors.bg2,
    borderWidth: 1,
    borderColor: colors.border,
  },
  liveDot: {
    width: 8,
    height: 8,
    borderRadius: 999,
  },
  liveText: {
    color: colors.txt2,
    fontSize: 11,
    fontWeight: '700',
  },
  runBadge: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
  },
  runBadgeText: {
    fontSize: 11,
    fontWeight: '800',
  },
  iconButton: {
    width: 38,
    height: 38,
    borderRadius: 999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg2,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tabBar: {
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: colors.bg0,
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 12,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
  },
  tabButtonActive: {
    borderColor: 'rgba(59,130,246,0.35)',
    backgroundColor: colors.blueDim,
  },
  tabText: {
    color: colors.txt3,
    fontSize: 13,
    fontWeight: '700',
  },
  tabTextActive: {
    color: colors.blue,
  },
  scroll: {
    padding: 16,
    paddingBottom: 28,
  },
  stack: {
    gap: 14,
  },
  statusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderRadius: 18,
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  statusBannerBody: {
    flex: 1,
    gap: 4,
  },
  statusBannerText: {
    fontSize: 14,
    fontWeight: '800',
  },
  statusBannerSub: {
    color: colors.txt3,
    fontSize: 12,
  },
  kpiGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  infoLabel: {
    color: colors.txt3,
    fontSize: 13,
    flex: 1,
  },
  infoValue: {
    color: colors.txt1,
    fontSize: 13,
    fontWeight: '700',
    flexShrink: 1,
    textAlign: 'right',
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
  },
  valueChip: {
    backgroundColor: colors.blueDim,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginLeft: 'auto',
    maxWidth: '68%',
  },
  valueChipText: {
    color: colors.blue,
    fontSize: 12,
    fontWeight: '700',
    textAlign: 'right',
  },
  probStack: {
    gap: 10,
    marginTop: 6,
  },
  frameWrap: {
    width: '100%',
    height: 220,
    borderRadius: 14,
    overflow: 'hidden',
    backgroundColor: colors.bg1,
    borderWidth: 1,
    borderColor: colors.border,
  },
  frameImage: {
    width: '100%',
    height: '100%',
  },
  webviewFrame: {
    flex: 1,
    backgroundColor: colors.bg1,
  },
  frameLayer: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
  },
  feedMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 10,
  },
  mutedText: {
    color: colors.txt3,
    fontSize: 11,
  },
  smallPill: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  smallPillText: {
    fontSize: 10,
    fontWeight: '800',
  },
  placeholder: {
    width: '100%',
    height: 220,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  placeholderCompact: {
    height: 120,
  },
  placeholderText: {
    color: colors.txt3,
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
    maxWidth: 220,
  },
  snapshotWrap: {
    gap: 10,
  },
  snapshotImageWrap: {
    width: '100%',
    height: 190,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
  },
  snapshotImage: {
    width: '100%',
    height: '100%',
  },
  analysisImageWrap: {
    width: '100%',
    height: 230,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
  },
  analysisImage: {
    width: '100%',
    height: '100%',
  },
  snapshotMeta: {
    gap: 4,
  },
  snapshotResult: {
    color: colors.txt2,
    fontSize: 11,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 10,
    flexWrap: 'wrap',
  },
  actionButton: {
    flexGrow: 1,
    flexBasis: 140,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 13,
    minHeight: 50,
  },
  actionButtonText: {
    fontSize: 13,
    fontWeight: '800',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  panelInput: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 13,
    color: colors.txt1,
    fontSize: 14,
    minHeight: 50,
  },
  flexInput: {
    flex: 1,
  },
  inputSuffix: {
    color: colors.txt3,
    fontSize: 13,
    minWidth: 42,
    textAlign: 'right',
  },
  thresholdWrap: {
    gap: 6,
  },
  thresholdRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 10,
  },
  thresholdValue: {
    fontSize: 12,
    fontWeight: '800',
  },
  thresholdTrack: {
    height: 8,
    borderRadius: 999,
    overflow: 'hidden',
    backgroundColor: colors.bg1,
  },
  thresholdFill: {
    height: '100%',
    borderRadius: 999,
  },
  fieldHeading: {
    color: colors.txt2,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 2,
  },
  // Charts & selector styles
  chartContainer: {
    height: 200,
    width: '100%',
    paddingVertical: 12,
    marginTop: 10,
  },
  chartScroll: {
    alignItems: 'flex-end',
    paddingHorizontal: 8,
  },
  chartBarsWrap: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 12,
    height: 150,
  },
  chartColumn: {
    alignItems: 'center',
    width: 44,
    height: '100%',
    justifyContent: 'flex-end',
  },
  chartBarTrack: {
    flex: 1,
    width: 16,
    backgroundColor: colors.bg2,
    borderRadius: 6,
    justifyContent: 'flex-end',
    alignItems: 'center',
    position: 'relative',
  },
  chartBarFill: {
    width: '100%',
    borderRadius: 6,
  },
  chartBarValue: {
    position: 'absolute',
    top: -16,
    fontSize: 8,
    color: colors.txt2,
    fontWeight: '700',
    width: 44,
    textAlign: 'center',
  },
  chartBarLabel: {
    fontSize: 9,
    color: colors.txt3,
    marginTop: 6,
    fontWeight: '600',
    width: 44,
    textAlign: 'center',
  },
  resSelector: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
    justifyContent: 'space-between',
    backgroundColor: colors.bg2,
    padding: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  resBtn: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: 8,
  },
  resBtnActive: {
    backgroundColor: colors.bg1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
    elevation: 1,
  },
  resBtnText: {
    fontSize: 11,
    color: colors.txt3,
    fontWeight: '700',
  },
  resBtnTextActive: {
    color: colors.blue,
  },
  // Efficiency log styles
  efficiencyList: {
    gap: 12,
  },
  efficiencyItem: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    padding: 12,
    backgroundColor: colors.bg1,
    gap: 10,
  },
  efficiencyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  efficiencyTime: {
    fontSize: 12,
    color: colors.txt2,
    fontWeight: '700',
  },
  efficiencyBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    borderWidth: 1,
  },
  efficiencyBadgeText: {
    fontSize: 10,
    fontWeight: '800',
  },
  efficiencyBody: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: colors.bg2,
    borderRadius: 10,
    padding: 10,
  },
  effDetail: {
    alignItems: 'center',
    flex: 1,
  },
  effDetailLabel: {
    fontSize: 10,
    color: colors.txt3,
    marginBottom: 4,
  },
  effDetailValue: {
    fontSize: 12,
    color: colors.txt1,
    fontWeight: '700',
  },
});
