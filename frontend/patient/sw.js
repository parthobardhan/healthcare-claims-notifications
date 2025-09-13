// Service Worker for Healthcare Claims Push Notifications
console.log('Healthcare Claims Service Worker: Loaded');

// Install event
self.addEventListener('install', event => {
    console.log('Healthcare Claims Service Worker: Installing...');
    // Skip waiting to activate immediately
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', event => {
    console.log('Healthcare Claims Service Worker: Activated');
    // Claim all clients immediately
    event.waitUntil(self.clients.claim());
});

// Push event - handles incoming push notifications
self.addEventListener('push', event => {
    console.log('🔔 Healthcare Claims Service Worker: Push event received');
    console.log('📊 Event data:', event.data);

    let notificationData = {
        title: 'Healthcare Claims Notification',
        body: 'You have a new claim update',
        icon: '/favicon.ico',
        url: '/'
    };

    // Parse notification data if available
    if (event.data) {
        try {
            // Try to parse as JSON first
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
            console.log('🔔 Healthcare Claims Service Worker: JSON notification data:', notificationData);
        } catch (error) {
            console.log('🔔 Healthcare Claims Service Worker: Not JSON data, using as text');
            // If JSON parsing fails, use the text as the notification body
            const textData = event.data.text();
            console.log('🔔 Healthcare Claims Service Worker: Text data received:', textData);

            // Update notification with text data
            notificationData.title = 'Healthcare Claims Update';
            notificationData.body = textData || 'You have a new claim update';

            console.log('🔔 Healthcare Claims Service Worker: Using text notification:', notificationData);
        }
    } else {
        console.log('🔔 Healthcare Claims Service Worker: No event data, using defaults');
    }

    const options = {
        body: notificationData.body,
        icon: notificationData.icon,
        data: {
            url: notificationData.url,
            timestamp: Date.now() // Add timestamp to make each notification unique
        },
        actions: [
            {
                action: 'open',
                title: 'View Claims',
                icon: '/favicon.ico'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ],
        vibrate: [200, 100, 200],
        requireInteraction: false,
        silent: false,
        tag: `healthcare-notification-${Date.now()}`, // Unique tag to prevent Chrome from grouping/suppressing
        renotify: true,
        // Chrome-specific options
        dir: 'auto',
        lang: 'en'
    };

    // Show the notification
    console.log('🎯 About to show notification with title:', notificationData.title);
    console.log('🎯 Notification options:', options);

    event.waitUntil(
        self.registration.showNotification(notificationData.title, options)
            .then(() => {
                console.log('✅ Healthcare Claims Service Worker: Notification shown successfully');
                console.log('🔔 Notification should now be visible in browser');
            })
            .catch(error => {
                console.error('❌ Healthcare Claims Service Worker: Error showing notification:', error);
                console.error('❌ This error prevents notifications from appearing');
            })
    );
});

// Notification click event
self.addEventListener('notificationclick', event => {
    console.log('Healthcare Claims Service Worker: Notification clicked');

    // Close the notification
    event.notification.close();

    // Handle action clicks
    const action = event.action;
    const url = event.notification.data.url || '/';

    if (action === 'close') {
        // Just close the notification (already done above)
        return;
    }

    // For 'open' action or default click, open/focus the app
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Check if app is already open
                for (let client of clientList) {
                    if (client.url.includes(url) && 'focus' in client) {
                        console.log('Healthcare Claims Service Worker: Focusing existing window');
                        return client.focus();
                    }
                }

                // If app is not open, open it
                if (clients.openWindow) {
                    console.log('Healthcare Claims Service Worker: Opening new window');
                    return clients.openWindow(url);
                }
            })
            .catch(error => {
                console.error('Healthcare Claims Service Worker: Error handling notification click:', error);
            })
    );
});

// Notification close event
self.addEventListener('notificationclose', event => {
    console.log('Healthcare Claims Service Worker: Notification closed', event.notification.tag);
});

console.log('Healthcare Claims Service Worker: Script loaded completely');
