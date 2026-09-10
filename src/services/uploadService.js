/**
 * Mock upload service.
 *
 * This currently just creates a local object URL so the file can be
 * previewed immediately in the browser (image/video/document icon).
 * Nothing is sent to a server.
 *
 * TO CONNECT A REAL BACKEND LATER:
 *   Replace the body of `uploadFile` with an actual network call, e.g.:
 *
 *   export async function uploadFile(file, { kind } = {}) {
 *     const formData = new FormData();
 *     formData.append('file', file);
 *     formData.append('kind', kind);
 *     const res = await fetch('/api/uploads', { method: 'POST', body: formData });
 *     if (!res.ok) throw new Error('Upload failed');
 *     const data = await res.json();
 *     return { id: data.id, url: data.url, name: file.name, kind, size: file.size };
 *   }
 *
 * Keep the same return shape ({ id, url, name, kind, size }) so calling
 * components don't need to change when the real API is wired up.
 */

let localIdCounter = 1;

export async function uploadFile(file, { kind = 'document' } = {}) {
  // Simulate a short network delay so upload UI states can be shown.
  await new Promise((resolve) => setTimeout(resolve, 350));

  const url = URL.createObjectURL(file);

  return {
    id: `local-${Date.now()}-${localIdCounter++}`,
    url,
    name: file.name,
    kind,
    size: file.size,
    mimeType: file.type,
  };
}

export function revokeUploadUrl(url) {
  try {
    URL.revokeObjectURL(url);
  } catch {
    // no-op — already revoked or invalid
  }
}

/**
 * Uploads a recorded voice note (Blob from MediaRecorder) the same way
 * as any other file upload, so it slots into the same attachment list.
 */
export async function uploadVoiceNote(blob) {
  const file = new File([blob], `voice-note-${Date.now()}.webm`, { type: blob.type || 'audio/webm' });
  return uploadFile(file, { kind: 'audio' });
}
