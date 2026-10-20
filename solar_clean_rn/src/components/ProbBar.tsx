import React from 'react';
import { DimensionValue, StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';

export function ProbBar({ label, value, color }: { label: string; value: number; color: string }) {
  const widthPercent: DimensionValue = `${Math.max(0, Math.min(100, value * 100))}%`;

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <Text style={styles.label}>{label}</Text>
        <Text style={[styles.value, { color }]}>{(value * 100).toFixed(1)}%</Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: widthPercent, backgroundColor: color }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  label: {
    color: colors.txt2,
    fontSize: 12,
  },
  value: {
    fontSize: 12,
    fontWeight: '700',
  },
  track: {
    height: 7,
    borderRadius: 999,
    backgroundColor: colors.bg1,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 999,
  },
});
