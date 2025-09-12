self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('push', event => {
  let data = {}; try { data = event.data ? event.data.json() : {}; } catch (e) {}
  const title = data.title || 'Notification';
  const body = data.body || '';
  const icon = data.icon || undefined;
  const url = data.url || '/';
  event.waitUntil(self.registration.showNotification(title, { body, icon, data: { url } }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) return client.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});

