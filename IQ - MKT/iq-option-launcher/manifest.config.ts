import manifest from './src/manifest.json';

if (manifest.host_permissions.some((pattern) => pattern === '<all_urls>')) {
  throw new Error('O manifesto não pode solicitar <all_urls>.');
}

export default manifest;
