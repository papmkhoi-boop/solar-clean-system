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
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Feather } from '@expo/vector-icons';
import { StatusBar } from 'expo-status-bar';
import { BrandMark } from '../components/BrandMark';
import { useApp } from '../context/AppContext';
import { colors } from '../theme';

export function RegisterScreen() {
  const { busy, lastError, openLogin, register } = useApp();

  const [fullname, setFullname] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleRegister() {
    setLocalError(null);
    setSuccessMessage(null);

    if (username.trim().length < 3) {
      setLocalError('Tài khoản phải có ít nhất 3 ký tự.');
      return;
    }
    if (password.length < 4) {
      setLocalError('Mật khẩu phải có ít nhất 4 ký tự.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Mật khẩu nhập lại không khớp.');
      return;
    }

    const result = await register(username, password, fullname);
    if (result.success) {
      setSuccessMessage(result.message || 'Đăng ký thành công.');
    }
  }

  const message = localError || lastError;

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
        <ScrollView contentContainerStyle={styles.scroll}>
          <View style={styles.card}>
            <View style={styles.brandWrap}>
              <BrandMark size={68} />
            </View>
            <Text style={styles.title}>Đăng ký tài khoản</Text>
            <Text style={styles.subtitle}>Tạo tài khoản mới để truy cập hệ thống Solar Clean.</Text>

            {message ? (
              <View style={[styles.banner, styles.bannerError]}>
                <Feather name="alert-triangle" size={16} color={colors.red} />
                <Text style={styles.bannerErrorText}>{message}</Text>
              </View>
            ) : null}

            {successMessage ? (
              <View style={[styles.banner, styles.bannerSuccess]}>
                <Feather name="check-circle" size={16} color={colors.green} />
                <Text style={styles.bannerSuccessText}>{successMessage}</Text>
              </View>
            ) : (
              <>
                <Field label="Họ và tên">
                  <TextInput
                    value={fullname}
                    onChangeText={setFullname}
                    style={styles.input}
                    placeholder="Nhập họ và tên"
                    placeholderTextColor={colors.txtMuted}
                  />
                </Field>

                <Field label="Tài khoản *">
                  <TextInput
                    value={username}
                    onChangeText={setUsername}
                    style={styles.input}
                    placeholder="Tối thiểu 3 ký tự"
                    placeholderTextColor={colors.txtMuted}
                    autoCapitalize="none"
                  />
                </Field>

                <Field label="Mật khẩu *">
                  <TextInput
                    value={password}
                    onChangeText={setPassword}
                    style={styles.input}
                    placeholder="Tối thiểu 4 ký tự"
                    placeholderTextColor={colors.txtMuted}
                    secureTextEntry
                  />
                </Field>

                <Field label="Nhập lại mật khẩu *">
                  <TextInput
                    value={confirmPassword}
                    onChangeText={setConfirmPassword}
                    style={styles.input}
                    placeholder="Nhập lại mật khẩu"
                    placeholderTextColor={colors.txtMuted}
                    secureTextEntry
                    onSubmitEditing={handleRegister}
                  />
                </Field>

                <TouchableOpacity
                  style={[styles.primaryButton, busy ? styles.primaryButtonBusy : null]}
                  onPress={handleRegister}
                  disabled={busy}
                >
                  <Feather name="user-plus" size={16} color="#fff" />
                  <Text style={styles.primaryButtonText}>{busy ? 'Đang xử lý...' : 'Đăng ký'}</Text>
                </TouchableOpacity>
              </>
            )}

            <View style={styles.footer}>
              <Text style={styles.footerHint}>Đã có tài khoản?</Text>
              <TouchableOpacity onPress={openLogin}>
                <Text style={styles.footerLink}>Đăng nhập</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View style={styles.fieldBlock}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.fieldWrap}>{children}</View>
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
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 22,
    paddingVertical: 32,
  },
  brandWrap: {
    alignItems: 'center',
  },
  card: {
    width: '100%',
    maxWidth: 460,
    alignSelf: 'center',
    alignItems: 'stretch',
    gap: 16,
    borderRadius: 26,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: 'rgba(17, 24, 39, 0.86)',
    paddingHorizontal: 24,
    paddingVertical: 28,
  },
  title: {
    color: '#fff',
    fontSize: 24,
    fontWeight: '800',
    textAlign: 'center',
  },
  subtitle: {
    color: colors.txt3,
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
    marginBottom: 4,
  },
  banner: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
  },
  bannerError: {
    borderColor: 'rgba(239,68,68,0.25)',
    backgroundColor: colors.redDim,
  },
  bannerSuccess: {
    borderColor: 'rgba(34,197,94,0.25)',
    backgroundColor: colors.greenDim,
  },
  bannerErrorText: {
    flex: 1,
    color: colors.red,
    fontSize: 13,
  },
  bannerSuccessText: {
    flex: 1,
    color: colors.green,
    fontSize: 13,
  },
  fieldBlock: {
    gap: 8,
  },
  fieldLabel: {
    color: colors.txt2,
    fontSize: 12,
    fontWeight: '700',
  },
  fieldWrap: {
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg1,
    borderRadius: 14,
    paddingHorizontal: 14,
    minHeight: 52,
  },
  input: {
    color: colors.txt1,
    fontSize: 14,
    paddingVertical: 14,
  },
  primaryButton: {
    marginTop: 4,
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
  footer: {
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
    width: 320,
    height: 320,
    top: -120,
    right: -90,
  },
  orbBottom: {
    width: 240,
    height: 240,
    bottom: -80,
    left: -60,
    backgroundColor: colors.cyanDim,
  },
});
