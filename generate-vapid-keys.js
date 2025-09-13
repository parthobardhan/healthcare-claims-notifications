const webpush = require('web-push');
const fs = require('fs');

console.log('🔑 Healthcare Claims - VAPID Key Generator');
console.log('==========================================\n');

// Generate new VAPID keys
const vapidKeys = webpush.generateVAPIDKeys();

console.log('✅ Generated new VAPID keys:');
console.log(`Public Key:  ${vapidKeys.publicKey}`);
console.log(`Private Key: ${vapidKeys.privateKey}`);
console.log('');

// Save to environment file format
const envContent = `# Healthcare Claims VAPID Keys
# Generated: ${new Date().toISOString()}
VAPID_PUBLIC_KEY=${vapidKeys.publicKey}
VAPID_PRIVATE_KEY=${vapidKeys.privateKey}
VAPID_SUBJECT=mailto:admin@healthcareclaims.com
`;

// Save to file
try {
    fs.writeFileSync('.env.vapid', envContent);
    console.log('💾 Keys saved to .env.vapid file');
} catch (error) {
    console.log('❌ Could not save to .env.vapid file:', error.message);
}

console.log('');
console.log('📋 Copy these export commands to set environment variables:');
console.log('');
console.log(`export VAPID_PUBLIC_KEY="${vapidKeys.publicKey}"`);
console.log(`export VAPID_PRIVATE_KEY="${vapidKeys.privateKey}"`);
console.log(`export VAPID_SUBJECT="mailto:admin@healthcareclaims.com"`);
console.log('');
console.log('🚀 Restart your backend with these environment variables to use the new keys.');
console.log('⚠️  Remember: Clear existing subscriptions when changing VAPID keys!');
