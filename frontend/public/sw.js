/* Armstrong PWA service worker: conservative navigation fallback only. */
const CACHE='armstrong-offline-v1';
const OFFLINE='/offline';
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.add(OFFLINE)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil((async()=>{for(const key of await caches.keys()){if(key.startsWith('armstrong-offline-')&&key!==CACHE)await caches.delete(key)}await self.clients.claim()})())});
self.addEventListener('fetch',event=>{const req=event.request;if(req.mode!=='navigate'||req.method!=='GET')return;event.respondWith(fetch(req).catch(async()=>{const cache=await caches.open(CACHE);return await cache.match(OFFLINE)||Response.error()}))});
