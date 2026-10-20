import React from 'react';
import { Feather } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

export function KpiCard({
  icon,
  label,
  value,
  color,
}: {
  icon: keyof typeof Feather.glyphMap;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <View style={styles.card}>
      <View style={[styles.iconWrap, { backgroundColor: `${color}1F` }]}>
        <Feather name={icon} size={18} color={color} />
      </View>
      <View style={styles.meta}>
        <Text style={styles.label}>{label}</Text>
        <Text style={[styles.value, { color }]} numberOfLines={2}>
          {value}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    minWidth: 150,
    flexGrow: 1,
    flexBasis: 150,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.bg2,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 88,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  meta: {
    flex: 1,
    gap: 3,
    minWidth: 0,
  },
  label: {
    color: colors.txt3,
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  value: {
    fontSize: 15,
    lineHeight: 18,
    fontWeight: '800',
  },
});
