/**
 * uploadService.js
 *
 * Handles file preparation and uploads for problem attachments.
 * For images ('photo'), converts the file to a standard base64 data URL
 * so that full image bytes safely reach the backend and Gemini Vision.
 * For non-image documents/videos, generates browser-local URLs for preview.
 */

let localIdCounter = 1;

const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg'];
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export async function uploadFile(file, { kind = 'document' } = {}) {
  // Simulate a short network delay so upload UI states can be shown.
  await new Promise((resolve) => setTimeout(resolve, 200));

  const isImage = kind === 'photo' || (file.type && file.type.startsWith('image/'));

  let fileUrl = null;

  if (isImage) {
    // Validate MIME type
    if (file.type && !ALLOWED_IMAGE_TYPES.includes(file.type.toLowerCase())) {
      throw new Error(`Unsupported image format: ${file.type}. Allowed formats: JPEG, PNG, WebP.`);
    }

    // Validate size limit
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      throw new Error(`Image size exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB).`);
    }

    // Convert image to base64 Data URL so backend receives real bytes
    fileUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Failed to read image file into data URL.'));
      reader.readAsDataURL(file);
    });
  } else {
    // Documents or videos use object URLs for local browser preview
    fileUrl = URL.createObjectURL(file);
  }

  return {
    id: `local-${Date.now()}-${localIdCounter++}`,
    url: fileUrl,
    name: file.name,
    kind,
    size: file.size,
    mimeType: file.type || (isImage ? 'image/jpeg' : 'application/octet-stream'),
  };
}

export function revokeUploadUrl(url) {
  try {
    if (url && typeof url === 'string' && url.startsWith('blob:')) {
      URL.revokeObjectURL(url);
    }
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
