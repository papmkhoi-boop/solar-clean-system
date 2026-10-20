import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

const CRACK_ALERT_CHANNEL_ID = 'crack-alerts';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

export async function ensureNotificationPermissions() {
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync(CRACK_ALERT_CHANNEL_ID, {
      name: 'Cảnh báo vết nứt',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
      vibrationPattern: [0, 400, 180, 400],
      lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
    });
  }

  const currentPermission = await Notifications.getPermissionsAsync();
  if (currentPermission.granted) {
    return true;
  }

  const requestedPermission = await Notifications.requestPermissionsAsync();
  return requestedPermission.granted;
}

export async function notifyCrackDetected(faults: string[]) {
  const detail = faults.length > 0 ? faults.join(', ') : 'Hệ thống vừa phát hiện vết nứt.';

  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'Cảnh báo vết nứt tấm pin',
      body: detail,
      sound: 'default',
      priority: Notifications.AndroidNotificationPriority.HIGH,
      data: {
        type: 'crack_detected',
      },
    },
    trigger: null,
  });
}
