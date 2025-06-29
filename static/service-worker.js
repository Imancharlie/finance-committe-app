const CACHE_NAME = 'mission-tracker-cache-v2';
const STATIC_CACHE = 'static-cache-v2';
const DYNAMIC_CACHE = 'dynamic-cache-v2';

// Files to cache immediately
const STATIC_FILES = [
  '/',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
];

// Pages to cache for offline navigation
const PAGES_TO_CACHE = [
  '/dashboard/',
  '/admin-log/',
  '/daily-collection/',
  '/add-member/',
  '/import-excel/'
];

self.addEventListener('install', event => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_FILES)),
      caches.open(DYNAMIC_CACHE).then(cache => cache.addAll(PAGES_TO_CACHE))
    ])
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map(key => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const { request } = event;
  
  // Skip non-GET requests
  if (request.method !== 'GET') return;
  
  // Handle API requests differently
  if (request.url.includes('/ajax/') || request.url.includes('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => {
          // Return offline response for API calls
          return new Response(JSON.stringify({ 
            error: 'You are offline. Please check your connection.' 
          }), {
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  event.respondWith(
    caches.match(request)
      .then(response => {
        // Return cached version if available
        if (response) {
          return response;
        }

        // Try to fetch from network
        return fetch(request)
          .then(fetchResponse => {
            // Cache successful responses for navigation requests
            if (request.mode === 'navigate' && fetchResponse.status === 200) {
              const responseClone = fetchResponse.clone();
              caches.open(DYNAMIC_CACHE).then(cache => {
                cache.put(request, responseClone);
              });
            }
            return fetchResponse;
          })
          .catch(() => {
            // Offline fallback for navigation requests
            if (request.mode === 'navigate') {
              return caches.match('/');
            }
            
            // Return offline page for other requests
            return new Response(`
              <!DOCTYPE html>
              <html>
                <head>
                  <title>Offline - Mission Tracker</title>
                  <meta name="viewport" content="width=device-width, initial-scale=1">
                  <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .offline-icon { font-size: 4rem; color: #666; }
                  </style>
                </head>
                <body>
                  <div class="offline-icon">📱</div>
                  <h2>You're Offline</h2>
                  <p>Please check your internet connection and try again.</p>
                  <button onclick="window.location.reload()">Retry</button>
                </body>
              </html>
            `, {
              headers: { 'Content-Type': 'text/html' }
            });
          });
      })
  );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(doBackgroundSync());
  }
});

function doBackgroundSync() {
  // Handle background sync when connection is restored
  return Promise.resolve();
} 