import React from 'react';
import { Image, StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors } from '../theme';

export function BrandMark({ size = 68 }: { size?: number }) {
  const borderRadius = Math.round(size * 0.28);

  return (
    <View
      style={[
        styles.glowWrap,
        {
          width: size,
          height: size,
          borderRadius,
        },
      ]}
    >
      <LinearGradient
        colors={[colors.blue, colors.cyan]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[
          styles.gradientBox,
          {
            borderRadius,
          },
        ]}
      >
        <Image source={require('../../assets/ctut.png')} style={styles.logo} resizeMode="contain" />
      </LinearGradient>
    </View>
  );
}

const styles = StyleSheet.create({
  glowWrap: {
    shadowColor: colors.blue,
    shadowOpacity: 0.45,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 10 },
    elevation: 10,
    overflow: 'hidden',
  },
  gradientBox: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logo: {
    width: '70%',
    height: '70%',
  },
});

