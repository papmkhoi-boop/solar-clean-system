import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
  useWindowDimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Feather } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { BrandMark } from '../components/BrandMark';
import { useApp } from '../context/AppContext';
import { colors } from '../theme';

export function LoginScreen() {
  const { width } = useWindowDimensions();
  const { busy, lastError, login, openRegister } = useApp();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  const wide = width >= 920;

  async function handleLogin() {
    if (!username.trim() || !password) {
      return;
    }
    await login(username, password);
  }

  const form = (
    <View style={styles.formCard}>
      <Text style={styles.formTitle}>Đăng nhập</Text>
      <Text style={styles.formSubtitle}>Truy cập hệ thống giám sát và điều khiển Solar Clean.</Text>

      {lastError ? (
        <View style={styles.errorBox}>
          <Feather name="alert-triangle" size={16} color={colors.red} />
          <Text style={styles.errorText}>{lastError}</Text>
        </View>
      ) : null}

      <Text style={styles.fieldLabel}>Tài khoản</Text>
      <View style={styles.fieldWrap}>
        <Feather name="user" size={16} color={colors.txt3} />
        <TextInput
          value={username}
          onChangeText={setUsername}
          style={styles.input}
          placeholder="Nhập tài khoản"
          placeholderTextColor={colors.txtMuted}
          autoCapitalize="none"
          autoComplete="off"
          importantForAutofill="no"
          textContentType="none"
        />
      </View>

      <Text style={styles.fieldLabel}>Mật khẩu</Text>
      <View style={styles.fieldWrap}>
        <Feather name="lock" size={16} color={colors.txt3} />
        <TextInput
          value={password}
          onChangeText={setPassword}
          style={styles.input}
          placeholder="Nhập mật khẩu"
          placeholderTextColor={colors.txtMuted}
          secureTextEntry
          onSubmitEditing={handleLogin}
        />
      </View>

      <TouchableOpacity
        style={[styles.primaryButton, busy ? styles.primaryButtonBusy : null]}
        onPress={handleLogin}
        disabled={busy}
      >
        <Text style={styles.primaryButtonText}>{busy ? 'Đang kết nối...' : 'Đăng nhập'}</Text>
        <Feather name="arrow-right" size={16} color="#fff" />
      </TouchableOpacity>

      <View style={styles.authFooter}>
        <Text style={styles.footerHint}>Chưa có tài khoản?</Text>
        <TouchableOpacity onPress={openRegister}>
          <Text style={styles.footerLink}>Đăng ký</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar style="light" />
      <LinearGradient colors={[colors.bg0, '#08111e', '#07101a']} style={StyleSheet.absoluteFill} />
      <View style={[styles.orb, styles.orbTop]} />
      <View style={[styles.orb, styles.orbBottom]} />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.select({
          ios: 'padding',
          android: undefined,
        })}
      >
        <ScrollView contentContainerStyle={wide ? styles.scrollWide : styles.scrollMobile}>
          {wide ? (
            <View style={styles.desktopShell}>
              <View style={styles.brandPanel}>
                <BrandMark size={84} />
                <Text style={styles.brandTitle}>Solar Clean</Text>
                <Text style={styles.brandSubtitle}>HỆ THỐNG GIÁM SÁT SCADA</Text>

                <FeatureRow
                  icon="activity"
                  title="Giám sát thời gian thực"
                  subtitle="Theo dõi trạng thái tấm pin, PLC và kết quả AI liên tục."
                />
                <FeatureRow
                  icon="cpu"
                  title="AI nhận diện độ bẩn"
                  subtitle="Nhận diện độ bẩn, độ tin cậy và gợi ý thời điểm vệ sinh."
                />
                <FeatureRow
                  icon="sliders"
                  title="Điều khiển từ xa"
                  subtitle="Khởi động, dừng, kết nối lại PLC và thay đổi thông số trên di động."
                />
                <View style={styles.readyPill}>
                  <View style={styles.readyDot} />
                  <Text style={styles.readyText}>Sẵn sàng vận hành</Text>
                </View>
              </View>

              <View style={styles.formPanel}>{form}</View>
            </View>
          ) : (
            <View style={styles.mobileShell}>
              <BrandMark size={72} />
              <Text style={styles.mobileTitle}>Solar Clean</Text>
              <Text style={styles.mobileSubtitle}>HỆ THỐNG GIÁM SÁT SCADA</Text>
              {form}
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function FeatureRow({
  icon,
  title,
  subtitle,
}: {
  icon: keyof typeof Feather.glyphMap;
  title: string;
  subtitle: string;
}) {
  return (
    <View style={styles.featureRow}>
      <View style={styles.featureIcon}>
        <Feather name={icon} size={18} color={colors.blue} />
      </View>
      <View style={styles.featureBody}>
        <Text style={styles.featureTitle}>{title}</Text>
        <Text style={styles.featureSubtitle}>{subtitle}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  screen: {
    flex: 1,
    backgroundColor: colors.bg0,
  },
  scrollMobile: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 22,
    paddingVertical: 32,
  },
  scrollWide: {
    flexGrow: 1,
    padding: 24,
    justifyContent: 'center',
  },
  desktopShell: {
    minHeight: 720,
    flexDirection: 'row',
    borderRadius: 32,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.overlay,
  },
  brandPanel: {
    flex: 1.15,
    padding: 40,
    backgroundColor: 'rgba(11, 17, 30, 0.88)',
    gap: 20,
    justifyContent: 'center',
  },
  formPanel: {
    flex: 0.95,
    padding: 32,
    justifyContent: 'center',
    backgroundColor: 'rgba(16, 22, 36, 0.94)',
    borderLeftWidth: 1,
    borderLeftColor: colors.border,
  },
  mobileShell: {
    width: '100%',
    maxWidth: 460,
    alignItems: 'center',
    gap: 16,
  },
  mobileTitle: {
    color: '#fff',
    fontSize: 28,
    fontWeight: '900',
    textAlign: 'center',
  },
  mobileSubtitle: {
    color: colors.cyan,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.5,
    textAlign: 'center',
  },
  brandTitle: {
    color: '#fff',
    fontSize: 38,
    fontWeight: '900',
    marginTop: 12,
  },
  brandSubtitle: {
    color: colors.cyan,
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 2,
    marginBottom: 12,
  },
  featureRow: {
    flexDirection: 'row',
    gap: 14,
    alignItems: 'flex-start',
  },
  featureIcon: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: colors.blueDim,
    borderWidth: 1,
    borderColor: 'rgba(59,130,246,0.25)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureBody: {
    flex: 1,
    gap: 4,
  },
  featureTitle: {
    color: colors.txt1,
    fontSize: 15,
    fontWeight: '700',
  },
  featureSubtitle: {
    color: colors.txt3,
    fontSize: 13,
    lineHeight: 18,
  },
  readyPill: {
    marginTop: 12,
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 8,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: 'rgba(34,197,94,0.26)',
    backgroundColor: colors.greenDim,
  },
  readyDot: {
    width: 8,
    height: 8,
    borderRadius: 999,
    backgroundColor: colors.green,
  },
  readyText: {
    color: colors.green,
    fontWeight: '700',
    fontSize: 12,
  },
  formCard: {
    width: '100%',
    maxWidth: 440,
    alignSelf: 'center',
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 26,
    backgroundColor: 'rgba(17, 24, 39, 0.86)',
    paddingHorizontal: 24,
    paddingVertical: 28,
    gap: 16,
  },
  formTitle: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '800',
    textAlign: 'center',
  },
  formSubtitle: {
    color: colors.txt3,
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 6,
    textAlign: 'center',
  },
  errorBox: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(239,68,68,0.25)',
    backgroundColor: colors.redDim,
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  errorText: {
    color: colors.red,
    fontSize: 13,
    flex: 1,
  },
  fieldLabel: {
    color: colors.txt2,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 2,
  },
  fieldWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
    borderRadius: 14,
    paddingHorizontal: 14,
    minHeight: 52,
  },
  input: {
    flex: 1,
    color: colors.txt1,
    fontSize: 14,
    paddingVertical: 14,
  },
  primaryButton: {
    marginTop: 6,
    borderRadius: 14,
    backgroundColor: colors.blue,
    paddingHorizontal: 18,
    paddingVertical: 15,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    minHeight: 52,
  },
  primaryButtonBusy: {
    opacity: 0.7,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '800',
  },
  authFooter: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
    marginTop: 4,
  },
  footerHint: {
    color: colors.txt3,
    fontSize: 13,
  },
  footerLink: {
    color: colors.blue,
    fontSize: 13,
    fontWeight: '700',
  },
  orb: {
    position: 'absolute',
    borderRadius: 999,
    backgroundColor: colors.blueDim,
  },
  orbTop: {
    width: 360,
    height: 360,
    top: -120,
    right: -100,
  },
  orbBottom: {
    width: 280,
    height: 280,
    bottom: -100,
    left: -80,
    backgroundColor: colors.cyanDim,
  },
});
