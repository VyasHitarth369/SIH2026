import Trans from './Trans.jsx';
import { useRef, useState } from 'react';
import { uploadFile, revokeUploadUrl } from '../../services/uploadService';

/**
 * A single attachment slot: label + hidden file input + drag/drop area.
 * Shows an inline preview once a file is selected/uploaded:
 *   - image  -> thumbnail
 *   - video  -> {<Trans text="playable" />} <video>
 *   - other  -> file name chip
 */
export default function FileUploadField({ label, accept, kind, dragLabel, onChange }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null); // { id, url, name, kind, size }
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = async (fileList) => {
    const picked = fileList?.[0];
    if (!picked) return;
    setUploading(true);
    try {
      const uploaded = await uploadFile(picked, { kind });
      setFile(uploaded);
      onChange?.(uploaded);
    } finally {
      setUploading(false);
    }
  };

  const clear = () => {
    if (file?.url) revokeUploadUrl(file.url);
    setFile(null);
    onChange?.(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="field" style={{ marginBottom: 0 }}>
      <label>{label}</label>
      <div
        className={`upload-drop${dragOver ? ' upload-drop--active' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="upload-drop__input"
          onChange={(e) => handleFiles(e.target.files)}
        />

        {!file && !uploading && (
          <div className="upload-drop__empty">
            <span className="upload-drop__icon">{kind === 'video' ? '🎥' : kind === 'photo' ? '🖼️' : '📄'}</span>
            <span>{dragLabel}</span>
          </div>
        )}

        {uploading && <div className="upload-drop__empty">{<Trans text="⏳ Uploading…" />}</div>}

        {file && !uploading && (
          <div className="upload-drop__preview" onClick={(e) => e.stopPropagation()}>
            {kind === 'photo' && <img src={file.url} alt={file.name} />}
            {kind === 'video' && <video src={file.url} controls preload="metadata" />}
            {kind === 'document' && <div className="upload-drop__file-chip">📄 {file.name}</div>}
            <div className="upload-drop__meta">
              <span className="upload-drop__name">{file.name}</span>
              <button type="button" className="upload-drop__remove" onClick={clear}>✕</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
