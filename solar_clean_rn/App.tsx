import React from 'react';
import { ActivityIndicator, SafeAreaView, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { AppProvider, useApp } from './src/context/AppContext';
import { colors } from './src/theme';
import { DashboardScreen } from './src/screens/DashboardScreen';
import { LoginScreen } from './src/screens/LoginScreen';
import { RegisterScreen } from './src/screens/RegisterScreen';

function Root() {
  const { authChecked, isLoggedIn, activeAuthScreen } = useApp();

  if (!authChecked) {
    return (
      <SafeAreaView style={styles.bootShell}>
        <StatusBar style="light" />
        <View style={styles.bootCard}>
          <ActivityIndicator color={colors.blue} size="small" />
          <Text style={styles.bootTitle}>Solar Clean</Text>
          <Text style={styles.bootSubtitle}>Đang khôi phục phiên làm việc...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (isLoggedIn) {
    return <DashboardScreen />;
  }

  return activeAuthScreen === 'register' ? <RegisterScreen /> : <LoginScreen />;
}

export default function App() {
  return (
    <AppProvider>
      <Root />
    </AppProvider>
  );
}

const styles = StyleSheet.create({
  bootShell: {
    flex: 1,
    backgroundColor: colors.bg0,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  bootCard: {
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingVertical: 28,
    backgroundColor: colors.bg1,
  },
  bootTitle: {
    color: colors.txt1,
    fontSize: 20,
    fontWeight: '800',
  },
  bootSubtitle: {
    color: colors.txt3,
    fontSize: 13,
  },
});
