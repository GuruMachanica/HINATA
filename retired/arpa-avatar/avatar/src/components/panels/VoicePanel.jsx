import { useEffect, useState } from 'react';
import { getAudioSourceOptions } from '../../config/audioSources';
import {
  AUDIO_PRIVACY_NOTE,
  labelAudioCaptureStatus,
} from '../../lib/audioCaptureCopy';
import { getDesktopApi } from '../../lib/desktopMode';
import {
  defaultLipSyncMouthStrength,
  defaultLipSyncSensitivity,
} from '../../config/lipSyncSensitivity';
import { PanelSelect, SliderRow, Divider } from '../ui/PanelPrimitives';

export function VoicePanel({
  audioSourceId,
  onAudioSourceChange,
  setAudioFile,
  windowSourceId,
  setWindowSourceId,
  audioStatus,
  audioError,
  onRestartAudio,
  lipSyncSensitivity,
  onLipSyncSensitivityChange,
  lipSyncMouthStrength,
  onLipSyncMouthStrengthChange,
}) {
  const [windowSources, setWindowSources] = useState([]);
  const audioSourceOptions = getAudioSourceOptions();
  const desktopApi = getDesktopApi();
  const statusLabel = labelAudioCaptureStatus(audioStatus);
  const showPermissionHint =
    audioStatus === 'error' &&
    typeof audioError === 'string' &&
    /permission denied/i.test(audioError);

  useEffect(() => {
    if (audioSourceId !== 'window' || !desktopApi?.getDesktopSources) return;
    void desktopApi.getDesktopSources(['window', 'screen']).then(setWindowSources);
  }, [audioSourceId, desktopApi]);

  const sourceOptions = audioSourceOptions.map((option) => ({
    value: option.id,
    label: option.label,
  }));

  const windowOptions = [
    { value: '', label: 'Select a window…' },
    ...windowSources.map((source) => ({ value: source.id, label: source.name })),
  ];

  return (
    <>
      <p className="panel-note">
        {desktopApi
          ? 'Device output captures all PC audio automatically. Pick a window when you only want one app (Chrome, Discord, etc.).'
          : 'Choose an audio source to drive real-time lip sync. Tab capture works best for AI assistants or media in the browser.'}
      </p>
      <p className="panel-note panel-note--compact">{AUDIO_PRIVACY_NOTE}</p>

      <label className="field-label" htmlFor="audio-source-select">
        Audio source
      </label>
      <PanelSelect
        id="audio-source-select"
        value={audioSourceId}
        onChange={onAudioSourceChange}
        options={sourceOptions}
      />
      <p className="panel-hint">
        {audioSourceOptions.find((option) => option.id === audioSourceId)?.description}
      </p>

      {audioSourceId !== 'none' && (
        <>
          <Divider />

          <SliderRow
            stacked
            id="lip-sync-sensitivity"
            label="Sensitivity"
            min={0.25}
            max={4}
            step={0.25}
            value={lipSyncSensitivity}
            onChange={onLipSyncSensitivityChange}
            onDoubleClick={() => onLipSyncSensitivityChange(defaultLipSyncSensitivity)}
          />
          <p className="panel-hint">
            Raise this when audio is detected but the mouth barely moves. Double-click to reset.
          </p>

          <Divider />

          <SliderRow
            stacked
            id="lip-sync-mouth-limit"
            label="Mouth limit"
            min={0.1}
            max={1}
            step={0.05}
            value={lipSyncMouthStrength}
            onChange={onLipSyncMouthStrengthChange}
            onDoubleClick={() => onLipSyncMouthStrengthChange(defaultLipSyncMouthStrength)}
          />
          <p className="panel-hint">
            Limits the maximum VRM mouth-expression weight. Double-click to reset.
          </p>
        </>
      )}

      {audioSourceId === 'window' && (
        <>
          <Divider />

          <label className="field-label" htmlFor="window-source-select">
            Window or screen
          </label>
          <PanelSelect
            id="window-source-select"
            value={windowSourceId ?? ''}
            onChange={(next) => setWindowSourceId(next || null)}
            options={windowOptions}
            placeholder="Select a window…"
          />
        </>
      )}

      {audioSourceId === 'file' && (
        <>
          <Divider />
          <div className="file-picker-row">
            <input
              type="file"
              accept="audio/*"
              onChange={(event) => setAudioFile(event.target.files?.[0] ?? null)}
            />
          </div>
        </>
      )}

      <Divider />

      <div className="voice-status-row">
        <span
          className={`voice-status voice-status--${audioStatus}`}
          title={typeof audioStatus === 'string' ? audioStatus : undefined}
        >
          {statusLabel}
        </span>
        {audioError && <span className="voice-error">{audioError}</span>}
        {showPermissionHint && desktopApi?.openPrivacySettings && (
          <button
            type="button"
            className="panel-button"
            onClick={() => void desktopApi.openPrivacySettings()}
          >
            Open system privacy settings
          </button>
        )}
      </div>

      <button type="button" className="panel-button" onClick={onRestartAudio}>
        Restart audio capture
      </button>
    </>
  );
}
