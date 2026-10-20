const { getDefaultConfig } = require('expo/metro-config');
const exclusionList = require('metro-config/src/defaults/exclusionList');
const path = require('path');

const config = getDefaultConfig(__dirname);

const escapePath = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const makeProjectBuildPattern = (...segments) => {
  const targetPath = path.resolve(__dirname, ...segments).replace(/\\/g, '/');
  return new RegExp(`^${escapePath(targetPath)}/.*`);
};

config.resolver.blockList = exclusionList([
  makeProjectBuildPattern('android', 'app', 'build'),
  makeProjectBuildPattern('android', 'build'),
  makeProjectBuildPattern('build'),
]);

module.exports = config;
