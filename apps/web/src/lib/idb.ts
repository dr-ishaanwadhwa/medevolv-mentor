const DB_NAME = 'medevolv_atlas_offline_v1';
const DB_VERSION = 1;
const STORE_GEOMETRY = 'geometry_blobs';
const STORE_MANIFEST = 'manifest';

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      reject(new Error('IndexedDB not supported in current environment'));
      return;
    }
    const request = window.indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_GEOMETRY)) {
        db.createObjectStore(STORE_GEOMETRY, { keyPath: 'url' });
      }
      if (!db.objectStoreNames.contains(STORE_MANIFEST)) {
        db.createObjectStore(STORE_MANIFEST, { keyPath: 'key' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function getCachedGeometryChunk(url: string): Promise<ArrayBuffer | null> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_GEOMETRY, 'readonly');
      const store = tx.objectStore(STORE_GEOMETRY);
      const req = store.get(url);
      req.onsuccess = () => {
        if (req.result && req.result.buffer instanceof ArrayBuffer) {
          resolve(req.result.buffer);
        } else {
          resolve(null);
        }
      };
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function setCachedGeometryChunk(url: string, buffer: ArrayBuffer, bytes: number): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_GEOMETRY, 'readwrite');
      const store = tx.objectStore(STORE_GEOMETRY);
      // Clone buffer or store slice to ensure safe persistence
      const copy = buffer.slice(0);
      const req = store.put({
        url,
        buffer: copy,
        bytes,
        timestamp: Date.now(),
      });
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('Failed to cache geometry in IndexedDB:', err);
  }
}

export async function getCachedManifest<T = unknown>(key = 'atlas.json'): Promise<T | null> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_MANIFEST, 'readonly');
      const store = tx.objectStore(STORE_MANIFEST);
      const req = store.get(key);
      req.onsuccess = () => {
        if (req.result && req.result.data) {
          resolve(req.result.data as T);
        } else {
          resolve(null);
        }
      };
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function setCachedManifest(key: string, data: unknown): Promise<void> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MANIFEST, 'readwrite');
      const store = tx.objectStore(STORE_MANIFEST);
      const req = store.put({
        key,
        data,
        timestamp: Date.now(),
      });
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn('Failed to cache manifest in IndexedDB:', err);
  }
}
